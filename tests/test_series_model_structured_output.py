"""OpenAI互換Structured Outputsの回帰試験。"""
from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from storycraft.series_model import OpenAIStoryModel
from storycraft.stages import ACTIVE_TEMPLATE_STAGES


class FakeTemplateLoader:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def render_system(self, response_mode: str = "json") -> str:
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
    def test_every_public_llm_stage_has_all_v2_templates_and_a_candidate_schema(self) -> None:
        self.assertIn("request_intake", ACTIVE_TEMPLATE_STAGES)
        for stage in ACTIVE_TEMPLATE_STAGES:
            with self.subTest(stage=stage, operation="generate"):
                rendered = OpenAIStoryModel._render("generate", stage, context={})
                self.assertIn("candidate-response-v1", rendered)
            with self.subTest(stage=stage, operation="review"):
                rendered = OpenAIStoryModel._render("review", stage, context={}, candidate={})
                self.assertIn("review-response-v1", rendered)
            with self.subTest(stage=stage, operation="revise"):
                rendered = OpenAIStoryModel._render("revise", stage, context={}, candidate={}, critique={})
                self.assertIn("candidate-response-v1", rendered)
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
        schema = actual["json_schema"]["schema"]
        self.assertEqual(actual["type"], "json_schema")
        self.assertTrue(actual["json_schema"]["strict"])
        self.assertEqual(schema["properties"]["schema_version"], {"const": "candidate-response-v1"})
        self.assertEqual(schema["properties"]["artifact_kind"], {"const": "initial-concept"})
        self.assertEqual(schema["properties"]["payload"]["required"], ["value"])

    def test_scene_prose_critique_uses_closed_review_wrapper(
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

        self.assertEqual(actual["type"], "json_schema")
        self.assertEqual(actual["json_schema"]["schema"]["properties"]["schema_version"], {"const": "review-response-v1"})

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
        schema = client.calls[0]["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["schema_version"], {"const": "candidate-response-v1"})
        self.assertEqual(schema["properties"]["payload"]["required"], ["value"])
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
