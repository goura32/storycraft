"""Provider-boundary credential validation.

The public Storycraft settings contract is the flat JSON payload validated by
``workspace._validate_settings``.  The remaining helpers validate and adapt only the internal HTTP-boundary mapping; no SDK client boundary is exposed.
"""
from __future__ import annotations

import math
import os
import re
from copy import deepcopy
from urllib.parse import parse_qsl, urlsplit
from typing import Any

from .endpoint_security import resolve_allowed_addresses
from .series_contracts import ContractError


LLM_PROVIDERS = frozenset({"ollama"})
_PROVIDER_API_KEY_ENV: dict[str, str] = {}
_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SECRET_QUERY_NAMES = frozenset({"api_key", "apikey", "key", "token", "access_token", "refresh_token", "secret"})
_FORBIDDEN_LLM_FIELDS = frozenset({"api_key", "authorization", "headers", "default_headers"})


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label}は空でない文字列が必要です")
    return value.strip()


def _validate_environment_name(value: object, label: str, *, allow_none: bool) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or _ENV_NAME_RE.fullmatch(value) is None:
        raise ContractError(f"{label}は有効な環境変数名が必要です")
    return value


def _validate_positive_number(value: object, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or float(value) <= 0:
        raise ContractError(f"{label}は0より大きい有限数が必要です")


def _validate_base_url(value: object) -> str:
    base_url = _required_text(value, "llm.base_url")
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError as exc:
        raise ContractError("llm.base_urlのURLが不正です") from exc
    if parsed.scheme != "http" or not parsed.netloc:
        raise ContractError("llm.base_urlはhttp URLが必要です")
    if parsed.username is not None or parsed.password is not None:
        raise ContractError("llm.base_urlへcredentialを埋め込むことはできません")
    for name, _value in parse_qsl(parsed.query, keep_blank_values=True):
        if name.lower().replace("-", "_") in _SECRET_QUERY_NAMES:
            raise ContractError("llm.base_urlのqueryへcredentialを埋め込むことはできません")
    host = parsed.hostname
    if host is None:
        raise ContractError("llm.base_urlへホスト名が必要です")
    try:
        # The canonical Ollama HTTP boundary uses the same private-address
        # validation as the direct provider request path.
        resolve_allowed_addresses(host, port)
    except ContractError as exc:
        raise ContractError("llm.base_urlはloopbackまたはプライベートLANのhostだけ許可されます") from exc
    return base_url


def _validate_header_name(value: object) -> str:
    header = _required_text(value, "llm.headers_env header")
    if ":" in header or any(ord(character) < 33 or ord(character) > 126 for character in header):
        raise ContractError("llm.headers_envのHeader名が不正です")
    return header


def _validate_llm(llm: object) -> dict[str, Any]:
    if not isinstance(llm, dict):
        raise ContractError("llm設定はオブジェクトが必要です")
    forbidden = set(llm) & _FORBIDDEN_LLM_FIELDS
    if forbidden:
        raise ContractError("LLM credentialを設定ファイルへ直接保存できません: " + ", ".join(sorted(forbidden)))
    provider = _required_text(llm.get("provider"), "llm.provider")
    if provider not in LLM_PROVIDERS:
        raise ContractError(f"llm.providerが不正です: {provider!r}")
    validated = deepcopy(llm)
    validated["provider"] = provider
    validated["base_url"] = _validate_base_url(validated.get("base_url"))
    validated["model"] = _required_text(validated.get("model"), "llm.model")
    validated["api_key_env"] = _validate_environment_name(validated.get("api_key_env"), "llm.api_key_env", allow_none=True)
    if validated["api_key_env"] is None:
        validated["api_key_env"] = _PROVIDER_API_KEY_ENV.get(provider)
    headers_env = validated.get("headers_env", {})
    if not isinstance(headers_env, dict):
        raise ContractError("llm.headers_envはオブジェクトが必要です")
    validated_headers: dict[str, str] = {}
    for raw_header, raw_environment in headers_env.items():
        header = _validate_header_name(raw_header)
        environment = _validate_environment_name(raw_environment, f"llm.headers_env.{header}", allow_none=False)
        assert isinstance(environment, str)
        if header.lower() in {existing.lower() for existing in validated_headers}:
            raise ContractError("llm.headers_envに大文字小文字だけが異なる重複Headerがあります")
        validated_headers[header] = environment
    validated["headers_env"] = validated_headers
    for field_name in ("first_event_timeout_seconds", "idle_timeout_seconds", "stream_progress_log_interval_seconds"):
        _validate_positive_number(validated.get(field_name), f"llm.{field_name}")
    for field_name in ("thinking", "stream"):
        if not isinstance(validated.get(field_name), bool):
            raise ContractError(f"llm.{field_name}はbooleanが必要です")
    return validated


def resolve_llm_credentials(llm: dict[str, Any], *, environ: dict[str, str] | os._Environ[str] | None = None) -> tuple[str, dict[str, str]]:
    """Resolve provider credentials from environment without persisting values."""
    validated = _validate_llm(llm)
    environment = os.environ if environ is None else environ
    provider = validated["provider"]
    api_key_env = validated["api_key_env"]
    if api_key_env is None:
        api_key = "ollama" if provider == "ollama" else "not-required"
    else:
        api_key = environment.get(api_key_env, "")
        if not api_key:
            raise ContractError(f"LLM API key環境変数が設定されていません: {api_key_env}")
    default_headers: dict[str, str] = {}
    for header, environment_name in validated["headers_env"].items():
        value = environment.get(environment_name, "")
        if not value:
            raise ContractError(f"LLM Header環境変数が設定されていません: {environment_name}")
        default_headers[header] = value
    return api_key, default_headers
