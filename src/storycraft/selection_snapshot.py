"""不変 selection snapshot の保存と検証。"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any

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
        if not isinstance(slot, str) or not slot or not isinstance(artifact_id, str) or not artifact_id:
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
        self.counter_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            counters = json.loads(self.counter_path.read_text(encoding="utf-8")) if self.counter_path.exists() else {}
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("counters.jsonを読み込めません") from exc
        value = counters.get("next_selection", 1)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ContractError("next_selectionが不正です")
        counters["next_selection"] = value + 1
        temporary = self.counter_path.with_suffix(".json.tmp")
        try:
            temporary.write_text(json.dumps(counters, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, self.counter_path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise ContractError("counters.jsonを保存できません") from exc
        return f"selection-{value:06d}"


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
