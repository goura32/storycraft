"""Storycraft Version 1 run-state契約。"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from storycraft.run_state import validate_run_state
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
