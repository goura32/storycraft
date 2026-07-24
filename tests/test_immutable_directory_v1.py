from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.immutable_directory import (
    finalize_immutable_directory,
)
from storycraft.series_contracts import ContractError


class ImmutableDirectoryV1Test(unittest.TestCase):
    def test_validates_moves_and_fsyncs_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            final = root / "final"
            staging.mkdir()
            (staging / "artifact.txt").write_text(
                "complete\n",
                encoding="utf-8",
            )

            validated: list[Path] = []

            def validator(path: Path) -> None:
                validated.append(path)
                self.assertTrue(path.is_dir())
                self.assertEqual(
                    (path / "artifact.txt").read_text(
                        encoding="utf-8"
                    ),
                    "complete\n",
                )

            with patch(
                "storycraft.immutable_directory."
                "fsync_directory"
            ) as fsync:
                finalize_immutable_directory(
                    staging=staging,
                    final=final,
                    validator=validator,
                )

            self.assertFalse(staging.exists())
            self.assertTrue(final.is_dir())
            self.assertEqual(
                validated,
                [staging, final],
            )
            fsync.assert_called_once_with(root)

    def test_missing_staging_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            with self.assertRaisesRegex(
                ContractError,
                "staging directory",
            ):
                finalize_immutable_directory(
                    staging=root / "missing",
                    final=root / "final",
                    validator=lambda path: None,
                )

    def test_existing_final_is_never_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            final = root / "final"
            staging.mkdir()
            final.mkdir()
            (staging / "value.txt").write_text(
                "staging\n",
                encoding="utf-8",
            )
            (final / "value.txt").write_text(
                "final\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ContractError,
                "既に存在",
            ):
                finalize_immutable_directory(
                    staging=staging,
                    final=final,
                    validator=lambda path: None,
                )

            self.assertTrue(staging.is_dir())
            self.assertEqual(
                (final / "value.txt").read_text(
                    encoding="utf-8"
                ),
                "final\n",
            )

    def test_pre_finalize_validation_failure_keeps_staging(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            final = root / "final"
            staging.mkdir()

            def validator(path: Path) -> None:
                raise ContractError("artifact is incomplete")

            with self.assertRaisesRegex(
                ContractError,
                "incomplete",
            ):
                finalize_immutable_directory(
                    staging=staging,
                    final=final,
                    validator=validator,
                )

            self.assertTrue(staging.is_dir())
            self.assertFalse(final.exists())

    def test_post_finalize_failure_does_not_roll_back(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            final = root / "final"
            staging.mkdir()
            calls = 0

            def validator(path: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise ContractError(
                        "final validation failed"
                    )

            with self.assertRaisesRegex(
                ContractError,
                "final validation failed",
            ):
                finalize_immutable_directory(
                    staging=staging,
                    final=final,
                    validator=validator,
                )

            self.assertFalse(staging.exists())
            self.assertTrue(final.is_dir())
            self.assertEqual(calls, 2)

    def test_rename_failure_keeps_staging(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            final = root / "final"
            staging.mkdir()

            with patch(
                "storycraft.immutable_directory.os.rename",
                side_effect=OSError("rename failed"),
            ):
                with self.assertRaisesRegex(
                    ContractError,
                    "finalizeできません",
                ):
                    finalize_immutable_directory(
                        staging=staging,
                        final=final,
                        validator=lambda path: None,
                    )

            self.assertTrue(staging.is_dir())
            self.assertFalse(final.exists())


if __name__ == "__main__":
    unittest.main()
