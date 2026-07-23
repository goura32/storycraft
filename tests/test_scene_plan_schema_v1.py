"""Storycraft Version 1 Scene Plan契約。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.initial_generation import (
    build_accepted_initial_design,
    build_initial_generation,
)
from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.series_model import OpenAIStoryModel

from tests.test_chapter_plan_schema_v1 import (
    adopted_volume_plan,
    chapter_plan_candidate,
)
from tests.test_initial_integrate_schema_v1 import (
    integrated_candidate,
)
from tests.test_initial_world_stage_v1 import load_json
from tests.test_volume_plan_schema_v1 import (
    BASIS_GENERATION_ID,
    adopted_series_plan,
)


CREATED_AT = "2026-07-24T07:10:00Z"
VOLUME_NUMBER = 1
CHAPTER_NUMBER = 1
SCENE_NUMBER = 1


def adopted_chapter_plan() -> dict:
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
        **deepcopy(chapter_plan_candidate()),
        "created_at": "2026-07-24T07:05:00Z",
    }


def scene_plan_candidate() -> dict:
    return {
        "purpose": (
            "澪を町へ到着させ、火災後の町の空気を示す。"
        ),
        "pov_character_id": "char-0001",
        "participant_ids": [
            "char-0001",
            "char-0002",
        ],
        "location_id": "loc-0002",
        "starting_conditions": [
            "澪は海辺の町へ戻ったばかりである。",
            "澪と凪は疎遠な状態にある。",
        ],
        "intended_beats": [
            "澪が町の変化を観察する。",
            "凪の所在につながる手掛かりを得る。",
        ],
        "intended_revelations": [],
        "intended_changes": [
            "澪が灯台へ向かう理由を得る。",
        ],
        "prohibited_disclosures": [
            "灯台火災の全容",
            "火災を起こした人物",
        ],
    }


class ScenePlanSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.design = build_accepted_initial_design(
            integrated_candidate(),
            self.brief,
            created_at="2026-07-24T07:00:00Z",
        )
        self.series_plan = adopted_series_plan()
        self.volume_plan = adopted_volume_plan()
        self.chapter_plan = adopted_chapter_plan()
        self.generation = build_initial_generation(
            self.design,
            generation_id=BASIS_GENERATION_ID,
            created_at="2026-07-24T07:01:00Z",
        )
        self.candidate = scene_plan_candidate()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
        volume_number: int = VOLUME_NUMBER,
        chapter_number: int = CHAPTER_NUMBER,
        scene_number: int = SCENE_NUMBER,
        basis_generation_id: str = BASIS_GENERATION_ID,
        chapter_plan: dict | None = None,
        generation: dict | None = None,
    ) -> None:
        ContractValidator._validate_scene_plan(
            value,
            self.brief,
            self.design,
            self.series_plan,
            self.volume_plan,
            chapter_plan or self.chapter_plan,
            generation or self.generation,
            volume_number,
            chapter_number,
            scene_number,
            basis_generation_id,
            adopted=adopted,
        )

    def adopted(self) -> dict:
        return {
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
            **deepcopy(self.candidate),
            "created_at": CREATED_AT,
        }

    def test_valid_candidate(self) -> None:
        self.validate(self.candidate)

    def test_candidate_rejects_adoption_metadata(self) -> None:
        value = deepcopy(self.candidate)
        value["scene_number"] = 1

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_target_volume_must_match_parent(self) -> None:
        with self.assertRaises(ContractError):
            self.validate(
                self.candidate,
                volume_number=2,
            )

    def test_target_chapter_must_match_parent(self) -> None:
        with self.assertRaises(ContractError):
            self.validate(
                self.candidate,
                chapter_number=2,
            )

    def test_target_scene_must_exist(self) -> None:
        with self.assertRaises(ContractError):
            self.validate(
                self.candidate,
                scene_number=3,
            )

    def test_unknown_pov_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["pov_character_id"] = "char-9999"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_participant_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["participant_ids"].append("char-9999")

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_pov_must_be_participant(self) -> None:
        value = deepcopy(self.candidate)
        value["participant_ids"] = ["char-0002"]

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_location_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["location_id"] = "loc-9999"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_participant_requires_current_state(self) -> None:
        generation = deepcopy(self.generation)
        del generation["state.json"]["characters"][
            "char-0002"
        ]

        with self.assertRaises(ContractError):
            self.validate(
                self.candidate,
                generation=generation,
            )

    def test_scene_revelation_count_cannot_exceed_chapter(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["intended_revelations"] = [
            "上位Planに存在しない開示",
        ]

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_revelation_wording_may_concretize_parent(
        self,
    ) -> None:
        chapter_plan = deepcopy(self.chapter_plan)
        chapter_plan["required_revelations"] = [
            "火災が事故ではない可能性を示す。",
        ]
        value = deepcopy(self.candidate)
        value["intended_revelations"] = [
            "現場の痕跡から事故ではない可能性を示す。",
        ]

        self.validate(
            value,
            chapter_plan=chapter_plan,
        )

    def test_allowed_and_prohibited_disclosure_cannot_overlap(
        self,
    ) -> None:
        chapter_plan = deepcopy(self.chapter_plan)
        chapter_plan["required_revelations"] = [
            "火災が事故ではない可能性を示す。",
        ]
        value = deepcopy(self.candidate)
        value["intended_revelations"] = [
            "火災が事故ではない可能性を示す。",
        ]
        value["prohibited_disclosures"].append(
            "火災が事故ではない可能性を示す。"
        )

        with self.assertRaises(ContractError):
            self.validate(
                value,
                chapter_plan=chapter_plan,
            )

    def test_valid_adopted_plan(self) -> None:
        self.validate(self.adopted(), adopted=True)

    def test_adopted_plan_id_must_match_target(self) -> None:
        value = self.adopted()
        value["scene_plan_id"] = "scene-plan-v01-c001-s002"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_parent_plan_must_match(self) -> None:
        value = self.adopted()
        value["chapter_plan_id"] = "chapter-plan-v01-c002"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_basis_must_match(self) -> None:
        value = self.adopted()
        value["basis_generation_id"] = "gen-000002"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_first_version_parent_plan_is_null(self) -> None:
        value = self.adopted()
        value["parent_plan_id"] = (
            "scene-plan-v01-c001-s001-v0000"
        )

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_plan_requires_timezone(self) -> None:
        value = self.adopted()
        value["created_at"] = "2026-07-24T07:10:00"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_model_templates_render(self) -> None:
        context = {
            "brief": self.brief,
            "initial_design": self.design,
            "series_plan": self.series_plan,
            "volume_plan": self.volume_plan,
            "chapter_plan": self.chapter_plan,
            "current_generation": self.generation,
            "target_volume_number": 1,
            "target_chapter_number": 1,
            "target_scene_number": 1,
        }

        for kind in ("generate", "critique", "revision"):
            kwargs = {"context": context}
            if kind != "generate":
                kwargs["candidate"] = self.candidate
            if kind == "revision":
                kwargs["critique"] = {"issues": []}

            rendered = OpenAIStoryModel._render(
                kind,
                "scene_plan",
                **kwargs,
            )
            self.assertIn("## 出力スキーマ", rendered)
            self.assertNotIn("{{", rendered)


if __name__ == "__main__":
    unittest.main()
