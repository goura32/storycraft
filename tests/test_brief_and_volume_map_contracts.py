"""keywords起点briefとCanon後volume_mapの公開契約。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storycraft.series_engine import ContractError, SeriesService


GENERATED_BRIEF = {
    "title": "霧の島の灯",
    "genre": "海洋幻想譚",
    "protagonist": "澪",
    "key_people": "父",
    "want": "父の暗号と島の秘密をたどる",
    "avoid": "救いのない結末",
    "ending": "澪が自らの居場所を選ぶ",
    "volumes": 4,
}


class KeywordBriefModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def generate(self, stage: str, context: dict) -> dict:
        self.calls.append((stage, context))
        if stage == "brief":
            return GENERATED_BRIEF
        raise AssertionError(stage)

    def critique(self, stage: str, candidate: dict, context: dict) -> dict:
        return {"issues": []}

    def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
        return candidate


class BriefAndVolumeMapContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="storycraft-keywords-"))

    def test_first_step_from_keywords_generates_and_adopts_a_brief(self) -> None:
        model = KeywordBriefModel()
        service = SeriesService(self.workspace)

        result = service.step(model, keywords=["霧の島", "灯台", "女性向け幻想譚", "4巻"])

        self.assertFalse(result.completed)
        state = service.store.load()
        self.assertEqual(state["brief"], GENERATED_BRIEF)
        self.assertEqual(state["keywords"], ["霧の島", "灯台", "女性向け幻想譚", "4巻"])
        self.assertEqual(model.calls, [("brief", {"keywords": state["keywords"]})])

    def test_volume_map_requires_existing_thread_ids_and_a_complete_major_thread_arc(self) -> None:
        valid = {
            "volumes": [
                {"title": "第1巻", "reader_question": "父の暗号は何を示すのか。", "thread_targets": [{"thread_id": "thread-0001", "required_action": "introduce"}]},
                {"title": "第2巻", "reader_question": "島の秘密はどこへつながるのか。", "thread_targets": [{"thread_id": "thread-0001", "required_action": "advance"}]},
                {"title": "第3巻", "reader_question": "真実を知れば何を選ぶのか。", "thread_targets": [{"thread_id": "thread-0001", "required_action": "advance"}]},
                {"title": "第4巻", "reader_question": "", "thread_targets": [{"thread_id": "thread-0001", "required_action": "resolve"}]},
            ]
        }
        threads = [{"id": "thread-0001", "importance": "major"}]

        SeriesService._validate_volume_map(valid, GENERATED_BRIEF, threads)

        invalid = {"volumes": [dict(volume) for volume in valid["volumes"]]}
        invalid["volumes"][0]["thread_targets"] = [{"thread_id": "thread-9999", "required_action": "introduce"}]
        with self.assertRaisesRegex(ContractError, "未知の主要項目"):
            SeriesService._validate_volume_map(invalid, GENERATED_BRIEF, threads)


if __name__ == "__main__":
    unittest.main()
