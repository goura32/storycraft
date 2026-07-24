"""Storycraft Version 1 Scene Commit Recovery分類。"""
from __future__ import annotations

import unittest

from storycraft.scene_commit_recovery import (
    CurrentGenerationRelation,
    DirectoryCondition,
    SceneCommitRecoveryAction,
    SceneCommitRecoverySnapshot,
    classify_scene_commit_recovery,
)


ABSENT = DirectoryCondition.ABSENT
COMPLETE = DirectoryCondition.COMPLETE
INVALID = DirectoryCondition.INVALID
PARENT = CurrentGenerationRelation.PARENT
EXPECTED = CurrentGenerationRelation.EXPECTED
OTHER = CurrentGenerationRelation.OTHER


def snapshot(
    *,
    phase: str = "prepared",
    current: CurrentGenerationRelation = PARENT,
    scene_staging: DirectoryCondition = ABSENT,
    generation_staging: DirectoryCondition = ABSENT,
    scene_final: DirectoryCondition = ABSENT,
    generation_final: DirectoryCondition = ABSENT,
    final_state_matches: bool = False,
) -> SceneCommitRecoverySnapshot:
    return SceneCommitRecoverySnapshot(
        phase=phase,
        current_generation_relation=current,
        scene_staging=scene_staging,
        generation_staging=generation_staging,
        scene_final=scene_final,
        generation_final=generation_final,
        final_state_matches=final_state_matches,
    )


class SceneCommitRecoveryV1Test(unittest.TestCase):
    def test_complete_staging_resumes_scene_finalize(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                scene_staging=COMPLETE,
                generation_staging=COMPLETE,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.FINALIZE_SCENE,
        )

    def test_incomplete_staging_restarts_commit(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                scene_staging=INVALID,
                generation_staging=COMPLETE,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.RESTART_COMMIT,
        )

    def test_complete_generation_staging_is_finalized(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                phase="scene_finalized",
                scene_final=COMPLETE,
                generation_staging=COMPLETE,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.FINALIZE_GENERATION,
        )

    def test_missing_generation_staging_is_rebuilt(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                phase="scene_finalized",
                scene_final=COMPLETE,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.REBUILD_GENERATION,
        )

    def test_both_finals_complete_state_update(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                phase="prepared",
                scene_final=COMPLETE,
                generation_final=COMPLETE,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.COMPLETE_STATE,
        )

    def test_expected_pointer_clears_matching_stale_pending(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                phase="generation_finalized",
                current=EXPECTED,
                scene_final=COMPLETE,
                generation_final=COMPLETE,
                final_state_matches=True,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.CLEAR_STALE_PENDING,
        )

    def test_expected_pointer_mismatch_is_manual(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                phase="generation_finalized",
                current=EXPECTED,
                scene_final=COMPLETE,
                generation_final=COMPLETE,
                final_state_matches=False,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.MANUAL,
        )

    def test_generation_without_scene_is_manual(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                generation_final=COMPLETE,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.MANUAL,
        )

    def test_invalid_final_is_manual(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                scene_final=INVALID,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.MANUAL,
        )

    def test_unrelated_current_generation_is_manual(
        self,
    ) -> None:
        action = classify_scene_commit_recovery(
            snapshot(
                current=OTHER,
                scene_final=COMPLETE,
                generation_final=COMPLETE,
            )
        )

        self.assertIs(
            action,
            SceneCommitRecoveryAction.MANUAL,
        )


if __name__ == "__main__":
    unittest.main()
