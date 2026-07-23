"""Storycraft Version 1 volume_plan Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError
from storycraft.series_plan_stage import (
    SeriesPlanStageService,
)
from storycraft.volume_plan_stage import (
    VolumePlanStageService,
)
from storycraft.workspace import validate_workspace_layout

from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    load_json_from,
)
from tests.test_series_plan_schema_v1 import (
    series_plan_candidate,
)
from tests.test_series_plan_stage_v1 import (
    create_series_plan_workspace,
)
from tests.test_volume_plan_schema_v1 import (
    volume_plan_candidate,
)


PLAN_AT = "2026-07-23T10:14:00Z"


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


def volume_two_candidate() -> dict:
    return {
        "starting_state_summary": (
            "第一巻の調査を経て、澪と凪は限定的に対話を再開し、"
            "火災記録と町の証言の不一致を追える状態にある。"
        ),
        "volume_purpose": "町の記録と証言の不一致を追う",
        "central_conflict": (
            "澪は記録の改変を疑うが、凪は町の関係者を"
            "刺激することを恐れて調査方法をめぐり対立する。"
        ),
        "character_changes": {
            "char-0001": (
                "個人的な疑念から町の隠蔽構造を調べる姿勢へ進む。"
            ),
            "char-0002": (
                "沈黙だけで守る姿勢から限定的な協力へ進む。"
            ),
        },
        "relationship_changes": {
            "rel-0001": (
                "完全な信頼には至らないが共同調査の関係になる。"
            ),
        },
        "thread_goals": {
            "thread-0001": (
                "火災記録と証言の不一致が組織的な隠蔽に"
                "つながる可能性を示す。"
            ),
            "thread-0002": (
                "凪が沈黙を選んだ理由に町の圧力があると示す。"
            ),
        },
        "revelations": [],
        "chapter_summaries": [
            {
                "chapter_number": 1,
                "purpose": (
                    "前巻Handoffを受け、旧記録の所在を確認する。"
                ),
            },
            {
                "chapter_number": 2,
                "purpose": (
                    "町の証言と公式記録の矛盾を比較する。"
                ),
            },
            {
                "chapter_number": 3,
                "purpose": (
                    "隠蔽へ関わる人物と仕組みの輪郭を得る。"
                ),
            },
        ],
        "required_end_state": "隠蔽に関わる構造を把握する",
        "handoff_expectations": [
            "姉妹それぞれの記憶を次巻で衝突させられる状態にする。",
            "隠蔽構造の関係者を継続調査対象として残す。",
        ],
    }


def prepare_second_volume_workspace(
    temporary: str,
) -> Path:
    workspace = create_volume_plan_workspace(temporary)
    VolumePlanStageService(workspace).run(
        AcceptingModel(volume_plan_candidate()),
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
                "summary": "第一巻の最終Sceneを確定。",
                "changed_targets": ["state"],
                "created_at": "2026-07-23T10:15:00Z",
            })
        write_json(destination / name, value)

    write_json(
        workspace / "handoffs/handoff-v01/handoff.json",
        {
            "schema_version": 1,
            "handoff_id": "handoff-v01",
            "volume_number": 1,
            "basis_generation_id": "gen-000002",
            "completed_chapter_ids": [
                "chapter-v01-c001",
            ],
            "completed_scene_ids": [
                "scene-v01-c001-s001",
            ],
            "character_states": {
                "char-0001": "町の記録を調査する。",
                "char-0002": "限定的に協力する。",
            },
            "relationship_states": {
                "rel-0001": "共同調査を始める。",
            },
            "resolved_threads": [],
            "open_threads": [
                "thread-0001",
                "thread-0002",
            ],
            "new_constraints": [
                "町の関係者へ調査を知られてはならない。",
            ],
            "ending_progress": "最初の手掛かりを得た。",
            "next_volume_requirements": [
                "旧記録の所在を追う。",
                "町の証言と記録を比較する。",
            ],
            "issues": [],
            "created_at": "2026-07-23T10:15:00Z",
        },
    )

    store = RunStateStore(workspace)
    state = store.load()
    state["status"] = "running"
    state["current_stage"] = "volume_plan"
    state["current_target"] = {
        "series": state["workspace_id"],
        "series_plan_id": "series-plan-0001",
        "volume_number": 2,
        "basis_generation_id": "gen-000002",
    }
    state["current_generation_id"] = "gen-000002"
    state["active_candidate"] = None
    state["active_scene_id"] = None
    state["pending_commit"] = None
    state["stop_reason"] = None
    state["last_error"] = None
    state["updated_at"] = "2026-07-23T10:15:00Z"
    store.save(state)
    return workspace


def create_volume_plan_workspace(
    temporary: str,
) -> Path:
    workspace = create_series_plan_workspace(temporary)
    SeriesPlanStageService(workspace).run(
        AcceptingModel(series_plan_candidate()),
        updated_at="2026-07-23T10:12:00Z",
    )
    return workspace


class VolumePlanStageV1Tests(unittest.TestCase):
    def test_generate_review_adopt_and_advance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_volume_plan_workspace(
                temporary
            )
            model = AcceptingModel(
                volume_plan_candidate()
            )

            state = VolumePlanStageService(workspace).run(
                model,
                updated_at=PLAN_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "volume_plan"),
                    ("critique", "volume_plan"),
                ],
            )
            self.assertEqual(
                state["current_stage"],
                "chapter_plan",
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
                    "volume_number": 1,
                    "chapter_number": 1,
                    "basis_generation_id": "gen-000001",
                },
            )
            self.assertIsNone(state["active_candidate"])

            path = (
                workspace
                / "design/volume-plans"
                / "v01-v0001"
                / "volume-plan.json"
            )
            adopted = load_json_from(path)
            self.assertEqual(
                adopted["schema_version"],
                1,
            )
            self.assertEqual(
                adopted["volume_plan_id"],
                "volume-plan-v01",
            )
            self.assertEqual(
                adopted["volume_number"],
                1,
            )
            self.assertEqual(adopted["version"], 1)
            self.assertEqual(
                adopted["status"],
                "accepted",
            )
            self.assertEqual(
                adopted["basis_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                adopted["series_plan_id"],
                "series-plan-0001",
            )
            self.assertIsNone(
                adopted["parent_plan_id"]
            )
            self.assertEqual(
                adopted["created_at"],
                PLAN_AT,
            )
            for key, value in (
                volume_plan_candidate().items()
            ):
                self.assertEqual(adopted[key], value)

            candidate = load_json_from(
                workspace
                / "runtime/candidates/volume_plan"
                / "candidate-000010/v0001/candidate.json"
            )
            self.assertEqual(
                candidate["content"],
                volume_plan_candidate(),
            )
            self.assertNotIn(
                "volume_plan_id",
                candidate["content"],
            )
            self.assertNotIn(
                "volume_number",
                candidate["content"],
            )

            self.assertEqual(
                model.contexts[0],
                model.contexts[1],
            )
            context = model.contexts[0]
            self.assertEqual(
                context["target_volume_number"],
                1,
            )
            self.assertEqual(
                context["series_plan"][
                    "series_plan_id"
                ],
                "series-plan-0001",
            )
            self.assertEqual(
                context["current_generation"][
                    "commit.json"
                ]["generation_id"],
                "gen-000001",
            )
            self.assertIsNone(
                context["previous_handoff"]
            )

            validate_workspace_layout(workspace)

    def test_invalid_candidate_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_volume_plan_workspace(
                temporary
            )
            invalid = volume_plan_candidate()
            del invalid["thread_goals"]["thread-0002"]

            state = VolumePlanStageService(workspace).run(
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
                    / "design/volume-plans"
                    / "v01-v0001"
                ).exists()
            )

    def test_wrong_stage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_volume_plan_workspace(
                temporary
            )
            state_store = RunStateStore(workspace)
            state = state_store.load()
            state["current_stage"] = "chapter_plan"
            state_store.save(state)

            with self.assertRaises(ContractError):
                VolumePlanStageService(workspace).run(
                    AcceptingModel(
                        volume_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_target_volume_must_match_run_state(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_volume_plan_workspace(
                temporary
            )
            state_store = RunStateStore(workspace)
            state = state_store.load()
            state["current_target"]["volume_number"] = 2
            state_store.save(state)

            with self.assertRaises(ContractError):
                VolumePlanStageService(workspace).run(
                    AcceptingModel(
                        volume_plan_candidate()
                    ),
                    updated_at=PLAN_AT,
                )

    def test_existing_different_plan_cannot_be_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_volume_plan_workspace(
                temporary
            )
            service = VolumePlanStageService(workspace)
            service.run(
                AcceptingModel(volume_plan_candidate()),
                updated_at=PLAN_AT,
            )

            state_store = RunStateStore(workspace)
            state = state_store.load()
            state["current_stage"] = "volume_plan"
            state["current_target"] = {
                "series": state["workspace_id"],
                "series_plan_id": "series-plan-0001",
                "volume_number": 1,
                "basis_generation_id": "gen-000001",
            }
            state_store.save(state)

            changed = deepcopy(volume_plan_candidate())
            changed["central_conflict"] = (
                "別の中心対立へ変更する。"
            )

            with self.assertRaises(ContractError):
                service.run(
                    AcceptingModel(changed),
                    updated_at=PLAN_AT,
                )

    def test_workspace_rejects_mutated_plan(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_volume_plan_workspace(
                temporary
            )
            VolumePlanStageService(workspace).run(
                AcceptingModel(volume_plan_candidate()),
                updated_at=PLAN_AT,
            )

            path = (
                workspace
                / "design/volume-plans"
                / "v01-v0001"
                / "volume-plan.json"
            )
            adopted = load_json_from(path)
            adopted["thread_goals"] = {
                "thread-0001": "一件だけへ改変する。",
            }
            path.write_text(
                __import__("json").dumps(
                    adopted,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)


    def test_second_volume_uses_current_generation_and_handoff(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = prepare_second_volume_workspace(
                temporary
            )
            model = AcceptingModel(
                volume_two_candidate()
            )

            state = VolumePlanStageService(workspace).run(
                model,
                updated_at="2026-07-23T10:16:00Z",
            )

            self.assertEqual(
                state["current_stage"],
                "chapter_plan",
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
                    "volume_plan_id": "volume-plan-v02",
                    "volume_number": 2,
                    "chapter_number": 1,
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
                context["previous_handoff"]["handoff_id"],
                "handoff-v01",
            )

            adopted = load_json_from(
                workspace
                / "design/volume-plans"
                / "v02-v0001"
                / "volume-plan.json"
            )
            self.assertEqual(
                adopted["basis_generation_id"],
                "gen-000002",
            )
            validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
