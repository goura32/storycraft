"""OpenAI互換Provider呼び出し層。

- POST /v1/chat/completions をストリームで呼ぶ
- thinking と streaming を常に有効 (extra_body={"think": true})
- 各試行で attempt_seed を変える
- delta.content だけを本文/JSONとして連結
- 無応答の判定: 初回受信まで first_event_timeout, その後は idle_timeout
- 生データを保存 (thinking本文は除く: 時刻/種別/文字数メタのみ)
"""
from __future__ import annotations

import json
import math
from queue import Empty, Queue
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from .config import resolve_llm_credentials
from .error_sanitizer import (
    safe_exception_message,
    sanitize_text,
)
from .log import logger
from .ollama import OllamaResponseFormatError, generate as ollama_generate
from .series_contracts import ContractError

STATUS_THINKING = "thinking"
STATUS_CONTENT = "content"
STATUS_SAVING = "saving"


def _positive_seconds(
    settings: dict[str, Any],
    field: str,
    default: float,
) -> float:
    value = settings.get(field, default)

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise ContractError(
            f"llm.{field}は0より大きい有限数が必要です"
        )

    return float(value)


def _raw_filename_component(value: str) -> str:
    """監査メタを保ったまま、ファイル名だけを移植可能な文字列へ正規化する。"""
    # 進捗refの総数（v:1/4 等）はログ/JSONメタには残し、ファイル名では省く。
    value = re.sub(r"/\d+", "", value)
    value = re.sub(r"([vcs]):\s*(\d+)", r"\1\2", value)
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return normalized or "unknown"


def _raw_filename(rec: "CallRecord", index: int) -> str:
    """生データ名へ工程を常に含め、工程に属さない座標は出力しない。"""
    parts = [f"{index:04d}", _raw_filename_component(rec.kind), _raw_filename_component(rec.phase)]
    scope_by_stage = {
        "volume_plan": ("v",),
        "chapter_plan": ("v", "c"),
        "scene_plan": ("v", "c", "s"),
        "scene_card": ("v", "c", "s"),
        "scene_prose": ("v", "c", "s"),
        "scene_continuity": ("v", "c", "s"),
        "volume_handoff": ("v",),
    }
    for coordinate in scope_by_stage.get(rec.phase, ()):
        match = re.search(rf"\b{coordinate}:\s*(\d+)", rec.ref)
        if match:
            parts.append(f"{coordinate}{match.group(1)}")
    return "_".join(parts)


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
    call_id: str | None = None

    def log_identity(self) -> str:
        quality = f" quality_pass={self.quality_pass}" if self.quality_pass else ""
        coordinate = "" if self.ref == self.phase else f" {self.ref.replace(' ', ',')}"
        return f"stage={self.phase}{coordinate} kind={self.kind}{quality} retry={self.attempt}/{self.retry_total}"

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
            "error": (
                sanitize_text(self.error)
                if self.error is not None
                else None
            ),
        }


