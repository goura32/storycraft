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


class SeriesPlanStageService:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()

    def run(self, model: Any | None, *, workspace_already_validated: bool = False, updated_at: str | None = None) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        if updated_at is None:
            raise ContractError("series_planの確定時刻が必要です")
        from .run_state import RunStateStore
        state = RunStateStore(self.workspace_root).load()
        if state["current_stage"] != "series_plan" or state["status"] != "running":
            raise ContractError("現在のrun-stateは実行可能なseries_planではありません")
        selection_id = state["current_selection_id"]
        if not isinstance(selection_id, str):
            raise ContractError("series_planには入力selectionが必要です")
        snapshot = SelectionSnapshotStore(self.workspace_root).load(selection_id)
        required_slots = {"request", "settings", "initial_design", "current_state"}
        if not required_slots.issubset(snapshot["slots"]) or "initial_design_adoption" not in snapshot["slots"]:
            raise ContractError("series_plan入力selectionに必須slotがありません")
        bundle = dict(snapshot)
        bundle["slots"] = {slot: snapshot["slots"][slot] for slot in required_slots}
        inputs = resolve_selection(self.workspace_root, bundle)
        self._require_inputs(inputs, state["current_target"])
        context = self._context(inputs, state["current_target"])
        target = dict(state["current_target"])
        spec = CandidateStageSpec(
            stage="series_plan", artifact_kind="series-plan", next_stage="volume_plan",
            next_target={"volume_number": 1}, content_id_factory=self._content_id,
            content_validator=lambda content: self._validate_candidate(
                content, context["request"], context["initial_design"],
            ),
        )
        return CandidateStageRunner(self.workspace_root, spec).run(model, context=context, updated_at=updated_at)

    @staticmethod
    def _validate_candidate(
        content: dict[str, Any], request: dict[str, Any], initial_design: dict[str, Any],
    ) -> None:
        DEFAULT_CONTENT_VALIDATORS["series-plan"](
            content,
            {"request": {"content": request}, "initial_design": {"content": initial_design}},
        )

    @staticmethod
    def _payload(record: dict[str, Any], slot: str) -> dict[str, Any]:
        value = record.get("payload") if slot == "settings" else record.get("content")
        if not isinstance(value, dict):
            raise ContractError(f"series_plan入力{slot}の内容が不正です")
        return value

    def _require_inputs(self, inputs: dict[str, dict[str, Any]], target: dict[str, Any]) -> None:
        required = {"request", "settings", "initial_design", "current_state"}
        if not required.issubset(inputs):
            raise ContractError("series_plan入力selectionに必須slotがありません")


    def _context(self, inputs: dict[str, dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
        return {"request": self._payload(inputs["request"], "request"), "settings": self._payload(inputs["settings"], "settings"), "initial_design": self._payload(inputs["initial_design"], "initial_design"), "current_state": self._payload(inputs["current_state"], "current_state")}


    def _content_id(self, _root: Path, target: dict[str, Any]) -> str:
        return f"series-plan-{reserve_counter(self.workspace_root, 'next_series_plan'):06d}"



def create_series_plan_stage_service(workspace_root: Path) -> "SeriesPlanStageService":
    return SeriesPlanStageService(workspace_root)
