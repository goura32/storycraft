"""JSON Candidate Adoption Crash Recovery試験。"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.series_plan_stage import (
    SeriesPlanStageService,
)
from storycraft.v1_workflow import V1WorkflowService

from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
)
from tests.test_series_plan_schema_v1 import (
    series_plan_candidate,
)
from tests.test_series_plan_stage_v1 import (
    PLAN_AT,
    create_series_plan_workspace,
)


class CandidateAdoptionRecoveryV1Tests(
    unittest.TestCase
):
    def test_prepared_recovery_finishes_without_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            service = SeriesPlanStageService(workspace)
            original_adopt = service._adopt

            def adopt_then_crash(
                *args: object,
                **kwargs: object,
            ) -> None:
                original_adopt(*args, **kwargs)
                raise RuntimeError(
                    "crash after artifact adoption"
                )

            with (
                patch.object(
                    service,
                    "_adopt",
                    side_effect=adopt_then_crash,
                ),
                self.assertRaises(RuntimeError),
            ):
                service.run(
                    AcceptingModel(
                        series_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

            store = RunStateStore(workspace)
            crashed = store.load()

            self.assertEqual(
                crashed["current_stage"],
                "series_plan",
            )
            self.assertEqual(
                crashed["pending_commit"]["kind"],
                "candidate_adoption",
            )
            self.assertEqual(
                crashed["pending_commit"]["phase"],
                "prepared",
            )
            self.assertIsNotNone(
                crashed["active_candidate"]
            )
            self.assertTrue(
                (
                    workspace
                    / "design/series-plans"
                    / "series-plan-v0001"
                    / "series-plan.json"
                ).is_file()
            )

            model_calls: list[object] = []

            recovered = V1WorkflowService(
                workspace,
                model_factory=lambda: (
                    model_calls.append(object())
                ),
            ).step()

            self.assertEqual(
                recovered["current_stage"],
                "volume_plan",
            )
            self.assertIsNone(
                recovered["active_candidate"]
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertEqual(model_calls, [])

    def test_artifact_finalized_recovery_finishes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            service = SeriesPlanStageService(workspace)
            original_save = (
                service.runner.state_store.save
            )

            def crash_before_final_state(
                state: dict,
            ) -> None:
                if (
                    state["current_stage"]
                    == "volume_plan"
                    and state["pending_commit"] is None
                ):
                    raise RuntimeError(
                        "crash before final state"
                    )
                original_save(state)

            with (
                patch.object(
                    service.runner.state_store,
                    "save",
                    side_effect=crash_before_final_state,
                ),
                self.assertRaises(RuntimeError),
            ):
                service.run(
                    AcceptingModel(
                        series_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

            crashed = RunStateStore(
                workspace
            ).load()

            self.assertEqual(
                crashed["pending_commit"]["phase"],
                "artifact_finalized",
            )

            model_calls: list[object] = []

            recovered = V1WorkflowService(
                workspace,
                model_factory=lambda: (
                    model_calls.append(object())
                ),
            ).step()

            self.assertEqual(
                recovered["current_stage"],
                "volume_plan",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertEqual(model_calls, [])

    def test_conflicting_adopted_artifact_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            service = SeriesPlanStageService(workspace)
            original_adopt = service._adopt

            def adopt_then_crash(
                *args: object,
                **kwargs: object,
            ) -> None:
                original_adopt(*args, **kwargs)
                raise RuntimeError("crash")

            with (
                patch.object(
                    service,
                    "_adopt",
                    side_effect=adopt_then_crash,
                ),
                self.assertRaises(RuntimeError),
            ):
                service.run(
                    AcceptingModel(
                        series_plan_candidate()
                    ),
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
            value["title"] = "競合するシリーズ題名"
            path.write_text(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            model_calls: list[object] = []

            with self.assertRaises(ContractError):
                V1WorkflowService(
                    workspace,
                    model_factory=lambda: (
                        model_calls.append(object())
                    ),
                ).step()

            self.assertEqual(model_calls, [])


    def test_active_candidate_and_pending_are_saved_together(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )
            service = SeriesPlanStageService(workspace)
            original_save = (
                service.runner.state_store.save
            )
            observed_phases: list[str] = []

            def checking_save(state: dict) -> None:
                if (
                    state["current_stage"]
                    == "series_plan"
                    and state["active_candidate"]
                    is not None
                ):
                    pending = state["pending_commit"]

                    self.assertIsInstance(
                        pending,
                        dict,
                    )
                    self.assertEqual(
                        pending["kind"],
                        "candidate_adoption",
                    )
                    observed_phases.append(
                        pending["phase"]
                    )

                original_save(state)

            with patch.object(
                service.runner.state_store,
                "save",
                side_effect=checking_save,
            ):
                service.run(
                    AcceptingModel(
                        series_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

            self.assertEqual(
                observed_phases,
                [
                    "prepared",
                    "artifact_finalized",
                ],
            )


if __name__ == "__main__":
    unittest.main()
