from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.artifact_ids import initial_counters
from storycraft.candidate_stage import CandidateStageRunner, CandidateStageSpec
from storycraft.run_state import RunStateStore
from storycraft.selection_snapshot import SelectionSnapshotStore

NOW = "2026-07-31T00:00:00Z"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def workspace(root: Path, *, stage: str = "series_plan") -> None:
    for relative in ("inputs", "quality", "candidates", "reviews", "runtime/settings", "runtime/selections", "runtime/staging", "runtime/calls", "runtime/adoptions", "design/series-plans", "design/initial-designs", "design/volume-plans", "design/chapter-plans", "design/scene-plans", "design/scene-cards"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    write_json(root / "runtime/counters.json", initial_counters())
    write_json(root / "inputs/request-000001/record.json", {
        "schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request",
        "input_selection_id": None, "created_at": NOW,
        "content": {"title": "依頼", "genre": "fantasy", "premise": "試験", "required_elements": ["塔"], "forbidden_elements": ["宇宙"], "ending_preference": "希望", "volume_count": 4, "language": "ja"},
    })
    write_json(root / "runtime/settings/settings-000001/record.json", {
        "schema_version": 1, "settings_id": "settings-000001",
        "payload": {"endpoint": "http://127.0.0.1:11434", "model": "fake", "quality_revision_limit": 1, "invalid_response_limit": 5}, "created_at": NOW,
    })
    # Valid initial-design content per closed schema
    initial_design_content = {
        "core": "英雄の旅",
        "cast": [{"name": "主人公", "role": "英雄"}],
        "world": "剣と魔法の世界",
        "knowledge_model": {},
        "unresolved_threads": [],
        "ending_conditions": ["塔を登頂する"]
    }
    write_json(root / "design/initial-designs/initial-design-000001/record.json", {
        "schema_version": 1, "artifact_id": "initial-design-000001", "artifact_kind": "initial-design",
        "input_selection_id": "selection-000001", "created_at": NOW,
        "content": initial_design_content,
    })
    # Valid generation content per closed schema
    generation_content = {
        "story_facts": [],
        "character_states": {},
        "world_states": {},
        "open_threads": [],
        "last_scene_summary": ""
    }
    write_json(root / "design/scene-cards/scene-card-v01-c01-s01/record.json", {
        "schema_version": 1, "artifact_id": "scene-card-v01-c01-s01", "artifact_kind": "scene-card",
        "input_selection_id": "selection-000001", "created_at": NOW,
        "content": generation_content,
    })
    SelectionSnapshotStore(root).create(input_selection_id=None, created_at=NOW, slots={"request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001", "current_state": "scene-card-v01-c01-s01"})
    target = {} if stage == "series_plan" else {"volume_number": 1, "chapter_number": 1, "scene_number": 1}
    RunStateStore(root).save({"schema_version": 3, "workspace_id": "ws-000001", "status": "running", "last_error": None, "current_stage": stage, "current_target": target, "current_selection_id": "selection-000001", "pending_commit": None, "published_volumes": [], "created_at": NOW, "updated_at": NOW})


class FakeModel:
    def __init__(self, root: Path, reviews: list[dict[str, object]]) -> None:
        self.root = root
        self.reviews = iter(reviews)
        self.calls: list[str] = []
        self.last_call_id: str | None = None

    def _record_physical_call(self, operation: str) -> None:
        call_id = f"call-{len(list((self.root / 'runtime/calls').iterdir())) + 1:06d}"
        write_json(self.root / "runtime/calls" / call_id / "record.json", {
            "schema_version": 1, "call_id": call_id, "operation": operation,
        })
        self.last_call_id = call_id

    def generate(self, stage: str, context: dict[str, object]) -> dict[str, object]:
        self.calls.append("generate")
        self._record_physical_call("generate")
        return {"schema_version": "candidate-response-v1", "artifact_kind": "series-plan", "payload": {"volumes": [1, 2, 3, 4], "thread_allocations": []}}

    def review(self, stage: str, context: dict[str, object], candidate: dict[str, object]) -> dict[str, object]:
        self.calls.append("review")
        self._record_physical_call("review")
        return next(self.reviews)

    def revise(self, stage: str, context: dict[str, object], candidate: dict[str, object], review: dict[str, object]) -> dict[str, object]:
        self.calls.append("revise")
        self._record_physical_call("revise")
        return {"schema_version": "candidate-response-v1", "artifact_kind": "series-plan", "payload": {"volumes": [1, 2, 3, 4], "thread_allocations": []}}


def spec() -> CandidateStageSpec:
    return CandidateStageSpec(stage="series_plan", artifact_kind="series-plan", next_stage="volume_plan", next_target={"volume_number": 1}, content_id_factory=lambda _root, _target: "series-plan-000001")


class CandidateStageTests(unittest.TestCase):
    def test_reserves_audit_ids_from_runtime_counters_not_existing_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace(root)
            for directory, identifier in (("candidates", "candidate-999999"), ("reviews", "review-999999"), ("quality", "quality-999999"), ("runtime/adoptions", "adoption-999999")):
                write_json(root / directory / identifier / "record.json", {"ignored": True})
            model = FakeModel(root, [{"schema_version": "review-response-v1", "decision": "pass", "issues": []}])
            with patch("storycraft.candidate_stage.recover_pending_commit") as mock_recover:
                mock_recover.return_value = {
                    "schema_version": 3,
                    "workspace_id": "ws-000001",
                    "status": "running",
                    "last_error": None,
                    "current_stage": "volume_plan",
                    "current_target": {"volume_number": 1},
                    "current_selection_id": "selection-000002",
                    "pending_commit": None,
                    "published_volumes": [],
                    "created_at": NOW,
                    "updated_at": NOW,
                }
                CandidateStageRunner(root, spec()).run(model, context={}, updated_at=NOW)

            self.assertTrue((root / "candidates/candidate-000001/record.json").is_file())
            self.assertTrue((root / "reviews/review-000001/record.json").is_file())
            self.assertTrue((root / "quality/quality-000001/record.json").is_file())

    def test_clean_review_records_all_immutable_records_and_recovers_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace(root)
            model = FakeModel(root, [{"schema_version": "review-response-v1", "decision": "pass", "issues": []}])
            with patch("storycraft.candidate_stage.recover_pending_commit") as mock_recover:
                mock_recover.return_value = {
                    "schema_version": 3,
                    "workspace_id": "ws-000001",
                    "status": "running",
                    "last_error": None,
                    "current_stage": "volume_plan",
                    "current_target": {"volume_number": 1},
                    "current_selection_id": "selection-000002",
                    "pending_commit": None,
                    "published_volumes": [],
                    "created_at": NOW,
                    "updated_at": NOW,
                }
                result = CandidateStageRunner(root, spec()).run(model, context={"request": "current"}, updated_at=NOW)

            self.assertEqual(model.calls, ["generate", "review"])
            self.assertEqual(result["current_stage"], "volume_plan")
            self.assertEqual(result["current_target"], {"volume_number": 1})
            self.assertIsNone(result["pending_commit"])
            self.assertNotIn("active_candidate", result)
            self.assertTrue((root / "candidates/candidate-000001/record.json").is_file())
            self.assertTrue((root / "reviews/review-000001/record.json").is_file())
            quality = json.loads((root / "quality/quality-000001/record.json").read_text(encoding="utf-8"))
            self.assertEqual(quality["result"], "accepted")
            self.assertEqual(quality["remaining_major_issues"], [])
            self.assertTrue((root / "runtime/calls/call-000001/record.json").is_file())

    def test_critical_issue_at_quality_cap_adopts_last_valid_candidate_with_notice(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace(root)
            critical = {"schema_version": "review-response-v1", "decision": "issues", "issues": [{"severity": "critical", "evidence_locations": ["$.title"], "explanation": "直す"}]}
            model = FakeModel(root, [critical, critical])
            with patch("storycraft.candidate_stage.recover_pending_commit") as mock_recover:
                mock_recover.return_value = {
                    "schema_version": 3,
                    "workspace_id": "ws-000001",
                    "status": "running",
                    "last_error": None,
                    "current_stage": "volume_plan",
                    "current_target": {"volume_number": 1},
                    "current_selection_id": "selection-000002",
                    "pending_commit": None,
                    "published_volumes": [],
                    "created_at": NOW,
                    "updated_at": NOW,
                }
                result = CandidateStageRunner(root, spec()).run(model, context={}, updated_at=NOW)

            self.assertEqual(model.calls, ["generate", "review", "revise", "review"])
            quality = json.loads((root / "quality/quality-000001/record.json").read_text(encoding="utf-8"))
            self.assertEqual(quality["result"], "accepted_with_notice")
            self.assertEqual(quality["notice_type"], "編集")
            self.assertEqual(result["current_stage"], "volume_plan")

    def test_provider_format_errors_use_invalid_response_retry_limit_not_transport_retry(self) -> None:
        from storycraft.candidate_stage import InvalidResponseLimitError
        from storycraft.ollama import OllamaResponseFormatError

        class MalformedModel:
            def __init__(self) -> None:
                self.calls = 0

            def generate(self, stage: str, context: dict[str, object]) -> dict[str, object]:
                self.calls += 1
                raise OllamaResponseFormatError("malformed provider response")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace(root)
            settings_path = root / "runtime/settings/settings-000001/record.json"
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            settings["payload"]["invalid_response_limit"] = 2
            write_json(settings_path, settings)
            model = MalformedModel()

            with self.assertRaises(InvalidResponseLimitError):
                CandidateStageRunner(root, spec()).run(model, context={}, updated_at=NOW)

            self.assertEqual(model.calls, 2)

    def test_replacing_scene_prose_removes_stale_continuity_slots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace(root, stage="scene_prose")
            runner = CandidateStageRunner(root, CandidateStageSpec(stage="scene_prose", artifact_kind="scene-prose", next_stage="scene_continuity", next_target={"volume_number": 1, "chapter_number": 1, "scene_number": 1}, content_id_factory=lambda _root, _target: "scene-prose-v01-c01-s01-000001"))
            slots = {"request": "request-000001", "settings": "settings-000001", "scene_prose.v01.c01.s01": "scene-prose-v01-c01-s01-000000", "continuity_update.v01.c01.s01": "continuity-v01-c01-s01-000001", "continuity_adoption.v01.c01.s01": "adoption-000099"}
            self.assertEqual(runner.updated_slots(slots, "scene-prose-v01-c01-s01-000001", "adoption-000001", "quality-000001"), {"request": "request-000001", "settings": "settings-000001", "scene_prose.v01.c01.s01": "scene-prose-v01-c01-s01-000001", "scene_prose_adoption.v01.c01.s01": "adoption-000001", "scene_prose_disposition.v01.c01.s01": "quality-000001"})

    def test_zero_quality_limit_keeps_revising_until_a_clean_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace(root)
            settings_path = root / "runtime/settings/settings-000001/record.json"
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            settings["payload"]["quality_revision_limit"] = 0
            write_json(settings_path, settings)
            critical = {"schema_version": "review-response-v1", "decision": "issues", "issues": [{"severity": "critical", "evidence_locations": ["$.title"], "explanation": "直す"}]}
            clean = {"schema_version": "review-response-v1", "decision": "pass", "issues": []}
            model = FakeModel(root, [critical, critical, clean])
            with patch("storycraft.candidate_stage.recover_pending_commit") as mock_recover:
                mock_recover.return_value = {
                    "schema_version": 3,
                    "workspace_id": "ws-000001",
                    "status": "running",
                    "last_error": None,
                    "current_stage": "volume_plan",
                    "current_target": {"volume_number": 1},
                    "current_selection_id": "selection-000002",
                    "pending_commit": None,
                    "published_volumes": [],
                    "created_at": NOW,
                    "updated_at": NOW,
                }
                CandidateStageRunner(root, spec()).run(model, context={}, updated_at=NOW)

            self.assertEqual(model.calls, ["generate", "review", "revise", "review", "revise", "review"])
