"""新規 v2 workspace の初期化・静的検証。"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Optional

from .artifact_ids import initial_counters
from .run_state import RunStateStore
from .selection_authority import resolve_selection
from .selection_snapshot import SelectionSnapshotStore
from .series_contracts import ContractError


_V2_DIRECTORIES = (
    "inputs", "quality", "runtime", "runtime/settings", "runtime/staging",
    "runtime/selections", "runtime/calls", "runtime/validations", "design",
    "design/initial", "design/series-plans", "design/volume-plans",
    "design/chapter-plans", "design/scene-plans", "generations", "scenes",
    "publications",
)


def create_workspace(
    workspace_root: Path,
    *,
    workspace_id: str,
    request: Optional[dict[str, Any]],
    settings: dict[str, Any],
    created_at: str,
    keywords: Optional[dict[str, Any]] = None,
) -> Path:
    """既存worktreeを触らず、新形式だけを持つ作業場所を作る。"""
    root = workspace_root.expanduser()
    if root.exists() or root.is_symlink():
        raise ContractError("workspaceが既に存在します")
    if (request is None) == (keywords is None):
        raise ContractError("requestまたはkeywordsの一方だけが必要です")
    if request is not None and not isinstance(request, dict):
        raise ContractError("requestはobjectでなければなりません")
    if keywords is not None and not isinstance(keywords, dict):
        raise ContractError("keywordsはobjectでなければなりません")
    if request is not None:
        _validate_request(request)
    if keywords is not None:
        _validate_keywords(keywords)
    _validate_settings(settings)
    if not isinstance(workspace_id, str) or not workspace_id.startswith("ws-"):
        raise ContractError("workspace_idが不正です")
    root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{root.name}.v2-", dir=root.parent))
    try:
        for relative in _V2_DIRECTORIES:
            (staging / relative).mkdir(parents=True, exist_ok=True)
        settings_id = "settings-000001"
        _write_json(staging / "runtime/settings" / settings_id / "record.json", {
            "schema_version": 1,
            "settings_id": settings_id,
            "payload": settings,
            "created_at": created_at,
        })
        counters = initial_counters()
        counters["next_settings"] = 2
        if request is not None:
            request_id = "request-000001"
            _write_json(staging / "inputs" / request_id / "record.json", {
                "schema_version": 1,
                "request_id": request_id,
                "payload": request,
                "created_at": created_at,
            })
            counters["next_request"] = 2
            _write_json(staging / "runtime/counters.json", counters)
            selection = SelectionSnapshotStore(staging).create(slots={
                "request": request_id,
                "settings": settings_id,
            }, created_at=created_at)
            stage, selection_id = "initial_design", selection["selection_id"]
        else:
            assert keywords is not None
            keywords_id = "keywords-000001"
            _write_json(staging / "inputs" / keywords_id / "record.json", {
                "schema_version": 1,
                "keywords_id": keywords_id,
                **keywords,
                "created_at": created_at,
            })
            counters["next_keywords"] = 2
            _write_json(staging / "runtime/counters.json", counters)
            stage, selection_id = "request_intake", None
        _write_json(staging / "runtime/counters.json", counters)
        state = {
            "schema_version": 3,  # V1 の schema_version に合わせる
            "workspace_id": workspace_id,
            # v1 では run_id と stop_reason は保存しない
            "status": "running",
            "last_error": None,
            "current_stage": stage,
            "current_target": {},
            "current_selection_id": selection_id,
            "active_candidate": None,
            "active_scene_id": None,
            "pending_commit": None,
            "published_volumes": [],
            "created_at": created_at,
            "updated_at": created_at,
        }
        RunStateStore(staging).save(state)
        (staging / "runtime/lock").touch(exist_ok=False)
        validate_workspace(staging)
        os.rename(staging, root)
        return root
    except Exception:
        # staging はこの関数だけが作った未公開領域。失敗時に残さない。
        import shutil
        shutil.rmtree(staging, ignore_errors=True)
        raise


def validate_workspace(workspace_root: Path) -> None:
    """providerを初期化せず、新形式の正本・参照を静的に検証する。"""
    root = workspace_root.expanduser()
    if not root.is_dir() or root.is_symlink():
        raise ContractError("v2 workspace directoryが存在しません")
    for relative in _V2_DIRECTORIES:
        if not (root / relative).is_dir() or (root / relative).is_symlink():
            raise ContractError(f"v2 workspace必須directoryがありません: {relative}")
    state = RunStateStore(root).load()
    selection_id = state["current_selection_id"]
    if selection_id is None:
        if state["current_stage"] != "request_intake":
            raise ContractError("selectionなしのstageが不正です")
        return
    assert isinstance(selection_id, str)
    snapshot = SelectionSnapshotStore(root).load(selection_id)
    resolve_selection(root, snapshot)


def _validate_request(value: Optional[dict[str, Any]]) -> None:
    if value is None:
        return
    fields = {"title", "genre", "premise", "required_elements", "forbidden_elements", "ending_preference", "volume_count", "language"}
    if set(value) != fields or value.get("language") != "ja":
        raise ContractError("request schemaが不正です")
    for key in ("title", "genre", "premise", "ending_preference"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ContractError(f"request {key}が不正です")
    for key in ("required_elements", "forbidden_elements"):
        item = value.get(key)
        if not isinstance(item, list) or any(not isinstance(x, str) or not x.strip() for x in item) or len(item) != len(set(item)):
            raise ContractError(f"request {key}が不正です")
    count = value.get("volume_count")
    if not isinstance(count, int) or isinstance(count, bool) or not 4 <= count <= 10:
        raise ContractError("request volume_countが不正です")


def _validate_keywords(value: Optional[dict[str, Any]]) -> None:
    if value is None:
        return
    if set(value) != {"keywords", "language"} or value.get("language") != "ja":
        raise ContractError("keywords schemaが不正です")
    words = value.get("keywords")
    if not isinstance(words, list) or not 1 <= len(words) <= 12 or any(not isinstance(x, str) or not 1 <= len(x.strip()) <= 80 for x in words) or len(words) != len(set(words)):
        raise ContractError("keywordsが不正です")


def _validate_settings(value: object) -> None:
    # V1 では max_input_chars は存在しないので必須フィールドから除く（ただし許容する）
    # V1 では request_options は任意（ただし許容する）
    required_fields = {"provider", "endpoint", "model", "technical_retry_limit", "quality_revision_limit", "invalid_response_limit",
              "chapter_per_volume_range", "chapter_scene_range", "scene_text_char_range"}
    if not isinstance(value, dict):
        raise ContractError("settings schemaが不正です")
    missing = required_fields - set(value.keys())
    if missing:
        raise ContractError(f"settingsに必須フィールドがありません: {missing}")
    if value.get("provider") != "ollama":
        raise ContractError("settingsのproviderは'ollama'でなければなりません")
    endpoint = value.get("endpoint")
    if not isinstance(endpoint, str) or not (endpoint.startswith("http://127.") or endpoint.startswith("http://localhost") or endpoint.startswith("http://[::1]") or endpoint.startswith("http://ws2.local:")):
        raise ContractError("endpointはloopback HTTPでなければなりません")
    if not isinstance(value.get("model"), str) or not value["model"]:
        raise ContractError("modelが不正です")
    for key, minimum in (("technical_retry_limit", 1), ("quality_revision_limit", 0), ("invalid_response_limit", 1)):
        item = value.get(key)
        if not isinstance(item, int) or isinstance(item, bool) or item < minimum:
            raise ContractError(f"{key}が不正です")
    for key in ("chapter_per_volume_range", "chapter_scene_range", "scene_text_char_range"):
        pair = value.get(key)
        if not isinstance(pair, list) or len(pair) != 2 or any(not isinstance(x, int) or isinstance(x, bool) for x in pair) or pair[0] > pair[1]:
            raise ContractError(f"{key}が不正です")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")