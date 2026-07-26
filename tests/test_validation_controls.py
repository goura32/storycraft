"""Acceptance用workspace検証延期helperの契約。"""
from __future__ import annotations

import sys
from types import ModuleType
import unittest

import storycraft.workspace as workspace_module
from tests.support.validation_controls import (
    defer_workspace_validation,
)


class ValidationControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module_name = (
            "storycraft._validation_controls_probe"
        )
        self.original = (
            workspace_module.validate_workspace_layout
        )
        self.probe = ModuleType(self.module_name)
        self.probe.validate_workspace_layout = (
            self.original
        )
        sys.modules[self.module_name] = self.probe

    def tearDown(self) -> None:
        sys.modules.pop(self.module_name, None)

    def test_validation_aliases_are_restored(
        self,
    ) -> None:
        with defer_workspace_validation():
            self.assertIsNot(
                workspace_module
                .validate_workspace_layout,
                self.original,
            )
            self.assertIsNot(
                self.probe.validate_workspace_layout,
                self.original,
            )

        self.assertIs(
            workspace_module.validate_workspace_layout,
            self.original,
        )
        self.assertIs(
            self.probe.validate_workspace_layout,
            self.original,
        )

    def test_validation_aliases_restore_after_error(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            RuntimeError,
            "test failure",
        ):
            with defer_workspace_validation():
                raise RuntimeError("test failure")

        self.assertIs(
            workspace_module.validate_workspace_layout,
            self.original,
        )
        self.assertIs(
            self.probe.validate_workspace_layout,
            self.original,
        )


if __name__ == "__main__":
    unittest.main()
