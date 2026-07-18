"""実送信promptがbrief/Canon/volume_map契約を使うことを確認する。"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

from storycraft import cli
from storycraft.llm import CallRecord, LLMClient
from storycraft.prompt_template import get_template_loader
from storycraft.series_contracts import LLMCallError
from storycraft.series_model import OpenAIStoryModel


STAGES = [
    "brief", "characters", "relationships", "world", "timeline", "threads", "volume_map",
    "volume_chapters", "scene_card", "scene", "continuity", "volume_summary", "closure",
]


class _CapturingClient:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(retry={"max_attempts": 1})
        self.messages: list[dict] | None = None

    def call_once(self, messages: list[dict], _response_format: dict, _seed: int) -> CallRecord:
        self.messages = messages
        return CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, content='{}')

    def save_raw(self, _record: CallRecord, _messages: list[dict]) -> None:
        pass


class _SequenceClient:
    def __init__(self, records: list[CallRecord]) -> None:
        self.settings = SimpleNamespace(retry={"max_attempts": len(records)})
        self.records = records
        self.calls = 0
        self.raw_saves = 0

    def call_once(self, _messages: list[dict], _response_format: dict, _seed: int) -> CallRecord:
        record = self.records[self.calls]
        self.calls += 1
        return record

    def save_raw(self, _record: CallRecord, _messages: list[dict]) -> None:
        self.raw_saves += 1


class _TemplateLoader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def render_system(self) -> str:
        return "JINJAでレンダリングされたsystemプロンプト"

    def load_schema_text(self, category: str, stage: str) -> str:
        return f"外部スキーマ:{category}/{stage}"

    def render_user(self, kind: str, template_stage: str, **kwargs: object) -> str:
        self.calls.append((kind, template_stage, kwargs))
        return "JINJAでレンダリングされたbriefプロンプト"


class SeriesEngineModelTemplateTests(unittest.TestCase):
    def test_generate_brief_renders_stage_template_as_sent_user_prompt(self) -> None:
        client = _CapturingClient()
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = client
        model.attempt = 0
        loader = _TemplateLoader()

        with patch("storycraft.series_model.get_template_loader", return_value=loader):
            model.generate("brief", {"keywords": ["霧の島"]})

        self.assertEqual(
            loader.calls,
            [("generate", "brief", {"stage": "brief", "context": {"keywords": ["霧の島"]}, "output_schema": "外部スキーマ:generate/brief"})],
        )
        self.assertEqual(client.messages[1]["content"], "JINJAでレンダリングされたbriefプロンプト")

    def test_call_exhaustion_raises_llm_call_error_for_transport_and_non_object_json(self) -> None:
        scenarios = {
            "transport": [
                CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, error="ConnectionError: offline"),
                CallRecord(kind="generate", phase="brief", ref="brief", attempt=2, seed=2, error="ConnectionError: offline"),
            ],
            "non_object_json": [
                CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, content="[]"),
                CallRecord(kind="generate", phase="brief", ref="brief", attempt=2, seed=2, content="[]"),
            ],
        }
        for name, records in scenarios.items():
            with self.subTest(name=name):
                client = _SequenceClient(records)
                model = OpenAIStoryModel.__new__(OpenAIStoryModel)
                model.client = client
                model.attempt = 0
                with self.assertRaisesRegex(LLMCallError, "brief のLLM呼び出しに失敗"):
                    model._call("generate", "brief", "prompt")
                self.assertEqual(client.calls, 2)
                self.assertEqual(client.raw_saves, 2)

    def test_call_logs_transport_and_json_parse_errors_for_each_retry(self) -> None:
        scenarios = {
            "transport": (
                [
                    CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, error="ConnectionError: secret-token\nFORGED"),
                    CallRecord(kind="generate", phase="brief", ref="brief", attempt=2, seed=2, error="ConnectionError: secret-token\nFORGED"),
                ],
                "LLM通信エラー",
            ),
            "json_parse": (
                [
                    CallRecord(kind="generate", phase="brief", ref="brief", attempt=1, seed=1, content="not json"),
                    CallRecord(kind="generate", phase="brief", ref="brief", attempt=2, seed=2, content="not json"),
                ],
                "LLM JSONパースエラー",
            ),
        }
        for name, (records, message) in scenarios.items():
            with self.subTest(name=name):
                client = _SequenceClient(records)
                model = OpenAIStoryModel.__new__(OpenAIStoryModel)
                model.client = client
                model.attempt = 0
                with self.assertLogs("storycraft", level="ERROR") as captured:
                    with self.assertRaises(LLMCallError):
                        model._call("generate", "brief", "prompt")
                output = "\n".join(captured.output)
                self.assertEqual(output.count(message), 2)
                self.assertIn("attempt=1/2", output)
                self.assertIn("attempt=2/2", output)
                if name == "transport":
                    self.assertIn("error_type=ConnectionError", output)
                    self.assertNotIn("secret-token", output)
                    self.assertNotIn("FORGED", output)

    def test_llm_client_returns_transport_failure_without_duplicate_error_log(self) -> None:
        def fail_create(**kwargs: object) -> object:
            raise ConnectionError("secret-token\\nFORGED")

        client = LLMClient.__new__(LLMClient)
        client.settings = SimpleNamespace(llm={"model": "test"})
        client.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fail_create)))
        messages = [{"__kind": "generate", "__phase": "brief", "__ref": "brief", "__attempt": 1}]
        with self.assertNoLogs("storycraft", level="ERROR"):
            record = client.call_once(messages, {"type": "json_object"}, 1)
        self.assertEqual(record.error, "ConnectionError: secret-token\\nFORGED")

    def test_cli_logs_safe_exhausted_transport_error_once_per_layer(self) -> None:
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = _SequenceClient([
            CallRecord(
                kind="generate", phase="brief", ref="brief", attempt=1, seed=1,
                error="ConnectionError: secret-token\nFORGED",
            ),
        ])
        model.attempt = 0

        def fail_run(args: object) -> None:
            model._call("generate", "brief", "prompt")

        stderr = io.StringIO()
        with patch.object(sys, "argv", ["storycraft", "run", "--out", "/tmp/output", "--keywords", "test"]), \
             patch("storycraft.cli.cmd_run", side_effect=fail_run), \
             self.assertLogs("storycraft", level="ERROR") as captured, \
             contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as exited:
                cli.main()

        output = "\n".join(captured.output)
        stderr_output = stderr.getvalue()
        self.assertEqual(exited.exception.code, 2)
        self.assertEqual(output.count("LLM通信エラー"), 1)
        self.assertEqual(output.count("契約エラーにより終了します"), 1)
        self.assertIn("error_type=ConnectionError", output)
        self.assertNotIn("secret-token", output)
        self.assertNotIn("FORGED", output)
        self.assertIn("reason=transport:ConnectionError", stderr_output)
        self.assertNotIn("secret-token", stderr_output)
        self.assertNotIn("FORGED", stderr_output)

    def test_real_brief_and_volume_map_prompts_express_ownership_boundaries(self) -> None:
        brief = OpenAIStoryModel._render("generate", "brief", context={"keywords": ["霧の島", "4巻"]})
        volume_map = OpenAIStoryModel._render("generate", "volume_map", context={})
        self.assertIn("keywords", brief)
        self.assertIn("自動レビュー", brief)
        self.assertIn("Canon", volume_map)
        self.assertIn("新しい人物、世界設定、因果、秘密、出来事、回収条件を作らない", volume_map)
        self.assertIn("`thread_targets`", volume_map)
        self.assertIn("`brief.ending` は結末の唯一の正本", volume_map)

    def test_brief_quality_templates_enforce_reviewed_adoption_boundaries(self) -> None:
        generate = OpenAIStoryModel._render("generate", "brief", context={"keywords": ["霧の島"]})
        critique = OpenAIStoryModel._render("critique", "brief", candidate={}, context={"keywords": ["霧の島"]})
        revision = OpenAIStoryModel._render("revision", "brief", candidate={}, critique={"issues": []}, context={"keywords": ["霧の島"]})
        self.assertNotIn("内容評価は行わない", generate)
        self.assertIn("自動レビュー", generate)
        self.assertIn("物語開始時点", critique)
        self.assertIn("物語開始時点", revision)
        self.assertIn("未公表または暗示された秘密や伏線", critique)
        self.assertIn("結末の方向性・読後感", critique)
        self.assertIn("候補にない誤字・表現・事実を作らない", critique)
        self.assertIn("未公表または暗示された秘密や伏線", revision)
        self.assertIn("結末の方向性・読後感", revision)
        self.assertIn("将来の対処・直面・克服・関係発展", critique)
        self.assertIn("将来の対処・直面・克服・関係発展", revision)
        self.assertIn("動詞と目的語の結び付き", critique)

    def test_active_templates_and_schemas_have_only_current_stages(self) -> None:
        root = Path(__file__).parents[1] / "templates" / "prompts"
        user = root / "user"
        for kind in ("generate", "critique", "revision"):
            for stage in STAGES:
                path = user / stage / f"{kind}_{stage}.j2"
                contents = path.read_text(encoding="utf-8")
                self.assertIn("{{ output_schema }}", contents, path)
                self.assertTrue(contents.rstrip().endswith("{{ output_schema }}"), path)
                self.assertNotIn("{% include", contents, path)
        self.assertFalse((user / "plan").exists())
        self.assertFalse((root / "schemas" / "plan.json").exists())
        self.assertEqual(len(list(user.glob("*/*.j2"))), len(STAGES) * 3)
        for stage in STAGES:
            self.assertTrue((root / "schemas" / f"{stage}.json").is_file(), stage)

    def test_every_current_stage_has_renderable_generation_critique_and_revision_contract(self) -> None:
        for stage in STAGES:
            for prompt in (
                OpenAIStoryModel._render("generate", stage, context={}),
                OpenAIStoryModel._render("critique", stage, candidate={}, context={}),
                OpenAIStoryModel._render("revision", stage, candidate={}, critique={"issues": []}, context={}),
            ):
                self.assertNotIn("{{", prompt, stage)
                self.assertIn("## 出力スキーマ", prompt, stage)

    def test_system_template_owns_json_response_protocol(self) -> None:
        system = get_template_loader().render_system()
        self.assertIn("必ず有効なJSONオブジェクトのみを返す", system)
        self.assertIn("コードブロック", system)

    def test_jinja_json_policy_keeps_japanese_unescaped(self) -> None:
        loader = get_template_loader()
        self.assertFalse(loader.env.policies["json.dumps_kwargs"]["ensure_ascii"])
        rendered = loader.env.from_string("{{ value | tojson }}").render(value={"title": "雨の地図"})
        self.assertIn("雨の地図", rendered)


if __name__ == "__main__":
    unittest.main()
