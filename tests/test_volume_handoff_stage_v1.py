"""Storycraft V1 volume_handoff Stage試験。"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from storycraft.run_state import RunStateStore
from storycraft.scene_commit_stage import (
    SceneCommitStageService,
)
from storycraft.series_contracts import ContractError
from storycraft.volume_handoff_stage import (
    VolumeHandoffStageService,
    determine_volume_handoff_transition,
)
from storycraft.v1_workflow import V1WorkflowService
from storycraft.workspace import validate_workspace_layout

from tests.test_scene_commit_stage_v1 import (
    COMMIT_AT,
    create_scene_commit_workspace,
)


HANDOFF_AT = "2026-07-24T11:20:00Z"
HANDOFF_RETRY_AT = "2026-07-24T11:21:00Z"


def prepare_volume_handoff_workspace(
    temporary: str,
) -> tuple[Path, dict]:
    workspace = create_scene_commit_workspace(temporary)

    # Scene Commit共通helperは複数Chapter・Sceneの
    # 遷移試験用データを持つ。Handoff試験では
    # 一章・一Scene完結のVolumeへ縮小する。
    volume_plan_path = (
        workspace
        / "design/volume-plans"
        / "v01-v0001"
        / "volume-plan.json"
    )
    volume_plan = json.loads(
        volume_plan_path.read_text(encoding="utf-8")
    )
    volume_plan["chapter_summaries"] = (
        volume_plan["chapter_summaries"][:1]
    )
    volume_plan_path.write_text(
        json.dumps(
            volume_plan,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    chapter_plan_path = (
        workspace
        / "design/chapter-plans"
        / "v01-c001-v0001"
        / "chapter-plan.json"
    )
    chapter_plan = json.loads(
        chapter_plan_path.read_text(encoding="utf-8")
    )
    chapter_plan["scene_summaries"] = (
        chapter_plan["scene_summaries"][:1]
    )
    chapter_plan_path.write_text(
        json.dumps(
            chapter_plan,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    state = SceneCommitStageService(workspace).run(
        updated_at=COMMIT_AT,
    )
    if state["current_stage"] != "volume_handoff":
        raise AssertionError(state)
    return workspace, state


class VolumeHandoffStageV1Tests(unittest.TestCase):
    def test_run_has_no_model_parameter(self) -> None:
        from inspect import signature

        self.assertNotIn(
            "model",
            signature(VolumeHandoffStageService.run).parameters,
        )

    def test_derives_handoff_and_advances_to_next_volume(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = prepare_volume_handoff_workspace(
                temporary
            )
            counters_path = workspace / "runtime/counters.json"
            before = json.loads(
                counters_path.read_text(encoding="utf-8")
            )

            state = VolumeHandoffStageService(
                workspace
            ).run(updated_at=HANDOFF_AT)

            self.assertEqual(
                state["current_stage"],
                "volume_plan",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000002",
            )
            self.assertIsNone(state["active_candidate"])
            self.assertIsNone(state["active_scene_id"])
            self.assertIsNone(state["pending_commit"])

            handoff = json.loads(
                (
                    workspace
                    / "handoffs/handoff-v01/handoff.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(handoff["handoff_id"], "handoff-v01")
            self.assertEqual(
                handoff["basis_generation_id"],
                "gen-000002",
            )
            self.assertEqual(
                handoff["completed_chapter_ids"],
                ["chapter-v01-c001"],
            )
            self.assertEqual(
                handoff["completed_scene_ids"],
                ["scene-v01-c001-s001"],
            )

            after = json.loads(
                counters_path.read_text(encoding="utf-8")
            )
            for key in (
                "next_candidate",
                "next_review",
                "next_revision",
            ):
                self.assertEqual(after[key], before[key])

            validate_workspace_layout(workspace)

    def test_final_volume_transition(self) -> None:
        stage, target = (
            determine_volume_handoff_transition(
                state={
                    "workspace_id": "ws-test-0001",
                },
                series_plan={
                    "series_plan_id": (
                        "series-plan-0001"
                    ),
                    "volume_count": 1,
                },
                volume_number=1,
                basis_generation_id="gen-000002",
            )
        )

        self.assertEqual(stage.value, "completion")
        self.assertEqual(
            target,
            {
                "series": "ws-test-0001",
                "series_plan_id": "series-plan-0001",
                "volume_number": 1,
                "basis_generation_id": "gen-000002",
                "final_handoff_id": "handoff-v01",
            },
        )

    def test_missing_final_scene_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = prepare_volume_handoff_workspace(
                temporary
            )
            shutil.rmtree(
                workspace / "scenes/scene-v01-c001-s001"
            )

            with self.assertRaisesRegex(
                ContractError,
                "確定directory",
            ):
                VolumeHandoffStageService(
                    workspace
                ).run(updated_at=HANDOFF_AT)

    def test_existing_corrupt_handoff_is_not_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, committed = prepare_volume_handoff_workspace(
                temporary
            )
            VolumeHandoffStageService(
                workspace
            ).run(updated_at=HANDOFF_AT)

            path = workspace / "handoffs/handoff-v01/handoff.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["ending_progress"] = "改変されたHandoff。"
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            RunStateStore(workspace).save(committed)

            with self.assertRaises(ContractError):
                VolumeHandoffStageService(
                    workspace
                ).run(updated_at=HANDOFF_RETRY_AT)

            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))[
                    "ending_progress"
                ],
                "改変されたHandoff。",
            )

    def test_workflow_dispatches_without_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = prepare_volume_handoff_workspace(
                temporary
            )
            factory_calls: list[object] = []

            state = V1WorkflowService(
                workspace,
                model_factory=lambda: factory_calls.append(
                    object()
                ),
            ).step(updated_at=HANDOFF_AT)

            self.assertEqual(
                state["current_stage"],
                "volume_plan",
            )
            self.assertEqual(factory_calls, [])



if __name__ == "__main__":
    unittest.main()
