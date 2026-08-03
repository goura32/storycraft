"""Prompt SchemaのStage別解決規則。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from jinja2 import UndefinedError, meta

from storycraft.prompt_template import PromptTemplate
from storycraft.stages import ACTIVE_TEMPLATE_STAGES


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

        return PromptTemplate(root)

    def test_common_critique_schema_is_used_for_all_stages(
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
                    "marker": "common",
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

    def test_missing_render_value_fails_closed(self) -> None:
        loader = PromptTemplate(
            Path(__file__).parents[1] / "templates" / "prompts"
        )

        with self.assertRaises(UndefinedError):
            loader.render_user(
                "generate",
                "request_intake",
                context={"present": True},
            )

    def test_every_template_placeholder_has_a_render_binding(self) -> None:
        root = Path(__file__).parents[1] / "templates" / "prompts"
        loader = PromptTemplate(root)

        for template_path in sorted((root / "user").rglob("*.j2")):
            relative = template_path.relative_to(root)
            stage = relative.parts[1]
            filename = relative.name
            kind = filename.split("_", 1)[0]
            expected = {"context", "output_schema"}
            if kind in {"critique", "fix"}:
                expected.add("candidate")
            if kind == "fix":
                expected.add("critique")

            with self.subTest(template=str(relative)):
                source = template_path.read_text(encoding="utf-8")
                actual = meta.find_undeclared_variables(
                    loader.env.parse(source)
                )
                self.assertEqual(actual, expected)

                values = {
                    "context": {"__context_placeholder__": stage},
                    "output_schema": '{"__schema_placeholder__":true}',
                }
                if kind in {"critique", "fix"}:
                    values["candidate"] = (
                        "__candidate_placeholder__"
                        if stage == "scene_prose"
                        else {"__candidate_placeholder__": True}
                    )
                if kind == "fix":
                    values["critique"] = {"__critique_placeholder__": True}

                rendered = loader.env.get_template(
                    str(relative).replace("\\", "/")
                ).render(**values)
                self.assertNotIn("{{", rendered)
                self.assertNotIn("{%", rendered)
                self.assertIn("__context_placeholder__", rendered)
                self.assertIn("__schema_placeholder__", rendered)
                if kind in {"critique", "fix"}:
                    self.assertIn("__candidate_placeholder__", rendered)
                if kind == "fix":
                    self.assertIn("__critique_placeholder__", rendered)

        for response_mode in ("json", "prose"):
            with self.subTest(system_response_mode=response_mode):
                rendered = loader.render_system(response_mode)
                self.assertNotIn("{{", rendered)
                self.assertNotIn("{%", rendered)

        self.assertEqual(
            set(ACTIVE_TEMPLATE_STAGES),
            {
                "request_intake",
                "initial_design",
                "series_plan",
                "volume_plan",
                "chapter_plan",
                "scene_plan",
                "scene_card",
                "scene_prose",
                "scene_continuity",
            },
        )


if __name__ == "__main__":
    unittest.main()
