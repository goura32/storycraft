"""§4 機械処理する応答の検証。

- 構造・必須項目・型
- 既知ID、許可されたIDの候補集合
- enum値
- ID間の参照関係

未知ID、未知enum、許可されていない既知ID、ID形式不正、参照先不在は
すべてスキーマ不正と同じ扱いにする。推測補正・自動作成・置換はしない。
"""
from __future__ import annotations

import re
from typing import Any

ID_RE = re.compile(r"^(char|rel|entity|time|thread)-\d{2,}$")
ID_PREFIX = {"char", "rel", "entity", "time", "thread"}


class ValidationError(Exception):
    pass


def check_structure(obj: Any, required: list[str]) -> None:
    if not isinstance(obj, dict):
        raise ValidationError("応答がオブジェクトではありません")
    for key in required:
        if key not in obj:
            raise ValidationError(f"必須項目がありません: {key}")


def check_id(value: str) -> str:
    if not isinstance(value, str) or not ID_RE.match(value):
        raise ValidationError(f"ID形式が不正です: {value!r}")
    return value


def check_id_in(value: str, allowed: set[str]) -> str:
    check_id(value)
    if value not in allowed:
        raise ValidationError(f"許可されていないIDです: {value} (許可: {sorted(allowed)})")
    return value


def check_enum(value: str, allowed: set[str]) -> str:
    if value not in allowed:
        raise ValidationError(f"許可されていないenum値です: {value} (許可: {sorted(allowed)})")
    return value


THREAD_ACTION_ENUM = {"導入", "進展", "回収", "展開"}
THREAD_STATUS_ENUM = {"未導入", "進行中", "回収済み"}
TIMELINE_STATUS_ENUM = {"予定", "進行中", "完了", "失効"}
CHARACTER_UPDATE_FIELD_ENUM = {
    "current_goal", "current_pressure", "current_location",
    "current_condition", "current_knowledge", "current_state",
}
ENTITY_UPDATE_FIELD_ENUM = {"current_state"}


def validate_plan_response(obj: Any, allowed_ids: set[str]) -> None:
    """全巻計画応答 (§5 単位1) の検証。"""
    required = ["volume_count", "volumes", "final_resolution", "series_viewpoint_rule"]
    check_structure(obj, required)
    if not isinstance(obj["volume_count"], int) or not (4 <= obj["volume_count"] <= 10):
        raise ValidationError("volume_count は 4-10 の整数でなければなりません")
    if not isinstance(obj["volumes"], list) or len(obj["volumes"]) != obj["volume_count"]:
        raise ValidationError("volumes の数が volume_count と一致しません")
    for v in obj["volumes"]:
        check_structure(v, ["number", "title", "role", "character_changes", "resolves", "leaves", "chapter_count", "viewpoint_rule"])
        if not (6 <= v.get("chapter_count", 0) <= 10):
            raise ValidationError("chapter_count は 6-10 でなければなりません")


def validate_characters_response(obj: Any, allowed_ids: set[str]) -> None:
    """登場人物・関係カード応答 (§5 単位2) の検証。"""
    required = ["characters", "relationships"]
    check_structure(obj, required)
    for c in obj["characters"]:
        check_structure(c, ["id", "name", "role", "narrative_function"])
    for r in obj["relationships"]:
        check_structure(r, ["id", "character_a_id", "character_b_id", "current_state", "reader_knowledge", "relationship_thread_id"])


def validate_world_response(obj: Any, allowed_ids: set[str]) -> None:
    """世界台帳応答 (§5 単位3) の検証。"""
    required = ["entities"]
    check_structure(obj, required)
    for e in obj["entities"]:
        check_structure(e, ["id", "kind", "name", "aliases", "stable_fact", "use_or_access_rule", "current_state"])


def validate_timeline_response(obj: Any, allowed_ids: set[str]) -> None:
    """時間・期限台帳応答 (§5 単位4) の検証。"""
    required = ["timelines"]
    check_structure(obj, required)
    for t in obj["timelines"]:
        check_structure(t, ["id", "kind", "description", "starts_at", "ends_at", "related_ids", "status", "actual_scene"])
        check_enum(t["status"], TIMELINE_STATUS_ENUM)


