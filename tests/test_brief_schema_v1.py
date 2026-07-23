from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import unittest

from storycraft.series_contracts import ContractError, ContractValidator


ROOT = Path(__file__).parent.parent


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )


class BriefSchemaV1Tests(unittest.TestCase):
    def assert_valid(self, value: dict) -> None:
        ContractValidator._validate_brief(value)

    def assert_invalid(self, value: dict) -> None:
        with self.assertRaises(ContractError):
            ContractValidator._validate_brief(value)

    def test_example_brief_is_valid(self) -> None:
        self.assert_valid(load_json("example_brief.json"))

    def test_valid_fixture_is_valid(self) -> None:
        self.assert_valid(
            load_json("tests/fixtures/brief/valid.json")
        )

    def test_missing_premise_is_invalid(self) -> None:
        self.assert_invalid(
            load_json(
                "tests/fixtures/brief/"
                "invalid-missing-premise.json"
            )
        )

    def test_volume_count_outside_range_is_invalid(self) -> None:
        self.assert_invalid(
            load_json(
                "tests/fixtures/brief/"
                "invalid-volume-count.json"
            )
        )

    def test_unknown_property_is_invalid(self) -> None:
        brief = load_json("tests/fixtures/brief/valid.json")
        brief["volumes"] = 4
        self.assert_invalid(brief)

    def test_keywords_source_requires_reference(self) -> None:
        brief = load_json("tests/fixtures/brief/valid.json")
        brief["source_type"] = "keywords"
        self.assert_invalid(brief)

    def test_keywords_source_accepts_reference(self) -> None:
        brief = deepcopy(
            load_json("tests/fixtures/brief/valid.json")
        )
        brief["source_type"] = "keywords"
        brief["source_reference"] = "input/keywords.json"
        self.assert_valid(brief)


if __name__ == "__main__":
    unittest.main()
