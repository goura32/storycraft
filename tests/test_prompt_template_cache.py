"""Prompt schema loader cacheの契約。"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.prompt_template import PromptTemplate


class PromptTemplateCacheTests(unittest.TestCase):
    def test_schema_file_is_read_once(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            template_root = Path(temporary)
            schema_directory = (
                template_root / "schemas"
            )
            schema_directory.mkdir()

            schema_path = (
                schema_directory / "request_intake.json"
            )
            schema_path.write_text(
                '{"type": "object"}',
                encoding="utf-8",
            )

            loader = PromptTemplate(template_root)
            original_open = Path.open
            open_calls = 0

            def counted_open(
                path: Path,
                *args: object,
                **kwargs: object,
            ):
                nonlocal open_calls
                open_calls += 1
                return original_open(
                    path,
                    *args,
                    **kwargs,
                )

            with patch.object(
                Path,
                "open",
                new=counted_open,
            ):
                first = loader.load_schema_object(
                    "generate",
                    "request_intake",
                )
                second = loader.load_schema_object(
                    "revision",
                    "request_intake",
                )

            self.assertIs(first, second)
            self.assertEqual(open_calls, 1)

    def test_different_loader_has_independent_cache(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            template_root = Path(temporary)
            schema_directory = (
                template_root / "schemas"
            )
            schema_directory.mkdir()

            schema_path = (
                schema_directory / "request_intake.json"
            )
            schema_path.write_text(
                '{"type": "object"}',
                encoding="utf-8",
            )

            first_loader = PromptTemplate(
                template_root
            )
            second_loader = PromptTemplate(
                template_root
            )

            first = first_loader.load_schema_object(
                "generate",
                "request_intake",
            )
            second = second_loader.load_schema_object(
                "generate",
                "request_intake",
            )

            self.assertEqual(first, second)
            self.assertIsNot(first, second)


if __name__ == "__main__":
    unittest.main()
