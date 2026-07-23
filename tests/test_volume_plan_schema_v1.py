"""Storycraft Version 1 Volume Plan契約。"""
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
from tests.test_series_plan_schema_v1 import (
    series_plan_candidate,
)


CREATED_AT = "2026-07-23T10:14:00Z"
BASIS_GENERATION_ID = "gen-000001"
VOLUME_NUMBER = 1


def adopted_series_plan() -> dict:
    return {
        "schema_version": 1,
        "series_plan_id": "series-plan-0001",
        "version": 1,
        "status": "accepted",
        "basis_generation_id": BASIS_GENERATION_ID,
        "parent_plan_id": None,
        **deepcopy(series_plan_candidate()),
        "created_at": "2026-07-23T10:12:00Z",
    }


def volume_plan_candidate() -> dict:
    return {
        "starting_state_summary": (
            "澪が海辺の町へ戻り、凪とは疎遠なまま、"
            "灯台火災の真相を調べ始める。"
        ),
        "volume_purpose": "帰郷と最初の証言を扱う",
        "central_conflict": (
            "澪は火災の真相を求めるが、凪は澪を守るため"
            "知っている事実を語ろうとしない。"
        ),
        "character_changes": {
            "char-0001": "疑念を抱くだけの状態から調査を選ぶ。",
            "char-0002": "沈黙を維持しつつ最初の手掛かりを示す。",
        },
        "relationship_changes": {
            "rel-0001": (
                "疎遠な関係の奥に互いを守ろうとする意図が見える。"
            ),
        },
        "thread_goals": {
            "thread-0001": (
                "灯台火災が事故ではない可能性を最初の謎として示す。"
            ),
            "thread-0002": (
                "姉妹が疎遠になった理由に凪の沈黙が関わると示す。"
            ),
        },
        "revelations": [
            "灯台火災は単純な事故ではない。",
        ],
        "chapter_summaries": [
            {
                "chapter_number": 1,
                "purpose": "澪を帰郷させ、町と姉妹の現在状態を示す。",
            },
            {
                "chapter_number": 2,
                "purpose": "灯台で凪と再会し、沈黙の理由を探る。",
            },
            {
                "chapter_number": 3,
                "purpose": "火災が事故ではない最初の手掛かりを得る。",
            },
        ],
        "required_end_state": "凪の関与を示す手掛かりを得る",
        "handoff_expectations": [
            "火災記録と町の証言の不一致を次巻で追える状態にする。",
            "姉妹の対話を完全には回復させず継続課題として残す。",
        ],
    }


class VolumePlanSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.design = build_accepted_initial_design(
            integrated_candidate(),
            self.brief,
            created_at="2026-07-23T10:10:00Z",
        )
        self.series_plan = adopted_series_plan()
        self.candidate = volume_plan_candidate()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
        volume_number: int = VOLUME_NUMBER,
        basis_generation_id: str = BASIS_GENERATION_ID,
    ) -> None:
        ContractValidator._validate_volume_plan(
            value,
            self.brief,
            self.design,
            self.series_plan,
            volume_number,
            basis_generation_id,
            adopted=adopted,
        )

    def adopted(self) -> dict:
        return {
            "schema_version": 1,
            "volume_plan_id": "volume-plan-v01",
            "volume_number": 1,
            "version": 1,
            "status": "accepted",
            "basis_generation_id": BASIS_GENERATION_ID,
            "series_plan_id": "series-plan-0001",
            "parent_plan_id": None,
            **deepcopy(self.candidate),
            "created_at": CREATED_AT,
        }

    def test_valid_candidate(self) -> None:
        self.validate(self.candidate)

    def test_candidate_rejects_adoption_metadata(self) -> None:
        value = deepcopy(self.candidate)
        value["volume_number"] = 1

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_target_volume_must_exist(self) -> None:
        with self.assertRaises(ContractError):
            self.validate(
                self.candidate,
                volume_number=5,
            )

    def test_all_allocated_character_ids_are_required(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        del value["character_changes"]["char-0002"]

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_character_outside_allocation_is_rejected(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["character_changes"]["char-unknown"] = "変更"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_relationship_ids_must_match_allocation(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["relationship_changes"] = {
            "rel-unknown": "変更",
        }

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_thread_ids_must_match_allocation(self) -> None:
        value = deepcopy(self.candidate)
        del value["thread_goals"]["thread-0002"]

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_revelation_count_must_match_schedule(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["revelations"] = []

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_revelation_wording_may_concretize_schedule(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["revelations"] = [
            "火災記録と現場の痕跡から、事故説へ疑いが生じる。",
        ]

        self.validate(value)

    def test_summary_wording_may_concretize_series_plan(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["volume_purpose"] = (
            "帰郷後の調査を通じて、最初の証言と"
            "姉妹の距離を具体的に描く。"
        )
        value["required_end_state"] = (
            "澪が凪の関与を疑う具体的証拠を持ち、"
            "次の調査へ進める。"
        )

        self.validate(value)

    def test_empty_unallocated_maps_are_allowed(
        self,
    ) -> None:
        series_plan = deepcopy(self.series_plan)
        for field in (
            "relationship_arc_map",
            "thread_progression",
        ):
            for identifier in series_plan[field]:
                series_plan[field][identifier] = [2]

        value = deepcopy(self.candidate)
        value["relationship_changes"] = {}
        value["thread_goals"] = {}

        ContractValidator._validate_volume_plan(
            value,
            self.brief,
            self.design,
            series_plan,
            1,
            BASIS_GENERATION_ID,
        )

    def test_chapter_numbers_must_be_consecutive(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["chapter_summaries"][1][
            "chapter_number"
        ] = 3

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_nonfinal_volume_requires_handoff_expectations(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["handoff_expectations"] = []

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_valid_adopted_plan(self) -> None:
        self.validate(self.adopted(), adopted=True)

    def test_adopted_plan_id_must_match_volume(self) -> None:
        value = self.adopted()
        value["volume_plan_id"] = "volume-plan-v02"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_plan_basis_must_match(self) -> None:
        value = self.adopted()
        value["basis_generation_id"] = "gen-000002"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_adopted_plan_requires_timezone(self) -> None:
        value = self.adopted()
        value["created_at"] = "2026-07-23T10:14:00"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_model_templates_render(self) -> None:
        context = {
            "brief": self.brief,
            "initial_design": self.design,
            "series_plan": self.series_plan,
            "current_generation": {
                "commit.json": {
                    "generation_id": BASIS_GENERATION_ID,
                },
            },
            "previous_handoff": None,
            "target_volume_number": 1,
        }

        generated = OpenAIStoryModel._render(
            "generate",
            "volume_plan",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "volume_plan",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "volume_plan",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("starting_state_summary", generated)
        self.assertIn("current Generation", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
