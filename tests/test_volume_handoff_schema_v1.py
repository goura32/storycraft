"""Storycraft V1 Volume Handoff契約試験。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.stages import V1_TEMPLATE_STAGES


ROOT = Path(__file__).parent.parent
GENERATION_ID = "gen-000020"


def volume_handoff_candidate() -> dict:
    return {
        "character_states": {
            "char-mio": (
                "凪への疑念を持ちながら調査を続ける。"
            ),
            "char-nagi": (
                "火災の夜に灯台へいたことだけを認めた。"
            ),
        },
        "relationship_states": {
            "rel-mio-nagi": (
                "信頼は改善したが、秘密が残る。"
            ),
        },
        "resolved_threads": [],
        "open_threads": [
            "thread-missing-memory",
            "thread-sister-trust",
        ],
        "new_constraints": [
            "地下保管庫へ入るには凪の鍵が必要",
        ],
        "ending_progress": "姉妹が対話を再開した。",
        "next_volume_requirements": [
            "旧管理記録の所在を追う",
            "町の有力者の関与を示す",
        ],
        "issues": [],
    }


def current_generation() -> dict:
    return {
        "canon.json": {
            "generation_id": GENERATION_ID,
        },
        "state.json": {
            "generation_id": GENERATION_ID,
            "characters": {
                "char-mio": {
                    "emotional_condition": "guarded",
                },
                "char-nagi": {
                    "emotional_condition": "tense",
                },
            },
            "relationships": {
                "rel-mio-nagi": {
                    "status": "estranged",
                    "trust": 3,
                },
            },
            "threads": {
                "thread-missing-memory": {
                    "status": "progressing",
                },
                "thread-sister-trust": {
                    "status": "open",
                },
            },
        },
        "evidence.json": {
            "generation_id": GENERATION_ID,
            "evidence": [],
        },
        "commit.json": {
            "generation_id": GENERATION_ID,
        },
    }


def series_plan() -> dict:
    return {
        "series_plan_id": "series-plan-0001",
        "volume_count": 4,
        "volume_summaries": [
            {
                "volume_number": number,
                "purpose": f"第{number}巻",
                "ending_change": f"第{number}巻末変化",
            }
            for number in range(1, 5)
        ],
    }


def volume_plan() -> dict:
    return {
        "volume_plan_id": "volume-plan-v01",
        "volume_number": 1,
        "series_plan_id": "series-plan-0001",
    }


def validate(
    candidate: dict,
    *,
    adopted: bool = False,
) -> None:
    ContractValidator._validate_volume_handoff(
        candidate,
        current_generation(),
        series_plan(),
        volume_plan(),
        1,
        GENERATION_ID,
        adopted=adopted,
        expected_chapter_ids=(
            ["chapter-v01-c001"]
            if adopted
            else None
        ),
        expected_scene_ids=(
            ["scene-v01-c001-s001"]
            if adopted
            else None
        ),
    )


class VolumeHandoffSchemaV1Test(unittest.TestCase):
    def test_validator_accepts_generation_authority(
        self,
    ) -> None:
        validate(volume_handoff_candidate())

    def test_validator_rejects_thread_partition(
        self,
    ) -> None:
        candidate = volume_handoff_candidate()
        candidate["resolved_threads"] = [
            "thread-missing-memory"
        ]
        candidate["open_threads"] = [
            "thread-sister-trust"
        ]

        with self.assertRaisesRegex(
            ContractError,
            "resolved_threads",
        ):
            validate(candidate)

    def test_validator_rejects_unknown_state_ids(
        self,
    ) -> None:
        candidate = volume_handoff_candidate()
        candidate["character_states"][
            "char-unknown"
        ] = "存在しない人物。"

        with self.assertRaisesRegex(
            ContractError,
            "Character ID",
        ):
            validate(candidate)

    def test_adopted_contract(self) -> None:
        adopted = {
            "schema_version": 1,
            "handoff_id": "handoff-v01",
            "volume_number": 1,
            "basis_generation_id": GENERATION_ID,
            "completed_chapter_ids": [
                "chapter-v01-c001",
            ],
            "completed_scene_ids": [
                "scene-v01-c001-s001",
            ],
            **deepcopy(volume_handoff_candidate()),
            "created_at": "2026-07-24T11:20:00Z",
        }

        validate(adopted, adopted=True)

        invalid = deepcopy(adopted)
        invalid["completed_scene_ids"] = [
            "scene-v01-c001-s002",
        ]
        with self.assertRaisesRegex(
            ContractError,
            "完了Scene順",
        ):
            validate(invalid, adopted=True)

    def test_code_only_stage_has_no_llm_assets(self) -> None:
        self.assertNotIn(
            "volume_handoff",
            V1_TEMPLATE_STAGES,
        )
        self.assertFalse(
            (
                ROOT
                / "templates/prompts/schemas/volume_handoff.json"
            ).exists()
        )
        self.assertFalse(
            (
                ROOT
                / "templates/prompts/user/volume_handoff"
            ).exists()
        )



if __name__ == "__main__":
    unittest.main()
