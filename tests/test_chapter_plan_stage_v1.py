"""Storycraft Version 1 chapter_plan Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from storycraft.chapter_plan_stage import (
    ChapterPlanStageService,
)
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.volume_plan_stage import (
    VolumePlanStageService,
)
from storycraft.workspace import validate_workspace_layout

from tests.test_chapter_plan_schema_v1 import (
    chapter_plan_candidate,
)
from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    load_json_from,
)
from tests.test_volume_plan_schema_v1 import (
    volume_plan_candidate,
)
from tests.test_volume_plan_stage_v1 import (
    create_volume_plan_workspace,
)


PLAN_AT = "2026-07-24T06:12:00Z"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def chapter_two_candidate() -> dict:
    return {
        "chapter_purpose": (
            "灯台で凪と再会し、沈黙の理由を探る。"
        ),
        "starting_conditions": [
            "澪は灯台火災を調べると決めている。",
            "凪は灯台にいるが、真相を語ることを避けている。",
        ],
        "ending_changes": [
            "澪と凪が火災について限定的な対話を始める。",
            "澪が凪の沈黙に別の理由があると気づく。",
        ],
        "scene_summaries": [
            {
                "scene_number": 1,
                "purpose": "灯台で姉妹を再会させる。",
            },
            {
                "scene_number": 2,
                "purpose": (
                    "火災当日の話題を出し、凪の反応を確かめる。"
                ),
            },
        ],
        "required_revelations": [],
        "constraints": [
            "火災が事故ではない事実はまだ確定させない。",
            "姉妹の信頼を完全には回復させない。",
        ],
    }


def create_chapter_plan_workspace(
    temporary: str,
) -> Path:
    workspace = create_volume_plan_workspace(temporary)
    VolumePlanStageService(workspace).run(
        AcceptingModel(volume_plan_candidate()),
        updated_at="2026-07-24T06:10:00Z",
    )
    return workspace


def prepare_second_chapter_workspace(
    temporary: str,
) -> Path:
    workspace = create_chapter_plan_workspace(temporary)
    ChapterPlanStageService(workspace).run(
        AcceptingModel(chapter_plan_candidate()),
        updated_at=PLAN_AT,
    )

    source = workspace / "generations/gen-000001"
    destination = workspace / "generations/gen-000002"
    shutil.copytree(source, destination)

    for name in (
        "canon.json",
        "state.json",
        "evidence.json",
        "commit.json",
    ):
        value = load_json_from(destination / name)
        value["generation_id"] = "gen-000002"
        if name == "commit.json":
            value.update({
                "parent_generation_id": "gen-000001",
                "commit_type": "scene",
                "source_artifact_type": "scene",
                "source_artifact_id": "scene-v01-c001-s001",
                "summary": "第一章の最終Sceneを確定。",
                "changed_targets": ["state"],
                "created_at": "2026-07-24T06:13:00Z",
            })
        write_json(destination / name, value)

    store = RunStateStore(workspace)
    state = store.load()
    state["status"] = "running"
    state["current_stage"] = "chapter_plan"
    state["current_target"] = {
        "series": state["workspace_id"],
        "series_plan_id": "series-plan-0001",
        "volume_plan_id": "volume-plan-v01",
        "volume_number": 1,
        "chapter_number": 2,
        "basis_generation_id": "gen-000002",
    }
    state["current_generation_id"] = "gen-000002"
    state["active_candidate"] = None
    state["active_scene_id"] = None
    state["pending_commit"] = None
    state["stop_reason"] = None
    state["last_error"] = None
    state["updated_at"] = "2026-07-24T06:13:00Z"
    store.save(state)
    return workspace


class ChapterPlanStageV1Tests(unittest.TestCase):
    def test_generate_review_adopt_and_advance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            model = AcceptingModel(
                chapter_plan_candidate()
            )

            state = ChapterPlanStageService(workspace).run(
                model,
                updated_at=PLAN_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "chapter_plan"),
                    ("critique", "chapter_plan"),
                ],
            )
            self.assertEqual(
                state["current_stage"],
                "scene_plan",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000001",
            )
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
                    "scene_number": 1,
                    "basis_generation_id": "gen-000001",
                },
            )
            self.assertIsNone(state["active_candidate"])

            path = (
                workspace
                / "design/chapter-plans"
                / "v01-c001-v0001"
                / "chapter-plan.json"
            )
            adopted = load_json_from(path)
            self.assertEqual(
                adopted["chapter_plan_id"],
                "chapter-plan-v01-c001",
            )
            self.assertEqual(adopted["volume_number"], 1)
            self.assertEqual(adopted["chapter_number"], 1)
            self.assertEqual(adopted["version"], 1)
            self.assertEqual(adopted["status"], "accepted")
            self.assertEqual(
                adopted["basis_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                adopted["volume_plan_id"],
                "volume-plan-v01",
            )
            self.assertIsNone(adopted["parent_plan_id"])
            self.assertEqual(adopted["created_at"], PLAN_AT)

            for key, value in (
                chapter_plan_candidate().items()
            ):
                self.assertEqual(adopted[key], value)

            context = model.contexts[0]
            self.assertEqual(
                context["target_volume_number"],
                1,
            )
            self.assertEqual(
                context["target_chapter_number"],
                1,
            )
            self.assertEqual(
                context["volume_plan"]["volume_plan_id"],
                "volume-plan-v01",
            )
            self.assertEqual(
                context["current_generation"][
                    "commit.json"
                ]["generation_id"],
                "gen-000001",
            )

            validate_workspace_layout(workspace)

    def test_invalid_candidate_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            invalid = chapter_plan_candidate()
            invalid["scene_summaries"][1][
                "scene_number"
            ] = 3

            state = ChapterPlanStageService(workspace).run(
                AcceptingModel(invalid),
                updated_at=PLAN_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "manual_review_required",
            )
            self.assertFalse(
                (
                    workspace
                    / "design/chapter-plans"
                    / "v01-c001-v0001"
                ).exists()
            )

    def test_wrong_stage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "scene_plan"
            store.save(state)

            with self.assertRaises(ContractError):
                ChapterPlanStageService(workspace).run(
                    AcceptingModel(
                        chapter_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_target_chapter_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            store = RunStateStore(workspace)
            state = store.load()
            state["current_target"]["chapter_number"] = 4
            store.save(state)

            with self.assertRaises(ContractError):
                ChapterPlanStageService(workspace).run(
                    AcceptingModel(
                        chapter_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_later_chapter_requires_prior_plan(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            store = RunStateStore(workspace)
            state = store.load()
            state["current_target"]["chapter_number"] = 2
            store.save(state)

            with self.assertRaises(ContractError):
                ChapterPlanStageService(workspace).run(
                    AcceptingModel(
                        chapter_two_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_revelation_budget_cannot_be_reused(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            first = deepcopy(chapter_plan_candidate())
            first["required_revelations"] = [
                "火災が単純な事故ではない可能性を示す。",
            ]
            ChapterPlanStageService(workspace).run(
                AcceptingModel(first),
                updated_at=PLAN_AT,
            )

            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "chapter_plan"
            state["current_target"] = {
                "series": state["workspace_id"],
                "series_plan_id": "series-plan-0001",
                "volume_plan_id": "volume-plan-v01",
                "volume_number": 1,
                "chapter_number": 2,
                "basis_generation_id": "gen-000001",
            }
            store.save(state)

            second = chapter_two_candidate()
            second["required_revelations"] = [
                "別表現で同じ開示枠を再利用する。",
            ]
            blocked = ChapterPlanStageService(
                workspace
            ).run(
                AcceptingModel(second),
                updated_at="2026-07-24T06:13:00Z",
            )

            self.assertEqual(blocked["status"], "blocked")
            self.assertFalse(
                (
                    workspace
                    / "design/chapter-plans"
                    / "v01-c002-v0001"
                ).exists()
            )

    def test_existing_different_plan_cannot_be_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            service = ChapterPlanStageService(workspace)
            service.run(
                AcceptingModel(chapter_plan_candidate()),
                updated_at=PLAN_AT,
            )

            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "chapter_plan"
            state["current_target"] = {
                "series": state["workspace_id"],
                "series_plan_id": "series-plan-0001",
                "volume_plan_id": "volume-plan-v01",
                "volume_number": 1,
                "chapter_number": 1,
                "basis_generation_id": "gen-000001",
            }
            store.save(state)

            changed = deepcopy(chapter_plan_candidate())
            changed["chapter_purpose"] = (
                "別の章目的へ変更する。"
            )

            with self.assertRaises(ContractError):
                service.run(
                    AcceptingModel(changed),
                    updated_at=PLAN_AT,
                )

    def test_workspace_rejects_mutated_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            ChapterPlanStageService(workspace).run(
                AcceptingModel(chapter_plan_candidate()),
                updated_at=PLAN_AT,
            )

            path = (
                workspace
                / "design/chapter-plans"
                / "v01-c001-v0001"
                / "chapter-plan.json"
            )
            adopted = load_json_from(path)
            adopted["scene_summaries"][1][
                "scene_number"
            ] = 3
            write_json(path, adopted)

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)

    def test_workspace_rejects_missing_prior_chapter(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = prepare_second_chapter_workspace(
                temporary
            )
            ChapterPlanStageService(workspace).run(
                AcceptingModel(chapter_two_candidate()),
                updated_at="2026-07-24T06:14:00Z",
            )

            shutil.rmtree(
                workspace
                / "design/chapter-plans"
                / "v01-c001-v0001"
            )

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)

    def test_workspace_rejects_revelation_overuse(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_chapter_plan_workspace(
                temporary
            )
            first = deepcopy(chapter_plan_candidate())
            first["required_revelations"] = [
                "火災が単純な事故ではない可能性を示す。",
            ]
            ChapterPlanStageService(workspace).run(
                AcceptingModel(first),
                updated_at=PLAN_AT,
            )

            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "chapter_plan"
            state["current_target"] = {
                "series": state["workspace_id"],
                "series_plan_id": "series-plan-0001",
                "volume_plan_id": "volume-plan-v01",
                "volume_number": 1,
                "chapter_number": 2,
                "basis_generation_id": "gen-000001",
            }
            store.save(state)

            ChapterPlanStageService(workspace).run(
                AcceptingModel(chapter_two_candidate()),
                updated_at="2026-07-24T06:13:00Z",
            )

            path = (
                workspace
                / "design/chapter-plans"
                / "v01-c002-v0001"
                / "chapter-plan.json"
            )
            adopted = load_json_from(path)
            adopted["required_revelations"] = [
                "同じVolume開示枠を重複消費する。",
            ]
            write_json(path, adopted)

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)

    def test_later_chapter_uses_current_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = prepare_second_chapter_workspace(
                temporary
            )
            model = AcceptingModel(
                chapter_two_candidate()
            )

            state = ChapterPlanStageService(workspace).run(
                model,
                updated_at="2026-07-24T06:14:00Z",
            )

            self.assertEqual(
                state["current_stage"],
                "scene_plan",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000002",
            )
            self.assertEqual(
                state["current_target"],
                {
                    "series": "ws-test-0001",
                    "series_plan_id": "series-plan-0001",
                    "volume_plan_id": "volume-plan-v01",
                    "chapter_plan_id": (
                        "chapter-plan-v01-c002"
                    ),
                    "volume_number": 1,
                    "chapter_number": 2,
                    "scene_number": 1,
                    "basis_generation_id": "gen-000002",
                },
            )

            context = model.contexts[0]
            self.assertEqual(
                context["current_generation"][
                    "commit.json"
                ]["commit_type"],
                "scene",
            )
            self.assertEqual(
                context["volume_plan"][
                    "basis_generation_id"
                ],
                "gen-000001",
            )

            adopted = load_json_from(
                workspace
                / "design/chapter-plans"
                / "v01-c002-v0001"
                / "chapter-plan.json"
            )
            self.assertEqual(
                adopted["basis_generation_id"],
                "gen-000002",
            )
            validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
