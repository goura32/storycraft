"""Storycraft Version 1 input Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
import tempfile
import unittest
from pathlib import Path

from storycraft.input_stage import InputStageService
from storycraft.run_state import RunStateStore
from storycraft.workspace import (
    create_workspace_from_brief,
    create_workspace_from_keywords,
    validate_workspace_layout,
)


ROOT = Path(__file__).parent.parent
CREATED_AT = "2026-07-23T13:00:00Z"
UPDATED_AT = "2026-07-23T13:05:00Z"


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(
            encoding="utf-8"
        )
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
    def __init__(self, brief: dict) -> None:
        self.brief = brief
        self.calls: list[str] = []

    def generate(self, stage: str, context: dict) -> dict:
        self.calls.append("generate")
        return deepcopy(self.brief)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.calls.append("critique")
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
                    "field": "premise",
                    "description": "premiseを修正する",
                    "suggestion": "候補に基づき書き直し",
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
    def __init__(self, brief: dict) -> None:
        self.brief = brief
        self.revision_calls = 0
        self.review_calls = 0

    def generate(self, stage: str, context: dict) -> dict:
        return deepcopy(self.brief)

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
                "field": "premise",
                "description": "未解決",
                "suggestion": "候補に基づき書き直し",
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
        revised["premise"] = (
            f"{candidate['premise']} 修正"
            f"{self.revision_calls}"
        )
        return revised


class InputStageV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.keywords = load_json(
            "tests/fixtures/keywords/valid.json"
        )
        self.config = load_json(
            "tests/fixtures/workspace/config.json"
        )
        self.generated = deepcopy(self.brief)
        self.generated["source_type"] = "keywords"
        self.generated["source_reference"] = (
            "input/keywords.json"
        )
        self.generated["avoid"] = list(
            dict.fromkeys(
                self.generated["avoid"]
                + self.keywords["avoid"]
            )
        )

    def test_brief_input_advances_without_model_call(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_brief(
                workspace,
                workspace_id="ws-test-0001",
                brief=self.brief,
                config=self.config,
                created_at=CREATED_AT,
            )

            state = InputStageService(workspace).run(
                NeverCalledModel(),
                updated_at=UPDATED_AT,
            )

            self.assertEqual(
                state["current_stage"],
                "initial_concept",
            )
            self.assertEqual(state["status"], "running")
            self.assertIsNone(state["active_candidate"])

    def test_keywords_generate_review_and_adopt_brief(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_keywords(
                workspace,
                workspace_id="ws-test-0001",
                keywords=self.keywords,
                config=self.config,
                created_at=CREATED_AT,
            )
            model = AcceptingModel(self.generated)

            state = InputStageService(workspace).run(
                model,
                updated_at=UPDATED_AT,
            )

            self.assertEqual(
                model.calls,
                ["generate", "critique"],
            )
            self.assertEqual(
                state["current_stage"],
                "initial_concept",
            )
            self.assertIsNone(state["active_candidate"])
            self.assertEqual(
                load_json_from(
                    workspace / "input/brief.json"
                ),
                self.generated,
            )
            validate_workspace_layout(workspace)

            version = (
                workspace
                / "runtime/candidates/input"
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
                )["decision"],
                "accept",
            )

    def test_revision_creates_new_candidate_version(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_keywords(
                workspace,
                workspace_id="ws-test-0001",
                keywords=self.keywords,
                config=self.config,
                created_at=CREATED_AT,
            )
            revised = deepcopy(self.generated)
            revised["premise"] = (
                self.generated["premise"] + " 修正版"
            )

            state = InputStageService(workspace).run(
                RevisingModel(
                    self.generated,
                    revised,
                ),
                updated_at=UPDATED_AT,
            )

            candidate_root = (
                workspace
                / "runtime/candidates/input"
                / "candidate-000001"
            )
            self.assertEqual(
                load_json_from(
                    candidate_root
                    / "v0001/status.json"
                )["status"],
                "needs_revision",
            )
            self.assertEqual(
                load_json_from(
                    candidate_root
                    / "v0002/status.json"
                )["status"],
                "accepted",
            )
            self.assertTrue(
                (
                    candidate_root
                    / "v0002/revision.json"
                ).is_file()
            )
            self.assertEqual(
                state["current_stage"],
                "initial_concept",
            )
            self.assertEqual(
                load_json_from(
                    workspace / "input/brief.json"
                ),
                revised,
            )

    def test_revision_limit_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_keywords(
                workspace,
                workspace_id="ws-test-0001",
                keywords=self.keywords,
                config=self.config,
                created_at=CREATED_AT,
            )
            model = NeverAcceptingModel(self.generated)

            state = InputStageService(workspace).run(
                model,
                updated_at=UPDATED_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "revision_limit",
            )
            self.assertEqual(
                state["active_candidate"],
                {
                    "kind": "input",
                    "candidate_id": "candidate-000001",
                    "version": 3,
                },
            )
            self.assertFalse(
                (workspace / "input/brief.json").exists()
            )
            self.assertEqual(model.revision_calls, 2)
            self.assertEqual(model.review_calls, 3)
            self.assertEqual(
                load_json_from(
                    workspace
                    / "runtime/candidates/input"
                    / "candidate-000001/v0003"
                    / "status.json"
                )["status"],
                "rejected",
            )

    def test_generated_brief_must_preserve_volume_hint(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_keywords(
                workspace,
                workspace_id="ws-test-0001",
                keywords=self.keywords,
                config=self.config,
                created_at=CREATED_AT,
            )
            invalid = deepcopy(self.generated)
            invalid["volume_count"] = 5

            state = InputStageService(workspace).run(
                AcceptingModel(invalid),
                updated_at=UPDATED_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "manual_review_required",
            )
            self.assertFalse(
                (workspace / "input/brief.json").exists()
            )
            self.assertIsNone(state["active_candidate"])

    def test_counters_reserve_candidate_reviews_and_revision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            create_workspace_from_keywords(
                workspace,
                workspace_id="ws-test-0001",
                keywords=self.keywords,
                config=self.config,
                created_at=CREATED_AT,
            )
            revised = deepcopy(self.generated)
            revised["premise"] += " 修正版"

            InputStageService(workspace).run(
                RevisingModel(
                    self.generated,
                    revised,
                ),
                updated_at=UPDATED_AT,
            )

            counters = load_json_from(
                workspace / "runtime/counters.json"
            )
            self.assertEqual(
                counters["next_candidate"],
                2,
            )
            self.assertEqual(
                counters["next_review"],
                3,
            )
            self.assertEqual(
                counters["next_revision"],
                2,
            )


def load_json_from(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


if __name__ == "__main__":
    unittest.main()
