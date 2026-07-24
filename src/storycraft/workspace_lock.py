"""Storycraft V1 workspaceの単一writer lock。"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import stat
from typing import Iterator

from .series_contracts import ContractError


@contextmanager
def workspace_lock(
    workspace_root: Path,
) -> Iterator[None]:
    """V1 workspaceの排他lockを非待機で取得する。"""
    root = workspace_root.expanduser()
    lock_path = root / "runtime/lock"

    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = -1
    handle = None

    try:
        try:
            descriptor = os.open(lock_path, flags)
        except FileNotFoundError as exc:
            raise ContractError(
                "V1 workspace lockがありません"
            ) from exc
        except OSError as exc:
            raise ContractError(
                "V1 workspace lockを開けません"
            ) from exc

        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ContractError(
                "V1 workspace lockは通常fileでなければなりません"
            )

        handle = os.fdopen(
            descriptor,
            "r+",
            encoding="utf-8",
            closefd=True,
        )
        descriptor = -1

        try:
            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError as exc:
            raise ContractError(
                "このV1 workspaceは別の実行で使用中です"
            ) from exc

        try:
            yield
        finally:
            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_UN,
            )
    finally:
        if handle is not None:
            handle.close()
        elif descriptor >= 0:
            os.close(descriptor)
