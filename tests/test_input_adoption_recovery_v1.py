"""Keywords Input Candidate Adoption Recovery試験。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.input_stage import InputStageService
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.v1_workflow import V1WorkflowService
from storycraft.workspace import (
    create_workspace_from_keywords,
)

from tests.test_input_stage_v1 import (
    AcceptingModel,
    CREATED_AT,
    UPDATED_AT,
)


ROOT = Path(__file__).parent.parent


def load_json(relative_path: str) -> dict:
    return json.loads(
        (
            ROOT / relative_path
        ).read_text(encoding="utf-8")
    )


def create_keywords_workspace(
    temporary: str,
) -> tuple[Path, dict]:
    workspace = Path(temporary) / "novel"

    keywords = load_json(
        "tests/fixtures/keywords/valid.json"
    )
    config = load_json(
        "tests/fixtures/workspace/config.json"
    )
    generated = load_json(
        "tests/fixtures/brief/valid.json"
    )
    generated = deepcopy(generated)
    generated["source_type"] = "keywords"
    generated["source_reference"] = (
        "input/keywords.json"
    )
    generated["avoid"] = list(
        keywords["avoid"]
    )
    generated["language"] = (
        keywords["language"]
    )
    generated["volume_count"] = (
        keywords["volume_hint"]
    )

    create_workspace_from_keywords(
        workspace,
        workspace_id="ws-input-recovery",
        keywords=keywords,
        config=config,
        created_at=CREATED_AT,
    )

    return workspace, generated


class InputAdoptionRecoveryV1Tests(
    unittest.TestCase
):
    def test_prepared_recovery_finishes_without_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            (
                workspace,
                generated,
            ) = create_keywords_workspace(
                temporary
            )

            service = InputStageService(workspace)

            from storycraft import input_stage

            original_adopt = (
                input_stage._adopt_generated_brief
            )

            def adopt_then_crash(
                *args: object,
                **kwargs: object,
            ) -> None:
                original_adopt(*args, **kwargs)
                raise RuntimeError(
                    "crash after Brief adoption"
                )

            with (
                patch(
                    "storycraft.input_stage."
                    "_adopt_generated_brief",
                    side_effect=adopt_then_crash,
                ),
                self.assertRaises(RuntimeError),
            ):
                service.run(
                    AcceptingModel(generated),
                    updated_at=UPDATED_AT,
                )

            crashed = RunStateStore(
                workspace
            ).load()

            self.assertEqual(
                crashed["current_stage"],
                "input",
            )
            self.assertEqual(
                crashed["pending_commit"],
                {
                    "kind": "candidate_adoption",
                    "target_id": (
                        "candidate-000001"
                    ),
                    "stage": "input",
                    "version": 1,
                    "phase": "prepared",
                },
            )
            self.assertEqual(
                crashed["active_candidate"],
                {
                    "kind": "input",
                    "candidate_id": (
                        "candidate-000001"
                    ),
                    "version": 1,
                },
            )
            self.assertEqual(
                load_json_from(
                    workspace / "input/brief.json"
                ),
                generated,
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
                "initial_concept",
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
            (
                workspace,
                generated,
            ) = create_keywords_workspace(
                temporary
            )

            service = InputStageService(workspace)
            original_save = (
                service.state_store.save
            )

            def crash_before_final_state(
                state: dict,
            ) -> None:
                if (
                    state["current_stage"]
                    == "initial_concept"
                    and state["pending_commit"] is None
                ):
                    raise RuntimeError(
                        "crash before Input state advance"
                    )
                original_save(state)

            with (
                patch.object(
                    service.state_store,
                    "save",
                    side_effect=crash_before_final_state,
                ),
                self.assertRaises(RuntimeError),
            ):
                service.run(
                    AcceptingModel(generated),
                    updated_at=UPDATED_AT,
                )

            crashed = RunStateStore(
                workspace
            ).load()

            self.assertEqual(
                crashed["current_stage"],
                "input",
            )
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
                "initial_concept",
            )
            self.assertIsNone(
                recovered["pending_commit"]
            )
            self.assertEqual(model_calls, [])

    def test_conflicting_brief_is_rejected_without_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            (
                workspace,
                generated,
            ) = create_keywords_workspace(
                temporary
            )

            service = InputStageService(workspace)

            from storycraft import input_stage

            original_adopt = (
                input_stage._adopt_generated_brief
            )

            def adopt_then_crash(
                *args: object,
                **kwargs: object,
            ) -> None:
                original_adopt(*args, **kwargs)
                raise RuntimeError("crash")

            with (
                patch(
                    "storycraft.input_stage."
                    "_adopt_generated_brief",
                    side_effect=adopt_then_crash,
                ),
                self.assertRaises(RuntimeError),
            ):
                service.run(
                    AcceptingModel(generated),
                    updated_at=UPDATED_AT,
                )

            path = workspace / "input/brief.json"
            conflicting = load_json_from(path)
            conflicting["title"] = (
                "競合する企画タイトル"
            )
            path.write_text(
                json.dumps(
                    conflicting,
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


def load_json_from(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


if __name__ == "__main__":
    unittest.main()
