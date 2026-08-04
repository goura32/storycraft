"""Provider-free volume publication through the generic commit manifest."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .artifact_record import validate_candidate_record, validate_quality_evidence, validate_record, validate_review_record
from .artifact_ids import reserve_counter
from .commit_recovery import recover_pending_commit
from .filesystem_security import atomic_write_text, assert_no_symlink_path, read_text_nofollow
from .publication_builder import build_volume_publication_files, validate_volume_publication_files
from .run_state import RunStateStore, make_pending_target
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError
from .state_derivation import apply_continuity_state
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
            "targets": [make_pending_target(
                publication_id, "volume-publication", staging_target, f"publications/{publication_id}",
            )],
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
        chapter_numbers = self._ordered_numbers(volume_content, "chapter_summaries", "chapter_number")
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
            for scene in self._ordered_numbers(chapter_content, "scene_summaries", "scene_number"):
                coordinate = f"v{volume:02d}.c{chapter:02d}.s{scene:02d}"
                committed = self._slot(slots, f"scene.{coordinate}")
                commit_record = self._slot(slots, f"scene_commit.{coordinate}")
                prose = self._slot(slots, f"scene_prose.{coordinate}")
                quality = self._slot(slots, f"scene_prose_disposition.{coordinate}")
                continuity_quality = self._slot(slots, f"continuity_disposition.{coordinate}")
                scene_card = self._slot(slots, f"scene_card.{coordinate}")
                continuity = self._slot(slots, f"continuity_update.{coordinate}")
                self._validate_quality_record(quality, "scene_prose_disposition")
                self._validate_quality_record(continuity_quality, "continuity_disposition")
                commit_id = self._record_id(commit_record, "scene_commit_id")
                validate_record("scene-commit", commit_id, commit_record)
                if (
                    commit_record.get("scene_id") != committed.get("artifact_id")
                    or commit_record.get("scene_prose_id") != prose.get("artifact_id")
                    or commit_record.get("scene_card_id") != scene_card.get("artifact_id")
                    or commit_record.get("continuity_update_id") != continuity.get("artifact_id")
                    or commit_record.get("quality_disposition_id") != quality.get("quality_id")
                ):
                    raise ContractError("巻公開のscene_commit recordがselection sourceと一致しません")
                source_state_id = self._committed_input_state_id(committed)
                self._validate_committed_source(committed, prose, quality, scene_card, continuity, source_state_id, volume, chapter, scene)
                self._validate_scene_commit_generation(commit_record, committed, continuity, source_state_id, current_state_id)
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
        if not isinstance(content, dict) or not isinstance(content.get(field), list):
            raise ContractError(f"巻公開の{field}計画が不正です")
        result: list[int] = []
        for item in content[field]:
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
        numbers = self._ordered_numbers(series.get("content"), "volume_summaries", "volume_number")
        if numbers != list(range(1, len(numbers) + 1)) or volume not in numbers:
            raise ContractError("巻公開selectionのseries plan巻集合が不正です")
        return len(numbers)

    def _committed_input_state_id(self, committed: dict[str, Any]) -> str:
        """Return the state selected when this scene was generated."""
        input_selection_id = committed.get("input_selection_id")
        if not isinstance(input_selection_id, str):
            raise ContractError("巻公開の確定場面に入力selectionがありません")
        try:
            snapshot = SelectionSnapshotStore(self.workspace_root).load(input_selection_id)
        except ContractError as exc:
            raise ContractError("巻公開の確定場面入力selectionを読めません") from exc
        state_id = snapshot["slots"].get("current_state")
        if not isinstance(state_id, str) or not state_id:
            raise ContractError("巻公開の確定場面入力selectionにcurrent_stateがありません")
        return state_id

    def _validate_quality_record(self, record: dict[str, Any], slot_name: str) -> None:
        if not isinstance(record, dict) or record.get("result") not in {"accepted", "accepted_with_notice"}:
            raise ContractError(f"{slot_name}の品質判定が不正です")
        root = assert_no_symlink_path(self.workspace_root, require_directory=True)
        quality_id = record.get("quality_id")
        if not isinstance(quality_id, str):
            raise ContractError(f"{slot_name}のquality_idが不正です")
        validate_record("quality-disposition", quality_id, record)
        issues = record.get("remaining_major_issues")
        if not isinstance(issues, list):
            raise ContractError(f"{slot_name}のremaining_major_issuesが不正です")
        if record["result"] == "accepted" and (issues or "notice_type" in record):
            raise ContractError(f"{slot_name}のaccepted判定が不正です")
        if record["result"] == "accepted_with_notice" and (not issues or record.get("notice_type") != "編集"):
            raise ContractError(f"{slot_name}のaccepted_with_notice判定が不正です")
        candidate_id = record.get("candidate_id")
        review_ids = record.get("review_record_ids")
        if not isinstance(candidate_id, str) or not isinstance(review_ids, list) or not review_ids or len(review_ids) != len(set(review_ids)):
            raise ContractError(f"{slot_name}のcandidate/review参照が不正です")
        candidate = self._load_json_record(root / "candidates" / candidate_id / "record.json")
        validate_candidate_record(candidate_id, candidate)
        reviews: dict[str, dict[str, Any]] = {}
        for review_id in review_ids:
            if not isinstance(review_id, str):
                raise ContractError(f"{slot_name}のreview参照が不正です")
            review = self._load_json_record(root / "reviews" / review_id / "record.json")
            validate_review_record(review_id, review)
            reviews[review_id] = review
        validate_quality_evidence(record, candidate["payload"], reviews)

    @staticmethod
    def _load_json_record(path: Path) -> dict[str, Any]:
        assert_no_symlink_path(path.parent, require_directory=True)
        if path.is_symlink() or not path.is_file():
            raise ContractError(f"品質参照recordが通常fileではありません: {path.name}")
        try:
            value = json.loads(read_text_nofollow(path))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("品質参照recordを読めません") from exc
        if not isinstance(value, dict):
            raise ContractError("品質参照recordがobjectではありません")
        return value

    @staticmethod
    def _validate_committed_source(
        committed: dict[str, Any], prose: dict[str, Any], quality: dict[str, Any],
        scene_card: dict[str, Any], continuity: dict[str, Any], scene_input_state_id: str,
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
            or committed_content.get("current_state_id") != scene_input_state_id
            or committed_content.get("quality_disposition_id") != quality.get("quality_id")
            or not isinstance(prose_content.get("text"), str) or not prose_content["text"].strip()
        ):
            raise ContractError("巻公開の確定場面sourceがselectionと一致しません")
        if quality.get("result") not in {"accepted", "accepted_with_notice"}:
            raise ContractError("巻公開のscene prose品質判定が公開可能ではありません")
        if not isinstance(quality.get("remaining_major_issues"), list):
            raise ContractError("巻公開のscene prose品質判定が不正です")

    def _validate_scene_commit_generation(
        self,
        committed: dict[str, Any],
        scene_record: dict[str, Any],
        continuity: dict[str, Any],
        input_state_id: str,
        final_state_id: str,
    ) -> None:
        output_state_id = committed.get("current_state_id")
        if not isinstance(output_state_id, str):
            raise ContractError("巻公開のscene_commit current_state参照が不正です")
        input_state = self._load_json_record(self.workspace_root / "generations" / input_state_id / "record.json")
        output_state = self._load_json_record(self.workspace_root / "generations" / output_state_id / "record.json")
        validate_record("generation", input_state_id, input_state)
        validate_record("generation", output_state_id, output_state)
        expected = apply_continuity_state(input_state.get("content"), continuity.get("content"))
        if output_state.get("content") != expected:
            raise ContractError("巻公開のscene_commit output generationが派生状態と一致しません")
        self._require_generation_ancestor(output_state_id, final_state_id)

    def _require_generation_ancestor(self, ancestor_id: str, descendant_id: str) -> None:
        current_id = descendant_id
        seen: set[str] = set()
        while current_id != ancestor_id:
            if current_id in seen:
                raise ContractError("巻公開のgeneration lineageが循環しています")
            seen.add(current_id)
            generation = self._load_json_record(self.workspace_root / "generations" / current_id / "record.json")
            validate_record("generation", current_id, generation)
            selection_id = generation.get("input_selection_id")
            if not isinstance(selection_id, str):
                raise ContractError("巻公開のgeneration input selectionが不正です")
            selection = SelectionSnapshotStore(self.workspace_root).load(selection_id)
            parent_id = selection["slots"].get("current_state")
            if not isinstance(parent_id, str):
                raise ContractError("巻公開のgeneration ancestorが不正です")
            current_id = parent_id

    def _write_files(self, staging_root: str, files: dict[str, dict[str, Any] | str]) -> None:
        directory = self.workspace_root / staging_root
        if directory.exists() or directory.is_symlink():
            raise ContractError("巻公開staging directoryを上書きできません")
        directory.mkdir(parents=True)
        for name, value in files.items():
            path = directory / name
            text = json.dumps(value, ensure_ascii=False, indent=2) + "\n" if isinstance(value, dict) else value
            atomic_write_text(path, text)
