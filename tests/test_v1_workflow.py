from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.v1_workflow import V1WorkflowService


CREATED_AT = "2026-07-24T00:00:00Z"


class FakeService:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root

    def run(
        self,
        *args: object,
        **kwargs: object,
    ) -> dict[str, object]:
        self.calls.append((args, kwargs))
        return {"executed": True}


class V1WorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        FakeService.calls = []

    def create_workspace(
        self,
        temporary: str,
        *,
        stage: str,
        source_type: str = "brief",
        pending_commit: dict[str, object] | None = None,
    ) -> Path:
        workspace = Path(temporary) / "novel"
        runtime = workspace / "runtime"
        input_root = workspace / "input"

        runtime.mkdir(parents=True)
        input_root.mkdir(parents=True)
        (runtime / "lock").touch()

        (input_root / "source.json").write_text(
            (
                '{"source_type": "'
                + source_type
                + '"}\n'
            ),
            encoding="utf-8",
        )

        active_scene_id = None
        current_generation_id = None
        target: dict[str, object] = {
            "series": "ws-test-0001",
        }

        if stage == "scene_commit":
            active_scene_id = "scene-v01-c001-s001"
            current_generation_id = "gen-000001"
            target.update(
                {
                    "volume_number": 1,
                    "chapter_number": 1,
                    "scene_number": 1,
                    "scene_id": active_scene_id,
                    "basis_generation_id": (
                        current_generation_id
                    ),
                }
            )

        state = {
            "schema_version": 1,
            "workspace_id": "ws-test-0001",
            "run_id": "run-000001",
            "status": "running",
            "current_stage": stage,
            "current_target": target,
            "current_generation_id": (
                current_generation_id
            ),
            "current_publication_id": None,
            "active_candidate": None,
            "active_scene_id": active_scene_id,
            "pending_commit": pending_commit,
            "stop_reason": None,
            "last_error": None,
            "created_at": CREATED_AT,
            "updated_at": CREATED_AT,
        }

        RunStateStore(workspace).save(state)
        return workspace

    def test_brief_input_does_not_create_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(
                temporary,
                stage="input",
                source_type="brief",
            )
            model_calls: list[object] = []

            with (
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.v1_workflow."
                    "InputStageService",
                    FakeService,
                ),
            ):
                result = V1WorkflowService(
                    workspace,
                    model_factory=lambda: model_calls.append(
                        object()
                    ),
                ).step()

            self.assertEqual(result, {"executed": True})
            self.assertEqual(model_calls, [])
            self.assertEqual(FakeService.calls[0][0], ())

    def test_keywords_input_creates_model_lazily(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(
                temporary,
                stage="input",
                source_type="keywords",
            )
            model = object()
            model_calls: list[object] = []

            def factory() -> object:
                model_calls.append(model)
                return model

            with (
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.v1_workflow."
                    "InputStageService",
                    FakeService,
                ),
            ):
                V1WorkflowService(
                    workspace,
                    model_factory=factory,
                ).step()

            self.assertEqual(model_calls, [model])
            self.assertIs(
                FakeService.calls[0][0][0],
                model,
            )

    def test_initial_accept_does_not_create_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(
                temporary,
                stage="initial_accept",
            )
            model_calls: list[object] = []

            with (
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.v1_workflow."
                    "InitialAcceptStageService",
                    FakeService,
                ),
            ):
                V1WorkflowService(
                    workspace,
                    model_factory=lambda: model_calls.append(
                        object()
                    ),
                ).step()

            self.assertEqual(model_calls, [])
            self.assertEqual(FakeService.calls[0][0], ())

    def test_model_stage_creates_model_once(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(
                temporary,
                stage="initial_concept",
            )
            model = object()
            calls: list[object] = []

            def factory() -> object:
                calls.append(model)
                return model

            with (
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch.dict(
                    "storycraft.v1_workflow."
                    "_MODEL_STAGE_SERVICES",
                    {
                        __import__(
                            "storycraft.stages",
                            fromlist=["Stage"],
                        ).Stage.INITIAL_CONCEPT: FakeService,
                    },
                ),
            ):
                V1WorkflowService(
                    workspace,
                    model_factory=factory,
                ).step()

            self.assertEqual(calls, [model])
            self.assertIs(
                FakeService.calls[0][0][0],
                model,
            )

    def test_pending_commit_recovery_returns_without_running_next_stage(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(
                temporary,
                stage="scene_commit",
                pending_commit={
                    "kind": "scene_commit",
                    "target_id": (
                        "scene-v01-c001-s001"
                    ),
                    "expected_generation_id": (
                        "gen-000002"
                    ),
                    "phase": "prepared",
                },
            )
            model_calls: list[object] = []
            store = RunStateStore(workspace)
            recovered = store.load()
            recovered["current_stage"] = "scene_plan"
            recovered["current_target"] = {
                "series": "ws-test-0001",
                "volume_number": 1,
                "chapter_number": 1,
                "scene_number": 2,
                "basis_generation_id": "gen-000002",
            }
            recovered["current_generation_id"] = (
                "gen-000002"
            )
            recovered["active_scene_id"] = None
            recovered["pending_commit"] = None

            def recover(state: dict) -> None:
                self.assertEqual(
                    state["current_stage"],
                    "scene_commit",
                )
                store.save(recovered)

            service = V1WorkflowService(
                workspace,
                model_factory=lambda: model_calls.append(
                    object()
                ),
            )

            with (
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ) as validate,
                patch.object(
                    service,
                    "_recover_pending_commit",
                    side_effect=recover,
                ) as recovery,
                patch.object(
                    service,
                    "_execute_stage",
                ) as execute,
            ):
                result = service.step()

            self.assertEqual(result, recovered)
            recovery.assert_called_once()
            execute.assert_not_called()
            self.assertEqual(validate.call_count, 2)
            self.assertEqual(model_calls, [])

    def test_scene_commit_does_not_create_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(
                temporary,
                stage="scene_commit",
            )
            model_calls: list[object] = []

            with (
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.v1_workflow."
                    "SceneCommitStageService",
                    FakeService,
                ),
            ):
                result = V1WorkflowService(
                    workspace,
                    model_factory=lambda: model_calls.append(
                        object()
                    ),
                ).step()

            self.assertEqual(result, {"executed": True})
            self.assertEqual(model_calls, [])
            self.assertEqual(FakeService.calls[0][0], ())




class V1WorkflowDispatchCoverageTest(unittest.TestCase):
    def test_every_v1_stage_has_dispatch_path(self) -> None:
        from storycraft import v1_workflow
        from storycraft.stages import Stage

        code_only_or_special = {
            Stage.INPUT,
            Stage.INITIAL_ACCEPT,
            Stage.SCENE_COMMIT,
            Stage.VOLUME_HANDOFF,
        }
        handled = (
            set(v1_workflow._MODEL_STAGE_SERVICES)
            | code_only_or_special
        )

        self.assertEqual(handled, set(Stage))

if __name__ == "__main__":
    unittest.main()
