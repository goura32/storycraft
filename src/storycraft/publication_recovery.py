"""v2 volume_publication manifest の provider-free recovery 境界。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .run_state import RunStateStore
from .series_contracts import ContractError
from .volume_publication_stage import VolumePublicationStageService


def execute_publication_recovery(
    workspace_root: Path,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """保存済み公開 manifest だけから前進する。LLMは呼ばない。"""
    root = workspace_root.expanduser()
    current = RunStateStore(root).load()
    if state is not None and current != state:
        raise ContractError("公開recovery開始前にrun-stateが変更されています")
    return VolumePublicationStageService(root).recover_pending(
        updated_at=current["updated_at"],
    )
