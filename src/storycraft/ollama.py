"""OpenAI-compatible Ollama boundary.

This module is deliberately transport-only: it discovers a model's capability via
``/v1/models/{model}``, sends a non-streaming OpenAI chat completion, and writes
one immutable audit record for each physical HTTP call when given a call directory.
"""
from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from collections.abc import Callable
from dataclasses import dataclass
import socket
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from jsonschema import Draft202012Validator, ValidationError

from .artifact_ids import reserve_counter_at
from .endpoint_security import pinned_http_request
from .error_sanitizer import redact_value
from .filesystem_security import (
    absolute_without_resolving,
    assert_directory_fd_identity,
    assert_no_symlink_path,
    assert_within,
    atomic_write_text,
    directory_fd_path,
    open_workspace_directory,
    remove_directory_at,
)
from .series_contracts import ContractError, EndpointResolutionError, LLMCallError


class OllamaTechnicalError(LLMCallError):
    """A connection, HTTP, or timeout failure from the provider."""


class OllamaResponseFormatError(ContractError):
    """The provider replied, but its capability or structured response was malformed."""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "provider redirect is not allowed", headers, fp)


_HTTP_OPENER = build_opener(ProxyHandler({}), _NoRedirectHandler)


def urlopen(request: Request, timeout: float):
    """Open only the address resolved and validated immediately for this call."""
    return _HTTP_OPENER.open(pinned_http_request(request), timeout=timeout)


def _failure_code(error: BaseException) -> str:
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(error, HTTPError):
        return "http_error"
    if isinstance(error, (URLError, OSError)):
        return "connection_error"
    return "connection_error"


def normalized_v1_base_url(endpoint: str) -> str:
    """Return exactly one OpenAI-compatible ``/v1`` path suffix."""
    try:
        parsed = urlsplit(endpoint)
    except (TypeError, ValueError) as exc:
        raise ContractError("provider endpointのURLが不正です") from exc
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1"):
        path = f"{path}/v1" if path else "/v1"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _require_settings_id(settings_id: str | None) -> None:
    if not isinstance(settings_id, str) or re.fullmatch(r"settings-[0-9]{6}", settings_id) is None:
        raise ContractError("call recordを保存するには有効なsettings_idが必要です")


@dataclass
class _RecordAnchor:
    root_path: Path
    directory_path: Path
    relative_parts: tuple[str, ...]
    root_descriptor: int
    directory_descriptor: int

    @classmethod
    def open(cls, workspace_root: Path, directory: Path) -> "_RecordAnchor":
        root_path = assert_no_symlink_path(Path(workspace_root), require_directory=True)
        directory_path = Path(directory)
        assert_within(root_path, directory_path)
        root_descriptor, directory_descriptor = open_workspace_directory(root_path, directory_path, create=True)
        try:
            relative_parts = absolute_without_resolving(directory_path).relative_to(absolute_without_resolving(root_path)).parts
            if relative_parts != ("runtime", "calls"):
                raise ContractError("call record directoryはworkspace/runtime/callsでなければなりません")
            runtime_descriptor = os.open(
                "runtime",
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=root_descriptor,
            )
            try:
                try:
                    counter_stat = os.stat("counters.json", dir_fd=runtime_descriptor, follow_symlinks=False)
                except FileNotFoundError as exc:
                    raise ContractError("runtime/counters.jsonがありません") from exc
                if stat.S_ISLNK(counter_stat.st_mode) or not stat.S_ISREG(counter_stat.st_mode):
                    raise ContractError("runtime/counters.jsonが通常fileではありません")
            finally:
                os.close(runtime_descriptor)
            return cls(root_path, absolute_without_resolving(directory_path), relative_parts, root_descriptor, directory_descriptor)
        except Exception:
            os.close(directory_descriptor)
            os.close(root_descriptor)
            raise

    def assert_current(self) -> None:
        assert_directory_fd_identity(self.root_path, self.root_descriptor)
        assert_directory_fd_identity(self.directory_path, self.directory_descriptor)

    def close(self) -> None:
        for descriptor in (self.directory_descriptor, self.root_descriptor):
            try:
                os.close(descriptor)
            except OSError:
                pass


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
    workspace_root: Path | None = None,
    record_anchor: _RecordAnchor | None = None,
    role: str = "provider",
    input_refs: list[str] | None = None,
    target_candidate_id: str | None = None,
) -> str:
    if directory is None:
        raise ContractError("provider呼出しにはcall record directoryが必要です")
    _require_settings_id(settings_id)
    if workspace_root is None:
        raise ContractError("call recordを保存するにはworkspace_rootが必要です")
    owns_anchor = record_anchor is None
    anchor = record_anchor or _RecordAnchor.open(Path(workspace_root), Path(directory))
    try:
        anchor.assert_current()
        call_id = f"call-{reserve_counter_at(anchor.root_descriptor, 'next_call'):06d}"
        try:
            os.mkdir(call_id, 0o700, dir_fd=anchor.directory_descriptor)
        except FileExistsError as exc:
            raise ContractError("call counterのrecord directoryが既に存在します") from exc
        target_name = call_id
        try:
            target_descriptor = os.open(
                target_name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=anchor.directory_descriptor,
            )
            try:
                redacted_request = redact_value(request)
                redacted_response = redact_value(response)
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
                    "request": redacted_request,
                    "response": redacted_response,
                    "transport": transport,
                    "validation": validation,
                }
                atomic_write_text(directory_fd_path(target_descriptor) / "record.json", _canonical_json(record) + "\n")
            finally:
                os.close(target_descriptor)
            anchor.assert_current()
            return call_id
        except Exception:
            try:
                remove_directory_at(anchor.directory_descriptor, target_name)
            except OSError:
                pass
            raise
    finally:
        if owns_anchor:
            anchor.close()


