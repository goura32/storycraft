from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from storycraft.series_contracts import ContractError
from storycraft.workspace_lock import workspace_lock


class WorkspaceLockV1Test(unittest.TestCase):
    def create_workspace(
        self,
        temporary: str,
    ) -> Path:
        workspace = Path(temporary) / "novel"
        runtime = workspace / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "lock").touch()
        return workspace

    def test_lock_can_be_reacquired_after_release(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)

            with workspace_lock(workspace):
                self.assertTrue(
                    (workspace / "runtime/lock").is_file()
                )

            with workspace_lock(workspace):
                pass

    def test_second_lock_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)

            with workspace_lock(workspace):
                with self.assertRaisesRegex(
                    ContractError,
                    "別の実行で使用中",
                ):
                    with workspace_lock(workspace):
                        pass

    def test_exception_releases_lock(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)

            with self.assertRaisesRegex(
                RuntimeError,
                "test failure",
            ):
                with workspace_lock(workspace):
                    raise RuntimeError("test failure")

            with workspace_lock(workspace):
                pass

    def test_missing_lock_is_not_created(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary) / "novel"
            (workspace / "runtime").mkdir(parents=True)

            with self.assertRaisesRegex(
                ContractError,
                "lockがありません",
            ):
                with workspace_lock(workspace):
                    pass

            self.assertFalse(
                (workspace / "runtime/lock").exists()
            )


if __name__ == "__main__":
    unittest.main()
