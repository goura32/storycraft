"""V2 selection-based planning-stage adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .candidate_stage import CandidateStageRunner, CandidateStageSpec
from .selection_authority import DEFAULT_CONTENT_VALIDATORS, resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError
from .workspace import validate_workspace


class SceneCardStageService:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()

    def run(self, model: Any | None, *, workspace_already_validated: bool = False, updated_at: str | None = None) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        if updated_at is None:
            raise ContractError("scene_cardの確定時刻が必要です")
        from .run_state import RunStateStore
        state = RunStateStore(self.workspace_root).load()
        if state["current_stage"] != "scene_card" or state["status"] != "running":
            raise ContractError("現在のrun-stateは実行可能なscene_cardではありません")
        selection_id = state["current_selection_id"]
        if not isinstance(selection_id, str):
            raise ContractError("scene_cardには入力selectionが必要です")
        snapshot = SelectionSnapshotStore(self.workspace_root).load(selection_id)
        target = state["current_target"]
        volume, chapter, scene = target.get("volume_number"), target.get("chapter_number"), target.get("scene_number")
        coordinate = f"v{volume:02d}.c{chapter:02d}.s{scene:02d}"
        required_slots = {"settings", "initial_design", "current_state", f"scene_plan.{coordinate}", f"scene_plan_adoption.{coordinate}"}
        if not required_slots.issubset(snapshot["slots"]):
            raise ContractError("scene_card入力selectionに必須slotがありません")
        bundle = dict(snapshot)
        # The adoption is required provenance, not model content; resolve only the
        # documented content bundle after asserting its selected parent exists.
        bundle["slots"] = {slot: snapshot["slots"][slot] for slot in required_slots if not slot.startswith("scene_plan_adoption.")}
        inputs = resolve_selection(self.workspace_root, bundle)
        self._require_inputs(inputs, target)
        context = self._context(inputs, state["current_target"])
        target = dict(state["current_target"])
        spec = CandidateStageSpec(
            stage="scene_card", artifact_kind="scene-card", next_stage="scene_prose",
            next_target=dict(target), content_id_factory=self._content_id,
            content_validator=lambda content: DEFAULT_CONTENT_VALIDATORS["scene-card"](
                content,
                {**inputs, "__current_slot__": f"scene_card.v{volume:02d}.c{chapter:02d}.s{scene:02d}"},
            ),
        )
        return CandidateStageRunner(self.workspace_root, spec).run(model, context=context, updated_at=updated_at)

    @staticmethod
    def _payload(record: dict[str, Any], slot: str) -> dict[str, Any]:
        value = record.get("payload") if slot == "settings" else record.get("content")
        if not isinstance(value, dict):
            raise ContractError(f"scene_card入力{slot}の内容が不正です")
        return value

    def _require_inputs(self, inputs: dict[str, dict[str, Any]], target: dict[str, Any]) -> None:
        volume, chapter, scene = target.get("volume_number"), target.get("chapter_number"), target.get("scene_number")
        required = {"settings", "initial_design", "current_state"}
        slot = f"scene_plan.v{volume:02d}.c{chapter:02d}.s{scene:02d}" if all(isinstance(value, int) and not isinstance(value, bool) and value >= 1 for value in (volume, chapter, scene)) else ""
        if not slot or not required.issubset(inputs) or slot not in inputs:
            raise ContractError("scene_card入力selectionまたは座標が不正です")


    def _context(self, inputs: dict[str, dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
        volume, chapter, scene = target["volume_number"], target["chapter_number"], target["scene_number"]
        return {"settings": self._payload(inputs["settings"], "settings"), "initial_design": self._payload(inputs["initial_design"], "initial_design"), "current_state": self._payload(inputs["current_state"], "current_state"), "scene_plan": self._payload(inputs[f"scene_plan.v{volume:02d}.c{chapter:02d}.s{scene:02d}"], "scene_plan"), "volume_number": volume, "chapter_number": chapter, "scene_number": scene}


    def _content_id(self, _root: Path, target: dict[str, Any]) -> str:
        return f"scene-card-v{target['volume_number']:02d}-c{target['chapter_number']:02d}-s{target['scene_number']:02d}-{reserve_counter(self.workspace_root, 'next_scene_card'):06d}"



def create_scene_card_stage_service(workspace_root: Path) -> "SceneCardStageService":
    return SceneCardStageService(workspace_root)
