"""Storycraft V1 publication Stage試験。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.publication_builder import (
    build_publication_files,
)
from storycraft.publication_stage import (
    PublicationStageService,
)
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.v1_workflow import V1WorkflowService
from storycraft.workspace import (
    _validate_publication_artifacts,
)

from tests.test_completion_schema_v1 import (
    GENERATION_ID,
    completion_candidate,
)
from tests.test_completion_stage_v1 import (
    create_completion_workspace,
)
from tests.test_publication_builder_v1 import (
    fixture_volumes,
)


PUBLICATION_AT = "2026-07-24T13:00:00Z"


def adopted_completion(
    *,
    status: str = "complete",
) -> dict:
    candidate = completion_candidate()
    candidate["status"] = status

    if status == "complete_with_issues":
        candidate["character_arc_checks"][0][
            "status"
        ] = "partially_satisfied"
        candidate["issues"] = [{
            "category": "minor_arc",
            "description": "人物Arcの余韻が弱い。",
        }]

    return {
        "schema_version": 1,
        "completion_id": "completion-000001",
        "basis_generation_id": GENERATION_ID,
        "precheck_summary": {
            "all_volumes_complete": True,
            "all_planned_scenes_committed": True,
            "unfinished_scene_work": False,
        },
        **candidate,
        "created_at": "2026-07-24T12:20:00Z",
    }


def create_publication_workspace(
    temporary: str,
    *,
    status: str = "complete",
) -> Path:
    workspace = create_completion_workspace(temporary)
    completion = adopted_completion(status=status)

    completion_path = (
        workspace
        / "completion/completion-000001/result.json"
    )
    completion_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    completion_path.write_text(
        json.dumps(
            completion,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    store = RunStateStore(workspace)
    state = store.load()
    state["status"] = "running"
    state["current_stage"] = "publication"
    state["current_target"] = {
        "series": state["workspace_id"],
        "series_plan_id": "series-plan-0001",
        "completion_id": "completion-000001",
        "completion_status": status,
        "basis_generation_id": GENERATION_ID,
    }
    state["active_candidate"] = None
    state["active_scene_id"] = None
    state["pending_commit"] = None
    state["stop_reason"] = None
    state["last_error"] = None
    store.save(state)
    return workspace


def prepared_inputs(
    *,
    status: str = "complete",
) -> dict:
    return {
        "title": "潮騒の記憶",
        "language": "ja",
        "basis_generation_id": GENERATION_ID,
        "completion": adopted_completion(
            status=status
        ),
        "volumes": fixture_volumes(),
    }


class PublicationStageV1Tests(unittest.TestCase):
    def run_stage(
        self,
        workspace: Path,
        *,
        status: str = "complete",
    ) -> tuple[dict, object]:
        service = PublicationStageService(workspace)

        with (
            patch(
                "storycraft.publication_stage."
                "validate_workspace_layout"
            ),
            patch.object(
                service,
                "_prepare_inputs",
                return_value=prepared_inputs(
                    status=status
                ),
            ),
            patch.object(
                service.state_store,
                "save",
                wraps=service.state_store.save,
            ) as save,
        ):
            state = service.run(
                updated_at=PUBLICATION_AT,
            )

        return state, save

    def test_publication_finalizes_and_completes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )

            state, save = self.run_stage(workspace)

            self.assertEqual(state["status"], "completed")
            self.assertEqual(
                state["current_stage"],
                "publication",
            )
            self.assertEqual(
                state["current_publication_id"],
                "pub-000001",
            )
            self.assertEqual(
                state["current_target"][
                    "publication_id"
                ],
                "pub-000001",
            )
            self.assertIsNone(state["pending_commit"])

            phases = []
            for call in save.call_args_list:
                pending = call.args[0]["pending_commit"]
                phases.append(
                    None
                    if pending is None
                    else pending["phase"]
                )

            self.assertEqual(
                phases,
                [
                    "prepared",
                    "publication_finalized",
                    None,
                ],
            )

    def test_publication_files_match_builder(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self.run_stage(workspace)

            expected = build_publication_files(
                publication_id="pub-000001",
                title="潮騒の記憶",
                language="ja",
                basis_generation_id=GENERATION_ID,
                completion=adopted_completion(),
                volumes=fixture_volumes(),
                created_at=PUBLICATION_AT,
            )
            final = workspace / "publications/pub-000001"

            for name, value in expected.items():
                path = final / name

                if isinstance(value, dict):
                    actual = json.loads(
                        path.read_text(encoding="utf-8")
                    )
                else:
                    actual = path.read_text(
                        encoding="utf-8"
                    )

                self.assertEqual(actual, value, name)

    def test_complete_with_issues_is_published(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary,
                status="complete_with_issues",
            )

            state, _ = self.run_stage(
                workspace,
                status="complete_with_issues",
            )

            self.assertEqual(state["status"], "completed")
            metadata = json.loads(
                (
                    workspace
                    / "publications/pub-000001/"
                    / "metadata.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                metadata["completion_status"],
                "complete_with_issues",
            )

    def test_incomplete_is_rejected_before_pending(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            service = PublicationStageService(workspace)
            inputs = prepared_inputs()
            inputs["completion"]["status"] = "incomplete"

            with (
                patch(
                    "storycraft.publication_stage."
                    "validate_workspace_layout"
                ),
                patch.object(
                    service,
                    "_prepare_inputs",
                    return_value=inputs,
                ),
                self.assertRaisesRegex(
                    ContractError,
                    "公開可能Completion",
                ),
            ):
                service.run(updated_at=PUBLICATION_AT)

            state = service.state_store.load()
            self.assertIsNone(state["pending_commit"])
            self.assertFalse(
                (
                    workspace
                    / "publications/pub-000001"
                ).exists()
            )

    def test_existing_final_is_not_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            final = (
                workspace / "publications/pub-000001"
            )
            final.mkdir()

            with self.assertRaisesRegex(
                ContractError,
                "上書き",
            ):
                self.run_stage(workspace)

            self.assertEqual(list(final.iterdir()), [])

    def test_workflow_uses_no_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            model_calls: list[object] = []

            with (
                patch(
                    "storycraft.v1_workflow."
                    "validate_workspace_layout"
                ),
                patch(
                    "storycraft.publication_stage."
                    "validate_workspace_layout"
                ),
                patch.object(
                    PublicationStageService,
                    "_prepare_inputs",
                    return_value=prepared_inputs(),
                ),
            ):
                state = V1WorkflowService(
                    workspace,
                    model_factory=lambda: (
                        model_calls.append(object())
                    ),
                ).step(updated_at=PUBLICATION_AT)

            self.assertEqual(state["status"], "completed")
            self.assertEqual(model_calls, [])

    def test_workspace_publication_validator(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_publication_workspace(
                temporary
            )
            self.run_stage(workspace)

            _validate_publication_artifacts(workspace)

            completion_copy = (
                workspace
                / "publications/pub-000001/"
                / "completion.json"
            )
            value = json.loads(
                completion_copy.read_text(
                    encoding="utf-8"
                )
            )
            value["summary"] = "改変された完結判定。"
            completion_copy.write_text(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                _validate_publication_artifacts(
                    workspace
                )


if __name__ == "__main__":
    unittest.main()
