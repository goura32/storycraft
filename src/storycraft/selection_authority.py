"""Resolve immutable selection slots to verified on-disk V2 records."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact_record import validate_record
from .artifact_registry import ARTIFACT_SPECS, artifact_directory, validate_artifact_reference
from .selection_snapshot import validate_selection_snapshot
from .series_contracts import ContractError


def resolve_selection(workspace_root: Path, snapshot: object) -> dict[str, dict[str, Any]]:
    value = validate_selection_snapshot(snapshot)
    resolved: dict[str, dict[str, Any]] = {}
    for slot, artifact_id in value["slots"].items():
        kind = _kind_for(slot, artifact_id)
        validate_artifact_reference(kind, artifact_id, slot)
        record_path = workspace_root / artifact_directory(kind, artifact_id) / "record.json"
        if record_path.is_symlink() or not record_path.is_file():
            raise ContractError("selectionのrecord.jsonが通常ファイルではありません")
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("selectionのrecord.jsonを読み込めません") from exc
        resolved[slot] = validate_record(kind, artifact_id, record)
    return resolved


def _kind_for(slot: str, artifact_id: str) -> str:
    if slot.startswith("scene_prose_disposition."):
        return "quality-disposition"
    matches: list[str] = []
    for kind, spec in ARTIFACT_SPECS.items():
        if kind == "quality-disposition":
            continue
        try:
            validate_artifact_reference(kind, artifact_id, slot)
        except ContractError:
            continue
        matches.append(kind)
    if len(matches) != 1:
        raise ContractError("selection slotからartifact kindを一意に解決できません")
    return matches[0]
