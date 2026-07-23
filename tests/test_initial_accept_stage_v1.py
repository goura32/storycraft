"""Storycraft Version 1 initial_accept Stage契約。"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from storycraft.initial_accept_stage import (
    InitialAcceptStageService,
)
from storycraft.initial_integrate_stage import (
    InitialIntegrateStageService,
)
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.workspace import validate_workspace_layout

from tests.test_initial_integrate_stage_v1 import (
    InitialIntegrateStageV1Tests,
)
from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    load_json_from,
)


ACCEPT_AT = "2026-07-23T10:10:00Z"
RECOVERY_AT = "2026-07-23T10:11:00Z"


def create_integrated_workspace(
    temporary: str,
) -> tuple[Path, dict]:
    helper = InitialIntegrateStageV1Tests(
        "test_generate_review_adopt_and_advance"
    )
    helper.setUp()
    workspace = helper.create_workspace(temporary)
    InitialIntegrateStageService(workspace).run(
        AcceptingModel(helper.integrated),
        updated_at="2026-07-23T10:09:00Z",
    )
    return workspace, helper.integrated


class InitialAcceptStageV1Tests(unittest.TestCase):
    def test_accepts_design_creates_generation_and_advances(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, integrated = (
                create_integrated_workspace(temporary)
            )

            state = InitialAcceptStageService(
                workspace
            ).run(updated_at=ACCEPT_AT)

            self.assertEqual(
                state["current_stage"],
                "series_plan",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                state["current_target"],
                {
                    "series": "ws-test-0001",
                    "basis_generation_id": "gen-000001",
                },
            )

            design = load_json_from(
                workspace
                / "design/initial/v0001"
                / "initial-design.json"
            )
            self.assertEqual(
                design["design_id"],
                "initial-design-0001",
            )
            self.assertEqual(design["version"], 1)
            self.assertEqual(
                {
                    key: design[key]
                    for key in integrated
                },
                integrated,
            )

            generation_root = (
                workspace / "generations/gen-000001"
            )
            self.assertEqual(
                {
                    path.name
                    for path in generation_root.iterdir()
                },
                {
                    "canon.json",
                    "state.json",
                    "evidence.json",
                    "commit.json",
                },
            )

            commit = load_json_from(
                generation_root / "commit.json"
            )
            self.assertEqual(
                commit["commit_type"],
                "initial_design",
            )
            self.assertIsNone(
                commit["parent_generation_id"]
            )

            counters = load_json_from(
                workspace / "runtime/counters.json"
            )
            self.assertEqual(
                counters["next_generation"],
                2,
            )
            validate_workspace_layout(workspace)

    def test_recovery_reuses_finalized_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = create_integrated_workspace(
                temporary
            )
            service = InitialAcceptStageService(workspace)
            service.run(updated_at=ACCEPT_AT)

            store = RunStateStore(workspace)
            recovery = store.load()
            recovery["current_stage"] = "initial_accept"
            recovery["current_target"] = {
                "series": "ws-test-0001",
            }
            recovery["current_generation_id"] = None
            recovery["updated_at"] = (
                "2026-07-23T10:09:30Z"
            )
            store.save(recovery)

            state = service.run(updated_at=RECOVERY_AT)

            self.assertEqual(
                state["current_generation_id"],
                "gen-000001",
            )
            counters = load_json_from(
                workspace / "runtime/counters.json"
            )
            self.assertEqual(
                counters["next_generation"],
                2,
            )

    def test_wrong_stage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = create_integrated_workspace(
                temporary
            )
            InitialAcceptStageService(workspace).run(
                updated_at=ACCEPT_AT
            )

            with self.assertRaises(ContractError):
                InitialAcceptStageService(workspace).run(
                    updated_at=RECOVERY_AT
                )

    def test_workspace_rejects_changed_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = create_integrated_workspace(
                temporary
            )
            InitialAcceptStageService(workspace).run(
                updated_at=ACCEPT_AT
            )

            path = (
                workspace
                / "generations/gen-000001/state.json"
            )
            invalid = load_json_from(path)
            character_id = next(
                iter(invalid["characters"])
            )
            invalid["characters"][character_id][
                "availability"
            ] = "unavailable"
            path.write_text(
                json.dumps(
                    invalid,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)

    def test_workspace_rejects_changed_accepted_design(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = create_integrated_workspace(
                temporary
            )
            InitialAcceptStageService(workspace).run(
                updated_at=ACCEPT_AT
            )

            path = (
                workspace
                / "design/initial/v0001"
                / "initial-design.json"
            )
            invalid = load_json_from(path)
            invalid["threads"][0]["title"] = "変更"
            path.write_text(
                json.dumps(
                    invalid,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
