"""OpenAI-compatible Ollama V2 boundary.

This module is deliberately transport-only: it discovers a model's capability via
``/v1/models/{model}``, sends a non-streaming OpenAI chat completion, and writes
one immutable audit record for each physical HTTP call when given a call directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Callable
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from jsonschema import Draft202012Validator, ValidationError

from .artifact_ids import reserve_counter
from .series_contracts import ContractError


class OllamaTechnicalError(ContractError):
    """A connection, HTTP, or timeout failure from the provider."""


class OllamaResponseFormatError(ContractError):
    """The provider replied, but its capability or structured response was malformed."""


def normalized_v1_base_url(endpoint: str) -> str:
    """Return exactly one OpenAI-compatible ``/v1`` path suffix."""
    parsed = urlsplit(endpoint)
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1"):
        path = f"{path}/v1" if path else "/v1"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _write_record(
    directory: Path | None,
    *,
    operation: str,
    endpoint: str,
    model: str,
    request: str | None,
    response: str | None,
    transport: str,
    validation: dict[str, Any],
    technical_attempt: int,
    format_attempt: int,
    seed: int,
    settings_id: str | None = None,
    role: str = "provider",
    input_refs: list[str] | None = None,
    target_candidate_id: str | None = None,
) -> str | None:
    if directory is None:
        return None
    counters = directory.parent / "counters.json"
    if directory.name == "calls" and counters.is_file():
        call_id = f"call-{reserve_counter(directory.parent.parent, 'next_call'):06d}"
    else:
        # Standalone boundary tests have no workspace counter authority.
        call_id = f"call-{uuid4().hex}"
    target = directory / call_id
    # A newly-created directory gives each physical call a write-once namespace.
    target.mkdir(parents=True, exist_ok=False)
    record = {
        "schema_version": 1,
        "call_id": call_id,
        "operation": operation,
        "role": role,
        "target_candidate_id": target_candidate_id,
        "input_refs": [] if input_refs is None else input_refs,
        "technical_attempt": technical_attempt,
        "format_attempt": format_attempt,
        "seed": seed,
        "endpoint": endpoint,
        "model": model,
        "settings_id": settings_id,
        "request": request,
        "response": response,
        "transport": transport,
        "validation": validation,
    }
    (target / "record.json").write_text(_canonical_json(record) + "\n", encoding="utf-8")
    return call_id


def _capability(
    base_url: str,
    model: str,
    *,
    call_record_dir: Path | None,
    technical_attempt: int,
    format_attempt: int,
    seed: int,
    settings_id: str | None,
) -> int:
    url = f"{base_url}/models/{quote(model, safe='')}"
    raw = ""
    try:
        with urlopen(Request(url, method="GET"), timeout=30) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw)
    except (HTTPError, URLError, OSError) as exc:
        _write_record(call_record_dir, operation="model_capability", endpoint=base_url, model=model,
                      request=None, response=None, transport="failure",
                      validation={"result": "not_applicable", "checks": [], "failure_code": None},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed, settings_id=settings_id)
        raise OllamaTechnicalError("Ollamaモデル情報取得に失敗しました") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _write_record(call_record_dir, operation="model_capability", endpoint=base_url, model=model,
                      request=None, response=raw, transport="success",
                      validation={"result": "invalid", "checks": [], "failure_code": "json_parse"},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed, settings_id=settings_id)
        raise OllamaResponseFormatError("Ollamaモデル情報が不正です") from exc
    valid = (
        isinstance(payload, dict)
        and set(payload) == {"id", "context_length"}
        and payload.get("id") == model
        and isinstance(payload.get("context_length"), int)
        and not isinstance(payload.get("context_length"), bool)
        and payload["context_length"] > 0
    )
    _write_record(call_record_dir, operation="model_capability", endpoint=base_url, model=model,
                  request=None, response=_canonical_json(payload), transport="success",
                  validation={"result": "valid" if valid else "invalid", "checks": ["id", "context_length"] if valid else [], "failure_code": None if valid else "schema_invalid"},
                  technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed, settings_id=settings_id)
    if not valid:
        raise OllamaResponseFormatError("Ollamaモデル情報が不正です")
    return payload["context_length"]


def generate(
    endpoint: str,
    model: str,
    prompt: str,
    schema: dict[str, Any] | None,
    *,
    request_options: Optional[dict[str, Any]] = None,
    messages: Optional[list[dict[str, str]]] = None,
    call_record_dir: Path | None = None,
    technical_attempt: int = 1,
    format_attempt: int = 1,
    seed: int = 1,
    operation: str = "generate",
    call_id_sink: Callable[[str], None] | None = None,
    settings_id: str | None = None,
    input_refs: list[str] | None = None,
    target_candidate_id: str | None = None,
) -> dict[str, Any] | str:
    """Invoke the non-streaming OpenAI-compatible structured or prose endpoint."""
    base_url = normalized_v1_base_url(endpoint)
    context_length = _capability(base_url, model, call_record_dir=call_record_dir,
                                 technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                                 settings_id=settings_id)
    # Use model's max context from capability, not settings
    options = {"num_ctx": context_length, "seed": seed}
    if request_options:
        # Only allow user-specified sampling options; think/stream/num_ctx are provider-controlled
        allowed = {"temperature", "top_p", "top_k", "repeat_penalty"}
        for key, value in request_options.items():
            if key in allowed:
                options[key] = value
    body_value = {
        "model": model,
        "messages": messages if messages is not None else [{"role": "user", "content": prompt}],
        "think": True,
        "stream": False,
        "options": options,
    }
    if schema is not None:
        body_value["response_format"] = {"type": "json_schema", "json_schema": {"name": "storycraft_response", "strict": True, "schema": schema}}
    body = _canonical_json(body_value)
    raw = ""
    try:
        request = Request(f"{base_url}/chat/completions", data=body.encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            envelope = json.loads(raw)
        content = envelope["choices"][0]["message"]["content"]
        if schema is None:
            if not isinstance(content, str) or not content.strip():
                raise TypeError("prose content is empty")
            value = content
        else:
            value = json.loads(content)
            if not isinstance(value, dict):
                raise TypeError("structured content is not an object")
            Draft202012Validator(schema).validate(value)
    except (HTTPError, URLError, OSError) as exc:
        call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                      request=body, response=None, transport="failure",
                      validation={"result": "not_applicable", "checks": [], "failure_code": None},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                      settings_id=settings_id, input_refs=input_refs, target_candidate_id=target_candidate_id)
        if call_id is not None and call_id_sink is not None:
            call_id_sink(call_id)
        raise OllamaTechnicalError("Ollama呼出しに失敗しました") from exc
    except ValidationError as exc:
        call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                      request=body, response=raw, transport="success",
                      validation={"result": "invalid", "checks": [], "failure_code": "schema_invalid"},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                      settings_id=settings_id, input_refs=input_refs, target_candidate_id=target_candidate_id)
        if call_id is not None and call_id_sink is not None:
            call_id_sink(call_id)
        raise OllamaResponseFormatError("Ollama応答JSONがschemaに一致しません") from exc
    except (UnicodeDecodeError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                      request=body, response=raw if "raw" in locals() else None, transport="success",
                      validation={"result": "invalid", "checks": [], "failure_code": "json_parse"},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                      settings_id=settings_id, input_refs=input_refs, target_candidate_id=target_candidate_id)
        if call_id is not None and call_id_sink is not None:
            call_id_sink(call_id)
        raise OllamaResponseFormatError("Ollama応答JSONが不正です") from exc
    call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                  request=body, response=content, transport="success",
                  validation={"result": "valid", "checks": [], "failure_code": None},
                  technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                  settings_id=settings_id, input_refs=input_refs, target_candidate_id=target_candidate_id)
    if call_id is not None and call_id_sink is not None:
        call_id_sink(call_id)
    return value
