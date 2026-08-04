"""Prompt schema loader cacheの契約。"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.prompt_template import PromptTemplate
from storycraft.series_contracts import ContractError


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
            original_read = __import__("storycraft.prompt_template", fromlist=["read_text_at"]).read_text_at
            read_calls = 0

            def counted_read(directory_fd: int, relative: Path, *args: object, **kwargs: object) -> str:
                nonlocal read_calls
                read_calls += 1
                return original_read(directory_fd, relative, *args, **kwargs)

            with patch("storycraft.prompt_template.read_text_at", new=counted_read):
                first = loader.load_schema_object(
                    "generate",
                    "request_intake",
                )
                second = loader.load_schema_object(
                    "revision",
                    "request_intake",
                )

            self.assertIs(first, second)
            self.assertEqual(read_calls, 1)

    def test_asset_swap_after_path_validation_cannot_escape_prompt_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "prompts"
            (root / "schemas").mkdir(parents=True)
            (root / "user" / "request_intake").mkdir(parents=True)
            schema_path = root / "schemas" / "request_intake.json"
            template_path = root / "user" / "request_intake" / "generate_request_intake.j2"
            schema_path.write_text('{"type":"object"}', encoding="utf-8")
            template_path.write_text("inside", encoding="utf-8")
            outside = Path(temporary) / "outside.txt"
            outside.write_text("OUTSIDE", encoding="utf-8")
            loader = PromptTemplate(root)
            original_asset_path = loader._asset_path

            def swap_after_validation(relative: Path, label: str) -> Path:
                selected = original_asset_path(relative, label)
                selected.unlink()
                selected.symlink_to(outside)
                return selected

            with patch.object(loader, "_asset_path", side_effect=swap_after_validation):
                with self.assertRaises(ContractError):
                    loader.load_schema_object("generate", "request_intake")
            with patch.object(loader, "_asset_path", side_effect=swap_after_validation):
                with self.assertRaises(ContractError):
                    loader.env.get_template("user/request_intake/generate_request_intake.j2")

    def test_prompt_root_swap_after_path_validation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "prompts"
            (root / "user").mkdir(parents=True)
            template_path = root / "user" / "request_intake.j2"
            template_path.write_text("inside", encoding="utf-8")
            outside = base / "outside"
            outside.mkdir()
            loader = PromptTemplate(root)
            original_asset_path = loader._asset_path

            def swap_after_validation(relative: Path, label: str) -> Path:
                selected = original_asset_path(relative, label)
                root.rename(base / "prompts-original")
                root.symlink_to(outside, target_is_directory=True)
                return selected

            try:
                with patch.object(loader, "_asset_path", side_effect=swap_after_validation):
                    with self.assertRaises(ContractError):
                        loader.env.get_template("user/request_intake.j2")
            finally:
                if root.is_symlink():
                    root.unlink()

    def test_different_loader_has_independent_cache(self) -> None:
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
