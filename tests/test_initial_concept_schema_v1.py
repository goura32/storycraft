"""Storycraft Version 1 Initial Concept契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.series_model import OpenAIStoryModel


ROOT = Path(__file__).parent.parent


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )


class InitialConceptSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        design = load_json(
            "tests/fixtures/initial-design/valid.json"
        )
        self.concept = design["concept"]
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )

    def test_fixture_concept_is_valid(self) -> None:
        ContractValidator._validate_initial_concept(
            self.concept,
            self.brief,
        )

    def test_missing_central_question_is_invalid(self) -> None:
        value = deepcopy(self.concept)
        del value["central_question"]

        with self.assertRaises(ContractError):
            ContractValidator._validate_initial_concept(
                value,
                self.brief,
            )

    def test_unknown_field_is_invalid(self) -> None:
        value = deepcopy(self.concept)
        value["characters"] = []

        with self.assertRaises(ContractError):
            ContractValidator._validate_initial_concept(
                value,
                self.brief,
            )

    def test_duplicate_theme_is_invalid(self) -> None:
        value = deepcopy(self.concept)
        value["themes"].append(value["themes"][0])

        with self.assertRaises(ContractError):
            ContractValidator._validate_initial_concept(
                value,
                self.brief,
            )

    def test_exact_avoid_phrase_is_rejected(self) -> None:
        value = deepcopy(self.concept)
        value["reader_promise"] = self.brief["avoid"][0]

        with self.assertRaises(ContractError):
            ContractValidator._validate_initial_concept(
                value,
                self.brief,
            )

    def test_model_templates_render(self) -> None:
        context = {"brief": self.brief}

        generated = OpenAIStoryModel._render(
            "generate",
            "initial_concept",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "initial_concept",
            candidate=self.concept,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "initial_concept",
            candidate=self.concept,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("dramatic_engine", generated)
        self.assertIn("Brief保持", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
