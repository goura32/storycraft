"""Storycraft Version 1 scene_commit Stage実行。"""
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
from .scene_generation import (
    build_accepted_scene_commit,
    build_scene_commit_candidate,
    validate_accepted_scene_commit,
    validate_scene_commit_candidate,
)


_SPEC = ReviewedCandidateSpec(
    stage="scene_commit",
    artifact_type="scene_commit",
    review_category="scene_commit_accuracy",
    next_stage="volume_publication",  # This is the final stage before publication
    model_stage="scene_commit",
)


class SceneCommitStageService:
    """場面確定工程：採用済みScene Prose、Scene Card、Continuity Update、基準Generationから、不変Sceneと後続Generationを決定的に構築する。
    
    この工程はLLMを呼ばず、コードのみで実行される。
    """

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        model: StoryModel | None = None,  # scene_commit doesn't use LLM
        *,
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            from .workspace import validate_workspace
            validate_workspace(self.workspace_root)

        state = self.state_store.load()

        if state["current_stage"] != "scene_commit":
            raise ContractError(
                "現在のrun-stateはscene_commitではありません: "
                f"expected='scene_commit', actual={state['current_stage']!r}"
            )
        if state["status"] != "running":
            raise ContractError(
                "scene_commitを実行できるrun statusではありません: "
                f"{state['status']!r}"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるためscene_commitを開始できません"
            )

        timestamp = updated_at or utc_now()
        
        # Load all required context
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
        scene_plan = read_json(
            self.workspace_root / "design/scene-plans" / f"scene-plan-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001" / "scene-plan.json"
        )
        scene_card = read_json(
            self.workspace_root / "design/scene-cards" / f"scene-card-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001" / "scene-card.json"
        )
        scene_prose = read_json(
            self.workspace_root / "scenes" / f"scene-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001" / "scene-prose.json"
        )
        continuity_update = read_json(
            self.workspace_root / "scenes" / f"scene-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001" / "continuity-update.json"
        )
        current_generation = read_json(
            self.workspace_root / "generations" / state["current_generation_id"] / "canon.json"
        )
        
        # Build scene commit candidate deterministically
        candidate = build_scene_commit_candidate(
            scene_prose=scene_prose,
            scene_card=scene_card,
            continuity_update=continuity_update,
            basis_generation=current_generation,
            volume_number=volume_number,
            chapter_number=chapter_number,
            scene_number=scene_number,
            timestamp=timestamp,
        )
        
        # Validate candidate
        ContractValidator._validate_scene_commit_candidate(
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            scene_card,
            scene_prose,
            continuity_update,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
        )
        
        # Adopt the candidate
        adopted_scene_commit = self._adopt_scene_commit(
            self.workspace_root,
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            scene_card,
            scene_prose,
            continuity_update,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            timestamp,
        )
        
        # Advance to next stage or complete
        next_target = {
            "series": state["workspace_id"],
            "basis_generation_id": adopted_scene_commit["generation_id"],
        }
        
        # Check if this was the last scene of the last chapter of the last volume
        # For now, advance to volume_publication
        next_stage = "volume_publication"
        
        advanced = advance_run_state(
            state,
            next_stage=next_stage,
            next_target=next_target,
            updated_at=timestamp,
        )
        self.state_store.save(advanced)
        return advanced

    def _adopt_scene_commit(
        self,
        workspace_root: Path,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        chapter_plan: dict[str, Any],
        scene_plan: dict[str, Any],
        scene_card: dict[str, Any],
        scene_prose: dict[str, Any],
        continuity_update: dict[str, Any],
        current_generation: dict[str, Any],
        volume_number: int,
        chapter_number: int,
        scene_number: int,
        timestamp: str,
    ) -> dict[str, Any]:
        """Scene Commitを採用し、Sceneと次のGenerationを決定的に構築する。"""
        
        # Build accepted scene commit
        accepted = build_accepted_scene_commit(
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            scene_card,
            scene_prose,
            continuity_update,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            timestamp,
        )
        
        # Validate
        validate_accepted_scene_commit(
            accepted,
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            scene_card,
            scene_prose,
            continuity_update,
            current_generation,
        )
        
        # Save scene-commit.json
        scene_commit_path = workspace_root / "scenes" / f"scene-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001" / "scene-commit.json"
        scene_commit_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_new(scene_commit_path, accepted)
        fsync_directory(scene_commit_path.parent)
        
        # Build and save next generation
        gen_id = f"gen-{int(current_generation['generation_id'].split('-')[1]) + 1:06d}"
        generation_files = build_accepted_scene_commit(
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            scene_card,
            scene_prose,
            continuity_update,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            timestamp,
        )
        
        gen_path = workspace_root / "generations" / gen_id
        gen_path.mkdir(parents=True, exist_ok=True)
        for name, value in generation_files.items():
            write_json_new(gen_path / name, value)
        fsync_directory(gen_path)
        
        return {"generation_id": gen_id}


def create_scene_commit_stage_service(workspace_root: Path) -> "SceneCommitStageService":
    return SceneCommitStageService(workspace_root)