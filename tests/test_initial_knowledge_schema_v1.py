"""Storycraft Version 1 Initial Knowledge契約。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.series_model import OpenAIStoryModel

from tests.test_initial_world_schema_v1 import (
    prerequisites,
    world_candidate,
)


def adopted_world() -> dict:
    candidate = world_candidate()
    location_ids = [
        f"loc-{index:04d}"
        for index in range(
            1,
            len(candidate["locations"]) + 1,
        )
    ]
    return {
        "world": deepcopy(candidate["world"]),
        "locations": [
            {
                "location_id": location_ids[index],
                "parent_location_id": (
                    None
                    if record["parent_location_index"] is None
                    else location_ids[
                        record["parent_location_index"]
                    ]
                ),
                **{
                    key: deepcopy(value)
                    for key, value in record.items()
                    if key != "parent_location_index"
                },
            }
            for index, record in enumerate(
                candidate["locations"]
            )
        ],
        "world_rules": [
            {
                "rule_id": f"rule-{index:04d}",
                **deepcopy(record),
            }
            for index, record in enumerate(
                candidate["world_rules"],
                1,
            )
        ],
    }


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
                "statement": (
                    "凪は澪を見捨てた。"
                ),
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


class InitialKnowledgeSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
        ) = prerequisites()
        self.world = adopted_world()
        self.candidate = knowledge_candidate()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
    ) -> None:
        ContractValidator._validate_initial_knowledge(
            value,
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
            self.world,
            adopted=adopted,
        )

    def test_candidate_is_valid(self) -> None:
        self.validate(self.candidate)

    def test_candidate_must_not_contain_knowledge_ids(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["knowledge_facts"][0][
            "knowledge_id"
        ] = "know-0001"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_character_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["character_knowledge"][0][
            "character_id"
        ] = "char-9999"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_all_character_fact_pairs_are_required(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["character_knowledge"].pop()

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_false_fact_cannot_be_known(self) -> None:
        value = deepcopy(self.candidate)
        value["character_knowledge"][1][
            "state"
        ] = "knows"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_duplicate_statements_are_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["knowledge_facts"][1]["statement"] = (
            value["knowledge_facts"][0]["statement"]
        )

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_model_templates_render(self) -> None:
        context = {
            "concept": self.concept,
            "characters": self.characters,
            "relationships": self.relationships,
            "world": self.world,
        }
        generated = OpenAIStoryModel._render(
            "generate",
            "initial_knowledge",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "initial_knowledge",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "initial_knowledge",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("knowledge_index", generated)
        self.assertIn("開始時点で知り得ない", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
