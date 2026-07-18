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
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from .log import logger
from .series_contracts import ContractError

STATUS_THINKING = "thinking"
STATUS_CONTENT = "content"
STATUS_SAVING = "saving"


def _raw_filename_component(value: str) -> str:
    """監査メタを保ったまま、ファイル名だけを移植可能な文字列へ正規化する。"""
    # 進捗refの総数（v:1/4 等）はログ/JSONメタには残し、ファイル名では省く。
    value = re.sub(r"/\d+", "", value)
    value = re.sub(r"([vcs]):\s*(\d+)", r"\1\2", value)
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return normalized or "unknown"


@dataclass
class CallRecord:
    kind: str
    phase: str
    ref: str
    attempt: int
    seed: int
    retry_total: int = 1
    quality_pass: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    content: str = ""
    meta_chunks: list[dict] = field(default_factory=list)  # {t, kind, chars}
    error: str | None = None

    def log_identity(self) -> str:
        quality = f" quality_pass={self.quality_pass}" if self.quality_pass else ""
        return f"phase={self.phase} ref={self.ref} kind={self.kind}{quality} retry={self.attempt}/{self.retry_total}"

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "phase": self.phase,
            "ref": self.ref,
            "attempt": self.attempt,
            "retry_total": self.retry_total,
            "quality_pass": self.quality_pass,
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
        base_url = settings.llm["base_url"]
        self.client = OpenAI(
            base_url=base_url,
            api_key="ollama",
            timeout=None,
        )
        # 接続先ヘルスチェック（未設定・到達不能なら即座に失敗）
        try:
            models = self.client.models.list()
            logger.info(f"Ollama接続確認: {base_url} (モデル数: {len(models.data)})")
        except Exception as e:
            logger.error(f"Ollama接続失敗: {base_url} - {type(e).__name__}: {e}")
            raise ContractError(f"LLMサーバーに接続できません: {base_url} - {e}")

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
            retry_total=meta.get("__retry_total", 1),
            quality_pass=meta.get("__quality_pass", ""),
        )
        logger.info("LLM開始: %s", rec.log_identity())
        try:
            stream = self.client.chat.completions.create(
                            model=llm["model"],
                            messages=[m for m in messages if not (isinstance(m, dict) and "__" in "".join(m.keys()))],  # type: ignore[list-item]
                            response_format=response_format,
                            stream=True,
                            extra_body={"think": bool(llm.get("thinking", True)), "seed": seed},
                        )
            idle_timeout = llm.get("idle_timeout_seconds", 600)
            progress_interval = llm.get("stream_progress_log_interval_seconds", 30)
            start = time.time()
            last_recv = start
            received_chunks = 0
            thinking_chars = 0
            content_chars = 0
            stream_finished = threading.Event()

            # OpenAI SDKの同期ストリーム反復は next(chunk) 待機中にブロックする。
            # その間も別スレッドで受信停滞を記録し、timeout 判定の死角を可視化する。
            def log_stream_stall() -> None:
                while not stream_finished.wait(progress_interval):
                    elapsed = time.time() - start
                    logger.info(
                        "LLM待機: %s 経過=%.1fs chunks=%s thinking_chars=%s content_chars=%s",
                        rec.log_identity(), elapsed, received_chunks, thinking_chars, content_chars,
                    )

            watchdog = threading.Thread(target=log_stream_stall, name=f"llm-watchdog-{rec.phase}", daemon=True)
            watchdog.start()
            try:
                for chunk in stream:
                    now = time.time()
                    received_chunks += 1
                    if now - last_recv > idle_timeout:
                        raise TimeoutError("受信後の無応答が idle_timeout を超えました")
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    reasoning = getattr(delta, "reasoning", None)
                    if reasoning:
                        reasoning = str(reasoning)
                        thinking_chars += len(reasoning)
                        rec.meta_chunks.append(
                            {"t": round(now - start, 2), "kind": STATUS_THINKING,
                             "chars": len(reasoning)}
                        )
                        last_recv = now
                    content = getattr(delta, "content", None)
                    if content:
                        content = str(content)
                        rec.content += content
                        content_chars += len(content)
                        rec.meta_chunks.append(
                            {"t": round(now - start, 2), "kind": STATUS_CONTENT,
                             "chars": len(content)}
                        )
                        last_recv = now
            finally:
                stream_finished.set()
                watchdog.join(timeout=1)
            rec.finished_at = time.time()
            duration = round(rec.finished_at - rec.started_at, 2)
            logger.info("LLM終了: %s 所要時間=%ss content_chars=%s", rec.log_identity(), duration, content_chars)
        except Exception as e:  # noqa: BLE001
            rec.error = f"{type(e).__name__}: {e}"
            rec.finished_at = time.time()
        return rec

    def call_once(self, messages, response_format, seed: int) -> CallRecord:
        return self._make_call(messages, response_format, seed)

    @staticmethod
    def _raw_markdown(filename: str, sent_messages: list, content: str) -> str:
        """生ログを、送受信の区切りが明確な人間確認用Markdownへ整形する。"""
        labels = {"system": "送信 (system)", "user": "送信 (user)"}
        sections = [f"# {filename}"]
        for message in sent_messages:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            message_content = message.get("content")
            if isinstance(role, str) and isinstance(message_content, str):
                sections.append(f"---\n## {labels.get(role, f'送信 ({role})')}\n\n{message_content}")
        sections.append(f"---\n## 受信\n\n{content}")
        return "\n".join(sections) + "\n"

    def save_raw(self, rec: CallRecord, prompt_messages: list) -> None:
        """送受信生データと、人間向けMarkdownを同じstemで保存。thinking本文は除く。"""
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        idx = len(list(self.raw_dir.glob("*.json")))
        sent_messages = [
            m for m in prompt_messages
            if not (isinstance(m, dict) and "__" in "".join(m.keys()))
        ]
        out = {
            "index": idx,
            "sent_messages": sent_messages,
            "received": rec.to_dict(),
            "content": rec.content,
        }
        json_path = self.raw_dir / (
            f"{idx:04d}_{_raw_filename_component(rec.kind)}_{_raw_filename_component(rec.ref)}.json"
        )
        json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        json_path.with_suffix(".md").write_text(
            self._raw_markdown(json_path.with_suffix(".md").name, sent_messages, rec.content),
            encoding="utf-8",
        )