def _capability(
    base_url: str,
    model: str,
    *,
    call_record_dir: Path | None,
    technical_attempt: int,
    format_attempt: int,
    seed: int,
    settings_id: str | None,
    workspace_root: Path | None,
    record_anchor: _RecordAnchor,
) -> int:
    url = f"{base_url}/models/{quote(model, safe='')}"
    raw = ""
    try:
        with urlopen(Request(url, method="GET"), timeout=30) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw)
    except (HTTPError, URLError, OSError, EndpointResolutionError) as exc:
        _write_record(call_record_dir, operation="model_capability", endpoint=base_url, model=model,
                      request=None, response=None, transport="failure",
                      validation={"result": "not_applicable", "checks": [], "failure_code": _failure_code(exc)},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed, settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor)
        raise OllamaTechnicalError("Ollamaモデル情報取得に失敗しました") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _write_record(call_record_dir, operation="model_capability", endpoint=base_url, model=model,
                      request=None, response=raw, transport="success",
                      validation={"result": "invalid", "checks": [], "failure_code": "json_parse"},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed, settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor)
        raise OllamaResponseFormatError("Ollamaモデル情報が不正です") from exc
    if isinstance(payload, dict) and "error" in payload:
        _write_record(call_record_dir, operation="model_capability", endpoint=base_url, model=model,
                      request=None, response=raw, transport="failure",
                      validation={"result": "not_applicable", "checks": [], "failure_code": "provider_error"},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed, settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor)
        raise OllamaTechnicalError("Ollama provider error envelope")
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
                  technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed, settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor)
    if not valid:
        raise OllamaResponseFormatError("Ollamaモデル情報が不正です")
    return payload["context_length"]


