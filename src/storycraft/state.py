"""状態の保存と再開。§7 に従う。

保存対象:
- 初回企画 (brief)
- 全巻・章・場面の計画
- 各台帳と場面ごとの状態更新
- 各場面の本文と引継ぎ要約
- 各呼び出しの送受信生データ (raw/)
- 進捗ログ (log/)
- 完了した最後の場面, 停止理由
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class State:
    root: Path
    data: dict[str, Any] = field(default_factory=dict)

    # 派生パス
    @property
    def plan_dir(self) -> Path:
        return self.root / "plan"

    @property
    def scene_dir(self) -> Path:
        return self.root / "scenes"

    @property
    def raw_dir(self) -> Path:
        return self.root / "raw"

    @property
    def log_dir(self) -> Path:
        return self.root / "log"

    @property
    def archive_state_path(self) -> Path:
        return self.root / "state.json"

    @property
    def stages_dir(self) -> Path:
        return self.root / "stages"

    def init_dirs(self) -> None:
        for d in (self.plan_dir, self.scene_dir, self.raw_dir, self.log_dir, self.stages_dir):
            d.mkdir(parents=True, exist_ok=True)

    # --- 永続化 ---
    def save(self) -> None:
        self.archive_state_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, root: Path) -> "State":
        s = cls(root=root)
        s.init_dirs()
        if s.archive_state_path.exists():
            s.data = json.loads(s.archive_state_path.read_text(encoding="utf-8"))
        else:
            s.data = {}
        return s

    # --- 進捗 ---
    def set_stage_done(self, stage: str, value: Any = True) -> None:
        self.data.setdefault("stages_done", {})[stage] = value
        self.save()

    def is_stage_done(self, stage: str) -> bool:
        return bool(self.data.get("stages_done", {}).get(stage))

    def mark_last_scene(self, ref: str) -> None:
        self.data["last_scene"] = ref
        self.save()

    def set_stop_reason(self, reason: str) -> None:
        self.data["stop_reason"] = reason
        self.save()

    # --- 計画・台帳の保存 ---
    def save_json(self, name: str, obj: Any) -> None:
        (self.plan_dir / f"{name}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_json(self, name: str) -> Any:
        p = self.plan_dir / f"{name}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {}

    # --- 場面本文の保存 ---
    def save_scene(self, vol: int, ch: int, sc: int, obj: Any) -> None:
        d = self.scene_dir / f"volume-{vol:02d}" / f"chapter-{ch:02d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"scene-{sc:02d}.json").write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_scene(self, vol: int, ch: int, sc: int) -> Any:
        p = self.scene_dir / f"volume-{vol:02d}" / f"chapter-{ch:02d}" / f"scene-{sc:02d}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {}
