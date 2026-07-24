"""Storycraft Version 1 scene_continuity Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from storycraft.run_state import RunStateStore
from storycraft.scene_card_stage import SceneCardStageService
from storycraft.scene_continuity_stage import (
    SceneContinuityStageService,
)
from storycraft.scene_prose_stage import SceneProseStageService
from storycraft.series_contracts import ContractError
from storycraft.workspace import validate_workspace_layout

from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    load_json_from,
)
from tests.test_scene_card_stage_v1 import (
    CARD_AT,
    create_scene_card_workspace,
    matching_card,
)
from tests.test_scene_prose_stage_v1 import (
    AcceptingProseModel,
    PROSE,
    PROSE_AT,
)


CONTINUITY_AT = "2026-07-24T10:10:00Z"


def create_scene_continuity_workspace(
    temporary: str,
) -> Path:
    workspace = create_scene_card_workspace(temporary)
    SceneCardStageService(workspace).run(
        AcceptingModel(matching_card()),
        updated_at=CARD_AT,
    )
    SceneProseStageService(workspace).run(
        AcceptingProseModel(PROSE),
        updated_at=PROSE_AT,
    )
    return workspace


def matching_continuity() -> dict:
    return {
        "summary": "澪が灯台へ到着した事実を反映する。",
        "operations": [{
            "target_type": "character_state",
            "target_id": "char-0001",
            "field": "current_location_id",
            "operation": "set",
            "old_value": "loc-0001",
            "new_value": "loc-0002",
            "reason": "本文冒頭で澪が灯台の扉を見ている。",
            "evidence_indices": [0],
        }],
        "evidence": [{
            "quote": (
                "灯台の扉は、澪が覚えていたよりも低かった。"
            ),
            "occurrence": 1,
            "context_before": "",
            "context_after": (
                "潮を含んだ風が、錆びた蝶番を細く鳴らしている。"
            ),
            "target_type": "character_state",
            "target_id": "char-0001",
            "change_summary": "澪の現在位置を灯台へ更新する。",
        }],
        "unchanged_assertions": [
            "凪は地下保管庫の鍵を保持したままである。",
        ],
    }


class AcceptingContinuityModel:
    def __init__(self, candidate: dict) -> None:
        self.candidate = candidate
        self.calls: list[tuple[str, str]] = []
        self.contexts: list[dict] = []

    def generate(self, stage: str, context: dict) -> dict:
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


class RevisingContinuityModel(AcceptingContinuityModel):
    def __init__(self, initial: dict, revised: dict) -> None:
        super().__init__(initial)
        self.revised = revised
        self.reviews = 0

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.calls.append(("critique", stage))
        self.reviews += 1
        if self.reviews == 1:
            return {
                "issues": [{
                    "severity": "minor",
                    "field": "summary",
                    "description": "要約が曖昧である。",
                    "suggestion": "更新内容を明記する。",
                }],
            }
        return {"issues": []}

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        self.calls.append(("revision", stage))
        return deepcopy(self.revised)


class SceneContinuityStageV1Tests(unittest.TestCase):
    def test_generate_review_adopt_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_continuity_workspace(
                temporary
            )
            model = AcceptingContinuityModel(
                matching_continuity()
            )

            state = SceneContinuityStageService(
                workspace
            ).run(
                model,
                updated_at=CONTINUITY_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "scene_continuity_v1"),
                    ("critique", "scene_continuity_v1"),
                ],
            )
            self.assertEqual(
                state["current_stage"],
                "scene_commit",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                state["current_target"][
                    "result_generation_id"
                ],
                "gen-000002",
            )
            self.assertEqual(
                state["current_target"]["continuity_version"],
                1,
            )
            self.assertIsNone(state["pending_commit"])

            root = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
            )
            continuity = load_json_from(
                root / "continuity.json"
            )
            self.assertEqual(
                continuity["continuity_id"],
                (
                    "continuity-scene-v01-c001-s001-v0001"
                ),
            )
            self.assertEqual(
                continuity["result_generation_id"],
                "gen-000002",
            )
            self.assertEqual(
                continuity["operations"][0]["operation_id"],
                "update-000001",
            )
            self.assertEqual(
                continuity["evidence"][0]["evidence_id"],
                "evidence-000001",
            )
            self.assertEqual(
                continuity["operations"][0]["evidence_ids"],
                ["evidence-000001"],
            )

            candidate = load_json_from(
                workspace
                / "runtime/candidates/scene_continuity"
                / "candidate-000015/v0001/candidate.json"
            )["content"]
            self.assertNotIn("operation_id", candidate["operations"][0])
            self.assertNotIn("evidence_id", candidate["evidence"][0])

            context = model.contexts[0]
            self.assertEqual(
                context["frozen_prose"],
                PROSE,
            )
            serialized = json.dumps(
                context,
                ensure_ascii=False,
            )
            self.assertIn("allowed_updates", serialized)
            self.assertNotIn("series_plan", serialized)
            self.assertNotIn("planned_resolution", serialized)
            self.assertNotIn("long_term_arcs", serialized)
            self.assertNotIn("ending", serialized)
            self.assertNotIn(
                "火災には未公開の経緯がある。",
                serialized,
            )
            self.assertNotIn("notes", serialized)

            counters = load_json_from(
                workspace / "runtime/counters.json"
            )
            self.assertEqual(counters["next_generation"], 3)
            self.assertEqual(counters["next_update"], 2)
            self.assertEqual(counters["next_evidence"], 2)
            validate_workspace_layout(workspace)

    def test_revision_creates_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_continuity_workspace(
                temporary
            )
            initial = matching_continuity()
            initial["summary"] = "位置を更新する。"
            revised = matching_continuity()

            state = SceneContinuityStageService(
                workspace
            ).run(
                RevisingContinuityModel(initial, revised),
                updated_at=CONTINUITY_AT,
            )

            self.assertEqual(state["current_stage"], "scene_commit")
            root = (
                workspace
                / "runtime/candidates/scene_continuity"
                / "candidate-000015"
            )
            self.assertEqual(
                load_json_from(root / "v0001/status.json")[
                    "status"
                ],
                "needs_revision",
            )
            self.assertEqual(
                load_json_from(root / "v0002/status.json")[
                    "status"
                ],
                "accepted",
            )

    def test_no_change_candidate_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_continuity_workspace(
                temporary
            )
            candidate = {
                "summary": "本文から確定できる状態変更はない。",
                "operations": [],
                "evidence": [],
                "unchanged_assertions": [
                    "鍵のholderは変更されていない。",
                ],
            }

            state = SceneContinuityStageService(
                workspace
            ).run(
                AcceptingContinuityModel(candidate),
                updated_at=CONTINUITY_AT,
            )

            self.assertEqual(state["current_stage"], "scene_commit")
            continuity = load_json_from(
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
                / "continuity.json"
            )
            self.assertEqual(continuity["operations"], [])
            self.assertEqual(continuity["evidence"], [])

    def test_invalid_candidates_block_without_adoption(self) -> None:
        invalids: list[tuple[str, dict]] = []

        outside = matching_continuity()
        outside["operations"][0]["target_id"] = "char-0002"
        outside["evidence"][0]["target_id"] = "char-0002"
        invalids.append(("outside allowlist", outside))

        stale = matching_continuity()
        stale["operations"][0]["old_value"] = "loc-9999"
        invalids.append(("stale old value", stale))

        missing_quote = matching_continuity()
        missing_quote["evidence"][0]["quote"] = (
            "本文に存在しない引用"
        )
        invalids.append(("missing quote", missing_quote))

        no_op = matching_continuity()
        no_op["operations"][0]["new_value"] = "loc-0001"
        invalids.append(("no-op", no_op))

        for name, candidate in invalids:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as temporary:
                    workspace = (
                        create_scene_continuity_workspace(
                            temporary
                        )
                    )
                    state = SceneContinuityStageService(
                        workspace
                    ).run(
                        AcceptingContinuityModel(candidate),
                        updated_at=CONTINUITY_AT,
                    )
                    self.assertEqual(state["status"], "blocked")
                    self.assertFalse(
                        (
                            workspace
                            / "runtime/staging"
                            / "scene-scene-v01-c001-s001"
                            / "continuity.json"
                        ).exists()
                    )

    def test_non_running_state_does_not_reserve_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_continuity_workspace(
                temporary
            )
            store = RunStateStore(workspace)
            state = store.load()
            state["status"] = "stopped"
            state["stop_reason"] = "user_requested"
            store.save(state)

            before = load_json_from(
                workspace / "runtime/counters.json"
            )["next_generation"]

            with self.assertRaisesRegex(
                ContractError,
                "run status",
            ):
                SceneContinuityStageService(workspace).run(
                    AcceptingContinuityModel(
                        matching_continuity()
                    ),
                    updated_at=CONTINUITY_AT,
                )

            after = load_json_from(
                workspace / "runtime/counters.json"
            )["next_generation"]
            self.assertEqual(after, before)

    def test_stale_basis_is_rejected_before_model(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_continuity_workspace(
                temporary
            )
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
                SceneContinuityStageService(workspace).run(
                    AcceptingContinuityModel(
                        matching_continuity()
                    ),
                    updated_at=CONTINUITY_AT,
                )

    def test_workspace_rejects_mutated_continuity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_continuity_workspace(
                temporary
            )
            SceneContinuityStageService(workspace).run(
                AcceptingContinuityModel(
                    matching_continuity()
                ),
                updated_at=CONTINUITY_AT,
            )
            path = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
                / "continuity.json"
            )
            value = load_json_from(path)
            value["evidence"][0]["quote"] = (
                "本文に存在しない引用"
            )
            path.write_text(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
