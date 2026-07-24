"""Scene Commit Recovery Executor試験。"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.scene_commit_recovery_executor import (
    execute_scene_commit_recovery,
)
from storycraft.scene_commit_stage import (
    SceneCommitStageService,
)
from storycraft.series_contracts import ContractError
from storycraft.v1_workflow import V1WorkflowService

from tests.test_scene_commit_stage_v1 import (
    COMMIT_AT,
    create_scene_commit_workspace,
)


class SceneCommitRecoveryExecutorV1Test(
    unittest.TestCase
):
    def test_prepared_recovery_finishes_commit(
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

            recovered = execute_scene_commit_recovery(
                workspace
            )

            self.assertEqual(
                recovered["current_stage"],
                "scene_plan",
            )
            self.assertEqual(
                recovered["current_generation_id"],
                "gen-000002",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertIsNone(
                recovered["active_scene_id"]
            )
            self.assertTrue(
                (
                    workspace
                    / "scenes/scene-v01-c001-s001"
                ).is_dir()
            )
            self.assertTrue(
                (
                    workspace
                    / "generations/gen-000002"
                ).is_dir()
            )

    def test_scene_rename_recovery_finishes_commit(
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
                    raise RuntimeError("scene phase crash")
                return original(state, **kwargs)

            with patch.object(
                service,
                "_save_pending_phase",
                side_effect=save_phase,
            ):
                with self.assertRaises(RuntimeError):
                    service.run(updated_at=COMMIT_AT)

            recovered = execute_scene_commit_recovery(
                workspace
            )

            self.assertEqual(
                recovered["current_generation_id"],
                "gen-000002",
            )
            self.assertTrue(
                (
                    workspace
                    / "generations/gen-000002"
                ).is_dir()
            )

    def test_missing_generation_staging_is_rebuilt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            service = SceneCommitStageService(workspace)
            original_finalize = (
                __import__(
                    "storycraft.scene_commit_stage",
                    fromlist=[
                        "finalize_immutable_directory"
                    ],
                ).finalize_immutable_directory
            )
            calls = 0

            def finalize(**kwargs: object) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError(
                        "generation finalize crash"
                    )
                original_finalize(**kwargs)

            with patch(
                "storycraft.scene_commit_stage."
                "finalize_immutable_directory",
                side_effect=finalize,
            ):
                with self.assertRaises(RuntimeError):
                    service.run(updated_at=COMMIT_AT)

            generation_staging = (
                Path(workspace)
                / "runtime/staging"
                / "generation-gen-000002"
            )
            for child in generation_staging.iterdir():
                child.unlink()
            generation_staging.rmdir()

            recovered = execute_scene_commit_recovery(
                workspace
            )

            self.assertEqual(
                recovered["current_generation_id"],
                "gen-000002",
            )
            self.assertTrue(
                (
                    workspace
                    / "generations/gen-000002"
                ).is_dir()
            )

    def test_invalid_generation_staging_restarts_commit(
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

            recovered = execute_scene_commit_recovery(
                workspace
            )

            self.assertEqual(
                recovered["current_generation_id"],
                "gen-000002",
            )
            orphans = list(
                (
                    Path(workspace)
                    / "runtime/orphans"
                ).glob(
                    "*-generation-gen-000002*"
                )
            )
            self.assertEqual(len(orphans), 1)

    def test_generation_rename_recovery_updates_state(
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
                        "generation phase crash"
                    )
                return original(state, **kwargs)

            with patch.object(
                service,
                "_save_pending_phase",
                side_effect=save_phase,
            ):
                with self.assertRaises(RuntimeError):
                    service.run(updated_at=COMMIT_AT)

            recovered = execute_scene_commit_recovery(
                workspace
            )

            self.assertEqual(
                recovered["current_stage"],
                "scene_plan",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )

    def test_invalid_scene_final_is_manual(
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

            (
                Path(workspace)
                / "scenes/scene-v01-c001-s001/prose.md"
            ).write_text(
                "競合する本文\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ContractError,
                "manual対応",
            ):
                execute_scene_commit_recovery(workspace)

    def test_workflow_recovery_never_creates_model(
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

            model_calls: list[object] = []
            recovered = V1WorkflowService(
                workspace,
                model_factory=lambda: model_calls.append(
                    object()
                ),
            ).step()

            self.assertEqual(
                recovered["current_stage"],
                "scene_plan",
            )
            self.assertEqual(model_calls, [])


if __name__ == "__main__":
    unittest.main()
