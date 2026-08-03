"""正本 docs/design/state-and-transitions.md に基づく閉じた run-state v3 契約。"""
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
    "pending_commit": None,
    "published_volumes": [],
    "created_at": "2026-07-28T00:00:00Z",
    "updated_at": "2026-07-28T00:00:00Z",
}


def target(artifact_id: str, artifact_kind: str, final_path: str, staging_root: str = "runtime/staging/adopt") -> dict[str, object]:
    role = {
        "adoption": "adoption_record",
        "selection": "selection_snapshot",
        "scene-commit": "scene_commit_record",
        "volume-publication": "publication_directory",
    }.get(artifact_kind, "content_artifact")
    return {
        "artifact_id": artifact_id,
        "target_kind": role,
        "artifact_kind": artifact_kind if role == "content_artifact" else None,
        "staging_path": f"{staging_root}/{artifact_id}",
        "final_path": final_path,
        "status": "pending",
    }


class RunStateV2Tests(unittest.TestCase):
    def test_run_state_is_closed_and_has_no_active_candidate_or_scene(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        self.assertIs(validate_run_state(state), state)
        for retired in ("active_candidate", "active_scene_id"):
            state = copy.deepcopy(BASE_STATE)
            state[retired] = None
            with self.assertRaisesRegex(ContractError, "field構成"):
                validate_run_state(state)

    def test_bootstrap_candidate_adoption_allows_null_input_selection(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state.update(current_stage="request_intake", current_target={}, current_selection_id=None)
        state["pending_commit"] = {
            "kind": "candidate_adoption",
            "staging_path": "runtime/staging/adopt",
            "input_selection_id": None,
            "output_selection_id": "selection-000001",
            "state_update": {
                "current_selection_id": "selection-000001",
                "current_stage": "initial_design",
                "current_target": {},
            },
            "targets": [
                target("request-000001", "request", "inputs/request-000001"),
                target("adoption-000001", "adoption", "runtime/adoptions/adoption-000001"),
                target("selection-000001", "selection", "runtime/selections/selection-000001"),
            ],
        }
        self.assertIs(validate_run_state(state), state)

    def test_initial_design_adoption_includes_its_first_generation(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state["pending_commit"] = {
            "kind": "candidate_adoption", "staging_path": "runtime/staging/adopt",
            "input_selection_id": "selection-000001", "output_selection_id": "selection-000002",
            "state_update": {"current_selection_id": "selection-000002", "current_stage": "series_plan", "current_target": {}},
            "targets": [
                target("initial-design-000001", "initial-design", "design/initial/initial-design-000001"),
                target("gen-000001", "generation", "generations/gen-000001"),
                target("adoption-000001", "adoption", "runtime/adoptions/adoption-000001"),
                target("selection-000002", "selection", "runtime/selections/selection-000002"),
            ],
        }
        self.assertIs(validate_run_state(state), state)

    def test_manifest_requires_exact_kind_specific_targets_and_state_update(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state["pending_commit"] = {
            "kind": "scene_commit",
            "staging_path": "runtime/staging/adopt",
            "input_selection_id": "selection-000001",
            "output_selection_id": "selection-000002",
            "state_update": {
                "current_selection_id": "selection-000002",
                "current_stage": "scene_plan",
                "current_target": {"volume_number": 1, "chapter_number": 1, "scene_number": 2},
            },
            "targets": [
                target("scene-v01-c01-s01-000002", "scene", "scenes/scene-v01-c01-s01-000002"),
                target("gen-000002", "generation", "generations/gen-000002"),
                target("scene-commit-v01-c01-s01-000001", "scene-commit", "scenes/scene-commit-v01-c01-s01-000001"),
                target("selection-000002", "selection", "runtime/selections/selection-000002"),
            ],
        }
        self.assertIs(validate_run_state(state), state)
        state["pending_commit"]["targets"].pop()
        with self.assertRaisesRegex(ContractError, "targets"):
            validate_run_state(state)

    def test_manifest_rejects_sha256_unknown_fields_and_noncanonical_paths(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state["pending_commit"] = {
            "kind": "volume_publication",
            "staging_path": "runtime/staging/volume-publication-000001",
            "input_selection_id": "selection-000001",
            "output_selection_id": None,
            "state_update": {
                "current_selection_id": "selection-000001",
                "current_stage": "volume_plan",
                "current_target": {"volume_number": 2},
                "published_volumes": [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
            },
            "targets": [target("volume-pub-v01-000001", "volume-publication", "publications/volume-pub-v01-000001", "runtime/staging/volume-publication-000001")],
        }
        state["pending_commit"]["targets"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ContractError, "field構成"):
            validate_run_state(state)
        del state["pending_commit"]["targets"][0]["sha256"]
        state["pending_commit"]["targets"][0]["final_path"] = "scenes/../scenes/scene-v01-c01-s01-000001"
        with self.assertRaisesRegex(ContractError, "正規相対"):
            validate_run_state(state)

    def test_completed_state_has_no_current_work(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state.update(
            status="completed",
            current_stage=None,
            current_target=None,
            current_selection_id="selection-000010",
            published_volumes=[{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
        )
        self.assertIs(validate_run_state(state), state)

    def test_final_volume_manifest_declares_completed_state_as_its_recovery_update(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state.update(current_stage="volume_publication", current_target={"volume_number": 1})
        state["pending_commit"] = {
            "kind": "volume_publication",
            "staging_path": "runtime/staging/volume-publication-volume-pub-v01-000001",
            "input_selection_id": "selection-000001",
            "output_selection_id": None,
            "state_update": {
                "status": "completed",
                "last_error": None,
                "current_selection_id": "selection-000001",
                "current_stage": None,
                "current_target": None,
                "published_volumes": [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
            },
            "targets": [target("volume-pub-v01-000001", "volume-publication", "publications/volume-pub-v01-000001", "runtime/staging/volume-publication-volume-pub-v01-000001")],
        }
        self.assertIs(validate_run_state(state), state)

    def test_blocked_state_requires_structured_error(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state.update(status="blocked", last_error={
            "code": "publication_invalid", "message": "公開参照が不整合です",
            "evidence_refs": ["validation-000001"], "occurred_at": "2026-07-28T00:00:01Z",
        })
        self.assertIs(validate_run_state(state), state)

    def test_published_volume_id_is_canonical_and_timestamp_is_utc(self) -> None:
        state = copy.deepcopy(BASE_STATE)
        state["published_volumes"] = [{"volume_number": 1, "publication_id": "volume-pub-v01-../../escape"}]
        with self.assertRaises(ContractError):
            validate_run_state(state)

        state = copy.deepcopy(BASE_STATE)
        state["created_at"] = "2026-07-28T00:00:00"
        state["updated_at"] = "2026-07-28T00:00:00+00:00"
        with self.assertRaises(ContractError):
            validate_run_state(state)
