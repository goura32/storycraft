from __future__ import annotations

import unittest

from storycraft.artifact_record import validate_call_record, validate_candidate_record, validate_record, validate_review_record
from storycraft.series_contracts import ContractError
from storycraft.selection_snapshot import validate_selection_snapshot


NOW = "2026-07-29T00:00:00Z"


class ArtifactRecordTests(unittest.TestCase):
    def test_content_artifacts_use_the_v2_envelope_and_input_selection_id(self) -> None:
        record = {
            "schema_version": 1,
            "artifact_id": "initial-design-000001",
            "artifact_kind": "initial-design",
            "input_selection_id": "selection-000001",
            "created_at": NOW,
            "content": {"core": {}},
        }
        self.assertIs(validate_record("initial-design", "initial-design-000001", record), record)

    def test_request_is_the_only_content_artifact_that_may_bootstrap_without_selection(self) -> None:
        record = {
            "schema_version": 1,
            "artifact_id": "request-000001",
            "artifact_kind": "request",
            "input_selection_id": None,
            "created_at": NOW,
            "content": {"title": "t"},
        }
        self.assertIs(validate_record("request", "request-000001", record), record)

    def test_rejects_retired_selection_id_or_non_bootstrap_null_input(self) -> None:
        retired = {
            "schema_version": 1,
            "artifact_id": "initial-design-000001",
            "artifact_kind": "initial-design",
            "selection_id": "selection-000001",
            "created_at": NOW,
            "content": {},
        }
        with self.assertRaisesRegex(ContractError, "field構成"):
            validate_record("initial-design", "initial-design-000001", retired)
        non_bootstrap = {
            "schema_version": 1,
            "artifact_id": "initial-design-000001",
            "artifact_kind": "initial-design",
            "input_selection_id": None,
            "created_at": NOW,
            "content": {},
        }
        with self.assertRaisesRegex(ContractError, "input_selection_id"):
            validate_record("initial-design", "initial-design-000001", non_bootstrap)

    def test_rejects_id_kind_and_unknown_field_mismatch(self) -> None:
        with self.assertRaises(ContractError):
            validate_record("initial-design", "initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000002", "artifact_kind": "initial-design", "input_selection_id": "selection-000001", "created_at": NOW, "content": {}})
        with self.assertRaises(ContractError):
            validate_record("settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": "x", "extra": True})

    def test_quality_disposition_omits_notice_for_clean_acceptance_and_has_no_adoption_back_reference(self) -> None:
        clean = {
            "schema_version": 1,
            "quality_id": "quality-000001",
            "candidate_id": "candidate-000001",
            "review_record_ids": ["review-000001"],
            "revision_count": 0,
            "result": "accepted",
            "remaining_major_issues": [],
            "created_at": NOW,
        }
        self.assertIs(validate_record("quality-disposition", "quality-000001", clean), clean)

        retired_back_reference = dict(clean, adoption_record_id="adoption-000001")
        with self.assertRaisesRegex(ContractError, "field構成"):
            validate_record("quality-disposition", "quality-000001", retired_back_reference)
        invalid_clean_notice = dict(clean, notice_type="編集")
        with self.assertRaisesRegex(ContractError, "notice_type"):
            validate_record("quality-disposition", "quality-000001", invalid_clean_notice)

    def test_scene_commit_has_a_closed_record_envelope(self) -> None:
        record = {
            "schema_version": 1,
            "artifact_id": "scene-commit-v01-c01-s01-000001",
            "artifact_kind": "scene-commit",
            "input_selection_id": "selection-000001",
            "created_at": NOW,
            "content": {
                "scene_commit_id": "scene-commit-v01-c01-s01-000001",
                "scene_id": "scene-artifact-v01-c01-s01-000002",
                "scene_card_id": "scene-card-v01-c01-s01-000001",
                "scene_prose_id": "scene-v01-c01-s01-000001",
                "continuity_update_id": "continuity-v01-c01-s01-000001",
                "current_state_id": "gen-000002",
                "quality_disposition_id": "quality-000001",
                "volume_number": 1,
                "chapter_number": 1,
                "scene_number": 1,
                "created_at": NOW,
            }
        }
        self.assertIs(validate_record("scene-commit", "scene-commit-v01-c01-s01-000001", record), record)
        with self.assertRaisesRegex(ContractError, "scene_commit record"):
            validate_record("scene-commit", "scene-commit-v01-c01-s01-000001", {**record, "unknown": True})

    def test_audit_and_selection_records_reject_noncanonical_directory_ids(self) -> None:
        candidate = {"schema_version": 1, "candidate_id": "candidate-000001", "artifact_kind": "initial-design", "input_selection_id": "selection-000001", "keywords_id": None, "settings_id": "settings-000001", "payload": {}, "parent_candidate_id": None, "review_record_id": None, "call_id": "call-000001", "created_at": NOW}
        review = {"schema_version": 1, "review_id": "review-000001", "candidate_id": "candidate-000001", "response": {"schema_version": "review-response-v1", "decision": "pass", "issues": []}, "call_id": "call-000001", "created_at": NOW}
        call = {"schema_version": 1, "call_id": "call-000001", "operation": "generate", "role": "writer", "target_candidate_id": None, "input_refs": [], "technical_attempt": 1, "format_attempt": 1, "seed": 1, "endpoint": "http://127.0.0.1", "model": "test", "settings_id": "settings-000001", "request": "request", "response": "response", "transport": "success", "validation": {"result": "valid", "checks": [], "failure_code": None}}
        selection = {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"settings": "settings-000001"}, "created_at": NOW}
        for validator, identifier, record in (
            (validate_candidate_record, "candidate-1", candidate),
            (validate_review_record, "review-1", review),
            (validate_call_record, "call-1", call),
        ):
            with self.subTest(identifier=identifier), self.assertRaises(ContractError):
                validator(identifier, record)
        with self.assertRaises(ContractError):
            validate_selection_snapshot({**selection, "selection_id": "selection-1"})
