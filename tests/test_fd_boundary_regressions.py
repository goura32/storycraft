"""Independent regression probes for descriptor and provider boundaries."""
from __future__ import annotations

import gc
import ipaddress
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request
from unittest.mock import patch

from storycraft.endpoint_security import pinned_http_request
from storycraft.artifact_ids import initial_counters
from storycraft.endpoint_security import EndpointResolutionError
from storycraft.cli import _load_object
from storycraft.llm import CallRecord, LLMClient
from storycraft.ollama import OllamaTechnicalError, _HTTP_OPENER, generate, urlopen
from storycraft.prompt_template import PromptTemplate
from storycraft.series_contracts import ContractError
from storycraft.workspace import create_workspace
from storycraft.workspace import validate_workspace
import storycraft.filesystem_security as filesystem_module
import storycraft.llm as llm_module
import storycraft.ollama as ollama_module
import storycraft.workspace as workspace_module


class _ProviderHandler(BaseHTTPRequestHandler):
    swap_callback = None
    request_count = 0

    def log_message(self, *_args) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        payload = {"id": "probe-model", "context_length": 4096}
        self._send_json(payload)

    def do_POST(self) -> None:  # noqa: N802
        type(self).request_count += 1
        if type(self).swap_callback is not None:
            type(self).swap_callback()
            type(self).swap_callback = None
        payload = {"choices": [{"message": {"content": "ok"}}]}
        self._send_json(payload)

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _RedirectHandler(BaseHTTPRequestHandler):
    request_count = 0

    def log_message(self, *_args) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        type(self).request_count += 1
        self.send_response(302)
        self.send_header("Location", "http://127.0.0.1:1/should-not-follow")
        self.end_headers()


