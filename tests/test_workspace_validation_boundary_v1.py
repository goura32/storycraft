"""Stage wrapperと共通runnerのworkspace検証境界。"""
from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

import storycraft.reviewed_candidate_stage as reviewed
import storycraft.volume_plan_stage as volume_stage
from storycraft.volume_plan_stage import (
    VolumePlanStageService,
)

from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
)
from tests.test_volume_plan_schema_v1 import (
    volume_plan_candidate,
)
from tests.test_volume_plan_stage_v1 import (
    create_volume_plan_workspace,
)


class WorkspaceValidationBoundaryV1Tests(
    unittest.TestCase
):
    def test_stage_wrapper_does_not_repeat_runner_precheck(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_volume_plan_workspace(
                temporary
            )

            with (
                patch.object(
                    volume_stage,
                    "validate_workspace_layout",
                    wraps=(
                        volume_stage
                        .validate_workspace_layout
                    ),
                ) as wrapper_validate,
                patch.object(
                    reviewed,
                    "validate_workspace_layout",
                    wraps=(
                        reviewed
                        .validate_workspace_layout
                    ),
                ) as runner_validate,
            ):
                state = VolumePlanStageService(
                    workspace
                ).run(
                    AcceptingModel(
                        volume_plan_candidate()
                    ),
                    updated_at=(
                        "2026-07-24T06:10:00Z"
                    ),
                )

            self.assertEqual(
                state["current_stage"],
                "chapter_plan",
            )
            self.assertEqual(
                wrapper_validate.call_count,
                1,
            )

            # 共通runner開始時の重複検証は省略し、
            # Adoption後の整合性検証だけ実行する。
            self.assertEqual(
                runner_validate.call_count,
                1,
            )

    def test_workflow_precheck_is_not_repeated_by_scene_stage(
        self,
    ) -> None:
        import storycraft.scene_plan_stage as scene_plan
        import storycraft.v1_workflow as workflow_module
        from storycraft.v1_workflow import (
            V1WorkflowService,
        )
        from tests.test_scene_plan_schema_v1 import (
            scene_plan_candidate,
        )
        from tests.test_scene_plan_stage_v1 import (
            create_scene_plan_workspace,
        )

        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_plan_workspace(
                temporary
            )
            model = AcceptingModel(
                scene_plan_candidate()
            )
            factory_calls: list[object] = []

            with (
                patch.object(
                    workflow_module,
                    "validate_workspace_layout",
                    wraps=(
                        workflow_module
                        .validate_workspace_layout
                    ),
                ) as workflow_validate,
                patch.object(
                    scene_plan,
                    "validate_workspace_layout",
                    wraps=(
                        scene_plan
                        .validate_workspace_layout
                    ),
                ) as stage_validate,
                patch.object(
                    reviewed,
                    "validate_workspace_layout",
                    wraps=(
                        reviewed
                        .validate_workspace_layout
                    ),
                ) as runner_validate,
            ):
                state = V1WorkflowService(
                    workspace,
                    model_factory=lambda: (
                        factory_calls.append(model)
                        or model
                    ),
                ).step(
                    updated_at=(
                        "2026-07-24T10:20:00Z"
                    )
                )

            self.assertEqual(
                state["current_stage"],
                "scene_card",
            )
            self.assertEqual(
                factory_calls,
                [model],
            )
            self.assertEqual(
                workflow_validate.call_count,
                1,
            )
            self.assertEqual(
                stage_validate.call_count,
                0,
            )

            # Adoption後の整合性検証だけを実行する。
            self.assertEqual(
                runner_validate.call_count,
                1,
            )

    def test_workflow_precheck_is_not_repeated_by_volume_stage(
        self,
    ) -> None:
        import storycraft.v1_workflow as workflow_module
        from storycraft.v1_workflow import (
            V1WorkflowService,
        )

        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_volume_plan_workspace(
                temporary
            )
            model = AcceptingModel(
                volume_plan_candidate()
            )
            factory_calls: list[object] = []

            with (
                patch.object(
                    workflow_module,
                    "validate_workspace_layout",
                    wraps=(
                        workflow_module
                        .validate_workspace_layout
                    ),
                ) as workflow_validate,
                patch.object(
                    volume_stage,
                    "validate_workspace_layout",
                    wraps=(
                        volume_stage
                        .validate_workspace_layout
                    ),
                ) as stage_validate,
                patch.object(
                    reviewed,
                    "validate_workspace_layout",
                    wraps=(
                        reviewed
                        .validate_workspace_layout
                    ),
                ) as runner_validate,
            ):
                state = V1WorkflowService(
                    workspace,
                    model_factory=lambda: (
                        factory_calls.append(model)
                        or model
                    ),
                ).step(
                    updated_at=(
                        "2026-07-24T06:11:00Z"
                    )
                )

            self.assertEqual(
                state["current_stage"],
                "chapter_plan",
            )
            self.assertEqual(
                factory_calls,
                [model],
            )
            self.assertEqual(
                workflow_validate.call_count,
                1,
            )
            self.assertEqual(
                stage_validate.call_count,
                0,
            )

            # Adoption後の整合性検証だけ実行する。
            self.assertEqual(
                runner_validate.call_count,
                1,
            )

    def test_all_prevalidated_model_stages_support_flag(
        self,
    ) -> None:
        import inspect
        import storycraft.v1_workflow as workflow

        self.assertEqual(
            set(
                workflow
                ._WORKFLOW_PREVALIDATED_MODEL_STAGES
            ),
            set(workflow._MODEL_STAGE_SERVICES),
        )

        for stage in sorted(
            workflow._WORKFLOW_PREVALIDATED_MODEL_STAGES,
            key=lambda value: value.value,
        ):
            with self.subTest(stage=stage.value):
                service_type = (
                    workflow
                    ._MODEL_STAGE_SERVICES[stage]
                )
                signature = inspect.signature(
                    service_type.run
                )

                self.assertIn(
                    "workspace_already_validated",
                    signature.parameters,
                )


if __name__ == "__main__":
    unittest.main()
