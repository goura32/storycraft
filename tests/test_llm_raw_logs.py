"""LLM生ログの人間向けMarkdown出力契約。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.llm import CallRecord, LLMClient
from storycraft.series_contracts import ContractError


class RawLogMarkdownTests(unittest.TestCase):
    @staticmethod
    def _canonical_raw_workspace(prefix: str) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix=prefix)) / "workspace"
        raw_dir = root / "runtime" / "raw_logs"
        raw_dir.mkdir(parents=True)
        return root, raw_dir

    def test_save_raw_requires_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            client = LLMClient.__new__(LLMClient)
            client.raw_dir = Path(temporary)
            with self.assertRaises(ContractError):
                client.save_raw(
                    CallRecord(kind="generate", phase="plan", ref="plan", attempt=1, seed=1, content="{}"),
                    [],
                )

    def test_save_raw_writes_same_stem_markdown_with_expanded_contents(self) -> None:
        workspace_root, raw_dir = self._canonical_raw_workspace("storycraft-raw-")
        client = LLMClient.__new__(LLMClient)
        client.raw_dir = raw_dir
        client.workspace_root = workspace_root
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
            "# 0000_generate_plan.md\n"
            "---\n"
            "## 送信 (system)\n\n"
            "JSONだけを返してください。\n"
            "改行はそのままです。\n"
            "---\n"
            "## 送信 (user)\n\n"
            "企画:\n"
            "雨の地図\n"
            "---\n"
            "## 受信\n\n"
            '{"volumes": [\n'
            '  {"number": 1}\n'
            "]}\n",
        )

    def test_save_raw_uses_stage_without_placeholder_coordinates_for_global_stage(self) -> None:
        workspace_root, raw_dir = self._canonical_raw_workspace("storycraft-raw-global-")
        client = LLMClient.__new__(LLMClient)
        client.raw_dir = raw_dir
        client.workspace_root = workspace_root

        client.save_raw(
            CallRecord(
                kind="generate", phase="request_intake", ref="v:-/-", attempt=1, seed=1, content="{}",
            ),
            [],
        )

        self.assertTrue((raw_dir / "0000_generate_request_intake.json").exists())
        self.assertTrue((raw_dir / "0000_generate_request_intake.md").exists())

    def test_save_raw_includes_stage_and_available_coordinates_for_scene_stage(self) -> None:
        workspace_root, raw_dir = self._canonical_raw_workspace("storycraft-raw-scene-")
        client = LLMClient.__new__(LLMClient)
        client.raw_dir = raw_dir
        client.workspace_root = workspace_root

        client.save_raw(
            CallRecord(
                kind="critique", phase="scene_prose", ref="v:1/4 c:6/8 s:2/3", attempt=1, seed=1, content="{}",
            ),
            [],
        )

        self.assertTrue((raw_dir / "0000_critique_scene_prose_v1_c6_s2.json").exists())
        self.assertTrue((raw_dir / "0000_critique_scene_prose_v1_c6_s2.md").exists())

    def test_save_raw_sanitizes_progress_ref_only_in_filename(self) -> None:
        workspace_root, raw_dir = self._canonical_raw_workspace("storycraft-raw-parent-")
        client = LLMClient.__new__(LLMClient)
        client.raw_dir = raw_dir
        client.workspace_root = workspace_root
        record = CallRecord(
            kind="generate",
            phase="scene_prose",
            ref="v:1/4 c:6/8 s:2/3",
            attempt=1,
            seed=1,
            content="{}",
        )

        client.save_raw(record, [])

        json_path = raw_dir / "0000_generate_scene_prose_v1_c6_s2.json"
        self.assertTrue(json_path.exists())
        self.assertEqual(list(raw_dir.rglob("*.json")), [json_path])
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["received"]["ref"], record.ref)


if __name__ == "__main__":
    unittest.main()
