"""Storycraft V1 completion Stage試験。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.completion_stage import (
    CompletionStageService,
)
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.v1_workflow import V1WorkflowService
from storycraft.workspace import (
    _validate_completion_artifacts,
)

from tests.test_completion_schema_v1 import (
    GENERATION_ID,
    completion_candidate,
    current_generation,
    handoffs,
    initial_design,
    series_plan,
)
from tests.test_volume_handoff_stage_v1 import (
    prepare_volume_handoff_workspace,
)


COMPLETION_AT = "2026-07-24T12:20:00Z"
COMPLETION_RETRY_AT = "2026-07-24T12:21:00Z"


class AcceptModel:
    def __init__(self, candidate: dict) -> None:
        self.candidate = deepcopy(candidate)
        self.calls: list[tuple[str, str]] = []
        self.contexts: list[dict] = []

    def generate(
        self,
        stage: str,
        context: dict,
    ) -> dict:
        self.calls.append(("generate", stage))
        self.contexts.append(deepcopy(context))
        return deepcopy(self.candidate)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.calls.append(("critique", stage))
        return {"issues": []}

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        raise AssertionError("revision must not be called")


def create_completion_workspace(
    temporary: str,
) -> Path:
    workspace, _ = prepare_volume_handoff_workspace(
        temporary
    )
    store = RunStateStore(workspace)
    state = store.load()
    state["current_stage"] = "completion"
    state["current_target"] = {
        "series": state["workspace_id"],
        "series_plan_id": "series-plan-0001",
        "volume_number": 1,
        "basis_generation_id": GENERATION_ID,
        "final_handoff_id": "handoff-v01",
    }
    store.save(state)
    return workspace


def prepared_inputs(
    generation: dict | None = None,
) -> dict:
    return {
        "initial_design": initial_design(),
        "series_plan": series_plan(),
        "handoffs": handoffs(),
        "current_generation": (
            generation or current_generation()
        ),
        "completed_scene_ids": [
            "scene-v01-c001-s001",
        ],
        "precheck_summary": {
            "all_volumes_complete": True,
            "all_planned_scenes_committed": True,
            "unfinished_scene_work": False,
        },
    }


def run_with_prepared_inputs(
    workspace: Path,
    candidate: dict,
    inputs: dict,
    *,
    updated_at: str = COMPLETION_AT,
) -> tuple[dict, AcceptModel]:
    service = CompletionStageService(workspace)
    model = AcceptModel(candidate)

    with (
        patch.object(
            service,
            "_prepare_inputs",
            return_value=deepcopy(inputs),
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
        state = service.run(
            model,
            updated_at=updated_at,
        )

    return state, model


class CompletionStageV1Tests(unittest.TestCase):
    def test_complete_finalizes_publication_and_completes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_completion_workspace(temporary)
            state, model = run_with_prepared_inputs(
                workspace,
                completion_candidate(),
                prepared_inputs(),
            )
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["current_stage"], "completion")
            self.assertEqual(
                state["current_publication_id"],
                "pub-000001",
            )
            self.assertIsNone(state["pending_commit"])
            self.assertEqual(
                model.calls,
                [
                    ("generate", "completion"),
                    ("critique", "completion"),
                ],
            )
            result = json.loads(
                (workspace / "completion/completion-000001/result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(result["status"], "complete")
            self.assertTrue(
                (workspace / "publications/pub-000001").is_dir()
            )

    def test_complete_with_issues_finalizes_publication(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_completion_workspace(temporary)
            candidate = completion_candidate()
            candidate["status"] = "complete_with_issues"
            candidate["character_arc_checks"][0]["status"] = "partially_satisfied"
            candidate["issues"] = [{
                "category": "minor_arc",
                "description": "人物Arcの余韻がやや弱い。",
            }]
            state, _ = run_with_prepared_inputs(
                workspace,
                candidate,
                prepared_inputs(),
            )
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["current_stage"], "completion")
            self.assertEqual(
                state["current_publication_id"],
                "pub-000001",
            )
            metadata = json.loads(
                (workspace / "publications/pub-000001/metadata.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                metadata["completion_status"],
                "complete_with_issues",
            )

    def test_incomplete_is_adopted_and_blocks(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_completion_workspace(
                temporary
            )
            generation = current_generation(
                thread_status="progressing"
            )
            candidate = completion_candidate()
            candidate["status"] = "incomplete"
            candidate["summary"] = (
                "完結必須Threadが未解決。"
            )
            candidate["thread_checks"][0]["status"] = (
                "progressing"
            )
            candidate["thread_checks"][0]["issues"] = [
                "完結必須Threadが未解決。",
            ]
            candidate["issues"] = [{
                "category": "required_thread",
                "description": (
                    "完結必須Threadがresolvedではない。"
                ),
            }]

            state, _ = run_with_prepared_inputs(
                workspace,
                candidate,
                prepared_inputs(generation),
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["current_stage"],
                "completion",
            )
            self.assertEqual(
                state["stop_reason"],
                "completion_incomplete",
            )
            self.assertEqual(
                state["last_error"]["code"],
                "COMPLETION_INCOMPLETE",
            )
            self.assertTrue(
                (
                    workspace
                    / "completion"
                    / "completion-000001"
                    / "result.json"
                ).is_file()
            )

    def test_missing_series_artifacts_reject_before_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_completion_workspace(
                temporary
            )
            model = AcceptModel(completion_candidate())

            with self.assertRaises(
                (ContractError, FileNotFoundError)
            ):
                CompletionStageService(workspace).run(
                    model,
                    updated_at=COMPLETION_AT,
                )

            self.assertEqual(model.calls, [])

    def test_existing_result_is_not_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_completion_workspace(
                temporary
            )
            service = CompletionStageService(workspace)
            candidate = completion_candidate()
            inputs = prepared_inputs()

            service._adopt(
                candidate,
                inputs["current_generation"],
                inputs["initial_design"],
                inputs["series_plan"],
                inputs["handoffs"],
                GENERATION_ID,
                "completion-000001",
                COMPLETION_AT,
            )

            changed = deepcopy(candidate)
            changed["summary"] = "別の完結判定。"

            with self.assertRaisesRegex(
                ContractError,
                "上書き",
            ):
                service._adopt(
                    changed,
                    inputs["current_generation"],
                    inputs["initial_design"],
                    inputs["series_plan"],
                    inputs["handoffs"],
                    GENERATION_ID,
                    "completion-000001",
                    COMPLETION_RETRY_AT,
                )

    def test_workflow_dispatches_completion_model_and_finishes_publication(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_completion_workspace(temporary)
            model = AcceptModel(completion_candidate())
            factory_calls: list[object] = []
            with (
                patch.object(
                    CompletionStageService,
                    "_prepare_inputs",
                    return_value=prepared_inputs(),
                ),
                patch("storycraft.v1_workflow.validate_workspace_layout"),
                patch("storycraft.completion_stage.validate_workspace_layout"),
                patch("storycraft.reviewed_candidate_stage.validate_workspace_layout"),
            ):
                state = V1WorkflowService(
                    workspace,
                    model_factory=lambda: (
                        factory_calls.append(model) or model
                    ),
                ).step(updated_at=COMPLETION_AT)
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["current_stage"], "completion")
            self.assertEqual(
                state["current_publication_id"],
                "pub-000001",
            )
            self.assertEqual(factory_calls, [model])
            self.assertEqual(
                model.calls,
                [
                    ("generate", "completion"),
                    ("critique", "completion"),
                ],
            )

    def test_workspace_completion_validator(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {
                (
                    "design/initial/v0001/"
                    "initial-design.json"
                ): initial_design(),
                (
                    "design/series-plans/"
                    "series-plan-v0001/"
                    "series-plan.json"
                ): series_plan(),
                (
                    "handoffs/handoff-v01/"
                    "handoff.json"
                ): handoffs()[0],
            }
            generation = current_generation()
            for name, value in generation.items():
                paths[
                    f"generations/{GENERATION_ID}/{name}"
                ] = value

            result = {
                "schema_version": 1,
                "completion_id": "completion-000001",
                "basis_generation_id": GENERATION_ID,
                "precheck_summary": {
                    "all_volumes_complete": True,
                    "all_planned_scenes_committed": True,
                    "unfinished_scene_work": False,
                },
                **completion_candidate(),
                "created_at": COMPLETION_AT,
            }
            paths[
                "completion/completion-000001/result.json"
            ] = result

            for relative, value in paths.items():
                path = root / relative
                path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
                path.write_text(
                    json.dumps(
                        value,
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            _validate_completion_artifacts(root)

            result["basis_generation_id"] = (
                "gen-999999"
            )
            (
                root
                / "completion/completion-000001/result.json"
            ).write_text(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                _validate_completion_artifacts(root)


if __name__ == "__main__":
    unittest.main()
