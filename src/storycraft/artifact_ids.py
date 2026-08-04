"""Immutable artifact identifiers and atomic counter reservation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading
from typing import Final

from .filesystem_security import assert_no_symlink_path
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
            if lock_path.is_symlink():
                raise ContractError("counters.lockはsymlinkであってはなりません")
            with lock_path.open("a+", encoding="utf-8") as lock_handle:
                if os.name == "posix":
                    import fcntl
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                try:
                    if path.is_symlink() or not path.is_file():
                        raise ContractError("counters.jsonは通常fileでなければなりません")
                    try:
                        value = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        raise ContractError("counters.jsonを読み込めません") from exc
                    if not isinstance(value, dict) or set(value) != _COUNTERS:
                        raise ContractError("counters.jsonのfield構成が不正です")
                    if any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in value.values()):
                        raise ContractError("counters.jsonの値が不正です")
                    reserved = value[counter]
                    value[counter] = reserved + 1
                    temporary = path.with_suffix(".json.tmp")
                    try:
                        with temporary.open("x", encoding="utf-8") as handle:
                            json.dump(value, handle, ensure_ascii=False, indent=2)
                            handle.write("\n")
                            handle.flush()
                            os.fsync(handle.fileno())
                        os.replace(temporary, path)
                        if os.name == "posix":
                            descriptor = os.open(path.parent, os.O_RDONLY)
                            try:
                                os.fsync(descriptor)
                            finally:
                                os.close(descriptor)
                    except OSError as exc:
                        temporary.unlink(missing_ok=True)
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
