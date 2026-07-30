"""docs/design/state-and-transitions.md の工程列。"""
from __future__ import annotations

import unittest

from storycraft.stages import STAGES, Stage


class StageModelV2Tests(unittest.TestCase):
    def test_current_stage_set_has_no_handoff_or_completion(self) -> None:
        self.assertEqual(
            STAGES,
            (
                "request_intake",
                "initial_design",
                "series_plan",
                "volume_plan",
                "chapter_plan",
                "scene_plan",
                "scene_card",
                "scene_prose",
                "scene_continuity",
                "scene_commit",
                "volume_publication",
            ),
        )
        self.assertEqual(Stage.VOLUME_PUBLICATION.value, "volume_publication")
