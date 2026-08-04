"""Provider-free atomic scene commit stage."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .artifact_registry import artifact_directory
from .artifact_record import validate_record
from .commit_recovery import recover_pending_commit
from .filesystem_security import atomic_write_text, assert_no_symlink_path
from .run_state import RunStateStore, make_pending_target
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore, validate_selection_snapshot
from .series_contracts import ContractError
from .state_derivation import apply_continuity_state
from .workspace import validate_workspace


def create_scene_commit_stage_service(workspace_root: Path) -> "SceneCommitStageService":
    return SceneCommitStageService(workspace_root)


class SceneCommitStageService:
    """Commit selected prose and continuity exactly once, without a model call."""

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
        del model  # This stage is deliberately provider-free.
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        state = self.state_store.load()
        if state["status"] != "running" or state["current_stage"] != "scene_commit":
            raise ContractError("現在のrun-stateは実行可能なscene_commitではありません")
        if state["pending_commit"] is not None:
            return recover_pending_commit(self.workspace_root)
        timestamp = updated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        input_selection_id = state["current_selection_id"]
        assert isinstance(input_selection_id, str)
        target = state["current_target"]
        volume, chapter, scene_number = self._coordinate(target)
        slots = resolve_selection(
            self.workspace_root,
            SelectionSnapshotStore(self.workspace_root).load(input_selection_id),
        )
        values = self._inputs(slots, volume, chapter, scene_number)
        self._validate_quality_disposition(values["continuity_disposition"])
        scene_plan = values["scene_plan"]["content"]
        scene_card = values["scene_card"]["content"]
        prose = values["scene_prose"]["content"]
        continuity = values["continuity_update"]["content"]
        old_state = values["current_state"]["content"]
        from .scene_continuity_stage import SceneContinuityStageService
        SceneContinuityStageService._validate_content(continuity, {
            "volume_number": volume, "chapter_number": chapter, "scene_number": scene_number,
        }, slots)
        self._validate_coordinate_bundle(
            volume, chapter, scene_number, scene_plan, scene_card, prose, continuity,
        )
        next_state_content = self._apply_continuity(old_state, continuity)

        scene_id = f"scene-v{volume:02d}-c{chapter:02d}-s{scene_number:02d}-{reserve_counter(self.workspace_root, 'next_scene'):06d}"
        generation_id = f"gen-{reserve_counter(self.workspace_root, 'next_generation'):06d}"
        scene_commit_id = f"scene-commit-v{volume:02d}-c{chapter:02d}-s{scene_number:02d}-{reserve_counter(self.workspace_root, 'next_scene_commit'):06d}"
        output_selection_id = f"selection-{reserve_counter(self.workspace_root, 'next_selection'):06d}"
        next_stage, next_target = self._next_work(values, volume, chapter, scene_number)
        scene_content = {
            "scene_prose_id": values["scene_prose"]["artifact_id"],
            "continuity_update_id": values["continuity_update"]["artifact_id"],
            "current_state_id": values["current_state"]["artifact_id"],
            "scene_card_id": values["scene_card"]["artifact_id"],
            "quality_disposition_id": values["scene_prose_disposition"]["quality_id"],
            "coordinate": {"volume_number": volume, "chapter_number": chapter, "scene_number": scene_number},
        }
        commit_record = {
            "schema_version": 1,
            "scene_commit_id": scene_commit_id,
            "scene_id": scene_id,
            "scene_card_id": scene_content["scene_card_id"],
            "scene_prose_id": scene_content["scene_prose_id"],
            "continuity_update_id": scene_content["continuity_update_id"],
            "current_state_id": generation_id,
            "quality_disposition_id": scene_content["quality_disposition_id"],
            "volume_number": volume,
            "chapter_number": chapter,
            "scene_number": scene_number,
            "created_at": timestamp,
        }
        output_slots = dict(slots_to_ids(slots))
        output_slots.update({
            f"scene.v{volume:02d}.c{chapter:02d}.s{scene_number:02d}": scene_id,
            "current_state": generation_id,
            f"scene_commit.v{volume:02d}.c{chapter:02d}.s{scene_number:02d}": scene_commit_id,
        })
        selection = {
            "schema_version": 1, "selection_id": output_selection_id,
            "input_selection_id": input_selection_id, "slots": output_slots, "created_at": timestamp,
        }
        validate_selection_snapshot(selection)
        staging_root = f"runtime/staging/scene-commit-{scene_commit_id}"
        records = {
            scene_id: self._content_record(scene_id, "scene", input_selection_id, timestamp, scene_content),
            generation_id: self._content_record(generation_id, "generation", input_selection_id, timestamp, next_state_content),
            scene_commit_id: commit_record,
            output_selection_id: selection,
        }
        for artifact_id, record in records.items():
            self._write_staged_record(f"{staging_root}/{artifact_id}", record)
        targets = [
            self._target(scene_id, "scene", staging_root),
            self._target(generation_id, "generation", staging_root),
            self._target(scene_commit_id, "scene-commit", staging_root),
            self._target(output_selection_id, "selection", staging_root),
        ]
        working = deepcopy(state)
        working["updated_at"] = timestamp
        working["pending_commit"] = {
            "kind": "scene_commit", "staging_path": staging_root,
            "input_selection_id": input_selection_id, "output_selection_id": output_selection_id,
            "state_update": {
                "current_selection_id": output_selection_id,
                "current_stage": next_stage, "current_target": next_target,
            },
            "targets": targets,
        }
        self.state_store.save(working)
        return recover_pending_commit(self.workspace_root)

    @staticmethod
    def _content_record(artifact_id: str, kind: str, selection_id: str, timestamp: str, content: dict[str, Any]) -> dict[str, Any]:
        return {"schema_version": 1, "artifact_id": artifact_id, "artifact_kind": kind,
                "input_selection_id": selection_id, "created_at": timestamp, "content": content}

    @staticmethod
    def _target(artifact_id: str, kind: str, staging_root: str) -> dict[str, Any]:
        staging_path = f"{staging_root}/{artifact_id}"
        return make_pending_target(artifact_id, kind, staging_path, artifact_directory(kind, artifact_id).as_posix())

    def _write_staged_record(self, relative_directory: str, record: dict[str, Any]) -> None:
        directory = self.workspace_root / relative_directory
        directory.mkdir(parents=True)
        assert_no_symlink_path(directory, require_directory=True)
        atomic_write_text(directory / "record.json", json.dumps(record, ensure_ascii=False, indent=2) + "\n")

    @staticmethod
    def _coordinate(target: object) -> tuple[int, int, int]:
        if not isinstance(target, dict):
            raise ContractError("scene_commitのcurrent_targetが不正です")
        values = tuple(target.get(key) for key in ("volume_number", "chapter_number", "scene_number"))
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in values):
            raise ContractError("scene_commitには有効な場面座標が必要です")
        return values  # type: ignore[return-value]

    @staticmethod
    def _inputs(slots: dict[str, dict[str, Any]], volume: int, chapter: int, scene: int) -> dict[str, dict[str, Any]]:
        names = {
            "series_plan": "series_plan", "volume_plan": f"volume_plan.v{volume:02d}",
            "chapter_plan": f"chapter_plan.v{volume:02d}.c{chapter:02d}",
            "scene_plan": f"scene_plan.v{volume:02d}.c{chapter:02d}.s{scene:02d}",
            "scene_card": f"scene_card.v{volume:02d}.c{chapter:02d}.s{scene:02d}",
            "scene_prose": f"scene_prose.v{volume:02d}.c{chapter:02d}.s{scene:02d}",
            "scene_prose_disposition": f"scene_prose_disposition.v{volume:02d}.c{chapter:02d}.s{scene:02d}",
            "continuity_update": f"continuity_update.v{volume:02d}.c{chapter:02d}.s{scene:02d}",
            "continuity_disposition": f"continuity_disposition.v{volume:02d}.c{chapter:02d}.s{scene:02d}",
            "current_state": "current_state",
        }
        missing = [label for label, slot in names.items() if slot not in slots]
        if missing:
            raise ContractError("scene_commit入力selectionに必須slotがありません: " + ", ".join(missing))
        return {label: slots[slot] for label, slot in names.items()}

    @staticmethod
    def _validate_quality_disposition(record: dict[str, Any]) -> None:
        if not isinstance(record, dict) or record.get("result") not in {"accepted", "accepted_with_notice"}:
            raise ContractError("continuity_dispositionの品質判定が不正です")

    @staticmethod
    def _validate_coordinate_bundle(volume: int, chapter: int, scene: int, *contents: object) -> None:
        expected = {"volume_number": volume, "chapter_number": chapter, "scene_number": scene}
        for content in contents:
            if not isinstance(content, dict) or ("coordinate" in content and content.get("coordinate") != expected):
                raise ContractError("scene_commit入力成果物の座標が一致しません")

    @staticmethod
    def _apply_continuity(old_state: object, continuity: object) -> dict[str, Any]:
        return apply_continuity_state(old_state, continuity)

    @staticmethod
    def _numbers(content: object, field: str, number_field: str) -> list[int]:
        if not isinstance(content, dict) or not isinstance(content.get(field), list):
            raise ContractError(f"{field}を持つ計画contentが必要です")
        values: list[int] = []
        for item in content[field]:
            raw = item.get(number_field) if isinstance(item, dict) else item
            if not isinstance(raw, int) or isinstance(raw, bool) or raw < 1:
                raise ContractError(f"{field}の番号が不正です")
            values.append(raw)
        if values != list(range(1, len(values) + 1)):
            raise ContractError(f"{field}の番号は1からの連続昇順でなければなりません")
        return values

    def _next_work(self, values: dict[str, dict[str, Any]], volume: int, chapter: int, scene: int) -> tuple[str, dict[str, int]]:
        scenes = self._numbers(values["chapter_plan"]["content"], "scene_summaries", "scene_number")
        chapters = self._numbers(values["volume_plan"]["content"], "chapter_summaries", "chapter_number")
        if scene not in scenes or chapter not in chapters:
            raise ContractError("scene_commit対象が親計画にありません")
        scene_index = scenes.index(scene)
        if scene_index + 1 < len(scenes):
            return "scene_plan", {"volume_number": volume, "chapter_number": chapter, "scene_number": scenes[scene_index + 1]}
        chapter_index = chapters.index(chapter)
        if chapter_index + 1 < len(chapters):
            return "chapter_plan", {"volume_number": volume, "chapter_number": chapters[chapter_index + 1]}
        return "volume_publication", {"volume_number": volume}


def slots_to_ids(slots: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Recover the ID field from resolved immutable records without path lookup."""
    result: dict[str, str] = {}
    for slot, record in slots.items():
        fields = ("artifact_id", "settings_id", "adoption_id", "quality_id", "scene_commit_id", "selection_id", "publication_id", "call_id")
        artifact_id = next((record.get(field) for field in fields if isinstance(record.get(field), str)), None)
        if not isinstance(artifact_id, str):
            raise ContractError("selection入力recordのIDが不正です")
        result[slot] = artifact_id
    return result
