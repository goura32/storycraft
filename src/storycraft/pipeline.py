"""パイプライン実行。§3 生成の流れ・§5 依頼単位・§10 コマンドラインに従う。

ステージ: plan, characters, world, timeline, threads, volume-plan,
          scene-cards, scenes, volume-summary, closure-check, output
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from .config import Settings
from .diversity import build_diversity_note
from .ids import IDSequencer
from .llm import LLMClient
from .log import logger
from .output import write_output
from .prompts import (
    closure_check, improve, plan_series, characters, world_ledger,
    timeline_ledger, threads_ledger, volume_chapters, scene_cards, scene_write,
    volume_summary,
)
from .state import State
from .validation import validate_scene_response

BASE_SEED = 1000


def _parse_json(rec_content: str) -> dict:
    text = rec_content.strip()
    # コードブロック (```json ... ```) を除去
    if text.startswith("```"):
        # 最初の改行までと最後の ``` を削る
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
    # 前後に余計な文字があれば最初の { と最後の } で挟む
    if not text.startswith("{"):
        start = text.find("{")
        if start >= 0:
            text = text[start:]
    if not text.endswith("}"):
        end = text.rfind("}")
        if end >= 0:
            text = text[: end + 1]
    return json.loads(text)


STAGES = [
    "plan", "characters", "world", "timeline", "threads",
    "volume-plan", "scene-cards", "scenes", "volume-summary",
    "closure-check", "output",
]


class Pipeline:
    def __init__(self, settings: Settings, state: State, llm: LLMClient,
                 sequencer: IDSequencer, base_seed: int = BASE_SEED):
        self.s = settings
        self.state = state
        self.llm = llm
        self.seq = sequencer
        self.base_seed = base_seed
        self.attempt = 0

    # ---- 共通: LLM呼び出し + 生データ保存 ----
    def _ask(self, kind: str, phase: str, ref: str, sys_p: str, user_p: str,
             schema: str, validator=None, allowed_ids: set | None = None,
             max_attempts: int | None = None) -> dict | None:
        if max_attempts is None:
            max_attempts = self.s.retry.get("max_attempts", 4)
        full_user = f"{user_p}\n\n【この呼び出し専用JSON Schema】\n{schema}\n\n必ずJSONオブジェクトだけを返してください。"
        for i in range(max_attempts):
            self.attempt += 1
            seed = self.base_seed + self.attempt
            meta = {"__kind": kind, "__phase": phase, "__ref": ref, "__attempt": i + 1}
            messages = [{"role": "system", "content": sys_p}, meta, {"role": "user", "content": full_user}]
            logger.info("[%s] %s 試行%d (seed=%d)", phase, ref, i + 1, seed)
            rec = self.llm.call_once(messages, {"type": "json_object"}, seed)
            self.llm.save_raw(rec, messages)
            if rec.error:
                logger.warning("  -> 呼び出し失敗: %s", rec.error)
                continue
            try:
                obj = _parse_json(rec.content)
            except json.JSONDecodeError as e:
                logger.warning("  -> JSON解析失敗: %s", e)
                continue
            if validator:
                try:
                    validator(obj, allowed_ids or set())
                except Exception as e:  # noqa: BLE001
                    logger.warning("  -> 検証失敗: %s", e)
                    continue
            return obj
        return None

    # ---- §5 単位ごとの実行 ----
    def stage_plan(self) -> bool:
        brief = self.state.data.get("brief")
        div = build_diversity_note(self.s.resolve_archive_dir(), self.s.diversity.get("recent_window", 5))
        sys_p, user_p, _, schema = plan_series(brief, div)
        obj = self._ask("plan", "plan", "series", sys_p, user_p, schema)
        if not obj:
            return False
        self.state.save_json("series_plan", obj)
        return True

    def stage_characters(self) -> bool:
        plan = self.state.load_json("series_plan")
        div = build_diversity_note(self.s.resolve_archive_dir(), self.s.diversity.get("recent_window", 5))
        sys_p, user_p, _, schema = characters(plan, div)
        obj = self._ask("characters", "characters", "all", sys_p, user_p, schema)
        if not obj:
            return False
        # 採番: char / rel
        chars = obj.get("characters", [])
        id_map = {}
        for c in chars:
            new_id = self.seq.next("char")
            id_map[c.get("id")] = new_id
            c["id"] = new_id
        rels = obj.get("relationships", [])
        for r in rels:
            new_id = self.seq.next("rel")
            if r.get("character_a_id") in id_map:
                r["character_a_id"] = id_map[r["character_a_id"]]
            if r.get("character_b_id") in id_map:
                r["character_b_id"] = id_map[r["character_b_id"]]
            r["id"] = new_id
        self.state.save_json("characters", {"characters": chars, "relationships": rels})
        return True

    def _ledger_stage(self, key: str, fn, out_name: str, kind_prefix: str, id_field: str, *fn_args) -> bool:
        sys_p, user_p, _, schema = fn(*fn_args)
        obj = self._ask(key, key, "all", sys_p, user_p, schema)
        if not obj:
            return False
        items = obj.get(list(obj.keys())[0], []) if obj else []
        for it in items:
            it["id"] = self.seq.next(kind_prefix)
        self.state.save_json(out_name, obj)
        return True

    def stage_world(self) -> bool:
        brief = self.state.data.get("brief")
        plan = self.state.load_json("series_plan")
        chars = self.state.load_json("characters")
        return self._ledger_stage("world", world_ledger, "world", "entity", "id", brief, plan, chars)

    def stage_timeline(self) -> bool:
        brief = self.state.data.get("brief")
        plan = self.state.load_json("series_plan")
        return self._ledger_stage("timeline", timeline_ledger, "timeline", "time", "id", brief, plan)

    def stage_threads(self) -> bool:
        brief = self.state.data.get("brief")
        plan = self.state.load_json("series_plan")
        chars = self.state.load_json("characters")
        world = self.state.load_json("world")
        timeline = self.state.load_json("timeline")
        sys_p, user_p, _, schema = threads_ledger(brief, plan, chars, world, timeline)
        obj = self._ask("threads", "threads", "all", sys_p, user_p, schema)
        if not obj:
            return False
        threads = obj.get("threads", [])
        char_ids = {c["id"] for c in chars.get("characters", [])}
        for t in threads:
            t["id"] = self.seq.next("thread")
            t["involved_characters"] = [c for c in t.get("involved_characters", []) if c in char_ids]
        self.state.save_json("threads", {"threads": threads})
        return True

    def stage_volume_plan(self, vol: int) -> bool:
        plan = self.state.load_json("series_plan")
        vol_plan = next((v for v in plan.get("volumes", []) if v.get("number") == vol), {})
        brief = self.state.data.get("brief")
        prior = self.state.data.get("volume_summaries", [])
        threads = self.state.load_json("threads")
        is_final = vol == plan.get("volume_count")
        sys_p, user_p, _, schema = volume_chapters(vol_plan, brief, prior, threads, is_final)
        obj = self._ask("volume-plan", f"vol{vol}", "chapters", sys_p, user_p, schema)
        if not obj:
            return False
        self.state.save_json(f"volume_{vol:02d}_chapters", obj)
        return True

    def stage_scene_cards(self, vol: int, ch: int) -> bool:
        chapters = self.state.load_json(f"volume_{vol:02d}_chapters")
        chapter = next((c for c in chapters.get("chapters", []) if c.get("chapter_number") == ch), {})
        brief = self.state.data.get("brief")
        handoff = self.state.data.get("last_handoff", "")
        vol_changes = self.state.data.get(f"vol_changes_{vol}", "")
        threads = self.state.load_json("threads")
        is_final_chapter = (vol == self.state.load_json("series_plan").get("volume_count")
                            and ch == len(chapters.get("chapters", [])))
        final_cond = brief.get("ending", "") if is_final_chapter else ""
        sys_p, user_p, _, schema = scene_cards(chapter, brief, handoff, vol_changes,
                                                threads, is_final_chapter, final_cond)
        obj = self._ask("scene-cards", f"vol{vol}.ch{ch}", "cards", sys_p, user_p, schema)
        if not obj:
            return False
        self.state.save_json(f"volume_{vol:02d}_chapter_{ch:02d}_cards", obj)
        return True

    def _scene_context(self, vol: int, ch: int, card: dict) -> dict:
        threads = self.state.load_json("threads")
        world = self.state.load_json("world")
        timeline = self.state.load_json("timeline")
        chars = self.state.load_json("characters")
        # 許可ID集合: 場面カードが参照するID
        allowed = set()
        for t in card.get("thread_actions", []):
            allowed.add(t.get("id"))
        for e in card.get("entity_ids", []):
            allowed.add(e)
        allowed.add(card.get("location_id", ""))
        return {
            "viewpoint": card.get("viewpoint_character"),
            "reader_disclosure": card.get("reader_disclosure"),
            "presentation_rules": card.get("presentation_rules"),
            "thread_actions": card.get("thread_actions"),
            "start_time": card.get("start_time"),
            "end_time": card.get("end_time"),
            "location_id": card.get("location_id"),
            "related_threads": [t for t in threads.get("threads", []) if t["id"] in allowed],
            "related_entities": [e for e in world.get("entities", []) if e["id"] in allowed],
            "related_timelines": [t for t in timeline.get("timelines", []) if t["id"] in allowed],
            "characters": chars,
            "prior_handoff": self.state.data.get("last_handoff", ""),
        }

    def stage_scenes(self, vol: int, ch: int, scene_range: tuple[int, int] | None = None) -> bool:
        cards = self.state.load_json(f"volume_{vol:02d}_chapter_{ch:02d}_cards")
        scene_cards = cards.get("scene_cards", [])
        # 許可ID集合: 全台帳 + 人物/関係
        allowed_ids = set()
        for name in ("characters", "world", "timeline", "threads"):
            d = self.state.load_json(name)
            if not d:
                continue
            for k, v in d.items():
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and "id" in item:
                            allowed_ids.add(item["id"])
        chars = self.state.load_json("characters")
        for r in chars.get("relationships", []):
            allowed_ids.add(r["id"])

        indices = range(len(scene_cards))
        if scene_range:
            lo, hi = scene_range
            indices = [i for i in indices if lo <= scene_cards[i].get("scene_number", i + 1) <= hi]

        passes = self.s.quality.get("max_improvement_passes", 1)
        for i in indices:
            card = scene_cards[i]
            sc_num = card.get("scene_number", i + 1)
            ref = f"vol{vol}.ch{ch}.sc{sc_num}"
            context = self._scene_context(vol, ch, card)
            sys_p, user_p, _, schema = scene_write(card, context)
            obj = self._ask("scene", f"vol{vol}.ch{ch}", f"sc{sc_num}", sys_p, user_p, schema,
                            validator=validate_scene_response, allowed_ids=allowed_ids)
            if obj is None:
                self.state.set_stop_reason(f"場面生成失敗: {ref}")
                return False
            best = obj
            # 改善ステージ
            for p in range(passes):
                sys_p2, user_p2, _, schema2 = improve(best, card, self.s.quality.get("improvement_directions", []))
                imp = self._ask("improve", f"vol{vol}.ch{ch}", f"sc{sc_num}.p{p+1}", sys_p2, user_p2, schema2,
                                validator=validate_scene_response, allowed_ids=allowed_ids)
                if imp is None:
                    continue
                # 計測可能な軸で悪化していないか簡易判定: 必須イベント含む・文字数目安
                target = self.s.quality.get("content_length_target_chars", 2200)
                tol = self.s.quality.get("content_length_tolerance_chars", 400)
                if (target - tol) <= len(imp.get("content", "")) <= (target + tol):
                    best = imp
            self.state.save_scene(vol, ch, sc_num, best)
            self.state.data["last_handoff"] = best.get("handoff_summary", "")
            self.state.mark_last_scene(ref)
            logger.info("  場面保存: %s (文字数=%d)", ref, len(best.get("content", "")))
        return True

    def stage_volume_summary(self, vol: int) -> bool:
        handoffs = []
        chapters = self.state.load_json(f"volume_{vol:02d}_chapters")
        for ch in chapters.get("chapters", []):
            ch_num = ch.get("chapter_number")
            scenes = self.state.load_scene(vol, ch_num, 1)
            # 最後の場面の handoff を取得（簡易: 章内全場面の最後）
            d = self.state.scene_dir / f"volume-{vol:02d}" / f"chapter-{ch_num:02d}"
            if d.exists():
                files = sorted(d.glob("scene-*.json"))
                if files:
                    last = json.loads(files[-1].read_text(encoding="utf-8"))
                    handoffs.append(last.get("handoff_summary", ""))
        plan = self.state.load_json("series_plan")
        sys_p, user_p, _, schema = volume_summary(handoffs, plan)
        obj = self._ask("volume-summary", f"vol{vol}", "summary", sys_p, user_p, schema)
        if not obj:
            return False
        summaries = self.state.data.get("volume_summaries", [])
        summaries.append(obj)
        self.state.data["volume_summaries"] = summaries
        self.state.save()
        return True

    def stage_closure_check(self) -> bool:
        threads = self.state.load_json("threads")
        main = [t for t in threads.get("threads", []) if t.get("importance") == "主要"]
        if not main:
            return True
        scene_updates = []
        plan = self.state.load_json("series_plan")
        for vol in range(1, plan.get("volume_count", 0) + 1):
            chapters = self.state.load_json(f"volume_{vol:02d}_chapters") or {}
            for ch in chapters.get("chapters", []):
                ch_num = ch.get("chapter_number")
                d = self.state.scene_dir / f"volume-{vol:02d}" / f"chapter-{ch_num:02d}"
                if d.exists():
                    for f in sorted(d.glob("scene-*.json")):
                        sc = json.loads(f.read_text(encoding="utf-8"))
                        scene_updates.append(sc.get("thread_updates", []))
        handoffs = [self.state.data.get("last_handoff", "")]
        sys_p, user_p, _, schema = closure_check(threads, scene_updates, handoffs)
        obj = self._ask("closure", "closure", "check", sys_p, user_p, schema)
        if not obj:
            return False
        unresolved = [r for r in obj.get("results", []) if r.get("status") == "未回収"]
        if unresolved:
            self.state.set_stop_reason(f"未回収の主要伏線: {[r['thread_id'] for r in unresolved]}")
            return False
        return True

    def stage_output(self, out_root: Path) -> bool:
        write_output(self.state, out_root)
        logger.info("Markdown出力完了: %s", out_root)
        return True
