from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.scene_generation import (
    apply_continuity_operations,
    build_scene_commit,
    build_scene_generation,
    state_target_record,
    validate_scene_commit,
    validate_scene_generation,
)
from storycraft.series_contracts import ContractError


COMMITTED_AT = "2026-07-24T10:10:00Z"


def parent_generation() -> dict:
    return {
        "canon.json": {
            "schema_version": 1,
            "generation_id": "gen-000001",
            "records": [{
                "canon_id": "canon-000001",
            }],
        },
        "state.json": {
            "schema_version": 1,
            "generation_id": "gen-000001",
            "characters": {
                "char-0001": {
                    "current_location_id": "loc-0001",
                    "goals": ["灯台を調べる"],
                },
            },
            "relationships": {
                "rel-0001": {
                    "trust": 2,
                },
            },
            "threads": {
                "thread-0001": {
                    "status": "open",
                },
            },
            "timeline": {
                "current_story_time": "夕方",
                "event_order": [],
            },
            "inventory": {
                "item-0001": {
                    "holder_id": "char-0002",
                },
            },
            "commitments": {
                "commitment-0001": {
                    "status": "open",
                },
            },
        },
        "evidence.json": {
            "schema_version": 1,
            "generation_id": "gen-000001",
            "evidence": [],
        },
        "commit.json": {
            "schema_version": 1,
            "generation_id": "gen-000001",
            "parent_generation_id": None,
            "commit_type": "initial_design",
            "source_artifact_type": "initial_design",
            "source_artifact_id": "initial-design-0001",
            "summary": "初期Generation。",
            "changed_targets": ["canon", "state"],
            "created_at": "2026-07-24T09:00:00Z",
        },
    }


def scene_card() -> dict:
    return {
        "scene_id": "scene-v01-c001-s001",
        "version": 1,
        "basis_generation_id": "gen-000001",
    }


def continuity() -> dict:
    return {
        "schema_version": 1,
        "continuity_id": (
            "continuity-scene-v01-c001-s001-v0001"
        ),
        "scene_id": "scene-v01-c001-s001",
        "version": 1,
        "basis_generation_id": "gen-000001",
        "prose_version": 1,
        "result_generation_id": "gen-000002",
        "summary": "澪の現在位置を灯台へ更新する。",
        "operations": [{
            "operation_id": "update-000001",
            "target_type": "character_state",
            "target_id": "char-0001",
            "field": "current_location_id",
            "operation": "set",
            "old_value": "loc-0001",
            "new_value": "loc-0002",
            "reason": "本文で灯台へ到着した。",
            "evidence_ids": ["evidence-000001"],
        }],
        "evidence": [{
            "evidence_id": "evidence-000001",
            "scene_id": "scene-v01-c001-s001",
            "quote": "澪は灯台へ着いた。",
            "occurrence": 1,
            "context_before": "",
            "context_after": "",
            "target_type": "character_state",
            "target_id": "char-0001",
            "change_summary": "現在位置を灯台へ更新する。",
        }],
        "unchanged_assertions": [],
        "created_at": COMMITTED_AT,
    }


