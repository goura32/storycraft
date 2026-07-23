"""Storycraft Version 1 initial_ending Stage契約。"""
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
    relationship_candidate,
    world_candidate,
)


ROOT = Path(__file__).parent.parent
CREATED_AT = "2026-07-23T18:00:00Z"
INPUT_AT = "2026-07-23T18:05:00Z"
CONCEPT_AT = "2026-07-23T18:10:00Z"
CHARACTERS_AT = "2026-07-23T18:15:00Z"
RELATIONSHIPS_AT = "2026-07-23T18:20:00Z"
WORLD_AT = "2026-07-23T18:25:00Z"
KNOWLEDGE_AT = "2026-07-23T18:30:00Z"
THREADS_AT = "2026-07-23T18:35:00Z"
ENDING_AT = "2026-07-23T18:40:00Z"


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )


def load_json_from(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RevisingModel:
    def __init__(self, initial: dict, revised: dict) -> None:
        self.initial = initial
        self.revised = revised
        self.reviews = 0

    def generate(self, stage: str, context: dict) -> dict:
        return deepcopy(self.initial)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.reviews += 1
        if self.reviews == 1:
            return {
                "issues": [{
                    "severity": "major",
                    "field": "ending.desired_effect",
                    "description": (
                        candidate["ending"][
                            "desired_effect"
                        ]
                    ),
                    "suggestion": (
                        "BriefのEnding希望に沿って書き直す"
                    ),
                }]
            }
        return {"issues": []}

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        return deepcopy(self.revised)


class NeverAcceptingModel:
    def __init__(self, value: dict) -> None:
        self.value = value
        self.review_calls = 0
        self.revision_calls = 0

    def generate(self, stage: str, context: dict) -> dict:
        return deepcopy(self.value)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.review_calls += 1
        return {
            "issues": [{
                "severity": "major",
                "field": "ending.desired_effect",
                "description": (
                    candidate["ending"]["desired_effect"]
                ),
                "suggestion": (
                    "BriefのEnding希望に沿って書き直す"
                ),
            }]
        }

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        self.revision_calls += 1
        revised = deepcopy(candidate)
        revised["ending"]["desired_effect"] += (
            f" 修正{self.revision_calls}"
        )
        return revised


class InitialEndingStageV1Tests(unittest.TestCase):
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
        self.ending = ending_candidate()

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
        return workspace

    def test_generate_review_adopt_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            root = workspace / "design/initial/v0001"
            brief = load_json_from(
                workspace / "input/brief.json"
            )
            concept = load_json_from(root / "concept.json")
            characters = load_json_from(
                root / "characters.json"
            )
            relationships = load_json_from(
                root / "relationships.json"
            )
            threads = load_json_from(root / "threads.json")
            model = AcceptingModel(self.ending)

            state = InitialEndingStageService(workspace).run(
                model,
                updated_at=ENDING_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "initial_ending"),
                    ("critique", "initial_ending"),
                ],
            )
            expected_context = {
                "brief": brief,
                "concept": concept,
                "characters": characters,
                "relationships": relationships,
                "threads": threads,
            }
            self.assertEqual(
                model.contexts,
                [expected_context, expected_context],
            )
            self.assertEqual(
                state["current_stage"],
                "initial_integrate",
            )
            self.assertIsNone(state["active_candidate"])

            adopted = load_json_from(root / "ending.json")
            self.assertEqual(
                adopted["ending"]["ending_id"],
                "ending-0001",
            )
            self.assertEqual(
                [
                    record["arc_id"]
                    for record in adopted[
                        "long_term_arcs"
                    ]
                ],
                [
                    "arc-0001",
                    "arc-0002",
                    "arc-0003",
                    "arc-0004",
                ],
            )
            validate_workspace_layout(workspace)

            candidate = load_json_from(
                workspace
                / "runtime/candidates/initial_ending"
                / "candidate-000007/v0001/candidate.json"
            )
            self.assertNotIn(
                "ending_id",
                candidate["content"]["ending"],
            )
            self.assertNotIn(
                "arc_id",
                candidate["content"][
                    "long_term_arcs"
                ][0],
            )

    def test_revision_creates_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            revised = deepcopy(self.ending)
            revised["ending"]["desired_effect"] = (
                "姉妹が痛みを受け止めながら、"
                "町で新しい関係を始める希望を残す。"
            )

            state = InitialEndingStageService(workspace).run(
                RevisingModel(self.ending, revised),
                updated_at=ENDING_AT,
            )

            root = (
                workspace
                / "runtime/candidates/initial_ending"
                / "candidate-000007"
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
                "initial_integrate",
            )

    def test_revision_limit_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            model = NeverAcceptingModel(self.ending)

            state = InitialEndingStageService(workspace).run(
                model,
                updated_at=ENDING_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "revision_limit",
            )
            self.assertEqual(
                state["active_candidate"],
                {
                    "kind": "initial_ending",
                    "candidate_id": "candidate-000007",
                    "version": 3,
                },
            )
            self.assertEqual(model.review_calls, 3)
            self.assertEqual(model.revision_calls, 2)
            self.assertFalse(
                (
                    workspace
                    / "design/initial/v0001/ending.json"
                ).exists()
            )

    def test_invalid_generation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            invalid = deepcopy(self.ending)
            invalid["ending"]["thread_requirements"].pop()

            state = InitialEndingStageService(workspace).run(
                AcceptingModel(invalid),
                updated_at=ENDING_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "manual_review_required",
            )
            self.assertIsNone(state["active_candidate"])

    def test_workspace_rejects_unknown_arc_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            InitialEndingStageService(workspace).run(
                AcceptingModel(self.ending),
                updated_at=ENDING_AT,
            )

            path = (
                workspace
                / "design/initial/v0001/ending.json"
            )
            invalid = load_json_from(path)
            invalid["long_term_arcs"][0][
                "target_id"
            ] = "char-9999"
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
