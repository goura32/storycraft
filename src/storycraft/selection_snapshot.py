"""不変 selection snapshot の保存と検証。"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
from typing import Any

from .artifact_ids import reserve_counter
from .series_contracts import ContractError


_REQUIRED_FIELDS = frozenset({
    "schema_version",
    "selection_id",
    "input_selection_id",
    "slots",
    "created_at",
})


def validate_selection_snapshot(value: object) -> dict[str, Any]:
    """選択スナップショットの局所契約を検証する。"""
    if not isinstance(value, dict) or set(value) != _REQUIRED_FIELDS:
        raise ContractError("selection snapshotのfield構成が不正です")
    if value["schema_version"] != 1:
        raise ContractError("selection snapshot.schema_versionは1でなければなりません")
    _require_id(value["selection_id"], "selection-", "selection_id")
    parent = value["input_selection_id"]
    if parent is not None:
        _require_id(parent, "selection-", "input_selection_id")
        if parent == value["selection_id"]:
            raise ContractError("input_selection_idは自身を参照できません")
    slots = value["slots"]
    if not isinstance(slots, dict) or not slots:
        raise ContractError("slotsは空でないオブジェクトでなければなりません")
    for slot, artifact_id in slots.items():
        if not isinstance(slot, str) or not _is_valid_slot(slot) or not isinstance(artifact_id, str) or not artifact_id:
            raise ContractError("slotsが不正です")
        if artifact_id.startswith("selection-"):
            raise ContractError("slotsはselection snapshotを参照できません")
    _parse_timestamp(value["created_at"])
    return value


class SelectionSnapshotStore:
    """runtime/selections 下の selection snapshot を一度だけ保存する。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.root = self.workspace_root / "runtime" / "selections"
        self.counter_path = self.workspace_root / "runtime" / "counters.json"

    def create(
        self,
        *,
        slots: dict[str, str],
        created_at: str,
        input_selection_id: str | None = None,
        selection_id: str | None = None,
    ) -> dict[str, Any]:
        if selection_id is None:
            selection_id = self._reserve_id()
        value = {
            "schema_version": 1,
            "selection_id": selection_id,
            "input_selection_id": input_selection_id,
            "slots": dict(slots),
            "created_at": created_at,
        }
        validate_selection_snapshot(value)
        directory = self.root / selection_id
        record = directory / "record.json"
        if directory.exists() or directory.is_symlink():
            raise ContractError("selection snapshotは不変で上書きできません")
        directory.mkdir(parents=True)
        try:
            with record.open("x", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
        except OSError as exc:
            raise ContractError("selection snapshotを保存できません") from exc
        return value

    def load(self, selection_id: str) -> dict[str, Any]:
        _require_id(selection_id, "selection-", "selection_id")
        path = self.root / selection_id / "record.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("selection snapshotを読み込めません") from exc
        validated = validate_selection_snapshot(value)
        if validated["selection_id"] != selection_id:
            raise ContractError("selection snapshot IDと保存先が一致しません")
        return validated

    def _reserve_id(self) -> str:
        return f"selection-{reserve_counter(self.workspace_root, 'next_selection'):06d}"


def _is_valid_slot(slot: str) -> bool:
    return bool(
        re.fullmatch(r"[a-z_]+", slot)
        or re.fullmatch(r"[a-z_]+\.v[0-9]{2}(\.c[0-9]{2})?(\.s[0-9]{2})?", slot)
        or re.fullmatch(r"scene_prose_disposition\.v[0-9]{2}\.c[0-9]{2}\.s[0-9]{2}", slot)
    )


def _require_id(value: object, prefix: str, label: str) -> None:
    if not isinstance(value, str) or not value.startswith(prefix) or len(value) == len(prefix):
        raise ContractError(f"{label}が不正です")


def _parse_timestamp(value: object) -> None:
    if not isinstance(value, str):
        raise ContractError("created_atはISO 8601文字列でなければなりません")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("created_atがISO 8601形式ではありません") from exc
