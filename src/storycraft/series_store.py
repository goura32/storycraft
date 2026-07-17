"""シリーズ状態の耐久永続化と作業場所ロック。"""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import fcntl

from .series_contracts import ContractError


class StateStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / "state.json"

    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict[str, Any]:
        if not self.exists():
            raise ContractError("保存済みシリーズがありません")
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContractError("保存状態が壊れています") from exc
        if data.get("version") != 4:
            raise ContractError("この保存状態は現行のシリーズ形式ではありません")
        required = {
            "brief", "keywords", "volume_map", "characters", "relationships", "world", "timeline", "threads",
            "chapters", "cards", "scenes", "volume_summaries", "initial_ledgers_confirmed",
            "attempts", "closure", "completed", "last_completed_unit", "stopped_at", "stop_reason",
        }
        if not required.issubset(data) or not isinstance(data["attempts"], list):
            raise ContractError("保存状態が製品契約を満たしていません")
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(self.path)
        self._fsync_directory()

    def _fsync_directory(self) -> None:
        if os.name != "posix":
            return
        descriptor = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @contextmanager
    def lock(self) -> Iterator[None]:
        self.root.mkdir(parents=True, exist_ok=True)
        handle = (self.root / ".series.lock").open("a+")
        try:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ContractError("この作業場所は別の実行で使用中です") from exc
            yield
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()
