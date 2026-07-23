"""Storycraft Version 1 series_plan Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from storycraft.initial_accept_stage import (
    InitialAcceptStageService,
)
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.series_plan_stage import (
    SeriesPlanStageService,
)
from storycraft.workspace import validate_workspace_layout

from tests.test_initial_accept_stage_v1 import (
    create_integrated_workspace,
)
from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    load_json_from,
)
from tests.test_series_plan_schema_v1 import (
    series_plan_candidate,
)


PLAN_AT = "2026-07-23T10:12:00Z"


def create_series_plan_workspace(
    temporary: str,
) -> Path:
    workspace, _ = create_integrated_workspace(temporary)
    InitialAcceptStageService(workspace).run(
        updated_at="2026-07-23T10:10:00Z",
    )
    return workspace


class SeriesPlanStageV1Tests(unittest.TestCase):
    def test_generate_review_adopt_and_advance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            model = AcceptingModel(
                series_plan_candidate()
            )

            state = SeriesPlanStageService(workspace).run(
                model,
                updated_at=PLAN_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "series_plan"),
                    ("critique", "series_plan"),
                ],
            )
            self.assertEqual(
                state["current_stage"],
                "volume_plan",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                state["current_target"],
                {
                    "series": "ws-test-0001",
                    "series_plan_id": "series-plan-0001",
                    "volume_number": 1,
                    "basis_generation_id": "gen-000001",
                },
            )
            self.assertIsNone(state["active_candidate"])

            path = (
                workspace
                / "design/series-plans"
                / "series-plan-v0001"
                / "series-plan.json"
            )
            adopted = load_json_from(path)
            self.assertEqual(
                adopted["schema_version"],
                1,
            )
            self.assertEqual(
                adopted["series_plan_id"],
                "series-plan-0001",
            )
            self.assertEqual(adopted["version"], 1)
            self.assertEqual(
                adopted["status"],
                "accepted",
            )
            self.assertEqual(
                adopted["basis_generation_id"],
                "gen-000001",
            )
            self.assertIsNone(
                adopted["parent_plan_id"]
            )
            self.assertEqual(
                adopted["created_at"],
                PLAN_AT,
            )
            for key, value in series_plan_candidate().items():
                self.assertEqual(adopted[key], value)

            candidate = load_json_from(
                workspace
                / "runtime/candidates/series_plan"
                / "candidate-000009/v0001/candidate.json"
            )
            self.assertEqual(
                candidate["content"],
                series_plan_candidate(),
            )
            self.assertNotIn(
                "series_plan_id",
                candidate["content"],
            )

            self.assertEqual(
                model.contexts[0],
                model.contexts[1],
            )
            context = model.contexts[0]
            self.assertEqual(
                context["brief"]["volume_count"],
                4,
            )
            self.assertEqual(
                context["initial_design"]["design_id"],
                "initial-design-0001",
            )
            self.assertEqual(
                context["initial_generation"][
                    "commit.json"
                ]["generation_id"],
                "gen-000001",
            )
            validate_workspace_layout(workspace)

    def test_invalid_candidate_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            invalid = series_plan_candidate()
            invalid["volume_count"] = 5

            state = SeriesPlanStageService(workspace).run(
                AcceptingModel(invalid),
                updated_at=PLAN_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "manual_review_required",
            )
            self.assertFalse(
                (
                    workspace
                    / "design/series-plans"
                    / "series-plan-v0001"
                ).exists()
            )

    def test_wrong_stage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            state_store = RunStateStore(workspace)
            state = state_store.load()
            state["current_stage"] = "volume_plan"
            state_store.save(state)

            with self.assertRaises(ContractError):
                SeriesPlanStageService(workspace).run(
                    AcceptingModel(
                        series_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_existing_different_plan_cannot_be_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            service = SeriesPlanStageService(workspace)
            service.run(
                AcceptingModel(series_plan_candidate()),
                updated_at=PLAN_AT,
            )

            state_store = RunStateStore(workspace)
            state = state_store.load()
            state["current_stage"] = "series_plan"
            state["current_target"] = {
                "series": state["workspace_id"],
                "basis_generation_id": "gen-000001",
            }
            state_store.save(state)

            changed = deepcopy(series_plan_candidate())
            changed["ending_path"] = (
                "別の結末へ接続する。"
            )

            with self.assertRaises(ContractError):
                service.run(
                    AcceptingModel(changed),
                    updated_at=PLAN_AT,
                )

    def test_workspace_rejects_mutated_plan(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            SeriesPlanStageService(workspace).run(
                AcceptingModel(series_plan_candidate()),
                updated_at=PLAN_AT,
            )

            path = (
                workspace
                / "design/series-plans"
                / "series-plan-v0001"
                / "series-plan.json"
            )
            value = json.loads(
                path.read_text(encoding="utf-8")
            )
            value["basis_generation_id"] = "gen-999999"
            path.write_text(
                json.dumps(
                    value,
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
