"""Storycraft Version 1 のStage遷移契約。"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from storycraft.series_contracts import ContractError
from storycraft.stage_transition import (
    ALLOWED_STAGE_TRANSITIONS,
    advance_run_state,
    allowed_next_stages,
    is_terminal_stage,
    validate_stage_transition,
)
from storycraft.stages import Stage


ROOT = Path(__file__).parent.parent


def load_run_state(relative_path: str) -> dict:
    return json.loads(
        (
            ROOT / "tests/fixtures" / relative_path
        ).read_text(encoding="utf-8")
    )


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

    def test_advance_run_state_updates_stage_and_preserves_scene(self) -> None:
        state = load_run_state(
            "workspace/run-state-running.json"
        )
        state["active_candidate"] = None

        advanced = advance_run_state(
            state,
            next_stage=Stage.SCENE_CONTINUITY,
            next_target={
                "volume_number": 1,
                "chapter_number": 1,
                "scene_number": 1,
            },
            updated_at="2026-07-23T10:46:00Z",
        )

        self.assertEqual(
            advanced["current_stage"],
            "scene_continuity",
        )
        self.assertEqual(
            advanced["active_scene_id"],
            "scene-v01-c001-s001",
        )
        self.assertEqual(
            state["current_stage"],
            "scene_prose",
        )

    def test_scene_commit_to_volume_handoff_clears_scene(self) -> None:
        state = load_run_state(
            "recovery/generation-rename-crash/run-state.json"
        )
        state["pending_commit"] = None

        advanced = advance_run_state(
            state,
            next_stage=Stage.VOLUME_HANDOFF,
            next_target={"volume_number": 1},
            updated_at="2026-07-23T10:46:00Z",
        )

        self.assertEqual(
            advanced["current_stage"],
            "volume_handoff",
        )
        self.assertIsNone(advanced["active_scene_id"])

    def test_scene_card_transition_requires_active_scene(self) -> None:
        state = load_run_state(
            "workspace/run-state-running.json"
        )
        state["current_stage"] = "scene_plan"
        state["active_candidate"] = None
        state["active_scene_id"] = None

        with self.assertRaisesRegex(
            ContractError,
            "active_scene_id",
        ):
            advance_run_state(
                state,
                next_stage=Stage.SCENE_CARD,
                next_target={
                    "volume_number": 1,
                    "chapter_number": 1,
                    "scene_number": 2,
                },
                updated_at="2026-07-23T10:46:00Z",
            )

    def test_scene_card_transition_accepts_new_scene_id(self) -> None:
        state = load_run_state(
            "workspace/run-state-running.json"
        )
        state["current_stage"] = "scene_plan"
        state["active_candidate"] = None
        state["active_scene_id"] = None

        advanced = advance_run_state(
            state,
            next_stage=Stage.SCENE_CARD,
            next_target={
                "volume_number": 1,
                "chapter_number": 1,
                "scene_number": 2,
            },
            active_scene_id="scene-v01-c001-s002",
            updated_at="2026-07-23T10:46:00Z",
        )

        self.assertEqual(
            advanced["active_scene_id"],
            "scene-v01-c001-s002",
        )

    def test_advance_rejects_active_candidate(self) -> None:
        state = load_run_state(
            "workspace/run-state-running.json"
        )

        with self.assertRaisesRegex(
            ContractError,
            "active_candidate",
        ):
            advance_run_state(
                state,
                next_stage=Stage.SCENE_CONTINUITY,
                next_target={
                    "volume_number": 1,
                    "chapter_number": 1,
                    "scene_number": 1,
                },
                updated_at="2026-07-23T10:46:00Z",
            )

    def test_advance_rejects_pending_commit(self) -> None:
        state = load_run_state(
            "recovery/generation-rename-crash/run-state.json"
        )

        with self.assertRaisesRegex(
            ContractError,
            "pending_commit",
        ):
            advance_run_state(
                state,
                next_stage=Stage.VOLUME_HANDOFF,
                next_target={"volume_number": 1},
                updated_at="2026-07-23T10:46:00Z",
            )

    def test_advance_rejects_backward_updated_at(self) -> None:
        state = load_run_state(
            "workspace/run-state-running.json"
        )
        state["active_candidate"] = None

        with self.assertRaisesRegex(
            ContractError,
            "updated_atを後退",
        ):
            advance_run_state(
                state,
                next_stage=Stage.SCENE_CONTINUITY,
                next_target={
                    "volume_number": 1,
                    "chapter_number": 1,
                    "scene_number": 1,
                },
                updated_at="2026-07-23T10:44:00Z",
            )

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
