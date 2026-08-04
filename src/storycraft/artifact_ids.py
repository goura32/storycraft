"""Immutable artifact identifiers and atomic counter reservation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
from typing import Final

from .filesystem_security import (
    _open_directory_chain,
    atomic_write_text,
    assert_no_symlink_path,
    directory_fd_path,
    directory_identity,
    open_directory_at,
    read_text_at,
)
from .series_contracts import ContractError

_COUNTERS: Final[frozenset[str]] = frozenset({
    "next_request", "next_settings", "next_keywords", "next_selection",
    "next_generation", "next_quality", "next_call", "next_validation",
    "next_candidate", "next_review", "next_adoption",
    "next_initial_design", "next_series_plan", "next_volume_plan",
    "next_chapter_plan", "next_scene_plan", "next_scene_card", "next_scene_prose", "next_scene",
    "next_continuity", "next_scene_commit", "next_volume_publication",
})
_COUNTER_LOCK = threading.Lock()


def reserve_counter(workspace_root: Path, counter: str) -> int:
    """Atomically reserve a positive counter value; reserved values are never reused."""
    if counter not in _COUNTERS:
        raise ContractError(f"未知のartifact counterです: {counter}")
    root = workspace_root.expanduser()
    assert_no_symlink_path(root, require_directory=True)
    root_descriptor = _open_directory_chain(root, expected_identity=directory_identity(root))
    try:
        return reserve_counter_at(root_descriptor, counter)
    except OSError as exc:
        raise ContractError("counters lockを取得できません") from exc
    finally:
        os.close(root_descriptor)


def reserve_counter_at(
    root_descriptor: int,
    counter: str,
    *,
    runtime_descriptor: int | None = None,
) -> int:
    """Reserve a counter relative to an already opened workspace root FD."""
    if counter not in _COUNTERS:
        raise ContractError(f"未知のartifact counterです: {counter}")
    if runtime_descriptor is None:
        runtime_descriptor = open_directory_at(
            root_descriptor,
            ("runtime",),
            expected_identity=directory_identity(directory_fd_path(root_descriptor) / "runtime"),
        )
    else:
        runtime_descriptor = os.dup(runtime_descriptor)
    try:
        with _COUNTER_LOCK:
            lock_descriptor = os.open(
                "counters.lock",
                os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=runtime_descriptor,
            )
            with os.fdopen(lock_descriptor, "a+", encoding="ascii") as lock_handle:
                if os.name == "posix":
                    import fcntl
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                try:
                    try:
                        value = json.loads(read_text_at(runtime_descriptor, Path("counters.json")))
                    except (OSError, json.JSONDecodeError) as exc:
                        raise ContractError("counters.jsonを読み込めません") from exc
                    if not isinstance(value, dict) or set(value) != _COUNTERS:
                        raise ContractError("counters.jsonのfield構成が不正です")
                    if any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in value.values()):
                        raise ContractError("counters.jsonの値が不正です")
                    reserved = value[counter]
                    value[counter] = reserved + 1
                    try:
                        atomic_write_text(directory_fd_path(runtime_descriptor) / "counters.json", json.dumps(value, ensure_ascii=False, indent=2) + "\n")
                    except OSError as exc:
                        raise ContractError("counters.jsonを原子的に保存できません") from exc
                    return reserved
                finally:
                    if os.name == "posix":
                        import fcntl
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise ContractError("counters lockを取得できません") from exc
    finally:
        os.close(runtime_descriptor)


def initial_counters() -> dict[str, int]:
    return {counter: 1 for counter in sorted(_COUNTERS)}
