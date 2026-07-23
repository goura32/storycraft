"""Storycraft Version 1 scene_plan Stage契約。"""
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
from storycraft.scene_plan_stage import (
    ScenePlanStageService,
)
from storycraft.series_contracts import ContractError
from storycraft.workspace import validate_workspace_layout

from tests.test_chapter_plan_schema_v1 import (
    chapter_plan_candidate,
)
from tests.test_chapter_plan_stage_v1 import (
    create_chapter_plan_workspace,
)
from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    load_json_from,
)
from tests.test_scene_plan_schema_v1 import (
    scene_plan_candidate,
)


PLAN_AT = "2026-07-24T07:20:00Z"


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


def scene_two_candidate() -> dict:
    return {
        "purpose": (
            "凪の所在を知り、灯台へ向かう動機を作る。"
        ),
        "pov_character_id": "char-0001",
        "participant_ids": [
            "char-0001",
            "char-0002",
        ],
        "location_id": "loc-0002",
        "starting_conditions": [
            "澪は町の空気に不自然さを感じている。",
            "凪との再会はまだ実現していない。",
        ],
        "intended_beats": [
            "澪が凪の所在を尋ねる。",
            "灯台へ向かう必要を理解する。",
        ],
        "intended_revelations": [],
        "intended_changes": [
            "澪が灯台へ向かうと決める。",
        ],
        "prohibited_disclosures": [
            "灯台火災の全容",
            "火災を起こした人物",
        ],
    }


def create_scene_plan_workspace(
    temporary: str,
    *,
    chapter_candidate: dict | None = None,
) -> Path:
    workspace = create_chapter_plan_workspace(temporary)
    ChapterPlanStageService(workspace).run(
        AcceptingModel(
            chapter_candidate or chapter_plan_candidate()
        ),
        updated_at="2026-07-24T07:18:00Z",
    )
    return workspace


def prepare_second_scene_workspace(
    temporary: str,
) -> Path:
    workspace = create_scene_plan_workspace(temporary)
    ScenePlanStageService(workspace).run(
        AcceptingModel(scene_plan_candidate()),
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
                "summary": "第一Sceneを確定。",
                "changed_targets": ["state"],
                "created_at": "2026-07-24T07:21:00Z",
            })
        write_json(destination / name, value)

    store = RunStateStore(workspace)
    state = store.load()
    state["status"] = "running"
    state["current_stage"] = "scene_plan"
    state["current_target"] = {
        "series": state["workspace_id"],
        "series_plan_id": "series-plan-0001",
        "volume_plan_id": "volume-plan-v01",
        "chapter_plan_id": "chapter-plan-v01-c001",
        "volume_number": 1,
        "chapter_number": 1,
        "scene_number": 2,
        "basis_generation_id": "gen-000002",
    }
    state["current_generation_id"] = "gen-000002"
    state["active_candidate"] = None
    state["active_scene_id"] = None
    state["pending_commit"] = None
    state["stop_reason"] = None
    state["last_error"] = None
    state["updated_at"] = "2026-07-24T07:21:00Z"
    store.save(state)
    return workspace


