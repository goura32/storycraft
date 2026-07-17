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
    "key_people": "父・航海士・島医者",
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
        if stage == "plan":
            return {"volumes": [
                {"title": f"第{number}巻", "change": f"第{number}巻の変化",
                 "leaves_question": "次巻の問い" if number < 4 else ""}
                for number in range(1, 5)
            ]}
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
                "kind": "期限", "description": "嵐まで七日", "related_ids": ["char-0001", "entity-0001"],
                "fixed_rule": "嵐の後は船が来ない", "initial_state": {"status": "予定"},
            }]}
        if stage == "threads":
            return {"threads": [{
                "kind": "謎", "importance": "major", "description": "父の失踪理由",
                "author_truth": "父は島を守るために去った", "reader_knowledge": "父は失踪した",
                "character_knowledge": {"char-0001": "父は戻らない"}, "presentation_rule": "直接説明しない",
                "introduce_by": "v01", "resolve_by": "v04", "resolution_condition": "真実を受け入れる",
                "traceability": {"brief_want": BRIEF["want"], "brief_ending": BRIEF["ending"], "leaves_question": "次巻の問い"},
                "initial_state": {"status": "open"},
            }]}
        if stage == "volume_chapters":
            volume = context["volume"]
            return {"chapters": [{
                "number": 1, "title": f"第{volume['number']}章", "purpose": "真実へ進む",
                "start_state": "開始", "end_state": "変化", "scene_count": 1,
            }]}
        if stage == "scene_card":
            return {
                "scene_id": context["scene_id"], "pov_character_id": "char-0001", "location_id": "entity-0001",
                "start_time_id": "time-0001", "end_time_id": "time-0001", "character_ids": ["char-0001"],
                "purpose": "秘密に近づく", "required_events": ["灯りを見つける"],
                "thread_actions": [{"thread_id": "thread-0001", "action": "resolve" if context["is_final_scene"] else "advance"}],
                "reader_disclosure": "父の不在", "withheld_information": "父の真実", "presentation_rules": "澪の観察だけで描く", "end_change": "秘密への距離が縮まる",
                "visible_ids": ["char-0001", "entity-0001", "thread-0001"],
                "allowed_update_ids": ["thread-0001"],
            }
        if stage == "scene":
            ending = " 澪は島に残る。" if context["is_final_scene"] else ""
            return {"content": f"本文 {context['card']['scene_id']} 灯りが揺れた。{ending}"}
        if stage == "continuity":
            content = context["content"]
            final = context["is_final_scene"]
            return {
                "handoff_summary": f"灯りが揺れた。{context['scene_id']}で次へ進む。",
                "state_updates": [{
                    "source_scene_id": context["scene_id"], "id": "thread-0001", "field": "status", "value": "resolved" if final else "in_progress",
                    "evidence": "存在しない根拠" if self.invalid_evidence else "灯りが揺れた。",
                }],
            }
        if stage == "volume_summary":
            return {"volume_summary": f"第{context['volume']['number']}巻の要約", "unresolved_thread_ids": []}
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
                "plan", "characters", "relationships", "world", "timeline", "threads",
                "volume_chapters", "scene_card", "scene", "continuity", "volume_summary",
                "volume_chapters", "scene_card", "scene", "continuity", "volume_summary",
                "volume_chapters", "scene_card", "scene", "continuity", "volume_summary",
                "volume_chapters", "scene_card", "scene", "continuity", "volume_summary", "closure",
            ],
        )
        state = SeriesService(self.workspace).store.load()
        self.assertEqual(state["version"], 3)
        self.assertEqual(state["characters"][0]["id"], "char-0001")
        self.assertEqual(state["relationships"][0]["id"], "rel-0001")
        self.assertEqual(state["world"][0]["id"], "entity-0001")
        self.assertEqual(state["timeline"][0]["id"], "time-0001")
        self.assertEqual(state["threads"][0]["id"], "thread-0001")
        self.assertEqual(state["threads"][0]["initial_state"]["status"], "open")
        self.assertEqual(state["threads"][0]["current_state"]["status"], "resolved")
        self.assertEqual(len(state["volume_summaries"]), 4)
        self.assertEqual(len(result.volume_paths), 4)

    def test_threads_require_major_traceability_and_closure_uses_final_scene_ending_authority(self) -> None:
        class UntraceableThreadModel(FlowModel):
            def generate(self, stage: str, context: dict) -> dict:
                value = super().generate(stage, context)
                if stage == "threads":
                    value["threads"][0].pop("traceability", None)
                return value

        with self.assertRaisesRegex(ContractError, "追跡"):
            SeriesService(self.workspace).run(BRIEF, UntraceableThreadModel())

    def test_ledger_generation_has_required_prior_local_context_and_prose_has_only_visible_records(self) -> None:
        model = FlowModel()
        SeriesService(self.workspace).run(BRIEF, model)
        calls = {stage: context for stage, context in model.calls}
        self.assertEqual(calls["relationships"]["brief"], BRIEF)
        self.assertIn("relationships", calls["world"])
        self.assertIn("world", calls["timeline"])
        self.assertIn("timeline", calls["threads"])
        scene_contexts = [context for stage, context in model.calls if stage == "scene"]
        self.assertTrue(scene_contexts)
        self.assertNotIn("ledgers", scene_contexts[0])
        self.assertEqual(set(scene_contexts[0]["writer_view"]), {"char-0001", "entity-0001", "thread-0001"})

    def test_continuity_rejects_update_without_literal_prose_evidence(self) -> None:
        with self.assertRaisesRegex(ContractError, "本文根拠"):
            SeriesService(self.workspace).run(BRIEF, FlowModel(invalid_evidence=True))

    def test_plan_rejects_overlong_detail_dump(self) -> None:
        plan = FlowModel().generate("plan", {})
        plan["volumes"][0]["change"] = "調査の詳細を追加する。" * 30
        with self.assertRaisesRegex(ContractError, "change は240文字以内"):
            SeriesService._validate_plan(plan, BRIEF)

    def test_plan_rejects_generated_number_or_ending_condition(self) -> None:
        plan = FlowModel().generate("plan", {})
        plan["volumes"][-1]["number"] = 4
        with self.assertRaisesRegex(ContractError, "採番または結末条件"):
            SeriesService._validate_plan(plan, BRIEF)

    def test_plan_rejects_hangul_left_by_revision(self) -> None:
        plan = FlowModel().generate("plan", {})
        plan["volumes"][0]["leaves_question"] = "手がかりを重点적으로探す。"
        with self.assertRaisesRegex(ContractError, "ハングル字形"):
            SeriesService._validate_plan(plan, BRIEF)

    def test_resume_does_not_regenerate_adopted_initial_ledgers(self) -> None:
        model = FlowModel()
        service = SeriesService(self.workspace)
        interrupted = service.run(BRIEF, model, stop_after_scene="v02-c01-s01")
        self.assertFalse(interrupted.completed)

        resumed = SeriesService(self.workspace).resume(model)
        self.assertTrue(resumed.completed)
        self.assertEqual([stage for stage, _ in model.calls].count("characters"), 1)
        self.assertEqual([stage for stage, _ in model.calls].count("threads"), 1)


if __name__ == "__main__":
    unittest.main()
