"""raw logの機密値除去とHTTP boundary契約の試験。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from storycraft.error_sanitizer import safe_exception_message, sanitize_text
from storycraft.llm import CallRecord, LLMClient


class LLMHardeningTests(unittest.TestCase):
    @staticmethod
    def _client(root: Path) -> LLMClient:
        (root / "runtime/calls").mkdir(parents=True)
        (root / "runtime/raw_logs").mkdir(parents=True)
        (root / "runtime/counters.json").write_text(
            json.dumps({
                "next_settings": 1,
                "next_request": 1,
                "next_keywords": 1,
                "next_adoption": 1,
                "next_candidate": 1,
                "next_quality": 1,
                "next_review": 1,
                "next_generation": 1,
                "next_selection": 1,
                "next_scene_commit": 1,
                "next_volume_publication": 1,
                "next_call": 1,
            }) + "\n",
            encoding="utf-8",
        )
        settings = SimpleNamespace(
            settings_id="settings-000001",
            llm={"ollama_http_boundary": True},
            retry={},
        )
        return LLMClient(settings, root / "runtime/raw_logs", workspace_root=root)

    def test_raw_json_sanitizes_manual_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            client = self._client(root)
            try:
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
                    [{"role": "user", "content": "公開可能なprompt"}],
                )
                path = next((root / "runtime/raw_logs").glob("*.json"))
                stored = path.read_text(encoding="utf-8")
                self.assertNotIn("password", stored)
                self.assertNotIn("raw-secret", stored)
                self.assertIn("[REDACTED]", stored)
                parsed = json.loads(stored)
                self.assertIn("[REDACTED]", parsed["received"]["error"])
            finally:
                client.close()

    def test_common_secret_formats_are_removed(self) -> None:
        samples = [
            "Authorization: Bearer ***",
            "x-api-key=abcdef123",
            "https://user:pass@example.test/path",
            "https://example.test/?token=abcdef123",
            "secret-token\\nFORGED",
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                sanitized = sanitize_text(sample)
                self.assertIn("[REDACTED]", sanitized)
                self.assertNotIn("abcdef123", sanitized)
                self.assertNotIn("pass@example", sanitized)
                self.assertNotIn("abcdefghijk12345", sanitized)
                self.assertNotIn("FORGED", sanitized)

        message = safe_exception_message(RuntimeError("api_key=private-value"))
        self.assertEqual(message, "RuntimeError: api_key: [REDACTED]")


if __name__ == "__main__":
    unittest.main()
