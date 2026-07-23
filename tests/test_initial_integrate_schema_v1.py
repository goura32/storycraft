"""Storycraft Version 1 Initial Integrate契約。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.series_model import OpenAIStoryModel

from tests.test_initial_ending_schema_v1 import (
    adopted_threads,
    ending_candidate,
)
from tests.test_initial_knowledge_schema_v1 import (
    adopted_world,
    prerequisites,
)
from tests.test_initial_threads_schema_v1 import (
    adopted_knowledge,
)


def adopted_ending() -> dict:
    candidate = ending_candidate()
    return {
        "ending": {
            "ending_id": "ending-0001",
            **deepcopy(candidate["ending"]),
        },
        "long_term_arcs": [
            {
                "arc_id": f"arc-{index:04d}",
                **deepcopy(record),
            }
            for index, record in enumerate(
                candidate["long_term_arcs"],
                1,
            )
        ],
    }


def integrated_candidate() -> dict:
    (
        _brief,
        concept,
        characters,
        relationships,
    ) = prerequisites()
    world = adopted_world()
    knowledge = adopted_knowledge()
    threads = adopted_threads()
    ending = adopted_ending()

    return {
        "concept": deepcopy(concept),
        "characters": deepcopy(
            characters["characters"]
        ),
        "relationships": deepcopy(
            relationships["relationships"]
        ),
        "world": deepcopy(world["world"]),
        "locations": deepcopy(world["locations"]),
        "world_rules": deepcopy(world["world_rules"]),
        "knowledge_facts": deepcopy(
            knowledge["knowledge_facts"]
        ),
        "character_knowledge": deepcopy(
            knowledge["character_knowledge"]
        ),
        "threads": deepcopy(threads["threads"]),
        "ending": deepcopy(ending["ending"]),
        "long_term_arcs": deepcopy(
            ending["long_term_arcs"]
        ),
    }


class InitialIntegrateSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
        ) = prerequisites()
        self.world = adopted_world()
        self.knowledge = adopted_knowledge()
        self.threads = adopted_threads()
        self.ending = adopted_ending()
        self.candidate = integrated_candidate()

    def validate(self, value: dict) -> None:
        ContractValidator._validate_initial_integrate(
            value,
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
            self.world,
            self.knowledge,
            self.threads,
            self.ending,
        )

    def test_candidate_is_valid(self) -> None:
        self.validate(self.candidate)

    def test_design_metadata_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["design_id"] = "initial-design-0001"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_missing_component_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value.pop("knowledge_facts")

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_character_identity_change_is_rejected(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["characters"][0][
            "character_id"
        ] = "char-9999"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_added_record_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        added = deepcopy(value["threads"][0])
        added["thread_id"] = "thread-9999"
        added["title"] = "追加Thread"
        added["question"] = "追加Threadは成立するか。"
        value["threads"].append(added)

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_record_reordering_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["long_term_arcs"].reverse()

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_reference_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["relationships"][0][
            "participant_ids"
        ][0] = "char-9999"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_ending_id_change_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["ending"]["ending_id"] = "ending-9999"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_model_templates_render(self) -> None:
        context = {
            "brief": self.brief,
            "concept": self.concept,
            "characters": self.characters,
            "relationships": self.relationships,
            "world": self.world,
            "knowledge": self.knowledge,
            "threads": self.threads,
            "ending": self.ending,
        }
        generated = OpenAIStoryModel._render(
            "generate",
            "initial_integrate",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "initial_integrate",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "initial_integrate",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("recordの件数と配列順", generated)
        self.assertIn("World Rule", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
