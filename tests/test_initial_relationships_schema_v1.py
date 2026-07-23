"""Storycraft Version 1 Initial Relationships契約。"""
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


def relationships_fixture() -> dict:
    return {
        "relationships": [{
            "participant_ids": [
                "char-0001",
                "char-0002",
            ],
            "relationship_type": "sisters",
            "public_description": "距離のある姉妹。",
            "private_truth": (
                "互いを守ろうとして異なる秘密を抱えている。"
            ),
            "initial_state": {
                "status": "疎遠",
                "trust": 2,
                "affection": 7,
                "hostility": 2,
            },
            "desired_arc": (
                "沈黙による保護から、"
                "真実を共有する関係へ変わる。"
            ),
            "constraints": [
                "突然完全に和解させない",
            ],
        }]
    }


class InitialRelationshipsSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        initial = load_json(
            "tests/fixtures/initial-design/valid.json"
        )
        self.concept = initial["concept"]
        self.characters = {
            "characters": [
                {
                    "character_id": "char-0001",
                    **{
                        key: value
                        for key, value in initial["characters"][0].items()
                        if key != "character_id"
                    },
                },
                {
                    "character_id": "char-0002",
                    **{
                        key: value
                        for key, value in initial["characters"][1].items()
                        if key != "character_id"
                    },
                },
            ]
        }
        self.candidate = relationships_fixture()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
    ) -> None:
        ContractValidator._validate_initial_relationships(
            value,
            self.concept,
            self.characters,
            adopted=adopted,
        )

    def test_candidate_is_valid(self) -> None:
        self.validate(self.candidate)

    def test_candidate_must_not_contain_relationship_id(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["relationships"][0][
            "relationship_id"
        ] = "rel-0001"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_character_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["relationships"][0]["participant_ids"][1] = (
            "char-9999"
        )

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_duplicate_relationship_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["relationships"].append(
            deepcopy(value["relationships"][0])
        )

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_adopted_relationship_ids_must_be_unique(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        second = deepcopy(value["relationships"][0])
        second["relationship_type"] = "rivals"
        value["relationships"].append(second)
        for record in value["relationships"]:
            record["relationship_id"] = "rel-0001"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_model_templates_render(self) -> None:
        context = {
            "concept": self.concept,
            "characters": self.characters,
        }
        generated = OpenAIStoryModel._render(
            "generate",
            "initial_relationships",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "initial_relationships",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "initial_relationships",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("relationship_id", generated)
        self.assertIn("公開／秘密の分離", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