class ScenePlanStageV1Tests(unittest.TestCase):
    def test_generate_review_adopt_and_advance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_plan_workspace(
                temporary
            )
            model = AcceptingModel(
                scene_plan_candidate()
            )

            state = ScenePlanStageService(workspace).run(
                model,
                updated_at=PLAN_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "scene_plan"),
                    ("critique", "scene_plan"),
                ],
            )
            self.assertEqual(
                state["current_stage"],
                "scene_card",
            )
            self.assertEqual(
                state["active_scene_id"],
                "scene-v01-c001-s001",
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
                    "scene_plan_id": (
                        "scene-plan-v01-c001-s001"
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
                / "design/scene-plans"
                / "v01-c001-s001-v0001"
                / "scene-plan.json"
            )
            adopted = load_json_from(path)
            self.assertEqual(
                adopted["scene_plan_id"],
                "scene-plan-v01-c001-s001",
            )
            self.assertEqual(adopted["volume_number"], 1)
            self.assertEqual(adopted["chapter_number"], 1)
            self.assertEqual(adopted["scene_number"], 1)
            self.assertEqual(adopted["version"], 1)
            self.assertEqual(adopted["status"], "accepted")
            self.assertEqual(
                adopted["basis_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                adopted["chapter_plan_id"],
                "chapter-plan-v01-c001",
            )
            self.assertIsNone(adopted["parent_plan_id"])
            self.assertEqual(adopted["created_at"], PLAN_AT)

            for key, value in (
                scene_plan_candidate().items()
            ):
                self.assertEqual(adopted[key], value)

            context = model.contexts[0]
            self.assertEqual(
                context["target_scene_number"],
                1,
            )
            self.assertEqual(
                context["chapter_plan"][
                    "chapter_plan_id"
                ],
                "chapter-plan-v01-c001",
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
            workspace = create_scene_plan_workspace(
                temporary
            )
            invalid = scene_plan_candidate()
            invalid["location_id"] = "loc-9999"

            state = ScenePlanStageService(workspace).run(
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
                    / "design/scene-plans"
                    / "v01-c001-s001-v0001"
                ).exists()
            )

    def test_wrong_stage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_plan_workspace(
                temporary
            )
            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "scene_card"
            state["active_scene_id"] = (
                "scene-v01-c001-s001"
            )
            store.save(state)

            with self.assertRaises(ContractError):
                ScenePlanStageService(workspace).run(
                    AcceptingModel(
                        scene_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_target_scene_must_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_plan_workspace(
                temporary
            )
            store = RunStateStore(workspace)
            state = store.load()
            state["current_target"]["scene_number"] = 3
            store.save(state)

            with self.assertRaises(ContractError):
                ScenePlanStageService(workspace).run(
                    AcceptingModel(
                        scene_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_later_scene_requires_prior_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_plan_workspace(
                temporary
            )
            store = RunStateStore(workspace)
            state = store.load()
            state["current_target"]["scene_number"] = 2
            store.save(state)

            with self.assertRaises(ContractError):
                ScenePlanStageService(workspace).run(
                    AcceptingModel(
                        scene_two_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_existing_different_plan_cannot_be_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_plan_workspace(
                temporary
            )
            service = ScenePlanStageService(workspace)
            service.run(
                AcceptingModel(scene_plan_candidate()),
                updated_at=PLAN_AT,
            )

            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "scene_plan"
            state["current_target"] = {
                "series": state["workspace_id"],
                "series_plan_id": "series-plan-0001",
                "volume_plan_id": "volume-plan-v01",
                "chapter_plan_id": "chapter-plan-v01-c001",
                "volume_number": 1,
                "chapter_number": 1,
                "scene_number": 1,
                "basis_generation_id": "gen-000001",
            }
            state["active_scene_id"] = None
            store.save(state)

            changed = deepcopy(scene_plan_candidate())
            changed["purpose"] = "別のScene目的へ変更する。"

            with self.assertRaises(ContractError):
                service.run(
                    AcceptingModel(changed),
                    updated_at=PLAN_AT,
                )

    def test_workspace_rejects_mutated_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_plan_workspace(
                temporary
            )
            ScenePlanStageService(workspace).run(
                AcceptingModel(scene_plan_candidate()),
                updated_at=PLAN_AT,
            )

            path = (
                workspace
                / "design/scene-plans"
                / "v01-c001-s001-v0001"
                / "scene-plan.json"
            )
            adopted = load_json_from(path)
            adopted["pov_character_id"] = "char-9999"
            write_json(path, adopted)

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)

    def test_revelation_budget_cannot_be_reused(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            chapter = deepcopy(chapter_plan_candidate())
            chapter["required_revelations"] = [
                "火災が事故ではない可能性を示す。",
            ]
            workspace = create_scene_plan_workspace(
                temporary,
                chapter_candidate=chapter,
            )

            first = deepcopy(scene_plan_candidate())
            first["intended_revelations"] = [
                "現場から事故ではない可能性を示す。",
            ]
            ScenePlanStageService(workspace).run(
                AcceptingModel(first),
                updated_at=PLAN_AT,
            )

            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "scene_plan"
            state["current_target"] = {
                "series": state["workspace_id"],
                "series_plan_id": "series-plan-0001",
                "volume_plan_id": "volume-plan-v01",
                "chapter_plan_id": "chapter-plan-v01-c001",
                "volume_number": 1,
                "chapter_number": 1,
                "scene_number": 2,
                "basis_generation_id": "gen-000001",
            }
            state["active_scene_id"] = None
            store.save(state)

            second = scene_two_candidate()
            second["intended_revelations"] = [
                "別表現で同じ開示枠を再利用する。",
            ]
            blocked = ScenePlanStageService(workspace).run(
                AcceptingModel(second),
                updated_at="2026-07-24T07:21:00Z",
            )

            self.assertEqual(blocked["status"], "blocked")
            self.assertFalse(
                (
                    workspace
                    / "design/scene-plans"
                    / "v01-c001-s002-v0001"
                ).exists()
            )

    def test_later_scene_uses_current_generation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = prepare_second_scene_workspace(
                temporary
            )
            model = AcceptingModel(
                scene_two_candidate()
            )

            state = ScenePlanStageService(workspace).run(
                model,
                updated_at="2026-07-24T07:22:00Z",
            )

            self.assertEqual(
                state["current_stage"],
                "scene_card",
            )
            self.assertEqual(
                state["active_scene_id"],
                "scene-v01-c001-s002",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000002",
            )
            self.assertEqual(
                state["current_target"][
                    "scene_plan_id"
                ],
                "scene-plan-v01-c001-s002",
            )

            context = model.contexts[0]
            self.assertEqual(
                context["current_generation"][
                    "commit.json"
                ]["commit_type"],
                "scene",
            )
            self.assertEqual(
                context["chapter_plan"][
                    "basis_generation_id"
                ],
                "gen-000001",
            )

            adopted = load_json_from(
                workspace
                / "design/scene-plans"
                / "v01-c001-s002-v0001"
                / "scene-plan.json"
            )
            self.assertEqual(
                adopted["basis_generation_id"],
                "gen-000002",
            )
            validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
