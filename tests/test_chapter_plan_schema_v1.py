"""Storycraft Version 1 Chapter Plan契約。"""
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
from tests.test_volume_plan_schema_v1 import (
    BASIS_GENERATION_ID,
    adopted_series_plan,
    volume_plan_candidate,
)


CREATED_AT = "2026-07-24T06:05:00Z"
VOLUME_NUMBER = 1
CHAPTER_NUMBER = 1


def adopted_volume_plan() -> dict:
    return {
        "schema_version": 1,
        "volume_plan_id": "volume-plan-v01",
        "volume_number": 1,
        "version": 1,
        "status": "accepted",
        "basis_generation_id": BASIS_GENERATION_ID,
        "series_plan_id": "series-plan-0001",
        "parent_plan_id": None,
        **deepcopy(volume_plan_candidate()),
        "created_at": "2026-07-24T06:00:00Z",
    }


def chapter_plan_candidate() -> dict:
    return {
        "chapter_purpose": (
            "澪を町へ帰郷させ、姉妹と灯台火災をめぐる"
            "現在の距離を読者へ示す。"
        ),
        "starting_conditions": [
            "澪は海辺の町へ戻ったばかりである。",
            "澪と凪は長く疎遠な状態にある。",
        ],
        "ending_changes": [
            "澪が灯台火災を自分で調べると決める。",
            "凪との再会が避けられない状況になる。",
        ],
        "scene_summaries": [
            {
                "scene_number": 1,
                "purpose": (
                    "澪を町へ到着させ、火災後の町の空気を示す。"
                ),
            },
            {
                "scene_number": 2,
                "purpose": (
                    "凪の所在を知り、灯台へ向かう動機を作る。"
                ),
            },
        ],
        "required_revelations": [],
        "constraints": [
            "火災の全容や犯人をこの章では明かさない。",
            "澪と凪の関係を回復済みにしない。",
        ],
    }


class ChapterPlanSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.design = build_accepted_initial_design(
            integrated_candidate(),
            self.brief,
            created_at="2026-07-24T05:55:00Z",
        )
        self.series_plan = adopted_series_plan()
        self.volume_plan = adopted_volume_plan()
        self.candidate = chapter_plan_candidate()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
        volume_number: int = VOLUME_NUMBER,
        chapter_number: int = CHAPTER_NUMBER,
        basis_generation_id: str = BASIS_GENERATION_ID,
        volume_plan: dict | None = None,
    ) -> None:
        ContractValidator._validate_chapter_plan(
            value,
            self.brief,
            self.design,
            self.series_plan,
            volume_plan or self.volume_plan,
            volume_number,
            chapter_number,
            basis_generation_id,
            adopted=adopted,
        )

    def adopted(self) -> dict:
        return {
            "schema_version": 1,
            "chapter_plan_id": "chapter-plan-v01-c001",
            "volume_number": 1,
            "chapter_number": 1,
            "version": 1,
            "status": "accepted",
            "basis_generation_id": BASIS_GENERATION_ID,
            "volume_plan_id": "volume-plan-v01",
            "parent_plan_id": None,
            **deepcopy(self.candidate),
            "created_at": CREATED_AT,
        }

    def test_valid_candidate(self) -> None:
        self.validate(self.candidate)

    def test_candidate_rejects_adoption_metadata(self) -> None:
        value = deepcopy(self.candidate)
        value["chapter_number"] = 1

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_target_volume_must_match_parent(self) -> None:
        with self.assertRaises(ContractError):
            self.validate(
                self.candidate,
                volume_number=2,
            )

    def test_target_chapter_must_exist(self) -> None:
        with self.assertRaises(ContractError):
            self.validate(
                self.candidate,
                chapter_number=4,
            )

    def test_scene_numbers_must_be_consecutive(self) -> None:
        value = deepcopy(self.candidate)
        value["scene_summaries"][1]["scene_number"] = 3

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_empty_volume_revelations_require_empty_chapter(
        self,
    ) -> None:
        volume_plan = deepcopy(self.volume_plan)
        volume_plan["revelations"] = []
        value = deepcopy(self.candidate)
        value["required_revelations"] = [
            "上位Planに存在しない開示",
        ]

        with self.assertRaises(ContractError):
            self.validate(
                value,
                volume_plan=volume_plan,
            )

    def test_chapter_revelation_count_cannot_exceed_volume(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["required_revelations"] = [
            "開示A",
            "開示B",
        ]

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_revelation_wording_may_concretize_parent(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["required_revelations"] = [
            "現場の痕跡から火災が事故ではない可能性を示す。",
        ]

        self.validate(value)

    def test_chapter_purpose_may_concretize_summary(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["chapter_purpose"] = (
            "帰郷した澪の視点で町の沈黙を描き、"
            "調査開始の動機を形成する。"
        )

        self.validate(value)

    def test_valid_adopted_plan(self) -> None:
        self.validate(self.adopted(), adopted=True)

    def test_adopted_plan_id_must_match_target(self) -> None:
        value = self.adopted()
        value["chapter_plan_id"] = "chapter-plan-v01-c002"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_parent_plan_must_match(self) -> None:
        value = self.adopted()
        value["volume_plan_id"] = "volume-plan-v02"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_basis_must_match(self) -> None:
        value = self.adopted()
        value["basis_generation_id"] = "gen-000002"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_first_version_parent_plan_is_null(self) -> None:
        value = self.adopted()
        value["parent_plan_id"] = "chapter-plan-v01-c001-v0000"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_plan_requires_timezone(self) -> None:
        value = self.adopted()
        value["created_at"] = "2026-07-24T06:05:00"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_model_templates_render(self) -> None:
        context = {
            "brief": self.brief,
            "volume_plan": self.volume_plan,
            "current_generation": {},
            "target_volume_number": 1,
            "target_chapter_number": 1,
        }

        for kind in ("generate", "critique", "revision"):
            kwargs = {
                "context": context,
            }
            if kind != "generate":
                kwargs["candidate"] = self.candidate
            if kind == "revision":
                kwargs["critique"] = {"issues": []}

            rendered = OpenAIStoryModel._render(
                kind,
                "chapter_plan",
                **kwargs,
            )
            self.assertIn("## 出力スキーマ", rendered)
            self.assertNotIn("{{", rendered)


if __name__ == "__main__":
    unittest.main()
