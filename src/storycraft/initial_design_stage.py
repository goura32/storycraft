"""Storycraft Version 1 initial_design Stage実行。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
from typing import Any

from .reviewed_candidate_stage import (
    ReviewedCandidateSpec,
    ReviewedCandidateStageRunner,
    fsync_directory,
    normalize_review,
    read_json,
    reserve_identifier,
    revision_limit_from_config,
    stop_state,
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
from .initial_generation import (
    build_accepted_initial_design,
    build_initial_generation,
    validate_accepted_initial_design,
    validate_initial_generation,
)


def create_initial_design_stage_service(workspace_root: Path) -> "InitialDesignStageService":
    return InitialDesignStageService(workspace_root)


_SPEC = ReviewedCandidateSpec(
    stage="initial_design",
    artifact_type="initial_design",
    review_category="initial_design_quality",
    next_stage="series_plan",
    model_stage="initial_design",
)


class InitialDesignStageService:
    """初期設計工程：作品の構造と意図を一つの候補として生成、確認、必要なら修正し、採用する。"""

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

        if state["current_stage"] != "initial_design":
            raise ContractError(
                "現在のrun-stateはinitial_designではありません: "
                f"expected='initial_design', actual={state['current_stage']!r}"
            )
        if state["status"] != "running":
            raise ContractError(
                "initial_designを実行できるrun statusではありません: "
                f"{state['status']!r}"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるためinitial_designを開始できません"
            )

        if model is None:
            raise ContractError(
                "initial_design生成にはStoryModelが必要です"
            )

        timestamp = updated_at or utc_now()
        brief = read_json(self.workspace_root / "input/brief.json")
        context = {"brief": deepcopy(brief)}

        runner = ReviewedCandidateStageRunner(
            self.workspace_root,
            _SPEC,
        )

        return runner.run(
            model=model,
            context=context,
            validator=lambda c: ContractValidator._validate_initial_design_candidate(c, brief),
            adopter=lambda c: self._adopt_initial_design(
                self.workspace_root, c, brief, timestamp
            ),
            next_target={
                "series": state["workspace_id"],
                "basis_generation_id": "gen-000001",
            },
            next_stage="series_plan",
            after_adoption=self._after_initial_design_adoption,
            updated_at=timestamp,
        )

    def _adopt_initial_design(
        self,
        workspace_root: Path,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        timestamp: str,
    ) -> None:
        """Initial Design候補を採用し、Initial Generationを作成する。"""
        brief_obj = read_json(workspace_root / "input/brief.json")
        brief_id = brief_obj.get("brief_id", "brief-000001")

        adopted = build_accepted_initial_design(
            candidate,
            brief,
            created_at=timestamp,
        )
        validate_accepted_initial_design(adopted, candidate, brief)

        # initial-design.json として保存
        design_path = workspace_root / "design/initial/v0001/initial-design.json"
        design_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_new(design_path, adopted)
        fsync_directory(design_path.parent)

        # Initial Generation を生成・保存
        gen_id = "gen-000001"
        generation_files = build_initial_generation(
            adopted,
            generation_id=gen_id,
            created_at=timestamp,
        )
        gen_path = workspace_root / "generations" / gen_id
        if not gen_path.exists():
            gen_path.mkdir(parents=True)
        for name, value in generation_files.items():
            write_json_new(gen_path / name, value)
        fsync_directory(gen_path)

    def _after_initial_design_adoption(
        self,
        candidate: dict[str, Any],
        adopted_state: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        """初期設計採用後の状態更新。"""
        # Generation ID を取得
        gen_id = "gen-000001"

        adopted_state["current_generation_id"] = gen_id
        return adopted_state


def create_initial_design_stage_service(workspace_root: Path) -> "InitialDesignStageService":
    return InitialDesignStageService(workspace_root)