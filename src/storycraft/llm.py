"""Provider HTTP boundary呼び出し層。

Ollamaの非ストリーミングHTTP応答を受け、各物理呼出しのcall recordとraw logを
FD anchorへ保存する。SDK client、stream fallback、別provider transportは持たない。
"""
from __future__ import annotations

import json
import os
import re
import stat
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import weakref

from .error_sanitizer import (
    redact_secrets,
    redact_value,
    safe_exception_message,
    sanitize_text,
)
from .filesystem_security import (
    assert_directory_fd_identity,
    assert_file_identity_at,
    assert_no_symlink_path,
    atomic_write_text_noreplace,
    absolute_without_resolving,
    directory_identity,
    directory_entry_identity,
    directory_fd_path,
    ensure_directory_at,
    _open_directory_chain,
    open_directory_at,
    read_text_at,
    unlink_if_identity_at,
)
from .log import logger
from .ollama import OllamaResponseFormatError, OllamaTechnicalError, generate as ollama_generate
from .series_contracts import ContractError

STATUS_THINKING = "thinking"
STATUS_CONTENT = "content"
STATUS_SAVING = "saving"
_RAW_LOG_LOCK = threading.Lock()


def _close_descriptors(*descriptors: int | None) -> None:
    for descriptor in descriptors:
        if not isinstance(descriptor, int):
            continue
        try:
            os.close(descriptor)
        except OSError:
            pass


def _entry_exists_at(directory_fd: int, name: str) -> bool:
    try:
        entry_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(entry_stat.st_mode):
        raise ContractError("raw log entryが通常fileではありません")
    return True


def _raw_filename_component(value: str) -> str:
    """監査メタを保ったまま、ファイル名だけを移植可能な文字列へ正規化する。"""
    # 進捗refの総数（v:1/4 等）はログ/JSONメタには残し、ファイル名では省く。
    value = re.sub(r"/\d+", "", value)
    value = re.sub(r"([vcs]):\s*(\d+)", r"\1\2", value)
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return normalized or "unknown"


def _raw_filename(rec: "CallRecord", index: int) -> str:
    """生データ名へ工程を常に含め、工程に属さない座標は出力しない。"""
    parts = [f"{index:04d}", _raw_filename_component(rec.kind), _raw_filename_component(rec.phase)]
    scope_by_stage = {
        "volume_plan": ("v",),
        "chapter_plan": ("v", "c"),
        "scene_plan": ("v", "c", "s"),
        "scene_card": ("v", "c", "s"),
        "scene_prose": ("v", "c", "s"),
        "scene_continuity": ("v", "c", "s"),
    }
    for coordinate in scope_by_stage.get(rec.phase, ()):
        match = re.search(rf"\b{coordinate}:\s*(\d+)", rec.ref)
        if match:
            parts.append(f"{coordinate}{match.group(1)}")
    return "_".join(parts)


@dataclass
class CallRecord:
    kind: str
    phase: str
    ref: str
    attempt: int
    seed: int
    retry_total: int = 1
    quality_pass: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    content: str = ""
    meta_chunks: list[dict] = field(default_factory=list)  # {t, kind, chars}
    error: str | None = None
    call_id: str | None = None

    def log_identity(self) -> str:
        quality = f" quality_pass={self.quality_pass}" if self.quality_pass else ""
        coordinate = "" if self.ref == self.phase else f" {self.ref.replace(' ', ',')}"
        return f"stage={self.phase}{coordinate} kind={self.kind}{quality} retry={self.attempt}/{self.retry_total}"

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "phase": self.phase,
            "ref": self.ref,
            "attempt": self.attempt,
            "retry_total": self.retry_total,
            "quality_pass": self.quality_pass,
            "seed": self.seed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "content_chars": len(self.content),
            "meta_chunks": self.meta_chunks,
            "error": (
                sanitize_text(self.error)
                if self.error is not None
                else None
            ),
        }


