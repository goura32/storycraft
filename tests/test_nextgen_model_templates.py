"""次世代モデルが実送信ユーザープロンプトへJinjaテンプレートを使う契約。"""
from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from storycraft.llm import CallRecord
from storycraft.nextgen_model import OpenAIStoryModel


class _CapturingClient:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(retry={"max_attempts": 1})
        self.messages: list[dict] | None = None

    def call_once(self, messages: list[dict], _response_format: dict, _seed: int) -> CallRecord:
        self.messages = messages
        return CallRecord(kind="generate", phase="plan", ref="plan", attempt=1, seed=1, content='{"volumes": []}')

    def save_raw(self, _record: CallRecord, _messages: list[dict]) -> None:
        pass


class _TemplateLoader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def render_system(self) -> str:
        return "JINJAでレンダリングされたsystemプロンプト"

    def render_user(self, kind: str, stage: str, **kwargs: object) -> str:
        self.calls.append((kind, stage, kwargs))
        return "JINJAでレンダリングされたplanプロンプト"


class NextGenerationModelTemplateTests(unittest.TestCase):
    def test_generate_renders_stage_template_as_sent_user_prompt(self) -> None:
        client = _CapturingClient()
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = client
        model.attempt = 0
        loader = _TemplateLoader()

        with patch("storycraft.nextgen_model.get_template_loader", return_value=loader):
            model.generate("plan", {"brief": {"title": "雨の地図"}})

        self.assertEqual(loader.calls, [("generate", "plan", {"brief": {"title": "雨の地図"}})])
        self.assertEqual(client.messages[1]["content"], "JINJAでレンダリングされたplanプロンプト")

    def test_real_plan_template_renders_brief_and_current_contract(self) -> None:
        client = _CapturingClient()
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = client  # type: ignore[assignment]
        model.attempt = 0

        model.generate("plan", {"brief": {"title": "雨の地図", "volumes": 4, "chapters_per_volume": [2, 3, 2, 3]}})

        prompt = client.messages[1]["content"]  # type: ignore[index]
        self.assertIn("# 全巻計画の生成", prompt)
        self.assertIn('"chapters_per_volume": [\n    2,\n    3,\n    2,\n    3\n  ]', prompt)
        self.assertIn("巻番号 n の `chapters` 件数は配列の n 番目の数と完全に一致", prompt)
        self.assertNotIn("巻数は5巻を第一候補", prompt)


if __name__ == "__main__":
    unittest.main()
