"""採用済みInitial DesignとInitial Generation契約。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.initial_generation import (
    build_accepted_initial_design,
    build_initial_generation,
    validate_accepted_initial_design,
    validate_initial_generation,
)
from storycraft.series_contracts import ContractError

from tests.test_initial_integrate_schema_v1 import (
    integrated_candidate,
)
from tests.test_initial_world_stage_v1 import load_json


CREATED_AT = "2026-07-23T10:10:00Z"


class InitialGenerationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.integrated = integrated_candidate()
        self.design = build_accepted_initial_design(
            self.integrated,
            self.brief,
            created_at=CREATED_AT,
        )
        self.generation = build_initial_generation(
            self.design,
            generation_id="gen-000001",
            created_at=CREATED_AT,
        )

    def test_accepted_design_is_valid(self) -> None:
        validate_accepted_initial_design(
            self.design,
            self.integrated,
            self.brief,
        )

    def test_accepted_design_rejects_changed_content(
        self,
    ) -> None:
        invalid = deepcopy(self.design)
        invalid["threads"][0]["title"] = "変更"

        with self.assertRaises(ContractError):
            validate_accepted_initial_design(
                invalid,
                self.integrated,
                self.brief,
            )

    def test_initial_generation_is_valid(self) -> None:
        validate_initial_generation(
            self.generation,
            self.design,
        )

    def test_generation_has_initial_story_state(
        self,
    ) -> None:
        state = self.generation["state.json"]

        self.assertEqual(
            set(state["characters"]),
            {
                record["character_id"]
                for record in self.design["characters"]
            },
        )
        self.assertEqual(
            set(state["relationships"]),
            {
                record["relationship_id"]
                for record in self.design["relationships"]
            },
        )
        self.assertEqual(
            set(state["threads"]),
            {
                record["thread_id"]
                for record in self.design["threads"]
            },
        )
        self.assertEqual(
            self.generation["evidence.json"]["evidence"],
            [],
        )
        self.assertIsNone(
            self.generation["commit.json"][
                "parent_generation_id"
            ]
        )

    def test_generation_rejects_state_drift(self) -> None:
        invalid = deepcopy(self.generation)
        character_id = next(
            iter(invalid["state.json"]["characters"])
        )
        invalid["state.json"]["characters"][
            character_id
        ]["availability"] = "unavailable"

        with self.assertRaises(ContractError):
            validate_initial_generation(
                invalid,
                self.design,
            )


if __name__ == "__main__":
    unittest.main()
