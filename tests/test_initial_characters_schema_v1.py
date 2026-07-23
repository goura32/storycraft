"""Storycraft Version 1 Initial Characters契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.series_model import OpenAIStoryModel


ROOT = Path(__file__).parent.parent


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )


def candidate_fixture() -> dict:
    return {
        "characters": [
            {
                "name": "澪",
                "aliases": [],
                "role": "protagonist",
                "public_profile": (
                    "記憶の一部を失い、海辺の町へ戻った女性。"
                ),
                "private_profile": (
                    "灯台火災の直前の出来事を思い出せていない。"
                ),
                "desires": [
                    "失われた記憶を理解する",
                    "凪との関係を確かめる"
                ],
                "fears": [
                    "自分が火災へ関与していた可能性"
                ],
                "misbeliefs": [
                    "凪は自分を見捨てた"
                ],
                "strengths": [
                    "観察力",
                    "粘り強さ"
                ],
                "weaknesses": [
                    "疑念を抱くと他人を遠ざける"
                ],
                "long_term_arc": (
                    "真相の所有ではなく、共有と信頼を選ぶ。"
                ),
                "initial_state": {
                    "emotion": "凪への警戒と戸惑い",
                    "situation": "長く離れていた町へ戻った直後。",
                    "recent_goal": "火災の夜について手掛かりを得る"
                }
            },
            {
                "name": "凪",
                "aliases": [],
                "role": "co_protagonist",
                "public_profile": (
                    "町に残り、灯台を管理している澪の姉。"
                ),
                "private_profile": (
                    "澪を守るため、火災の夜の一部を隠している。"
                ),
                "desires": [
                    "澪を守る",
                    "町の平穏を保つ"
                ],
                "fears": [
                    "真相が澪を再び傷つけること"
                ],
                "misbeliefs": [
                    "沈黙が最善の保護になる"
                ],
                "strengths": [
                    "責任感",
                    "忍耐"
                ],
                "weaknesses": [
                    "秘密を抱え込む"
                ],
                "long_term_arc": (
                    "保護のための沈黙をやめ、"
                    "対等に真実を共有する。"
                ),
                "initial_state": {
                    "emotion": "澪との再会への緊張",
                    "situation": "町に残り、灯台を管理している。",
                    "recent_goal": "澪へ話す内容を見極める"
                }
            }
        ]
    }


class InitialCharactersSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.concept = load_json(
            "tests/fixtures/initial-design/valid.json"
        )["concept"]
        self.candidate = candidate_fixture()

    def validate(self, value: dict, *, adopted: bool = False) -> None:
        ContractValidator._validate_initial_characters(
            value,
            self.brief,
            self.concept,
            adopted=adopted,
        )

    def test_candidate_is_valid(self) -> None:
        self.validate(self.candidate)

    def test_candidate_must_not_contain_character_id(self) -> None:
        value = deepcopy(self.candidate)
        value["characters"][0]["character_id"] = "char-0001"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_adopted_characters_require_unique_ids(self) -> None:
        value = deepcopy(self.candidate)
        for record in value["characters"]:
            record["character_id"] = "char-0001"

        with self.assertRaises(ContractError):
            self.validate(value, adopted=True)

    def test_protagonist_is_required(self) -> None:
        value = deepcopy(self.candidate)
        value["characters"][0]["role"] = "supporting"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_duplicate_names_are_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["characters"][1]["name"] = "澪"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_model_templates_render(self) -> None:
        context = {
            "brief": self.brief,
            "concept": self.concept,
        }
        generated = OpenAIStoryModel._render(
            "generate",
            "initial_characters",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "initial_characters",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "initial_characters",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("character_id", generated)
        self.assertIn("公開／秘密の分離", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
