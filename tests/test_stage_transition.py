"""正本 docs の v2 工程遷移。"""
from __future__ import annotations

import unittest

from storycraft.stage_transition import allowed_next_stages, validate_stage_transition
from storycraft.series_contracts import ContractError
from storycraft.stages import Stage


class StageTransitionV2Tests(unittest.TestCase):
    def test_initial_design_is_one_stage(self) -> None:
        self.assertEqual(
            allowed_next_stages(Stage.REQUEST_INTAKE),
            frozenset({Stage.INITIAL_DESIGN}),
        )
        self.assertEqual(
            allowed_next_stages(Stage.INITIAL_DESIGN),
            frozenset({Stage.SERIES_PLAN}),
        )

    def test_volume_publication_returns_to_next_volume_plan(self) -> None:
        self.assertEqual(
            allowed_next_stages(Stage.VOLUME_PUBLICATION),
            frozenset({Stage.VOLUME_PLAN}),
        )
        self.assertEqual(
            validate_stage_transition("volume_publication", "volume_plan"),
            (Stage.VOLUME_PUBLICATION, Stage.VOLUME_PLAN),
        )

    def test_legacy_stages_are_not_transitions(self) -> None:
        with self.assertRaisesRegex(ContractError, "未知"):
            allowed_next_stages("completion")
