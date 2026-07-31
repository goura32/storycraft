from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.commit_recovery import recover_pending_commit
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError

NOW = "2026-07-29T00:00:00Z"
REQUEST = {"title": "t", "genre": "g", "premise": "p", "required_elements": [], "forbidden_elements": [], "ending_preference": "e", "volume_count": 4, "language": "ja"}


def write_record(root: Path, relative: str, record: dict) -> None:
    path = root / relative / "record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def base_state() -> dict:
    return {"schema_version": 3, "workspace_id": "ws-000001", "status": "running", "last_error": None, "current_stage": "request_intake", "current_target": {}, "current_selection_id": None, "pending_commit": {"kind": "candidate_adoption", "staging_path": "runtime/staging/adopt", "input_selection_id": None, "output_selection_id": "selection-000001", "state_update": {"current_selection_id": "selection-000001", "current_stage": "initial_design", "current_target": {}}, "targets": [{"artifact_id": "request-000001", "artifact_kind": "request", "staging_path": "runtime/staging/adopt/inputs/request-000001", "final_path": "inputs/request-000001", "status": "pending"}, {"artifact_id": "adoption-000001", "artifact_kind": "adoption", "staging_path": "runtime/staging/adopt/runtime/adoptions/adoption-000001", "final_path": "runtime/adoptions/adoption-000001", "status": "pending"}, {"artifact_id": "selection-000001", "artifact_kind": "selection", "staging_path": "runtime/staging/adopt/runtime/selections/selection-000001", "final_path": "runtime/selections/selection-000001", "status": "pending"}]}, "published_volumes": [], "created_at": NOW, "updated_at": NOW}


def populate_staging(root: Path) -> None:
    write_record(root, "runtime/staging/adopt/inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
    write_record(root, "runtime/staging/adopt/runtime/adoptions/adoption-000001", {"schema_version": 1, "adoption_id": "adoption-000001", "source_kind": "direct_request", "candidate_id": None, "quality_id": None, "output_content_artifact_ids": ["request-000001"], "output_selection_id": "selection-000001", "input_selection_id": None, "created_at": NOW})
    write_record(root, "runtime/staging/adopt/runtime/selections/selection-000001", {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"request": "request-000001", "settings": "settings-000001"}, "created_at": NOW})


def candidate_adoption_state() -> dict:
    state = base_state()
    state.update(current_stage="series_plan", current_selection_id="selection-000001")
    staging = "runtime/staging/candidate-adoption"
    state["pending_commit"] = {
        "kind": "candidate_adoption", "staging_path": staging, "input_selection_id": "selection-000001", "output_selection_id": "selection-000002",
        "state_update": {"current_selection_id": "selection-000002", "current_stage": "volume_plan", "current_target": {"volume_number": 1}},
        "targets": [
            {"artifact_id": "series-plan-000001", "artifact_kind": "series-plan", "staging_path": f"{staging}/series-plan-000001", "final_path": "design/series-plans/series-plan-000001", "status": "pending"},
            {"artifact_id": "adoption-000001", "artifact_kind": "adoption", "staging_path": f"{staging}/adoption-000001", "final_path": "runtime/adoptions/adoption-000001", "status": "pending"},
            {"artifact_id": "selection-000002", "artifact_kind": "selection", "staging_path": f"{staging}/selection-000002", "final_path": "runtime/selections/selection-000002", "status": "pending"},
        ],
    }
    return state


