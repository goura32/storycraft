"""V2 selection-based scene continuity adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .candidate_stage import CandidateStageRunner, CandidateStageSpec
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError
from .workspace import validate_workspace


class SceneContinuityStageService:
    """Propose and adopt continuity only against the selected adopted prose."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()

    def run(self, model: Any | None, *, workspace_already_validated: bool = False, updated_at: str | None = None) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        if updated_at is None:
            raise ContractError("scene_continuityの確定時刻が必要です")
        from .run_state import RunStateStore
        state = RunStateStore(self.workspace_root).load()
        if state["status"] != "running" or state["current_stage"] != "scene_continuity":
            raise ContractError("現在のrun-stateは実行可能なscene_continuityではありません")
        selection_id = state["current_selection_id"]
        if not isinstance(selection_id, str):
            raise ContractError("scene_continuityには入力selectionが必要です")
        target = self._coordinate(state["current_target"])
        snapshot = SelectionSnapshotStore(self.workspace_root).load(selection_id)
        coordinate = self._slot_coordinate(target)
        required = {"settings", "current_state", f"scene_plan.{coordinate}", f"scene_card.{coordinate}", f"scene_prose.{coordinate}"}
        if not required.issubset(snapshot["slots"]):
            raise ContractError("scene_continuity入力selectionに必須slotがありません")
        bundle = dict(snapshot)
        bundle["slots"] = {slot: snapshot["slots"][slot] for slot in required}
        inputs = resolve_selection(self.workspace_root, bundle)
        self._require_inputs(inputs, target)
        spec = CandidateStageSpec(
            stage="scene_continuity", artifact_kind="continuity-update", next_stage="scene_commit",
            next_target=dict(target), content_id_factory=self._content_id,
            content_validator=lambda content: self._validate_content(content, target),
        )
        return CandidateStageRunner(self.workspace_root, spec).run(
            model, context=self._context(inputs, target), updated_at=updated_at,
        )

    @staticmethod
    def _coordinate(value: object) -> dict[str, int]:
        if not isinstance(value, dict) or set(value) != {"volume_number", "chapter_number", "scene_number"}:
            raise ContractError("scene_continuityのcurrent_targetが不正です")
        if any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in value.values()):
            raise ContractError("scene_continuityには有効な場面座標が必要です")
        return dict(value)

    @staticmethod
    def _slot_coordinate(target: dict[str, int]) -> str:
        return f"v{target['volume_number']:02d}.c{target['chapter_number']:02d}.s{target['scene_number']:02d}"

    @staticmethod
    def _payload(record: dict[str, Any], slot: str) -> dict[str, Any]:
        value = record.get("payload") if slot == "settings" else record.get("content")
        if not isinstance(value, dict):
            raise ContractError(f"scene_continuity入力{slot}の内容が不正です")
        return value

    def _require_inputs(self, inputs: dict[str, dict[str, Any]], target: dict[str, int]) -> None:
        coordinate = self._slot_coordinate(target)
        required = {"settings", "current_state", f"scene_plan.{coordinate}", f"scene_card.{coordinate}", f"scene_prose.{coordinate}"}
        if not required.issubset(inputs):
            raise ContractError("scene_continuity入力selectionが不正です")
        for slot in (f"scene_plan.{coordinate}", f"scene_card.{coordinate}", f"scene_prose.{coordinate}"):
            if not isinstance(self._payload(inputs[slot], slot), dict):
                raise ContractError("scene_continuity入力成果物が不正です")

    def _context(self, inputs: dict[str, dict[str, Any]], target: dict[str, int]) -> dict[str, Any]:
        coordinate = self._slot_coordinate(target)
        return {
            "settings": self._payload(inputs["settings"], "settings"),
            "current_state": self._payload(inputs["current_state"], "current_state"),
            "scene_plan": self._payload(inputs[f"scene_plan.{coordinate}"], "scene_plan"),
            "scene_card": self._payload(inputs[f"scene_card.{coordinate}"], "scene_card"),
            "scene_prose": self._payload(inputs[f"scene_prose.{coordinate}"], "scene_prose"),
            **target,
        }

    def _content_id(self, _root: Path, target: dict[str, Any]) -> str:
        return f"continuity-v{target['volume_number']:02d}-c{target['chapter_number']:02d}-s{target['scene_number']:02d}-{reserve_counter(self.workspace_root, 'next_continuity'):06d}"

    @staticmethod
    def _validate_content(content: object, target: dict[str, int]) -> None:
        if not isinstance(content, dict) or set(content) != {"coordinate", "changes"} or content.get("coordinate") != target or not isinstance(content.get("changes"), list):
            raise ContractError("continuity_update contentが不正です")
        for change in content["changes"]:
            if not isinstance(change, dict) or set(change) != {"op", "target", "path", "value", "evidence_locations"}:
                raise ContractError("continuity_update changeが不正です")
            if change["op"] not in {"set", "add", "remove"} or change["target"] not in {"story_facts", "character_knowledge", "reader_disclosures", "unresolved_thread_states", "timeline_position"}:
                raise ContractError("continuity_update changeが不正です")
            if not isinstance(change["path"], str) or not change["path"].startswith(f"$.{change['target']}"):
                raise ContractError("continuity_update pathが不正です")
            if not isinstance(change["evidence_locations"], list) or not change["evidence_locations"] or any(not isinstance(item, str) or not item for item in change["evidence_locations"]):
                raise ContractError("continuity_update evidence_locationsが不正です")


def create_scene_continuity_stage_service(workspace_root: Path) -> SceneContinuityStageService:
    return SceneContinuityStageService(workspace_root)
