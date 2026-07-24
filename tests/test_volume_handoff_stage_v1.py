"""Storycraft V1 volume_handoff Stage試験。"""
from __future__ import annotations

from copy import deepcopy
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


class AcceptModel:
    def __init__(
        self,
        candidate: dict | None = None,
    ) -> None:
        if candidate is None:
            raise AssertionError(
                "AcceptModelにはWorkspaceに対応する"
                "Candidateが必要です"
            )
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


def candidate_for_workspace(
    workspace: Path,
) -> dict:
    """巻末GenerationのAuthorityに一致するCandidateを作る。"""
    run_state = RunStateStore(workspace).load()
    generation_id = run_state["current_generation_id"]
    if not isinstance(generation_id, str):
        raise AssertionError(run_state)

    generation_state = json.loads(
        (
            workspace
            / "generations"
            / generation_id
            / "state.json"
        ).read_text(encoding="utf-8")
    )

    characters = generation_state["characters"]
    relationships = generation_state["relationships"]
    threads = generation_state["threads"]

    resolved_threads = sorted(
        thread_id
        for thread_id, record in threads.items()
        if record.get("status") == "resolved"
    )
    open_threads = sorted(
        thread_id
        for thread_id, record in threads.items()
        if record.get("status") != "resolved"
    )

    return {
        "character_states": {
            character_id: (
                f"{character_id}の巻末状態を"
                "巻末Generationから引き継ぐ。"
            )
            for character_id in sorted(characters)
        },
        "relationship_states": {
            relationship_id: (
                f"{relationship_id}の巻末状態を"
                "巻末Generationから引き継ぐ。"
            )
            for relationship_id in sorted(relationships)
        },
        "resolved_threads": resolved_threads,
        "open_threads": open_threads,
        "new_constraints": [],
        "ending_progress": (
            "第一巻で予定された変化が進行した。"
        ),
        "next_volume_requirements": [
            "巻末Generationの未解決状態を"
            "次巻へ引き継ぐ。",
        ],
        "issues": [],
    }


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
    def test_adopts_handoff_and_advances_to_next_volume(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = (
                prepare_volume_handoff_workspace(
                    temporary
                )
            )
            model = AcceptModel(
                candidate_for_workspace(workspace)
            )

            state = VolumeHandoffStageService(
                workspace
            ).run(
                model,
                updated_at=HANDOFF_AT,
            )

            self.assertEqual(
                state["current_stage"],
                "volume_plan",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000002",
            )
            self.assertEqual(
                state["current_target"],
                {
                    "series": "ws-test-0001",
                    "series_plan_id": (
                        "series-plan-0001"
                    ),
                    "volume_number": 2,
                    "basis_generation_id": (
                        "gen-000002"
                    ),
                },
            )
            self.assertIsNone(
                state["active_candidate"]
            )
            self.assertIsNone(
                state["active_scene_id"]
            )
            self.assertIsNone(
                state["pending_commit"]
            )

            path = (
                workspace
                / "handoffs/handoff-v01/handoff.json"
            )
            handoff = json.loads(
                path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                handoff["handoff_id"],
                "handoff-v01",
            )
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
            self.assertEqual(
                handoff["created_at"],
                HANDOFF_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "volume_handoff"),
                    ("critique", "volume_handoff"),
                ],
            )
            context = model.contexts[0]
            self.assertEqual(
                context["target_volume_number"],
                1,
            )
            self.assertFalse(
                context["is_final_volume"]
            )
            self.assertEqual(
                len(context["completed_scenes"]),
                1,
            )
            self.assertEqual(
                context["current_generation"][
                    "commit.json"
                ]["source_artifact_id"],
                "scene-v01-c001-s001",
            )

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

    def test_missing_final_scene_is_rejected_before_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = (
                prepare_volume_handoff_workspace(
                    temporary
                )
            )
            shutil.rmtree(
                workspace
                / "scenes/scene-v01-c001-s001"
            )
            model = AcceptModel(
                candidate_for_workspace(workspace)
            )

            with self.assertRaisesRegex(
                ContractError,
                "確定directory",
            ):
                VolumeHandoffStageService(
                    workspace
                ).run(
                    model,
                    updated_at=HANDOFF_AT,
                )

            self.assertEqual(model.calls, [])

    def test_invalid_thread_partition_blocks_candidate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = (
                prepare_volume_handoff_workspace(
                    temporary
                )
            )
            candidate = candidate_for_workspace(
                workspace
            )
            if not candidate["open_threads"]:
                raise AssertionError(
                    "試験には未解決Threadが必要です"
                )
            moved_thread = candidate[
                "open_threads"
            ].pop(0)
            candidate["resolved_threads"].append(
                moved_thread
            )
            model = AcceptModel(candidate)

            state = VolumeHandoffStageService(
                workspace
            ).run(
                model,
                updated_at=HANDOFF_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "manual_review_required",
            )
            self.assertEqual(
                state["last_error"]["code"],
                "VOLUME_HANDOFF_GENERATION_INVALID",
            )
            self.assertFalse(
                (
                    workspace
                    / "handoffs/handoff-v01"
                ).exists()
            )

    def test_existing_different_handoff_is_not_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, committed = (
                prepare_volume_handoff_workspace(
                    temporary
                )
            )

            original = candidate_for_workspace(
                workspace
            )
            VolumeHandoffStageService(
                workspace
            ).run(
                AcceptModel(original),
                updated_at=HANDOFF_AT,
            )

            # Crash相当としてStage遷移前stateへ戻す。
            RunStateStore(workspace).save(committed)

            changed = deepcopy(original)
            changed["ending_progress"] = (
                "姉妹の対話は始まったが、"
                "信頼回復には至っていない。"
            )

            with self.assertRaisesRegex(
                ContractError,
                "上書き",
            ):
                VolumeHandoffStageService(
                    workspace
                ).run(
                    AcceptModel(changed),
                    updated_at=HANDOFF_RETRY_AT,
                )

            handoff = json.loads(
                (
                    workspace
                    / "handoffs/handoff-v01/handoff.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                handoff["ending_progress"],
                original["ending_progress"],
            )

    def test_workflow_dispatches_model_stage(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _ = (
                prepare_volume_handoff_workspace(
                    temporary
                )
            )
            model = AcceptModel(
                candidate_for_workspace(workspace)
            )
            factory_calls: list[object] = []

            state = V1WorkflowService(
                workspace,
                model_factory=lambda: (
                    factory_calls.append(model)
                    or model
                ),
            ).step(
                updated_at=HANDOFF_AT,
            )

            self.assertEqual(
                state["current_stage"],
                "volume_plan",
            )
            self.assertEqual(factory_calls, [model])
            self.assertEqual(
                model.calls,
                [
                    ("generate", "volume_handoff"),
                    ("critique", "volume_handoff"),
                ],
            )


if __name__ == "__main__":
    unittest.main()
