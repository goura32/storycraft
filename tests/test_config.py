"""設定の品質ゲート契約。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storycraft.config import Settings
from storycraft.series_contracts import ContractError


class QualityConfigurationTests(unittest.TestCase):
    def test_default_uses_one_critique_revision_pass(self) -> None:
        self.assertEqual(Settings.load().quality["max_critique_passes"], 1)

    def test_config_can_increase_critique_revision_pass_limit(self) -> None:
        config = Path(tempfile.mkdtemp()) / "storycraft.yaml"
        config.write_text("quality:\n  max_critique_passes: 2\n", encoding="utf-8")

        self.assertEqual(Settings.load(str(config)).quality["max_critique_passes"], 2)

    def test_config_rejects_non_positive_critique_revision_pass_limit(self) -> None:
        config = Path(tempfile.mkdtemp()) / "storycraft.yaml"
        config.write_text("quality:\n  max_critique_passes: 0\n", encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "1以上"):
            Settings.load(str(config))
