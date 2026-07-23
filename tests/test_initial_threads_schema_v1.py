"""Storycraft Version 1 Initial Threads契約。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.series_model import OpenAIStoryModel

from tests.test_initial_knowledge_schema_v1 import (
    adopted_world,
    knowledge_candidate,
    prerequisites,
)


def adopted_knowledge() -> dict:
    candidate = knowledge_candidate()
    identifiers = [
        f"know-{index:04d}"
        for index in range(
            1,
            len(candidate["knowledge_facts"]) + 1,
        )
    ]
    return {
        "knowledge_facts": [
            {
                "knowledge_id": identifiers[index],
                **deepcopy(record),
            }
            for index, record in enumerate(
                candidate["knowledge_facts"]
            )
        ],
        "character_knowledge": [
            {
                "character_id": record["character_id"],
                "knowledge_id": identifiers[
                    record["knowledge_index"]
                ],
                "state": record["state"],
            }
            for record in candidate[
                "character_knowledge"
            ]
        ],
    }


def thread_candidate() -> dict:
    return {
        "threads": [
            {
                "title": "失われた記憶",
                "question": (
                    "澪は灯台火災の夜に"
                    "何を経験したのか。"
                ),
                "importance": "major",
                "kind": "mystery",
                "introduced_by": "knowledge",
                "required_for_completion": True,
                "planned_resolution": (
                    "澪と凪が異なる認識を共有し、"
                    "火災の経緯を受け止められる状態にする。"
                ),
                "reader_visibility": "reader_visible",
                "initial_status": "open",
            },
            {
                "title": "姉妹の信頼",
                "question": (
                    "澪と凪は沈黙をやめて"
                    "真実を共有できるか。"
                ),
                "importance": "supporting",
                "kind": "relationship",
                "introduced_by": "relationship",
                "required_for_completion": True,
                "planned_resolution": (
                    "互いを守るための沈黙から、"
                    "対等な共有へ関係を変化させる。"
                ),
                "reader_visibility": "reader_visible",
                "initial_status": "open",
            },
        ]
    }


class InitialThreadsSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
        ) = prerequisites()
        self.world = adopted_world()
        self.knowledge = adopted_knowledge()
        self.candidate = thread_candidate()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
    ) -> None:
        ContractValidator._validate_initial_threads(
            value,
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
            self.world,
            self.knowledge,
            adopted=adopted,
        )

    def test_candidate_is_valid(self) -> None:
        self.validate(self.candidate)

    def test_candidate_must_not_contain_thread_id(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["threads"][0]["thread_id"] = "thread-0001"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_major_is_required_for_completion(self) -> None:
        value = deepcopy(self.candidate)
        value["threads"][0][
            "required_for_completion"
        ] = False

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_major_must_start_open(self) -> None:
        value = deepcopy(self.candidate)
        value["threads"][0]["initial_status"] = "planned"
        value["threads"][0]["reader_visibility"] = "hidden"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_planned_thread_must_be_hidden(self) -> None:
        value = deepcopy(self.candidate)
        value["threads"][1]["initial_status"] = "planned"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_duplicate_questions_are_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["threads"][1]["question"] = (
            value["threads"][0]["question"]
        )

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_at_least_one_major_is_required(self) -> None:
        value = deepcopy(self.candidate)
        for record in value["threads"]:
            record["importance"] = "supporting"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_model_templates_render(self) -> None:
        context = {
            "concept": self.concept,
            "characters": self.characters,
            "relationships": self.relationships,
            "world": self.world,
            "knowledge": self.knowledge,
        }
        generated = OpenAIStoryModel._render(
            "generate",
            "initial_threads",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "initial_threads",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "initial_threads",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("required_for_completion", generated)
        self.assertIn("人物と関係", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
