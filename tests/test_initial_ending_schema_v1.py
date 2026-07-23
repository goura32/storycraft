"""Storycraft Version 1 Initial Ending契約。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.series_model import OpenAIStoryModel

from tests.test_initial_knowledge_schema_v1 import (
    prerequisites,
)
from tests.test_initial_threads_schema_v1 import (
    thread_candidate,
)


def adopted_threads() -> dict:
    candidate = thread_candidate()
    return {
        "threads": [
            {
                "thread_id": f"thread-{index:04d}",
                **deepcopy(record),
            }
            for index, record in enumerate(
                candidate["threads"],
                1,
            )
        ]
    }


def ending_candidate() -> dict:
    return {
        "ending": {
            "desired_effect": (
                "痛みを残しつつ、姉妹が互いを"
                "信じ直せる希望を感じさせる。"
            ),
            "required_outcomes": [
                "澪と凪が火災への異なる認識を共有する",
                "姉妹が沈黙ではなく対話を選ぶ",
            ],
            "forbidden_outcomes": [
                "救いのない断絶で終わる",
                "露悪的な残虐描写を結末の中心にする",
            ],
            "character_end_states": {
                "char-0001": (
                    "記憶の不完全さを受け入れ、"
                    "凪との共有を選べる。"
                ),
                "char-0002": (
                    "保護のための沈黙をやめ、"
                    "澪へ対等に向き合える。"
                ),
            },
            "relationship_end_states": {
                "rel-0001": (
                    "互いの不完全な認識を"
                    "共有できる姉妹関係になる。"
                ),
            },
            "thread_requirements": [
                "thread-0001",
                "thread-0002",
            ],
            "final_revelations": [
                "灯台火災の夜に姉妹が異なって認識した事実",
            ],
            "private_notes": (
                "法的決着より姉妹の選択を中心にする。"
            ),
        },
        "long_term_arcs": [
            {
                "target_type": "character",
                "target_id": "char-0001",
                "start_state": (
                    "凪への疑念を抱え、"
                    "失われた記憶の完全な回復を求める。"
                ),
                "turning_points": [
                    "自分の認識にも欠落があると受け止める",
                    "凪の沈黙の理由と向き合う",
                ],
                "desired_end_state": (
                    "真相の独占ではなく共有を選ぶ。"
                ),
                "failure_modes": [
                    "完全な記憶だけを信頼の条件にする",
                ],
            },
            {
                "target_type": "character",
                "target_id": "char-0002",
                "start_state": (
                    "澪を守るために火災の一部を隠している。"
                ),
                "turning_points": [
                    "沈黙が澪の疑念を深めると理解する",
                    "不完全でも事実を共有する",
                ],
                "desired_end_state": (
                    "澪を対等な相手として信頼する。"
                ),
                "failure_modes": [
                    "保護を理由に最後まで情報を隠す",
                ],
            },
            {
                "target_type": "thread",
                "target_id": "thread-0001",
                "start_state": (
                    "灯台火災の夜の経験が未解決である。"
                ),
                "turning_points": [
                    "姉妹の認識差が明確になる",
                    "異なる認識を照合できる状態になる",
                ],
                "desired_end_state": (
                    "火災の経緯を姉妹が共有して受け止める。"
                ),
                "failure_modes": [
                    "入力にない犯人や証拠で解決する",
                ],
            },
            {
                "target_type": "thread",
                "target_id": "thread-0002",
                "start_state": (
                    "姉妹は互いを守ろうとして沈黙している。"
                ),
                "turning_points": [
                    "沈黙が関係を守らないと理解する",
                    "互いの秘密を言葉にする",
                ],
                "desired_end_state": (
                    "不完全な真実でも共有できる。"
                ),
                "failure_modes": [
                    "一方だけが告白して関係変化を終える",
                ],
            },
        ],
    }


class InitialEndingSchemaV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
        ) = prerequisites()
        self.threads = adopted_threads()
        self.candidate = ending_candidate()

    def validate(
        self,
        value: dict,
        *,
        adopted: bool = False,
    ) -> None:
        ContractValidator._validate_initial_ending(
            value,
            self.brief,
            self.concept,
            self.characters,
            self.relationships,
            self.threads,
            adopted=adopted,
        )

    def test_candidate_is_valid(self) -> None:
        self.validate(self.candidate)

    def test_candidate_must_not_contain_ids(self) -> None:
        value = deepcopy(self.candidate)
        value["ending"]["ending_id"] = "ending-0001"
        value["long_term_arcs"][0]["arc_id"] = "arc-0001"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_character_end_state_is_rejected(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["ending"]["character_end_states"][
            "char-9999"
        ] = "未知の人物。"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_all_principal_end_states_are_required(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["ending"]["character_end_states"].pop(
            "char-0001"
        )

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_required_threads_must_match_exactly(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["ending"]["thread_requirements"].pop()

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_unknown_arc_target_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["long_term_arcs"][0][
            "target_id"
        ] = "char-9999"

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_duplicate_arc_target_is_rejected(self) -> None:
        value = deepcopy(self.candidate)
        value["long_term_arcs"].append(
            deepcopy(value["long_term_arcs"][0])
        )

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_principal_character_arcs_are_required(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["long_term_arcs"] = [
            arc
            for arc in value["long_term_arcs"]
            if not (
                arc["target_type"] == "character"
                and arc["target_id"] == "char-0001"
            )
        ]

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_required_thread_arcs_are_required(
        self,
    ) -> None:
        value = deepcopy(self.candidate)
        value["long_term_arcs"] = [
            arc
            for arc in value["long_term_arcs"]
            if not (
                arc["target_type"] == "thread"
                and arc["target_id"] == "thread-0001"
            )
        ]

        with self.assertRaises(ContractError):
            self.validate(value)

    def test_model_templates_render(self) -> None:
        context = {
            "brief": self.brief,
            "concept": self.concept,
            "characters": self.characters,
            "relationships": self.relationships,
            "threads": self.threads,
        }
        generated = OpenAIStoryModel._render(
            "generate",
            "initial_ending",
            context=context,
        )
        reviewed = OpenAIStoryModel._render(
            "critique",
            "initial_ending",
            candidate=self.candidate,
            context=context,
        )
        revised = OpenAIStoryModel._render(
            "revision",
            "initial_ending",
            candidate=self.candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("thread_requirements", generated)
        self.assertIn("Turning Point", reviewed)
        self.assertIn(
            "引用されたfieldだけを変更",
            revised,
        )


if __name__ == "__main__":
    unittest.main()
