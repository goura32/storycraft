"""Storycraft Version 1 scene_card Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from storycraft.run_state import RunStateStore
from storycraft.scene_card_stage import SceneCardStageService
from storycraft.scene_plan_stage import ScenePlanStageService
from storycraft.series_contracts import ContractError
from storycraft.workspace import validate_workspace_layout

from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    load_json_from,
)
from tests.test_scene_card_schema_v1 import (
    scene_card_candidate,
)
from tests.test_scene_plan_schema_v1 import (
    scene_plan_candidate,
)
from tests.test_scene_plan_stage_v1 import (
    create_scene_plan_workspace,
)


CARD_AT = "2026-07-24T08:20:00Z"


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


def create_scene_card_workspace(temporary: str) -> Path:
    workspace = create_scene_plan_workspace(temporary)
    ScenePlanStageService(workspace).run(
        AcceptingModel(scene_plan_candidate()),
        updated_at="2026-07-24T08:19:00Z",
    )
    return workspace


def matching_card() -> dict:
    plan = scene_plan_candidate()
    candidate = scene_card_candidate()
    candidate["pov_character_id"] = plan["pov_character_id"]
    candidate["participant_ids"] = deepcopy(
        plan["participant_ids"]
    )
    candidate["location_id"] = plan["location_id"]
    return candidate


class SceneCardStageV1Tests(unittest.TestCase):
    def test_generate_review_adopt_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_card_workspace(temporary)
            model = AcceptingModel(matching_card())

            state = SceneCardStageService(workspace).run(
                model,
                updated_at=CARD_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "scene_card_v1"),
                    ("critique", "scene_card_v1"),
                ],
            )
            self.assertEqual(state["current_stage"], "scene_prose")
            self.assertEqual(
                state["active_scene_id"],
                "scene-v01-c001-s001",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                state["current_target"]["scene_card_version"],
                1,
            )
            self.assertEqual(
                state["current_target"]["scene_id"],
                "scene-v01-c001-s001",
            )

            path = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
                / "scene-card.json"
            )
            adopted = load_json_from(path)
            self.assertEqual(
                adopted["scene_id"],
                "scene-v01-c001-s001",
            )
            self.assertEqual(adopted["version"], 1)
            self.assertEqual(
                adopted["basis_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                adopted["scene_plan_id"],
                "scene-plan-v01-c001-s001",
            )
            self.assertEqual(adopted["created_at"], CARD_AT)
            for key, value in matching_card().items():
                self.assertEqual(adopted[key], value)

            context = model.contexts[0]
            self.assertNotIn("ending", context)
            self.assertNotIn("long_term_arcs", context)
            self.assertEqual(
                {
                    record["character_id"]
                    for record in context[
                        "relevant_design"
                    ]["characters"]
                },
                set(scene_plan_candidate()["participant_ids"]),
            )
            validate_workspace_layout(workspace)

    def test_invalid_candidate_blocks_without_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_card_workspace(temporary)
            invalid = matching_card()
            invalid["allowed_revelations"] = ["know-9999"]

            state = SceneCardStageService(workspace).run(
                AcceptingModel(invalid),
                updated_at=CARD_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertFalse(
                (
                    workspace
                    / "runtime/staging"
                    / "scene-scene-v01-c001-s001"
                ).exists()
            )

    def test_stale_basis_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_card_workspace(temporary)
            store = RunStateStore(workspace)
            state = store.load()
            state["current_target"][
                "basis_generation_id"
            ] = "gen-999999"
            store.save(state)

            with self.assertRaisesRegex(
                ContractError,
                "basis_generation_id",
            ):
                SceneCardStageService(workspace).run(
                    AcceptingModel(matching_card()),
                    updated_at=CARD_AT,
                )

    def test_existing_different_card_cannot_be_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_card_workspace(temporary)
            service = SceneCardStageService(workspace)
            service.run(
                AcceptingModel(matching_card()),
                updated_at=CARD_AT,
            )

            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "scene_card"
            state["current_target"].pop(
                "scene_card_version",
                None,
            )
            state["current_target"].pop("scene_id", None)
            store.save(state)

            changed = matching_card()
            changed["purpose"] = "別のScene目的へ変更する。"

            with self.assertRaises(ContractError):
                service.run(
                    AcceptingModel(changed),
                    updated_at=CARD_AT,
                )

    def test_workspace_rejects_mutated_card(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_card_workspace(temporary)
            SceneCardStageService(workspace).run(
                AcceptingModel(matching_card()),
                updated_at=CARD_AT,
            )
            path = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
                / "scene-card.json"
            )
            adopted = load_json_from(path)
            adopted["pov_character_id"] = "char-9999"
            write_json(path, adopted)

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