class DescriptorBoundaryRegressionTests(unittest.TestCase):
    @staticmethod
    def _bare_workspace(root: Path) -> None:
        (root / "runtime/calls").mkdir(parents=True)
        (root / "runtime/counters.json").write_text(json.dumps(initial_counters()) + "\n", encoding="utf-8")
        (root / "runtime/raw_logs").mkdir(parents=True)

    @staticmethod
    def _swap_directory(path: Path, backup: Path, external: Path) -> None:
        path.rename(backup)
        path.symlink_to(external, target_is_directory=True)

    def test_call_record_anchor_rejects_directory_swap_without_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            external = Path(temporary) / "external-calls"
            root.mkdir()
            external.mkdir()
            self._bare_workspace(root)
            calls = root / "runtime/calls"
            backup = root / "runtime/calls.backup"

            server = HTTPServer(("127.0.0.1", 0), _ProviderHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            _ProviderHandler.swap_callback = lambda: self._swap_directory(calls, backup, external)
            try:
                with self.assertRaises(ContractError):
                    generate(
                        f"http://127.0.0.1:{server.server_port}",
                        "probe-model",
                        "probe",
                        None,
                        call_record_dir=calls,
                        workspace_root=root,
                        settings_id="settings-000001",
                    )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
                if calls.is_symlink():
                    calls.unlink()
                if backup.exists():
                    backup.rename(calls)
            self.assertEqual(list(external.iterdir()), [])

    def test_llm_call_rejects_runtime_replacement_before_provider_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            client = LLMClient(
                SimpleNamespace(
                    settings_id="settings-000001",
                    llm={
                        "ollama_http_boundary": True,
                        "base_url": "http://127.0.0.1:1/v1",
                        "model": "probe-model",
                    },
                ),
                root / "runtime/raw_logs",
                workspace_root=root,
            )
            runtime = root / "runtime"
            backup = base / "runtime-original"
            replacement = base / "runtime-replacement"
            (replacement / "calls").mkdir(parents=True)
            (replacement / "raw_logs").mkdir()
            (replacement / "counters.json").write_text(json.dumps(initial_counters()) + "\n", encoding="utf-8")
            runtime.rename(backup)
            replacement.rename(runtime)
            try:
                with self.assertRaises(ContractError):
                    client.call_once(
                        [{"role": "user", "content": "probe"}, {"settings_id": "settings-000001"}],
                        None,
                        1,
                    )
            finally:
                client.close()
                runtime.rename(replacement)
                backup.rename(runtime)
            self.assertEqual(list((replacement / "calls").iterdir()), [])

    def test_raw_log_anchor_rejects_directory_swap_without_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            raw_dir = root / "runtime/raw_logs"
            external = Path(temporary) / "external-raw"
            external.mkdir()
            backup = root / "runtime/raw_logs.backup"
            settings = SimpleNamespace(llm={"ollama_http_boundary": True}, retry={})
            client = LLMClient(settings, raw_dir, workspace_root=root)
            original_write = client._write_raw_file
            write_count = 0

            def swap_after_first(path: Path, content: str) -> None:
                nonlocal write_count
                original_write(path, content)
                write_count += 1
                if write_count == 1:
                    self._swap_directory(raw_dir, backup, external)

            client._write_raw_file = swap_after_first
            record = CallRecord(kind="generate", phase="probe", ref="probe", attempt=1, seed=1, content="ok")
            try:
                with self.assertRaises(ContractError):
                    client.save_raw(record, [{"role": "user", "content": "probe"}])
            finally:
                client.close()
                if raw_dir.is_symlink():
                    raw_dir.unlink()
                if backup.exists():
                    backup.rename(raw_dir)
            self.assertEqual(list(external.iterdir()), [])

    def test_raw_reservation_is_removed_when_existing_nonregular_pair_entry_is_found(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            raw_dir = root / "runtime/raw_logs"
            os.mkfifo(raw_dir / "0000_generate_probe.json")
            settings = SimpleNamespace(llm={"ollama_http_boundary": True}, retry={})
            client = LLMClient(settings, raw_dir, workspace_root=root)
            try:
                with self.assertRaises(ContractError):
                    client.save_raw(
                        CallRecord(kind="generate", phase="probe", ref="probe", attempt=1, seed=1, content="ok"),
                        [],
                    )
                self.assertEqual(list(raw_dir.glob(".*.reserve")), [])
            finally:
                client.close()

    def test_workspace_returns_fd_anchored_root_after_parent_alias_swap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            parent = base / "parent"
            parent.mkdir()
            root = parent / "workspace"
            backup_parent = base / "parent.backup"
            original_check = workspace_module._assert_directory_fd_identity
            parent_checks = 0

            def check(path: Path, descriptor: int) -> None:
                nonlocal parent_checks
                original_check(path, descriptor)
                if path == parent:
                    parent_checks += 1
                    if parent_checks == 4:
                        parent.rename(backup_parent)
                        parent.mkdir()

            request = {
                "title": "題名", "genre": ["幻想"], "premise": "前提",
                "required_elements": [], "avoid": [], "ending_preference": "希望",
                "volume_count": 4, "language": "ja",
            }
            settings = {
                "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "probe",
                "technical_retry_limit": 1, "quality_revision_limit": 1,
                "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1],
                "chapter_scene_range": [1, 1], "scene_text_char_range": [100, 100],
            }
            with patch.object(workspace_module, "_assert_directory_fd_identity", side_effect=check):
                anchored = create_workspace(
                    root, workspace_id="ws-probe", request=request, settings=settings,
                    created_at="2026-08-05T00:00:00Z",
                )
            self.assertTrue(isinstance(anchored, Path))
            self.assertTrue((anchored / "runtime/run-state.json").is_file())
            self.assertFalse(root.exists())
            anchored.close()  # type: ignore[attr-defined]

    def test_workspace_first_open_race_rejects_replaced_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            parent = base / "parent"
            parent.mkdir()
            root = parent / "workspace"
            external = base / "external-parent"
            external.mkdir()
            backup = base / "parent.backup"
            original_open = filesystem_module.os.open
            swapped = False

            def raced_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if not swapped and path == parent.name and kwargs.get("dir_fd") is not None:
                    swapped = True
                    parent.rename(backup)
                    external.rename(parent)
                return original_open(path, flags, *args, **kwargs)

            request = {
                "title": "題名", "genre": ["幻想"], "premise": "前提",
                "required_elements": [], "avoid": [], "ending_preference": "希望",
                "volume_count": 4, "language": "ja",
            }
            settings = {
                "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "probe",
                "technical_retry_limit": 1, "quality_revision_limit": 1,
                "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1],
                "chapter_scene_range": [1, 1], "scene_text_char_range": [100, 100],
            }
            try:
                with patch.object(filesystem_module.os, "open", side_effect=raced_open):
                    with self.assertRaises(ContractError):
                        create_workspace(
                            root, workspace_id="ws-probe", request=request, settings=settings,
                            created_at="2026-08-05T00:00:00Z",
                        )
                self.assertFalse((parent / "workspace").exists())
            finally:
                if parent.exists():
                    parent.rename(external)
                if backup.exists():
                    backup.rename(parent)

    def test_call_record_published_leaf_swap_is_rejected_without_deleting_competitor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            calls = root / "runtime/calls"
            server = HTTPServer(("127.0.0.1", 0), _ProviderHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            original_write = ollama_module.atomic_write_text_noreplace
            swapped = False

            def swap_record_leaf(path: Path, content: str) -> tuple[int, int]:
                nonlocal swapped
                identity = original_write(path, content)
                if not swapped and path.name == "record.json":
                    path.unlink()
                    path.write_text('{"attacker":true}\n', encoding="utf-8")
                    swapped = True
                return identity

            try:
                with patch.object(ollama_module, "atomic_write_text_noreplace", side_effect=swap_record_leaf):
                    with self.assertRaises(ContractError):
                        generate(
                            f"http://127.0.0.1:{server.server_port}",
                            "probe-model",
                            "probe",
                            None,
                            call_record_dir=calls,
                            workspace_root=root,
                            settings_id="settings-000001",
                        )
                leaf = calls / "call-000001/record.json"
                self.assertEqual(leaf.read_text(encoding="utf-8"), '{"attacker":true}\n')
                self.assertFalse((calls / "call-000002").exists())
            finally:
                server.shutdown()
                server.server_close()

    def test_call_record_directory_leaf_swap_is_rejected_without_deleting_original(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            calls = root / "runtime/calls"
            backup = base / "call-original"
            server = HTTPServer(("127.0.0.1", 0), _ProviderHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            original_write = ollama_module.atomic_write_text_noreplace
            swapped = False

            def swap_call_directory(path: Path, content: str) -> tuple[int, int]:
                nonlocal swapped
                identity = original_write(path, content)
                if not swapped and path.name == "record.json":
                    target_directory = Path(os.readlink(path.parent))
                    target_directory.rename(backup)
                    target_directory.mkdir()
                    swapped = True
                return identity

            try:
                with patch.object(ollama_module, "atomic_write_text_noreplace", side_effect=swap_call_directory):
                    with self.assertRaises(ContractError):
                        generate(
                            f"http://127.0.0.1:{server.server_port}",
                            "probe-model",
                            "probe",
                            None,
                            call_record_dir=calls,
                            workspace_root=root,
                            settings_id="settings-000001",
                        )
                self.assertTrue((backup / "record.json").is_file())
                self.assertEqual(list((calls / "call-000001").iterdir()), [])
            finally:
                server.shutdown()
                server.server_close()

    def test_call_record_first_open_race_rejects_replaced_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            calls = root / "runtime/calls"
            external = Path(temporary) / "external-calls"
            external.mkdir()
            backup = root / "runtime/calls.backup"
            original_open = ollama_module.open_workspace_directory
            swapped = False

            def raced_open(root_arg, child_arg, *, create=True, **kwargs):
                nonlocal swapped
                if not swapped:
                    swapped = True
                    calls.rename(backup)
                    external.rename(calls)
                return original_open(root_arg, child_arg, create=create, **kwargs)

            try:
                with patch.object(ollama_module, "open_workspace_directory", side_effect=raced_open):
                    with self.assertRaises(ContractError):
                        ollama_module.generate(
                            "http://127.0.0.1:1", "probe-model", "probe", None,
                            call_record_dir=calls, workspace_root=root, settings_id="settings-000001",
                        )
                self.assertEqual(list(calls.iterdir()), [])
            finally:
                if calls.exists():
                    calls.rename(external)
                if backup.exists():
                    backup.rename(calls)

    def test_raw_log_first_open_race_rejects_replaced_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            raw_dir = root / "runtime/raw_logs"
            external = Path(temporary) / "external-raw"
            external.mkdir()
            backup = root / "runtime/raw_logs.backup"
            original_open = llm_module.open_workspace_directory
            swapped = False

            def raced_open(root_arg, child_arg, *, create=True, **kwargs):
                nonlocal swapped
                if not swapped:
                    swapped = True
                    raw_dir.rename(backup)
                    external.rename(raw_dir)
                return original_open(root_arg, child_arg, create=create, **kwargs)

            settings = SimpleNamespace(
                settings_id="settings-000001",
                llm={"ollama_http_boundary": True, "base_url": "http://127.0.0.1:1/v1", "model": "probe"},
                retry={},
            )
            try:
                with patch.object(llm_module, "open_workspace_directory", side_effect=raced_open):
                    with self.assertRaises(ContractError):
                        LLMClient(settings, raw_dir, workspace_root=root)
                self.assertEqual(list(raw_dir.iterdir()), [])
            finally:
                if raw_dir.exists():
                    raw_dir.rename(external)
                if backup.exists():
                    backup.rename(raw_dir)

    def test_raw_post_publish_failure_rolls_back_published_pair_member(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            client = LLMClient(
                SimpleNamespace(settings_id="settings-000001", llm={"ollama_http_boundary": True}, retry={}),
                root / "runtime/raw_logs",
                workspace_root=root,
            )
            original_fsync = filesystem_module.os.fsync
            fsync_count = 0

            def fail_after_json_publish(descriptor: int) -> None:
                nonlocal fsync_count
                fsync_count += 1
                if fsync_count == 3:  # reservation, JSON temporary, JSON directory
                    raise OSError("directory fsync failed after publication")
                original_fsync(descriptor)

            try:
                with patch.object(filesystem_module.os, "fsync", side_effect=fail_after_json_publish):
                    with self.assertRaises(OSError):
                        client.save_raw(
                            CallRecord(kind="generate", phase="probe", ref="probe", attempt=1, seed=1, content="ok"),
                            [{"role": "user", "content": "probe"}],
                        )
                self.assertEqual(list((root / "runtime/raw_logs").iterdir()), [])
            finally:
                client.close()

    def test_raw_published_leaf_swap_is_rejected_without_deleting_competitor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            client = LLMClient(
                SimpleNamespace(settings_id="settings-000001", llm={"ollama_http_boundary": True}, retry={}),
                root / "runtime/raw_logs",
                workspace_root=root,
            )
            original_write = llm_module.atomic_write_text_noreplace
            swapped = False

            def swap_json_leaf(path: Path, content: str) -> tuple[int, int]:
                nonlocal swapped
                identity = original_write(path, content)
                if not swapped and path.name.endswith(".json"):
                    path.unlink()
                    path.write_text('{"attacker":true}\n', encoding="utf-8")
                    swapped = True
                return identity

            try:
                with patch.object(llm_module, "atomic_write_text_noreplace", side_effect=swap_json_leaf):
                    with self.assertRaises(ContractError):
                        client.save_raw(
                            CallRecord(kind="generate", phase="probe", ref="probe", attempt=1, seed=1, content="ok"),
                            [{"role": "user", "content": "probe"}],
                        )
                json_files = list((root / "runtime/raw_logs").glob("*.json"))
                self.assertEqual(len(json_files), 1)
                self.assertEqual(json_files[0].read_text(encoding="utf-8"), '{"attacker":true}\n')
                self.assertEqual(list((root / "runtime/raw_logs").glob("*.md")), [])
            finally:
                client.close()

    def test_raw_target_competitor_after_reservation_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            raw_dir = root / "runtime/raw_logs"
            settings = SimpleNamespace(llm={"ollama_http_boundary": True}, retry={})
            client = LLMClient(settings, raw_dir, workspace_root=root)
            original_exists = llm_module._entry_exists_at
            injected = False

            def inject_competitor(directory_fd: int, name: str) -> bool:
                nonlocal injected
                result = original_exists(directory_fd, name)
                if not injected and name.endswith(".json"):
                    descriptor = os.open(
                        name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0),
                        0o600,
                        dir_fd=directory_fd,
                    )
                    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                        handle.write("competitor")
                    injected = True
                return result

            try:
                with patch.object(llm_module, "_entry_exists_at", side_effect=inject_competitor):
                    with self.assertRaises(ContractError):
                        client.save_raw(
                            CallRecord(kind="generate", phase="probe", ref="probe", attempt=1, seed=1, content="ok"),
                            [{"role": "user", "content": "probe"}],
                        )
                competitor = next(raw_dir.glob("*.json"))
                self.assertEqual(competitor.read_text(encoding="utf-8"), "competitor")
                self.assertEqual(list(raw_dir.glob(".*.reserve")), [])
            finally:
                client.close()

    def test_mutated_boundary_cannot_reach_sdk_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            settings = SimpleNamespace(
                settings_id="settings-000001",
                llm={"ollama_http_boundary": True, "base_url": "http://127.0.0.1:1/v1", "model": "probe"},
                retry={},
            )
            client = LLMClient(settings, root / "runtime/raw_logs", workspace_root=root)
            called = False

            class Completions:
                def create(self, **_kwargs):
                    nonlocal called
                    called = True
                    return []

            client.client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
            try:
                client.settings.llm["ollama_http_boundary"] = False
                with self.assertRaisesRegex(ContractError, "HTTP boundary"):
                    client.call_once([{"role": "user", "content": "probe"}], None, 1)
                self.assertFalse(called)
                self.assertEqual(list((root / "runtime/calls").glob("*/record.json")), [])
            finally:
                client.close()

    def test_validate_does_not_delete_stale_raw_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            parent = base / "parent"
            parent.mkdir()
            root = parent / "workspace"
            request = {
                "title": "題名", "genre": ["幻想"], "premise": "前提",
                "required_elements": [], "avoid": [], "ending_preference": "希望",
                "volume_count": 4, "language": "ja",
            }
            settings = {
                "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "probe",
                "technical_retry_limit": 1, "quality_revision_limit": 1,
                "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1],
                "chapter_scene_range": [1, 1], "scene_text_char_range": [100, 100],
            }
            workspace = create_workspace(
                root, workspace_id="ws-probe", request=request, settings=settings,
                created_at="2026-08-05T00:00:00Z",
            )
            try:
                raw_dir = workspace / "runtime/raw_logs"
                reservation = raw_dir / ".0000_probe_generate.reserve"
                json_path = raw_dir / "0000_probe_generate.json"
                reservation.write_text("0", encoding="ascii")
                json_path.write_text("probe", encoding="utf-8")
                before = {path.name: path.read_bytes() for path in raw_dir.iterdir()}
                with self.assertRaises(ContractError):
                    validate_workspace(workspace)
                after = {path.name: path.read_bytes() for path in raw_dir.iterdir()}
                self.assertEqual(after, before)
            finally:
                workspace.close()  # type: ignore[attr-defined]

    def test_workspace_target_competitor_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            parent = base / "parent"
            parent.mkdir()
            root = parent / "workspace"
            original_check = workspace_module._assert_directory_fd_identity
            parent_checks = 0

            def check(path: Path, descriptor: int) -> None:
                nonlocal parent_checks
                original_check(path, descriptor)
                if path == parent:
                    parent_checks += 1
                    if parent_checks == 3:
                        root.write_text("competitor", encoding="utf-8")

            request = {
                "title": "題名", "genre": ["幻想"], "premise": "前提",
                "required_elements": [], "avoid": [], "ending_preference": "希望",
                "volume_count": 4, "language": "ja",
            }
            settings = {
                "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "probe",
                "technical_retry_limit": 1, "quality_revision_limit": 1,
                "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1],
                "chapter_scene_range": [1, 1], "scene_text_char_range": [100, 100],
            }
            with patch.object(workspace_module, "_assert_directory_fd_identity", side_effect=check):
                with self.assertRaisesRegex(ContractError, "既に存在"):
                    create_workspace(
                        root, workspace_id="ws-probe", request=request, settings=settings,
                        created_at="2026-08-05T00:00:00Z",
                    )
            self.assertEqual(root.read_text(encoding="utf-8"), "competitor")

    def test_prompt_loader_releases_root_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            template_dir = Path(temporary) / "templates"
            template_dir.mkdir()
            before = len(os.listdir("/proc/self/fd"))
            loaders = [PromptTemplate(template_dir) for _ in range(20)]
            self.assertEqual(len({loader._root_descriptor for loader in loaders}), 20)
            for loader in loaders:
                loader.close()
            del loaders
            gc.collect()
            self.assertLessEqual(len(os.listdir("/proc/self/fd")), before + 2)

    def test_provider_pins_hostname_and_preserves_host_header(self) -> None:
        request = Request("http://local.test:11434/v1/models/probe")
        with patch(
            "storycraft.endpoint_security.resolve_allowed_addresses",
            return_value=(ipaddress.ip_address("127.0.0.1"),),
        ):
            pinned = pinned_http_request(request)
        self.assertEqual(pinned.full_url, "http://127.0.0.1:11434/v1/models/probe")
        self.assertEqual(pinned.get_header("Host"), "local.test:11434")

    def test_provider_opener_disables_environment_proxy(self) -> None:
        proxy_handlers = [handler for handler in _HTTP_OPENER.handlers if isinstance(handler, ProxyHandler)]
        self.assertEqual(proxy_handlers, [])

    def test_llm_constructor_rejects_sdk_provider_bypass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            settings = SimpleNamespace(
                llm={"base_url": "http://127.0.0.1:11434/v1", "model": "probe", "ollama_http_boundary": False},
            )
            with self.assertRaisesRegex(ContractError, "HTTP boundary"):
                LLMClient(settings, root / "runtime/raw_logs", workspace_root=root)

    def test_completion_dns_failure_is_recorded_as_technical_failure(self) -> None:
        server = HTTPServer(("127.0.0.1", 0), _ProviderHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            root.mkdir()
            self._bare_workspace(root)
            import storycraft.ollama as ollama_module
            original_pin = ollama_module.pinned_http_request
            pin_calls = 0

            def fail_on_completion(request):
                nonlocal pin_calls
                pin_calls += 1
                if pin_calls == 2:
                    raise EndpointResolutionError("probe DNS failure")
                return original_pin(request)

            try:
                with patch("storycraft.ollama.pinned_http_request", side_effect=fail_on_completion):
                    with self.assertRaises(OllamaTechnicalError):
                        generate(
                            f"http://127.0.0.1:{server.server_port}", "probe-model", "probe", None,
                            call_record_dir=root / "runtime/calls", workspace_root=root,
                            settings_id="settings-000001",
                        )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
            records = [json.loads(path.read_text(encoding="utf-8")) for path in (root / "runtime/calls").glob("*/record.json")]
            completion = next(record for record in records if record["operation"] == "generate")
            self.assertEqual(completion["transport"], "failure")
            self.assertEqual(completion["validation"]["failure_code"], "connection_error")

    def test_cli_input_fifo_is_rejected_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fifo = Path(temporary) / "input.json"
            os.mkfifo(fifo)
            started = time.monotonic()
            with self.assertRaises(ContractError):
                _load_object(str(fifo))
            self.assertLess(time.monotonic() - started, 1.0)

    def test_provider_redirect_is_not_followed(self) -> None:
        _RedirectHandler.request_count = 0
        server = HTTPServer(("127.0.0.1", 0), _RedirectHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with self.assertRaises(HTTPError) as raised:
                with urlopen(Request(f"http://127.0.0.1:{server.server_port}/redirect"), timeout=3):
                    pass
            self.assertEqual(raised.exception.code, 302)
            self.assertEqual(_RedirectHandler.request_count, 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
