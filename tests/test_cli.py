from __future__ import annotations

import json
from pathlib import Path
import subprocess

import tempfile
import unittest

from storycraft.workflow import _model_settings_from_payload


class WorkflowSettingsTests(unittest.TestCase):
    def test_immutable_settings_supply_model_retry_configuration(self) -> None:
        settings = _model_settings_from_payload(
            {
                "provider": "ollama",
                "endpoint": "http://127.0.0.1:11434/v1",
                "model": "test-model",
                "technical_retry_limit": 3,
                "request_options": {"temperature": 0.4},
            }
        )

        self.assertEqual(settings.llm["base_url"], "http://127.0.0.1:11434/v1")
        self.assertEqual(settings.llm["model"], "test-model")
        self.assertEqual(settings.llm["request_options"], {"temperature": 0.4})
        self.assertTrue(settings.llm["v2_openai_ollama"])
        self.assertEqual(settings.retry, {"max_attempts": 3})


class CliV2AcceptanceTests(unittest.TestCase):
    def test_packaged_console_entrypoint_targets_public_cli(self) -> None:
        pyproject = (Path(__file__).parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
        self.assertIn('storycraft = "storycraft.cli:console_main"', pyproject)

    def test_workspace_lock_conflict_uses_specified_exit_code(self) -> None:
        from storycraft.cli import main
        from storycraft.workspace_lock import WorkspaceLockBusy
        from unittest.mock import patch

        with patch("storycraft.cli.cmd_status", side_effect=WorkspaceLockBusy("busy")):
            # status itself does not acquire the lock; exercise the public error boundary.
            with patch("storycraft.cli._parser") as parser:
                parser.return_value.parse_args.return_value = type(
                    "Args", (), {"command": "status", "workspace": ".", "json": True}
                )()
                self.assertEqual(main([]), 75)

    def test_private_lan_endpoint_is_accepted(self) -> None:
        from storycraft.workspace import _validate_endpoint

        for endpoint in (
            "http://10.0.0.25:11434",
            "http://172.16.10.25:11434",
            "http://192.168.1.50:11434",
            "http://[fd12:3456:789a::25]:11434",
        ):
            _validate_endpoint(endpoint)

    def test_invalid_config_uses_private_lan_contract_and_does_not_create_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            request = Path(temporary) / "request.json"
            config = Path(temporary) / "config.json"
            request.write_text(json.dumps({"title": "題", "genre": "幻想", "premise": "前提", "required_elements": [], "forbidden_elements": [], "ending_preference": "希望", "volume_count": 4, "language": "ja"}), encoding="utf-8")
            valid = {"provider": "ollama", "endpoint": "http://192.168.1.50:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1000, 1000]}
            invalid_cases = (
                ("endpoint", "http://example.com:11434"),
                ("endpoint", "https://127.0.0.1:11434"),
                ("endpoint", "http://user@127.0.0.1:11434"),
                ("endpoint", "http://127.0.0.1:11434/?query=yes"),
                ("endpoint", "http://127.0.0.1:11434/#fragment"),
                ("endpoint", "http://127.0.0.1:not-a-port"),
                ("chapter_scene_range", [0, 1]),
                ("chapter_scene_range", [2, 1]),
                ("unrecognized", True),
                ("request_options", {"think": True}),
                ("request_options", {"temperature": 2.1}),
            )
            for number, (key, value) in enumerate(invalid_cases):
                root = Path(temporary) / f"novel-{number}"
                payload = {**valid, key: value}
                config.write_text(json.dumps(payload), encoding="utf-8")
                result = subprocess.run(["uv", "run", "storycraft", "init", "--workspace", str(root), "--request", str(request), "--config", str(config), "--json"], text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(set(json.loads(result.stderr)), {"ok", "code", "message"})
                self.assertFalse(json.loads(result.stderr)["ok"])
                self.assertEqual(json.loads(result.stderr)["code"], "invalid_argument")
                self.assertIn(f"#/config/{key}", json.loads(result.stderr)["message"])
                self.assertFalse(root.exists())

    def test_init_status_and_validate_are_provider_free_json_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            request = Path(temporary) / "request.json"
            config = Path(temporary) / "config.json"
            request.write_text(json.dumps({"title": "題", "genre": "幻想", "premise": "前提", "required_elements": [], "forbidden_elements": [], "ending_preference": "希望", "volume_count": 4, "language": "ja"}), encoding="utf-8")
            config.write_text(json.dumps({"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1000, 1000]}), encoding="utf-8")
            command = ["uv", "run", "storycraft"]
            initialized = subprocess.run(command + ["init", "--workspace", str(root), "--request", str(request), "--config", str(config), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            self.assertEqual(json.loads(initialized.stdout)["status"], "created")
            status = subprocess.run(command + ["status", "--workspace", str(root), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(status.returncode, 0, status.stderr)
            payload = json.loads(status.stdout)
            # V1 spec (schema_version 3): no stop_reason in run-state
            self.assertEqual(set(payload), {"workspace_id", "status", "current_stage", "current_target", "current_selection_id", "last_error", "pending_commit"})
            self.assertIsNone(payload["last_error"])
            human = subprocess.run(command + ["status", "--workspace", str(root)], text=True, capture_output=True, check=False)
            self.assertEqual(human.returncode, 0, human.stderr)
            self.assertRegex(human.stdout, r"^workspace: .+ / status: running / stage: initial_design / target: \{\} / selection: selection-000001\n$")
            validated = subprocess.run(command + ["validate", "--workspace", str(root), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(validated.returncode, 0, validated.stderr)
            validation = json.loads(validated.stdout)
            self.assertEqual(set(validation), {"workspace_id", "status", "current_stage", "current_target", "current_selection_id", "last_error", "pending_commit", "checks"})
            self.assertTrue(all(item["passed"] for item in validation["checks"]))
            (root / "inputs" / "request-000001" / "record.json").unlink()
            invalidated = subprocess.run(command + ["validate", "--workspace", str(root), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(invalidated.returncode, 5)
            self.assertEqual(invalidated.stdout, "")
            self.assertEqual(json.loads(invalidated.stderr), {"ok": False, "code": "validation_failed", "message": "validation_failed"})
            run = subprocess.run(command + ["run", "--workspace", str(root), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(run.returncode, 4)
            self.assertEqual(run.stdout, "")
            self.assertEqual(set(json.loads(run.stderr)), {"ok", "code", "message"})

    def test_unavailable_provider_uses_machine_error_protocol_and_persists_technical_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            request = Path(temporary) / "request.json"
            config = Path(temporary) / "config.json"
            request.write_text(json.dumps({"title": "題", "genre": "幻想", "premise": "前提", "required_elements": [], "forbidden_elements": [], "ending_preference": "希望", "volume_count": 4, "language": "ja"}), encoding="utf-8")
            config.write_text(json.dumps({"provider": "ollama", "endpoint": "http://127.0.0.1:1", "model": "unavailable", "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1000, 1000]}), encoding="utf-8")
            command = ["uv", "run", "storycraft"]
            initialized = subprocess.run(command + ["init", "--workspace", str(root), "--request", str(request), "--config", str(config), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)

            result = subprocess.run(command + ["run", "--workspace", str(root), "--json"], text=True, capture_output=True, check=False)

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertTrue(result.stderr.endswith("\n"))
            self.assertEqual(json.loads(result.stderr), {"ok": False, "code": "technical_retry_exhausted", "message": "technical_retry_exhausted"})
            state = json.loads((root / "runtime" / "run-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "blocked")
            self.assertEqual(state["last_error"]["code"], "technical_retry_exhausted")

    def test_init_json_has_only_its_documented_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            request = Path(temporary) / "request.json"
            config = Path(temporary) / "config.json"
            request.write_text(json.dumps({"title": "題", "genre": "幻想", "premise": "前提", "required_elements": [], "forbidden_elements": [], "ending_preference": "希望", "volume_count": 4, "language": "ja"}), encoding="utf-8")
            config.write_text(json.dumps({"provider": "ollama", "endpoint": "http://localhost:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1000, 1000]}), encoding="utf-8")
            result = subprocess.run(["uv", "run", "storycraft", "init", "--workspace", str(root), "--request", str(request), "--config", str(config), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(json.loads(result.stdout)), {"workspace_id", "status", "current_selection_id"})
            self.assertEqual(result.stderr, "")

    def test_argument_errors_use_the_single_line_json_error_protocol(self) -> None:
        result = subprocess.run(["uv", "run", "storycraft", "init"], text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(set(json.loads(result.stderr)), {"ok", "code", "message"})
        self.assertEqual(json.loads(result.stderr)["code"], "invalid_argument")
        self.assertTrue(result.stderr.endswith("\n"))