def _generate_with_anchor(
    endpoint: str,
    model: str,
    prompt: str,
    schema: dict[str, Any] | None,
    *,
    request_options: Optional[dict[str, Any]] = None,
    messages: Optional[list[dict[str, str]]] = None,
    call_record_dir: Path | None = None,
    workspace_root: Path | None = None,
    technical_attempt: int = 1,
    format_attempt: int = 1,
    seed: int = 1,
    operation: str = "generate",
    call_id_sink: Callable[[str], None] | None = None,
    settings_id: str | None = None,
    input_refs: list[str] | None = None,
    target_candidate_id: str | None = None,
    record_anchor: _RecordAnchor,
) -> dict[str, Any] | str:
    """Invoke the non-streaming OpenAI-compatible structured or prose endpoint."""
    base_url = normalized_v1_base_url(endpoint)
    context_length = _capability(base_url, model, call_record_dir=call_record_dir,
                                 technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                                 settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor)
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
        if isinstance(envelope, dict) and "error" in envelope:
            raise OllamaTechnicalError("Ollama provider error envelope")
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
    except (HTTPError, URLError, OSError, EndpointResolutionError) as exc:
        call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                      request=body, response=None, transport="failure",
                      validation={"result": "not_applicable", "checks": [], "failure_code": _failure_code(exc)},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                      settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor, input_refs=input_refs, target_candidate_id=target_candidate_id)
        if call_id is not None and call_id_sink is not None:
            call_id_sink(call_id)
        raise OllamaTechnicalError("Ollama呼出しに失敗しました") from exc
    except OllamaTechnicalError as exc:
        call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                      request=body, response=raw, transport="failure",
                      validation={"result": "not_applicable", "checks": [], "failure_code": "provider_error"},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                      settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor, input_refs=input_refs, target_candidate_id=target_candidate_id)
        if call_id is not None and call_id_sink is not None:
            call_id_sink(call_id)
        raise exc
    except ValidationError as exc:
        call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                      request=body, response=raw, transport="success",
                      validation={"result": "invalid", "checks": [], "failure_code": "schema_invalid"},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                      settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor, input_refs=input_refs, target_candidate_id=target_candidate_id)
        if call_id is not None and call_id_sink is not None:
            call_id_sink(call_id)
        raise OllamaResponseFormatError("Ollama応答JSONがschemaに一致しません") from exc
    except (UnicodeDecodeError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                      request=body, response=raw if "raw" in locals() else None, transport="success",
                      validation={"result": "invalid", "checks": [], "failure_code": "json_parse"},
                      technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                      settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor, input_refs=input_refs, target_candidate_id=target_candidate_id)
        if call_id is not None and call_id_sink is not None:
            call_id_sink(call_id)
        raise OllamaResponseFormatError("Ollama応答JSONが不正です") from exc
    call_id = _write_record(call_record_dir, operation=operation, endpoint=base_url, model=model,
                  request=body, response=content, transport="success",
                  validation={"result": "valid", "checks": [], "failure_code": None},
                  technical_attempt=technical_attempt, format_attempt=format_attempt, seed=seed,
                  settings_id=settings_id, workspace_root=workspace_root, record_anchor=record_anchor, input_refs=input_refs, target_candidate_id=target_candidate_id)
    if call_id is not None and call_id_sink is not None:
        call_id_sink(call_id)
    return value


def generate(
    endpoint: str,
    model: str,
    prompt: str,
    schema: dict[str, Any] | None,
    *,
    request_options: Optional[dict[str, Any]] = None,
    messages: Optional[list[dict[str, str]]] = None,
    call_record_dir: Path | None = None,
    workspace_root: Path | None = None,
    technical_attempt: int = 1,
    format_attempt: int = 1,
    seed: int = 1,
    operation: str = "generate",
    call_id_sink: Callable[[str], None] | None = None,
    settings_id: str | None = None,
    input_refs: list[str] | None = None,
    target_candidate_id: str | None = None,
) -> dict[str, Any] | str:
    """Invoke the provider only with an FD-anchored audit record destination."""
    if call_record_dir is None:
        raise ContractError("provider呼出しにはcall record directoryが必要です")
    if workspace_root is None:
        raise ContractError("call recordを保存するにはworkspace_rootが必要です")
    _require_settings_id(settings_id)
    anchor = _RecordAnchor.open(Path(workspace_root), Path(call_record_dir))
    try:
        return _generate_with_anchor(
            endpoint,
            model,
            prompt,
            schema,
            request_options=request_options,
            messages=messages,
            call_record_dir=call_record_dir,
            workspace_root=workspace_root,
            technical_attempt=technical_attempt,
            format_attempt=format_attempt,
            seed=seed,
            operation=operation,
            call_id_sink=call_id_sink,
            settings_id=settings_id,
            input_refs=input_refs,
            target_candidate_id=target_candidate_id,
            record_anchor=anchor,
        )
    finally:
        anchor.close()
