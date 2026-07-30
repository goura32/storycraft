"""Storycraft Version 1 series_plan Stage実行。"""
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


_SPEC = {
    "stage": "series_plan",
    "artifact_type": "series_plan",
    "review_category": "series_plan_quality",
    "next_stage": "volume_plan",
    "model_stage": "series_plan",
}


class SeriesPlanStageService:
    """シリーズ計画工程：全巻の役割、巻数、結末必須事項の進行・解決予定を作る。"""

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

        if state["current_stage"] != "series_plan":
            raise ContractError(
                "現在のrun-stateはseries_planではありません: "
                f"expected='series_plan', actual={state['current_stage']!r}"
            )
        if state["status"] != "running":
            raise ContractError(
                "series_planを実行できるrun statusではありません: "
                f"{state['status']!r}"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるためseries_planを開始できません"
            )

        if model is None:
            raise ContractError(
                "series_plan生成にはStoryModelが必要です"
            )

        timestamp = updated_at or utc_now()
        brief = read_json(self.workspace_root / "input/brief.json")
        initial_design = read_json(
            self.workspace_root / "design/initial/v0001/initial-design.json"
        )
        context = {
            "brief": deepcopy(brief),
            "initial_design": deepcopy(initial_design),
        }

        runner = ReviewedCandidateStageRunner(
            self.workspace_root,
            _SPEC,
        )

        return runner.run(
            model=model,
            context=context,
            validator=lambda c: ContractValidator._validate_series_plan(c, brief, initial_design, "gen-000001"),
            adopter=lambda c: self._adopt_series_plan(
                self.workspace_root, c, brief, timestamp
            ),
            next_target={
                "series": state["workspace_id"],
                "basis_generation_id": "gen-000001",
                "volume_number": 1,
            },
            next_stage="volume_plan",
            after_adoption=self._after_series_plan_adoption,
            updated_at=timestamp,
        )

    def _adopt_series_plan(
        self,
        workspace_root: Path,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        timestamp: str,
    ) -> None:
        """Series Plan候補を採用する。"""
        from .reviewed_candidate_stage import (
            fsync_directory,
            read_json,
            write_json_new,
        )

        adopted = {
            "schema_version": 1,
            "series_plan_id": "series-plan-000001",
            "version": 1,
            "brief_id": "brief-000001",
            "created_at": timestamp,
            **candidate,
        }

        # Schema validation
        from .series_contracts import ContractValidator
        brief_obj = read_json(self.workspace_root / "input/brief.json")
        initial_design = read_json(
            self.workspace_root / "design/initial/v0001/initial-design.json"
        )
        ContractValidator._validate_series_plan(
            adopted,
            brief_obj,
            read_json(self.workspace_root / "design/initial/v0001/initial-design.json"),
            "gen-000001",
            adopted=True,
        )

        # series-plan.json として保存
        plan_path = self.workspace_root / "design/series-plans" / "series-plan-000001" / "series-plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_new(plan_path, adopted)
        fsync_directory(plan_path.parent)

    def _after_series_plan_adoption(
        self,
        candidate: dict[str, Any],
        adopted_state: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        """シリーズ計画採用後の状態更新。"""
        return adopted_state


def create_series_plan_stage_service(workspace_root: Path) -> "SeriesPlanStageService":
    return SeriesPlanStageService(workspace_root)