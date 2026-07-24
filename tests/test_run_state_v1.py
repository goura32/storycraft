"""Storycraft Version 1 run-state契約。"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from storycraft.run_state import (
    RunStateStore,
    is_stale_scene_commit_recovery_state,
    validate_recovery_run_state,
    validate_run_state,
)
from storycraft.series_contracts import ContractError


ROOT = Path(__file__).parent.parent


def load_fixture(relative_path: str) -> dict:
    return json.loads(
        (ROOT / "tests/fixtures" / relative_path).read_text(
            encoding="utf-8"
        )
    )


class RunStateV1Tests(unittest.TestCase):
    def test_running_fixture_is_valid(self) -> None:
        state = load_fixture("workspace/run-state-running.json")
        self.assertIs(validate_run_state(state), state)

    def test_stopped_fixture_is_valid(self) -> None:
        validate_run_state(
            load_fixture("workspace/run-state-stopped.json")
        )

    def test_completed_fixture_is_valid(self) -> None:
        validate_run_state(
            load_fixture("workspace/run-state-completed.json")
        )

    def test_scene_commit_recovery_fixtures_are_valid(self) -> None:
        validate_run_state(
            load_fixture("recovery/scene-rename-crash/run-state.json")
        )
        validate_run_state(
            load_fixture(
                "recovery/generation-rename-crash/run-state.json"
            )
        )

    def test_publication_recovery_fixture_is_valid(self) -> None:
        validate_run_state(
            load_fixture(
                "recovery/publication-rename-crash/run-state.json"
            )
        )

    def test_completed_state_requires_publication(self) -> None:
        state = load_fixture(
            "invalid/run-state-completed-without-publication.json"
        )
        with self.assertRaisesRegex(
            ContractError,
            "current_publication_id",
        ):
            validate_run_state(state)

    def test_unknown_stage_is_rejected(self) -> None:
        state = load_fixture("workspace/run-state-running.json")
        state["current_stage"] = "scene"
        with self.assertRaisesRegex(ContractError, "V1工程"):
            validate_run_state(state)

    def test_running_state_rejects_stop_reason(self) -> None:
        state = load_fixture("workspace/run-state-running.json")
        state["stop_reason"] = "user_requested"
        with self.assertRaisesRegex(ContractError, "stop_reason"):
            validate_run_state(state)

    def test_scene_commit_rejects_state_updated_phase(self) -> None:
        state = load_fixture(
            "recovery/generation-rename-crash/run-state.json"
        )
        state["pending_commit"]["phase"] = "state_updated"
        with self.assertRaisesRegex(ContractError, "phase"):
            validate_run_state(state)

    def test_recovery_validator_accepts_stale_scene_pending(
        self,
    ) -> None:
        state = load_fixture(
            "workspace/run-state-running.json"
        )
        state["status"] = "running"
        state["current_stage"] = "scene_plan"
        state["current_target"] = {
            "series": state["workspace_id"],
            "volume_number": 1,
            "chapter_number": 1,
            "scene_number": 2,
            "basis_generation_id": "gen-000002",
        }
        state["current_generation_id"] = "gen-000002"
        state["active_candidate"] = None
        state["active_scene_id"] = None
        state["pending_commit"] = {
            "kind": "scene_commit",
            "target_id": "scene-v01-c001-s001",
            "expected_generation_id": "gen-000002",
            "phase": "generation_finalized",
        }
        state["stop_reason"] = None
        state["last_error"] = None

        with self.assertRaises(ContractError):
            validate_run_state(state)

        self.assertIs(
            validate_recovery_run_state(state),
            state,
        )
        self.assertTrue(
            is_stale_scene_commit_recovery_state(
                state
            )
        )

    def test_recovery_validator_rejects_prepared_stale_pending(
        self,
    ) -> None:
        state = load_fixture(
            "workspace/run-state-running.json"
        )
        state["status"] = "running"
        state["current_stage"] = "scene_plan"
        state["current_target"] = {
            "series": state["workspace_id"],
            "volume_number": 1,
            "chapter_number": 1,
            "scene_number": 2,
            "basis_generation_id": "gen-000002",
        }
        state["current_generation_id"] = "gen-000002"
        state["active_candidate"] = None
        state["active_scene_id"] = None
        state["pending_commit"] = {
            "kind": "scene_commit",
            "target_id": "scene-v01-c001-s001",
            "expected_generation_id": "gen-000002",
            "phase": "prepared",
        }
        state["stop_reason"] = None
        state["last_error"] = None

        with self.assertRaises(ContractError):
            validate_recovery_run_state(state)

    def test_store_load_recovery_reads_stale_pending(
        self,
    ) -> None:
        state = load_fixture(
            "workspace/run-state-running.json"
        )
        state["status"] = "running"
        state["current_stage"] = "scene_plan"
        state["current_target"] = {
            "series": state["workspace_id"],
            "volume_number": 1,
            "chapter_number": 1,
            "scene_number": 2,
            "basis_generation_id": "gen-000002",
        }
        state["current_generation_id"] = "gen-000002"
        state["active_candidate"] = None
        state["active_scene_id"] = None
        state["pending_commit"] = {
            "kind": "scene_commit",
            "target_id": "scene-v01-c001-s001",
            "expected_generation_id": "gen-000002",
            "phase": "generation_finalized",
        }
        state["stop_reason"] = None
        state["last_error"] = None

        with tempfile.TemporaryDirectory() as temporary:
            store = RunStateStore(Path(temporary))
            store.runtime_root.mkdir(
                parents=True,
                exist_ok=True,
            )
            store.path.write_text(
                json.dumps(
                    state,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                store.load()

            self.assertEqual(
                store.load_recovery(),
                state,
            )

    def test_store_saves_and_loads_runtime_run_state(self) -> None:
        state = load_fixture("workspace/run-state-running.json")

        with tempfile.TemporaryDirectory() as temporary:
            store = RunStateStore(Path(temporary))
            store.save(state)

            self.assertTrue(store.exists())
            self.assertEqual(store.load(), state)
            self.assertFalse(
                store.path.with_suffix(".json.tmp").exists()
            )

    def test_store_atomically_replaces_previous_state(self) -> None:
        running = load_fixture("workspace/run-state-running.json")
        stopped = load_fixture("workspace/run-state-stopped.json")

        with tempfile.TemporaryDirectory() as temporary:
            store = RunStateStore(Path(temporary))
            store.save(running)
            store.save(stopped)

            self.assertEqual(store.load()["status"], "stopped")

    def test_store_rejects_invalid_state_before_writing(self) -> None:
        state = load_fixture("workspace/run-state-running.json")
        state["current_stage"] = "scene"

        with tempfile.TemporaryDirectory() as temporary:
            store = RunStateStore(Path(temporary))
            with self.assertRaisesRegex(ContractError, "V1工程"):
                store.save(state)

            self.assertFalse(store.exists())

    def test_store_rejects_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = RunStateStore(Path(temporary))
            store.runtime_root.mkdir(parents=True)
            store.path.write_text("{", encoding="utf-8")

            with self.assertRaisesRegex(
                ContractError,
                "JSONとして読めません",
            ):
                store.load()

    def test_store_requires_existing_run_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = RunStateStore(Path(temporary))

            with self.assertRaisesRegex(
                ContractError,
                "run-stateがありません",
            ):
                store.load()

    def test_active_scene_requires_scene_coordinates(self) -> None:
        state = copy.deepcopy(
            load_fixture("workspace/run-state-running.json")
        )
        del state["current_target"]["scene_number"]
        with self.assertRaisesRegex(
            ContractError,
            "scene_number",
        ):
            validate_run_state(state)


if __name__ == "__main__":
    unittest.main()


class CandidateAdoptionPendingStateV1Tests(
    unittest.TestCase
):
    def test_candidate_adoption_pending_is_valid(
        self,
    ) -> None:
        state = load_fixture(
            "workspace/run-state-running.json"
        )
        state["current_stage"] = "series_plan"
        state["active_scene_id"] = None
        state["active_candidate"] = {
            "kind": "series_plan",
            "candidate_id": "candidate-000001",
            "version": 1,
        }
        state["pending_commit"] = {
            "kind": "candidate_adoption",
            "target_id": "candidate-000001",
            "stage": "series_plan",
            "version": 1,
            "phase": "prepared",
        }

        validated = validate_run_state(state)

        self.assertEqual(
            validated["pending_commit"]["phase"],
            "prepared",
        )

    def test_candidate_pending_must_match_active(
        self,
    ) -> None:
        state = load_fixture(
            "workspace/run-state-running.json"
        )
        state["current_stage"] = "series_plan"
        state["active_scene_id"] = None
        state["active_candidate"] = {
            "kind": "series_plan",
            "candidate_id": "candidate-000002",
            "version": 1,
        }
        state["pending_commit"] = {
            "kind": "candidate_adoption",
            "target_id": "candidate-000001",
            "stage": "series_plan",
            "version": 1,
            "phase": "prepared",
        }

        with self.assertRaisesRegex(
            ContractError,
            "active_candidate",
        ):
            validate_run_state(state)
