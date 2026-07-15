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


THREAD_ACTION_ENUM = {"導入", "進展", "回収"}
THREAD_STATUS_ENUM = {"未導入", "進行中", "回収済み"}
TIMELINE_STATUS_ENUM = {"予定", "進行中", "完了", "失効"}
UPDATE_FIELD_ENUM = {
    "current_goal", "current_pressure", "current_location",
    "current_condition", "current_knowledge", "current_state",
}


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
        check_enum(u["field"], UPDATE_FIELD_ENUM)
    for u in obj["relationship_updates"]:
        check_id_in(u["relationship_id"], allowed_ids)
    for u in obj["entity_updates"]:
        check_id_in(u["entity_id"], allowed_ids)
        check_enum(u["field"], UPDATE_FIELD_ENUM)
    for u in obj["timeline_updates"]:
        check_id_in(u["timeline_id"], allowed_ids)
        check_enum(u["status"], TIMELINE_STATUS_ENUM)
