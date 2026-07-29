from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliV2AcceptanceTests(unittest.TestCase):
    def test_invalid_config_does_not_create_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"; request = Path(temporary) / "request.json"; config = Path(temporary) / "config.json"
            request.write_text("{}", encoding="utf-8")
            config.write_text(json.dumps({"provider": "openai"}), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "storycraft.cli_v2", "init", "--workspace", str(root), "--request", str(request), "--config", str(config)], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(root.exists())

    def test_init_status_and_validate_are_provider_free_json_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            request = Path(temporary) / "request.json"
            config = Path(temporary) / "config.json"
            request.write_text(json.dumps({"title": "題", "volume_count": 1}), encoding="utf-8")
            config.write_text(json.dumps({"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1000, 1000], "max_input_chars": 50000}), encoding="utf-8")
            command = [sys.executable, "-m", "storycraft.cli_v2"]
            initialized = subprocess.run(command + ["init", "--workspace", str(root), "--request", str(request), "--config", str(config), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            self.assertEqual(json.loads(initialized.stdout)["status"], "created")
            status = subprocess.run(command + ["status", "--workspace", str(root), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(status.returncode, 0, status.stderr)
            payload = json.loads(status.stdout)
            self.assertEqual(set(payload), {"workspace_id", "status", "current_stage", "current_target", "current_selection_id", "stop_reason", "pending_commit", "runtime_lock", "run_state_path", "manifest_path"})
            validated = subprocess.run(command + ["validate", "--workspace", str(root), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertTrue(all(item["passed"] for item in json.loads(validated.stdout)["checks"]))
            run = subprocess.run(command + ["run", "--workspace", str(root), "--json"], text=True, capture_output=True, check=False)
            self.assertEqual(run.returncode, 4)
            self.assertEqual(json.loads(run.stderr)["code"], "blocked")
