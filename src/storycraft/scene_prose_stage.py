"""V2 selection-based scene prose adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .candidate_stage import CandidateStageRunner, CandidateStageSpec
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError
from .workspace import validate_workspace


class SceneProseStageService:
    """Generate and adopt prose exclusively from the current immutable selection."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()

    def run(self, model: Any | None, *, workspace_already_validated: bool = False, updated_at: str | None = None) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        if updated_at is None:
            raise ContractError("scene_proseの確定時刻が必要です")
        from .run_state import RunStateStore
        state = RunStateStore(self.workspace_root).load()
        if state["status"] != "running" or state["current_stage"] != "scene_prose":
            raise ContractError("現在のrun-stateは実行可能なscene_proseではありません")
        selection_id = state["current_selection_id"]
        if not isinstance(selection_id, str):
            raise ContractError("scene_proseには入力selectionが必要です")
        target = self._coordinate(state["current_target"])
        snapshot = SelectionSnapshotStore(self.workspace_root).load(selection_id)
        coordinate = self._slot_coordinate(target)
        required = {"settings", "current_state", f"scene_plan.{coordinate}", f"scene_card.{coordinate}"}
        if not required.issubset(snapshot["slots"]):
            raise ContractError("scene_prose入力selectionに必須slotがありません")
        bundle = dict(snapshot)
        bundle["slots"] = {slot: snapshot["slots"][slot] for slot in required}
        inputs = resolve_selection(self.workspace_root, bundle)
        self._require_inputs(inputs, target)
        spec = CandidateStageSpec(
            stage="scene_prose", artifact_kind="scene-prose", next_stage="scene_continuity",
            next_target=dict(target), content_id_factory=self._content_id,
            content_validator=lambda content: self._validate_content(content, target, inputs["settings"]),
        )
        return CandidateStageRunner(self.workspace_root, spec).run(
            model, context=self._context(inputs, target), updated_at=updated_at,
        )

    @staticmethod
    def _coordinate(value: object) -> dict[str, int]:
        if not isinstance(value, dict) or set(value) != {"volume_number", "chapter_number", "scene_number"}:
            raise ContractError("scene_proseのcurrent_targetが不正です")
        if any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in value.values()):
            raise ContractError("scene_proseには有効な場面座標が必要です")
        return dict(value)

    @staticmethod
    def _slot_coordinate(target: dict[str, int]) -> str:
        return f"v{target['volume_number']:02d}.c{target['chapter_number']:02d}.s{target['scene_number']:02d}"

    @staticmethod
    def _payload(record: dict[str, Any], slot: str) -> dict[str, Any]:
        value = record.get("payload") if slot == "settings" else record.get("content")
        if not isinstance(value, dict):
            raise ContractError(f"scene_prose入力{slot}の内容が不正です")
        return value

    def _require_inputs(self, inputs: dict[str, dict[str, Any]], target: dict[str, int]) -> None:
        coordinate = self._slot_coordinate(target)
        required = {"settings", "current_state", f"scene_plan.{coordinate}", f"scene_card.{coordinate}"}
        if not required.issubset(inputs):
            raise ContractError("scene_prose入力selectionが不正です")
        expected = target
        for slot in (f"scene_plan.{coordinate}", f"scene_card.{coordinate}"):
            content = self._payload(inputs[slot], slot)
            if not isinstance(content, dict):
                raise ContractError("scene_prose入力成果物が不正です")

    def _context(self, inputs: dict[str, dict[str, Any]], target: dict[str, int]) -> dict[str, Any]:
        coordinate = self._slot_coordinate(target)
        return {
            "settings": self._payload(inputs["settings"], "settings"),
            "current_state": self._payload(inputs["current_state"], "current_state"),
            "scene_plan": self._payload(inputs[f"scene_plan.{coordinate}"], "scene_plan"),
            "scene_card": self._payload(inputs[f"scene_card.{coordinate}"], "scene_card"),
            **target,
        }

    def _content_id(self, _root: Path, target: dict[str, Any]) -> str:
        return f"scene-prose-v{target['volume_number']:02d}-c{target['chapter_number']:02d}-s{target['scene_number']:02d}-{reserve_counter(self.workspace_root, 'next_scene_prose'):06d}"

    @staticmethod
    def _validate_content(content: object, target: dict[str, int], settings: dict[str, Any]) -> None:
        if not isinstance(content, dict) or set(content) != {"coordinate", "text"} or content.get("coordinate") != target:
            raise ContractError("scene_prose contentが不正です")
        text = content.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ContractError("scene_prose textが不正です")
        range_value = settings.get("scene_text_char_range")
        if range_value is not None:
            if not isinstance(range_value, list) or len(range_value) != 2 or any(not isinstance(item, int) or isinstance(item, bool) for item in range_value) or not 1 <= range_value[0] <= range_value[1] or not range_value[0] <= len(text) <= range_value[1]:
                raise ContractError("scene_prose textの長さがsettingsと一致しません")


def create_scene_prose_stage_service(workspace_root: Path) -> SceneProseStageService:
    return SceneProseStageService(workspace_root)
