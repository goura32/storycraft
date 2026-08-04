"""巻単位公開の決定的組立・検証。"""
from __future__ import annotations

import re
from typing import Any

from .artifact_registry import artifact_spec
from .series_contracts import ContractError
from .time_contract import parse_utc_timestamp

_PUBLICATION_ID = re.compile(r"^volume-pub-v[0-9]{2}-[0-9]{6}$")


def build_volume_publication_files(
    *, publication_id: str, volume_number: int, input_selection_id: str,
    settings_id: str, series_plan_id: str, volume_plan_id: str,
    current_state_id: str, chapter_plan_ids: list[str], scene_ids: list[str],
    quality_disposition_refs: list[str], scenes: list[dict[str, Any]],
    created_at: str, remaining_major_issues: bool = False,
) -> dict[str, dict[str, Any] | str]:
    """一巻だけの公開記録と読者向け原稿を決定的に組み立てる。"""
    if not isinstance(volume_number, int) or isinstance(volume_number, bool) or volume_number < 1:
        raise ContractError("volume_numberは1以上の整数でなければなりません")
    _identifier(publication_id, rf"^volume-pub-v{volume_number:02d}-[0-9]{{6}}$", "volume_publication_id")
    for kind, value, label in (("selection", input_selection_id, "input_selection_id"), ("settings", settings_id, "settings_id"), ("series-plan", series_plan_id, "series_plan_id"), ("volume-plan", volume_plan_id, "volume_plan_id"), ("generation", current_state_id, "current_state_id")):
        try:
            match = artifact_spec(kind).match_id(value)
        except ContractError as exc:
            raise ContractError(f"{label}が不正です") from exc
        if kind == "volume-plan" and int(match.group("volume")) != volume_number:
            raise ContractError(f"{label}の巻番号が不正です")
    _timestamp(created_at)
    if not chapter_plan_ids or len(chapter_plan_ids) != len(set(chapter_plan_ids)):
        raise ContractError("chapter_plan_idsが不正です")
    for item in chapter_plan_ids:
        try:
            match = artifact_spec("chapter-plan").match_id(item)
        except ContractError as exc:
            raise ContractError("chapter_plan_idsが不正です") from exc
        if int(match.group("volume")) != volume_number:
            raise ContractError("chapter_plan_idsの巻番号が不正です")
    if not scene_ids or len(scene_ids) != len(set(scene_ids)):
        raise ContractError("scene_idsが不正です")
    for item in scene_ids:
        try:
            match = artifact_spec("scene").match_id(item)
        except ContractError as exc:
            raise ContractError("scene_idsが不正です") from exc
        if int(match.group("volume")) != volume_number:
            raise ContractError("scene_idsの巻番号が不正です")
    if len(quality_disposition_refs) != len(scene_ids):
        raise ContractError("quality_disposition_refsがscene_idsと一致しません")
    for item in quality_disposition_refs:
        try:
            artifact_spec("quality-disposition").match_id(item)
        except ContractError as exc:
            raise ContractError("quality_disposition_refsがscene_idsと一致しません") from exc
    if len(scenes) != len(scene_ids): raise ContractError("scenesがscene_idsと一致しません")
    prose: list[str] = []
    for expected, scene in zip(scene_ids, scenes, strict=True):
        if not isinstance(scene, dict) or set(scene) != {"scene_id", "prose"} or scene["scene_id"] != expected or not isinstance(scene["prose"], str) or not scene["prose"].strip():
            raise ContractError("scenesの要素が不正です")
        prose.append(scene["prose"].strip())
    record: dict[str, Any] = {"schema_version": 1, "volume_publication_id": publication_id, "volume_number": volume_number, "input_selection_id": input_selection_id, "created_at": created_at}
    manuscript = "\n\n".join(prose) + "\n"
    if remaining_major_issues:
        record["publication_notice_type"] = "編集"
        manuscript = "編集上の注意があります。\n\n" + manuscript
    return {"record.json": record, "manuscript.md": manuscript}


def validate_volume_publication_files(files: object) -> None:
    """確定前後の公開二ファイルを同一規則で検証する。"""
    if not isinstance(files, dict) or set(files) != {"record.json", "manuscript.md"}: raise ContractError("巻公開はrecord.jsonとmanuscript.mdだけを持つ必要があります")
    record, manuscript = files["record.json"], files["manuscript.md"]
    if not isinstance(record, dict) or not isinstance(manuscript, str): raise ContractError("巻公開ファイルの型が不正です")
    required = {"schema_version", "volume_publication_id", "volume_number", "input_selection_id", "created_at"}
    if set(record) not in (required, required | {"publication_notice_type"}): raise ContractError("巻公開record.jsonのfield構成が不正です")
    if record["schema_version"] != 1: raise ContractError("巻公開record.json.schema_versionは1でなければなりません")
    number = record["volume_number"]
    if not isinstance(number, int) or isinstance(number, bool) or number < 1: raise ContractError("巻公開record.json.volume_numberが不正です")
    _identifier(record["volume_publication_id"], rf"^volume-pub-v{number:02d}-[0-9]{{6}}$", "volume_publication_id")
    try:
        artifact_spec("selection").match_id(record["input_selection_id"])
    except ContractError as exc:
        raise ContractError("巻公開record.json.input_selection_idが不正です") from exc

    _timestamp(record["created_at"])
    notice = record.get("publication_notice_type")
    if "publication_notice_type" in record and notice != "編集": raise ContractError("publication_notice_typeは編集のみ許可されます")
    prefix = "編集上の注意があります。\n\n" if notice == "編集" else ""
    if not manuscript.startswith(prefix) or not manuscript.endswith("\n") or not manuscript[len(prefix):].strip(): raise ContractError("巻公開manuscript.mdが公開注意または本文契約を満たしません")


def _identifier(value: object, pattern: str, label: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(pattern, value): raise ContractError(f"{label}が不正です")


def _timestamp(value: object) -> None:
    parse_utc_timestamp(value, "created_at")
