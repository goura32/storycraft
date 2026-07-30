"""Storycraft Version 1 volume_plan Stage実行。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .reviewed_candidate_stage import (
    ReviewedCandidateSpec,
    ReviewedCandidateStageRunner,
    fsync_directory,
    read_json,
    utc_now,
    write_json_new,
)
from .run_state import RunStateStore, validate_run_state
from .error_sanitizer import safe_exception_message
from .series_contracts import (
    ContractError,
    ContractValidator,
    StoryModel,
)
from .stage_transition import advance_run_state
from .workspace import validate_workspace


_SPEC = ReviewedCandidateSpec(
    stage="volume_plan",
    artifact_type="volume_plan",
    review_category="volume_plan_quality",
    next_stage="chapter_plan",
    model_stage="volume_plan",
)


class VolumePlanStageService:
    """巻計画工程：指定巻の構成、起承転結、結末必須事項の履行方針を作る。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        model: StoryModel | None,
        *,
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            from .workspace import validate_workspace
            validate_workspace(self.workspace_root)

        state = self.state_store.load()

        if state["current_stage"] != "volume_plan":
            raise ContractError(
                "現在のrun-stateはvolume_planではありません: "
                f"expected='volume_plan', actual={state['current_stage']!r}"
            )
        if state["status"] != "running":
            raise ContractError(
                "volume_planを実行できるrun statusではありません: "
                f"{state['status']!r}"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるためvolume_planを開始できません"
            )

        if model is None:
            raise ContractError(
                "volume_plan生成にはStoryModelが必要です"
            )

        timestamp = updated_at or utc_now()
        runner = ReviewedCandidateStageRunner(
            self.workspace_root,
            _SPEC,
        )

        # Load context: brief, initial_design, series_plan
        brief = read_json(self.workspace_root / "input/brief.json")
        initial_design = read_json(
            self.workspace_root / "design/initial/v0001/initial-design.json"
        )
        series_plan = read_json(
            self.workspace_root / "design/series-plans/series-plan-000001/series-plan.json"
        )
        
        # Get target volume number
        target = state["current_target"]
        volume_number = target.get("volume_number", 1)
        
        # Extract volume-specific context from series_plan
        volume_summary = None
        for vs in series_plan.get("volume_summaries", []):
            if vs.get("volume_number") == volume_number:
                volume_summary = vs
                break
        
        context = {
            "brief": deepcopy(brief),
            "initial_design": deepcopy(initial_design),
            "series_plan": deepcopy(series_plan),
            "volume_number": volume_number,
            "volume_summary": volume_summary,
        }

        return runner.run(
            model=model,
            context=context,
            validator=lambda c: ContractValidator._validate_volume_plan(
                c, brief, initial_design, series_plan, volume_number, "gen-000001"
            ),
            adopter=lambda c: self._adopt_volume_plan(
                self.workspace_root, c, brief, initial_design, series_plan, volume_number, timestamp
            ),
            next_target={
                "series": state["workspace_id"],
                "basis_generation_id": state["current_generation_id"],
                "volume_number": volume_number,
            },
            next_stage="chapter_plan",
            after_adoption=self._after_volume_plan_adoption,
            updated_at=timestamp,
        )

    def _adopt_volume_plan(
        self,
        workspace_root: Path,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_number: int,
        timestamp: str,
    ) -> None:
        """Volume Plan候補を採用する。"""
        adopted = {
            "schema_version": 1,
            "volume_plan_id": f"volume-plan-v{volume_number:02d}-000001",
            "version": 1,
            "brief_id": "brief-000001",
            "series_plan_id": "series-plan-000001",
            "volume_number": volume_number,
            "created_at": timestamp,
            **candidate,
        }

        # Schema validation
        from .series_contracts import ContractValidator
        brief_obj = read_json(self.workspace_root / "input/brief.json")
        initial_design_obj = read_json(
            self.workspace_root / "design/initial/v0001/initial-design.json"
        )
        series_plan_obj = read_json(
            self.workspace_root / "design/series-plans/series-plan-000001/series-plan.json"
        )
        ContractValidator._validate_volume_plan(
            adopted,
            brief_obj,
            initial_design_obj,
            series_plan_obj,
            volume_number,
            adopted=True,
        )

        # volume-plan.json として保存
        plan_path = workspace_root / "design/volume-plans" / f"volume-plan-v{volume_number:02d}-000001" / "volume-plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_new(plan_path, adopted)
        fsync_directory(plan_path.parent)

    def _after_volume_plan_adoption(
        self,
        candidate: dict[str, Any],
        adopted_state: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        """巻計画採用後の状態更新。"""
        return adopted_state


def create_volume_plan_stage_service(workspace_root: Path) -> "VolumePlanStageService":
    return VolumePlanStageService(workspace_root)