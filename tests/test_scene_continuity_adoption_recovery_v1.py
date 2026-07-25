"""Scene Continuity Candidate Adoption Recovery試験。"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.run_state import RunStateStore
from storycraft.scene_continuity_stage import (
    SceneContinuityStageService,
)
from storycraft.series_contracts import ContractError
from storycraft.v1_workflow import V1WorkflowService

from tests.test_scene_continuity_stage_v1 import (
    AcceptingContinuityModel,
    CONTINUITY_AT,
    create_scene_continuity_workspace,
    matching_continuity,
)


class SceneContinuityAdoptionRecoveryV1Tests(
    unittest.TestCase
):
    def test_recovery_reuses_reserved_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_continuity_workspace(
                temporary
            )
            service = SceneContinuityStageService(
                workspace
            )
            original_adopt = service._adopt

            def adopt_then_crash(
                *args: object,
                **kwargs: object,
            ) -> None:
                original_adopt(*args, **kwargs)
                raise RuntimeError(
                    "crash after continuity adoption"
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
                    AcceptingContinuityModel(
                        matching_continuity()
                    ),
                    updated_at=CONTINUITY_AT,
                )

            store = RunStateStore(workspace)
            crashed = store.load()

            self.assertEqual(
                crashed["pending_commit"][
                    "reserved"
                ],
                {
                    "result_generation_id": (
                        "gen-000002"
                    ),
                },
            )

            counters_before = json.loads(
                (
                    workspace
                    / "runtime/counters.json"
                ).read_text(encoding="utf-8")
            )
            model_calls: list[object] = []

            recovered = V1WorkflowService(
                workspace,
                model_factory=lambda: (
                    model_calls.append(object())
                ),
            ).step()

            counters_after = json.loads(
                (
                    workspace
                    / "runtime/counters.json"
                ).read_text(encoding="utf-8")
            )

            self.assertEqual(
                recovered["current_stage"],
                "scene_commit",
            )
            self.assertEqual(
                recovered["current_target"][
                    "result_generation_id"
                ],
                "gen-000002",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertEqual(model_calls, [])
            self.assertEqual(
                counters_after["next_generation"],
                counters_before["next_generation"],
            )
            self.assertEqual(
                counters_after["next_evidence"],
                counters_before["next_evidence"],
            )
            self.assertEqual(
                counters_after["next_update"],
                counters_before["next_update"],
            )

    def test_conflicting_continuity_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_continuity_workspace(
                temporary
            )
            service = SceneContinuityStageService(
                workspace
            )
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
                    AcceptingContinuityModel(
                        matching_continuity()
                    ),
                    updated_at=CONTINUITY_AT,
                )

            path = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
                / "continuity.json"
            )
            value = json.loads(
                path.read_text(encoding="utf-8")
            )
            value["summary"] = "競合する更新。"
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


if __name__ == "__main__":
    unittest.main()
