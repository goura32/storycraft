"""v2 run の recovery-first dispatcher。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .publication_recovery import execute_publication_recovery
from .run_state import RunStateStore
from .series_contracts import ContractError
from .volume_publication_stage import VolumePublicationStageService
from .workspace_lock import workspace_lock


class RunUnavailable(ContractError):
    """健全だが未実装の次工程、または停止済み run を示す。"""


def run_v2(workspace_root: Path) -> dict[str, Any]:
    """最初に保存済み確定を収束する。LLMは必要になるまで初期化しない。"""
    root = workspace_root.expanduser()
    with workspace_lock(root):
        store = RunStateStore(root)
        state = store.load()
        if state["status"] == "blocked":
            raise RunUnavailable("blocked workspaceはrunできません")
        if state["status"] == "completed":
            return state
        pending = state["pending_commit"]
        if isinstance(pending, dict):
            if pending.get("kind") != "volume_publication":
                raise RunUnavailable("未移行のpending_commitはrunできません")
            try:
                return execute_publication_recovery(root, state)
            except ContractError as exc:
                blocked = dict(state)
                blocked.update({"status": "blocked", "stop_reason": "manual_review_required", "last_error": {"code": "publication_invalid", "message": str(exc), "evidence_refs": [], "occurred_at": state["updated_at"]}})
                store.save(blocked)
                raise RunUnavailable("publication_invalid") from exc
        if state["current_stage"] == "volume_publication":
            try:
                return VolumePublicationStageService(root).run(updated_at=state["updated_at"])
            except ContractError as exc:
                blocked = dict(state)
                blocked.update({"status": "blocked", "stop_reason": "manual_review_required", "last_error": {"code": "publication_invalid", "message": str(exc), "evidence_refs": [], "occurred_at": state["updated_at"]}})
                store.save(blocked)
                raise RunUnavailable("publication_invalid") from exc
        raise RunUnavailable("このv2工程のdispatcherは未実装です")