class SceneGenerationV1Test(unittest.TestCase):
    def test_state_target_record_supports_all_sources(
        self,
    ) -> None:
        state = parent_generation()["state.json"]

        cases = (
            ("character_state", "char-0001"),
            ("relationship_state", "rel-0001"),
            ("thread_state", "thread-0001"),
            ("timeline_state", "timeline"),
            ("inventory_state", "item-0001"),
            ("commitment_state", "commitment-0001"),
        )
        for target_type, target_id in cases:
            with self.subTest(
                target_type=target_type,
                target_id=target_id,
            ):
                self.assertIsInstance(
                    state_target_record(
                        state,
                        target_type,
                        target_id,
                    ),
                    dict,
                )

    def test_apply_operations_does_not_mutate_parent(
        self,
    ) -> None:
        original = parent_generation()["state.json"]
        updated = apply_continuity_operations(
            original,
            continuity(),
        )

        self.assertEqual(
            original["characters"]["char-0001"][
                "current_location_id"
            ],
            "loc-0001",
        )
        self.assertEqual(
            updated["characters"]["char-0001"][
                "current_location_id"
            ],
            "loc-0002",
        )

    def test_old_value_mismatch_is_rejected(
        self,
    ) -> None:
        invalid = continuity()
        invalid["operations"][0]["old_value"] = "loc-9999"

        with self.assertRaisesRegex(
            ContractError,
            "old_value",
        ):
            apply_continuity_operations(
                parent_generation()["state.json"],
                invalid,
            )

    def test_duplicate_state_update_is_rejected(
        self,
    ) -> None:
        invalid = continuity()
        invalid["operations"].append(
            deepcopy(invalid["operations"][0])
        )

        with self.assertRaisesRegex(
            ContractError,
            "複数回更新",
        ):
            apply_continuity_operations(
                parent_generation()["state.json"],
                invalid,
            )

    def test_build_scene_commit_is_deterministic(
        self,
    ) -> None:
        first = build_scene_commit(
            scene_card=scene_card(),
            continuity=continuity(),
        )
        second = build_scene_commit(
            scene_card=scene_card(),
            continuity=continuity(),
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first,
            {
                "schema_version": 1,
                "scene_id": "scene-v01-c001-s001",
                "scene_version": 1,
                "parent_generation_id": "gen-000001",
                "result_generation_id": "gen-000002",
                "scene_card_version": 1,
                "continuity_update_id": (
                    "continuity-"
                    "scene-v01-c001-s001-v0001"
                ),
                "committed_at": COMMITTED_AT,
                "commit_summary": (
                    "澪の現在位置を灯台へ更新する。"
                ),
            },
        )
        validate_scene_commit(
            first,
            scene_card=scene_card(),
            continuity=continuity(),
        )

    def test_build_scene_generation_is_deterministic(
        self,
    ) -> None:
        parent = parent_generation()
        continuity_value = continuity()
        commit = build_scene_commit(
            scene_card=scene_card(),
            continuity=continuity_value,
        )

        first = build_scene_generation(
            parent_generation=parent,
            continuity=continuity_value,
            scene_commit=commit,
        )
        second = build_scene_generation(
            parent_generation=parent,
            continuity=continuity_value,
            scene_commit=commit,
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first["state.json"]["generation_id"],
            "gen-000002",
        )
        self.assertEqual(
            first["state.json"]["characters"][
                "char-0001"
            ]["current_location_id"],
            "loc-0002",
        )
        self.assertEqual(
            first["canon.json"]["records"],
            parent["canon.json"]["records"],
        )
        self.assertEqual(
            first["evidence.json"]["evidence"],
            continuity_value["evidence"],
        )
        self.assertEqual(
            first["commit.json"]["changed_targets"],
            ["char-0001.current_location_id"],
        )
        self.assertEqual(
            parent["state.json"]["characters"][
                "char-0001"
            ]["current_location_id"],
            "loc-0001",
        )

        validate_scene_generation(
            first,
            parent_generation=parent,
            continuity=continuity_value,
            scene_commit=commit,
        )

    def test_generation_validation_rejects_mutation(
        self,
    ) -> None:
        parent = parent_generation()
        continuity_value = continuity()
        commit = build_scene_commit(
            scene_card=scene_card(),
            continuity=continuity_value,
        )
        generated = build_scene_generation(
            parent_generation=parent,
            continuity=continuity_value,
            scene_commit=commit,
        )
        generated["state.json"]["characters"][
            "char-0001"
        ]["current_location_id"] = "loc-9999"

        with self.assertRaisesRegex(
            ContractError,
            "決定的構築結果",
        ):
            validate_scene_generation(
                generated,
                parent_generation=parent,
                continuity=continuity_value,
                scene_commit=commit,
            )


if __name__ == "__main__":
    unittest.main()
