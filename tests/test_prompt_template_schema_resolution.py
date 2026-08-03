"""Prompt SchemaのStage別解決規則。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.prompt_template import PromptTemplate


class PromptTemplateSchemaResolutionTests(
    unittest.TestCase,
):
    def create_loader(
        self,
        temporary: str,
    ) -> PromptTemplate:
        root = Path(temporary) / "prompts"
        schemas = root / "schemas"
        schemas.mkdir(parents=True)

        (schemas / "critique.json").write_text(
            json.dumps({
                "marker": "common",
            }),
            encoding="utf-8",
        )
        (
            schemas
            / "critique_initial_concept.json"
        ).write_text(
            json.dumps({
                "marker": "initial-concept",
            }),
            encoding="utf-8",
        )

        return PromptTemplate(root)

    def test_stage_specific_critique_schema_is_preferred(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            loader = self.create_loader(temporary)

            schema = loader.load_schema_object(
                "critique",
                "initial_concept",
            )

            self.assertEqual(
                schema,
                {
                    "marker": "initial-concept",
                },
            )

    def test_common_critique_schema_is_fallback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            loader = self.create_loader(temporary)

            schema = loader.load_schema_object(
                "critique",
                "initial_characters",
            )

            self.assertEqual(
                schema,
                {
                    "marker": "common",
                },
            )

    def test_tojson_uses_one_canonical_utf8_json_form(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            loader = self.create_loader(temporary)
            rendered = loader.env.from_string("{{ value | tojson }}").render(value={"b": 1, "a": "日本語"})
            self.assertEqual(rendered, '{"a":"日本語","b":1}')


if __name__ == "__main__":
    unittest.main()
