"""Storycraft Version 1 initial_knowledge Stage契約。"""
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
from storycraft.initial_knowledge_stage import (
    InitialKnowledgeStageService,
)
from storycraft.initial_relationships_stage import (
    InitialRelationshipsStageService,
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

from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    NeverCalledModel,
    character_candidate,
    relationship_candidate,
    world_candidate,
)


ROOT = Path(__file__).parent.parent
CREATED_AT = "2026-07-23T16:00:00Z"
INPUT_AT = "2026-07-23T16:05:00Z"
CONCEPT_AT = "2026-07-23T16:10:00Z"
CHARACTERS_AT = "2026-07-23T16:15:00Z"
RELATIONSHIPS_AT = "2026-07-23T16:20:00Z"
WORLD_AT = "2026-07-23T16:25:00Z"
KNOWLEDGE_AT = "2026-07-23T16:30:00Z"


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )


def load_json_from(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def knowledge_candidate() -> dict:
    return {
        "knowledge_facts": [
            {
                "statement": (
                    "灯台火災は単純な事故ではない。"
                ),
                "truth_status": "true",
                "reader_visibility": "hidden",
                "source_type": "world",
                "private_notes": (
                    "火災には未公開の経緯がある。"
                ),
            },
            {
                "statement": "凪は澪を見捨てた。",
                "truth_status": "false",
                "reader_visibility": "hidden",
                "source_type": "character",
                "private_notes": (
                    "澪が開始時点で抱いている誤解。"
                ),
            },
        ],
        "character_knowledge": [
            {
                "character_id": "char-0001",
                "knowledge_index": 0,
                "state": "suspects",
            },
            {
                "character_id": "char-0001",
                "knowledge_index": 1,
                "state": "believes",
            },
            {
                "character_id": "char-0002",
                "knowledge_index": 0,
                "state": "knows",
            },
            {
                "character_id": "char-0002",
                "knowledge_index": 1,
                "state": "disbelieves",
            },
        ],
    }


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
                    "field": (
                        "knowledge_facts[0].private_notes"
                    ),
                    "description": (
                        candidate["knowledge_facts"][0][
                            "private_notes"
                        ]
                    ),
                    "suggestion": (
                        "入力事実だけで具体的に書き直す"
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
                "field": (
                    "knowledge_facts[0].private_notes"
                ),
                "description": (
                    candidate["knowledge_facts"][0][
                        "private_notes"
                    ]
                ),
                "suggestion": (
                    "入力事実だけで具体的に書き直す"
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
        revised["knowledge_facts"][0][
            "private_notes"
        ] += f" 修正{self.revision_calls}"
        return revised


class InitialKnowledgeStageV1Tests(unittest.TestCase):
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
        self.knowledge = knowledge_candidate()

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
        return workspace

    def test_generate_review_adopt_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            root = workspace / "design/initial/v0001"
            concept = load_json_from(root / "concept.json")
            characters = load_json_from(
                root / "characters.json"
            )
            relationships = load_json_from(
                root / "relationships.json"
            )
            world = load_json_from(root / "world.json")
            model = AcceptingModel(self.knowledge)

            state = InitialKnowledgeStageService(
                workspace
            ).run(
                model,
                updated_at=KNOWLEDGE_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "initial_knowledge"),
                    ("critique", "initial_knowledge"),
                ],
            )
            expected_context = {
                "concept": concept,
                "characters": characters,
                "relationships": relationships,
                "world": world,
            }
            self.assertEqual(
                model.contexts,
                [expected_context, expected_context],
            )
            self.assertEqual(
                state["current_stage"],
                "initial_threads",
            )
            self.assertIsNone(state["active_candidate"])

            adopted = load_json_from(
                root / "knowledge.json"
            )
            self.assertEqual(
                [
                    record["knowledge_id"]
                    for record in adopted[
                        "knowledge_facts"
                    ]
                ],
                ["know-0001", "know-0002"],
            )
            self.assertEqual(
                {
                    record["knowledge_id"]
                    for record in adopted[
                        "character_knowledge"
                    ]
                },
                {"know-0001", "know-0002"},
            )
            validate_workspace_layout(workspace)

            candidate = load_json_from(
                workspace
                / "runtime/candidates/initial_knowledge"
                / "candidate-000005/v0001/candidate.json"
            )
            self.assertIn(
                "knowledge_index",
                candidate["content"][
                    "character_knowledge"
                ][0],
            )
            self.assertNotIn(
                "knowledge_id",
                candidate["content"][
                    "knowledge_facts"
                ][0],
            )

    def test_revision_creates_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            revised = deepcopy(self.knowledge)
            revised["knowledge_facts"][0][
                "private_notes"
            ] = (
                "Worldのprivate truthに由来する"
                "開始時点の作者用情報。"
            )

            state = InitialKnowledgeStageService(
                workspace
            ).run(
                RevisingModel(self.knowledge, revised),
                updated_at=KNOWLEDGE_AT,
            )

            root = (
                workspace
                / "runtime/candidates/initial_knowledge"
                / "candidate-000005"
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
                "initial_threads",
            )

    def test_revision_limit_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            model = NeverAcceptingModel(self.knowledge)

            state = InitialKnowledgeStageService(
                workspace
            ).run(
                model,
                updated_at=KNOWLEDGE_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "revision_limit",
            )
            self.assertEqual(
                state["active_candidate"],
                {
                    "kind": "initial_knowledge",
                    "candidate_id": "candidate-000005",
                    "version": 3,
                },
            )
            self.assertEqual(model.review_calls, 3)
            self.assertEqual(model.revision_calls, 2)
            self.assertFalse(
                (
                    workspace
                    / "design/initial/v0001/knowledge.json"
                ).exists()
            )

    def test_invalid_generation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            invalid = deepcopy(self.knowledge)
            invalid["character_knowledge"][1][
                "state"
            ] = "knows"

            state = InitialKnowledgeStageService(
                workspace
            ).run(
                AcceptingModel(invalid),
                updated_at=KNOWLEDGE_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "manual_review_required",
            )
            self.assertIsNone(state["active_candidate"])

    def test_workspace_rejects_unknown_knowledge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            InitialKnowledgeStageService(workspace).run(
                AcceptingModel(self.knowledge),
                updated_at=KNOWLEDGE_AT,
            )

            path = (
                workspace
                / "design/initial/v0001/knowledge.json"
            )
            invalid = load_json_from(path)
            invalid["character_knowledge"][0][
                "knowledge_id"
            ] = "know-9999"
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
