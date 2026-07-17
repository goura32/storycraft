"""シリーズ工程の契約型と決定的検証。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


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


class ContractValidator:
    """モデル入出力と状態の決定的な製品契約を検証する。"""

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
            ContractValidator._require(record, "name", "role", "narrative_function", "fixed_profile")
            ContractValidator._initial_state(record)
            if "id" in record:
                raise ContractError("人物IDはプログラムが採番します")

    @staticmethod
    def _validate_relationships(value: dict[str, Any], characters: list[dict[str, Any]]) -> None:
        records = value.get("relationships")
        ids = {record["id"] for record in characters}
        if not isinstance(records, list):
            raise ContractError("関係台帳が配列ではありません")
        for record in records:
            ContractValidator._require(record, "character_a_id", "character_b_id", "fixed_meaning")
            ContractValidator._initial_state(record)
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
            ContractValidator._require(record, "kind", "name", "stable_fact", "use_or_access_rule")
            ContractValidator._initial_state(record)
            if "id" in record:
                raise ContractError("世界IDはプログラムが採番します")

    @staticmethod
    def _validate_timeline(value: dict[str, Any], known_ids: set[str]) -> None:
        records = value.get("timelines")
        if not isinstance(records, list):
            raise ContractError("時間台帳が配列ではありません")
        for record in records:
            ContractValidator._require(record, "kind", "description", "related_ids", "fixed_rule")
            ContractValidator._initial_state(record)
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
            ContractValidator._require(record, "kind", "importance", "description", "author_truth", "reader_knowledge", "character_knowledge", "presentation_rule", "introduce_by", "resolve_by", "resolution_condition")
            state = ContractValidator._initial_state(record)
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
            ContractValidator._require(chapter, "title", "purpose", "start_state", "end_state")
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
            ContractValidator._require(issue, "field", "description", "suggestion")

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