"""次世代モデルが実送信ユーザープロンプトへJinjaテンプレートを使う契約。"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from storycraft.prompt_template import get_template_loader
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

    def load_schema_text(self, category: str, stage: str) -> str:
        return f"外部スキーマ:{category}/{stage}"

    def render_user(self, kind: str, template_stage: str, **kwargs: object) -> str:
        self.calls.append((kind, template_stage, kwargs))
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

        self.assertEqual(
            loader.calls,
            [("generate", "stage", {"stage": "plan", "context": {"brief": {"title": "雨の地図"}}, "output_schema": "外部スキーマ:generate/plan"})],
        )
        self.assertEqual(client.messages[1]["content"], "JINJAでレンダリングされたplanプロンプト")

    def test_real_plan_template_renders_brief_and_current_contract(self) -> None:
        client = _CapturingClient()
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = client  # type: ignore[assignment]
        model.attempt = 0

        model.generate("plan", {"brief": {"title": "雨の地図", "volumes": 4, "chapters_per_volume": [2, 3, 2, 3]}})

        prompt = client.messages[1]["content"]  # type: ignore[index]
        self.assertIn("# plan の生成", prompt)
        self.assertIn('"chapters_per_volume": [\n      2,\n      3,\n      2,\n      3\n    ]', prompt)
        self.assertIn("全巻構成だけを作る", prompt)
        self.assertIn("中国語の漢字語・簡体字", prompt)
        self.assertIn("前巻の結果を受け", prompt)
        self.assertIn("入力にない過去の関係", prompt)
        self.assertIn('"required": [\n    "volumes"\n  ]', prompt)
        self.assertNotIn("巻数は5巻を第一候補", prompt)

    def test_active_templates_use_output_schema_placeholder_not_inline_json_schema(self) -> None:
        root = Path(__file__).parents[1] / "templates" / "prompts" / "user"
        names = ["generate_stage.j2", "critique_stage.j2", "fix_stage.j2"]
        for name in names:
            contents = (root / name).read_text(encoding="utf-8")
            self.assertIn("{{ output_schema }}", contents, name)
            self.assertNotIn("```json", contents, name)
            self.assertNotIn("ensure_ascii", contents, name)
            self.assertNotIn("indent=2", contents, name)
            self.assertNotIn("JSONオブジェクトだけを返すこと。", contents, name)
            self.assertTrue(contents.rstrip().endswith("{{ output_schema }}"), name)

    def test_every_current_stage_has_renderable_generation_critique_and_fix_contract(self) -> None:
        stages = [
            "plan", "characters", "relationships", "world", "timeline", "threads",
            "volume_chapters", "scene_card", "scene", "continuity", "volume_summary", "closure",
        ]
        for stage in stages:
            generation = OpenAIStoryModel._render("generate", stage, context={})
            critique = OpenAIStoryModel._render("critique", stage, candidate={}, context={})
            revision = OpenAIStoryModel._render("fix", stage, candidate={}, critique={"issues": []}, context={})
            for prompt in (generation, critique, revision):
                self.assertNotIn("{{", prompt, stage)
                self.assertIn("## 出力スキーマ", prompt, stage)

    def test_system_template_owns_json_response_protocol(self) -> None:
        system = get_template_loader().render_system()
        self.assertIn("必ず有効なJSONオブジェクトのみを返す", system)
        self.assertIn("コードブロック", system)

    def test_jinja_json_policy_keeps_japanese_unescaped(self) -> None:
        loader = get_template_loader()
        self.assertFalse(loader.env.policies["json.dumps_kwargs"]["ensure_ascii"])
        self.assertEqual(loader.env.policies["json.dumps_kwargs"]["indent"], 2)
        rendered = loader.env.from_string("{{ value | tojson }}").render(value={"title": "雨の地図"})
        self.assertIn("雨の地図", rendered)
        self.assertNotIn("\\\\u96e8", rendered)


if __name__ == "__main__":
    unittest.main()
