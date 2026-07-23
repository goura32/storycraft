"""Storycraft Version 1 Series Plan契約。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.initial_generation import (
    build_accepted_initial_design,
)
from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.series_model import OpenAIStoryModel

from tests.test_initial_integrate_schema_v1 import (
    integrated_candidate,
)
from tests.test_initial_world_stage_v1 import load_json


CREATED_AT = "2026-07-23T10:12:00Z"
BASIS_GENERATION_ID = "gen-000001"


def series_plan_candidate() -> dict:
    return {
        "volume_count": 4,
        "series_objectives": [
            "灯台火災の真相を段階的に明かす",
            "澪と凪の信頼を段階的に回復する",
        ],
        "volume_summaries": [
            {
                "volume_number": 1,
                "purpose": "帰郷と最初の証言を扱う",
                "ending_change": "凪の関与を示す手掛かりを得る",
            },
            {
                "volume_number": 2,
                "purpose": "町の記録と証言の不一致を追う",
                "ending_change": "隠蔽に関わる構造を把握する",
            },
            {
                "volume_number": 3,
                "purpose": "姉妹それぞれの記憶と沈黙を衝突させる",
                "ending_change": "澪が失われた記憶の核心へ近づく",
            },
            {
                "volume_number": 4,
                "purpose": "真相共有と姉妹の選択を描く",
                "ending_change": "主要Threadを評価可能な状態にする",
            },
        ],
        "character_arc_map": {
            "char-0001": [1, 2, 3, 4],
            "char-0002": [1, 2, 3, 4],
        },
        "relationship_arc_map": {
            "rel-0001": [1, 2, 3, 4],
        },
        "thread_progression": {
            "thread-0001": [1, 2, 3, 4],
            "thread-0002": [1, 2, 3, 4],
        },
        "revelation_schedule": [
            {
                "volume_number": 1,
                "knowledge_id": "know-0001",
            },
            {
                "volume_number": 3,
                "knowledge_id": "know-0002",
            },
        ],
        "ending_path": (
            "第四巻で記録と記憶を照合し、姉妹が真相を"
            "受け止めたうえで対話を選ぶ。"
        ),
        "global_constraints": [
            "残虐描写を抑制する",
            "予定を確定済み事実として扱わない",
        ],
    }


class SeriesPlanSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.design = build_accepted_initial_design(
            integrated_candidate(),
            self.brief,
            created_at="2026-07-23T10:10:00Z",
        )
        self.candidate = series_plan_candidate()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
        basis_generation_id: str = BASIS_GENERATION_ID,
    ) -> None:
        ContractValidator._validate_series_plan(
            value,
            self.brief,
            self.design,
            basis_generation_id,
            adopted=adopted,
        )

    def adopted(self) -> dict:
        return {
            "schema_version": 1,
            "series_plan_id": "series-plan-0001",
            "version": 1,
            "status": "accepted",
            "basis_generation_id": BASIS_GENERATION_ID,
            "parent_plan_id": None,
            **deepcopy(self.candidate),
            "created_at": CREATED_AT,
        }

    def test_valid_candidate(self) -> None:
        self.validate(self.candidate)

    def test_candidate_rejects_adoption_metadata(self) -> None:
        value = deepcopy(self.candidate)
        value["version"] = 1
        with self.assertRaises(ContractError):
            self.validate(value)

    def test_volume_count_must_match_brief(self) -> None:
        value = deepcopy(self.candidate)
        value["volume_count"] = 5
        with self.assertRaises(ContractError):
            self.validate(value)

    def test_volume_summaries_must_be_consecutive(self) -> None:
        value = deepcopy(self.candidate)
        value["volume_summaries"][1]["volume_number"] = 3
        with self.assertRaises(ContractError):
            self.validate(value)

    def test_all_character_ids_are_required(self) -> None:
        value = deepcopy(self.candidate)
        del value["character_arc_map"]["char-0002"]
        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_relationship_id_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["relationship_arc_map"] = {
            "rel-unknown": [1],
        }
        with self.assertRaises(ContractError):
            self.validate(value)

    def test_arc_volume_numbers_must_be_ascending(self) -> None:
        value = deepcopy(self.candidate)
        value["thread_progression"]["thread-0001"] = [
            2,
            1,
            3,
            4,
        ]
        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_knowledge_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["revelation_schedule"][0][
            "knowledge_id"
        ] = "know-unknown"
        with self.assertRaises(ContractError):
            self.validate(value)

    def test_same_knowledge_cannot_be_scheduled_twice(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["revelation_schedule"][1][
            "knowledge_id"
        ] = "know-0001"
        with self.assertRaises(ContractError):
            self.validate(value)

    def test_valid_adopted_plan(self) -> None:
        self.validate(self.adopted(), adopted=True)

    def test_adopted_plan_basis_must_match(self) -> None:
        value = self.adopted()
        value["basis_generation_id"] = "gen-000002"
        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_plan_requires_timezone(self) -> None:
        value = self.adopted()
        value["created_at"] = "2026-07-23T10:12:00"
        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_model_templates_render(self) -> None:
        context = {
            "brief": self.brief,
            "initial_design": self.design,
            "initial_generation": {
                "generation_id": BASIS_GENERATION_ID,
            },
        }
        generated = OpenAIStoryModel._render(
            "generate",
            "series_plan",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "series_plan",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "series_plan",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("volume_summaries", generated)
        self.assertIn("全Thread", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
