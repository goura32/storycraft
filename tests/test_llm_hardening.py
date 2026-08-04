"""blocking stream timeoutとLLM error安全化試験。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import time
import unittest

from storycraft.error_sanitizer import (
    safe_exception_message,
    sanitize_text,
)
from storycraft.llm import CallRecord, LLMClient


def chunk(
    *,
    content: str | None = None,
    reasoning: str | None = None,
) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                delta=SimpleNamespace(
                    content=content,
                    reasoning=reasoning,
                )
            )
        ]
    )


class BlockingStream:
    def __init__(self) -> None:
        self.closed = threading.Event()
        self.close_calls = 0

    def __iter__(self) -> BlockingStream:
        return self

    def __next__(self) -> object:
        self.closed.wait()
        raise StopIteration

    def close(self) -> None:
        self.close_calls += 1
        self.closed.set()


class OneChunkThenBlockStream:
    def __init__(self) -> None:
        self.first = True
        self.closed = threading.Event()
        self.close_calls = 0

    def __iter__(self) -> OneChunkThenBlockStream:
        return self

    def __next__(self) -> object:
        if self.first:
            self.first = False
            return chunk(content="本文")

        self.closed.wait()
        raise StopIteration

    def close(self) -> None:
        self.close_calls += 1
        self.closed.set()


def make_client(
    stream_or_factory: object,
    *,
    first_timeout: float = 0.05,
    idle_timeout: float = 0.05,
) -> LLMClient:
    client = LLMClient.__new__(LLMClient)
    client.settings = SimpleNamespace(
        llm={
            "model": "test",
            "thinking": True,
            "first_event_timeout_seconds": (
                first_timeout
            ),
            "idle_timeout_seconds": (
                idle_timeout
            ),
            "stream_progress_log_interval_seconds": (
                0.01
            ),
        }
    )

    if callable(stream_or_factory):
        create = stream_or_factory
    else:
        create = lambda **_kwargs: stream_or_factory

    client.client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=create
            )
        )
    )
    return client


def messages() -> list[dict]:
    return [{
        "__kind": "generate",
        "__phase": "request_intake",
        "__ref": "request_intake",
        "__attempt": 1,
        "__retry_total": 1,
    }]


class LLMHardeningTests(unittest.TestCase):
    def test_first_event_timeout_releases_caller(
        self,
    ) -> None:
        stream = BlockingStream()
        client = make_client(stream)

        started = time.monotonic()
        record = client.call_once(
            messages(),
            {"type": "json_object"},
            1,
        )
        elapsed = time.monotonic() - started

        self.assertEqual(
            record.error,
            (
                "TimeoutError: "
                "first_event_timeout exceeded"
            ),
        )
        self.assertLess(elapsed, 0.8)
        self.assertGreaterEqual(
            stream.close_calls,
            1,
        )

    def test_idle_timeout_after_first_chunk(
        self,
    ) -> None:
        stream = OneChunkThenBlockStream()
        client = make_client(stream)

        record = client.call_once(
            messages(),
            None,
            1,
        )

        self.assertEqual(record.content, "本文")
        self.assertEqual(
            record.error,
            "TimeoutError: idle_timeout exceeded",
        )
        self.assertGreaterEqual(
            stream.close_calls,
            1,
        )

    def test_provider_exception_is_sanitized(
        self,
    ) -> None:
        def fail_create(**_kwargs: object) -> object:
            raise ConnectionError(
                "Authorization: Bearer "
                "top-secret\nFORGED"
            )

        client = make_client(fail_create)

        record = client.call_once(
            messages(),
            {"type": "json_object"},
            1,
        )

        self.assertEqual(
            record.error,
            (
                "ConnectionError: "
                "Authorization: [REDACTED]"
            ),
        )
        self.assertNotIn(
            "top-secret",
            record.error,
        )
        self.assertNotIn("FORGED", record.error)

    def test_raw_json_sanitizes_manual_error(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            client = make_client(BlockingStream())
            client.raw_dir = Path(temporary)
            client.workspace_root = Path(temporary)

            record = CallRecord(
                kind="generate",
                phase="request_intake",
                ref="request_intake",
                attempt=1,
                seed=1,
                error=(
                    "HTTPError: "
                    "https://user:password@example.test/"
                    "?api_key=raw-secret"
                ),
            )

            client.save_raw(
                record,
                [{
                    "role": "user",
                    "content": "公開可能なprompt",
                }],
            )

            path = next(
                Path(temporary).glob("*.json")
            )
            stored = path.read_text(
                encoding="utf-8"
            )

            self.assertNotIn("password", stored)
            self.assertNotIn("raw-secret", stored)
            self.assertIn("[REDACTED]", stored)

            parsed = json.loads(stored)
            self.assertIn(
                "[REDACTED]",
                parsed["received"]["error"],
            )

    def test_common_secret_formats_are_removed(
        self,
    ) -> None:
        samples = [
            "Authorization: Bearer abcdef123",
            "x-api-key=abcdef123",
            "https://user:pass@example.test/path",
            "https://example.test/?token=abcdef123",
            "OpenAI key sk-abcdefghijk12345",
            "secret-token\\nFORGED",
        ]

        for sample in samples:
            with self.subTest(sample=sample):
                sanitized = sanitize_text(sample)
                self.assertIn(
                    "[REDACTED]",
                    sanitized,
                )
                self.assertNotIn(
                    "abcdef123",
                    sanitized,
                )
                self.assertNotIn(
                    "pass@example",
                    sanitized,
                )
                self.assertNotIn(
                    "abcdefghijk12345",
                    sanitized,
                )
                self.assertNotIn(
                    "FORGED",
                    sanitized,
                )

        message = safe_exception_message(
            RuntimeError(
                "api_key=private-value"
            )
        )
        self.assertEqual(
            message,
            "RuntimeError: api_key: [REDACTED]",
        )


if __name__ == "__main__":
    unittest.main()
