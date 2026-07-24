from __future__ import annotations

import unittest

from storycraft.series_contracts import ContractError
from storycraft.stage_transition import (
    allowed_next_stages,
    validate_stage_transition,
)
from storycraft.stages import Stage


class SceneCommitTransitionV1Test(unittest.TestCase):
    def test_scene_commit_has_only_documented_next_stages(
        self,
    ) -> None:
        self.assertEqual(
            allowed_next_stages(Stage.SCENE_COMMIT),
            frozenset({
                Stage.SCENE_PLAN,
                Stage.CHAPTER_PLAN,
                Stage.VOLUME_HANDOFF,
            }),
        )

    def test_scene_commit_cannot_skip_to_scene_card(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ContractError,
            "不正なV1 Stage遷移",
        ):
            validate_stage_transition(
                Stage.SCENE_COMMIT,
                Stage.SCENE_CARD,
            )


if __name__ == "__main__":
    unittest.main()
