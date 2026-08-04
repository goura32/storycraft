from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest

from jsonschema import Draft202012Validator

import storycraft
from storycraft.artifact_record import validate_call_record, validate_quality_evidence
from storycraft.artifact_ids import initial_counters, reserve_counter
from storycraft.error_sanitizer import redact_secrets
from storycraft.llm import CallRecord, LLMClient
from storycraft.prompt_template import PromptTemplate
from storycraft.scene_commit_stage import SceneCommitStageService
from storycraft.series_model import OpenAIStoryModel
from storycraft.series_contracts import ContractError
from storycraft.workspace import create_workspace


ROOT = Path(__file__).resolve().parents[1]


class HardeningContractTests(unittest.TestCase):
    def test_wrapped_structured_schema_resolves_defs_at_wrapper_root(self) -> None:
        schema = OpenAIStoryModel._response_schema("generate", "series_plan")
        Draft202012Validator.check_schema(schema)
        self.assertIn("$defs", schema)
        self.assertIn("$defs", schema["properties"]["payload"])

    def test_scene_prose_generation_prompt_is_raw_text_only(self) -> None:
        rendered = OpenAIStoryModel._render(
            "generate", "scene_prose", context={"scene_card": {}}
        )
        self.assertNotIn("output_schema", rendered)
        self.assertNotIn("## 出力スキーマ", rendered)

    def test_scene_prose_revision_prompt_is_raw_text_only(self) -> None:
        rendered = OpenAIStoryModel._render(
            "revise",
            "scene_prose",
            context={"scene_card": {}},
            candidate="本文",
            critique={"issues": []},
        )
        self.assertNotIn("output_schema", rendered)
        self.assertNotIn("## 出力スキーマ", rendered)

    def test_continuity_prompts_use_active_change_contract(self) -> None:
        prompt_dir = ROOT / "templates/prompts/user/scene_continuity"
        for path in prompt_dir.glob("*.j2"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("old_value", text, path.name)
            self.assertNotIn("new_value", text, path.name)
            self.assertNotIn("operations", text, path.name)
            self.assertIn("evidence_locations", text, path.name)
            self.assertIn("op", text, path.name)

    def test_array_continuity_update_uses_index_path(self) -> None:
        old_state = {
            "story_facts": [{"fact_id": "fact-000001", "value": "開始"}],
            "character_knowledge": {},
            "reader_disclosures": [],
            "unresolved_thread_states": {"塔の試練": {"status": "open"}},
            "timeline_position": 0,
        }
        updated = SceneCommitStageService._apply_continuity(
            old_state,
            {
                "changes": [
                    {
                        "op": "set",
                        "target": "story_facts",
                        "path": "/story_facts/0/value",
                        "value": "判明",
                        "evidence_locations": ["prose:0"],
                    }
                ]
            },
        )
        self.assertEqual(updated["story_facts"][0]["value"], "判明")

    def test_quality_acceptance_rejects_critical_review_without_notice(self) -> None:
        candidate = {"text": "本文"}
        review = {
            "candidate_id": "candidate-000001",
            "response": {
                "schema_version": "review-response-v1",
                "decision": "issues",
                "issues": [
                    {
                        "severity": "critical",
                        "evidence_locations": ["prose:0"],
                        "explanation": "重大",
                    }
                ],
            }
        }
        quality = {
            "candidate_id": "candidate-000001",
            "result": "accepted",
            "remaining_major_issues": [],
        }
        with self.assertRaises(ContractError):
            validate_quality_evidence(quality, candidate, {"review-000001": review})

    def test_provider_error_failure_code_is_a_valid_call_record(self) -> None:
        record = {
            "schema_version": 1,
            "call_id": "call-000001",
            "operation": "generate",
            "role": "provider",
            "target_candidate_id": None,
            "input_refs": [],
            "technical_attempt": 1,
            "format_attempt": 1,
            "seed": 1,
            "endpoint": "http://127.0.0.1:11434/v1",
            "model": "m",
            "settings_id": "settings-000001",
            "request": "{}",
            "response": "{\"error\":\"provider\"}",
            "transport": "failure",
            "validation": {
                "result": "not_applicable",
                "checks": [],
                "failure_code": "provider_error",
            },
        }
        validate_call_record("call-000001", record)

    def test_prompt_loader_rejects_schema_path_escape(self) -> None:
        loader = PromptTemplate(ROOT / "templates/prompts")
        with self.assertRaises((ContractError, ValueError)):
            loader.load_schema_object("generate", "../../../example_request")

    def test_raw_logs_redact_secrets_and_reserve_unique_atomic_stems(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace_root = Path(temporary) / "workspace"
            raw_dir = workspace_root / "runtime" / "raw_logs"
            raw_dir.mkdir(parents=True)
            client = LLMClient.__new__(LLMClient)
            client.raw_dir = raw_dir
            client.workspace_root = workspace_root
            barrier = threading.Barrier(8)

            def save(index: int) -> None:
                barrier.wait()
                client.save_raw(
                    CallRecord(
                        kind="generate",
                        phase="initial_design",
                        ref="initial_design",
                        attempt=1,
                        seed=index + 1,
                        content=f"api_key: secret-{index}",
                    ),
                    [{"role": "user", "content": f"Authorization: Bearer token-{index}"}],
                )

            threads = [threading.Thread(target=save, args=(index,)) for index in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            json_files = sorted(raw_dir.glob("*.json"))
            markdown_files = sorted(raw_dir.glob("*.md"))
            self.assertEqual(len(json_files), 8)
            self.assertEqual(len(markdown_files), 8)
            raw_text = "\n".join(path.read_text(encoding="utf-8") for path in (*json_files, *markdown_files))
            self.assertNotIn("secret-", raw_text)
            self.assertNotIn("Bearer token-", raw_text)
            self.assertIn("[REDACTED]", raw_text)

    def test_redactor_handles_quoted_json_secret_fields(self) -> None:
        raw = '{"api_key": "plain-secret-123", "client_secret": "plain-secret-456"}'
        redacted = redact_secrets(raw)
        self.assertNotIn("plain-secret-123", redacted)
        self.assertNotIn("plain-secret-456", redacted)
        self.assertEqual(redacted.count("[REDACTED]"), 2)

    def test_raw_log_symlink_is_rejected_before_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "workspace"
            external = Path(temporary) / "external"
            external.mkdir()
            (root / "runtime").mkdir(parents=True)
            raw_dir = root / "runtime" / "raw_logs"
            raw_dir.symlink_to(external, target_is_directory=True)
            client = LLMClient.__new__(LLMClient)
            client.raw_dir = raw_dir
            client.workspace_root = root
            with self.assertRaises(ContractError):
                client.save_raw(CallRecord(kind="generate", phase="plan", ref="plan", attempt=1, seed=1, content="{}"), [])
            self.assertEqual(list(external.iterdir()), [])

    def test_workspace_parent_symlink_is_rejected(self) -> None:
        settings = {
            "provider": "ollama",
            "endpoint": "http://127.0.0.1:11434",
            "model": "m",
            "technical_retry_limit": 1,
            "quality_revision_limit": 1,
            "invalid_response_limit": 1,
            "chapter_per_volume_range": [1, 1],
            "chapter_scene_range": [1, 1],
            "scene_text_char_range": [1, 20],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            external = root / "external"
            external.mkdir()
            parent = root / "parent-link"
            parent.symlink_to(external, target_is_directory=True)
            with self.assertRaises(ContractError):
                create_workspace(
                    parent / "workspace",
                    workspace_id="ws-000001",
                    request=None,
                    keywords={"keywords": ["test"], "language": "ja"},
                    settings=settings,
                    created_at="2026-08-04T00:00:00Z",
                )
            self.assertEqual(list(external.iterdir()), [])

    def test_counter_reservation_is_safe_for_concurrent_threads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "runtime").mkdir()
            (root / "runtime/counters.json").write_text(
                json.dumps(initial_counters()) + "\n", encoding="utf-8"
            )
            values: list[int] = []
            lock = threading.Lock()

            def reserve() -> None:
                value = reserve_counter(root, "next_call")
                with lock:
                    values.append(value)

            threads = [threading.Thread(target=reserve) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(sorted(values), list(range(1, 9)))

    def test_settings_legacy_public_api_is_not_exported(self) -> None:
        self.assertNotIn("Settings", getattr(storycraft, "__all__", ()))
        self.assertFalse(hasattr(storycraft, "Settings"))


if __name__ == "__main__":
    unittest.main()