def populate_candidate_adoption_staging(root: Path) -> None:
    staging = "runtime/staging/candidate-adoption"
    write_record(root, "runtime/selections/selection-000001", {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"request": "request-000001", "settings": "settings-000001"}, "created_at": NOW})
    write_record(root, "candidates/candidate-000001", {"schema_version": 1, "candidate_id": "candidate-000001", "artifact_kind": "series-plan", "input_selection_id": "selection-000001", "keywords_id": None, "settings_id": "settings-000001", "payload": {"title": "plan"}, "parent_candidate_id": None, "review_record_id": None, "call_id": "call-000001", "created_at": NOW})
    write_record(root, "reviews/review-000001", {"schema_version": 1, "review_id": "review-000001", "candidate_id": "candidate-000001", "response": {"schema_version": "review-response-v1", "decision": "pass", "issues": []}, "call_id": "call-000002", "created_at": NOW})
    write_record(root, "quality/quality-000001", {"schema_version": 1, "quality_id": "quality-000001", "candidate_id": "candidate-000001", "review_record_ids": ["review-000001"], "revision_count": 0, "result": "accepted", "remaining_major_issues": [], "created_at": NOW})
    write_record(root, f"{staging}/series-plan-000001", {"schema_version": 1, "artifact_id": "series-plan-000001", "artifact_kind": "series-plan", "input_selection_id": "selection-000001", "created_at": NOW, "content": {"title": "plan"}})
    write_record(root, f"{staging}/adoption-000001", {"schema_version": 1, "adoption_id": "adoption-000001", "source_kind": "candidate", "candidate_id": "candidate-000001", "quality_id": "quality-000001", "output_content_artifact_ids": ["series-plan-000001"], "output_selection_id": "selection-000002", "input_selection_id": "selection-000001", "created_at": NOW})
    write_record(root, f"{staging}/selection-000002", {"schema_version": 1, "selection_id": "selection-000002", "input_selection_id": "selection-000001", "slots": {"request": "request-000001", "settings": "settings-000001", "series_plan": "series-plan-000001"}, "created_at": NOW})


def scene_commit_state() -> dict:
    state = base_state()
    state.update(current_stage="scene_commit", current_target={"volume_number": 1, "chapter_number": 1, "scene_number": 1}, current_selection_id="selection-000001")
    staging = "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001"
    state["pending_commit"] = {
        "kind": "scene_commit", "staging_path": staging,
        "input_selection_id": "selection-000001", "output_selection_id": "selection-000002",
        "state_update": {"current_selection_id": "selection-000002", "current_stage": "scene_plan", "current_target": {"volume_number": 1, "chapter_number": 1, "scene_number": 2}},
        "targets": [
            {"artifact_id": "scene-artifact-v01-c01-s01-000002", "artifact_kind": "scene", "staging_path": f"{staging}/scene-artifact-v01-c01-s01-000002", "final_path": "scenes/scene-artifact-v01-c01-s01-000002", "status": "pending"},
            {"artifact_id": "gen-000002", "artifact_kind": "generation", "staging_path": f"{staging}/gen-000002", "final_path": "generations/gen-000002", "status": "pending"},
            {"artifact_id": "scene-commit-v01-c01-s01-000001", "artifact_kind": "scene-commit", "staging_path": f"{staging}/scene-commit-v01-c01-s01-000001", "final_path": "scenes/scene-commit-v01-c01-s01-000001", "status": "pending"},
            {"artifact_id": "selection-000002", "artifact_kind": "selection", "staging_path": f"{staging}/selection-000002", "final_path": "runtime/selections/selection-000002", "status": "pending"},
        ],
    }
    return state


def populate_scene_commit_staging(root: Path) -> None:
    # Write the request record (required for selection-000001)
    write_record(root, "inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
    # Write the selection-000001 record (which depends on the request and settings)
    write_record(root, "runtime/selections/selection-000001", {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"request": "request-000001", "settings": "settings-000001"}, "created_at": NOW})
    staging = "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001"
    write_record(root, f"{staging}/scene-artifact-v01-c01-s01-000002", {"schema_version": 1, "artifact_id": "scene-artifact-v01-c01-s01-000002", "artifact_kind": "scene", "input_selection_id": "selection-000001", "created_at": NOW, "content": {}})
    write_record(root, f"{staging}/gen-000002", {"schema_version": 1, "artifact_id": "gen-000002", "artifact_kind": "generation", "input_selection_id": "selection-000001", "created_at": NOW, "content": {}})
    write_record(root, f"{staging}/scene-commit-v01-c01-s01-000001", {"schema_version": 1, "artifact_id": "scene-commit-v01-c01-s01-000001", "artifact_kind": "scene-commit", "input_selection_id": "selection-000001", "created_at": NOW, "content": {
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
    }})
    write_record(root, f"{staging}/selection-000002", {"schema_version": 1, "selection_id": "selection-000002", "input_selection_id": "selection-000001", "slots": {"settings": "settings-000001", "scene_commit.v01.c01.s01": "scene-commit-v01-c01-s01-000001"}, "created_at": NOW})


