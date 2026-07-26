"""Storycraft Version 1 の工程モデル契約。"""
from __future__ import annotations

import unittest

from storycraft.stages import (
    ACTIVE_TEMPLATE_STAGES,
    FINALIZATION_STAGES,
    INITIAL_DESIGN_STAGES,
    INPUT_STAGES,
    PLANNING_STAGES,
    SCENE_STAGES,
    STAGES,
    STAGE_GROUPS,
    V1_TEMPLATE_STAGES,
    Stage,
)


EXPECTED_STAGES = (
    "input",
    "initial_concept",
    "initial_characters",
    "initial_relationships",
    "initial_world",
    "initial_knowledge",
    "initial_threads",
    "initial_ending",
    "initial_integrate",
    "initial_accept",
    "series_plan",
    "volume_plan",
    "chapter_plan",
    "scene_plan",
    "scene_card",
    "scene_prose",
    "scene_continuity",
    "scene_commit",
    "volume_handoff",
    "completion",
    "publication",
)

EXPECTED_TEMPLATE_STAGES = (
    "brief",
    "initial_concept",
    "initial_characters",
    "initial_relationships",
    "initial_world",
    "initial_knowledge",
    "initial_threads",
    "initial_ending",
    "initial_integrate",
    "series_plan",
    "volume_plan",
    "chapter_plan",
    "scene_plan",
    "scene_card_v1",
    "scene_prose_v1",
    "scene_continuity_v1",
    "volume_handoff",
    "completion",
)


class StageModelV1Tests(unittest.TestCase):
    def test_stage_order_matches_v1_contract(self) -> None:
        self.assertEqual(STAGES, EXPECTED_STAGES)

    def test_stage_enum_contains_exactly_v1_stages(
        self,
    ) -> None:
        self.assertEqual(
            tuple(stage.value for stage in Stage),
            EXPECTED_STAGES,
        )

    def test_stage_groups_cover_every_stage_once(
        self,
    ) -> None:
        grouped = tuple(
            stage
            for group in STAGE_GROUPS
            for stage in group
        )

        self.assertEqual(len(grouped), 21)
        self.assertEqual(len(set(grouped)), 21)
        self.assertEqual(
            tuple(stage.value for stage in grouped),
            EXPECTED_STAGES,
        )

    def test_model_templates_contain_only_v1_stages(
        self,
    ) -> None:
        self.assertEqual(
            V1_TEMPLATE_STAGES,
            EXPECTED_TEMPLATE_STAGES,
        )
        self.assertEqual(
            ACTIVE_TEMPLATE_STAGES,
            EXPECTED_TEMPLATE_STAGES,
        )
        self.assertEqual(
            len(ACTIVE_TEMPLATE_STAGES),
            len(set(ACTIVE_TEMPLATE_STAGES)),
        )

    def test_stage_groups_preserve_phase_boundaries(
        self,
    ) -> None:
        self.assertEqual(INPUT_STAGES, (Stage.INPUT,))
        self.assertEqual(len(INITIAL_DESIGN_STAGES), 9)
        self.assertEqual(len(PLANNING_STAGES), 4)
        self.assertEqual(len(SCENE_STAGES), 4)
        self.assertEqual(len(FINALIZATION_STAGES), 3)


if __name__ == "__main__":
    unittest.main()
