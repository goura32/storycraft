"""仕様どおりの次世代生成フロー受け入れテスト。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from storycraft.series_engine import ContractError, SeriesService


BRIEF = {
    "title": "霧の島の灯",
    "genre": "海洋幻想譚",
    "protagonist": "灯台守の娘・澪",
    "key_people": [
        {"name": "父", "present_position": "灯台守", "initial_relation_to_protagonist": "主人公の父"},
        {"name": "航海士", "present_position": "島を訪れる航海士", "initial_relation_to_protagonist": "主人公の相談相手"},
        {"name": "島医者", "present_position": "島の診療所を営む医師", "initial_relation_to_protagonist": "主人公の幼なじみ"},
    ],
    "want": "父の失踪と灯台の秘密を解く",
    "avoid": "救いのない結末",
    "ending": "澪が父の真実を受け入れ、島に残る",
    "volumes": 4,
    "chapters_per_volume": [1, 1, 1, 1],
}


class FlowModel:
    """工程の入力境界と採番を検証する決定的モデル。"""

    def __init__(self, *, invalid_evidence: bool = False) -> None:
        self.invalid_evidence = invalid_evidence
        self.calls: list[tuple[str, dict]] = []

    def generate(self, stage: str, context: dict) -> dict:
        self.calls.append((stage, context))
        if stage == "characters":
            return {"characters": [{
                "name": "澪", "role": "主人公", "narrative_function": "秘密を解く",
                "fixed_profile": "灯台守の娘", "initial_state": {"current_goal": "父を探す", "current_location": "灯台"},
            }]}
        if stage == "relationships":
            assert context["characters"][0]["id"] == "char-0001"
            return {"relationships": [{
                "character_a_id": "char-0001", "character_b_id": "char-0001",
                "fixed_meaning": "自分自身への疑念", "initial_state": {"current_state": "揺れている"},
            }]}
        if stage == "world":
            return {"entities": [{
                "kind": "場所", "name": "霧の灯台", "stable_fact": "島の北端にある",
                "use_or_access_rule": "灯台守だけが上階へ入れる", "initial_state": {"current_state": "稼働中"},
            }]}
        if stage == "timeline":
            return {"timelines": [{
                "kind": "期限", "description": "嵐まで七日", "sequence": 0, "related_ids": ["char-0001", "entity-0001"],
                "fixed_rule": "嵐の後は船が来ない", "initial_state": {"status": "予定"},
            }]}
        if stage == "threads":
            return {"threads": [{
                "kind": "謎", "importance": "major", "description": "父の失踪理由",
                "author_truth": "父は島を守るために去った", "reader_knowledge": "父は失踪した",
                "character_knowledge": {"char-0001": "父は戻らない"}, "presentation_rule": "直接説明しない",
                "resolution_condition": "真実を受け入れる",
                "initial_state": {"status": "open"},
            }]}
        if stage == "volume_map":
            return {"volumes": [
                {"title": f"第{number}巻", "reader_question": "次巻の問い" if number < 4 else "", "thread_targets": [{"thread_id": "thread-0001", "required_action": ("introduce", "advance", "advance", "resolve")[number - 1]}]}
                for number in range(1, 5)
            ]}
        if stage == "volume_chapters":
            volume = context["volume"]
            return {"chapters": [{
                "number": 1, "title": f"第{volume['number']}章", "purpose": "真実へ進む",
                "start_state": "開始", "end_state": "変化", "scene_count": 1,
            }]}
        if stage == "scene_card":
            thread_actions = context["required_thread_actions"]
            visible_ids = ["char-0001", "entity-0001", "time-0001"]
            if thread_actions:
                visible_ids.append("thread-0001")
            return {
                "scene_id": context["scene_id"], "pov_character_id": "char-0001", "location_id": "entity-0001",
                "start_time_id": "time-0001", "end_time_id": "time-0001", "character_ids": ["char-0001"],
                "purpose": "秘密に近づく", "required_events": ["灯りを見つける"],
                "thread_actions": thread_actions,
                "reader_disclosure": "父の不在", "withheld_information": "父の真実", "presentation_rules": "澪の観察だけで描く", "end_change": "秘密への距離が縮まる",
                "visible_ids": visible_ids,
                "allowed_update_ids": ["thread-0001"] if thread_actions else [],
            }
        if stage == "scene":
            ending = " 澪は島に残る。" if context["is_final_scene"] else ""
            return {"content": f"本文 {context['card']['scene_id']} 灯りが揺れた。{ending}"}
        if stage == "continuity":
            content = context["content"]
            final = context["is_final_scene"]
            updates = []
            if context["card"]["allowed_update_ids"]:
                updates = [{
                    "source_scene_id": context["scene_id"], "id": "thread-0001", "field": "status", "value": "resolved" if final else "in_progress",
                    "evidence": "存在しない根拠" if self.invalid_evidence else "灯りが揺れた。",
                }]
            return {
                "handoff_summary": f"灯りが揺れた。{context['scene_id']}で次へ進む。",
                "state_updates": updates,
            }
        if stage == "volume_summary":
            unresolved = [
                thread["id"] for thread in context["threads"]
                if thread["importance"] == "major" and thread["current_state"]["status"] != "resolved"
            ]
            return {"volume_summary": f"第{context['volume']['number']}巻の要約", "unresolved_thread_ids": unresolved}
        if stage == "closure":
            return {"resolved_ids": ["thread-0001"], "ending_evidence": "島に残る", "ending_authority": BRIEF["ending"]}
        raise AssertionError(f"unexpected stage: {stage}")

    def critique(self, stage: str, candidate: dict, context: dict) -> dict:
        return {"issues": []}

    def revision(self, stage: str, candidate: dict, critique: dict, context: dict) -> dict:
        return candidate


class SeriesEngineFlowAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="storycraft-flow-"))

    def test_run_builds_initial_ledgers_before_chapter_scene_and_prose(self) -> None:
        model = FlowModel()
        result = SeriesService(self.workspace).run(BRIEF, model)

        self.assertTrue(result.completed)
        self.assertEqual(
            [stage for stage, _ in model.calls],
            [
                "characters", "relationships", "world", "timeline", "threads", "volume_map",
                "volume_chapters", "scene_card", "scene", "continuity", "volume_summary",
                "volume_chapters", "scene_card", "scene", "continuity", "volume_summary",
                "volume_chapters", "scene_card", "scene", "continuity", "volume_summary",
                "volume_chapters", "scene_card", "scene", "continuity", "volume_summary", "closure",
            ],
        )
        state = SeriesService(self.workspace).store.load()
        self.assertEqual(state["version"], 5)
        self.assertEqual(state["characters"][0]["id"], "char-0001")
        self.assertEqual(state["relationships"][0]["id"], "rel-0001")
        self.assertEqual(state["world"][0]["id"], "entity-0001")
        self.assertEqual(state["timeline"][0]["id"], "time-0001")
        self.assertEqual(state["threads"][0]["id"], "thread-0001")
        self.assertEqual(state["threads"][0]["initial_state"]["status"], "open")
        self.assertEqual(state["threads"][0]["current_state"]["status"], "resolved")
        self.assertEqual(len(state["volume_summaries"]), 4)
        self.assertEqual(len(result.volume_paths), 4)

    def test_volume_map_must_be_generated_after_canon_ledgers(self) -> None:
        model = FlowModel()
        SeriesService(self.workspace).run(BRIEF, model)
        calls = [stage for stage, _ in model.calls]
        self.assertGreater(calls.index("volume_map"), calls.index("threads"))
        state = SeriesService(self.workspace).store.load()
        self.assertNotIn("plan", state)
        self.assertEqual(state["volume_map"]["volumes"][-1]["reader_question"], "")

    def test_ledger_generation_has_required_prior_local_context_and_prose_has_only_visible_records(self) -> None:
        model = FlowModel()
        SeriesService(self.workspace).run(BRIEF, model)
        calls = {stage: context for stage, context in model.calls}
        self.assertEqual(calls["relationships"]["brief"], BRIEF)
        self.assertIn("relationships", calls["world"])
        self.assertIn("world", calls["timeline"])
        self.assertIn("threads", calls["volume_map"]["ledgers"])
        scene_contexts = [context for stage, context in model.calls if stage == "scene"]
        self.assertTrue(scene_contexts)
        self.assertNotIn("ledgers", scene_contexts[0])
        self.assertEqual(set(scene_contexts[0]["writer_view"]), {"char-0001", "entity-0001", "time-0001", "thread-0001"})

    def test_continuity_rejects_update_without_literal_prose_evidence(self) -> None:
        with self.assertRaisesRegex(ContractError, "本文根拠"):
            SeriesService(self.workspace).run(BRIEF, FlowModel(invalid_evidence=True))

    def test_resume_does_not_regenerate_adopted_initial_ledgers(self) -> None:
        model = FlowModel()
        service = SeriesService(self.workspace)
        interrupted = service.run(BRIEF, model, stop_after_scene="v02-c01-s01")
        self.assertFalse(interrupted.completed)

        resumed = SeriesService(self.workspace).resume(model)
        self.assertTrue(resumed.completed)
        self.assertEqual([stage for stage, _ in model.calls].count("characters"), 1)
        self.assertEqual([stage for stage, _ in model.calls].count("threads"), 1)
    def test_volume_targets_are_assigned_to_exactly_one_scene_card(self) -> None:
        class TwoSceneModel(FlowModel):
            def generate(self, stage: str, context: dict) -> dict:
                if stage == "volume_chapters" and context["volume"]["number"] == 1:
                    return {"chapters": [{
                        "number": 1, "title": "第1章", "purpose": "真実へ進む",
                        "start_state": "開始", "end_state": "変化", "scene_count": 2,
                    }]}
                return super().generate(stage, context)

        model = TwoSceneModel()
        service = SeriesService(self.workspace)
        result = service.run(BRIEF, model)
        self.assertTrue(result.completed)
        cards = service.store.load()["cards"]
        self.assertEqual(cards["v01-c01-s01"]["thread_actions"], [{"thread_id": "thread-0001", "action": "introduce"}])
        self.assertEqual(cards["v01-c01-s02"]["thread_actions"], [])
        contexts = [context for stage, context in model.calls if stage == "scene_card" and context["volume"]["number"] == 1]
        self.assertEqual(contexts[0]["required_thread_actions"], [{"thread_id": "thread-0001", "action": "introduce"}])
        self.assertEqual(contexts[1]["required_thread_actions"], [])

    def test_scene_card_rejects_action_not_assigned_to_its_scene(self) -> None:
        class DuplicateActionModel(FlowModel):
            def generate(self, stage: str, context: dict) -> dict:
                if stage == "volume_chapters" and context["volume"]["number"] == 1:
                    return {"chapters": [{
                        "number": 1, "title": "第1章", "purpose": "真実へ進む",
                        "start_state": "開始", "end_state": "変化", "scene_count": 2,
                    }]}
                value = super().generate(stage, context)
                if stage == "scene_card" and context["scene_id"] == "v01-c01-s02":
                    value["thread_actions"] = [{"thread_id": "thread-0001", "action": "introduce"}]
                    value["visible_ids"].append("thread-0001")
                    value["allowed_update_ids"] = ["thread-0001"]
                return value

        with self.assertRaisesRegex(ContractError, "場面への割当"):
            SeriesService(self.workspace).run(BRIEF, DuplicateActionModel())

    def test_volume_card_actions_reject_targets_outside_its_volume_plan(self) -> None:
        class ExtraActionModel(FlowModel):
            def generate(self, stage: str, context: dict) -> dict:
                value = super().generate(stage, context)
                if stage == "scene_card" and context["volume"]["number"] == 1:
                    value["thread_actions"].append({"thread_id": "thread-0001", "action": "resolve"})
                return value

        with self.assertRaisesRegex(ContractError, "場面への割当|巻配分の対象外"):
            SeriesService(self.workspace).run(BRIEF, ExtraActionModel())
    def test_volume_card_actions_reject_duplicates_across_scene_cards(self) -> None:
        state = {
            "cards": {
                "v01-c01-s01": {"thread_actions": [{"thread_id": "thread-0001", "action": "introduce"}]},
                "v01-c01-s02": {"thread_actions": [{"thread_id": "thread-0001", "action": "introduce"}]},
            }
        }
        volume = {"number": 1, "thread_targets": [{"thread_id": "thread-0001", "required_action": "introduce"}]}
        with self.assertRaisesRegex(ContractError, "重複"):
            SeriesService(self.workspace)._validate_volume_thread_targets(state, volume)


if __name__ == "__main__":
    unittest.main()
