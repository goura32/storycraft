"""Completion Candidate Adoption Recovery試験。"""
from __future__ import annotations

from copy import deepcopy
import tempfile
import unittest
from unittest.mock import patch

from storycraft.completion_stage import (
    CompletionStageService,
)
from storycraft.run_state import RunStateStore
from storycraft.v1_workflow import V1WorkflowService

from tests.test_completion_stage_v1 import (
    AcceptModel,
    COMPLETION_AT,
    completion_candidate,
    create_completion_workspace,
    prepared_inputs,
)


class CompletionAdoptionRecoveryV1Tests(
    unittest.TestCase
):
    def test_recovery_reuses_completion_id_without_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_completion_workspace(
                temporary
            )
            inputs = prepared_inputs()
            service = CompletionStageService(workspace)
            original_adopt = service._adopt

            def adopt_then_crash(
                *args: object,
                **kwargs: object,
            ) -> None:
                original_adopt(*args, **kwargs)
                raise RuntimeError(
                    "crash after completion adoption"
                )

            common_patches = (
                patch.object(
                    CompletionStageService,
                    "_prepare_inputs",
                    return_value=deepcopy(inputs),
                ),
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.completion_stage."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.reviewed_candidate_stage."
                    "validate_workspace_layout"
                ),
            )

            with (
                common_patches[0],
                common_patches[1],
                common_patches[2],
                common_patches[3],
                patch.object(
                    service,
                    "_adopt",
                    side_effect=adopt_then_crash,
                ),
                self.assertRaises(RuntimeError),
            ):
                service.run(
                    AcceptModel(
                        completion_candidate()
                    ),
                    updated_at=COMPLETION_AT,
                )

            crashed = RunStateStore(
                workspace
            ).load()

            self.assertEqual(
                crashed["pending_commit"]["reserved"],
                {
                    "completion_id": (
                        "completion-000001"
                    ),
                },
            )

            model_calls: list[object] = []

            with (
                patch.object(
                    CompletionStageService,
                    "_prepare_inputs",
                    return_value=deepcopy(inputs),
                ),
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.completion_stage."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.reviewed_candidate_stage."
                    "validate_workspace_layout"
                ),
            ):
                recovered = V1WorkflowService(
                    workspace,
                    model_factory=lambda: (
                        model_calls.append(object())
                    ),
                ).step()

            self.assertEqual(
                recovered["current_stage"],
                "publication",
            )
            self.assertEqual(
                recovered["current_target"][
                    "completion_id"
                ],
                "completion-000001",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertEqual(model_calls, [])
            self.assertTrue(
                (
                    workspace
                    / "completion"
                    / "completion-000001"
                    / "result.json"
                ).is_file()
            )


if __name__ == "__main__":
    unittest.main()