class CommitRecoveryTests(unittest.TestCase):
    def test_recovery_target_status_location_matrix_uses_real_filesystem(self) -> None:
        """Each target's declared status and on-disk location converges or blocks.

        The other manifest targets remain staged so a successful case proves that
        recovery continues through the whole manifest and applies its state update.
        """
        cases = (
            ("pending", "missing", False, "pending.*staging"),
            ("pending", "staging", True, None),
            ("pending", "final", True, None),
            ("pending", "both", False, "stagingとfinal"),
            ("pending", "invalid-final", False, "field構成"),
            ("finalized", "missing", False, "finalized.*final"),
            ("finalized", "staging", False, "finalized.*final"),
            ("finalized", "final", True, None),
            ("finalized", "both", False, "stagingとfinal"),
            ("finalized", "invalid-final", False, "field構成"),
        )
        for status, location, succeeds, message in cases:
            with self.subTest(status=status, location=location), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                state = base_state()
                state["pending_commit"]["targets"][0]["status"] = status
                populate_staging(root)
                for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                    (root / parent).mkdir(parents=True)
                write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
                staging = root / "runtime/staging/adopt/inputs/request-000001"
                final = root / "inputs/request-000001"
                if location in {"final", "invalid-final", "both"}:
                    final.parent.mkdir(parents=True, exist_ok=True)
                    if location == "both":
                        final.mkdir()
                        (final / "record.json").write_text(staging.joinpath("record.json").read_text(encoding="utf-8"), encoding="utf-8")
                    else:
                        staging.rename(final)
                if location == "missing":
                    staging.rename(root / "removed-target")
                if location == "invalid-final":
                    (final / "record.json").write_text("{}", encoding="utf-8")
                RunStateStore(root).save(state)

                if succeeds:
                    recovered = recover_pending_commit(root)
                    self.assertIsNone(recovered["pending_commit"])
                    self.assertEqual(recovered["current_stage"], "initial_design")
                    self.assertTrue((root / "inputs/request-000001/record.json").is_file())
                else:
                    assert message is not None
                    with self.assertRaisesRegex(ContractError, message):
                        recover_pending_commit(root)

    def test_recovery_allows_pending_staging_alongside_another_finalized_target(self) -> None:
        """Different targets may occupy their normal interrupted locations together."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = base_state()
            state["pending_commit"]["targets"][1]["status"] = "finalized"
            populate_staging(root)
            for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            (root / "runtime/staging/adopt/runtime/adoptions/adoption-000001").rename(root / "runtime/adoptions/adoption-000001")
            RunStateStore(root).save(state)

            recovered = recover_pending_commit(root)

            self.assertIsNone(recovered["pending_commit"])
            self.assertTrue((root / "inputs/request-000001/record.json").is_file())
            self.assertTrue((root / "runtime/adoptions/adoption-000001/record.json").is_file())

    def test_rejects_finalized_target_that_only_has_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            populate_staging(root)
            state = base_state()
            state["pending_commit"]["targets"][0]["status"] = "finalized"
            RunStateStore(root).save(state)

            with self.assertRaisesRegex(ContractError, "finalized.*final"):
                recover_pending_commit(root)

    def test_finalizes_only_manifest_target_directories_validates_then_applies_update_and_clears_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = base_state()
            populate_staging(root)
            for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            RunStateStore(root).save(state)
            recovered = recover_pending_commit(root)
            self.assertIsNone(recovered["pending_commit"])
            self.assertEqual(recovered["current_selection_id"], "selection-000001")
            self.assertEqual(recovered["current_stage"], "initial_design")
            self.assertTrue((root / "inputs/request-000001/record.json").is_file())
            self.assertFalse((root / "runtime/staging/adopt/inputs/request-000001").exists())

    def test_rejects_an_unlisted_directory_under_the_manifest_staging_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            populate_staging(root)
            (root / "runtime/staging/adopt/unlisted").mkdir()
            RunStateStore(root).save(base_state())
            with self.assertRaisesRegex(ContractError, "manifest外"):
                recover_pending_commit(root)

    def test_recovery_rejects_symlinked_staging_components_without_renaming_external_source(self) -> None:
        """A symlinked ancestor must not turn a manifest rename into an external move."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            populate_staging(root)
            for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            external = root / "external-source"
            (root / "runtime/staging/adopt/inputs").rename(external)
            (root / "runtime/staging/adopt/inputs").symlink_to(external, target_is_directory=True)
            RunStateStore(root).save(base_state())

            with self.assertRaisesRegex(ContractError, "symlink"):
                recover_pending_commit(root)

            self.assertTrue((external / "request-000001/record.json").is_file())
            self.assertFalse((root / "inputs/request-000001").exists())

    def test_recovery_rejects_symlinked_final_ancestor_without_renaming_into_external_tree(self) -> None:
        """Checking only final.parent misses a symlink higher in the final path."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            populate_candidate_adoption_staging(root)
            external_design = root / "external-design"
            (external_design / "series-plans").mkdir(parents=True)
            (root / "design").symlink_to(external_design, target_is_directory=True)
            RunStateStore(root).save(candidate_adoption_state())

            with self.assertRaisesRegex(ContractError, "symlink"):
                recover_pending_commit(root)

            self.assertTrue((root / "runtime/staging/candidate-adoption/series-plan-000001/record.json").is_file())
            self.assertFalse((external_design / "series-plans/series-plan-000001").exists())

    def test_recovery_rejects_a_candidate_adoption_when_quality_points_to_another_candidate_without_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("inputs", "design/series-plans", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            populate_candidate_adoption_staging(root)
            quality = root / "quality/quality-000001/record.json"
            value = json.loads(quality.read_text(encoding="utf-8"))
            value["candidate_id"] = "candidate-000002"
            quality.write_text(json.dumps(value), encoding="utf-8")
            RunStateStore(root).save(candidate_adoption_state())

            with self.assertRaisesRegex(ContractError, "quality candidate参照"):
                recover_pending_commit(root)

    def test_recovery_rejects_a_candidate_adoption_with_a_non_delta_output_selection_without_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("inputs", "design/series-plans", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            populate_candidate_adoption_staging(root)
            selection = root / "runtime/staging/candidate-adoption/selection-000002/record.json"
            value = json.loads(selection.read_text(encoding="utf-8"))
            value["slots"]["unexpected"] = "request-000001"
            selection.write_text(json.dumps(value), encoding="utf-8")
            RunStateStore(root).save(candidate_adoption_state())

            with self.assertRaisesRegex(ContractError, "output selection delta"):
                recover_pending_commit(root)

    def test_recovers_a_real_closed_scene_commit_manifest_without_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("scenes", "generations", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            populate_scene_commit_staging(root)
            RunStateStore(root).save(scene_commit_state())

            recovered = recover_pending_commit(root)

            self.assertIsNone(recovered["pending_commit"])
            self.assertEqual(recovered["current_stage"], "scene_plan")
            self.assertTrue((root / "scenes/scene-commit-v01-c01-s01-000001/record.json").is_file())

    def test_rejects_scene_commit_record_with_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("scenes", "generations", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {}, "created_at": NOW})
            populate_scene_commit_staging(root)
            commit = root / "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001/scene-commit-v01-c01-s01-000001/record.json"
            value = json.loads(commit.read_text(encoding="utf-8"))
            value["unexpected"] = True
            commit.write_text(json.dumps(value), encoding="utf-8")
            RunStateStore(root).save(scene_commit_state())

            with self.assertRaisesRegex(ContractError, "scene_commit record"):
                recover_pending_commit(root)
