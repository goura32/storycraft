"""新規 v2 workspace の初期化・静的検証。"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .run_state import RunStateStore
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError


_V2_DIRECTORIES = (
    "inputs", "quality", "runtime", "runtime/settings", "runtime/staging",
    "runtime/selections", "runtime/calls", "runtime/validations", "design",
    "design/initial", "design/series-plans", "design/volume-plans",
    "design/chapter-plans", "design/scene-plans", "generations", "scenes",
    "publications",
)


def create_v2_workspace(
    workspace_root: Path,
    *,
    workspace_id: str,
    request: dict[str, Any],
    settings: dict[str, Any],
    created_at: str,
) -> Path:
    """既存worktreeを触らず、新形式だけを持つ作業場所を作る。"""
    root = workspace_root.expanduser()
    if root.exists() or root.is_symlink():
        raise ContractError("workspaceが既に存在します")
    if not isinstance(request, dict):
        raise ContractError("requestはobjectでなければなりません")
    _validate_settings(settings)
    if not isinstance(workspace_id, str) or not workspace_id.startswith("ws-"):
        raise ContractError("workspace_idが不正です")
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.v2-", dir=root.parent))
    try:
        for relative in _V2_DIRECTORIES:
            (staging / relative).mkdir(parents=True, exist_ok=True)
        request_id = "request-000001"
        settings_id = "settings-000001"
        _write_json(staging / "inputs" / request_id / "record.json", {"schema_version": 1, "request_id": request_id, "payload": request, "created_at": created_at})
        _write_json(staging / "runtime/settings" / settings_id / "record.json", {"schema_version": 1, "settings_id": settings_id, "payload": settings, "created_at": created_at})
        _write_json(staging / "runtime/counters.json", {"next_request": 2, "next_settings": 2, "next_selection": 1, "next_volume_publication": 1})
        selection = SelectionSnapshotStore(staging).create(slots={"request": request_id, "settings": settings_id}, created_at=created_at)
        state = {
            "schema_version": 2, "workspace_id": workspace_id, "run_id": "run-000001",
            "status": "running", "stop_reason": None, "last_error": None,
            "current_stage": "initial_design", "current_target": {},
            "current_selection_id": selection["selection_id"], "active_candidate": None,
            "active_scene_id": None, "pending_commit": None, "published_volumes": [],
            "created_at": created_at, "updated_at": created_at,
        }
        RunStateStore(staging).save(state)
        (staging / "runtime/lock").touch(exist_ok=False)
        validate_v2_workspace(staging)
        os.rename(staging, root)
        return root
    except Exception:
        # staging はこの関数だけが作った未公開領域。失敗時に残さない。
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
        raise


def validate_v2_workspace(workspace_root: Path) -> None:
    """providerを初期化せず、新形式の正本・参照を静的に検証する。"""
    root = workspace_root.expanduser()
    if not root.is_dir() or root.is_symlink():
        raise ContractError("v2 workspace directoryが存在しません")
    for relative in _V2_DIRECTORIES:
        if not (root / relative).is_dir() or (root / relative).is_symlink():
            raise ContractError(f"v2 workspace必須directoryがありません: {relative}")
    state = RunStateStore(root).load()
    selection_id = state["current_selection_id"]
    assert isinstance(selection_id, str)
    snapshot = SelectionSnapshotStore(root).load(selection_id)
    authorities = {
        "request": ("inputs", "request_id"),
        "settings": ("runtime/settings", "settings_id"),
    }
    for slot, artifact_id in snapshot["slots"].items():
        authority = authorities.get(slot)
        if authority is None:
            # この static validator は bootstrap workspace 専用である。
            # 後続 slot を理解しないまま成功にしてはならない。
            raise ContractError(f"未対応のselection slotです: {slot}")
        directory, id_field = authority
        artifact_dir = root / directory / artifact_id
        path = artifact_dir / "record.json"
        if artifact_dir.is_symlink() or not path.is_file() or path.is_symlink():
            raise ContractError(f"selection slotの正本がありません: {slot}")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError(f"selection slotの正本を読めません: {slot}") from exc
        if not isinstance(record, dict) or record.get("schema_version") != 1 or record.get(id_field) != artifact_id:
            raise ContractError(f"selection slotの正本IDが一致しません: {slot}")


def _validate_settings(value: object) -> None:
    fields = {"provider", "endpoint", "model", "technical_retry_limit", "quality_revision_limit", "invalid_response_limit", "chapter_per_volume_range", "chapter_scene_range", "scene_text_char_range", "max_input_chars"}
    if not isinstance(value, dict) or set(value) != fields or value.get("provider") != "ollama": raise ContractError("settings schemaが不正です")
    endpoint = value.get("endpoint")
    if not isinstance(endpoint, str) or not (endpoint.startswith("http://127.") or endpoint.startswith("http://localhost") or endpoint.startswith("http://[::1]")): raise ContractError("endpointはloopback HTTPでなければなりません")
    if not isinstance(value.get("model"), str) or not value["model"]: raise ContractError("modelが不正です")
    for key, minimum in (("technical_retry_limit", 1), ("quality_revision_limit", 0), ("invalid_response_limit", 1), ("max_input_chars", 50000)):
        item = value.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item < minimum or (key == "max_input_chars" and item > 200000): raise ContractError(f"{key}が不正です")
    for key in ("chapter_per_volume_range", "chapter_scene_range", "scene_text_char_range"):
        pair = value.get(key)
        if not isinstance(pair, list) or len(pair) != 2 or any(not isinstance(x, int) or isinstance(x, bool) for x in pair) or pair[0] > pair[1]: raise ContractError(f"{key}が不正です")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
