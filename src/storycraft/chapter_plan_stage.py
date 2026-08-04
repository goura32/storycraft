"""Selection-based planning-stage adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .candidate_stage import CandidateStageRunner, CandidateStageSpec
from .selection_authority import DEFAULT_CONTENT_VALIDATORS, resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError
from .workspace import validate_workspace


class ChapterPlanStageService:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()

    def run(self, model: Any | None, *, workspace_already_validated: bool = False, updated_at: str | None = None) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        if updated_at is None:
            raise ContractError("chapter_planの確定時刻が必要です")
        from .run_state import RunStateStore
        state = RunStateStore(self.workspace_root).load()
        if state["current_stage"] != "chapter_plan" or state["status"] != "running":
            raise ContractError("現在のrun-stateは実行可能なchapter_planではありません")
        selection_id = state["current_selection_id"]
        if not isinstance(selection_id, str):
            raise ContractError("chapter_planには入力selectionが必要です")
        snapshot = SelectionSnapshotStore(self.workspace_root).load(selection_id)
        volume = state["current_target"].get("volume_number")
        required_slots = {"settings", "initial_design", "current_state", "series_plan", f"volume_plan.v{volume:02d}"}
        if not required_slots.issubset(snapshot["slots"]):
            raise ContractError("chapter_plan入力selectionに必須slotがありません")
        bundle = dict(snapshot)
        bundle["slots"] = {slot: snapshot["slots"][slot] for slot in required_slots}
        inputs = resolve_selection(self.workspace_root, bundle)
        self._require_inputs(inputs, state["current_target"])
        context = self._context(inputs, state["current_target"])
        target = dict(state["current_target"])
        spec = CandidateStageSpec(
            stage="chapter_plan", artifact_kind="chapter-plan", next_stage="scene_plan",
            next_target={"volume_number": target["volume_number"], "chapter_number": target["chapter_number"], "scene_number": 1}, content_id_factory=self._content_id,
            content_validator=lambda content: DEFAULT_CONTENT_VALIDATORS["chapter-plan"](
                content,
                {**inputs, "__current_slot__": f"chapter_plan.v{target['volume_number']:02d}.c{target['chapter_number']:02d}", "__strict_parent__": True},
            ),
        )
        return CandidateStageRunner(self.workspace_root, spec).run(model, context=context, updated_at=updated_at)

    @staticmethod
    def _payload(record: dict[str, Any], slot: str) -> dict[str, Any]:
        value = record.get("payload") if slot == "settings" else record.get("content")
        if not isinstance(value, dict):
            raise ContractError(f"chapter_plan入力{slot}の内容が不正です")
        return value

    def _require_inputs(self, inputs: dict[str, dict[str, Any]], target: dict[str, Any]) -> None:
        required = {"settings", "initial_design", "current_state", "series_plan"}
        volume, chapter = target.get("volume_number"), target.get("chapter_number")
        slot = f"volume_plan.v{volume:02d}" if isinstance(volume, int) and not isinstance(volume, bool) else ""
        if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 1 for value in (volume, chapter)) or not required.issubset(inputs) or slot not in inputs:
            raise ContractError("chapter_plan入力selectionまたは座標が不正です")


    def _context(self, inputs: dict[str, dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
        volume = target["volume_number"]
        return {"settings": self._payload(inputs["settings"], "settings"), "initial_design": self._payload(inputs["initial_design"], "initial_design"), "current_state": self._payload(inputs["current_state"], "current_state"), "series_plan": self._payload(inputs["series_plan"], "series_plan"), "volume_plan": self._payload(inputs[f"volume_plan.v{volume:02d}"], "volume_plan"), "volume_number": volume, "chapter_number": target["chapter_number"]}


    def _content_id(self, _root: Path, target: dict[str, Any]) -> str:
        return f"chapter-plan-v{target['volume_number']:02d}-c{target['chapter_number']:02d}-{reserve_counter(self.workspace_root, 'next_chapter_plan'):06d}"



def create_chapter_plan_stage_service(workspace_root: Path) -> "ChapterPlanStageService":
    return ChapterPlanStageService(workspace_root)
