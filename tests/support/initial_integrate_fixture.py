"""Initial Integrate直前・完了workspaceの純粋fixture builder。"""
from __future__ import annotations

from pathlib import Path

from storycraft.initial_characters_stage import (
    InitialCharactersStageService,
)
from storycraft.initial_concept_stage import (
    InitialConceptStageService,
)
from storycraft.initial_ending_stage import (
    InitialEndingStageService,
)
from storycraft.initial_integrate_stage import (
    InitialIntegrateStageService,
)
from storycraft.initial_knowledge_stage import (
    InitialKnowledgeStageService,
)
from storycraft.initial_relationships_stage import (
    InitialRelationshipsStageService,
)
from storycraft.initial_threads_stage import (
    InitialThreadsStageService,
)
from storycraft.initial_world_stage import (
    InitialWorldStageService,
)
from storycraft.input_stage import InputStageService
from storycraft.workspace import (
    create_workspace_from_brief,
)

from tests.test_initial_ending_schema_v1 import (
    ending_candidate,
)
from tests.test_initial_integrate_schema_v1 import (
    integrated_candidate,
)
from tests.test_initial_knowledge_stage_v1 import (
    knowledge_candidate,
)
from tests.test_initial_threads_schema_v1 import (
    thread_candidate,
)
from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    NeverCalledModel,
    character_candidate,
    load_json,
    relationship_candidate,
    world_candidate,
)


CREATED_AT = "2026-07-23T10:00:00Z"
INPUT_AT = "2026-07-23T10:01:00Z"
CONCEPT_AT = "2026-07-23T10:02:00Z"
CHARACTERS_AT = "2026-07-23T10:03:00Z"
RELATIONSHIPS_AT = "2026-07-23T10:04:00Z"
WORLD_AT = "2026-07-23T10:05:00Z"
KNOWLEDGE_AT = "2026-07-23T10:06:00Z"
THREADS_AT = "2026-07-23T10:07:00Z"
ENDING_AT = "2026-07-23T10:08:00Z"
INTEGRATE_AT = "2026-07-23T10:09:00Z"


def build_pre_integrate_workspace(
    temporary: str,
) -> tuple[Path, dict]:
    """Initial Ending採用後のworkspaceを構築する。"""
    brief = load_json(
        "tests/fixtures/brief/valid.json"
    )
    config = load_json(
        "tests/fixtures/workspace/config.json"
    )
    concept = load_json(
        "tests/fixtures/initial-design/valid.json"
    )["concept"]

    workspace = Path(temporary) / "novel"

    create_workspace_from_brief(
        workspace,
        workspace_id="ws-test-0001",
        brief=brief,
        config=config,
        created_at=CREATED_AT,
    )

    InputStageService(workspace).run(
        NeverCalledModel(),
        updated_at=INPUT_AT,
    )
    InitialConceptStageService(workspace).run(
        AcceptingModel(concept),
        updated_at=CONCEPT_AT,
    )
    InitialCharactersStageService(workspace).run(
        AcceptingModel(character_candidate()),
        updated_at=CHARACTERS_AT,
    )
    InitialRelationshipsStageService(workspace).run(
        AcceptingModel(relationship_candidate()),
        updated_at=RELATIONSHIPS_AT,
    )
    InitialWorldStageService(workspace).run(
        AcceptingModel(world_candidate()),
        updated_at=WORLD_AT,
    )
    InitialKnowledgeStageService(workspace).run(
        AcceptingModel(knowledge_candidate()),
        updated_at=KNOWLEDGE_AT,
    )
    InitialThreadsStageService(workspace).run(
        AcceptingModel(thread_candidate()),
        updated_at=THREADS_AT,
    )
    InitialEndingStageService(workspace).run(
        AcceptingModel(ending_candidate()),
        updated_at=ENDING_AT,
    )

    return workspace, integrated_candidate()


def build_integrated_workspace(
    temporary: str,
) -> tuple[Path, dict]:
    """Initial Integrate採用後のworkspaceを構築する。"""
    workspace, integrated = (
        build_pre_integrate_workspace(temporary)
    )

    InitialIntegrateStageService(workspace).run(
        AcceptingModel(integrated),
        updated_at=INTEGRATE_AT,
    )

    return workspace, integrated
