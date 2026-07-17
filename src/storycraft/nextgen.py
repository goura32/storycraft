"""仕様準拠の次世代Storycraft実行系。"""
from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol


class ContractError(ValueError):
    """利用者入力または生成結果が製品契約を満たさない。"""


class StoryModel(Protocol):
    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]: ...

    def critique(self, stage: str, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]: ...

    def revise(self, stage: str, candidate: dict[str, Any], critique: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RunResult:
    completed: bool
    volume_count: int
    volume_paths: list[Path]
    series_path: Path
    closure: dict[str, Any]


class _Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / "state.json"

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict[str, Any]:
        if not self.exists():
            raise ContractError("保存済みシリーズがありません")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContractError("保存状態が壊れています") from exc
        if data.get("version") != 3:
            raise ContractError("この保存状態は現行の次世代形式ではありません")
        required = {
            "brief", "plan", "characters", "relationships", "world", "timeline", "threads",
            "chapters", "cards", "scenes", "volume_summaries", "initial_ledgers_confirmed",
            "attempts", "closure", "completed", "last_completed_unit", "stopped_at", "stop_reason",
        }
        if not required.issubset(data) or not isinstance(data["attempts"], list):
            raise ContractError("保存状態が製品契約を満たしていません")
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)


class SeriesService:
    """一つのシリーズを工程正本から生成、再開、出力する公開境界。"""

    _INITIAL_STAGES = ("plan", "characters", "relationships", "world", "timeline", "threads")

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.store = _Store(workspace)

    def run(self, brief: dict[str, Any], model: StoryModel, *, stop_after_scene: str | None = None) -> RunResult:
        if self.store.exists():
            raise ContractError("この作業場所には保存済みシリーズがあります。resume を使ってください")
        state = self._new_state(brief)
        self.store.save(state)
        return self._advance(state, model, stop_after_scene=stop_after_scene)

    def resume(self, model: StoryModel) -> RunResult:
        return self._advance(self.store.load(), model)

    def step(self, model: StoryModel, brief: dict[str, Any] | None = None) -> RunResult:
        if not self.store.exists():
            if brief is None:
                raise ContractError("初回の step には企画が必要です")
            state = self._new_state(brief)
            self.store.save(state)
        else:
            state = self.store.load()
        if state["completed"]:
            return self._result(state, self._volume_paths())
        self._run_one(state, model)
        self.store.save(state)
        return self._result(state)

    def _new_state(self, brief: dict[str, Any]) -> dict[str, Any]:
        self._validate_brief(brief)
        return {
            "version": 3,
            "brief": brief,
            "plan": None,
            "characters": None,
            "relationships": None,
            "world": None,
            "timeline": None,
            "threads": None,
            "chapters": {},
            "cards": {},
            "scenes": [],
            "volume_summaries": {},
            "initial_ledgers_confirmed": False,
            "attempts": [],
            "closure": {},
            "completed": False,
            "last_completed_unit": None,
            "stopped_at": None,
            "stop_reason": None,
            "_active": None,
        }

    def _advance(self, state: dict[str, Any], model: StoryModel, *, stop_after_scene: str | None = None) -> RunResult:
        try:
            while not state["completed"]:
                scene_id = self._run_one(state, model)
                self.store.save(state)
                if scene_id is not None and scene_id == stop_after_scene:
                    return self._result(state)
            return self._result(state, self._volume_paths())
        except ContractError as exc:
            active = state.get("_active") or {"stage": "unknown", "unit": None}
            state["stopped_at"] = active
            state["stop_reason"] = str(exc)
            self.store.save(state)
            raise

    def _run_one(self, state: dict[str, Any], model: StoryModel) -> str | None:
        if state["plan"] is None:
            plan = self._improve("plan", {"brief": state["brief"]}, model, state, lambda item: self._validate_plan(item, state["brief"]))
            self._validate_chapter_count_length(state["brief"], len(plan["volumes"]))
            state["plan"] = plan
            state["last_completed_unit"] = {"stage": "plan", "unit": None}
            return None
        if state["characters"] is None:
            proposed = self._improve("characters", {"brief": state["brief"], "plan": state["plan"]}, model, state, self._validate_characters)
            state["characters"] = self._assign_ids(proposed["characters"], "char")
            return None
        if state["relationships"] is None:
            context = {"brief": state["brief"], "plan": state["plan"], "characters": state["characters"]}
            proposed = self._improve("relationships", context, model, state, lambda item: self._validate_relationships(item, state["characters"]))
            state["relationships"] = self._assign_ids(proposed["relationships"], "rel")
            return None
        if state["world"] is None:
            context = {"brief": state["brief"], "plan": state["plan"], "characters": state["characters"], "relationships": state["relationships"]}
            proposed = self._improve("world", context, model, state, self._validate_world)
            state["world"] = self._assign_ids(proposed["entities"], "entity")
            return None
        if state["timeline"] is None:
            context = self._ledger_context(state)
            proposed = self._improve("timeline", context, model, state, lambda item: self._validate_timeline(item, self._known_ids(state)))
            state["timeline"] = self._assign_ids(proposed["timelines"], "time")
            return None
        if state["threads"] is None:
            context = self._ledger_context(state)
            proposed = self._improve("threads", context, model, state, lambda item: self._validate_threads(item, self._known_ids(state), state["brief"], state["plan"]))
            state["threads"] = self._assign_ids(proposed["threads"], "thread")
            return None
        if not state["initial_ledgers_confirmed"]:
            self._validate_initial_ledgers(state)
            state["initial_ledgers_confirmed"] = True
            return None

        for volume_number, planned_volume in enumerate(state["plan"]["volumes"], 1):
            volume = {**planned_volume, "number": volume_number}
            volume_key = str(volume_number)
            if volume_key not in state["chapters"]:
                context = {"brief": state["brief"], "volume": volume, "ledgers": self._ledger_context(state), "prior_summaries": self._prior_summaries(state, volume["number"])}
                state["chapters"][volume_key] = self._improve("volume_chapters", context, model, state, lambda item: self._validate_chapters(item, volume, state["brief"]))["chapters"]
                return None
            for chapter in state["chapters"][volume_key]:
                for scene_number in range(1, chapter["scene_count"] + 1):
                    scene_id = self._scene_id(volume["number"], chapter["number"], scene_number)
                    if any(scene["scene_id"] == scene_id for scene in state["scenes"]):
                        continue
                    is_final_scene = self._is_final_scene(state, volume, chapter, scene_number)
                    card_context = self._card_context(state, volume, chapter, scene_number, is_final_scene)
                    card = self._improve("scene_card", card_context, model, state, lambda item: self._validate_card(item, scene_id, state))
                    state["cards"][scene_id] = card
                    state["last_completed_unit"] = {"stage": "scene_card", "unit": scene_id}
                    prose_context = self._writer_context(state, card, scene_id, is_final_scene)
                    prose = self._improve("scene", prose_context, model, state, self._validate_scene)
                    continuity_context = {"scene_id": scene_id, "content": prose["content"], "card": card, "is_final_scene": is_final_scene}
                    continuity = self._improve("continuity", continuity_context, model, state, lambda item: self._validate_continuity(item, prose["content"], card, state, is_final_scene))
                    self._apply_updates(state, continuity["state_updates"], scene_id)
                    state["scenes"].append({"scene_id": scene_id, "volume": volume["number"], "chapter": chapter["number"], "content": prose["content"], "handoff_summary": continuity["handoff_summary"], "state_updates": continuity["state_updates"]})
                    return scene_id
            if volume_key not in state["volume_summaries"]:
                scenes = [scene for scene in state["scenes"] if scene["volume"] == volume["number"]]
                context = {"volume": volume, "scenes": scenes, "threads": state["threads"]}
                summary = self._improve("volume_summary", context, model, state, lambda item: self._validate_volume_summary(item, state))
                state["volume_summaries"][volume_key] = summary
                return None

        if not state["closure"]:
            context = {"brief": state["brief"], "threads": state["threads"], "scenes": state["scenes"], "volume_summaries": state["volume_summaries"]}
            state["closure"] = self._improve("closure", context, model, state, lambda item: self._validate_closure(item, state))
            return None
        self._write_output(state)
        state["completed"] = True
        return None

    def _improve(self, stage: str, context: dict[str, Any], model: StoryModel, state: dict[str, Any], validator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        state["_active"] = {"stage": stage, "unit": context.get("scene_id")}
        candidate: dict[str, Any] | None = None
        error = ""
        for _ in range(4):
            proposed = model.generate(stage, context)
            try:
                if not isinstance(proposed, dict):
                    raise ContractError("草稿がオブジェクトではありません")
                validator(proposed)
            except ContractError as exc:
                error = str(exc)
                self._record_attempt(state, stage, "draft_rejected", context, proposed, error)
                self.store.save(state)
                continue
            candidate = proposed
            break
        if candidate is None:
            raise ContractError(f"{stage} の草稿を検証できませんでした: {error}")
        self._record_attempt(state, stage, "draft", context, candidate, "accepted")
        try:
            critique = model.critique(stage, candidate, context)
            self._validate_critique(critique)
        except Exception as exc:
            self._record_attempt(state, stage, "critique_failed", context, None, str(exc))
            return candidate
        self._record_attempt(state, stage, "critique", context, critique, "accepted")
        if not critique["issues"]:
            return candidate
        revised: dict[str, Any] | None = None
        try:
            revised = model.revise(stage, candidate, critique, context)
            if not isinstance(revised, dict):
                raise ContractError("修正版がオブジェクトではありません")
            validator(revised)
            self._validate_revision_preserves_contract(stage, candidate, revised)
        except Exception as exc:
            self._record_attempt(state, stage, "revision_failed", context, revised, str(exc))
            return candidate
        self._record_attempt(state, stage, "revision", context, revised, "accepted")
        return revised

    @staticmethod
    def _record_attempt(state: dict[str, Any], stage: str, kind: str, input_value: dict[str, Any], response: Any, validation: str) -> None:
        state["attempts"].append({
            "stage": stage, "kind": kind, "unit": input_value.get("scene_id"), "input": input_value,
            "response": response, "validation": validation, "raw_reference": None,
        })

    @staticmethod
    def _validate_revision_preserves_contract(stage: str, candidate: dict[str, Any], revised: dict[str, Any]) -> None:
        critical = {
            "scene_card": ("scene_id", "required_events", "thread_actions", "character_ids", "visible_ids", "allowed_update_ids"),
            "continuity": ("state_updates",),
            "volume_chapters": ("chapters",),
            "closure": ("resolved_ids",),
        }
        for field in critical.get(stage, ()):
            if field in candidate and revised.get(field) != candidate[field]:
                raise ContractError(f"修正版が契約上重要な {field} を変更または欠落しました")

    @staticmethod
    def _validate_brief(brief: dict[str, Any]) -> None:
        if not isinstance(brief, dict):
            raise ContractError("企画はオブジェクトでなければなりません")
        for key in ("title", "genre", "protagonist", "key_people", "want", "avoid", "ending"):
            if not isinstance(brief.get(key), str) or not brief[key].strip():
                raise ContractError(f"企画の必須項目がありません: {key}")
        if brief.get("volumes") is not None and (not isinstance(brief["volumes"], int) or not 4 <= brief["volumes"] <= 10):
            raise ContractError("volumes は 4〜10 の整数でなければなりません")
        counts = brief.get("chapters_per_volume")
        if counts is not None and (not isinstance(counts, list) or not all(isinstance(value, int) and 1 <= value <= 12 for value in counts) or (brief.get("volumes") and len(counts) != brief["volumes"])):
            raise ContractError("chapters_per_volume は巻数と一致する1〜12の整数配列でなければなりません")

    @staticmethod
    def _validate_chapter_count_length(brief: dict[str, Any], volume_count: int) -> None:
        counts = brief.get("chapters_per_volume")
        if counts is not None and len(counts) != volume_count:
            raise ContractError("chapters_per_volume は全巻構成の巻数と一致しなければなりません")

    @staticmethod
    def _validate_plan(plan: dict[str, Any], brief: dict[str, Any]) -> None:
        volumes = plan.get("volumes")
        if not isinstance(volumes, list) or not 4 <= len(volumes) <= 10 or (brief.get("volumes") and len(volumes) != brief["volumes"]):
            raise ContractError("全巻構成の巻数が不正です")
        for expected, volume in enumerate(volumes, 1):
            if not isinstance(volume, dict) or "number" in volume or "ending_condition" in volume:
                raise ContractError("全巻構成に採番または結末条件を含めてはいけません")
            for key in ("title", "change", "leaves_question"):
                if not isinstance(volume.get(key), str):
                    raise ContractError(f"全巻構成の {key} が不正です")
            limits = {"title": 48, "change": 240, "leaves_question": 160}
            for key, limit in limits.items():
                if len(volume[key]) > limit:
                    raise ContractError(f"全巻構成の {key} は{limit}文字以内でなければなりません")
                if any("\uac00" <= character <= "\ud7a3" for character in volume[key]):
                    raise ContractError(f"全巻構成の {key} に日本語以外のハングル字形があります")
            if expected < len(volumes):
                if not volume["leaves_question"].strip():
                    raise ContractError("最終巻以外には次巻へ続く問いが必要です")
            elif volume["leaves_question"]:
                raise ContractError("最終巻の問いは空文字列でなければなりません")

    @staticmethod
    def _validate_characters(value: dict[str, Any]) -> None:
        records = value.get("characters")
        if not isinstance(records, list) or not records:
            raise ContractError("人物台帳が空です")
        for record in records:
            SeriesService._require(record, "name", "role", "narrative_function", "fixed_profile")
            SeriesService._initial_state(record)
            if "id" in record:
                raise ContractError("人物IDはプログラムが採番します")

    @staticmethod
    def _validate_relationships(value: dict[str, Any], characters: list[dict[str, Any]]) -> None:
        records = value.get("relationships")
        ids = {record["id"] for record in characters}
        if not isinstance(records, list):
            raise ContractError("関係台帳が配列ではありません")
        for record in records:
            SeriesService._require(record, "character_a_id", "character_b_id", "fixed_meaning")
            SeriesService._initial_state(record)
            if record["character_a_id"] not in ids or record["character_b_id"] not in ids:
                raise ContractError("関係台帳が未知の人物を参照しています")
            if "id" in record:
                raise ContractError("関係IDはプログラムが採番します")

    @staticmethod
    def _validate_world(value: dict[str, Any]) -> None:
        records = value.get("entities")
        if not isinstance(records, list):
            raise ContractError("世界台帳が配列ではありません")
        for record in records:
            SeriesService._require(record, "kind", "name", "stable_fact", "use_or_access_rule")
            SeriesService._initial_state(record)
            if "id" in record:
                raise ContractError("世界IDはプログラムが採番します")

    @staticmethod
    def _validate_timeline(value: dict[str, Any], known_ids: set[str]) -> None:
        records = value.get("timelines")
        if not isinstance(records, list):
            raise ContractError("時間台帳が配列ではありません")
        for record in records:
            SeriesService._require(record, "kind", "description", "related_ids", "fixed_rule")
            SeriesService._initial_state(record)
            if not isinstance(record["related_ids"], list) or not set(record["related_ids"]).issubset(known_ids):
                raise ContractError("時間台帳が未知IDを参照しています")
            if "id" in record:
                raise ContractError("時間IDはプログラムが採番します")

    @staticmethod
    def _validate_threads(value: dict[str, Any], known_ids: set[str], brief: dict[str, Any], plan: dict[str, Any]) -> None:
        records = value.get("threads")
        if not isinstance(records, list) or not records:
            raise ContractError("主要項目台帳が空です")
        major_count = 0
        questions = {volume["leaves_question"] for volume in plan["volumes"] if volume["leaves_question"]}
        for record in records:
            SeriesService._require(record, "kind", "importance", "description", "author_truth", "reader_knowledge", "character_knowledge", "presentation_rule", "introduce_by", "resolve_by", "resolution_condition")
            state = SeriesService._initial_state(record)
            if record["importance"] not in {"major", "supporting"} or state.get("status") not in {"open", "in_progress", "resolved"}:
                raise ContractError("主要項目の状態または重要度が不正です")
            if not isinstance(record["character_knowledge"], dict) or not set(record["character_knowledge"]).issubset(known_ids):
                raise ContractError("主要項目が未知の人物を参照しています")
            if "id" in record:
                raise ContractError("主要項目IDはプログラムが採番します")
            if record["importance"] == "major":
                major_count += 1
                traceability = record.get("traceability")
                if not isinstance(traceability, dict) or traceability.get("brief_want") != brief["want"] or traceability.get("brief_ending") != brief["ending"] or traceability.get("leaves_question") not in questions:
                    raise ContractError("主要項目に企画・結末・巻末の問いへの追跡情報がありません")
        if major_count == 0:
            raise ContractError("主要項目台帳には major が必要です")

    @staticmethod
    def _validate_chapters(value: dict[str, Any], volume: dict[str, Any], brief: dict[str, Any]) -> None:
        chapters = value.get("chapters")
        expected_count = (brief.get("chapters_per_volume") or [None] * len([volume]))[volume["number"] - 1] if brief.get("chapters_per_volume") else None
        if not isinstance(chapters, list) or not chapters or (expected_count is not None and len(chapters) != expected_count):
            raise ContractError("章一覧の件数が不正です")
        for number, chapter in enumerate(chapters, 1):
            if not isinstance(chapter, dict) or chapter.get("number") != number:
                raise ContractError("章番号が連番ではありません")
            SeriesService._require(chapter, "title", "purpose", "start_state", "end_state")
            if not isinstance(chapter.get("scene_count"), int) or not 1 <= chapter["scene_count"] <= 4:
                raise ContractError("場面数は1〜4でなければなりません")

    def _validate_card(self, card: dict[str, Any], scene_id: str, state: dict[str, Any]) -> None:
        self._require(card, "scene_id", "pov_character_id", "location_id", "start_time_id", "end_time_id", "character_ids", "purpose", "required_events", "thread_actions", "reader_disclosure", "withheld_information", "presentation_rules", "end_change", "visible_ids", "allowed_update_ids")
        if card["scene_id"] != scene_id:
            raise ContractError("場面カードのIDが実行対象と一致しません")
        characters = {record["id"] for record in state["characters"]}
        times = {record["id"] for record in state["timeline"]}
        world = {record["id"] for record in state["world"]}
        threads = {record["id"] for record in state["threads"]}
        known = self._known_ids(state)
        if card["pov_character_id"] not in characters or card["location_id"] not in world:
            raise ContractError("場面カードの視点人物または場所が不正です")
        if card["start_time_id"] not in times or card["end_time_id"] not in times:
            raise ContractError("場面カードの時刻が不正です")
        if not isinstance(card["character_ids"], list) or not card["character_ids"] or not set(card["character_ids"]).issubset(characters):
            raise ContractError("場面カードの登場人物が不正です")
        if not isinstance(card["thread_actions"], list):
            raise ContractError("場面カードの伏線操作が不正です")
        for action in card["thread_actions"]:
            self._require(action, "thread_id", "action")
            if action["thread_id"] not in threads or action["action"] not in {"introduce", "advance", "resolve"}:
                raise ContractError("場面カードの伏線操作が不正です")
        for field in ("visible_ids", "allowed_update_ids"):
            values = card[field]
            if not isinstance(values, list) or len(values) != len(set(values)) or not set(values).issubset(known):
                raise ContractError(f"場面カードの {field} が不正です")
        if not set(card["allowed_update_ids"]).issubset(card["visible_ids"]):
            raise ContractError("状態更新の許可IDは可視IDの部分集合でなければなりません")

    @staticmethod
    def _validate_scene(value: dict[str, Any]) -> None:
        if set(value) != {"content"} or not isinstance(value.get("content"), str) or not value["content"].strip():
            raise ContractError("場面本文は空でない content だけを返さなければなりません")

    def _validate_continuity(self, value: dict[str, Any], content: str, card: dict[str, Any], state: dict[str, Any], is_final_scene: bool) -> None:
        self._require(value, "handoff_summary", "state_updates")
        if not isinstance(value["state_updates"], list):
            raise ContractError("状態更新が配列ではありません")
        seen: set[str] = set()
        unresolved = {record["id"] for record in state["threads"] if record["importance"] == "major" and record["current_state"].get("status") != "resolved"}
        resolved: set[str] = set()
        for update in value["state_updates"]:
            self._require(update, "source_scene_id", "id", "field", "value", "evidence")
            if update["source_scene_id"] != card["scene_id"]:
                raise ContractError("状態更新の場面IDが実行対象と一致しません")
            if update["id"] in seen or update["id"] not in card["allowed_update_ids"]:
                raise ContractError("状態更新が重複または未許可です")
            seen.add(update["id"])
            if not isinstance(update["evidence"], str) or not update["evidence"] or update["evidence"] not in content:
                raise ContractError("状態更新に本文根拠がありません")
            target = self._record_for_id(state, update["id"])
            if target is None:
                raise ContractError("状態更新が未知IDを参照しています")
            field = update["field"]
            if field == "status":
                if not update["id"].startswith("thread-") or update["value"] not in {"open", "in_progress", "resolved"}:
                    raise ContractError("主要項目以外のstatus更新または不正な状態です")
                if update["value"] == "resolved":
                    resolved.add(update["id"])
            elif field == "current_state" or field not in target["current_state"]:
                raise ContractError("更新できないフィールドです")
        if is_final_scene and not unresolved.issubset(resolved):
            raise ContractError("最終場面で主要項目がすべて回収されていません")

    @staticmethod
    def _validate_volume_summary(value: dict[str, Any], state: dict[str, Any]) -> None:
        if not isinstance(value.get("volume_summary"), str) or not value["volume_summary"].strip() or not isinstance(value.get("unresolved_thread_ids"), list):
            raise ContractError("巻要約が不正です")
        known = {record["id"] for record in state["threads"]}
        if not set(value["unresolved_thread_ids"]).issubset(known):
            raise ContractError("巻要約が未知の主要項目を参照しています")

    def _validate_closure(self, value: dict[str, Any], state: dict[str, Any]) -> None:
        resolved = value.get("resolved_ids")
        required = {record["id"] for record in state["threads"] if record["importance"] == "major"}
        if not isinstance(resolved, list) or set(resolved) != required or len(resolved) != len(set(resolved)):
            raise ContractError("完結確認の主要項目が台帳と一致しません")
        for item in required:
            record = self._record_for_id(state, item)
            if record is None or record["current_state"].get("status") != "resolved":
                raise ContractError("未回収の主要項目があります")
        evidence = value.get("ending_evidence")
        final_scene = state["scenes"][-1] if state["scenes"] else {}
        if value.get("ending_authority") != state["brief"]["ending"] or not isinstance(evidence, str) or not evidence or evidence not in final_scene.get("content", ""):
            raise ContractError("結末の本文根拠がありません")

    @staticmethod
    def _validate_critique(value: Any) -> None:
        if not isinstance(value, dict) or not isinstance(value.get("issues"), list):
            raise ContractError("批評の issues が配列ではありません")
        for issue in value["issues"]:
            if not isinstance(issue, dict) or issue.get("severity") not in {"critical", "major", "minor"}:
                raise ContractError("批評 issue が不正です")
            SeriesService._require(issue, "field", "description", "suggestion")

    @staticmethod
    def _require(value: Any, *fields: str) -> None:
        if not isinstance(value, dict):
            raise ContractError("応答項目がオブジェクトではありません")
        for field in fields:
            if not isinstance(value.get(field), str) or not value[field].strip():
                if field in {"required_events", "character_ids", "thread_actions", "visible_ids", "allowed_update_ids", "state_updates", "related_ids"} and isinstance(value.get(field), list):
                    continue
                if field == "character_knowledge" and isinstance(value.get(field), dict):
                    continue
                raise ContractError(f"必須項目がありません: {field}")

    @staticmethod
    def _initial_state(record: dict[str, Any]) -> dict[str, Any]:
        state = record.get("initial_state")
        if not isinstance(state, dict) or not state:
            raise ContractError("開始時の現在状態がありません")
        return state

    @staticmethod
    def _assign_ids(records: list[dict[str, Any]], prefix: str) -> list[dict[str, Any]]:
        assigned: list[dict[str, Any]] = []
        for number, record in enumerate(records, 1):
            copy = dict(record)
            copy["id"] = f"{prefix}-{number:04d}"
            copy["current_state"] = dict(copy["initial_state"])
            assigned.append(copy)
        return assigned

    def _validate_initial_ledgers(self, state: dict[str, Any]) -> None:
        if not all(state[key] is not None for key in ("characters", "relationships", "world", "timeline", "threads")):
            raise ContractError("初期台帳がそろっていません")
        for record in state["threads"]:
            for character_id in record["character_knowledge"]:
                if character_id not in self._known_ids(state):
                    raise ContractError("主要項目台帳の人物参照が不正です")

    def _ledger_context(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"brief": state["brief"], "plan": state["plan"], "characters": state["characters"] or [], "relationships": state["relationships"] or [], "world": state["world"] or [], "timeline": state["timeline"] or [], "threads": state["threads"] or []}

    def _known_ids(self, state: dict[str, Any]) -> set[str]:
        return {record["id"] for key in ("characters", "relationships", "world", "timeline", "threads") for record in (state[key] or [])}

    def _record_for_id(self, state: dict[str, Any], identifier: str) -> dict[str, Any] | None:
        for key in ("characters", "relationships", "world", "timeline", "threads"):
            for record in state[key] or []:
                if record["id"] == identifier:
                    return record
        return None

    def _apply_updates(self, state: dict[str, Any], updates: list[dict[str, Any]], scene_id: str) -> None:
        for update in updates:
            target = self._record_for_id(state, update["id"])
            assert target is not None
            target["current_state"][update["field"]] = update["value"]
            target["last_scene_id"] = scene_id

    def _card_context(self, state: dict[str, Any], volume: dict[str, Any], chapter: dict[str, Any], scene_number: int, is_final_scene: bool) -> dict[str, Any]:
        scene_id = self._scene_id(volume["number"], chapter["number"], scene_number)
        return {"scene_id": scene_id, "volume": volume, "chapter": chapter, "scene_number": scene_number, "ledgers": self._ledger_context(state), "previous_handoff": state["scenes"][-1]["handoff_summary"] if state["scenes"] else "", "is_final_scene": is_final_scene}

    def _writer_context(self, state: dict[str, Any], card: dict[str, Any], scene_id: str, is_final_scene: bool) -> dict[str, Any]:
        visible = {record["id"]: record for key in ("characters", "relationships", "world", "timeline", "threads") for record in state[key] or [] if record["id"] in card["visible_ids"]}
        return {"scene_id": scene_id, "card": card, "writer_view": visible, "previous_handoff": state["scenes"][-1]["handoff_summary"] if state["scenes"] else "", "is_final_scene": is_final_scene, "ending": state["brief"]["ending"] if is_final_scene else ""}

    @staticmethod
    def _scene_id(volume: int, chapter: int, scene: int) -> str:
        return f"v{volume:02d}-c{chapter:02d}-s{scene:02d}"

    def _is_final_scene(self, state: dict[str, Any], volume: dict[str, Any], chapter: dict[str, Any], scene_number: int) -> bool:
        return volume["number"] == len(state["plan"]["volumes"]) and chapter["number"] == state["chapters"][str(volume["number"])][-1]["number"] and scene_number == chapter["scene_count"]

    @staticmethod
    def _prior_summaries(state: dict[str, Any], volume_number: int) -> list[dict[str, Any]]:
        return [state["volume_summaries"][str(number)] for number in range(1, volume_number) if str(number) in state["volume_summaries"]]

    def _validate_manuscript_state(self, state: dict[str, Any]) -> None:
        expected: set[str] = set()
        for volume_number in range(1, len(state["plan"]["volumes"]) + 1):
            chapters = state["chapters"].get(str(volume_number))
            if not isinstance(chapters, list) or not chapters:
                raise ContractError("必要な章がありません")
            for chapter in chapters:
                for scene_number in range(1, chapter["scene_count"] + 1):
                    expected.add(self._scene_id(volume_number, chapter["number"], scene_number))
        scenes = state["scenes"]
        actual = {scene.get("scene_id") for scene in scenes if isinstance(scene, dict)}
        if actual != expected:
            raise ContractError("必要な場面が欠落または不正です")
        contents = [scene.get("content") for scene in scenes]
        if not all(isinstance(content, str) and content.strip() for content in contents):
            raise ContractError("空本文があります")
        if len(contents) != len(set(contents)):
            raise ContractError("場面本文が重複しています")

    def _write_output(self, state: dict[str, Any]) -> list[Path]:
        self._validate_manuscript_state(state)
        self.workspace.mkdir(parents=True, exist_ok=True)
        output = self.workspace / "output"
        staging = Path(tempfile.mkdtemp(prefix=".output-", dir=self.workspace))
        paths: list[Path] = []
        try:
            for volume_number, volume in enumerate(state["plan"]["volumes"], 1):
                chapters = {chapter["number"]: chapter["title"] for chapter in state["chapters"][str(volume_number)]}
                scenes = [scene for scene in state["scenes"] if scene["volume"] == volume_number]
                lines = [f"# 第{volume_number}巻 {volume['title']}", "<!-- 無料導入巻 -->" if volume_number == 1 else "<!-- 販売対象巻 -->", ""]
                current = None
                for scene in scenes:
                    if current != scene["chapter"]:
                        current = scene["chapter"]
                        lines.extend([f"## 第{current}章 {chapters[current]}", ""])
                    lines.extend([scene["content"], ""])
                path = staging / f"volume-{volume_number:02d}.md"
                path.write_text("\n".join(lines), encoding="utf-8")
                paths.append(path)
            series = staging / "series.md"
            series.write_text("\n\n".join(path.read_text(encoding="utf-8") for path in paths), encoding="utf-8")
            self._validate_output(paths, series)
            backup = self.workspace / ".output-previous"
            if backup.exists():
                shutil.rmtree(backup)
            if output.exists():
                output.replace(backup)
            staging.replace(output)
            if backup.exists():
                shutil.rmtree(backup)
            return [output / path.name for path in paths]
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise

    @staticmethod
    def _validate_output(paths: list[Path], series: Path) -> None:
        bodies = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if "## 第" not in text:
                raise ContractError(f"必要な章がない出力です: {path.name}")
            body = "\n".join(line for line in text.splitlines() if not line.startswith("#") and not line.startswith("<!--")).strip()
            if not body:
                raise ContractError(f"空本文の出力です: {path.name}")
            bodies.append(body)
        if len(bodies) != len(set(bodies)):
            raise ContractError("巻本文が重複しています")
        if not series.exists() or not series.read_text(encoding="utf-8").strip():
            raise ContractError("全巻Markdownがありません")

    def _volume_paths(self) -> list[Path]:
        return sorted((self.workspace / "output").glob("volume-*.md"))

    def _result(self, state: dict[str, Any], paths: list[Path] | None = None) -> RunResult:
        return RunResult(completed=bool(state["completed"]), volume_count=len(state["plan"]["volumes"]) if state["plan"] else 0, volume_paths=paths or self._volume_paths(), series_path=self.workspace / "output" / "series.md", closure=state["closure"])
