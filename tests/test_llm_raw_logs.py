"""LLM生ログの人間向けMarkdown出力契約。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.llm import CallRecord, LLMClient


class RawLogMarkdownTests(unittest.TestCase):
    def test_save_raw_writes_same_stem_markdown_with_expanded_contents(self) -> None:
        raw_dir = Path(tempfile.mkdtemp(prefix="storycraft-raw-"))
        client = LLMClient.__new__(LLMClient)
        client.raw_dir = raw_dir
        record = CallRecord(
            kind="generate",
            phase="plan",
            ref="plan",
            attempt=1,
            seed=1,
            content='{"volumes": [\n  {"number": 1}\n]}',
        )

        client.save_raw(
            record,
            [
                {"role": "system", "content": "JSONだけを返してください。\n改行はそのままです。"},
                {"role": "user", "content": "企画:\n雨の地図"},
                {"__kind": "generate", "__phase": "plan"},
            ],
        )

        json_path = raw_dir / "0000_generate_plan.json"
        markdown_path = raw_dir / "0000_generate_plan.md"
        self.assertTrue(json_path.exists())
        self.assertTrue(markdown_path.exists())
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["content"], record.content)
        self.assertEqual(
            markdown_path.read_text(encoding="utf-8"),
            "# 0000_generate_plan.md\n\n"
            "## system\n\n"
            "JSONだけを返してください。\n"
            "改行はそのままです。\n\n"
            "## user\n\n"
            "企画:\n"
            "雨の地図\n\n"
            "## received\n\n"
            '{"volumes": [\n'
            '  {"number": 1}\n'
            "]}\n",
        )


if __name__ == "__main__":
    unittest.main()
