"""Storycraft Version 1 initial_integrate Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

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
from storycraft.series_contracts import ContractError
from storycraft.workspace import (
    create_workspace_from_brief,
    validate_workspace_layout,
)

from tests.test_initial_ending_schema_v1 import (
    ending_candidate,
)
from tests.test_initial_ending_stage_v1 import (
    NeverAcceptingModel,
    RevisingModel,
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
    load_json_from,
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


class InitialIntegrateStageV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.config = load_json(
            "tests/fixtures/workspace/config.json"
        )
        self.concept = load_json(
            "tests/fixtures/initial-design/valid.json"
        )["concept"]
        self.characters_candidate = character_candidate()
        self.relationships_candidate = (
            relationship_candidate()
        )
        self.world_candidate = world_candidate()
        self.knowledge_candidate = knowledge_candidate()
        self.threads_candidate = thread_candidate()
        self.ending_candidate = ending_candidate()
        self.integrated = integrated_candidate()

    def create_workspace(self, temporary: str) -> Path:
        workspace = Path(temporary) / "novel"
        create_workspace_from_brief(
            workspace,
            workspace_id="ws-test-0001",
            brief=self.brief,
            config=self.config,
            created_at=CREATED_AT,
        )
        InputStageService(workspace).run(
            NeverCalledModel(),
            updated_at=INPUT_AT,
        )
        InitialConceptStageService(workspace).run(
            AcceptingModel(self.concept),
            updated_at=CONCEPT_AT,
        )
        InitialCharactersStageService(workspace).run(
            AcceptingModel(self.characters_candidate),
            updated_at=CHARACTERS_AT,
        )
        InitialRelationshipsStageService(workspace).run(
            AcceptingModel(self.relationships_candidate),
            updated_at=RELATIONSHIPS_AT,
        )
        InitialWorldStageService(workspace).run(
            AcceptingModel(self.world_candidate),
            updated_at=WORLD_AT,
        )
        InitialKnowledgeStageService(workspace).run(
            AcceptingModel(self.knowledge_candidate),
            updated_at=KNOWLEDGE_AT,
        )
        InitialThreadsStageService(workspace).run(
            AcceptingModel(self.threads_candidate),
            updated_at=THREADS_AT,
        )
        InitialEndingStageService(workspace).run(
            AcceptingModel(self.ending_candidate),
            updated_at=ENDING_AT,
        )
        return workspace

    def test_generate_review_adopt_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            root = workspace / "design/initial/v0001"
            brief = load_json_from(
                workspace / "input/brief.json"
            )
            expected_context = {
                "brief": brief,
                "concept": load_json_from(
                    root / "concept.json"
                ),
                "characters": load_json_from(
                    root / "characters.json"
                ),
                "relationships": load_json_from(
                    root / "relationships.json"
                ),
                "world": load_json_from(
                    root / "world.json"
                ),
                "knowledge": load_json_from(
                    root / "knowledge.json"
                ),
                "threads": load_json_from(
                    root / "threads.json"
                ),
                "ending": load_json_from(
                    root / "ending.json"
                ),
            }
            model = AcceptingModel(self.integrated)

            state = InitialIntegrateStageService(
                workspace
            ).run(
                model,
                updated_at=INTEGRATE_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "initial_integrate"),
                    ("critique", "initial_integrate"),
                ],
            )
            self.assertEqual(
                model.contexts,
                [expected_context, expected_context],
            )
            self.assertEqual(
                state["current_stage"],
                "initial_accept",
            )
            self.assertIsNone(state["active_candidate"])
            self.assertEqual(
                load_json_from(root / "integrated.json"),
                self.integrated,
            )
            validate_workspace_layout(workspace)

            candidate = load_json_from(
                workspace
                / "runtime/candidates/initial_integrate"
                / "candidate-000008/v0001/candidate.json"
            )
            self.assertNotIn(
                "design_id",
                candidate["content"],
            )
            self.assertNotIn(
                "created_at",
                candidate["content"],
            )

    def test_revision_creates_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            revised = deepcopy(self.integrated)
            revised["ending"]["desired_effect"] = (
                "痛みを受け止めた姉妹が、町で新しい"
                "関係を始める希望を残す。"
            )

            state = InitialIntegrateStageService(
                workspace
            ).run(
                RevisingModel(self.integrated, revised),
                updated_at=INTEGRATE_AT,
            )

            root = (
                workspace
                / "runtime/candidates/initial_integrate"
                / "candidate-000008"
            )
            self.assertEqual(
                load_json_from(
                    root / "v0001/status.json"
                )["status"],
                "needs_revision",
            )
            self.assertEqual(
                load_json_from(
                    root / "v0002/status.json"
                )["status"],
                "accepted",
            )
            self.assertTrue(
                (root / "v0002/revision.json").is_file()
            )
            self.assertEqual(
                state["current_stage"],
                "initial_accept",
            )

    def test_revision_limit_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)

            state = InitialIntegrateStageService(
                workspace
            ).run(
                NeverAcceptingModel(self.integrated),
                updated_at=INTEGRATE_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "revision_limit",
            )
            self.assertEqual(
                state["active_candidate"],
                {
                    "kind": "initial_integrate",
                    "candidate_id": "candidate-000008",
                    "version": 3,
                },
            )
            self.assertFalse(
                (
                    workspace
                    / "design/initial/v0001/integrated.json"
                ).exists()
            )

    def test_invalid_generation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            invalid = deepcopy(self.integrated)
            invalid["long_term_arcs"].reverse()

            state = InitialIntegrateStageService(
                workspace
            ).run(
                AcceptingModel(invalid),
                updated_at=INTEGRATE_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "manual_review_required",
            )
            self.assertIsNone(state["active_candidate"])
            self.assertFalse(
                (
                    workspace
                    / "design/initial/v0001/integrated.json"
                ).exists()
            )

    def test_workspace_rejects_unknown_reference(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            InitialIntegrateStageService(workspace).run(
                AcceptingModel(self.integrated),
                updated_at=INTEGRATE_AT,
            )

            path = (
                workspace
                / "design/initial/v0001/integrated.json"
            )
            invalid = load_json_from(path)
            invalid["relationships"][0][
                "participant_ids"
            ][0] = "char-9999"
            path.write_text(
                json.dumps(
                    invalid,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
