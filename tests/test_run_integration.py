"""次世代Storycraftの最小受け入れテスト。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storycraft.nextgen import ContractError, SeriesService


BRIEF = {
    "title": "霧の島の灯",
    "premise": "灯台守の娘が父の秘密を解く物語",
    "ending": "娘が父の真実を受け入れ、島に残る",
    "volumes": 4,
    "major_questions": ["父はなぜ灯台を去ったのか"],
}


class DeterministicModel:
    """受け入れテストだけで使う、決定的な生成・批評・修正モデル。"""

    def __init__(self, *, invalid_update: bool = False) -> None:
        self.invalid_update = invalid_update
        self.contexts: list[dict] = []
        self.plan_calls = 0

    def generate(self, stage: str, context: dict) -> dict:
        if stage == "plan":
            self.plan_calls += 1
            return {
                "volumes": [
                    {
                        "number": number,
                        "title": f"第{number}巻",
                        "chapters": [{"number": 1, "title": "灯の章"}],
                        "change": f"第{number}巻の変化",
                        "leaves_question": "次の灯は誰が守るのか" if number < 4 else "",
                    }
                    for number in range(1, 5)
                ]
            }
        if stage == "scene_card":
            return {
                "scene_id": context["scene_id"],
                "visible_thread_ids": ["question-01"],
                "allowed_update_ids": ["question-01"],
            }
        if stage == "scene":
            self.contexts.append(context)
            scene_id = context["card"]["scene_id"]
            update_id = "forbidden" if self.invalid_update else "question-01"
            final_scene = scene_id == "v04-c01-s02"
            return {
                "content": f"本文 {scene_id}",
                "handoff_summary": f"引継ぎ {scene_id}",
                "state_updates": [
                    {
                        "id": update_id,
                        "status": "resolved" if final_scene else "in_progress",
                    }
                ],
            }
        if stage == "closure":
            return {"resolved_ids": ["question-01"], "ending_reached": True}
        raise AssertionError(f"unexpected stage: {stage}")

    def critique(self, stage: str, candidate: dict, context: dict) -> dict:
        return {"issues": []}

    def revise(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
        return candidate


class NextGenerationAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="storycraft-nextgen-"))
        self.service = SeriesService(self.workspace)

    def test_run_completes_requested_volumes_and_writes_complete_markdown(self) -> None:
        result = self.service.run(BRIEF, DeterministicModel())

        self.assertTrue(result.completed)
        self.assertEqual(result.volume_count, 4)
        self.assertEqual(
            [path.name for path in result.volume_paths],
            ["volume-01.md", "volume-02.md", "volume-03.md", "volume-04.md"],
        )
        self.assertTrue(result.series_path.exists())
        bodies = [path.read_text(encoding="utf-8") for path in result.volume_paths]
        self.assertTrue(all("本文" in body for body in bodies))
        self.assertEqual(len(bodies), len(set(bodies)))
        self.assertTrue(result.closure["ending_reached"])
        self.assertEqual(result.closure["resolved_ids"], ["question-01"])

    def test_scene_applies_only_allowed_updates_and_exposes_updated_state(self) -> None:
        model = DeterministicModel()
        self.service.run(BRIEF, model)

        second_scene_context = next(
            context
            for context in model.contexts
            if context["card"]["scene_id"] == "v01-c01-s02"
        )
        self.assertEqual(second_scene_context["threads"]["question-01"]["status"], "in_progress")

        with self.assertRaises(ContractError):
            SeriesService(self.workspace / "invalid").run(BRIEF, DeterministicModel(invalid_update=True))

    def test_resume_continues_from_saved_adopted_state_without_repeating_brief(self) -> None:
        model = DeterministicModel()
        interrupted = self.service.run(BRIEF, model, stop_after_scene="v02-c01-s01")
        self.assertFalse(interrupted.completed)
        self.assertTrue((self.workspace / "state.json").exists())

        resumed = SeriesService(self.workspace).resume(model)
        self.assertTrue(resumed.completed)
        self.assertEqual(model.plan_calls, 1)
        self.assertTrue(resumed.series_path.exists())


if __name__ == "__main__":
    unittest.main()