def validate_threads_response(obj: Any, allowed_ids: set[str]) -> None:
    """伏線台帳応答 (§5 単位5) の検証。"""
    required = ["threads"]
    check_structure(obj, required)
    for t in obj["threads"]:
        check_structure(t, ["id", "kind", "importance", "description", "core_fact", "involved_characters",
                            "reader_knowledge", "character_knowledge", "presentation_rule", "clue_plan",
                            "must_not_reveal_before", "introduce_by", "resolve_by", "resolution_condition", "status"])
        check_enum(t["importance"], {"主要", "補助"})
        check_enum(t["status"], THREAD_STATUS_ENUM)
        for cid in t.get("involved_characters", []):
            check_id_in(cid, allowed_ids)


def validate_volume_chapters_response(obj: Any, allowed_ids: set[str]) -> None:
    """巻の章一覧応答 (§5 単位6) の検証。"""
    required = ["chapters"]
    check_structure(obj, required)
    for c in obj["chapters"]:
        check_structure(c, ["chapter_number", "title", "purpose", "start_state", "end_state", "scene_count"])
        if not (2 <= c.get("scene_count", 0) <= 4):
            raise ValidationError("scene_count は 2-4 でなければなりません")


def validate_scene_cards_response(obj: Any, allowed_ids: set[str]) -> None:
    """場面カード応答 (§5 単位7) の検証。"""
    required = ["scene_cards"]
    check_structure(obj, required)
    for sc in obj["scene_cards"]:
        check_structure(sc, ["scene_number", "viewpoint_character", "start_time", "end_time", "location_id",
                             "entity_ids", "purpose", "opening", "required_events", "characters",
                             "thread_actions", "reader_disclosure", "presentation_rules", "end_change"])
        for ta in sc.get("thread_actions", []):
            check_id_in(ta["id"], allowed_ids)
            check_enum(ta["action"], THREAD_ACTION_ENUM)
        for eid in sc.get("entity_ids", []):
            check_id_in(eid, allowed_ids)
        if sc.get("location_id"):
            check_id_in(sc["location_id"], allowed_ids)


def validate_volume_summary_response(obj: Any, allowed_ids: set[str]) -> None:
    """巻要約応答 (§5 単位9) の検証。"""
    required = ["volume_summary", "unresolved_questions", "character_relations"]
    check_structure(obj, required)


def validate_closure_response(obj: Any, allowed_ids: set[str]) -> None:
    """完結前確認応答 (§5 単位10) の検証。"""
    required = ["results"]
    check_structure(obj, required)
    for r in obj["results"]:
        check_structure(r, ["thread_id", "status", "scene"])
        check_enum(r["status"], {"回収済み", "未回収"})
        check_id_in(r["thread_id"], allowed_ids)


def validate_critique_response(obj: Any, allowed_ids: set[str]) -> None:
    """批評応答 (§3.13) の検証。"""
    required = ["issues", "overall_assessment"]
    check_structure(obj, required)
    if not isinstance(obj["issues"], list):
        raise ValidationError("issues は配列でなければなりません")
    for issue in obj["issues"]:
        check_structure(issue, ["severity", "category", "location", "problem", "suggestion"])
        check_enum(issue["severity"], {"致命的", "重要", "軽微", "主要"})
    if not isinstance(obj["overall_assessment"], str):
        raise ValidationError("overall_assessment は文字列でなければなりません")


def validate_fix_response(obj: Any, allowed_ids: set[str]) -> None:
    """修正応答 (§3.13) の検証。場面執筆と同一構造。"""
    validate_scene_response(obj, allowed_ids)


def validate_scene_response(obj: Any, allowed_ids: set[str]) -> None:
    """場面執筆応答 (§5 単位8) の検証。"""
    required = ["content", "handoff_summary", "thread_updates", "character_updates",
                "relationship_updates", "entity_updates", "timeline_updates"]
    check_structure(obj, required)
    if not isinstance(obj["content"], str) or not obj["content"].strip():
        raise ValidationError("content が空です")
    for u in obj["thread_updates"]:
        check_id_in(u["id"], allowed_ids)
        check_enum(u["action"], THREAD_ACTION_ENUM)
    for u in obj["character_updates"]:
        check_id_in(u["character_id"], allowed_ids)
        check_enum(u["field"], CHARACTER_UPDATE_FIELD_ENUM)
    for u in obj["relationship_updates"]:
        check_id_in(u["relationship_id"], allowed_ids)
    for u in obj["entity_updates"]:
        check_id_in(u["entity_id"], allowed_ids)
        check_enum(u["field"], ENTITY_UPDATE_FIELD_ENUM)
    for u in obj["timeline_updates"]:
        check_id_in(u["timeline_id"], allowed_ids)
        check_enum(u["status"], TIMELINE_STATUS_ENUM)
