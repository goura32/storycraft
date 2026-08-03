"""OpenAI互換Structured Outputsの回帰試験。"""
from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

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
            call_id="call-test",
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
    def test_initial_design_review_and_revision_prompts_include_live_inputs(self) -> None:
        context = {"request": {"title": "brief-title"}, "settings": {"model": "local"}}
        candidate = {"core": {"logline": "current-candidate"}}
        critique = {"decision": "issues", "issues": [{"severity": "critical", "explanation": "fix-this"}]}

        review_prompt = OpenAIStoryModel._render("review", "initial_design", context=context, candidate=candidate)
        revise_prompt = OpenAIStoryModel._render("revise", "initial_design", context=context, candidate=candidate, critique=critique)

        self.assertIn("brief-title", review_prompt)
        self.assertIn("current-candidate", review_prompt)
        self.assertIn("brief-title", revise_prompt)
        self.assertIn("current-candidate", revise_prompt)
        self.assertIn("fix-this", revise_prompt)

    def test_legacy_revision_alias_uses_canonical_revise_prompt(self) -> None:
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        client = CaptureClient()
        setattr(model, "client", client)
        model._seed_sequence = 0

        actual = model.revision(
            "initial_design",
            {"core": {"logline": "current-candidate"}},
            {"decision": "issues", "issues": []},
            {"request": {"title": "brief-title"}},
        )

        self.assertEqual(actual, {"value": "ok"})
        self.assertEqual(client.calls[0]["messages"][2]["__kind"], "revise")
        self.assertIn("current-candidate", client.calls[0]["messages"][1]["content"])
        self.assertIn("candidate-response-v1", client.calls[0]["messages"][1]["content"])
        legacy_prompt = OpenAIStoryModel._render(
            "revision",
            "initial_design",
            candidate={"core": {"logline": "legacy-candidate"}},
            critique={"decision": "issues", "issues": []},
            context={"request": {"title": "legacy-title"}},
        )
        self.assertNotIn("{{", legacy_prompt)
        self.assertIn("legacy-candidate", legacy_prompt)
        self.assertIn("candidate-response-v1", legacy_prompt)

    def test_prose_revision_uses_raw_text_fix_template(self) -> None:
        model = OpenAIStoryModel.__new__(OpenAIStoryModel)
        client = CaptureClient()
        setattr(model, "client", client)
        model._seed_sequence = 0

        actual = model.revision_prose(
            "scene_prose",
            "本文候補",
            {"decision": "issues", "issues": []},
            {"scene": {"id": "scene-000001"}},
        )

        self.assertEqual(actual, '{"value": "ok"}')
        self.assertIsNone(client.calls[0]["response_format"])
        self.assertEqual(client.calls[0]["messages"][2]["__kind"], "revise")
        self.assertIn("本文候補", client.calls[0]["messages"][1]["content"])
        self.assertIn("candidate-response-v1", client.calls[0]["messages"][1]["content"])

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
        actual = OpenAIStoryModel._response_format("critique", "scene_prose")

        self.assertEqual(actual["type"], "json_schema")
        schema = actual["json_schema"]["schema"]
        self.assertEqual(schema["properties"]["schema_version"], {"const": "review-response-v1"})
        validator = Draft202012Validator(schema)
        base = {"schema_version": "review-response-v1", "decision": "issues", "issues": [{"severity": "notice", "explanation": "n", "evidence_locations": []}]}
        for location in ("prose:0", "paragraph:0", "$.text"):
            value = {**base, "issues": [{**base["issues"][0], "evidence_locations": [location]}]}
            self.assertEqual(list(validator.iter_errors(value)), [], location)
        for location in ("offset:0", "text"):
            value = {**base, "issues": [{**base["issues"][0], "evidence_locations": [location]}]}
            self.assertTrue(list(validator.iter_errors(value)), location)

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
