"""Storycraft Version 1 initial_concept Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from storycraft.initial_concept_stage import (
    InitialConceptStageService,
)
from storycraft.input_stage import InputStageService
from storycraft.workspace import (
    create_workspace_from_brief,
    validate_workspace_layout,
)


ROOT = Path(__file__).parent.parent
CREATED_AT = "2026-07-23T13:00:00Z"
INPUT_UPDATED_AT = "2026-07-23T13:05:00Z"
CONCEPT_UPDATED_AT = "2026-07-23T13:10:00Z"


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )


def load_json_from(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


class NeverCalledModel:
    def generate(self, stage: str, context: dict) -> dict:
        raise AssertionError("model must not be called")

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        raise AssertionError("model must not be called")

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        raise AssertionError("model must not be called")


class AcceptingModel:
    def __init__(self, concept: dict) -> None:
        self.concept = concept
        self.calls: list[tuple[str, str]] = []
        self.contexts: list[dict] = []

    def generate(self, stage: str, context: dict) -> dict:
        self.calls.append(("generate", stage))
        self.contexts.append(deepcopy(context))
        return deepcopy(self.concept)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.calls.append(("critique", stage))
        self.contexts.append(deepcopy(context))
        return {"issues": []}

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        raise AssertionError("revision must not be called")


class RevisingModel:
    def __init__(
        self,
        initial: dict,
        revised: dict,
    ) -> None:
        self.initial = initial
        self.revised = revised
        self.review_count = 0

    def generate(self, stage: str, context: dict) -> dict:
        return deepcopy(self.initial)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.review_count += 1
        if self.review_count == 1:
            return {
                "issues": [{
                    "severity": "major",
                    "field": "central_question",
                    "description": (
                        candidate["central_question"]
                    ),
                    "suggestion": "Briefに基づき書き直す",
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
    def __init__(self, concept: dict) -> None:
        self.concept = concept
        self.review_calls = 0
        self.revision_calls = 0

    def generate(self, stage: str, context: dict) -> dict:
        return deepcopy(self.concept)

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
                "field": "central_question",
                "description": (
                    candidate["central_question"]
                ),
                "suggestion": "Briefに基づき書き直す",
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
        revised["central_question"] = (
            candidate["central_question"]
            + f" 修正{self.revision_calls}"
        )
        return revised


class InitialConceptStageV1Tests(unittest.TestCase):
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
            updated_at=INPUT_UPDATED_AT,
        )
        return workspace

    def test_generate_review_adopt_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            model = AcceptingModel(self.concept)

            state = InitialConceptStageService(
                workspace
            ).run(
                model,
                updated_at=CONCEPT_UPDATED_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "initial_concept"),
                    ("critique", "initial_concept"),
                ],
            )
            self.assertEqual(
                model.contexts,
                [
                    {"brief": self.brief},
                    {"brief": self.brief},
                ],
            )
            self.assertEqual(
                state["current_stage"],
                "initial_characters",
            )
            self.assertEqual(state["status"], "running")
            self.assertIsNone(state["active_candidate"])

            adopted = (
                workspace
                / "design/initial/v0001/concept.json"
            )
            self.assertEqual(
                load_json_from(adopted),
                self.concept,
            )
            validate_workspace_layout(workspace)

            version = (
                workspace
                / "runtime/candidates/initial_concept"
                / "candidate-000001/v0001"
            )
            self.assertEqual(
                load_json_from(
                    version / "status.json"
                )["status"],
                "accepted",
            )
            self.assertEqual(
                load_json_from(
                    version / "review.json"
                )["target_type"],
                "initial_concept",
            )

    def test_revision_creates_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            revised = deepcopy(self.concept)
            revised["central_question"] = (
                "姉妹は真実を共有し、"
                "再び互いを信じられるか。"
            )

            state = InitialConceptStageService(
                workspace
            ).run(
                RevisingModel(
                    self.concept,
                    revised,
                ),
                updated_at=CONCEPT_UPDATED_AT,
            )

            root = (
                workspace
                / "runtime/candidates/initial_concept"
                / "candidate-000001"
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
                "initial_characters",
            )
            self.assertEqual(
                load_json_from(
                    workspace
                    / "design/initial/v0001/concept.json"
                ),
                revised,
            )

    def test_revision_limit_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            model = NeverAcceptingModel(self.concept)

            state = InitialConceptStageService(
                workspace
            ).run(
                model,
                updated_at=CONCEPT_UPDATED_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "revision_limit",
            )
            self.assertEqual(
                state["active_candidate"],
                {
                    "kind": "initial_concept",
                    "candidate_id": "candidate-000001",
                    "version": 3,
                },
            )
            self.assertEqual(model.review_calls, 3)
            self.assertEqual(model.revision_calls, 2)
            self.assertFalse(
                (
                    workspace
                    / "design/initial/v0001/concept.json"
                ).exists()
            )
            self.assertEqual(
                load_json_from(
                    workspace
                    / "runtime/candidates/initial_concept"
                    / "candidate-000001/v0003/status.json"
                )["status"],
                "rejected",
            )

    def test_invalid_generation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            invalid = deepcopy(self.concept)
            del invalid["dramatic_engine"]

            state = InitialConceptStageService(
                workspace
            ).run(
                AcceptingModel(invalid),
                updated_at=CONCEPT_UPDATED_AT,
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
                    / "design/initial/v0001/concept.json"
                ).exists()
            )

    def test_brief_tone_must_be_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            invalid = deepcopy(self.concept)
            invalid["tone"] = ["静か"]

            state = InitialConceptStageService(
                workspace
            ).run(
                AcceptingModel(invalid),
                updated_at=CONCEPT_UPDATED_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertIn(
                "toneを保持していません",
                state["last_error"]["message"],
            )


if __name__ == "__main__":
    unittest.main()
