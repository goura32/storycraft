"""V2 provider-free volume publication through the generic commit manifest."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .commit_recovery import recover_pending_commit
from .publication_builder import build_volume_publication_files, validate_volume_publication_files
from .run_state import RunStateStore
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError
from .workspace import validate_workspace


def create_volume_publication_stage_service(workspace_root: Path) -> "VolumePublicationStageService":
    return VolumePublicationStageService(workspace_root)


class VolumePublicationStageService:
    """Publish exactly the committed scene sources selected for one volume."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        model: Any | None = None,
        *,
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        del model
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        state = self.state_store.load()
        if state["status"] != "running" or state["current_stage"] != "volume_publication":
            raise ContractError("現在のrun-stateは実行可能なvolume_publicationではありません")
        if state["pending_commit"] is not None:
            return recover_pending_commit(self.workspace_root)
        timestamp = updated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        volume_number = self._volume_number(state["current_target"])
        input_selection_id = state["current_selection_id"]
        assert isinstance(input_selection_id, str)
        slots = resolve_selection(
            self.workspace_root,
            SelectionSnapshotStore(self.workspace_root).load(input_selection_id),
        )
        inputs = self._publication_inputs(slots, volume_number)
        publication_id = f"volume-pub-v{volume_number:02d}-{reserve_counter(self.workspace_root, 'next_volume_publication'):06d}"
        files = build_volume_publication_files(
            publication_id=publication_id,
            volume_number=volume_number,
            input_selection_id=input_selection_id,
            settings_id=inputs["settings_id"],
            series_plan_id=inputs["series_plan_id"],
            volume_plan_id=inputs["volume_plan_id"],
            current_state_id=inputs["current_state_id"],
            chapter_plan_ids=inputs["chapter_plan_ids"],
            scene_ids=inputs["scene_ids"],
            quality_disposition_refs=inputs["quality_ids"],
            scenes=inputs["scenes"],
            remaining_major_issues=inputs["has_remaining_major_issues"],
            created_at=timestamp,
        )
        validate_volume_publication_files(files)
        staging_root = f"runtime/staging/volume-publication-{publication_id}"
        staging_target = f"{staging_root}/{publication_id}"
        self._write_files(staging_target, files)
        if volume_number == inputs["volume_count"]:
            state_update = {
                "status": "completed",
                "last_error": None,
                "current_selection_id": input_selection_id,
                "current_stage": None,
                "current_target": None,
                "published_volumes": [
                    *state["published_volumes"],
                    {"volume_number": volume_number, "publication_id": publication_id},
                ],
            }
        else:
            state_update = {
                "current_selection_id": input_selection_id,
                "current_stage": "volume_plan",
                "current_target": {"volume_number": volume_number + 1},
                "published_volumes": [
                    *state["published_volumes"],
                    {"volume_number": volume_number, "publication_id": publication_id},
                ],
            }
        pending = {
            "kind": "volume_publication",
            "staging_path": staging_root,
            "input_selection_id": input_selection_id,
            "output_selection_id": None,
            "state_update": state_update,
            "targets": [{
                "artifact_id": publication_id,
                "artifact_kind": "volume-publication",
                "staging_path": staging_target,
                "final_path": f"publications/{publication_id}",
                "status": "pending",
            }],
        }
        working = deepcopy(state)
        working["updated_at"] = timestamp
        working["pending_commit"] = pending
        self.state_store.save(working)
        return recover_pending_commit(self.workspace_root)

    @staticmethod
    def _volume_number(target: object) -> int:
        if not isinstance(target, dict) or set(target) != {"volume_number"}:
            raise ContractError("volume_publication.current_targetが不正です")
        number = target["volume_number"]
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            raise ContractError("volume_publication.current_target.volume_numberが不正です")
        return number

    def _publication_inputs(self, slots: dict[str, dict[str, Any]], volume: int) -> dict[str, Any]:
        settings = self._slot(slots, "settings")
        series = self._slot(slots, "series_plan")
        volume_plan = self._slot(slots, f"volume_plan.v{volume:02d}")
        current_state = self._slot(slots, "current_state")
        settings_id = self._record_id(settings, "settings_id")
        series_id = self._record_id(series, "artifact_id")
        volume_id = self._record_id(volume_plan, "artifact_id")
        current_state_id = self._record_id(current_state, "artifact_id")
        if volume_plan.get("artifact_kind") != "volume-plan" or current_state.get("artifact_kind") != "generation":
            raise ContractError("巻公開selectionのvolume planまたはcurrent stateが不正です")
        volume_content = volume_plan.get("content")
        if not isinstance(volume_content, dict):
            raise ContractError("巻公開selectionのvolume planが不正です")
        volume_count = self._volume_count(series, volume)
        chapter_numbers = self._ordered_numbers(volume_content, "chapters", "chapter_number")
        chapter_slots = {f"chapter_plan.v{volume:02d}.c{number:02d}" for number in chapter_numbers}
        selected_chapter_slots = {key for key in slots if key.startswith(f"chapter_plan.v{volume:02d}.")}
        if selected_chapter_slots != chapter_slots:
            raise ContractError("巻公開selectionのchapter plan集合が計画と一致しません")
        chapter_ids: list[str] = []
        scene_ids: list[str] = []
        quality_ids: list[str] = []
        scenes: list[dict[str, str]] = []
        has_remaining_major_issues = False
        for chapter in chapter_numbers:
            chapter_record = self._slot(slots, f"chapter_plan.v{volume:02d}.c{chapter:02d}")
            if chapter_record.get("artifact_kind") != "chapter-plan":
                raise ContractError("巻公開selectionのchapter planが不正です")
            chapter_content = chapter_record.get("content")
            if not isinstance(chapter_content, dict):
                raise ContractError("巻公開selectionのchapter planが不正です")
            chapter_ids.append(self._record_id(chapter_record, "artifact_id"))
            for scene in self._ordered_numbers(chapter_content, "scenes", "scene_number"):
                coordinate = f"v{volume:02d}.c{chapter:02d}.s{scene:02d}"
                committed = self._slot(slots, f"scene.{coordinate}")
                prose = self._slot(slots, f"scene_prose.{coordinate}")
                quality = self._slot(slots, f"scene_prose_disposition.{coordinate}")
                scene_card = self._slot(slots, f"scene_card.{coordinate}")
                continuity = self._slot(slots, f"continuity_update.{coordinate}")
                current_state = self._slot(slots, "current_state")
                self._validate_committed_source(committed, prose, quality, scene_card, continuity, current_state, volume, chapter, scene)
                scene_ids.append(self._record_id(committed, "artifact_id"))
                quality_ids.append(self._record_id(quality, "quality_id"))
                prose_content = prose["content"]
                assert isinstance(prose_content, dict)
                scenes.append({"scene_id": scene_ids[-1], "prose": prose_content["text"]})
                issues = quality["remaining_major_issues"]
                assert isinstance(issues, list)
                has_remaining_major_issues = has_remaining_major_issues or bool(issues)
        if not scene_ids:
            raise ContractError("巻公開には少なくとも一場面の確定が必要です")
        return {
            "settings_id": settings_id, "series_plan_id": series_id, "volume_plan_id": volume_id,
            "current_state_id": current_state_id, "chapter_plan_ids": chapter_ids, "scene_ids": scene_ids,
            "quality_ids": quality_ids, "scenes": scenes,
            "has_remaining_major_issues": has_remaining_major_issues, "volume_count": volume_count,
        }

    @staticmethod
    def _slot(slots: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
        record = slots.get(name)
        if not isinstance(record, dict):
            raise ContractError(f"巻公開に必要なselection slotがありません: {name}")
        return record

    @staticmethod
    def _record_id(record: dict[str, Any], name: str) -> str:
        value = record.get(name)
        if not isinstance(value, str) or not value:
            raise ContractError("巻公開selection recordのIDが不正です")
        return value

    @staticmethod
    def _ordered_numbers(content: object, field: str, number_field: str) -> list[int]:
        modern_field = {"volumes": "volume_summaries", "chapters": "chapter_summaries", "scenes": "scene_summaries"}.get(field, field)
        if not isinstance(content, dict) or not isinstance(content.get(modern_field), list):
            raise ContractError(f"巻公開の{field}計画が不正です")
        result: list[int] = []
        for item in content[modern_field]:
            number = item.get(number_field) if isinstance(item, dict) else None
            if not isinstance(number, int) or isinstance(number, bool) or number < 1:
                raise ContractError(f"巻公開の{field}計画番号が不正です")
            result.append(number)
        if not result or result != list(range(1, len(result) + 1)):
            raise ContractError(f"巻公開の{field}計画は1からの連続昇順でなければなりません")
        return result

    def _volume_count(self, series: dict[str, Any], volume: int) -> int:
        if series.get("artifact_kind") != "series-plan":
            raise ContractError("巻公開selectionのseries planが不正です")
        numbers = self._ordered_numbers(series.get("content"), "volumes", "volume_number")
        if numbers != list(range(1, len(numbers) + 1)) or volume not in numbers:
            raise ContractError("巻公開selectionのseries plan巻集合が不正です")
        return len(numbers)

    @staticmethod
    def _validate_committed_source(
        committed: dict[str, Any], prose: dict[str, Any], quality: dict[str, Any],
        scene_card: dict[str, Any], continuity: dict[str, Any], current_state: dict[str, Any],
        volume: int, chapter: int, scene: int,
    ) -> None:
        coordinate = {"volume_number": volume, "chapter_number": chapter, "scene_number": scene}
        committed_content = committed.get("content")
        prose_content = prose.get("content")
        if (
            committed.get("artifact_kind") != "scene" or prose.get("artifact_kind") != "scene-prose"
            or not isinstance(committed_content, dict) or not isinstance(prose_content, dict)
            or committed_content.get("coordinate") != coordinate or prose_content.get("coordinate") != coordinate
            or committed_content.get("scene_prose_id") != prose.get("artifact_id")
            or committed_content.get("scene_card_id") != scene_card.get("artifact_id")
            or committed_content.get("continuity_update_id") != continuity.get("artifact_id")
            or committed_content.get("current_state_id") != current_state.get("artifact_id")
            or committed_content.get("quality_disposition_id") != quality.get("quality_id")
            or not isinstance(prose_content.get("text"), str) or not prose_content["text"].strip()
        ):
            raise ContractError("巻公開の確定場面sourceがselectionと一致しません")
        if quality.get("result") not in {"accepted", "accepted_with_notice"}:
            raise ContractError("巻公開のscene prose品質判定が公開可能ではありません")
        if not isinstance(quality.get("remaining_major_issues"), list):
            raise ContractError("巻公開のscene prose品質判定が不正です")

    def _write_files(self, staging_root: str, files: dict[str, dict[str, Any] | str]) -> None:
        directory = self.workspace_root / staging_root
        if directory.exists() or directory.is_symlink():
            raise ContractError("巻公開staging directoryを上書きできません")
        directory.mkdir(parents=True)
        for name, value in files.items():
            path = directory / name
            text = json.dumps(value, ensure_ascii=False, indent=2) + "\n" if isinstance(value, dict) else value
            path.write_text(text, encoding="utf-8")
