"""Immutable artifact identifiers and atomic counter reservation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
from typing import Final

from .filesystem_security import atomic_write_text, assert_no_symlink_file_path, assert_no_symlink_path, open_nofollow, read_text_nofollow
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
    runtime = root / "runtime"
    assert_no_symlink_path(runtime, require_directory=True)
    path = runtime / "counters.json"
    lock_path = runtime / "counters.lock"
    try:
        with _COUNTER_LOCK:
            lock_descriptor = open_nofollow(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
            with os.fdopen(lock_descriptor, "a+", encoding="utf-8") as lock_handle:
                if os.name == "posix":
                    import fcntl
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                try:
                    assert_no_symlink_file_path(path, require_file=True)
                    try:
                        value = json.loads(read_text_nofollow(path))
                    except (OSError, json.JSONDecodeError) as exc:
                        raise ContractError("counters.jsonを読み込めません") from exc
                    if not isinstance(value, dict) or set(value) != _COUNTERS:
                        raise ContractError("counters.jsonのfield構成が不正です")
                    if any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in value.values()):
                        raise ContractError("counters.jsonの値が不正です")
                    reserved = value[counter]
                    value[counter] = reserved + 1
                    try:
                        atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
                    except OSError as exc:
                        raise ContractError("counters.jsonを原子的に保存できません") from exc
                    return reserved
                finally:
                    if os.name == "posix":
                        import fcntl
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise ContractError("counters lockを取得できません") from exc


def initial_counters() -> dict[str, int]:
    return {counter: 1 for counter in sorted(_COUNTERS)}
