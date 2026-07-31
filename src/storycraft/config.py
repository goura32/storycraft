"""設定の読み込み、検証、credential解決。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import yaml

from .series_contracts import ContractError


LLM_PROVIDERS = frozenset({
    "ollama",
})

_PROVIDER_API_KEY_ENV = {}

_ENV_NAME_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)

_SECRET_QUERY_NAMES = frozenset({
    "api_key",
    "apikey",
    "key",
    "token",
    "access_token",
    "refresh_token",
    "secret",
})

_FORBIDDEN_LLM_FIELDS = frozenset({
    "api_key",
    "authorization",
    "headers",
    "default_headers",
})
DEFAULTS: dict[str, Any] = {
    "llm": {
        "provider": "ollama",
        "model": "qwen3.6:35b-a3b-mtp-q4_K_M",
        "api_key_env": None,
        "headers_env": {},
        "thinking": True,
        "stream": True,
        "first_event_timeout_seconds": 3600,
        "idle_timeout_seconds": 600,
        "stream_progress_log_interval_seconds": 60,
    },
    "retry": {
        "max_attempts": 4,
        "technical_retry_limit": 3,
    },
    "quality": {
        "max_critique_passes": 1,
        "invalid_response_limit": 3,
        "improvement_directions": [
            "地の文を削り、くどさを排除する",
            "対話を自然にする",
        ],
        "content_length_target_chars": 2200,
        "content_length_tolerance_chars": 400,
    },
    "output": {
        "dir": "./storycraft-out",
    },
    "diversity": {
        "archive_dir": "~/.storycraft/archive",
        "recent_window": 5,
    },
}


def _deep_merge(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    out = deepcopy(base)

    for key, value in override.items():
        if (
            key in out
            and isinstance(out[key], dict)
            and isinstance(value, dict)
        ):
            out[key] = _deep_merge(
                out[key],
                value,
            )
        else:
            out[key] = deepcopy(value)

    return out


def _required_text(
    value: object,
    label: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(
            f"{label}は空でない文字列が必要です"
        )

    return value.strip()


def _validate_environment_name(
    value: object,
    label: str,
    *,
    allow_none: bool,
) -> str | None:
    if value is None and allow_none:
        return None

    if (
        not isinstance(value, str)
        or not _ENV_NAME_RE.fullmatch(value)
    ):
        raise ContractError(
            f"{label}は有効な環境変数名が必要です"
        )

    return value


def _validate_positive_number(
    value: object,
    label: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise ContractError(
            f"{label}は0より大きい有限数が必要です"
        )


def _validate_base_url(value: object) -> str:
    base_url = _required_text(
        value,
        "llm.base_url",
    )
    parsed = urlsplit(base_url)

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
    ):
        raise ContractError(
            "llm.base_urlはhttpまたはhttps URLが必要です"
        )

    # Loopback-only enforcement per design spec: allow only
    # 127.0.0.0/8, ::1, localhost (admin-cli-and-acceptance-contract §51)
    host = parsed.hostname
    if host is None:
        raise ContractError(
            "llm.base_urlへホスト名が必要です"
        )
    if host != "localhost" and not host.startswith("127."):
        raise ContractError(
            "llm.base_urlはloopbackアドレスのみ許可されます"
        )

    if (
        parsed.username is not None
        or parsed.password is not None
    ):
        raise ContractError(
            "llm.base_urlへcredentialを"
            "埋め込むことはできません"
        )

    for name, _value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):
        normalized = name.lower().replace(
            "-",
            "_",
        )
        if normalized in _SECRET_QUERY_NAMES:
            raise ContractError(
                "llm.base_urlのqueryへcredentialを"
                "埋め込むことはできません"
            )

    return base_url


def _validate_header_name(value: object) -> str:
    header = _required_text(
        value,
        "llm.headers_env header",
    )

    if (
        ":" in header
        or any(
            ord(character) < 33
            or ord(character) > 126
            for character in header
        )
    ):
        raise ContractError(
            "llm.headers_envのHeader名が不正です"
        )

    return header


def _validate_llm(
    llm: object,
) -> dict[str, Any]:
    if not isinstance(llm, dict):
        raise ContractError(
            "llm設定はオブジェクトが必要です"
        )

    forbidden = (
        set(llm)
        & _FORBIDDEN_LLM_FIELDS
    )
    if forbidden:
        raise ContractError(
            "LLM credentialを設定ファイルへ"
            "直接保存できません: "
            + ", ".join(sorted(forbidden))
        )

    provider = _required_text(
        llm.get("provider"),
        "llm.provider",
    )
    if provider not in LLM_PROVIDERS:
        raise ContractError(
            "llm.providerが不正です: "
            f"{provider!r}"
        )

    llm["provider"] = provider
    llm["base_url"] = _validate_base_url(
        llm.get("base_url")
    )
    llm["model"] = _required_text(
        llm.get("model"),
        "llm.model",
    )

    api_key_env = _validate_environment_name(
        llm.get("api_key_env"),
        "llm.api_key_env",
        allow_none=True,
    )
    if api_key_env is None:
        api_key_env = _PROVIDER_API_KEY_ENV.get(
            provider
        )
    llm["api_key_env"] = api_key_env

    headers_env = llm.get("headers_env", {})
    if not isinstance(headers_env, dict):
        raise ContractError(
            "llm.headers_envはオブジェクトが必要です"
        )

    validated_headers: dict[str, str] = {}
    for raw_header, raw_environment in (
        headers_env.items()
    ):
        header = _validate_header_name(
            raw_header
        )
        environment = _validate_environment_name(
            raw_environment,
            (
                "llm.headers_env."
                f"{header}"
            ),
            allow_none=False,
        )
        assert isinstance(environment, str)

        normalized = header.lower()
        if normalized in {
            existing.lower()
            for existing in validated_headers
        }:
            raise ContractError(
                "llm.headers_envに大文字小文字だけが"
                "異なる重複Headerがあります"
            )

        validated_headers[header] = environment

    llm["headers_env"] = validated_headers

    for field_name in (
        "first_event_timeout_seconds",
        "idle_timeout_seconds",
        "stream_progress_log_interval_seconds",
    ):
        _validate_positive_number(
            llm.get(field_name),
            f"llm.{field_name}",
        )

    for field_name in (
        "thinking",
        "stream",
    ):
        if not isinstance(
            llm.get(field_name),
            bool,
        ):
            raise ContractError(
                f"llm.{field_name}はbooleanが必要です"
            )

    return llm


def resolve_llm_credentials(
    llm: dict[str, Any],
    *,
    environ: dict[str, str] | os._Environ[str] | None = None,
) -> tuple[str, dict[str, str]]:
    """環境変数からAPI keyと追加Headerを解決する。"""
    validated = _validate_llm(
        deepcopy(llm)
    )
    environment = (
        os.environ
        if environ is None
        else environ
    )

    provider = validated["provider"]
    api_key_env = validated["api_key_env"]

    if api_key_env is None:
        api_key = (
            "ollama"
            if provider == "ollama"
            else "not-required"
        )
    else:
        api_key = environment.get(
            api_key_env,
            "",
        )
        if not api_key:
            raise ContractError(
                "LLM API key環境変数が"
                "設定されていません: "
                f"{api_key_env}"
            )

    default_headers: dict[str, str] = {}
    for header, environment_name in (
        validated["headers_env"].items()
    ):
        value = environment.get(
            environment_name,
            "",
        )
        if not value:
            raise ContractError(
                "LLM Header環境変数が"
                "設定されていません: "
                f"{environment_name}"
            )

        default_headers[header] = value

    return api_key, default_headers


def _environment_float(
    environment_name: str,
) -> float:
    value = os.environ[environment_name]

    try:
        parsed = float(value)
    except ValueError as exc:
        raise ContractError(
            f"{environment_name}は数値が必要です"
        ) from exc

    if not math.isfinite(parsed) or parsed <= 0:
        raise ContractError(
            f"{environment_name}は"
            "0より大きい有限数が必要です"
        )

    return parsed


def _apply_environment_overrides(
    config: dict[str, Any],
) -> None:
    llm = config["llm"]

    text_overrides = {
        "STORYCRAFT_LLM_PROVIDER": "provider",
        "STORYCRAFT_LLM_BASE_URL": "base_url",
        "STORYCRAFT_LLM_MODEL": "model",
    }
    for environment_name, field_name in (
        text_overrides.items()
    ):
        value = os.environ.get(
            environment_name
        )
        if value:
            llm[field_name] = value

    if "STORYCRAFT_LLM_API_KEY_ENV" in os.environ:
        value = os.environ[
            "STORYCRAFT_LLM_API_KEY_ENV"
        ].strip()
        llm["api_key_env"] = value or None

    numeric_overrides = {
        "STORYCRAFT_LLM_IDLE_TIMEOUT": (
            "idle_timeout_seconds"
        ),
        "STORYCRAFT_LLM_FIRST_TIMEOUT": (
            "first_event_timeout_seconds"
        ),
    }
    for environment_name, field_name in (
        numeric_overrides.items()
    ):
        if environment_name in os.environ:
            llm[field_name] = _environment_float(
                environment_name
            )


@dataclass
class Settings:
    llm: dict[str, Any] = field(
        default_factory=dict
    )
    retry: dict[str, Any] = field(
        default_factory=dict
    )
    quality: dict[str, Any] = field(
        default_factory=dict
    )
    output: dict[str, Any] = field(
        default_factory=dict
    )
    diversity: dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def load(
        cls,
        config_path: str | None = None,
    ) -> "Settings":
        config = _deep_merge(
            DEFAULTS,
            {},
        )

        if config_path:
            path = Path(
                config_path
            ).expanduser()

            if not path.exists():
                raise FileNotFoundError(
                    "設定ファイルが見つかりません: "
                    f"{config_path}"
                )

            try:
                with path.open(
                    encoding="utf-8"
                ) as handle:
                    user = (
                        yaml.safe_load(handle)
                        or {}
                    )
            except yaml.YAMLError as exc:
                raise ContractError(
                    "設定YAMLを解析できません"
                ) from exc

            if not isinstance(user, dict):
                raise ContractError(
                    "設定ファイルはオブジェクトが必要です"
                )

            config = _deep_merge(
                config,
                user,
            )

        _apply_environment_overrides(config)
        config["llm"] = _validate_llm(
            config["llm"]
        )

        max_critique_passes = config[
            "quality"
        ].get("max_critique_passes")
        if (
            isinstance(
                max_critique_passes,
                bool,
            )
            or not isinstance(
                max_critique_passes,
                int,
            )
            or max_critique_passes < 0
        ):
            raise ContractError(
                "quality.max_critique_passesは"
                "0以上の整数で指定してください"
            )

        invalid_response_limit = config[
            "quality"
        ].get("invalid_response_limit")
        if (
            isinstance(
                invalid_response_limit,
                bool,
            )
            or not isinstance(
                invalid_response_limit,
                int,
            )
            or invalid_response_limit < 1
        ):
            raise ContractError(
                "quality.invalid_response_limitは"
                "1以上の整数で指定してください"
            )

        technical_retry_limit = config[
            "retry"
        ].get("technical_retry_limit")
        if (
            isinstance(
                technical_retry_limit,
                bool,
            )
            or not isinstance(
                technical_retry_limit,
                int,
            )
            or technical_retry_limit < 1
        ):
            raise ContractError(
                "retry.technical_retry_limitは"
                "1以上の整数で指定してください"
            )

        return cls(
            llm=config["llm"],
            retry=config["retry"],
            quality=config["quality"],
            output=config["output"],
            diversity=config["diversity"],
        )

    def resolve_archive_dir(self) -> Path:
        return Path(
            os.path.expanduser(
                self.diversity["archive_dir"]
            )
        )

    def resolve_output_dir(
        self,
        cli_out: str | None,
    ) -> Path:
        if cli_out:
            return Path(cli_out)

        if self.output.get("dir"):
            return Path(
                os.path.expanduser(
                    self.output["dir"]
                )
            )

        return Path("./storycraft-out")
