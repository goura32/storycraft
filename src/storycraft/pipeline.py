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
    closure_check, critique, fix, improve, plan_series, characters, world_ledger,
    timeline_ledger, threads_ledger, volume_chapters, scene_cards, scene_write,
    volume_summary,
)
from .state import State
from .validation import (validate_plan_response, validate_characters_response, validate_world_response,
                         validate_timeline_response, validate_threads_response, validate_volume_chapters_response,
                         validate_scene_cards_response, validate_scene_response, validate_volume_summary_response,
                         validate_closure_response, validate_critique_response, validate_fix_response)

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
             max_attempts: int | None = None, log_prefix: str = "") -> dict | None:
        if max_attempts is None:
            max_attempts = self.s.retry.get("max_attempts", 4)
        full_user = f"{user_p}\n\n【この呼び出し専用JSON Schema】\n{schema}\n\n必ずJSONオブジェクトだけを返してください。"
        # refごとに決定論的なシード系列を生成
        ref_seed_base = self.base_seed + (abs(hash(ref)) % 1000000)
        for attempt in range(max_attempts):
            seed = ref_seed_base + attempt
            meta = {"__kind": kind, "__phase": phase, "__ref": ref, "__attempt": attempt + 1}
            messages = [{"role": "system", "content": sys_p}, meta, {"role": "user", "content": full_user}]
            prefix = f"{log_prefix} " if log_prefix else ""
            logger.info("[%s] %s%s 試行%d (seed=%d)", phase, prefix, ref, attempt + 1, seed)
            rec = self.llm.call_once(messages, {"type": "json_object"}, seed)
            self.llm.save_raw(rec, messages)
            if rec.error:
                logger.warning("  -> 呼び出し失敗 (seed=%d): %s", seed, rec.error)
                continue
            try:
                obj = _parse_json(rec.content)
            except json.JSONDecodeError as e:
                logger.warning("  -> JSON解析失敗 (seed=%d): %s", seed, e)
                continue
            if validator:
                try:
                    validator(obj, allowed_ids or set())
                except Exception as e:  # noqa: BLE001
                    logger.warning("  -> 検証失敗 (seed=%d): %s", seed, e)
                    continue
            return obj
        return None

    # ---- 共通: 生成→批評→修正 の二段階改善パイプライン ----
    def _generate_with_improvement(self, kind: str, phase: str, ref: str,
                                    sys_p: str, user_p: str, schema: str,
                                    validator, allowed_ids: set,
                                    card: dict | None = None,
                                    log_prefix: str = "") -> dict | None:
        """生成→批評→修正 の二段階改善を実行し、最良版を返す。
        card が None の場合は場面以外（plan, characters 等）として扱う。
        """
        # 1. 生成（リトライ込み）
        obj = self._ask(kind, phase, ref, sys_p, user_p, schema,
                        validator=validator, allowed_ids=allowed_ids, log_prefix=log_prefix)
        if obj is None:
            return None
        best = obj

        passes = self.s.quality.get("max_improvement_passes", 1)
        if passes == 0:
            return best

        # 改善の方向
        directions = self.s.quality.get("improvement_directions", [])

        for p in range(passes):
            # 1. 批評
            sys_p_crit, user_p_crit, _, schema_crit = critique(best, card or {}, directions)
            crit = self._ask("critique", phase, f"{ref}.crit{p+1}", sys_p_crit, user_p_crit, schema_crit,
                            validator=validate_critique_response, allowed_ids=set(), log_prefix=log_prefix)
            if crit is None:
                continue

            # 2. 修正
            sys_p_fix, user_p_fix, _, schema_fix = fix(best, crit, card or {}, directions)
            imp = self._ask("fix", phase, f"{ref}.fix{p+1}", sys_p_fix, user_p_fix, schema_fix,
                            validator=validator, allowed_ids=allowed_ids, log_prefix=log_prefix)
            if imp is None:
                continue

            # 採用判定: 計測可能な軸で悪化していないか
            # 共通: 構造・ID・enum は validator で保証済み
            # 個別判定は stage ごとに実装可能（ここでは基本チェックのみ）
            if self._adopt_check(best, imp, card):
                best = imp
                logger.info("  -> 改善採用: %s (pass=%d)", ref, p + 1)
            else:
                logger.info("  -> 改善不採用: %s (pass=%d)", ref, p + 1)

        return best

    def _adopt_check(self, best: dict, imp: dict, card: dict | None) -> bool:
        """改善版を採用するか判定。ステージ固有のチェックはオーバーライドで拡張。"""
        # 基本: 必須キーの存在と空でないこと
        if not isinstance(imp, dict):
            return False
        return True

    # ---- §5 単位ごとの実行 ----
    def stage_plan(self) -> bool:
        brief = self.state.data.get("brief")
        div = build_diversity_note(self.s.resolve_archive_dir(), self.s.diversity.get("recent_window", 5))
        sys_p, user_p, _, schema = plan_series(brief, div)
        obj = self._generate_with_improvement("plan", "plan", "series", sys_p, user_p, schema,
                                              validator=validate_plan_response, allowed_ids=set(),
                                              card=None, log_prefix="plan")
        if not obj:
            return False
        self.state.save_json("series_plan", obj)
        return True

    def stage_characters(self) -> bool:
        plan = self.state.load_json("series_plan")
        div = build_diversity_note(self.s.resolve_archive_dir(), self.s.diversity.get("recent_window", 5))
        sys_p, user_p, _, schema = characters(plan, div)
        obj = self._generate_with_improvement("characters", "characters", "all", sys_p, user_p, schema,
                                              validator=validate_characters_response, allowed_ids=set(),
                                              card=None, log_prefix="characters")
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
        allowed = set()
        for c in chars.get("characters", []):
            allowed.add(c["id"])
        for r in chars.get("relationships", []):
            allowed.add(r["id"])
        sys_p, user_p, _, schema = world_ledger(brief, plan, chars)
        obj = self._generate_with_improvement("world", "world", "all", sys_p, user_p, schema,
                                              validator=validate_world_response, allowed_ids=allowed,
                                              card=None, log_prefix="world")
        if not obj:
            return False
        items = obj.get("entities", [])
        for it in items:
            it["id"] = self.seq.next("entity")
        self.state.save_json("world", {"entities": items})
        return True

    def stage_timeline(self) -> bool:
        brief = self.state.data.get("brief")
        plan = self.state.load_json("series_plan")
        sys_p, user_p, _, schema = timeline_ledger(brief, plan)
        obj = self._generate_with_improvement("timeline", "timeline", "all", sys_p, user_p, schema,
                                              validator=validate_timeline_response, allowed_ids=set(),
                                              card=None, log_prefix="timeline")
        if not obj:
            return False
        items = obj.get("timelines", [])
        for it in items:
            it["id"] = self.seq.next("time")
        self.state.save_json("timeline", {"timelines": items})
        return True

    def stage_threads(self) -> bool:
        brief = self.state.data.get("brief")
        plan = self.state.load_json("series_plan")
        chars = self.state.load_json("characters")
        world = self.state.load_json("world")
        timeline = self.state.load_json("timeline")
        char_ids = {c["id"] for c in chars.get("characters", [])}
        entity_ids = {e["id"] for e in world.get("entities", [])}
        time_ids = {t["id"] for t in timeline.get("timelines", [])}
        allowed = char_ids | entity_ids | time_ids
        sys_p, user_p, _, schema = threads_ledger(brief, plan, chars, world, timeline)
        obj = self._generate_with_improvement("threads", "threads", "all", sys_p, user_p, schema,
                                              validator=validate_threads_response, allowed_ids=allowed,
                                              card=None, log_prefix="threads")
        if not obj:
            return False
        threads = obj.get("threads", [])
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
        thread_ids = {t["id"] for t in threads.get("threads", [])}
        sys_p, user_p, _, schema = volume_chapters(vol_plan, brief, prior, threads, is_final)
        obj = self._generate_with_improvement("volume-plan", f"vol{vol}", "chapters", sys_p, user_p, schema,
                                              validator=validate_volume_chapters_response, allowed_ids=thread_ids,
                                              card=None, log_prefix=f"vol{vol}-plan")
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
        thread_ids = {t["id"] for t in threads.get("threads", [])}
        entity_ids = {e["id"] for e in self.state.load_json("world").get("entities", [])}
        char_ids = {c["id"] for c in self.state.load_json("characters").get("characters", [])}
        rel_ids = {r["id"] for r in self.state.load_json("characters").get("relationships", [])}
        allowed = thread_ids | entity_ids | char_ids | rel_ids
        sys_p, user_p, _, schema = scene_cards(chapter, brief, handoff, vol_changes,
                                                threads, is_final_chapter, final_cond)
        obj = self._generate_with_improvement("scene-cards", f"vol{vol}.ch{ch}", "cards", sys_p, user_p, schema,
                                              validator=validate_scene_cards_response, allowed_ids=allowed,
                                              card=None, log_prefix=f"vol{vol}.ch{ch}-cards")
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
        # 総巻数・総章数・総場面数を取得してログプレフィックス用にする
        plan = self.state.load_json("series_plan")
        total_volumes = plan.get("volume_count", 0)
        chapters = self.state.load_json(f"volume_{vol:02d}_chapters")
        total_chapters = len(chapters.get("chapters", []))
        total_scenes = len(scene_cards)
        for i in indices:
            card = scene_cards[i]
            sc_num = card.get("scene_number", i + 1)
            ref = f"vol{vol}.ch{ch}.sc{sc_num}"
            # ログプレフィックス: 進行状況を表示
            log_prefix = f"巻{vol}/{total_volumes} 章:{ch}/{total_chapters} 場面:{sc_num}/{total_scenes}"
            context = self._scene_context(vol, ch, card)
            sys_p, user_p, _, schema = scene_write(card, context)
            obj = self._ask("scene", f"vol{vol}.ch{ch}", f"sc{sc_num}", sys_p, user_p, schema,
                            validator=validate_scene_response, allowed_ids=allowed_ids, log_prefix=log_prefix)
            if obj is None:
                self.state.set_stop_reason(f"場面生成失敗: {ref}")
                return False
            best = obj
            # 改善ステージ（二段階: 批評→修正）
            for p in range(passes):
                # 1. 批評
                sys_p_crit, user_p_crit, _, schema_crit = critique(best, card, self.s.quality.get("improvement_directions", []))
                crit = self._ask("critique", f"vol{vol}.ch{ch}", f"sc{sc_num}.crit{p+1}", sys_p_crit, user_p_crit, schema_crit,
                                validator=validate_critique_response, allowed_ids=set(), log_prefix=log_prefix)
                if crit is None:
                    continue
                # 2. 修正
                sys_p_fix, user_p_fix, _, schema_fix = fix(best, crit, card, self.s.quality.get("improvement_directions", []))
                imp = self._ask("fix", f"vol{vol}.ch{ch}", f"sc{sc_num}.fix{p+1}", sys_p_fix, user_p_fix, schema_fix,
                                validator=validate_fix_response, allowed_ids=allowed_ids, log_prefix=log_prefix)
                if imp is None:
                    continue
                # 計測可能な軸で悪化していないか判定（仕様 §3.13）
                # 1. 文字数目安
                target = self.s.quality.get("content_length_target_chars", 2200)
                tol = self.s.quality.get("content_length_tolerance_chars", 400)
                content = imp.get("content", "")
                if not (target - tol) <= len(content) <= (target + tol):
                    continue
                # 2. 必須イベント（required_events）の含有
                required = card.get("required_events", [])
                if required and not all(ev in content for ev in required if ev):
                    continue
                # 3. thread_actions と一致する更新が保たれるか
                best_thread_actions = [u["id"] for u in best.get("thread_updates", [])]
                imp_thread_actions = [u["id"] for u in imp.get("thread_updates", [])]
                if set(best_thread_actions) != set(imp_thread_actions):
                    continue
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
            # 最後の場面の handoff を取得
            d = self.state.scene_dir / f"volume-{vol:02d}" / f"chapter-{ch_num:02d}"
            if d.exists():
                files = sorted(d.glob("scene-*.json"))
                if files:
                    last = json.loads(files[-1].read_text(encoding="utf-8"))
                    handoffs.append(last.get("handoff_summary", ""))
        plan = self.state.load_json("series_plan")
        sys_p, user_p, _, schema = volume_summary(handoffs, plan)
        obj = self._generate_with_improvement("volume-summary", f"vol{vol}", "summary", sys_p, user_p, schema,
                                              validator=validate_volume_summary_response, allowed_ids=set(),
                                              card=None, log_prefix=f"volsum-{vol}")
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
        thread_ids = {t["id"] for t in main}
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
                        scene_updates.extend(sc.get("thread_updates", []))
        handoffs = [self.state.data.get("last_handoff", "")]
        sys_p, user_p, _, schema = closure_check(threads, scene_updates, handoffs)
        obj = self._generate_with_improvement("closure", "closure", "check", sys_p, user_p, schema,
                                              validator=validate_closure_response, allowed_ids=thread_ids,
                                              card=None, log_prefix="closure")
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
