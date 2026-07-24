"""Storycraft V1の一工程実行境界。"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .chapter_plan_stage import ChapterPlanStageService
from .initial_accept_stage import InitialAcceptStageService
from .initial_characters_stage import (
    InitialCharactersStageService,
)
from .initial_concept_stage import InitialConceptStageService
from .initial_ending_stage import InitialEndingStageService
from .initial_integrate_stage import InitialIntegrateStageService
from .initial_knowledge_stage import InitialKnowledgeStageService
from .initial_relationships_stage import (
    InitialRelationshipsStageService,
)
from .initial_threads_stage import InitialThreadsStageService
from .initial_world_stage import InitialWorldStageService
from .input_stage import InputStageService
from .run_state import RunStateStore
from .scene_card_stage import SceneCardStageService
from .scene_continuity_stage import (
    SceneContinuityStageService,
)
from .scene_plan_stage import ScenePlanStageService
from .scene_prose_stage import SceneProseStageService
from .series_contracts import ContractError, StoryModel
from .series_plan_stage import SeriesPlanStageService
from .stages import Stage
from .volume_plan_stage import VolumePlanStageService
from .workspace import validate_workspace_layout
from .workspace_lock import workspace_lock


ModelFactory = Callable[[], StoryModel]


_MODEL_STAGE_SERVICES = {
    Stage.INITIAL_CONCEPT: InitialConceptStageService,
    Stage.INITIAL_CHARACTERS: InitialCharactersStageService,
    Stage.INITIAL_RELATIONSHIPS: InitialRelationshipsStageService,
    Stage.INITIAL_WORLD: InitialWorldStageService,
    Stage.INITIAL_KNOWLEDGE: InitialKnowledgeStageService,
    Stage.INITIAL_THREADS: InitialThreadsStageService,
    Stage.INITIAL_ENDING: InitialEndingStageService,
    Stage.INITIAL_INTEGRATE: InitialIntegrateStageService,
    Stage.SERIES_PLAN: SeriesPlanStageService,
    Stage.VOLUME_PLAN: VolumePlanStageService,
    Stage.CHAPTER_PLAN: ChapterPlanStageService,
    Stage.SCENE_PLAN: ScenePlanStageService,
    Stage.SCENE_CARD: SceneCardStageService,
    Stage.SCENE_PROSE: SceneProseStageService,
    Stage.SCENE_CONTINUITY: SceneContinuityStageService,
}


class V1WorkflowService:
    """V1 workspaceをLockして現在Stageを一回だけ実行する。"""

    def __init__(
        self,
        workspace_root: Path,
        *,
        model_factory: ModelFactory | None = None,
    ) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)
        self.model_factory = model_factory

    def step(
        self,
        *,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        """現在Stageを一工程だけ進める。"""
        with workspace_lock(self.workspace_root):
            validate_workspace_layout(self.workspace_root)
            state = self.state_store.load()

            if state["pending_commit"] is not None:
                self._recover_pending_commit(state)
                validate_workspace_layout(
                    self.workspace_root
                )
                state = self.state_store.load()

            return self._execute_stage(
                state,
                updated_at=updated_at,
            )

    def _execute_stage(
        self,
        state: dict[str, Any],
        *,
        updated_at: str | None,
    ) -> dict[str, Any]:
        stage = Stage(state["current_stage"])

        if stage is Stage.INPUT:
            service = InputStageService(self.workspace_root)

            if self._input_requires_model():
                return service.run(
                    self._create_model(),
                    updated_at=updated_at,
                )

            return service.run(updated_at=updated_at)

        if stage is Stage.INITIAL_ACCEPT:
            return InitialAcceptStageService(
                self.workspace_root
            ).run(
                updated_at=updated_at,
            )

        service_type = _MODEL_STAGE_SERVICES.get(stage)

        if service_type is None:
            raise ContractError(
                "V1 Stageはまだ実装されていません: "
                f"{stage.value}"
            )

        return service_type(self.workspace_root).run(
            self._create_model(),
            updated_at=updated_at,
        )

    def _input_requires_model(self) -> bool:
        source_path = (
            self.workspace_root / "input/source.json"
        )

        try:
            source = json.loads(
                source_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(
                "input/source.jsonを読み込めません"
            ) from exc

        source_type = source.get("source_type")

        if source_type == "brief":
            return False
        if source_type == "keywords":
            return True

        raise ContractError(
            "input/source.jsonのsource_typeが不正です"
        )

    def _create_model(self) -> StoryModel:
        if self.model_factory is None:
            raise ContractError(
                "現在StageにはLLM Modelが必要です"
            )

        return self.model_factory()

    def _recover_pending_commit(
        self,
        state: dict[str, Any],
    ) -> None:
        pending = state["pending_commit"]
        assert isinstance(pending, dict)

        raise ContractError(
            "pending_commit Recoveryは未実装です: "
            f"kind={pending.get('kind')!r} "
            f"phase={pending.get('phase')!r}"
        )
