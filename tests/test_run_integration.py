"""公開コマンド相当の最小再開・step受け入れ契約。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storycraft.nextgen import ContractError, SeriesService


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


class PlanModel:
    def generate(self, stage: str, context: dict) -> dict:
        if stage != "plan":
            raise AssertionError(stage)
        return {"volumes": [
            {"number": number, "title": f"第{number}巻", "change": "変化", "leaves_question": "問い" if number < 4 else "", "ending_condition": "島に残る" if number == 4 else ""}
            for number in range(1, 5)
        ]}

    def critique(self, stage: str, candidate: dict, context: dict) -> dict:
        return {"issues": []}

    def revise(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
        return candidate


class NextGenerationStepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="storycraft-step-"))

    def test_step_creates_then_adopts_plan_without_requiring_brief_again(self) -> None:
        service = SeriesService(self.workspace)
        result = service.step(PlanModel(), BRIEF)
        self.assertFalse(result.completed)
        self.assertEqual(result.volume_count, 4)
        self.assertIsNotNone(service.store.load()["plan"])

    def test_first_step_requires_brief(self) -> None:
        with self.assertRaisesRegex(ContractError, "企画"):
            SeriesService(self.workspace).step(PlanModel())


if __name__ == "__main__":
    unittest.main()
