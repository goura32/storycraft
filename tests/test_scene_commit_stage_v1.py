"""Storycraft Version 1 scene_commit Stage契約。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from storycraft.run_state import RunStateStore
from storycraft.scene_commit_stage import (
    SceneCommitStageService,
    determine_scene_commit_transition,
)
from storycraft.scene_continuity_stage import (
    SceneContinuityStageService,
)
from storycraft.series_contracts import ContractError
from storycraft.stages import Stage
from storycraft.workspace import validate_workspace_layout

from tests.support.workspace_fixtures import (
    clone_cached_workspace,
)

from tests.test_initial_world_stage_v1 import (
    load_json_from,
)
from tests.test_scene_continuity_stage_v1 import (
    AcceptingContinuityModel,
    CONTINUITY_AT,
    create_scene_continuity_workspace,
    matching_continuity,
)


COMMIT_AT = "2026-07-24T10:11:00Z"


def _build_scene_commit_workspace(
    temporary: str,
) -> Path:
    workspace = create_scene_continuity_workspace(
        temporary
    )
    SceneContinuityStageService(workspace).run(
        AcceptingContinuityModel(matching_continuity()),
        updated_at=CONTINUITY_AT,
    )
    return workspace


def create_scene_commit_workspace(
    temporary: str,
) -> Path:
    workspace, payload = clone_cached_workspace(
        key="scene-commit-v1",
        temporary=temporary,
        builder=_build_scene_commit_workspace,
    )

    if payload is not None:
        raise AssertionError(
            "scene commit fixture payloadが不正です"
        )

    return workspace


def transition_state() -> dict:
    return {
        "workspace_id": "ws-test-0001",
        "current_target": {
            "volume_number": 1,
            "chapter_number": 1,
            "scene_number": 1,
        },
    }


def series_plan() -> dict:
    return {
        "series_plan_id": "series-plan-0001",
    }


def volume_plan(chapters: int = 2) -> dict:
    return {
        "volume_plan_id": "volume-plan-v01",
        "chapter_summaries": [
            {
                "chapter_number": number,
                "purpose": f"Chapter {number}",
            }
            for number in range(1, chapters + 1)
        ],
    }


def chapter_plan(scenes: int = 2) -> dict:
    return {
        "chapter_plan_id": "chapter-plan-v01-c001",
        "scene_summaries": [
            {
                "scene_number": number,
                "purpose": f"Scene {number}",
            }
            for number in range(1, scenes + 1)
        ],
    }


class SceneCommitStageV1Test(unittest.TestCase):
    def test_commit_finalizes_scene_and_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )

            state = SceneCommitStageService(
                workspace
            ).run(
                updated_at=COMMIT_AT,
            )

            self.assertEqual(
                state["current_stage"],
                "scene_plan",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000002",
            )
            self.assertIsNone(state["active_scene_id"])
            self.assertIsNone(state["pending_commit"])
            self.assertEqual(
                state["current_target"],
                {
                    "series": "ws-test-0001",
                    "series_plan_id": "series-plan-0001",
                    "volume_plan_id": "volume-plan-v01",
                    "chapter_plan_id": (
                        "chapter-plan-v01-c001"
                    ),
                    "volume_number": 1,
                    "chapter_number": 1,
                    "scene_number": 2,
                    "basis_generation_id": "gen-000002",
                },
            )

            scene_root = (
                workspace
                / "scenes/scene-v01-c001-s001"
            )
            self.assertEqual(
                {
                    path.name
                    for path in scene_root.iterdir()
                },
                {
                    "scene-card.json",
                    "prose.md",
                    "continuity.json",
                    "commit.json",
                },
            )
            self.assertFalse(
                (
                    workspace
                    / "runtime/staging"
                    / "scene-scene-v01-c001-s001"
                ).exists()
            )

            commit = load_json_from(
                scene_root / "commit.json"
            )
            self.assertEqual(
                commit["parent_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                commit["result_generation_id"],
                "gen-000002",
            )
            self.assertEqual(
                commit["committed_at"],
                CONTINUITY_AT,
            )

            generation_root = (
                workspace / "generations/gen-000002"
            )
            self.assertEqual(
                {
                    path.name
                    for path in generation_root.iterdir()
                },
                {
                    "canon.json",
                    "state.json",
                    "evidence.json",
                    "commit.json",
                },
            )
            self.assertFalse(
                (
                    workspace
                    / "runtime/staging"
                    / "generation-gen-000002"
                ).exists()
            )

            generated_state = load_json_from(
                generation_root / "state.json"
            )
            self.assertEqual(
                generated_state["characters"][
                    "char-0001"
                ]["current_location_id"],
                "loc-0002",
            )
            parent_state = load_json_from(
                workspace
                / "generations/gen-000001/state.json"
            )
            self.assertEqual(
                parent_state["characters"]["char-0001"][
                    "current_location_id"
                ],
                "loc-0001",
            )

            generation_commit = load_json_from(
                generation_root / "commit.json"
            )
            self.assertEqual(
                generation_commit["source_artifact_id"],
                "scene-v01-c001-s001",
            )
            self.assertEqual(
                generation_commit["created_at"],
                CONTINUITY_AT,
            )

            validate_workspace_layout(workspace)

    def test_missing_scene_staging_is_rebuilt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            staging = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
            )
            shutil.rmtree(staging)

            state = SceneCommitStageService(
                workspace
            ).run(
                updated_at=COMMIT_AT,
            )

            self.assertEqual(
                state["current_generation_id"],
                "gen-000002",
            )
            self.assertTrue(
                (
                    workspace
                    / "scenes/scene-v01-c001-s001"
                ).is_dir()
            )

    def test_incomplete_scene_staging_is_orphaned(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            staging = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
            )
            (staging / "continuity.json").unlink()

            state = SceneCommitStageService(
                workspace
            ).run(
                updated_at=COMMIT_AT,
            )

            self.assertEqual(
                state["current_generation_id"],
                "gen-000002",
            )
            orphans = list(
                (
                    workspace / "runtime/orphans"
                ).glob(
                    "*-scene-scene-v01-c001-s001*"
                )
            )
            self.assertEqual(len(orphans), 1)
            self.assertFalse(
                (
                    orphans[0] / "continuity.json"
                ).exists()
            )

    def test_pending_phases_are_saved_in_order(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            service = SceneCommitStageService(workspace)

            with patch.object(
                service.state_store,
                "save",
                wraps=service.state_store.save,
            ) as save:
                service.run(updated_at=COMMIT_AT)

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
                    "scene_finalized",
                    "generation_finalized",
                    None,
                ],
            )

    def test_target_result_generation_must_match(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            store = RunStateStore(workspace)
            state = store.load()
            state["current_target"][
                "result_generation_id"
            ] = "gen-000003"
            store.save(state)

            with self.assertRaisesRegex(
                ContractError,
                "result_generation_id",
            ):
                SceneCommitStageService(workspace).run(
                    updated_at=COMMIT_AT,
                )

            self.assertFalse(
                (
                    workspace
                    / "generations/gen-000002"
                ).exists()
            )

    def test_existing_scene_final_is_not_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_commit_workspace(
                temporary
            )
            final = (
                workspace
                / "scenes/scene-v01-c001-s001"
            )
            final.mkdir()

            with self.assertRaisesRegex(
                ContractError,
                "確定済みScene",
            ):
                SceneCommitStageService(workspace).run(
                    updated_at=COMMIT_AT,
                )

            self.assertTrue(final.is_dir())

    def test_transition_to_next_scene(self) -> None:
        stage, target = determine_scene_commit_transition(
            state=transition_state(),
            series_plan=series_plan(),
            volume_plan=volume_plan(2),
            chapter_plan=chapter_plan(2),
            result_generation_id="gen-000002",
        )

        self.assertIs(stage, Stage.SCENE_PLAN)
        self.assertEqual(target["scene_number"], 2)
        self.assertEqual(
            target["basis_generation_id"],
            "gen-000002",
        )

    def test_transition_to_next_chapter(self) -> None:
        stage, target = determine_scene_commit_transition(
            state=transition_state(),
            series_plan=series_plan(),
            volume_plan=volume_plan(2),
            chapter_plan=chapter_plan(1),
            result_generation_id="gen-000002",
        )

        self.assertIs(stage, Stage.CHAPTER_PLAN)
        self.assertEqual(target["chapter_number"], 2)
        self.assertNotIn("chapter_plan_id", target)
        self.assertNotIn("scene_number", target)

    def test_transition_to_volume_handoff(self) -> None:
        stage, target = determine_scene_commit_transition(
            state=transition_state(),
            series_plan=series_plan(),
            volume_plan=volume_plan(1),
            chapter_plan=chapter_plan(1),
            result_generation_id="gen-000002",
        )

        self.assertIs(stage, Stage.VOLUME_HANDOFF)
        self.assertEqual(target["volume_number"], 1)
        self.assertEqual(
            target["basis_generation_id"],
            "gen-000002",
        )
        self.assertNotIn("chapter_number", target)


if __name__ == "__main__":
    unittest.main()
