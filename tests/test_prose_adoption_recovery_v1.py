"""Scene Prose Candidate Adoption Recovery試験。"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.run_state import RunStateStore
from storycraft.scene_prose_stage import (
    SceneProseStageService,
)
from storycraft.series_contracts import ContractError
from storycraft.v1_workflow import V1WorkflowService

from tests.test_scene_prose_stage_v1 import (
    AcceptingProseModel,
    PROSE,
    PROSE_AT,
    create_scene_prose_workspace,
)


class ProseAdoptionRecoveryV1Tests(
    unittest.TestCase
):
    def test_prepared_recovery_finishes_without_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_prose_workspace(
                temporary
            )
            service = SceneProseStageService(
                workspace
            )
            original_adopt = service._adopt

            def adopt_then_crash(
                *args: object,
                **kwargs: object,
            ) -> None:
                original_adopt(*args, **kwargs)
                raise RuntimeError(
                    "crash after prose adoption"
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
                    AcceptingProseModel(PROSE),
                    updated_at=PROSE_AT,
                )

            store = RunStateStore(workspace)
            crashed = store.load()

            self.assertEqual(
                crashed["current_stage"],
                "scene_prose",
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

            prose_path = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
                / "prose.md"
            )
            self.assertEqual(
                prose_path.read_text(
                    encoding="utf-8"
                ),
                PROSE + "\n",
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
                "scene_continuity",
            )
            self.assertEqual(
                recovered["current_target"][
                    "prose_version"
                ],
                1,
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
            workspace = create_scene_prose_workspace(
                temporary
            )
            service = SceneProseStageService(
                workspace
            )
            original_save = (
                service.runner.state_store.save
            )

            def crash_before_final_state(
                state: dict,
            ) -> None:
                if (
                    state["current_stage"]
                    == "scene_continuity"
                    and state["pending_commit"] is None
                ):
                    raise RuntimeError(
                        "crash before prose state advance"
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
                    AcceptingProseModel(PROSE),
                    updated_at=PROSE_AT,
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
                "scene_continuity",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertEqual(model_calls, [])

    def test_conflicting_prose_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_prose_workspace(
                temporary
            )
            service = SceneProseStageService(
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
                    AcceptingProseModel(PROSE),
                    updated_at=PROSE_AT,
                )

            prose_path = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
                / "prose.md"
            )
            prose_path.write_text(
                "競合する本文。\n",
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
            workspace = create_scene_prose_workspace(
                temporary
            )
            service = SceneProseStageService(
                workspace
            )
            original_save = (
                service.runner.state_store.save
            )
            observed_phases: list[str] = []

            def checking_save(state: dict) -> None:
                if (
                    state["current_stage"]
                    == "scene_prose"
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
                    AcceptingProseModel(PROSE),
                    updated_at=PROSE_AT,
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
