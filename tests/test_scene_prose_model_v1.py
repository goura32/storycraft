"""V1 Scene本文用raw text model契約。"""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
import unittest

from storycraft.prompt_template import get_template_loader
from storycraft.series_model import OpenAIStoryModel


PROSE = "潮風が灯台の扉を細く鳴らした。"


class FakeClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.settings = SimpleNamespace(
            retry={"max_attempts": 1},
        )
        self.calls: list[tuple[list, object, int]] = []

    def call_once(
        self,
        messages: list,
        response_format: object,
        seed: int,
    ) -> SimpleNamespace:
        self.calls.append(
            (
                deepcopy(messages),
                response_format,
                seed,
            )
        )
        return SimpleNamespace(
            content=self.content,
            error=None,
        )

    def save_raw(
        self,
        record: object,
        messages: list,
    ) -> None:
        return None


class SceneProseModelV1Tests(unittest.TestCase):
    def model(self, content: str) -> OpenAIStoryModel:
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        model.client = FakeClient(content)
        model._seed_sequence = 0
        return model

    def test_generate_and_revision_render_as_prose(self) -> None:
        generate = OpenAIStoryModel._render(
            "generate",
            "scene_prose_v1",
            context={"scene_card": {}},
        )
        revision = OpenAIStoryModel._render(
            "revision",
            "scene_prose_v1",
            candidate=PROSE,
            critique={"issues": []},
            context={"scene_card": {}},
        )

        self.assertIn("本文そのものだけ", generate)
        self.assertIn(PROSE, revision)
        self.assertNotIn("{{", generate)
        self.assertNotIn("{{", revision)

    def test_prose_system_does_not_require_json(self) -> None:
        system = get_template_loader().render_system("prose")

        self.assertIn("日本語散文本文だけ", system)
        self.assertIn("JSON", system)
        self.assertNotIn(
            "必ず有効なJSONオブジェクトのみを返す",
            system,
        )

    def test_generate_prose_uses_unstructured_response(self) -> None:
        model = self.model(f"\n{PROSE}\n")

        result = model.generate_prose(
            "scene_prose_v1",
            {"scene_card": {}},
        )

        self.assertEqual(result, PROSE)
        client = model.client
        self.assertIsInstance(client, FakeClient)
        messages, response_format, seed = client.calls[0]
        self.assertIsNone(response_format)
        self.assertEqual(seed, 1)
        self.assertIn(
            "日本語散文本文だけ",
            messages[0]["content"],
        )

    def test_critique_prose_stays_json_mode(self) -> None:
        model = self.model('{"issues": []}')

        result = model.critique_prose(
            "scene_prose_v1",
            PROSE,
            {"scene_card": {}},
        )

        self.assertEqual(result, {"issues": []})
        client = model.client
        self.assertIsInstance(client, FakeClient)
        _, response_format, _ = client.calls[0]
        self.assertEqual(
            response_format,
            {"type": "json_object"},
        )


if __name__ == "__main__":
    unittest.main()
