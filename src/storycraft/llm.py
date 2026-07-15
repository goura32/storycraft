"""Ollama (OpenAI互換) 呼び出し層。§5 に従う。

- POST /v1/chat/completions をストリームで呼ぶ
- thinking と streaming を常に有効 (extra_body={"think": true})
- 各試行で attempt_seed を変える
- delta.content だけを本文/JSONとして連結
- 無応答の判定: 初回受信まで first_event_timeout, その後は idle_timeout
- 生データを保存 (thinking本文は除く: 時刻/種別/文字数メタのみ)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from .log import logger

STATUS_THINKING = "thinking"
STATUS_CONTENT = "content"
STATUS_SAVING = "saving"


@dataclass
class CallRecord:
    kind: str
    phase: str
    ref: str
    attempt: int
    seed: int
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    content: str = ""
    meta_chunks: list[dict] = field(default_factory=list)  # {t, kind, chars}
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "phase": self.phase,
            "ref": self.ref,
            "attempt": self.attempt,
            "seed": self.seed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "content_chars": len(self.content),
            "meta_chunks": self.meta_chunks,
            "error": self.error,
        }


class LLMClient:
    def __init__(self, settings, raw_dir: Path):
        self.settings = settings
        self.raw_dir = raw_dir
        self.client = OpenAI(
            base_url=settings.llm["base_url"],
            api_key="ollama",
            timeout=None,
        )

    def _make_call(self, messages: list[ChatCompletionMessageParam], response_format, seed: int) -> CallRecord:
        llm = self.settings.llm
        meta = {}
        if messages and isinstance(messages[-1], dict) and "__" in "".join(messages[-1].keys()):
            meta = messages[-1]  # type: ignore[assignment]
        rec = CallRecord(
            kind=meta.get("__kind", "gen"),
            phase=meta.get("__phase", ""),
            ref=meta.get("__ref", ""),
            attempt=meta.get("__attempt", 1),
            seed=seed,
        )
        try:
            stream = self.client.chat.completions.create(
                            model=llm["model"],
                            messages=[m for m in messages if not (isinstance(m, dict) and "__" in "".join(m.keys()))],  # type: ignore[list-item]
                            response_format=response_format,
                            stream=True,
                            extra_body={"think": bool(llm.get("thinking", True)), "seed": seed},
                        )
            first_event_timeout = llm.get("first_event_timeout_seconds", 3600)
            idle_timeout = llm.get("idle_timeout_seconds", 600)
            last_recv = time.time()
            start = time.time()
            for chunk in stream:
                now = time.time()
                if now - last_recv > idle_timeout:
                    raise TimeoutError("受信後の無応答が idle_timeout を超えました")
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning", None)
                if reasoning:
                    reasoning = str(reasoning)
                    rec.meta_chunks.append(
                        {"t": round(now - start, 2), "kind": STATUS_THINKING,
                         "chars": len(reasoning)}
                    )
                    last_recv = now
                content = getattr(delta, "content", None)
                if content:
                    content = str(content)
                    rec.content += content
                    rec.meta_chunks.append(
                        {"t": round(now - start, 2), "kind": STATUS_CONTENT,
                         "chars": len(content)}
                    )
                    last_recv = now
            rec.finished_at = time.time()
        except Exception as e:  # noqa: BLE001
            rec.error = f"{type(e).__name__}: {e}"
            rec.finished_at = time.time()
            logger.error("LLM呼び出し失敗: %s", rec.error)
        return rec

    def call_once(self, messages, response_format, seed: int) -> CallRecord:
        return self._make_call(messages, response_format, seed)

    def save_raw(self, rec: CallRecord, prompt_messages: list) -> None:
        """送受信生データを保存。thinking本文は除く（§5）。"""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        idx = len(list(self.raw_dir.glob("*.json")))
        out = {
            "index": idx,
            "sent_messages": [
                m for m in prompt_messages
                if not (isinstance(m, dict) and "__" in "".join(m.keys()))
            ],
            "received": rec.to_dict(),
            "content": rec.content,
        }
        (self.raw_dir / f"{idx:04d}_{rec.kind}_{rec.ref}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