def _open_canonical_workspace_descriptors(
    workspace_root: Path,
    raw_dir: Path,
    *,
    expected_root_identity: tuple[int, int] | None = None,
    include_calls: bool = True,
) -> tuple[Path, int, int, int | None, int]:
    """Open root, runtime, calls, and raw logs in ancestor-FD order.

    The runtime ancestor must be captured before opening any runtime child.  In
    particular, opening ``raw_logs`` first and then resolving ``runtime`` by
    pathname would allow an ancestor replacement to redirect call records.
    """
    root_candidate = absolute_without_resolving(Path(workspace_root))
    raw_candidate = absolute_without_resolving(Path(raw_dir))
    canonical_raw = root_candidate / "runtime" / "raw_logs"
    if raw_candidate != canonical_raw:
        raise ContractError("raw log directoryはworkspace/runtime/raw_logsでなければなりません")
    if expected_root_identity is None:
        expected_root_identity = directory_identity(root_candidate)
    root_path = assert_no_symlink_path(root_candidate, require_directory=True)
    root_descriptor: int | None = None
    runtime_descriptor: int | None = None
    call_descriptor: int | None = None
    raw_descriptor: int | None = None
    try:
        root_descriptor = _open_directory_chain(root_path, expected_identity=expected_root_identity)
        expected_runtime_identity = directory_entry_identity(root_descriptor, "runtime")
        runtime_descriptor = open_directory_at(
            root_descriptor,
            ("runtime",),
            expected_identity=expected_runtime_identity,
        )
        if include_calls:
            expected_call_identity = directory_entry_identity(runtime_descriptor, "calls")
            call_descriptor = open_directory_at(
                runtime_descriptor,
                ("calls",),
                expected_identity=expected_call_identity,
            )
        try:
            expected_raw_identity = directory_entry_identity(runtime_descriptor, "raw_logs")
        except ContractError as missing_or_invalid:
            try:
                entry = os.stat("raw_logs", dir_fd=runtime_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                raw_descriptor = ensure_directory_at(runtime_descriptor, ("raw_logs",), exist_ok=True)
            except OSError:
                raise missing_or_invalid
            else:
                raise missing_or_invalid
        else:
            raw_descriptor = open_directory_at(
                runtime_descriptor,
                ("raw_logs",),
                expected_identity=expected_raw_identity,
            )
        return root_path, root_descriptor, runtime_descriptor, call_descriptor, raw_descriptor
    except Exception:
        _close_descriptors(*(descriptor for descriptor in (raw_descriptor, call_descriptor, runtime_descriptor, root_descriptor) if isinstance(descriptor, int)))
        raise


class LLMClient:
    def __init__(
        self,
        settings,
        raw_dir: Path,
        workspace_root: Path | None = None,
    ) -> None:
        if settings.llm.get("ollama_http_boundary") is not True:
            raise ContractError("Ollama providerはHTTP boundary経由でなければなりません")
        if workspace_root is None:
            raise ContractError("LLMClientにはworkspace_rootが必要です")
        root_candidate = absolute_without_resolving(Path(workspace_root))
        raw_candidate = absolute_without_resolving(Path(raw_dir))
        expected_root_identity = directory_identity(root_candidate)
        root, root_descriptor, runtime_descriptor, call_descriptor, raw_descriptor = _open_canonical_workspace_descriptors(
            root_candidate,
            raw_candidate,
            expected_root_identity=expected_root_identity,
        )
        self.settings = settings
        self.settings_id = getattr(settings, "settings_id", None)
        self.raw_dir = raw_candidate
        self.workspace_root = root
        self._workspace_root_anchor_path = directory_fd_path(root_descriptor)
        self._workspace_root_descriptor = root_descriptor
        self._runtime_directory_descriptor = runtime_descriptor
        self._call_directory_descriptor = call_descriptor
        self._raw_directory_descriptor = raw_descriptor
        self._directory_finalizer = weakref.finalize(
            self,
            _close_descriptors,
            call_descriptor,
            runtime_descriptor,
            raw_descriptor,
            root_descriptor,
        )


    def close(self) -> None:
        finalizer = getattr(self, "_directory_finalizer", None)
        if finalizer is not None and finalizer.alive:
            finalizer()
        self._workspace_root_descriptor = None
        self._runtime_directory_descriptor = None
        self._call_directory_descriptor = None
        self._raw_directory_descriptor = None
        self._workspace_root_anchor_path = None

    def persisted_seed_ceiling(self) -> int:
        """Return the largest seed already persisted in canonical call records."""
        calls_descriptor = getattr(self, "_call_directory_descriptor", None)
        if not isinstance(calls_descriptor, int):
            raise ContractError("provider callにはcanonical calls descriptorが必要です")
        ceiling = 0
        for entry in os.listdir(calls_descriptor):
            if not re.fullmatch(r"call-[0-9]{6}", entry):
                continue
            descriptor = os.open(
                entry,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=calls_descriptor,
            )
            try:
                record = json.loads(read_text_at(descriptor, Path("record.json")))
            except (OSError, json.JSONDecodeError) as exc:
                raise ContractError("既存call recordのseedを検証できません") from exc
            finally:
                os.close(descriptor)
            if not isinstance(record, dict) or not isinstance(record.get("seed"), int) or isinstance(record.get("seed"), bool):
                raise ContractError("既存call recordのseedが不正です")
            ceiling = max(ceiling, record["seed"])
        return ceiling

    def _ensure_directory_anchors(self) -> None:
        """Initialize anchors for narrowly-scoped low-level test/adaptor objects."""
        if isinstance(getattr(self, "_workspace_root_descriptor", None), int) and isinstance(
            getattr(self, "_raw_directory_descriptor", None), int
        ) and isinstance(getattr(self, "_runtime_directory_descriptor", None), int) and isinstance(
            getattr(self, "_call_directory_descriptor", None), int
        ):
            return
        workspace_root = getattr(self, "workspace_root", None)
        raw_dir = getattr(self, "raw_dir", None)
        if workspace_root is None or raw_dir is None:
            raise ContractError("provider callにはworkspace_rootとraw_dirが必要です")
        root_candidate = absolute_without_resolving(Path(workspace_root))
        raw_candidate = absolute_without_resolving(Path(raw_dir))
        expected_root_identity = directory_identity(root_candidate)
        root, root_descriptor, runtime_descriptor, call_descriptor, raw_descriptor = _open_canonical_workspace_descriptors(
            root_candidate,
            raw_candidate,
            expected_root_identity=expected_root_identity,
        )
        self.workspace_root = root
        self.raw_dir = raw_candidate
        self._workspace_root_anchor_path = directory_fd_path(root_descriptor)
        self._workspace_root_descriptor = root_descriptor
        self._runtime_directory_descriptor = runtime_descriptor
        self._call_directory_descriptor = call_descriptor
        self._raw_directory_descriptor = raw_descriptor
        self._directory_finalizer = weakref.finalize(
            self,
            _close_descriptors,
            call_descriptor,
            runtime_descriptor,
            raw_descriptor,
            root_descriptor,
        )

    def call_once(self, messages, response_format, seed: int) -> CallRecord:
        if self.settings.llm.get("ollama_http_boundary") is not True:
            raise ContractError("Ollama providerはHTTP boundary経由でなければなりません")
        meta = messages[-1] if messages and isinstance(messages[-1], dict) else {}
        bound_settings_id = meta.get("settings_id") or self.settings_id or getattr(self.settings, "settings_id", None)
        if not isinstance(bound_settings_id, str) or re.fullmatch(r"settings-[0-9]{6}", bound_settings_id) is None:
            raise ContractError("provider callには有効なsettings_idが必要です")
        visible_messages = [
            message for message in messages
            if isinstance(message, dict) and isinstance(message.get("role"), str)
            and isinstance(message.get("content"), str)
        ]
        rec = CallRecord(
            kind=meta.get("__kind", "gen"), phase=meta.get("__phase", ""),
            ref=meta.get("__ref", ""), attempt=meta.get("__attempt", 1), seed=seed,
            retry_total=meta.get("__retry_total", 1), quality_pass=meta.get("__quality_pass", ""),
        )
        schema: dict[str, Any] | None = None
        if isinstance(response_format, dict):
            schema = response_format.get("json_schema", {}).get("schema", {"type": "object"})
        self._ensure_directory_anchors()
        root_descriptor = getattr(self, "_workspace_root_descriptor", None)
        runtime_descriptor = getattr(self, "_runtime_directory_descriptor", None)
        call_descriptor = getattr(self, "_call_directory_descriptor", None)
        if not isinstance(root_descriptor, int) or not isinstance(runtime_descriptor, int) or not isinstance(call_descriptor, int):
            raise ContractError("provider callにはworkspace root descriptorが必要です")
        anchored_root = directory_fd_path(root_descriptor)
        anchored_call_dir = directory_fd_path(call_descriptor)
        try:
            value = ollama_generate(
                self.settings.llm["base_url"], self.settings.llm["model"],
                visible_messages[-1]["content"] if visible_messages else "", schema,
                request_options=self.settings.llm.get("request_options"),
                messages=visible_messages, call_record_dir=anchored_call_dir,
                workspace_root=anchored_root,
                technical_attempt=rec.attempt, format_attempt=meta.get("__format_attempt", 1), seed=seed,
                operation=rec.kind, call_id_sink=lambda call_id: setattr(rec, "call_id", call_id),
                settings_id=bound_settings_id, input_refs=meta.get("input_refs", []),
                target_candidate_id=meta.get("target_candidate_id"),
                runtime_directory_descriptor=runtime_descriptor,
                call_record_descriptor=call_descriptor,
            )
            rec.content = value if schema is None and isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        except OllamaResponseFormatError:
            rec.finished_at = time.time()
            raise
        except OllamaTechnicalError as error:
            rec.error = safe_exception_message(error)
        except ContractError:
            raise
        rec.finished_at = time.time()
        return rec

    @staticmethod
    def _raw_markdown(filename: str, sent_messages: list, content: str) -> str:
        """生ログを、送受信の区切りが明確な人間確認用Markdownへ整形する。"""
        labels = {"system": "送信 (system)", "user": "送信 (user)"}
        sections = [f"# {filename}"]
        for message in sent_messages:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            message_content = message.get("content")
            if isinstance(role, str) and isinstance(message_content, str):
                sections.append(f"---\n## {labels.get(role, f'送信 ({role})')}\n\n{message_content}")
        sections.append(f"---\n## 受信\n\n{content}")
        return "\n".join(sections) + "\n"

    def save_raw(self, rec: CallRecord, prompt_messages: list) -> None:
        """送受信生データと、人間向けMarkdownを同じstemで保存。thinking本文は除く。"""
        with _RAW_LOG_LOCK:
            root_descriptor = getattr(self, "_workspace_root_descriptor", None)
            raw_descriptor = getattr(self, "_raw_directory_descriptor", None)
            temporary_anchor = False
            runtime_anchor_descriptor: int | None = None
            if not isinstance(root_descriptor, int) or not isinstance(raw_descriptor, int):
                raw_candidate = absolute_without_resolving(Path(self.raw_dir))
                workspace_root = getattr(self, "workspace_root", None)
                if workspace_root is None:
                    raise ContractError("raw log保存にはworkspace_rootが必要です")
                root_candidate = absolute_without_resolving(Path(workspace_root))
                expected_root_identity = directory_identity(root_candidate)
                _, root_descriptor, runtime_anchor_descriptor, _, raw_descriptor = _open_canonical_workspace_descriptors(
                    root_candidate,
                    raw_candidate,
                    expected_root_identity=expected_root_identity,
                    include_calls=False,
                )
                temporary_anchor = True
            try:
                assert_directory_fd_identity(
                    getattr(self, "_workspace_root_anchor_path", None) or self.workspace_root,
                    root_descriptor,
                )
                assert_directory_fd_identity(self.raw_dir, raw_descriptor)
                raw_view = directory_fd_path(raw_descriptor)
                idx = 0
                while True:
                    stem = _raw_filename(rec, idx)
                    json_name = f"{stem}.json"
                    markdown_name = f"{stem}.md"
                    reservation_name = f".{stem}.reserve"
                    reservation_identity: tuple[int, int] | None = None
                    descriptor: int | None = None
                    json_path = raw_view / json_name
                    markdown_path = raw_view / markdown_name
                    try:
                        descriptor = os.open(
                            reservation_name,
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                            0o600,
                            dir_fd=raw_descriptor,
                        )
                        reservation_stat = os.fstat(descriptor)
                        if not stat.S_ISREG(reservation_stat.st_mode):
                            raise ContractError("raw reservationが通常fileではありません")
                        reservation_identity = (reservation_stat.st_dev, reservation_stat.st_ino)
                        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                            descriptor = None
                            handle.write(str(os.getpid()))
                            handle.flush()
                            os.fsync(handle.fileno())
                        if _entry_exists_at(raw_descriptor, json_name) or _entry_exists_at(raw_descriptor, markdown_name):
                            unlink_if_identity_at(raw_descriptor, reservation_name, reservation_identity)
                            idx += 1
                            continue
                        break
                    except FileExistsError:
                        idx += 1
                        continue
                    except Exception:
                        if descriptor is not None:
                            os.close(descriptor)
                        if reservation_identity is not None:
                            unlink_if_identity_at(raw_descriptor, reservation_name, reservation_identity)
                        raise

                json_published = False
                markdown_published = False
                json_identity: tuple[int, int] | None = None
                markdown_identity: tuple[int, int] | None = None
                try:
                    sent_messages_value = redact_value([
                        m for m in prompt_messages
                        if not (isinstance(m, dict) and "__" in "".join(m.keys()))
                    ])
                    assert isinstance(sent_messages_value, list)
                    sent_messages = sent_messages_value
                    received = redact_value(rec.to_dict())
                    assert isinstance(received, dict)
                    if received["error"] is not None:
                        received["error"] = sanitize_text(received["error"])
                    content = redact_secrets(rec.content)
                    out = {
                        "index": idx,
                        "sent_messages": sent_messages,
                        "received": received,
                        "content": content,
                    }
                    try:
                        json_identity = self._write_raw_file(json_path, json.dumps(out, ensure_ascii=False, indent=2))
                        json_published = True
                    except Exception as error:
                        json_published = bool(getattr(error, "_storycraft_published_target", False))
                        json_identity = getattr(error, "_storycraft_published_identity", None)
                        raise
                    try:
                        markdown_identity = self._write_raw_file(markdown_path, self._raw_markdown(markdown_path.name, sent_messages, content))
                        markdown_published = True
                    except Exception as error:
                        markdown_published = bool(getattr(error, "_storycraft_published_target", False))
                        markdown_identity = getattr(error, "_storycraft_published_identity", None)
                        raise
                    if json_identity is None or markdown_identity is None:
                        raise ContractError("raw log公開identityがありません")
                    assert_file_identity_at(raw_descriptor, json_name, json_identity)
                    assert_file_identity_at(raw_descriptor, markdown_name, markdown_identity)
                    assert_directory_fd_identity(self.raw_dir, raw_descriptor)
                except Exception:
                    # A raw call is published only as a complete JSON/Markdown pair.
                    # Roll back the first rename when the second file cannot be made.
                    if json_published and json_identity is not None:
                        unlink_if_identity_at(raw_descriptor, json_name, json_identity)
                    if markdown_published and markdown_identity is not None:
                        unlink_if_identity_at(raw_descriptor, markdown_name, markdown_identity)
                    raise
                finally:
                    if reservation_identity is not None:
                        unlink_if_identity_at(raw_descriptor, reservation_name, reservation_identity)
            finally:
                if temporary_anchor:
                    _close_descriptors(raw_descriptor, runtime_anchor_descriptor, root_descriptor)

    @staticmethod
    def _write_raw_file(path: Path, content: str) -> tuple[int, int]:
        return atomic_write_text_noreplace(path, content)
