from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from storycraft.llm import LLMClient
from storycraft.ollama import OllamaResponseFormatError
from storycraft.prompt_template import PromptTemplate
from storycraft.series_model import OpenAIStoryModel


class V2ModelPlumbingTests(unittest.TestCase):
    def test_system_prompt_propagates_prose_response_mode(self) -> None:
        loader = PromptTemplate(Path(__file__).parents[1] / "templates" / "prompts")

        prose = loader.render_system("prose")
        structured = loader.render_system("json")

        self.assertIn("完成した自然な日本語散文本文だけ", prose)
        self.assertNotIn("JSONオブジェクト", prose)
        self.assertIn("JSONオブジェクト", structured)

    def test_prose_format_failures_consume_invalid_response_limit(self) -> None:
        client = LLMClient.__new__(LLMClient)
        with tempfile.TemporaryDirectory() as temporary:
            client.settings_id = "settings-000001"
            client.raw_dir = Path(temporary) / "runtime" / "raw_logs"
            client.settings = SimpleNamespace(llm={
                "v2_openai_ollama": True,
                "base_url": "http://127.0.0.1:11434/v1",
                "model": "m",
                "invalid_response_limit": 2,
            }, retry={"max_attempts": 1})
            model = OpenAIStoryModel.__new__(OpenAIStoryModel)
            model.client = client
            model._seed_sequence = 0
            model._format_attempt = 1
            with patch("storycraft.llm.ollama_generate", side_effect=OllamaResponseFormatError("empty")) as generate:
                with self.assertRaises(OllamaResponseFormatError):
                    model._call_text("generate", "scene_prose", "prompt")

        self.assertEqual(generate.call_count, 2)

    def test_call_once_keeps_v2_prose_as_raw_text_when_response_format_is_none(self) -> None:
        client = LLMClient.__new__(LLMClient)
        with tempfile.TemporaryDirectory() as temporary:
            client.settings_id = "settings-000001"
            client.raw_dir = Path(temporary) / "runtime" / "raw_logs"
            client.settings = SimpleNamespace(llm={
                "v2_openai_ollama": True,
                "base_url": "http://127.0.0.1:11434/v1",
                "model": "m",
            })
            with patch("storycraft.llm.ollama_generate", return_value="本文") as generate:
                result = client.call_once(
                    [{"role": "user", "content": "user"}],
                    None,
                    17,
                )

        self.assertIsNone(result.error)
        self.assertEqual(result.content, "本文")
        self.assertIsNone(generate.call_args.args[3])

    def test_public_model_implements_candidate_model_surface(self) -> None:
        self.assertTrue(callable(getattr(OpenAIStoryModel, "generate", None)))
        self.assertTrue(callable(getattr(OpenAIStoryModel, "review", None)))
        self.assertTrue(callable(getattr(OpenAIStoryModel, "revise", None)))

    def test_call_once_uses_ollama_boundary_with_options_messages_and_attempt_metadata(self) -> None:
        client = LLMClient.__new__(LLMClient)
        with tempfile.TemporaryDirectory() as temporary:
            client.settings_id = "settings-000001"
            client.raw_dir = Path(temporary) / "runtime" / "raw_logs"
            client.settings = SimpleNamespace(llm={
                "v2_openai_ollama": True,
                "base_url": "http://127.0.0.1:11434/v1",
                "model": "m",
                "request_options": {"temperature": 0.4},
            })
            with patch("storycraft.llm.ollama_generate", return_value={"value": "ok"}) as generate:
                result = client.call_once(
                    [
                        {"role": "system", "content": "system"},
                        {"role": "user", "content": "user"},
                        {"__kind": "generate", "__phase": "initial_design", "__attempt": 2, "__retry_total": 3},
                    ],
                    {"type": "json_schema", "json_schema": {"schema": {"type": "object"}}},
                    17,
                )
        self.assertIsNone(result.error)
        self.assertEqual(json.loads(result.content), {"value": "ok"})
        args, kwargs = generate.call_args
        self.assertEqual(args, ("http://127.0.0.1:11434/v1", "m", "user", {"type": "object"}))
        self.assertEqual(kwargs | {"call_id_sink": None}, {
            "request_options": {"temperature": 0.4},
            "messages": [{"role": "system", "content": "system"}, {"role": "user", "content": "user"}],
            "call_record_dir": client.raw_dir.parent / "calls",
            "technical_attempt": 2, "format_attempt": 1, "seed": 17, "operation": "generate",
            "settings_id": "settings-000001", "input_refs": [], "target_candidate_id": None,
            "call_id_sink": None,
        })

    def test_call_once_propagates_provider_format_error_instead_of_marking_it_transport(self) -> None:
        client = LLMClient.__new__(LLMClient)
        client.settings_id = "settings-000001"
        client.raw_dir = Path(tempfile.gettempdir()) / "storycraft-test-raw"
        client.settings = SimpleNamespace(llm={"v2_openai_ollama": True, "base_url": "http://127.0.0.1:11434/v1", "model": "m"})
        with patch("storycraft.llm.ollama_generate", side_effect=OllamaResponseFormatError("bad response")):
            with self.assertRaisesRegex(OllamaResponseFormatError, "bad response"):
                client.call_once([{"role": "user", "content": "user"}], {"type": "json_schema", "json_schema": {"schema": {}}}, 1)


if __name__ == "__main__":
    unittest.main()
