"""LLM Provider設定とcredential分離試験。"""
from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from storycraft.cli import _workspace_config
from storycraft.config import (
    Settings,
    resolve_llm_credentials,
)
from storycraft.llm import LLMClient
from storycraft.series_contracts import ContractError


class LLMProviderConfigTests(unittest.TestCase):
    def test_default_ollama_requires_no_secret(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            settings = Settings.load()
            api_key, headers = (
                resolve_llm_credentials(
                    settings.llm
                )
            )

        self.assertEqual(
            settings.llm["provider"],
            "ollama",
        )
        self.assertIsNone(
            settings.llm["api_key_env"]
        )
        self.assertEqual(api_key, "ollama")
        self.assertEqual(headers, {})

    def test_openai_uses_standard_environment_name(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.yaml"
            path.write_text(
                """
llm:
  provider: openai
  base_url: https://api.openai.com/v1
  model: test-model
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": (
                        "openai-secret"
                    ),
                },
                clear=True,
            ):
                settings = Settings.load(
                    str(path)
                )
                api_key, headers = (
                    resolve_llm_credentials(
                        settings.llm
                    )
                )

        self.assertEqual(
            settings.llm["api_key_env"],
            "OPENAI_API_KEY",
        )
        self.assertEqual(
            api_key,
            "openai-secret",
        )
        self.assertEqual(headers, {})

    def test_openrouter_config_persists_names_only(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.yaml"
            path.write_text(
                """
llm:
  provider: openrouter
  base_url: https://openrouter.ai/api/v1
  model: test/model
  headers_env:
    HTTP-Referer: OPENROUTER_HTTP_REFERER
    X-Title: OPENROUTER_X_TITLE
""".strip()
                + "\n",
                encoding="utf-8",
            )

            environment = {
                "OPENROUTER_API_KEY": (
                    "openrouter-secret"
                ),
                "OPENROUTER_HTTP_REFERER": (
                    "https://example.test"
                ),
                "OPENROUTER_X_TITLE": (
                    "Storycraft"
                ),
            }

            with patch.dict(
                os.environ,
                environment,
                clear=True,
            ):
                settings = Settings.load(
                    str(path)
                )
                api_key, headers = (
                    resolve_llm_credentials(
                        settings.llm
                    )
                )

            workspace_config = (
                _workspace_config(settings)
            )
            serialized = json.dumps(
                workspace_config,
                ensure_ascii=False,
            )

        self.assertEqual(
            settings.llm["api_key_env"],
            "OPENROUTER_API_KEY",
        )
        self.assertEqual(
            api_key,
            "openrouter-secret",
        )
        self.assertEqual(
            headers,
            {
                "HTTP-Referer": (
                    "https://example.test"
                ),
                "X-Title": "Storycraft",
            },
        )

        self.assertIn(
            "OPENROUTER_API_KEY",
            serialized,
        )
        self.assertIn(
            "OPENROUTER_HTTP_REFERER",
            serialized,
        )
        self.assertNotIn(
            "openrouter-secret",
            serialized,
        )
        self.assertNotIn(
            "https://example.test",
            serialized,
        )

    def test_missing_api_key_environment_is_rejected(
        self,
    ) -> None:
        llm = {
            **Settings.load().llm,
            "provider": "openai",
            "base_url": (
                "https://api.openai.com/v1"
            ),
            "api_key_env": "MISSING_API_KEY",
        }

        with (
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
            self.assertRaisesRegex(
                ContractError,
                "MISSING_API_KEY",
            ),
        ):
            resolve_llm_credentials(llm)

    def test_literal_api_key_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.yaml"
            path.write_text(
                """
llm:
  api_key: literal-secret
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ContractError,
                "直接保存",
            ):
                Settings.load(str(path))

    def test_credential_in_base_url_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.yaml"
            path.write_text(
                """
llm:
  base_url: https://user:password@example.test/v1
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ContractError,
                "credential",
            ):
                Settings.load(str(path))

    def test_client_receives_resolved_credentials(
        self,
    ) -> None:
        llm = {
            **Settings.load().llm,
            "provider": "openrouter",
            "base_url": (
                "https://openrouter.ai/api/v1"
            ),
            "model": "test/model",
            "api_key_env": (
                "OPENROUTER_API_KEY"
            ),
            "headers_env": {
                "HTTP-Referer": (
                    "OPENROUTER_HTTP_REFERER"
                ),
            },
        }
        settings = SimpleNamespace(llm=llm)

        with tempfile.TemporaryDirectory() as temporary:
            with (
                patch.dict(
                    os.environ,
                    {
                        "OPENROUTER_API_KEY": (
                            "runtime-secret"
                        ),
                        "OPENROUTER_HTTP_REFERER": (
                            "https://example.test"
                        ),
                    },
                    clear=True,
                ),
                patch(
                    "storycraft.llm.OpenAI"
                ) as openai,
            ):
                openai.return_value.models.list.return_value = (
                    SimpleNamespace(data=[])
                )

                LLMClient(
                    settings,
                    Path(temporary),
                )

        options = openai.call_args.kwargs

        self.assertEqual(
            options["api_key"],
            "runtime-secret",
        )
        self.assertEqual(
            options["default_headers"],
            {
                "HTTP-Referer": (
                    "https://example.test"
                ),
            },
        )
        self.assertEqual(
            options["max_retries"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
