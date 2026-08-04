"""Canonical flat settings payload contract."""
from __future__ import annotations

import unittest

from storycraft.series_contracts import ContractError
from storycraft.workspace import _validate_settings


BASE = {
    "provider": "ollama",
    "endpoint": "http://127.0.0.1:11434",
    "model": "test",
    "technical_retry_limit": 1,
    "quality_revision_limit": 1,
    "invalid_response_limit": 3,
    "chapter_per_volume_range": [4, 8],
    "chapter_scene_range": [2, 5],
    "scene_text_char_range": [1200, 2400],
}


class QualityConfigurationTests(unittest.TestCase):
    def test_flat_settings_accepts_positive_quality_revision_limit(self) -> None:
        payload = dict(BASE)
        _validate_settings(payload)

    def test_flat_settings_can_increase_quality_revision_limit(self) -> None:
        payload = {**BASE, "quality_revision_limit": 2}
        _validate_settings(payload)

    def test_flat_settings_rejects_zero_quality_revision_limit(self) -> None:
        with self.assertRaisesRegex(ContractError, "quality_revision_limit"):
            _validate_settings({**BASE, "quality_revision_limit": 0})

    def test_flat_settings_rejects_legacy_nested_yaml_shape(self) -> None:
        with self.assertRaises(ContractError):
            _validate_settings({"llm": {"base_url": "http://localhost:11434"}})


if __name__ == "__main__":
    unittest.main()
