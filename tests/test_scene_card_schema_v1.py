"""Storycraft Version 1 Scene Card schema／意味契約。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)

from storycraft.initial_generation import (
    build_accepted_initial_design,
    build_initial_generation,
)
from tests.test_initial_integrate_schema_v1 import (
    integrated_candidate,
)
from tests.test_initial_world_stage_v1 import load_json
from tests.test_scene_plan_schema_v1 import (
    adopted_chapter_plan,
    scene_plan_candidate,
)
from tests.test_chapter_plan_schema_v1 import (
    adopted_volume_plan,
)
from tests.test_volume_plan_schema_v1 import (
    BASIS_GENERATION_ID,
    adopted_series_plan,
)


def adopted_parents() -> dict:
    brief = load_json("tests/fixtures/brief/valid.json")
    initial_design = build_accepted_initial_design(
        integrated_candidate(),
        brief,
        created_at="2026-07-24T07:00:00Z",
    )
    current_generation = build_initial_generation(
        initial_design,
        generation_id=BASIS_GENERATION_ID,
        created_at="2026-07-24T07:01:00Z",
    )
    scene_plan = {
        "schema_version": 1,
        "scene_plan_id": "scene-plan-v01-c001-s001",
        "volume_number": 1,
        "chapter_number": 1,
        "scene_number": 1,
        "version": 1,
        "status": "accepted",
        "basis_generation_id": BASIS_GENERATION_ID,
        "chapter_plan_id": "chapter-plan-v01-c001",
        "parent_plan_id": None,
        **deepcopy(scene_plan_candidate()),
        "created_at": "2026-07-24T07:10:00Z",
    }
    return {
        "brief": brief,
        "initial_design": initial_design,
        "series_plan": adopted_series_plan(),
        "volume_plan": adopted_volume_plan(),
        "chapter_plan": adopted_chapter_plan(),
        "scene_plan": scene_plan,
        "current_generation": current_generation,
    }


def scene_card_candidate() -> dict:
    return {
        "pov_character_id": "char-0001",
        "participant_ids": [
            "char-0001",
            "char-0002",
        ],
        "location_id": "loc-0001",
        "story_time": "第一巻・帰郷当日の夕方",
        "purpose": "火災の夜の手掛かりへ近づく。",
        "opening_state": (
            "澪は凪と向き合い、答えを求めている。"
        ),
        "required_beats": [
            {
                "beat_id": "beat-01",
                "description": "澪が鍵の存在に気づく。",
                "required": True,
                "order_hint": 1,
            },
            {
                "beat_id": "beat-02",
                "description": "凪が火災の夜の所在を認める。",
                "required": True,
                "order_hint": 2,
            },
        ],
        "conflict": (
            "澪は答えを求めるが、凪は全容を話せない。"
        ),
        "allowed_revelations": [
            "know-0001",
            "thread-0001",
        ],
        "required_revelations": [
            "know-0001",
        ],
        "forbidden_revelations": [
            "know-0002",
        ],
        "allowed_updates": [
            {
                "target_type": "character_state",
                "target_id": "char-0001",
                "allowed_fields": [
                    "current_location_id",
                    "knowledge_states",
                ],
            },
            {
                "target_type": "relationship_state",
                "target_id": "rel-0001",
                "allowed_fields": [
                    "trust",
                    "last_change_scene_id",
                ],
            },
            {
                "target_type": "thread_state",
                "target_id": "thread-0001",
                "allowed_fields": [
                    "progress_summary",
                    "latest_development_scene_id",
                    "status",
                ],
            },
        ],
        "ending_state_targets": [
            "澪は火災の夜について新しい事実を知る。",
        ],
        "style_constraints": [
            "三人称一元視点",
            "澪の知覚を越えない",
        ],
    }


class SceneCardSchemaV1Tests(unittest.TestCase):
    def test_valid_candidate(self) -> None:
        parents = adopted_parents()
        scene_plan = parents["scene_plan"]
        candidate = scene_card_candidate()
        candidate["pov_character_id"] = scene_plan[
            "pov_character_id"
        ]
        candidate["participant_ids"] = deepcopy(
            scene_plan["participant_ids"]
        )
        candidate["location_id"] = scene_plan["location_id"]

        ContractValidator._validate_scene_card_v1(
            candidate,
            parents["brief"],
            parents["initial_design"],
            parents["series_plan"],
            parents["volume_plan"],
            parents["chapter_plan"],
            scene_plan,
            parents["current_generation"],
            1,
            1,
            1,
            "gen-000001",
        )

    def test_metadata_is_forbidden_in_candidate(self) -> None:
        parents = adopted_parents()
        candidate = scene_card_candidate()
        candidate["pov_character_id"] = parents[
            "scene_plan"
        ]["pov_character_id"]
        candidate["participant_ids"] = deepcopy(
            parents["scene_plan"]["participant_ids"]
        )
        candidate["location_id"] = parents[
            "scene_plan"
        ]["location_id"]
        candidate["scene_id"] = "scene-v01-c001-s001"

        with self.assertRaisesRegex(
            ContractError,
            "採用metadata",
        ):
            ContractValidator._validate_scene_card_v1(
                candidate,
                parents["brief"],
                parents["initial_design"],
                parents["series_plan"],
                parents["volume_plan"],
                parents["chapter_plan"],
                parents["scene_plan"],
                parents["current_generation"],
                1,
                1,
                1,
                "gen-000001",
            )

    def test_required_revelation_must_be_allowed(self) -> None:
        parents = adopted_parents()
        candidate = scene_card_candidate()
        candidate["pov_character_id"] = parents[
            "scene_plan"
        ]["pov_character_id"]
        candidate["participant_ids"] = deepcopy(
            parents["scene_plan"]["participant_ids"]
        )
        candidate["location_id"] = parents[
            "scene_plan"
        ]["location_id"]
        candidate["required_revelations"] = ["know-0002"]

        with self.assertRaisesRegex(
            ContractError,
            "部分集合",
        ):
            ContractValidator._validate_scene_card_v1(
                candidate,
                parents["brief"],
                parents["initial_design"],
                parents["series_plan"],
                parents["volume_plan"],
                parents["chapter_plan"],
                parents["scene_plan"],
                parents["current_generation"],
                1,
                1,
                1,
                "gen-000001",
            )

    def test_update_field_must_exist(self) -> None:
        parents = adopted_parents()
        candidate = scene_card_candidate()
        candidate["pov_character_id"] = parents[
            "scene_plan"
        ]["pov_character_id"]
        candidate["participant_ids"] = deepcopy(
            parents["scene_plan"]["participant_ids"]
        )
        candidate["location_id"] = parents[
            "scene_plan"
        ]["location_id"]
        candidate["allowed_updates"][0][
            "allowed_fields"
        ] = ["invented_field"]

        with self.assertRaisesRegex(
            ContractError,
            "存在しないfield",
        ):
            ContractValidator._validate_scene_card_v1(
                candidate,
                parents["brief"],
                parents["initial_design"],
                parents["series_plan"],
                parents["volume_plan"],
                parents["chapter_plan"],
                parents["scene_plan"],
                parents["current_generation"],
                1,
                1,
                1,
                "gen-000001",
            )


if __name__ == "__main__":
    unittest.main()
