"""設定の読み込みとマージ。§5 接続設定・§10.2 設定ファイルに従う。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .series_contracts import ContractError

DEFAULTS: dict[str, Any] = {
    "llm": {
        "base_url": "http://ws1.local:11434/v1",
        "model": "qwen3.6:35b-a3b-mtp-q4_K_M",
        "thinking": True,
        "stream": True,
        "first_event_timeout_seconds": 3600,
        "idle_timeout_seconds": 600,
    },
    "retry": {
        "max_attempts": 4,
    },
    "quality": {
        "max_critique_passes": 1,
        "improvement_directions": [
            "地の文を削り、くどさを排除する",
            "対話を自然にする",
        ],
        "content_length_target_chars": 2200,
        "content_length_tolerance_chars": 400,
    },
    "output": {
        "dir": "./storycraft-out",
    },
    "diversity": {
        "archive_dir": "~/.storycraft/archive",
        "recent_window": 5,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class Settings:
    llm: dict = field(default_factory=dict)
    retry: dict = field(default_factory=dict)
    quality: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)
    diversity: dict = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: str | None = None) -> "Settings":
        cfg = _deep_merge(DEFAULTS, {})
        if config_path:
            p = Path(config_path)
            if p.exists():
                with p.open(encoding="utf-8") as f:
                    user = yaml.safe_load(f) or {}
                cfg = _deep_merge(cfg, user)
            else:
                raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
        # 環境変数での上書き
        if os.environ.get("STORYCRAFT_LLM_BASE_URL"):
            cfg["llm"]["base_url"] = os.environ["STORYCRAFT_LLM_BASE_URL"]
        if os.environ.get("STORYCRAFT_LLM_MODEL"):
            cfg["llm"]["model"] = os.environ["STORYCRAFT_LLM_MODEL"]
        if os.environ.get("STORYCRAFT_LLM_IDLE_TIMEOUT"):
            cfg["llm"]["idle_timeout_seconds"] = float(os.environ["STORYCRAFT_LLM_IDLE_TIMEOUT"])
        if os.environ.get("STORYCRAFT_LLM_FIRST_TIMEOUT"):
            cfg["llm"]["first_event_timeout_seconds"] = float(os.environ["STORYCRAFT_LLM_FIRST_TIMEOUT"])
        max_critique_passes = cfg["quality"].get("max_critique_passes")
        if isinstance(max_critique_passes, bool) or not isinstance(max_critique_passes, int) or max_critique_passes < 1:
            raise ContractError("quality.max_critique_passes は1以上の整数で指定してください")
        return cls(
            llm=cfg["llm"],
            retry=cfg["retry"],
            quality=cfg["quality"],
            output=cfg["output"],
            diversity=cfg["diversity"],
        )

    def resolve_archive_dir(self) -> Path:
        return Path(os.path.expanduser(self.diversity["archive_dir"]))

    def resolve_output_dir(self, cli_out: str | None) -> Path:
        if cli_out:
            return Path(cli_out)
        if self.output.get("dir"):
            return Path(os.path.expanduser(self.output["dir"]))
        return Path("./storycraft-out")
