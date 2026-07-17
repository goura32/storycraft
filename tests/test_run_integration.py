"""公開コマンド相当の最小再開・step受け入れ契約。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storycraft.series_engine import ContractError, SeriesService


BRIEF = {
    "title": "霧の島の灯",
    "genre": "海洋幻想譚",
    "protagonist": "澪",
    "key_people": "父",
    "want": "父を探す",
    "avoid": "救いのない結末",
    "ending": "島に残る",
    "volumes": 4,
}


class FirstLedgerModel:
    def generate(self, stage: str, context: dict) -> dict:
        if stage != "characters":
            raise AssertionError(stage)
        return {"characters": [{"name": "澪", "role": "主人公", "narrative_function": "父を探す", "fixed_profile": "灯台守", "initial_state": {"goal": "父を探す"}}]}

    def critique(self, stage: str, candidate: dict, context: dict) -> dict:
        return {"issues": []}

    def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
        return candidate


class SeriesEngineStepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="storycraft-step-"))

    def test_step_creates_first_canon_ledger_without_requiring_brief_again(self) -> None:
        service = SeriesService(self.workspace)
        result = service.step(FirstLedgerModel(), BRIEF)
        self.assertFalse(result.completed)
        self.assertEqual(result.volume_count, 0)
        self.assertEqual(service.store.load()["characters"][0]["id"], "char-0001")

    def test_first_step_requires_brief(self) -> None:
        with self.assertRaisesRegex(ContractError, "企画"):
            SeriesService(self.workspace).step(FirstLedgerModel())


if __name__ == "__main__":
    unittest.main()
