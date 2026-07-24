"""Scene Commit Recovery filesystem Inspector試験。"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.scene_commit_recovery import (
    CurrentGenerationRelation,
    DirectoryCondition,
    SceneCommitRecoveryAction,
    classify_scene_commit_recovery,
    inspect_scene_commit_recovery,
)
from storycraft.scene_commit_stage import (
    SceneCommitStageService,
)

from tests.test_scene_commit_stage_v1 import (
    COMMIT_AT,
    create_scene_commit_workspace,
)


class SceneCommitRecoveryInspectorV1Test(
    unittest.TestCase
):
    def test_prepared_with_complete_staging(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            service = SceneCommitStageService(workspace)

            with patch(
                "storycraft.scene_commit_stage."
                "finalize_immutable_directory",
                side_effect=RuntimeError(
                    "crash after prepared"
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "after prepared",
                ):
                    service.run(updated_at=COMMIT_AT)

            state = service.state_store.load()
            inspection = inspect_scene_commit_recovery(
                workspace,
                state,
            )

            self.assertEqual(
                inspection.snapshot.phase,
                "prepared",
            )
            self.assertIs(
                inspection.snapshot.
                current_generation_relation,
                CurrentGenerationRelation.PARENT,
            )
            self.assertIs(
                inspection.snapshot.scene_staging,
                DirectoryCondition.COMPLETE,
            )
            self.assertIs(
                inspection.snapshot.generation_staging,
                DirectoryCondition.COMPLETE,
            )
            self.assertIs(
                inspection.snapshot.scene_final,
                DirectoryCondition.ABSENT,
            )
            self.assertIs(
                classify_scene_commit_recovery(
                    inspection.snapshot
                ),
                SceneCommitRecoveryAction.FINALIZE_SCENE,
            )

    def test_scene_rename_before_phase_update(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            service = SceneCommitStageService(workspace)
            original = service._save_pending_phase
            calls = 0

            def save_phase(state: dict, **kwargs: object):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError(
                        "crash before scene phase save"
                    )
                return original(state, **kwargs)

            with patch.object(
                service,
                "_save_pending_phase",
                side_effect=save_phase,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "scene phase",
                ):
                    service.run(updated_at=COMMIT_AT)

            state = service.state_store.load()
            inspection = inspect_scene_commit_recovery(
                workspace,
                state,
            )

            self.assertEqual(
                inspection.snapshot.phase,
                "prepared",
            )
            self.assertIs(
                inspection.snapshot.scene_final,
                DirectoryCondition.COMPLETE,
            )
            self.assertIs(
                inspection.snapshot.scene_staging,
                DirectoryCondition.ABSENT,
            )
            self.assertIs(
                inspection.snapshot.generation_staging,
                DirectoryCondition.COMPLETE,
            )
            self.assertIs(
                classify_scene_commit_recovery(
                    inspection.snapshot
                ),
                SceneCommitRecoveryAction.
                FINALIZE_GENERATION,
            )

    def test_generation_rename_before_phase_update(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            service = SceneCommitStageService(workspace)
            original = service._save_pending_phase
            calls = 0

            def save_phase(state: dict, **kwargs: object):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise RuntimeError(
                        "crash before generation phase save"
                    )
                return original(state, **kwargs)

            with patch.object(
                service,
                "_save_pending_phase",
                side_effect=save_phase,
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "generation phase",
                ):
                    service.run(updated_at=COMMIT_AT)

            state = service.state_store.load()
            inspection = inspect_scene_commit_recovery(
                workspace,
                state,
            )

            self.assertEqual(
                inspection.snapshot.phase,
                "scene_finalized",
            )
            self.assertIs(
                inspection.snapshot.scene_final,
                DirectoryCondition.COMPLETE,
            )
            self.assertIs(
                inspection.snapshot.generation_final,
                DirectoryCondition.COMPLETE,
            )
            self.assertIs(
                classify_scene_commit_recovery(
                    inspection.snapshot
                ),
                SceneCommitRecoveryAction.COMPLETE_STATE,
            )

    def test_invalid_scene_final_is_reported(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            service = SceneCommitStageService(workspace)
            original = service._save_pending_phase
            calls = 0

            def save_phase(state: dict, **kwargs: object):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("crash")
                return original(state, **kwargs)

            with patch.object(
                service,
                "_save_pending_phase",
                side_effect=save_phase,
            ):
                with self.assertRaises(RuntimeError):
                    service.run(updated_at=COMMIT_AT)

            prose = (
                workspace
                / "scenes/scene-v01-c001-s001/prose.md"
            )
            prose.write_text(
                "改変された本文\n",
                encoding="utf-8",
            )

            state = service.state_store.load()
            inspection = inspect_scene_commit_recovery(
                workspace,
                state,
            )

            self.assertIs(
                inspection.snapshot.scene_final,
                DirectoryCondition.INVALID,
            )
            self.assertIsNotNone(
                inspection.scene_final_error
            )
            self.assertIs(
                classify_scene_commit_recovery(
                    inspection.snapshot
                ),
                SceneCommitRecoveryAction.MANUAL,
            )

    def test_incomplete_staging_requests_restart(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            service = SceneCommitStageService(workspace)

            with patch(
                "storycraft.scene_commit_stage."
                "finalize_immutable_directory",
                side_effect=RuntimeError("crash"),
            ):
                with self.assertRaises(RuntimeError):
                    service.run(updated_at=COMMIT_AT)

            generation_staging = (
                Path(workspace)
                / "runtime/staging"
                / "generation-gen-000002"
            )
            (
                generation_staging / "state.json"
            ).unlink()

            state = service.state_store.load()
            inspection = inspect_scene_commit_recovery(
                workspace,
                state,
            )

            self.assertIs(
                inspection.snapshot.scene_staging,
                DirectoryCondition.COMPLETE,
            )
            self.assertIs(
                inspection.snapshot.generation_staging,
                DirectoryCondition.INVALID,
            )
            self.assertIs(
                classify_scene_commit_recovery(
                    inspection.snapshot
                ),
                SceneCommitRecoveryAction.RESTART_COMMIT,
            )


if __name__ == "__main__":
    unittest.main()
