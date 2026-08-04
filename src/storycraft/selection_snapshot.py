"""不変 selection snapshot の保存と検証。"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from .artifact_ids import reserve_counter
from .artifact_registry import artifact_spec
from .filesystem_security import atomic_write_text, assert_no_symlink_path, read_text_nofollow
from .series_contracts import ContractError
from .time_contract import parse_utc_timestamp


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
        assert_no_symlink_path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        assert_no_symlink_path(self.root, require_directory=True)
        directory.mkdir(parents=True)
        try:
            atomic_write_text(record, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        except OSError as exc:
            raise ContractError("selection snapshotを保存できません") from exc
        return value

    def load(self, selection_id: str) -> dict[str, Any]:
        _require_id(selection_id, "selection-", "selection_id")
        path = self.root / selection_id / "record.json"
        try:
            value = json.loads(read_text_nofollow(path))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("selection snapshotを読み込めません") from exc
        validated = validate_selection_snapshot(value)
        if validated["selection_id"] != selection_id:
            raise ContractError("selection snapshot IDと保存先が一致しません")
        return validated

    def _reserve_id(self) -> str:
        return f"selection-{reserve_counter(self.workspace_root, 'next_selection'):06d}"


def _is_valid_slot(slot: str) -> bool:
    if slot in {"request", "settings", "initial_design", "initial_design_adoption", "current_state", "series_plan", "series_plan_adoption"}:
        return True
    patterns = (
        r"(?:volume_plan|volume_plan_adoption)\.v[0-9]{2}",
        r"(?:chapter_plan|chapter_plan_adoption)\.v[0-9]{2}\.c[0-9]{2}",
        r"(?:scene_plan|scene_plan_adoption|scene_card|scene_card_adoption|scene_prose|scene_prose_adoption|scene_prose_disposition|continuity_update|continuity_adoption|continuity_disposition|scene|scene_commit)\.v[0-9]{2}\.c[0-9]{2}\.s[0-9]{2}",
    )
    return any(re.fullmatch(pattern, slot) is not None for pattern in patterns)


def _require_id(value: object, prefix: str, label: str) -> None:
    try:
        artifact_spec("selection").match_id(value)
    except ContractError:
        raise ContractError(f"{label}が不正です")


def _parse_timestamp(value: object) -> None:
    parse_utc_timestamp(value, "created_at")
