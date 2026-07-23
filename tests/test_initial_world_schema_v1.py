"""Storycraft Version 1 Initial World契約。"""
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


def prerequisites() -> tuple[dict, dict, dict, dict]:
    brief = load_json("tests/fixtures/brief/valid.json")
    initial = load_json(
        "tests/fixtures/initial-design/valid.json"
    )
    concept = initial["concept"]

    characters = {"characters": []}
    for index, record in enumerate(
        initial["characters"],
        1,
    ):
        copied = deepcopy(record)
        copied["character_id"] = f"char-{index:04d}"
        copied["initial_state"] = {
            "emotion": "開始時の感情",
            "situation": "開始時の状況。",
            "recent_goal": "直近の目的",
        }
        characters["characters"].append(copied)

    relationships = {
        "relationships": [{
            "relationship_id": "rel-0001",
            "participant_ids": [
                "char-0001",
                "char-0002",
            ],
            "relationship_type": "sisters",
            "public_description": "距離のある姉妹。",
            "private_truth": (
                "互いを守ろうとして異なる秘密を抱えている。"
            ),
            "initial_state": {
                "status": "疎遠",
                "trust": 2,
                "affection": 7,
                "hostility": 2,
            },
            "desired_arc": (
                "沈黙から真実を共有する関係へ変わる。"
            ),
            "constraints": [
                "突然完全に和解させない",
            ],
        }]
    }
    return brief, concept, characters, relationships


def world_candidate() -> dict:
    return {
        "world": {
            "setting_summary": (
                "海と崖に囲まれた小さな町。"
            ),
            "historical_background": (
                "十年前の灯台火災で旧管理棟が焼失した。"
            ),
            "social_structure": (
                "古くからの住民の結びつきが強い。"
            ),
            "technology_or_magic": (
                "現代日本相当。超常要素はない。"
            ),
            "cultural_norms": [
                "町の問題を外へ漏らさない",
            ],
            "major_conflicts": [
                "過去を明らかにしたい者と隠したい者の対立",
            ],
            "public_knowledge": [
                "灯台火災は事故と発表された",
            ],
            "private_truths": [
                "火災には未公開の経緯がある",
            ],
        },
        "locations": [
            {
                "name": "汐見町",
                "parent_location_index": None,
                "description": (
                    "海と崖に囲まれた小さな町。"
                ),
                "access_constraints": [],
                "public_facts": [
                    "灯台が町の象徴",
                ],
                "private_facts": [],
            },
            {
                "name": "汐見灯台",
                "parent_location_index": 0,
                "description": (
                    "岬の先に立つ白い灯台。"
                ),
                "access_constraints": [
                    "管理区域への立入りには許可が必要",
                ],
                "public_facts": [
                    "十年前に旧管理棟が焼失した",
                ],
                "private_facts": [
                    "一般には公開されていない区域がある",
                ],
            },
        ],
        "world_rules": [{
            "name": "現実的因果",
            "description": (
                "事件は人間の行動と物理的原因で説明される。"
            ),
            "scope": "series",
            "exceptions": [],
            "reader_visibility": "reader_visible",
            "change_policy": "immutable",
        }],
    }


class InitialWorldSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
        ) = prerequisites()
        self.candidate = world_candidate()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
    ) -> None:
        ContractValidator._validate_initial_world(
            value,
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
            adopted=adopted,
        )

    def test_candidate_is_valid(self) -> None:
        self.validate(self.candidate)

    def test_candidate_must_not_contain_ids(self) -> None:
        value = deepcopy(self.candidate)
        value["locations"][0]["location_id"] = "loc-0001"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_parent_must_reference_prior_location(self) -> None:
        value = deepcopy(self.candidate)
        value["locations"][0]["parent_location_index"] = 1

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_duplicate_location_names_are_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["locations"][1]["name"] = "汐見町"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_duplicate_rule_names_are_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["world_rules"].append(
            deepcopy(value["world_rules"][0])
        )

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_model_templates_render(self) -> None:
        context = {
            "brief": self.brief,
            "concept": self.concept,
            "characters": self.characters,
            "relationships": self.relationships,
        }
        generated = OpenAIStoryModel._render(
            "generate",
            "initial_world",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "initial_world",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "initial_world",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("parent_location_index", generated)
        self.assertIn("後付け", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
