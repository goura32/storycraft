"""OpenAI互換Structured Outputsの回帰試験。"""
from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from storycraft.series_model import OpenAIStoryModel


class FakeTemplateLoader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def render_system(self) -> str:
        return "system prompt"

    def load_schema_object(
        self,
        kind: str,
        stage: str,
    ) -> dict:
        self.calls.append((kind, stage))

        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["value"],
            "properties": {
                "value": {
                    "type": "string",
                },
            },
        }


class CaptureClient:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            retry={
                "max_attempts": 1,
            }
        )
        self.calls: list[dict] = []
        self.saved: list[tuple[object, object]] = []

    def call_once(
        self,
        messages,
        response_format,
        seed: int,
    ):
        self.calls.append({
            "messages": messages,
            "response_format": response_format,
            "seed": seed,
        })

        return SimpleNamespace(
            error=None,
            content='{"value": "ok"}',
        )

    def save_raw(
        self,
        record,
        messages,
    ) -> None:
        self.saved.append(
            (
                record,
                messages,
            )
        )


class StructuredOutputTests(unittest.TestCase):
    def test_response_format_uses_strict_stage_schema(
        self,
    ) -> None:
        loader = FakeTemplateLoader()

        with patch(
            "storycraft.series_model."
            "get_template_loader",
            return_value=loader,
        ):
            actual = (
                OpenAIStoryModel
                ._response_format(
                    "generate",
                    "initial_concept",
                )
            )

        self.assertEqual(
            loader.calls,
            [
                (
                    "generate",
                    "initial_concept",
                ),
            ],
        )
        self.assertEqual(
            actual,
            {
                "type": "json_schema",
                "json_schema": {
                    "name": (
                        "storycraft_generate_"
                        "initial_concept"
                    ),
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": (
                            False
                        ),
                        "required": ["value"],
                        "properties": {
                            "value": {
                                "type": "string",
                            },
                        },
                    },
                },
            },
        )

    def test_scene_prose_critique_keeps_json_mode(
        self,
    ) -> None:
        with patch(
            "storycraft.series_model."
            "get_template_loader",
            side_effect=AssertionError(
                "scene_prose critiqueで"
                "Schemaを読み込みました"
            ),
        ):
            actual = (
                OpenAIStoryModel
                ._response_format(
                    "critique",
                    "scene_prose",
                )
            )

        self.assertEqual(
            actual,
            {
                "type": "json_object",
            },
        )

    def test_call_forwards_stage_schema_to_client(
        self,
    ) -> None:
        loader = FakeTemplateLoader()
        client = CaptureClient()

        model = OpenAIStoryModel.__new__(
            OpenAIStoryModel
        )
        model.client = client
        model._seed_sequence = 0

        with patch(
            "storycraft.series_model."
            "get_template_loader",
            return_value=loader,
        ):
            actual = model._call(
                "generate",
                "initial_concept",
                "test prompt",
            )

        self.assertEqual(
            actual,
            {
                "value": "ok",
            },
        )
        self.assertEqual(
            len(client.calls),
            1,
        )
        self.assertEqual(
            client.calls[0][
                "response_format"
            ],
            {
                "type": "json_schema",
                "json_schema": {
                    "name": (
                        "storycraft_generate_"
                        "initial_concept"
                    ),
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": (
                            False
                        ),
                        "required": ["value"],
                        "properties": {
                            "value": {
                                "type": "string",
                            },
                        },
                    },
                },
            },
        )
        self.assertEqual(
            client.calls[0]["seed"],
            1,
        )
        self.assertEqual(
            len(client.saved),
            1,
        )


if __name__ == "__main__":
    unittest.main()
