from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from storycraft.ollama import ContractError, OllamaResponseFormatError, generate, normalized_v1_base_url
from storycraft.artifact_ids import initial_counters


class Handler(BaseHTTPRequestHandler):
    capability = {"id": "m", "context_length": 8192}
    completion = {"choices": [{"message": {"content": '{"schema_version": 1}'}}]}
    paths: list[str] = []
    bodies: list[dict] = []

    def do_GET(self):
        type(self).paths.append(self.path)
        data = json.dumps(type(self).capability).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        type(self).paths.append(self.path)
        type(self).bodies.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        data = json.dumps(type(self).completion).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class OllamaTests(unittest.TestCase):
    def setUp(self) -> None:
        Handler.capability = {"id": "m", "context_length": 8192}
        Handler.completion = {"choices": [{"message": {"content": '{"schema_version": 1}'}}]}
        Handler.paths = []
        Handler.bodies = []
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/v1/"
        self._temporary = tempfile.TemporaryDirectory()
        self.workspace_root = Path(self._temporary.name) / "workspace"
        self.workspace_root.mkdir()
        runtime = self.workspace_root / "runtime"
        runtime.mkdir()
        (runtime / "counters.json").write_text(json.dumps(initial_counters()) + "\n", encoding="utf-8")
        self.records = runtime / "calls"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._temporary.cleanup()

    @staticmethod
    def _canonical_records(tmp: str) -> tuple[Path, Path]:
        workspace = Path(tmp) / "workspace"
        runtime = workspace / "runtime"
        runtime.mkdir(parents=True)
        (runtime / "counters.json").write_text(json.dumps(initial_counters()) + "\n", encoding="utf-8")
        return runtime / "calls", workspace

    def test_normalized_v1_base_url_collapses_duplicate_suffix(self) -> None:
        self.assertEqual(
            normalized_v1_base_url("http://127.0.0.1:11434/v1/v1/"),
            "http://127.0.0.1:11434/v1",
        )

    def test_rejects_unrecorded_provider_call_before_http(self):
        with self.assertRaisesRegex(ContractError, "call record"):
            generate(
                self.endpoint,
                "m",
                "p",
                {"type": "object"},
                workspace_root=self.workspace_root,
                settings_id="settings-000001",
            )
        self.assertEqual(Handler.paths, [])

    def test_rejects_canonical_call_records_without_counter_before_http(self):
        broken_root = Path(self._temporary.name) / "broken"
        (broken_root / "runtime/calls").mkdir(parents=True)
        with self.assertRaisesRegex(ContractError, "counters"):
            generate(
                self.endpoint,
                "m",
                "p",
                {"type": "object"},
                call_record_dir=broken_root / "runtime/calls",
                workspace_root=broken_root,
                settings_id="settings-000001",
            )
        self.assertEqual(Handler.paths, [])

    def test_posts_non_streaming_openai_request_from_normalized_v1_base(self):
        self.assertEqual(
            generate(self.endpoint, "m", "p", {"type": "object"}, request_options={"temperature": 0.2, "top_k": 20}, call_record_dir=self.records, workspace_root=self.workspace_root, settings_id="settings-000001"),
            {"schema_version": 1},
        )
        self.assertEqual(Handler.paths, ["/v1/models/m", "/v1/chat/completions"])
        body = Handler.bodies[0]
        self.assertEqual(body["messages"], [{"role": "user", "content": "p"}])
        self.assertEqual(body["response_format"]["json_schema"]["schema"], {"type": "object"})
        self.assertTrue(body["think"])
        self.assertFalse(body["stream"])
        self.assertEqual(body["options"], {"num_ctx": 8192, "seed": 1, "temperature": 0.2, "top_k": 20})

    def test_rejects_capability_with_wrong_model_id(self):
        Handler.capability = {"id": "other", "context_length": 8192}
        with self.assertRaisesRegex(ContractError, "モデル情報"):
            generate(self.endpoint, "m", "p", {"type": "object"}, call_record_dir=self.records, workspace_root=self.workspace_root, settings_id="settings-000001")
        self.assertEqual(Handler.paths, ["/v1/models/m"])

    def test_rejects_capability_with_unexpected_fields(self):
        Handler.capability = {"id": "m", "context_length": 8192, "unexpected": True}
        with self.assertRaises(OllamaResponseFormatError):
            generate(self.endpoint, "m", "p", {"type": "object"}, call_record_dir=self.records, workspace_root=self.workspace_root, settings_id="settings-000001")

    def test_rejects_completion_object_that_violates_the_requested_schema(self):
        Handler.completion = {"choices": [{"message": {"content": '{"unexpected":true}'}}]}
        schema = {
            "type": "object", "additionalProperties": False,
            "required": ["value"], "properties": {"value": {"type": "string"}},
        }
        with tempfile.TemporaryDirectory() as tmp:
            records, workspace = self._canonical_records(tmp)
            with self.assertRaises(OllamaResponseFormatError):
                generate(self.endpoint, "m", "p", schema, call_record_dir=records, workspace_root=workspace, settings_id="settings-000001")
            completion = next(
                json.loads(path.read_text(encoding="utf-8"))
                for path in records.glob("*/record.json")
                if json.loads(path.read_text(encoding="utf-8"))["operation"] == "generate"
            )
        self.assertEqual(completion["validation"]["failure_code"], "schema_invalid")

    def test_writes_immutable_records_for_capability_and_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            records, workspace = self._canonical_records(tmp)
            generate(self.endpoint, "m", "p", {"type": "object"}, call_record_dir=records, workspace_root=workspace, settings_id="settings-000001")
            saved = sorted(records.glob("*/record.json"))
            self.assertEqual(len(saved), 2)
            payloads = [json.loads(path.read_text(encoding="utf-8")) for path in saved]
        payloads = {payload["operation"]: payload for payload in payloads}
        self.assertEqual(set(payloads), {"model_capability", "generate"})
        self.assertEqual([payloads[name]["transport"] for name in ("model_capability", "generate")], ["success", "success"])
        self.assertEqual(payloads["model_capability"]["request"], None)
        self.assertEqual(payloads["model_capability"]["response"], json.dumps({"id": "m", "context_length": 8192}, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        self.assertEqual(payloads["model_capability"]["validation"], {"result": "valid", "checks": ["id", "context_length"], "failure_code": None})

    def test_writes_failed_capability_attempt_before_raising(self):
        Handler.capability = {"id": "other", "context_length": 8192}
        with tempfile.TemporaryDirectory() as tmp:
            records, workspace = self._canonical_records(tmp)
            with self.assertRaises(OllamaResponseFormatError):
                generate(self.endpoint, "m", "p", {"type": "object"}, call_record_dir=records, workspace_root=workspace, settings_id="settings-000001")
            saved = list(records.glob("*/record.json"))
            self.assertEqual(len(saved), 1)
            payload = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["operation"], "model_capability")
        self.assertEqual(payload["transport"], "success")
        self.assertEqual(payload["validation"]["result"], "invalid")
        self.assertEqual(payload["validation"]["failure_code"], "schema_invalid")

    def test_malformed_completion_is_a_format_error_with_a_successful_invalid_audit_record(self):
        Handler.completion = {"choices": [{"message": {"content": "not-json"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            records, workspace = self._canonical_records(tmp)
            with self.assertRaises(OllamaResponseFormatError):
                generate(self.endpoint, "m", "p", {"type": "object"}, call_record_dir=records, workspace_root=workspace, settings_id="settings-000001")
            payloads = [json.loads(path.read_text(encoding="utf-8")) for path in records.glob("*/record.json")]
        completion = next(record for record in payloads if record["operation"] == "generate")
        self.assertEqual(completion["transport"], "success")
        self.assertEqual(completion["validation"]["result"], "invalid")
        self.assertEqual(completion["validation"]["failure_code"], "json_parse")

    def test_rejects_call_records_without_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            records = Path(tmp) / "calls"
            with self.assertRaisesRegex(ContractError, "workspace_root"):
                generate(
                    self.endpoint, "m", "p", {"type": "object"},
                    call_record_dir=records, settings_id="settings-000001",
                )
            self.assertFalse(records.exists())

    def test_rejects_noncanonical_call_record_directory_before_http(self) -> None:
        other = self.workspace_root / "runtime/other-calls"
        with self.assertRaisesRegex(ContractError, "runtime/calls"):
            generate(
                self.endpoint,
                "m",
                "p",
                {"type": "object"},
                call_record_dir=other,
                workspace_root=self.workspace_root,
                settings_id="settings-000001",
            )
        self.assertFalse(other.exists())
        self.assertEqual(Handler.paths, [])

    def test_rejects_reused_physical_seed_before_http(self) -> None:
        generate(
            self.endpoint,
            "m",
            "p",
            {"type": "object"},
            call_record_dir=self.records,
            workspace_root=self.workspace_root,
            settings_id="settings-000001",
            seed=1,
        )
        Handler.paths = []
        with self.assertRaisesRegex(ContractError, "seed"):
            generate(
                self.endpoint,
                "m",
                "p",
                {"type": "object"},
                call_record_dir=self.records,
                workspace_root=self.workspace_root,
                settings_id="settings-000001",
                seed=1,
            )
        self.assertEqual(Handler.paths, [])

    def test_rejects_call_records_outside_workspace_root_before_http(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            records = Path(tmp) / "outside" / "calls"
            with self.assertRaisesRegex(ContractError, "workspace root外"):
                generate(
                    self.endpoint, "m", "p", {"type": "object"},
                    call_record_dir=records, workspace_root=workspace,
                    settings_id="settings-000001",
                )
            self.assertFalse(records.exists())
            self.assertEqual(Handler.paths, [])

    def test_requires_settings_id_when_persisting_call_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            records = Path(tmp) / "calls"
            with self.assertRaisesRegex(ContractError, "settings_id"):
                generate(self.endpoint, "m", "p", {"type": "object"}, call_record_dir=records, workspace_root=Path(tmp))
            self.assertFalse(records.exists())


if __name__ == "__main__":
    unittest.main()
