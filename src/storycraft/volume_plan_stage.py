"""Selection-based planning-stage adapter."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_ids import reserve_counter
from .candidate_stage import CandidateStageRunner, CandidateStageSpec
from .artifact_registry import artifact_spec
from .selection_authority import DEFAULT_CONTENT_VALIDATORS, resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError
from .workspace import validate_workspace


class VolumePlanStageService:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()

    def run(self, model: Any | None, *, workspace_already_validated: bool = False, updated_at: str | None = None) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace(self.workspace_root)
        if updated_at is None:
            raise ContractError("volume_planの確定時刻が必要です")
        from .run_state import RunStateStore
        state = RunStateStore(self.workspace_root).load()
        if state["current_stage"] != "volume_plan" or state["status"] != "running":
            raise ContractError("現在のrun-stateは実行可能なvolume_planではありません")
        selection_id = state["current_selection_id"]
        if not isinstance(selection_id, str):
            raise ContractError("volume_planには入力selectionが必要です")
        snapshot = SelectionSnapshotStore(self.workspace_root).load(selection_id)
        volume = state["current_target"].get("volume_number")
        if not isinstance(volume, int) or isinstance(volume, bool) or volume < 1:
            raise ContractError("volume_planの対象巻が不正です")
        published_volumes = state["published_volumes"]
        if not isinstance(published_volumes, list) or len(published_volumes) != volume - 1 or [
            entry.get("volume_number") if isinstance(entry, dict) else None
            for entry in published_volumes
        ] != list(range(1, volume)):
            raise ContractError("volume_planの対象巻は公開済み巻の次でなければなりません")
        required_slots = {"settings", "current_state", "series_plan"}
        prior_slot = f"volume_plan.v{volume - 1:02d}" if volume > 1 else None
        current_slot = f"volume_plan.v{volume:02d}"
        if current_slot in snapshot["slots"]:
            raise ContractError("volume_planの対象巻は既にselectionへ存在します")
        if prior_slot is not None:
            required_slots.add(prior_slot)
        if not required_slots.issubset(snapshot["slots"]):
            raise ContractError("volume_plan入力selectionに必須slotがありません")
        resolved_selection = resolve_selection(self.workspace_root, snapshot)
        inputs = {slot: resolved_selection[slot] for slot in required_slots}
        if prior_slot is not None:
            prior = inputs.get(prior_slot)
            prior_id = prior.get("artifact_id") if isinstance(prior, dict) else None
            if not isinstance(prior, dict) or not isinstance(prior_id, str):
                raise ContractError("第2巻以降volume_planの前巻計画が不正です")
            try:
                prior_match = artifact_spec("volume-plan").match_id(prior_id)
            except ContractError as exc:
                raise ContractError("第2巻以降volume_planの前巻計画IDが不正です") from exc
            if int(prior_match.group("volume")) != volume - 1:
                raise ContractError("volume_planの前巻計画座標が対象巻と一致しません")
            inputs["prior_volume_plan"] = prior
        self._require_inputs(inputs, state["current_target"])
        context = self._context(inputs, state["current_target"])
        target = dict(state["current_target"])
        spec = CandidateStageSpec(
            stage="volume_plan", artifact_kind="volume-plan", next_stage="chapter_plan",
            next_target={"volume_number": target["volume_number"], "chapter_number": 1}, content_id_factory=self._content_id,
            content_validator=lambda content: DEFAULT_CONTENT_VALIDATORS["volume-plan"](
                content,
                {**inputs, "__current_slot__": f"volume_plan.v{target['volume_number']:02d}", "__strict_parent__": True},
            ),
        )
        return CandidateStageRunner(self.workspace_root, spec).run(model, context=context, updated_at=updated_at)

    @staticmethod
    def _payload(record: dict[str, Any], slot: str) -> dict[str, Any]:
        value = record.get("payload") if slot == "settings" else record.get("content")
        if not isinstance(value, dict):
            raise ContractError(f"volume_plan入力{slot}の内容が不正です")
        return value

    def _require_inputs(self, inputs: dict[str, dict[str, Any]], target: dict[str, Any]) -> None:
        volume = target.get("volume_number")
        required = {"settings", "current_state", "series_plan"}
        if not isinstance(volume, int) or isinstance(volume, bool) or volume < 1 or not required.issubset(inputs):
            raise ContractError("volume_plan入力selectionまたは座標が不正です")
        if volume == 1 and "prior_volume_plan" in inputs:
            raise ContractError("第1巻volume_planにprior_volume_planは許可されません")
        if volume > 1 and "prior_volume_plan" not in inputs:
            raise ContractError("第2巻以降volume_planにprior_volume_planがありません")


    def _context(self, inputs: dict[str, dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
        context = {"settings": self._payload(inputs["settings"], "settings"), "current_state": self._payload(inputs["current_state"], "current_state"), "series_plan": self._payload(inputs["series_plan"], "series_plan"), "volume_number": target["volume_number"]}
        if "prior_volume_plan" in inputs:
            context["prior_volume_plan"] = self._payload(inputs["prior_volume_plan"], "prior_volume_plan")
        return context


    def _content_id(self, _root: Path, target: dict[str, Any]) -> str:
        return f"volume-plan-v{target['volume_number']:02d}-{reserve_counter(self.workspace_root, 'next_volume_plan'):06d}"



def create_volume_plan_stage_service(workspace_root: Path) -> "VolumePlanStageService":
    return VolumePlanStageService(workspace_root)
