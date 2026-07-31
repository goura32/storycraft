from __future__ import annotations

import unittest

from storycraft.scene_generation import state_target_record
from storycraft.series_contracts import ContractError


class StateTargetRecordTests(unittest.TestCase):
    def test_resolves_the_same_sources_as_scene_card_validation(self) -> None:
        state = {
            "characters": {"char-0001": {"emotion": "calm"}},
            "relationships": {},
            "threads": {},
            "inventory": {},
            "commitments": {},
            "timeline": {"current": "t1"},
        }

        self.assertEqual(
            state_target_record(state, "character_state", "char-0001"),
            {"emotion": "calm"},
        )
        self.assertEqual(
            state_target_record(state, "timeline_state", "timeline"),
            {"current": "t1"},
        )

    def test_rejects_unknown_or_missing_target(self) -> None:
        state = {
            "characters": {}, "relationships": {}, "threads": {},
            "inventory": {}, "commitments": {}, "timeline": {},
        }

        with self.assertRaises(ContractError):
            state_target_record(state, "character_state", "char-0001")
        with self.assertRaises(ContractError):
            state_target_record(state, "unknown", "x")
