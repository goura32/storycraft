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

    def test_raw_reservation_fifo_is_rejected_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw_dir = Path(temporary) / "raw"
            raw_dir.mkdir()
            name = ".probe.reserve"
            os.mkfifo(raw_dir / name)
            descriptor = os.open(raw_dir, os.O_RDONLY | os.O_DIRECTORY)
            try:
                started = time.monotonic()
                with self.assertRaises(ContractError):
                    workspace_module._raw_log_read_text(descriptor, name)
                self.assertLess(time.monotonic() - started, 1.0)
            finally:
                os.close(descriptor)

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
            self.assertGreaterEqual(len(os.listdir("/proc/self/fd")), before + 20)
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
