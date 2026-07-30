"""正本 docs/design/state-and-transitions.md に基づく run-state v3 契約。"""
from __future__ import annotations

import copy
import unittest

from storycraft.run_state import validate_run_state
from storycraft.series_contracts import ContractError


BASE_STATE = {
    "schema_version": 3,
    "workspace_id": "ws-000001",
    "status": "running",
    "last_error": None,
    "current_stage": "scene_plan",
    "current_target": {
        "volume_number": 1,
        "chapter_number": 1,
        "scene_number": 2,
    },
    "current_selection_id": "selection-000001",
    "active_candidate": None,
    "active_scene_id": None,
    "pending_commit": None,
    "published_volumes": [],
    "created_at": "2026-07-28T00:00:00Z",
    "updated_at": "2026-07-28T00:00:00Z",
}


class RunStateV2Tests(unittest.TestCase):
    def test_running_state_with_selection_and_scene_target_is_valid(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        self.assertIs(validate_run_state(state), state)

    def test_request_intake_allows_no_selection_before_request_adoption(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state.update(current_stage="request_intake", current_selection_id=None, current_target={})
        self.assertIs(validate_run_state(state), state)

    def test_manifest_rejects_absolute_or_parent_paths(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state["pending_commit"] = {"kind": "volume_publication", "staging_path": "runtime/staging/pub", "input_selection_id": "selection-000001", "output_selection_id": None, "state_update": {}, "targets": [{"artifact_id": "volume-pub-v01-000001", "artifact_kind": "volume_publication", "staging_path": "../outside", "final_path": "/tmp/outside", "sha256": "0" * 64, "status": "pending"}]}
        with self.assertRaises(ContractError):
            validate_run_state(state)

    def test_completed_state_has_no_current_work(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state.update(
            status="completed",
            current_stage=None,
            current_target=None,
            current_selection_id="selection-000010",
            published_volumes=[
                {
                    "volume_number": 1,
                    "publication_id": "volume-pub-v01-000001",
                }
            ],
        )
        self.assertIs(validate_run_state(state), state)

    def test_completed_state_rejects_current_stage(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state["status"] = "completed"
        with self.assertRaisesRegex(ContractError, "completed"):
            validate_run_state(state)

    def test_blocked_state_requires_manual_review_and_structured_error(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state.update(
            status="blocked",
            last_error={
                "code": "publication_invalid",
                "message": "公開参照が不整合です",
                "evidence_refs": ["validation-000001"],
                "occurred_at": "2026-07-28T00:00:01Z",
            },
        )
        self.assertIs(validate_run_state(state), state)

    def test_published_volumes_must_be_contiguous_and_unique(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state["published_volumes"] = [
            {
                "volume_number": 2,
                "publication_id": "volume-pub-v02-000002",
            }
        ]
        with self.assertRaisesRegex(ContractError, "published_volumes"):
            validate_run_state(state)

    def test_volume_publication_target_accepts_only_volume_number(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state["current_stage"] = "volume_publication"
        state["current_target"] = {"volume_number": 1}
        self.assertIs(validate_run_state(state), state)

        state["current_target"]["basis_generation_id"] = "gen-000001"
        with self.assertRaisesRegex(ContractError, "current_target"):
            validate_run_state(state)