class LLMClient:
    def __init__(
        self,
        settings,
        raw_dir: Path,
    ) -> None:
        self.settings = settings
        self.raw_dir = raw_dir

        llm = settings.llm
        base_url = llm["base_url"]

        first_event_timeout = _positive_seconds(
            llm,
            "first_event_timeout_seconds",
            3600,
        )
        idle_timeout = _positive_seconds(
            llm,
            "idle_timeout_seconds",
            600,
        )

        api_key, default_headers = (
            resolve_llm_credentials(llm)
        )

        client_options: dict[str, Any] = {
            "base_url": base_url,
            "api_key": api_key,
            "timeout": max(
                first_event_timeout,
                idle_timeout,
            ),
            "max_retries": 0,
        }
        if default_headers:
            client_options["default_headers"] = (
                default_headers
            )

        self.client = OpenAI(
            **client_options
        )

        safe_base_url = sanitize_text(
            base_url,
            max_length=500,
        )

        try:
            models = self.client.models.list(
                timeout=min(
                    first_event_timeout,
                    60.0,
                ),
            )
            logger.info(
                "LLM接続確認: base_url=%s models=%s",
                safe_base_url,
                len(models.data),
            )
        except Exception as error:
            error_type = type(error).__name__
            logger.error(
                "LLM接続失敗: base_url=%s "
                "error_type=%s",
                safe_base_url,
                error_type,
            )
            raise ContractError(
                "LLMサーバーに接続できません: "
                f"base_url={safe_base_url} "
                f"error_type={error_type}"
            ) from error

    @staticmethod
    def _request_stream_close(
        stream: object,
    ) -> None:
        """stream closeが停止しても呼出し元を塞がない。"""
        close = getattr(stream, "close", None)
        if not callable(close):
            return

        def close_safely() -> None:
            try:
                close()
            except Exception:
                pass

        closer = threading.Thread(
            target=close_safely,
            name="llm-stream-close",
            daemon=True,
        )
        closer.start()
        closer.join(timeout=0.2)

    def _consume_stream(
        self,
        stream: object,
        rec: CallRecord,
        *,
        first_event_timeout: float,
        idle_timeout: float,
        progress_interval: float,
    ) -> tuple[int, int, int]:
        """blocking iteratorをworkerへ隔離して監視する。"""
        events: Queue[tuple[str, object]] = Queue()
        stop_requested = threading.Event()

        def read_stream() -> None:
            try:
                for chunk in stream:
                    if stop_requested.is_set():
                        break
                    events.put(("chunk", chunk))
            except BaseException as error:
                events.put(("error", error))
            finally:
                events.put(("done", None))

        worker = threading.Thread(
            target=read_stream,
            name=f"llm-stream-{rec.phase}",
            daemon=True,
        )
        worker.start()

        started = time.monotonic()
        deadline = started + first_event_timeout
        next_progress = started + progress_interval

        received_event = False
        received_chunks = 0
        thinking_chars = 0
        content_chars = 0

        try:
            while True:
                now = time.monotonic()
                wait_until = min(
                    deadline,
                    next_progress,
                )
                wait_seconds = max(
                    wait_until - now,
                    0.0,
                )

                try:
                    event_kind, payload = events.get(
                        timeout=wait_seconds,
                    )
                except Empty:
                    now = time.monotonic()

                    if now >= deadline:
                        timeout_kind = (
                            "idle_timeout"
                            if received_event
                            else "first_event_timeout"
                        )
                        raise TimeoutError(
                            f"{timeout_kind} exceeded"
                        )

                    if now >= next_progress:
                        logger.info(
                            "LLM待機: %s 経過=%.2fs "
                            "chunks=%s thinking=%s "
                            "content=%s",
                            rec.log_identity(),
                            now - started,
                            received_chunks,
                            thinking_chars,
                            content_chars,
                        )
                        next_progress = (
                            now + progress_interval
                        )

                    continue

                now = time.monotonic()

                if event_kind == "done":
                    break

                if event_kind == "error":
                    if isinstance(
                        payload,
                        BaseException,
                    ):
                        raise payload
                    raise RuntimeError(
                        "stream worker error"
                    )

                if event_kind != "chunk":
                    raise RuntimeError(
                        "unknown stream worker event"
                    )

                received_event = True
                received_chunks += 1
                deadline = now + idle_timeout

                chunk = payload
                choices = getattr(
                    chunk,
                    "choices",
                    None,
                )
                if not choices:
                    continue

                delta = choices[0].delta

                reasoning = getattr(
                    delta,
                    "reasoning",
                    None,
                )
                if reasoning:
                    reasoning = str(reasoning)
                    thinking_chars += len(reasoning)
                    rec.meta_chunks.append({
                        "t": round(
                            now - started,
                            2,
                        ),
                        "kind": STATUS_THINKING,
                        "chars": len(reasoning),
                    })

                content = getattr(
                    delta,
                    "content",
                    None,
                )
                if content:
                    content = str(content)
                    rec.content += content
                    content_chars += len(content)
                    rec.meta_chunks.append({
                        "t": round(
                            now - started,
                            2,
                        ),
                        "kind": STATUS_CONTENT,
                        "chars": len(content),
                    })
        finally:
            stop_requested.set()
            self._request_stream_close(stream)
            worker.join(timeout=0.2)

        return (
            received_chunks,
            thinking_chars,
            content_chars,
        )

    def _make_call(
        self,
        messages: list[ChatCompletionMessageParam],
        response_format,
        seed: int,
    ) -> CallRecord:
        llm = self.settings.llm
        meta = {}

        if (
            messages
            and isinstance(messages[-1], dict)
            and "__" in "".join(messages[-1].keys())
        ):
            meta = messages[-1]  # type: ignore[assignment]

        rec = CallRecord(
            kind=meta.get("__kind", "gen"),
            phase=meta.get("__phase", ""),
            ref=meta.get("__ref", ""),
            attempt=meta.get("__attempt", 1),
            seed=seed,
            retry_total=meta.get(
                "__retry_total",
                1,
            ),
            quality_pass=meta.get(
                "__quality_pass",
                "",
            ),
        )

        logger.info(
            "LLM開始: %s",
            rec.log_identity(),
        )

        try:
            first_event_timeout = _positive_seconds(
                llm,
                "first_event_timeout_seconds",
                3600,
            )
            idle_timeout = _positive_seconds(
                llm,
                "idle_timeout_seconds",
                600,
            )
            progress_interval = _positive_seconds(
                llm,
                "stream_progress_log_interval_seconds",
                60,
            )

            request = {
                "model": llm["model"],
                "messages": [
                    message
                    for message in messages
                    if not (
                        isinstance(message, dict)
                        and "__"
                        in "".join(message.keys())
                    )
                ],
                "stream": True,
                "extra_body": {
                    "think": bool(
                        llm.get("thinking", True)
                    ),
                    "seed": seed,
                },
            }

            if response_format is not None:
                request["response_format"] = (
                    response_format
                )

            stream = (
                self.client
                .chat
                .completions
                .create(
                    **request,
                    timeout=first_event_timeout,
                )
            )

            (
                _received_chunks,
                _thinking_chars,
                content_chars,
            ) = self._consume_stream(
                stream,
                rec,
                first_event_timeout=(
                    first_event_timeout
                ),
                idle_timeout=idle_timeout,
                progress_interval=(
                    progress_interval
                ),
            )

            rec.finished_at = time.time()
            duration = round(
                rec.finished_at - rec.started_at,
                2,
            )

            logger.info(
                "LLM終了: %s 所要時間=%ss "
                "content_chars=%s",
                rec.log_identity(),
                duration,
                content_chars,
            )
        except Exception as error:
            rec.error = safe_exception_message(
                error
            )
            rec.finished_at = time.time()

        return rec

    def call_once(self, messages, response_format, seed: int) -> CallRecord:
        if not self.settings.llm.get("v2_openai_ollama", False):
            return self._make_call(messages, response_format, seed)
        meta = messages[-1] if messages and isinstance(messages[-1], dict) else {}
        visible_messages = [
            message for message in messages
            if isinstance(message, dict) and isinstance(message.get("role"), str)
            and isinstance(message.get("content"), str)
        ]
        rec = CallRecord(
            kind=meta.get("__kind", "gen"), phase=meta.get("__phase", ""),
            ref=meta.get("__ref", ""), attempt=meta.get("__attempt", 1), seed=seed,
            retry_total=meta.get("__retry_total", 1), quality_pass=meta.get("__quality_pass", ""),
        )
        schema: dict[str, Any] | None = None
        if isinstance(response_format, dict):
            schema = response_format.get("json_schema", {}).get("schema", {"type": "object"})
        try:
            value = ollama_generate(
                self.settings.llm["base_url"], self.settings.llm["model"],
                visible_messages[-1]["content"] if visible_messages else "", schema,
                request_options=self.settings.llm.get("request_options"),
                messages=visible_messages, call_record_dir=self.raw_dir.parent / "calls",
                technical_attempt=rec.attempt, format_attempt=meta.get("__format_attempt", 1), seed=seed,
                operation=rec.kind, call_id_sink=lambda call_id: setattr(rec, "call_id", call_id),
                settings_id=meta.get("settings_id"), input_refs=meta.get("input_refs", []),
                target_candidate_id=meta.get("target_candidate_id"),
            )
            rec.content = value if schema is None and isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        except OllamaResponseFormatError:
            rec.finished_at = time.time()
            raise
        except Exception as error:
            rec.error = safe_exception_message(error)
        rec.finished_at = time.time()
        return rec

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
        received = rec.to_dict()
        if received["error"] is not None:
            received["error"] = sanitize_text(
                received["error"]
            )

        out = {
            "index": idx,
            "sent_messages": sent_messages,
            "received": received,
            "content": rec.content,
        }
        json_path = self.raw_dir / f"{_raw_filename(rec, idx)}.json"
        json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        json_path.with_suffix(".md").write_text(
            self._raw_markdown(json_path.with_suffix(".md").name, sent_messages, rec.content),
            encoding="utf-8",
        )
