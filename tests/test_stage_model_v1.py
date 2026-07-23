"""Storycraft Version 1 の工程モデル契約。"""
from __future__ import annotations

import unittest

from storycraft.stages import (
    ACTIVE_TEMPLATE_STAGES,
    FINALIZATION_STAGES,
    INITIAL_DESIGN_STAGES,
    LEGACY_TEMPLATE_STAGES,
    V1_TEMPLATE_STAGES,
    INPUT_STAGES,
    PLANNING_STAGES,
    SCENE_STAGES,
    STAGES,
    STAGE_GROUPS,
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


class StageModelV1Tests(unittest.TestCase):
    def test_stage_order_matches_v1_contract(self) -> None:
        self.assertEqual(STAGES, EXPECTED_STAGES)

    def test_stage_enum_contains_exactly_the_v1_stages(self) -> None:
        self.assertEqual(tuple(stage.value for stage in Stage), EXPECTED_STAGES)

    def test_stage_groups_cover_every_stage_exactly_once(self) -> None:
        grouped = tuple(stage for group in STAGE_GROUPS for stage in group)

        self.assertEqual(len(grouped), 21)
        self.assertEqual(len(set(grouped)), 21)
        self.assertEqual(tuple(stage.value for stage in grouped), EXPECTED_STAGES)

    def test_legacy_template_stages_are_centralized_during_migration(self) -> None:
        self.assertEqual(len(LEGACY_TEMPLATE_STAGES), 13)
        self.assertEqual(len(set(LEGACY_TEMPLATE_STAGES)), 13)
        self.assertIn("brief", LEGACY_TEMPLATE_STAGES)
        self.assertIn("closure", LEGACY_TEMPLATE_STAGES)

    def test_template_stage_sets_remain_separated_during_migration(
        self,
    ) -> None:
        self.assertEqual(
            V1_TEMPLATE_STAGES,
            (
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
            ),
        )
        self.assertEqual(
            ACTIVE_TEMPLATE_STAGES,
            LEGACY_TEMPLATE_STAGES + V1_TEMPLATE_STAGES,
        )
        self.assertEqual(
            len(ACTIVE_TEMPLATE_STAGES),
            len(set(ACTIVE_TEMPLATE_STAGES)),
        )

    def test_stage_groups_preserve_phase_boundaries(self) -> None:
        self.assertEqual(INPUT_STAGES, (Stage.INPUT,))
        self.assertEqual(len(INITIAL_DESIGN_STAGES), 9)
        self.assertEqual(len(PLANNING_STAGES), 4)
        self.assertEqual(len(SCENE_STAGES), 4)
        self.assertEqual(len(FINALIZATION_STAGES), 3)


if __name__ == "__main__":
    unittest.main()
