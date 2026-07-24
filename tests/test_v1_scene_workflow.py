"""V1 Workflowによる一Scene縦断統合試験。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from storycraft.v1_workflow import V1WorkflowService
from storycraft.workspace import validate_workspace_layout

from tests.test_scene_card_stage_v1 import matching_card
from tests.test_scene_continuity_stage_v1 import (
    matching_continuity,
)
from tests.test_scene_plan_schema_v1 import (
    scene_plan_candidate,
)
from tests.test_scene_plan_stage_v1 import (
    create_scene_plan_workspace,
)
from tests.test_scene_prose_stage_v1 import PROSE


PLAN_AT = "2026-07-24T08:19:00Z"
CARD_AT = "2026-07-24T08:20:00Z"
PROSE_AT = "2026-07-24T09:20:00Z"
CONTINUITY_AT = "2026-07-24T10:10:00Z"
COMMIT_AT = "2026-07-24T10:11:00Z"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class OneSceneModel:
    """一Scene縦断に必要な全Model operationを提供する。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def generate(
        self,
        stage: str,
        context: dict,
    ) -> dict:
        self.calls.append(("generate", stage))

        candidates = {
            "scene_plan": scene_plan_candidate(),
            "scene_card_v1": matching_card(),
            "scene_continuity_v1": (
                matching_continuity()
            ),
        }
        if stage not in candidates:
            raise AssertionError(
                f"unexpected generate stage: {stage}"
            )
        return deepcopy(candidates[stage])

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

    def generate_prose(
        self,
        stage: str,
        context: dict,
    ) -> str:
        self.calls.append(("generate", stage))
        return PROSE

    def critique_prose(
        self,
        stage: str,
        candidate: str,
        context: dict,
    ) -> dict:
        self.calls.append(("critique", stage))
        return {"issues": []}

    def revision_prose(
        self,
        stage: str,
        candidate: str,
        critique: dict,
        context: dict,
    ) -> str:
        raise AssertionError("revision must not be called")


class V1SceneWorkflowTest(unittest.TestCase):
    def test_scene_plan_to_next_scene_plan(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_plan_workspace(
                temporary
            )
            model = OneSceneModel()
            factory_calls: list[OneSceneModel] = []

            def factory() -> OneSceneModel:
                factory_calls.append(model)
                return model

            workflow = V1WorkflowService(
                workspace,
                model_factory=factory,
            )

            states = [
                workflow.step(updated_at=PLAN_AT),
                workflow.step(updated_at=CARD_AT),
                workflow.step(updated_at=PROSE_AT),
                workflow.step(updated_at=CONTINUITY_AT),
                workflow.step(updated_at=COMMIT_AT),
            ]

            self.assertEqual(
                [
                    state["current_stage"]
                    for state in states
                ],
                [
                    "scene_card",
                    "scene_prose",
                    "scene_continuity",
                    "scene_commit",
                    "scene_plan",
                ],
            )

            self.assertEqual(
                [
                    state["current_generation_id"]
                    for state in states
                ],
                [
                    "gen-000001",
                    "gen-000001",
                    "gen-000001",
                    "gen-000001",
                    "gen-000002",
                ],
            )

            # Scene Commitはcode-onlyなのでfactoryは呼ばれない。
            self.assertEqual(
                factory_calls,
                [model, model, model, model],
            )
            self.assertEqual(
                model.calls,
                [
                    ("generate", "scene_plan"),
                    ("critique", "scene_plan"),
                    ("generate", "scene_card_v1"),
                    ("critique", "scene_card_v1"),
                    ("generate", "scene_prose_v1"),
                    ("critique", "scene_prose_v1"),
                    (
                        "generate",
                        "scene_continuity_v1",
                    ),
                    (
                        "critique",
                        "scene_continuity_v1",
                    ),
                ],
            )

            final_state = states[-1]
            self.assertEqual(
                final_state["current_target"][
                    "volume_number"
                ],
                1,
            )
            self.assertEqual(
                final_state["current_target"][
                    "chapter_number"
                ],
                1,
            )
            self.assertEqual(
                final_state["current_target"][
                    "scene_number"
                ],
                2,
            )
            self.assertEqual(
                final_state["current_target"][
                    "basis_generation_id"
                ],
                "gen-000002",
            )
            self.assertIsNone(
                final_state["active_candidate"]
            )
            self.assertIsNone(
                final_state["active_scene_id"]
            )
            self.assertIsNone(
                final_state["pending_commit"]
            )

            scene_root = (
                workspace
                / "scenes/scene-v01-c001-s001"
            )
            generation_root = (
                workspace / "generations/gen-000002"
            )

            self.assertTrue(scene_root.is_dir())
            self.assertTrue(generation_root.is_dir())

            scene_plan = read_json(
                workspace
                / "design/scene-plans"
                / "v01-c001-s001-v0001"
                / "scene-plan.json"
            )
            scene_card = read_json(
                scene_root / "scene-card.json"
            )
            continuity = read_json(
                scene_root / "continuity.json"
            )
            generation_commit = read_json(
                generation_root / "commit.json"
            )

            self.assertEqual(
                scene_plan["basis_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                scene_card["basis_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                continuity["basis_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                continuity["result_generation_id"],
                "gen-000002",
            )
            self.assertEqual(
                generation_commit[
                    "parent_generation_id"
                ],
                "gen-000001",
            )
            self.assertEqual(
                generation_commit["generation_id"],
                "gen-000002",
            )

            validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
