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
import threading
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
from .artifact_record import validate_call_record
from .endpoint_security import pinned_http_request
from .error_sanitizer import redact_value
from .filesystem_security import (
    _open_directory_chain,
    absolute_without_resolving,
    assert_directory_fd_identity,
    assert_file_identity_at,
    assert_no_symlink_path,
    assert_within,
    atomic_write_text_noreplace,
    directory_identity,
    directory_entry_identity,
    directory_fd_path,
    ensure_directory_at,
    open_directory_at,
    read_text_at,
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
_SEED_RESERVATION_LOCK = threading.RLock()


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
    while path.endswith("/v1/v1"):
        path = path[:-3]
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
    runtime_descriptor: int
    directory_descriptor: int

    @classmethod
    def open(
        cls,
        workspace_root: Path,
        directory: Path,
        *,
        runtime_descriptor: int | None = None,
        directory_descriptor: int | None = None,
    ) -> "_RecordAnchor":
        root_candidate = absolute_without_resolving(Path(workspace_root))
        expected_root_identity = directory_identity(root_candidate)
        root_path = assert_no_symlink_path(root_candidate, require_directory=True)
        directory_path = Path(directory)
        root_descriptor: int | None = None
        owned_runtime_descriptor: int | None = None
        owned_directory_descriptor: int | None = None
        try:
            if runtime_descriptor is not None or directory_descriptor is not None:
                if runtime_descriptor is None or directory_descriptor is None:
                    raise ContractError("runtime/calls descriptorは一組で必要です")
                root_descriptor = _open_directory_chain(root_path, expected_identity=expected_root_identity)
                owned_runtime_descriptor = os.dup(runtime_descriptor)
                owned_directory_descriptor = os.dup(directory_descriptor)
                directory_path = directory_fd_path(root_descriptor) / "runtime/calls"
                assert_directory_fd_identity(directory_fd_path(root_descriptor) / "runtime", owned_runtime_descriptor)
                assert_directory_fd_identity(directory_path, owned_directory_descriptor)
            else:
                candidate_absolute = absolute_without_resolving(directory_path)
                assert_within(root_path, candidate_absolute)
                candidate_relative = candidate_absolute.relative_to(absolute_without_resolving(root_path)).parts
                if candidate_relative != ("runtime", "calls"):
                    raise ContractError("call record directoryはworkspace/runtime/callsでなければなりません")
                root_descriptor = _open_directory_chain(root_path, expected_identity=expected_root_identity)
                expected_runtime_identity = directory_entry_identity(root_descriptor, "runtime")
                owned_runtime_descriptor = open_directory_at(
                    root_descriptor,
                    ("runtime",),
                    expected_identity=expected_runtime_identity,
                )
                try:
                    expected_directory_identity = directory_entry_identity(owned_runtime_descriptor, "calls")
                except ContractError as missing_or_invalid:
                    try:
                        os.stat("calls", dir_fd=owned_runtime_descriptor, follow_symlinks=False)
                    except FileNotFoundError:
                        owned_directory_descriptor = ensure_directory_at(owned_runtime_descriptor, ("calls",), exist_ok=True)
                    except OSError:
                        raise missing_or_invalid
                    else:
                        raise missing_or_invalid
                else:
                    owned_directory_descriptor = open_directory_at(
                        owned_runtime_descriptor,
                        ("calls",),
                        expected_identity=expected_directory_identity,
                    )
                directory_path = directory_fd_path(root_descriptor) / "runtime/calls"
            relative_parts = ("runtime", "calls")
            try:
                counter_stat = os.stat("counters.json", dir_fd=owned_runtime_descriptor, follow_symlinks=False)
            except FileNotFoundError as exc:
                raise ContractError("runtime/counters.jsonがありません") from exc
            if stat.S_ISLNK(counter_stat.st_mode) or not stat.S_ISREG(counter_stat.st_mode):
                raise ContractError("runtime/counters.jsonが通常fileではありません")
            assert_directory_fd_identity(directory_path, owned_directory_descriptor)
            return cls(root_path, directory_path, relative_parts, root_descriptor, owned_runtime_descriptor, owned_directory_descriptor)
        except Exception:
            for descriptor in (owned_directory_descriptor, owned_runtime_descriptor, root_descriptor):
                if isinstance(descriptor, int):
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
            raise

    def assert_current(self) -> None:
        assert_directory_fd_identity(self.root_path, self.root_descriptor)
        assert_directory_fd_identity(directory_fd_path(self.root_descriptor) / "runtime", self.runtime_descriptor)
        assert_directory_fd_identity(self.directory_path, self.directory_descriptor)

    def close(self) -> None:
        for descriptor in (self.directory_descriptor, self.runtime_descriptor, self.root_descriptor):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _assert_seed_available(directory_fd: int, seed: int) -> None:
    """Reject a physical provider call seed already persisted in this workspace."""
    try:
        entries = os.listdir(directory_fd)
    except OSError as exc:
        raise ContractError("call record directoryを列挙できません") from exc
    for name in entries:
        if re.fullmatch(r"call-[0-9]{6}", name) is None:
            continue
        try:
            call_descriptor = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            try:
                record = json.loads(read_text_at(call_descriptor, Path("record.json")))
            finally:
                os.close(call_descriptor)
            validated = validate_call_record(name, record)
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            raise ContractError("既存call recordのseedを検証できません") from exc
        if validated["seed"] == seed:
            raise ContractError("provider callのseedが既存物理callと重複しています")


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
    runtime_descriptor: int | None = None,
    directory_descriptor: int | None = None,
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
    anchor = record_anchor or _RecordAnchor.open(
        Path(workspace_root),
        Path(directory),
        runtime_descriptor=runtime_descriptor,
        directory_descriptor=directory_descriptor,
    )
    try:
        anchor.assert_current()
        call_id = f"call-{reserve_counter_at(anchor.root_descriptor, 'next_call', runtime_descriptor=anchor.runtime_descriptor):06d}"
        try:
            os.mkdir(call_id, 0o700, dir_fd=anchor.directory_descriptor)
        except FileExistsError as exc:
            raise ContractError("call counterのrecord directoryが既に存在します") from exc
        target_name = call_id
        record_identity: tuple[int, int] | None = None
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
                record_identity = atomic_write_text_noreplace(
                    directory_fd_path(target_descriptor) / "record.json",
                    _canonical_json(record) + "\n",
                )
                assert_file_identity_at(target_descriptor, "record.json", record_identity)
                assert_directory_fd_identity(directory_fd_path(anchor.directory_descriptor) / target_name, target_descriptor)
            finally:
                os.close(target_descriptor)
            anchor.assert_current()
            return call_id
        except Exception as error:
            record_identity = getattr(error, "_storycraft_published_identity", record_identity)
            remove_target = False
            if record_identity is None:
                try:
                    probe_descriptor = os.open(
                        target_name,
                        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                        dir_fd=anchor.directory_descriptor,
                    )
                    try:
                        remove_target = not os.listdir(probe_descriptor)
                    finally:
                        os.close(probe_descriptor)
                except OSError:
                    remove_target = False
            else:
                try:
                    probe_descriptor = os.open(
                        target_name,
                        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                        dir_fd=anchor.directory_descriptor,
                    )
                    try:
                        assert_file_identity_at(probe_descriptor, "record.json", record_identity)
                        remove_target = True
                    finally:
                        os.close(probe_descriptor)
                except (OSError, ContractError):
                    remove_target = False
            if remove_target:
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


def _generate_with_anchor_impl(
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
    capability_seed = seed + 1
    _assert_seed_available(record_anchor.directory_descriptor, capability_seed)
    _assert_seed_available(record_anchor.directory_descriptor, seed)
    context_length = _capability(base_url, model, call_record_dir=call_record_dir,
                                 technical_attempt=technical_attempt, format_attempt=format_attempt, seed=capability_seed,
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


def _generate_with_anchor(*args: Any, **kwargs: Any) -> dict[str, Any] | str:
    """Serialize seed check, provider calls, and their immutable records."""
    with _SEED_RESERVATION_LOCK:
        return _generate_with_anchor_impl(*args, **kwargs)


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
    runtime_directory_descriptor: int | None = None,
    call_record_descriptor: int | None = None,
) -> dict[str, Any] | str:
    """Invoke the provider only with an FD-anchored audit record destination."""
    if call_record_dir is None:
        raise ContractError("provider呼出しにはcall record directoryが必要です")
    if workspace_root is None:
        raise ContractError("call recordを保存するにはworkspace_rootが必要です")
    _require_settings_id(settings_id)
    anchor = _RecordAnchor.open(
        Path(workspace_root),
        Path(call_record_dir),
        runtime_descriptor=runtime_directory_descriptor,
        directory_descriptor=call_record_descriptor,
    )
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
