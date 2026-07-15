"""機械採番。§4 台帳IDと参照の規則に従う。

ID形式は 2桁: char-01, rel-01, entity-01, time-01, thread-01。
削除・失敗・過去のIDは再利用しない（カウンタを減らさない）。
"""
from __future__ import annotations

import json
from pathlib import Path

PREFIX = {
    "char": "char",
    "rel": "rel",
    "entity": "entity",
    "time": "time",
    "thread": "thread",
}


class IDSequencer:
    def __init__(self, state_dir: Path):
        self.counter: dict[str, int] = {}
        self.path = state_dir / "ids.json"
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.counter = data.get("counter", {})
            except (json.JSONDecodeError, OSError):
                self.counter = {}

    def next(self, kind: str) -> str:
        if kind not in PREFIX:
            raise ValueError(f"未知の台帳種別: {kind}")
        prefix = PREFIX[kind]
        n = self.counter.get(prefix, 0) + 1
        self.counter[prefix] = n
        self._save()
        return f"{prefix}-{n:02d}"

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"counter": self.counter}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
