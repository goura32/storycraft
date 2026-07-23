"""Storycraft Version 1 のStage遷移契約。"""
from __future__ import annotations

import unittest

from storycraft.series_contracts import ContractError
from storycraft.stage_transition import (
    ALLOWED_STAGE_TRANSITIONS,
    allowed_next_stages,
    is_terminal_stage,
    validate_stage_transition,
)
from storycraft.stages import Stage


class StageTransitionV1Tests(unittest.TestCase):
    def test_every_v1_stage_has_transition_definition(self) -> None:
        self.assertEqual(
            set(ALLOWED_STAGE_TRANSITIONS),
            set(Stage),
        )

    def test_fixed_initial_and_planning_chain_is_allowed(self) -> None:
        chain = (
            Stage.INPUT,
            Stage.INITIAL_CONCEPT,
            Stage.INITIAL_CHARACTERS,
            Stage.INITIAL_RELATIONSHIPS,
            Stage.INITIAL_WORLD,
            Stage.INITIAL_KNOWLEDGE,
            Stage.INITIAL_THREADS,
            Stage.INITIAL_ENDING,
            Stage.INITIAL_INTEGRATE,
            Stage.INITIAL_ACCEPT,
            Stage.SERIES_PLAN,
            Stage.VOLUME_PLAN,
            Stage.CHAPTER_PLAN,
            Stage.SCENE_PLAN,
            Stage.SCENE_CARD,
            Stage.SCENE_PROSE,
            Stage.SCENE_CONTINUITY,
            Stage.SCENE_COMMIT,
        )

        for current, following in zip(chain, chain[1:]):
            self.assertEqual(
                validate_stage_transition(current, following),
                (current, following),
            )

    def test_scene_commit_allows_each_documented_branch(self) -> None:
        self.assertEqual(
            allowed_next_stages(Stage.SCENE_COMMIT),
            frozenset({
                Stage.SCENE_CARD,
                Stage.CHAPTER_PLAN,
                Stage.SCENE_PLAN,
                Stage.VOLUME_HANDOFF,
            }),
        )

    def test_volume_handoff_allows_next_volume_or_completion(self) -> None:
        self.assertEqual(
            allowed_next_stages("volume_handoff"),
            frozenset({
                Stage.VOLUME_PLAN,
                Stage.COMPLETION,
            }),
        )

    def test_completion_allows_publication(self) -> None:
        validate_stage_transition(
            Stage.COMPLETION,
            Stage.PUBLICATION,
        )

    def test_pipeline_skip_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ContractError,
            "input -> series_plan",
        ):
            validate_stage_transition(
                Stage.INPUT,
                Stage.SERIES_PLAN,
            )

    def test_unknown_stage_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            ContractError,
            "未知のV1 Stage",
        ):
            allowed_next_stages("brief")

    def test_publication_is_terminal(self) -> None:
        self.assertTrue(is_terminal_stage(Stage.PUBLICATION))
        self.assertEqual(
            allowed_next_stages(Stage.PUBLICATION),
            frozenset(),
        )

    def test_non_terminal_stage_is_not_terminal(self) -> None:
        self.assertFalse(is_terminal_stage(Stage.INPUT))


if __name__ == "__main__":
    unittest.main()
