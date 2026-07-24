"""未採用staging directoryのOrphan隔離。"""
from __future__ import annotations

import os
from pathlib import Path
import re

from .reviewed_candidate_stage import fsync_directory
from .series_contracts import ContractError


def move_directory_to_orphans(
    workspace_root: Path,
    source: Path,
    *,
    updated_at: str,
) -> Path:
    """未採用stagingを上書きせずorphansへ移す。"""
    root = workspace_root.expanduser()
    source = source.expanduser()
    staging_root = root / "runtime/staging"
    orphans_root = root / "runtime/orphans"

    if source.parent != staging_root:
        raise ContractError(
            "Orphanへ移動できるのはruntime/staging直下だけです"
        )

    if source.is_symlink() or not source.is_dir():
        raise ContractError(
            "Recovery対象stagingが通常directoryでは"
            "ないためmanual対応が必要です"
        )

    if (
        orphans_root.is_symlink()
        or not orphans_root.is_dir()
    ):
        raise ContractError(
            "runtime/orphans directoryが存在しません"
        )

    timestamp = re.sub(
        r"[^0-9A-Za-z]",
        "",
        updated_at,
    )
    base = f"{timestamp}-{source.name}"
    destination = orphans_root / base
    suffix = 1

    while destination.exists() or destination.is_symlink():
        destination = (
            orphans_root / f"{base}-{suffix:03d}"
        )
        suffix += 1

    try:
        os.rename(source, destination)
        fsync_directory(staging_root)
        fsync_directory(orphans_root)
    except OSError as exc:
        raise ContractError(
            "stagingをorphansへ移動できません"
        ) from exc

    return destination
