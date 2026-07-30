"""Storycraft Version 1 scene_plan Stage実行。"""
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
    stage="scene_plan",
    artifact_type="scene_plan",
    review_category="scene_plan_quality",
    next_stage="scene_card",
    model_stage="scene_plan",
)


class ScenePlanStageService:
    """場面計画工程：指定巻・章・場面の目的、構成要素、制約を作る。"""

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

        if state["current_stage"] != "scene_plan":
            raise ContractError(
                "現在のrun-stateはscene_planではありません: "
                f"expected='scene_plan', actual={state['current_stage']!r}"
            )
        if state["status"] != "running":
            raise ContractError(
                "scene_planを実行できるrun statusではありません: "
                f"{state['status']!r}"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるためscene_planを開始できません"
            )

        if model is None:
            raise ContractError(
                "scene_plan生成にはStoryModelが必要です"
            )

        timestamp = updated_at or utc_now()
        runner = ReviewedCandidateStageRunner(
            self.workspace_root,
            _SPEC,
        )

        # Load context
        brief = read_json(self.workspace_root / "input/brief.json")
        initial_design = read_json(
            self.workspace_root / "design/initial/v0001/initial-design.json"
        )
        series_plan = read_json(
            self.workspace_root / "design/series-plans/series-plan-000001/series-plan.json"
        )
        target = state["current_target"]
        volume_number = target.get("volume_number", 1)
        chapter_number = target.get("chapter_number", 1)
        scene_number = target.get("scene_number", 1)
        
        volume_plan = read_json(
            self.workspace_root / "design/volume-plans" / f"volume-plan-v{volume_number:02d}-000001" / "volume-plan.json"
        )
        chapter_plan = read_json(
            self.workspace_root / "design/chapter-plans" / f"chapter-plan-v{volume_number:02d}-c{chapter_number:02d}-000001" / "chapter-plan.json"
        )
        
        context = {
            "brief": deepcopy(brief),
            "initial_design": deepcopy(initial_design),
            "series_plan": deepcopy(series_plan),
            "volume_plan": deepcopy(volume_plan),
            "chapter_plan": deepcopy(chapter_plan),
            "volume_number": volume_number,
            "chapter_number": chapter_number,
            "scene_number": scene_number,
        }

        return runner.run(
            model=model,
            context=context,
            validator=lambda c: ContractValidator._validate_scene_plan(
                c, brief, initial_design, series_plan, volume_plan, chapter_plan,
                {},  # current_generation
                volume_number, chapter_number, scene_number, "gen-000001"
            ),
            adopter=lambda c: self._adopt_scene_plan(
                self.workspace_root, c, brief, initial_design, series_plan, volume_plan, chapter_plan,
                volume_number, chapter_number, scene_number, timestamp
            ),
            next_target={
                "series": state["workspace_id"],
                "basis_generation_id": state["current_generation_id"],
                "volume_number": volume_number,
                "chapter_number": chapter_number,
                "scene_number": scene_number,
            },
            next_stage="scene_card",
            after_adoption=self._after_scene_plan_adoption,
            updated_at=timestamp,
        )

    def _adopt_scene_plan(
        self,
        workspace_root: Path,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        chapter_plan: dict[str, Any],
        volume_number: int,
        chapter_number: int,
        scene_number: int,
        timestamp: str,
    ) -> None:
        """Scene Plan候補を採用する。"""
        adopted = {
            "schema_version": 1,
            "scene_plan_id": f"scene-plan-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001",
            "version": 1,
            "brief_id": "brief-000001",
            "series_plan_id": "series-plan-000001",
            "volume_plan_id": f"volume-plan-v{volume_number:02d}-000001",
            "chapter_plan_id": f"chapter-plan-v{volume_number:02d}-c{chapter_number:02d}-000001",
            "volume_number": volume_number,
            "chapter_number": chapter_number,
            "scene_number": scene_number,
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
        volume_plan_obj = read_json(
            self.workspace_root / "design/volume-plans" / f"volume-plan-v{volume_number:02d}-000001" / "volume-plan.json"
        )
        chapter_plan_obj = read_json(
            self.workspace_root / "design/chapter-plans" / f"chapter-plan-v{volume_number:02d}-c{chapter_number:02d}-000001" / "chapter-plan.json"
        )
        ContractValidator._validate_scene_plan(
                            adopted,
                            brief_obj,
                            initial_design_obj,
                            series_plan_obj,
                            volume_plan_obj,
                            chapter_plan_obj,
                            {},  # current_generation
                            volume_number,
                            chapter_number,
                            scene_number,
                            "gen-000001",
                            adopted=True,
                        )

        # scene-plan.json として保存
        plan_path = workspace_root / "design/scene-plans" / f"scene-plan-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001" / "scene-plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_new(plan_path, adopted)
        fsync_directory(plan_path.parent)

    def _after_scene_plan_adoption(
        self,
        candidate: dict[str, Any],
        adopted_state: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        """場面計画採用後の状態更新。"""
        return adopted_state


def create_scene_plan_stage_service(workspace_root: Path) -> "ScenePlanStageService":
    return ScenePlanStageService(workspace_root)