from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from storycraft.artifact_record import validate_quality_evidence
from storycraft.continuity_paths import path_tokens
from storycraft.error_sanitizer import redact_secrets, redact_value
from storycraft.llm import CallRecord, LLMClient
from storycraft.series_contracts import ContractError
from storycraft.workspace import create_workspace, validate_workspace
from storycraft.workflow import _block
from storycraft.run_state import RunStateStore
from storycraft.selection_authority import resolve_selection
from storycraft.selection_snapshot import SelectionSnapshotStore
from tests.test_volume_publication_service import workspace as publication_workspace, write_json
from storycraft.commit_recovery import recover_pending_commit
import storycraft.workspace as workspace_module


class DeferredAuditRegressionTests(unittest.TestCase):
    def test_quality_notice_must_list_every_critical_review_issue(self) -> None:
        candidate = {"text": "本文"}
        reviews = {
            "review-000001": {
                "candidate_id": "candidate-000001",
                "response": {
                    "schema_version": "review-response-v1",
                    "decision": "issues",
                    "issues": [
                        {"severity": "critical", "evidence_locations": ["prose:0"], "explanation": "重大A"},
                        {"severity": "critical", "evidence_locations": ["prose:0"], "explanation": "重大B"},
                    ],
                },
            },
        }
        quality = {
            "candidate_id": "candidate-000001",
            "result": "accepted_with_notice",
            "remaining_major_issues": [
                {"code": "quality.critical", "message": "重大A", "evidence_locations": ["prose:0"]},
            ],
        }
        with self.assertRaises(ContractError):
            validate_quality_evidence(quality, candidate, reviews)

    def test_publication_selection_rejects_quality_candidate_payload_swap(self) -> None:
        temporary, root = publication_workspace()
        self.addCleanup(temporary.cleanup)
        quality_path = root / "quality" / "quality-000011" / "record.json"
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        quality["candidate_id"] = "candidate-000021"
        quality["review_record_ids"] = ["review-000021"]
        write_json(quality_path, quality)
        selection_id = RunStateStore(root).load()["current_selection_id"]
        snapshot = SelectionSnapshotStore(root).load(selection_id)
        with self.assertRaises(ContractError):
            resolve_selection(root, snapshot)

    def test_direct_publication_recovery_rejects_quality_candidate_payload_swap(self) -> None:
        temporary, root = publication_workspace()
        self.addCleanup(temporary.cleanup)
        with patch("storycraft.volume_publication_stage.recover_pending_commit", side_effect=RuntimeError("staged")):
            with self.assertRaisesRegex(RuntimeError, "staged"):
                from storycraft.volume_publication_stage import VolumePublicationStageService
                VolumePublicationStageService(root).run(updated_at="2026-08-01T00:00:00Z")
        quality_path = root / "quality" / "quality-000011" / "record.json"
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        quality["candidate_id"] = "candidate-000021"
        quality["review_record_ids"] = ["review-000021"]
        write_json(quality_path, quality)
        with self.assertRaises(ContractError):
            recover_pending_commit(root)
        self.assertFalse((root / "publications" / "volume-pub-v01-000001").exists())

    def test_continuity_accepts_json_pointer_only(self) -> None:
        with self.assertRaises(ContractError):
            path_tokens("story_facts", "$.story_facts/0/value")
        with self.assertRaises(ContractError):
            path_tokens("story_facts", "$.story_facts.0.value")
        self.assertEqual(path_tokens("story_facts", "/story_facts/0/value"), ["story_facts", "0", "value"])

    def test_redaction_covers_unquoted_password_forms(self) -> None:
        for value in (
            "password=TOPSECRET",
            "passwd: TOPSECRET",
            "passphrase=TOPSECRET",
            "Password: TOPSECRET",
        ):
            redacted = redact_secrets(value)
            self.assertNotIn("TOPSECRET", redacted)
            self.assertIn("[REDACTED]", redacted)

    def test_redaction_covers_escaped_nested_json_secret_forms(self) -> None:
        nested = json.dumps({"api_key": "ESCAPED-SENTINEL"}, separators=(",", ":"))
        for value in (nested, json.dumps({"payload": nested}, separators=(",", ":"))):
            redacted = redact_secrets(value)
            self.assertNotIn("ESCAPED-SENTINEL", redacted)
            self.assertIn("[REDACTED]", redacted)
        value = redact_value({"payload": nested})
        self.assertNotIn("ESCAPED-SENTINEL", json.dumps(value, ensure_ascii=False))

    def test_raw_log_pair_rolls_back_when_second_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace_root = Path(temporary) / "workspace"
            raw_dir = workspace_root / "runtime" / "raw_logs"
            raw_dir.mkdir(parents=True)
            client = LLMClient.__new__(LLMClient)
            client.raw_dir = raw_dir
            client.workspace_root = workspace_root
            record = CallRecord(
                kind="generate",
                phase="initial_design",
                ref="initial_design",
                attempt=1,
                seed=1,
                started_at=0.0,
                finished_at=1.0,
                content="本文",
            )
            original_writer = LLMClient._write_raw_file
            call_count = 0

            def write_pair_file(path: Path, content: str) -> tuple[int, int]:
                nonlocal call_count
                if call_count == 1:
                    raise OSError("markdown write failed")
                call_count += 1
                return original_writer(path, content)

            with patch.object(LLMClient, "_write_raw_file", side_effect=write_pair_file):
                with self.assertRaises(OSError):
                    client.save_raw(record, [])
            self.assertEqual(list(raw_dir.glob("*.json")), [])
            self.assertEqual(list(raw_dir.glob("*.md")), [])
            self.assertEqual(list(raw_dir.glob(".*.reserve")), [])

    def test_workspace_validation_rejects_fixed_runtime_symlinks(self) -> None:
        settings = {
            "provider": "ollama",
            "endpoint": "http://127.0.0.1:11434",
            "model": "test",
            "technical_retry_limit": 1,
            "quality_revision_limit": 1,
            "invalid_response_limit": 1,
            "chapter_per_volume_range": [1, 1],
            "chapter_scene_range": [1, 1],
            "scene_text_char_range": [1000, 1000],
        }
        request = {
            "title": "題名",
            "genre": ["幻想"],
            "premise": "前提",
            "required_elements": [],
            "avoid": [],
            "ending_preference": "希望",
            "volume_count": 4,
            "language": "ja",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            create_workspace(root, workspace_id="ws-test", request=request, settings=settings, created_at="2026-07-28T00:00:00Z")
            original_files = {
                relative: (root / relative).read_bytes()
                for relative in ("runtime/counters.json", "runtime/lock", "runtime/counters.lock", "runtime/run-state.json")
            }
            for relative in ("runtime/counters.json", "runtime/lock", "runtime/counters.lock", "runtime/run-state.json", "runtime/raw_logs"):
                path = root / relative
                if path.is_dir():
                    path.rmdir()
                else:
                    path.unlink()
                target = Path(temporary) / ("external-" + relative.replace("/", "-"))
                if relative.endswith("raw_logs"):
                    target.mkdir()
                else:
                    target.write_text("external", encoding="utf-8")
                path.symlink_to(target, target_is_directory=relative.endswith("raw_logs"))
                with self.assertRaises(ContractError):
                    validate_workspace(root)
                path.unlink()
                if target.is_dir():
                    target.rmdir()
                else:
                    target.unlink()
                if relative == "runtime/raw_logs":
                    path.mkdir()
                else:
                    path.write_bytes(original_files[relative])

    def test_create_workspace_parent_swap_after_directory_fd_open_fails_closed(self) -> None:
        settings = {
            "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test",
            "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 1,
            "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100],
        }
        request = {
            "title": "題名", "genre": ["幻想"], "premise": "前提", "required_elements": [], "avoid": [],
            "ending_preference": "希望", "volume_count": 4, "language": "ja",
        }
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            parent = base / "parent"
            parent.mkdir()
            outside = base / "outside"
            outside.mkdir()
            backup = base / "parent-original"
            staging_name: str | None = None
            original_creator = __import__("storycraft.workspace", fromlist=["create_unique_directory_at"]).create_unique_directory_at

            def swap_parent(directory_fd: int, prefix: str) -> str:
                nonlocal staging_name
                created = original_creator(directory_fd, prefix)
                staging_name = created
                parent.rename(backup)
                parent.symlink_to(outside, target_is_directory=True)
                return created

            with patch("storycraft.workspace.create_unique_directory_at", side_effect=swap_parent):
                with self.assertRaises(ContractError):
                    create_workspace(
                        parent / "workspace", workspace_id="ws-test", request=request,
                        settings=settings, created_at="2026-07-28T00:00:00Z",
                    )
            self.assertFalse((outside / "workspace").exists())
            if parent.is_symlink():
                parent.unlink()
            elif parent.exists():
                shutil.rmtree(parent)
            if backup.exists():
                shutil.rmtree(backup)

    def test_validate_workspace_raw_logs_swap_after_fd_open_fails_closed(self) -> None:
        settings = {
            "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test",
            "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 1,
            "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100],
        }
        request = {
            "title": "題名", "genre": ["幻想"], "premise": "前提", "required_elements": [], "avoid": [],
            "ending_preference": "希望", "volume_count": 4, "language": "ja",
        }
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "workspace"
            create_workspace(root, workspace_id="ws-test", request=request, settings=settings, created_at="2026-07-28T00:00:00Z")
            raw_dir = root / "runtime/raw_logs"
            backup = base / "raw-logs-original"
            outside = base / "outside"
            outside.mkdir()
            original_check = workspace_module._assert_directory_fd_identity
            checks = 0

            def swap_raw_logs(path: Path, descriptor: int) -> None:
                nonlocal checks
                original_check(path, descriptor)
                if path == raw_dir:
                    checks += 1
                    if checks == 1:
                        raw_dir.rename(backup)
                        raw_dir.symlink_to(outside, target_is_directory=True)

            with patch.object(workspace_module, "_assert_directory_fd_identity", side_effect=swap_raw_logs):
                with self.assertRaises(ContractError):
                    validate_workspace(root)
            raw_dir.unlink()
            backup.rename(raw_dir)


    def test_workflow_block_sanitizes_persisted_error_message(self) -> None:
        state = {
            "schema_version": 3,
            "workspace_id": "ws-test",
            "status": "running",
            "last_error": None,
            "current_stage": "initial_design",
            "current_target": {},
            "current_selection_id": "selection-000001",
            "pending_commit": None,
            "published_volumes": [],
            "created_at": "2026-07-28T00:00:00Z",
            "updated_at": "2026-07-28T00:00:00Z",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            RunStateStore(root).save(state)
            _block(RunStateStore(root), state, "internal_error", "Authorization: Bearer TOPSECRET")
            saved = RunStateStore(root).load()
            self.assertNotIn("TOPSECRET", saved["last_error"]["message"])
            self.assertIn("[REDACTED]", saved["last_error"]["message"])

    def test_workspace_rejects_an_incomplete_raw_log_pair(self) -> None:
        settings = {
            "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test",
            "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 1,
            "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100],
        }
        request = {
            "title": "題名", "genre": ["幻想"], "premise": "前提", "required_elements": [], "avoid": [],
            "ending_preference": "希望", "volume_count": 4, "language": "ja",
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            create_workspace(root, workspace_id="ws-test", request=request, settings=settings, created_at="2026-07-28T00:00:00Z")
            (root / "runtime/raw_logs/incomplete.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ContractError):
                validate_workspace(root)


if __name__ == "__main__":
    unittest.main()
