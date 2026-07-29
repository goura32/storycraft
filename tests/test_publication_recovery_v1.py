"""Storycraft V1 completion内Publication確定operationのCrash Recovery試験。"""
from __future__ import annotations

import shutil
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.publication_recovery import (
    execute_publication_recovery,
)
from storycraft.publication_stage import (
    PublicationStageService,
)
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.v1_workflow import V1WorkflowService

from tests.test_publication_stage_v1 import (
    PUBLICATION_AT,
    create_publication_workspace,
    prepared_inputs,
)


class PublicationRecoveryV1Tests(unittest.TestCase):
    def _run_until_crash(
        self,
        workspace: Path,
        *,
        crash: str,
    ) -> None:
        service = PublicationStageService(workspace)

        with (
            patch(
                "storycraft.publication_stage."
                "validate_workspace_layout"
            ),
            patch.object(
                service,
                "_prepare_inputs",
                return_value=prepared_inputs(),
            ),
        ):
            if crash == "prepared":
                with (
                    patch(
                        "storycraft.publication_stage."
                        "finalize_immutable_directory",
                        side_effect=RuntimeError(
                            "prepared crash"
                        ),
                    ),
                    self.assertRaises(RuntimeError),
                ):
                    service.run(
                        updated_at=PUBLICATION_AT
                    )
                return

            original_save = service.state_store.save
            save_calls = 0

            def save(state: dict) -> None:
                nonlocal save_calls
                save_calls += 1

                if (
                    crash == "rename"
                    and save_calls == 2
                ):
                    raise RuntimeError(
                        "rename phase crash"
                    )

                if (
                    crash == "finalized"
                    and save_calls == 3
                ):
                    raise RuntimeError(
                        "completed state crash"
                    )

                original_save(state)

            with (
                patch.object(
                    service.state_store,
                    "save",
                    side_effect=save,
                ),
                self.assertRaises(RuntimeError),
            ):
                service.run(updated_at=PUBLICATION_AT)

    def _recover(
        self,
        workspace: Path,
    ) -> dict:
        with (
            patch.object(
                PublicationStageService,
                "_prepare_inputs",
                return_value=prepared_inputs(),
            ),
            patch(
                "storycraft.publication_recovery."
                "validate_workspace_layout"
            ),
        ):
            return execute_publication_recovery(
                workspace
            )

    def test_prepared_staging_is_finalized(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self._run_until_crash(
                workspace,
                crash="prepared",
            )

            store = RunStateStore(workspace)
            crashed = store.load()
            self.assertEqual(
                crashed["pending_commit"]["phase"],
                "prepared",
            )
            self.assertTrue(
                (
                    workspace
                    / "runtime/staging/"
                    / "publication-pub-000001"
                ).is_dir()
            )
            self.assertFalse(
                (
                    workspace
                    / "publications/pub-000001"
                ).exists()
            )

            counters_path = workspace / "runtime/counters.json"
            counters_after_crash = counters_path.read_bytes()

            recovered = self._recover(workspace)

            self.assertEqual(
                counters_path.read_bytes(),
                counters_after_crash,
            )
            self.assertEqual(
                recovered["status"],
                "completed",
            )
            self.assertEqual(
                recovered["current_stage"],
                "completion",
            )
            self.assertEqual(
                recovered["current_publication_id"],
                "pub-000001",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertTrue(
                (
                    workspace
                    / "publications/pub-000001"
                ).is_dir()
            )
            self.assertFalse(
                (
                    workspace
                    / "runtime/staging/"
                    / "publication-pub-000001"
                ).exists()
            )

    def test_rename_crash_completes_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self._run_until_crash(
                workspace,
                crash="rename",
            )

            crashed = RunStateStore(workspace).load()
            self.assertEqual(
                crashed["pending_commit"]["phase"],
                "prepared",
            )
            self.assertTrue(
                (
                    workspace
                    / "publications/pub-000001"
                ).is_dir()
            )
            self.assertFalse(
                (
                    workspace
                    / "runtime/staging/"
                    / "publication-pub-000001"
                ).exists()
            )

            recovered = self._recover(workspace)

            self.assertEqual(
                recovered["status"],
                "completed",
            )
            self.assertEqual(
                recovered["current_stage"],
                "completion",
            )
            self.assertEqual(
                recovered["current_publication_id"],
                "pub-000001",
            )

    def test_publication_finalized_completes_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self._run_until_crash(
                workspace,
                crash="finalized",
            )

            crashed = RunStateStore(workspace).load()
            self.assertEqual(
                crashed["pending_commit"]["phase"],
                "publication_finalized",
            )

            recovered = self._recover(workspace)

            self.assertEqual(
                recovered["status"],
                "completed",
            )
            self.assertEqual(
                recovered["current_stage"],
                "completion",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )

    def test_invalid_staging_is_manual(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self._run_until_crash(
                workspace,
                crash="prepared",
            )

            (
                workspace
                / "runtime/staging/"
                / "publication-pub-000001/v01.md"
            ).write_text(
                "競合する本文\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ContractError,
                "manual対応",
            ):
                self._recover(workspace)

    def test_invalid_final_is_manual(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self._run_until_crash(
                workspace,
                crash="rename",
            )

            (
                workspace
                / "publications/pub-000001/v01.md"
            ).write_text(
                "競合する本文\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ContractError,
                "manual対応",
            ):
                self._recover(workspace)

    def test_staging_and_final_conflict_is_manual(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self._run_until_crash(
                workspace,
                crash="prepared",
            )

            staging = (
                workspace
                / "runtime/staging/"
                / "publication-pub-000001"
            )
            final = (
                workspace
                / "publications/pub-000001"
            )
            shutil.copytree(staging, final)

            with self.assertRaisesRegex(
                ContractError,
                "manual対応",
            ):
                self._recover(workspace)

    def test_workflow_recovery_never_creates_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self._run_until_crash(
                workspace,
                crash="prepared",
            )

            model_calls: list[object] = []

            with (
                patch.object(
                    PublicationStageService,
                    "_prepare_inputs",
                    return_value=prepared_inputs(),
                ),
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.publication_recovery."
                    "validate_workspace_layout"
                ),
            ):
                recovered = V1WorkflowService(
                    workspace,
                    model_factory=lambda: (
                        model_calls.append(object())
                    ),
                ).step()

            self.assertEqual(
                recovered["status"],
                "completed",
            )
            self.assertEqual(
                recovered["current_stage"],
                "completion",
            )
            self.assertEqual(
                recovered["current_publication_id"],
                "pub-000001",
            )
            self.assertEqual(model_calls, [])


if __name__ == "__main__":
    unittest.main()
