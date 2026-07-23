"""Storycraft Version 1 initial_relationships Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from storycraft.initial_characters_stage import (
    InitialCharactersStageService,
)
from storycraft.initial_concept_stage import (
    InitialConceptStageService,
)
from storycraft.initial_relationships_stage import (
    InitialRelationshipsStageService,
)
from storycraft.input_stage import InputStageService
from storycraft.series_contracts import ContractError
from storycraft.workspace import (
    create_workspace_from_brief,
    validate_workspace_layout,
)


ROOT = Path(__file__).parent.parent
CREATED_AT = "2026-07-23T14:00:00Z"
INPUT_AT = "2026-07-23T14:05:00Z"
CONCEPT_AT = "2026-07-23T14:10:00Z"
CHARACTERS_AT = "2026-07-23T14:15:00Z"
RELATIONSHIPS_AT = "2026-07-23T14:20:00Z"


def load_json(relative_path: str) -> dict:
    return json.loads(
        (ROOT / relative_path).read_text(encoding="utf-8")
    )


def load_json_from(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def character_candidate() -> dict:
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
                    "凪との関係を確かめる",
                ],
                "fears": [
                    "自分が火災へ関与していた可能性",
                ],
                "misbeliefs": [
                    "凪は自分を見捨てた",
                ],
                "strengths": [
                    "観察力",
                    "粘り強さ",
                ],
                "weaknesses": [
                    "疑念を抱くと他人を遠ざける",
                ],
                "long_term_arc": (
                    "真相の所有ではなく、共有と信頼を選ぶ。"
                ),
                "initial_state": {
                    "emotion": "凪への警戒と戸惑い",
                    "situation": "長く離れていた町へ戻った直後。",
                    "recent_goal": (
                        "火災の夜について手掛かりを得る"
                    ),
                },
            },
            {
                "name": "凪",
                "aliases": [],
                "role": "co_protagonist",
                "public_profile": (
                    "町に残り、灯台を管理している澪の姉。"
                ),
                "private_profile": (
                    "澪を守るため、"
                    "火災の夜の一部を隠している。"
                ),
                "desires": [
                    "澪を守る",
                    "町の平穏を保つ",
                ],
                "fears": [
                    "真相が澪を再び傷つけること",
                ],
                "misbeliefs": [
                    "沈黙が最善の保護になる",
                ],
                "strengths": [
                    "責任感",
                    "忍耐",
                ],
                "weaknesses": [
                    "秘密を抱え込む",
                ],
                "long_term_arc": (
                    "保護のための沈黙をやめ、"
                    "対等に真実を共有する。"
                ),
                "initial_state": {
                    "emotion": "澪との再会への緊張",
                    "situation": (
                        "町に残り、灯台を管理している。"
                    ),
                    "recent_goal": "澪へ話す内容を見極める",
                },
            },
        ]
    }


def relationship_candidate() -> dict:
    return {
        "relationships": [{
            "participant_ids": [
                "char-0001",
                "char-0002",
            ],
            "relationship_type": "sisters",
            "public_description": "距離のある姉妹。",
            "private_truth": (
                "互いを守ろうとして"
                "異なる秘密を抱えている。"
            ),
            "initial_state": {
                "status": "疎遠",
                "trust": 2,
                "affection": 7,
                "hostility": 2,
            },
            "desired_arc": (
                "沈黙による保護から、"
                "真実を共有する関係へ変わる。"
            ),
            "constraints": [
                "突然完全に和解させない",
            ],
        }]
    }


class NeverCalledModel:
    def generate(self, stage: str, context: dict) -> dict:
        raise AssertionError("model must not be called")

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        raise AssertionError("model must not be called")

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        raise AssertionError("model must not be called")


class AcceptingModel:
    def __init__(self, value: dict) -> None:
        self.value = value
        self.calls: list[tuple[str, str]] = []
        self.contexts: list[dict] = []

    def generate(self, stage: str, context: dict) -> dict:
        self.calls.append(("generate", stage))
        self.contexts.append(deepcopy(context))
        return deepcopy(self.value)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.calls.append(("critique", stage))
        self.contexts.append(deepcopy(context))
        return {"issues": []}

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        raise AssertionError("revision must not be called")


class RevisingModel:
    def __init__(self, initial: dict, revised: dict) -> None:
        self.initial = initial
        self.revised = revised
        self.reviews = 0

    def generate(self, stage: str, context: dict) -> dict:
        return deepcopy(self.initial)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.reviews += 1
        if self.reviews == 1:
            return {
                "issues": [{
                    "severity": "major",
                    "field": "relationships[0].desired_arc",
                    "description": (
                        candidate["relationships"][0][
                            "desired_arc"
                        ]
                    ),
                    "suggestion": (
                        "人物Arcに基づき書き直す"
                    ),
                }]
            }
        return {"issues": []}

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        return deepcopy(self.revised)


class NeverAcceptingModel:
    def __init__(self, value: dict) -> None:
        self.value = value
        self.review_calls = 0
        self.revision_calls = 0

    def generate(self, stage: str, context: dict) -> dict:
        return deepcopy(self.value)

    def critique(
        self,
        stage: str,
        candidate: dict,
        context: dict,
    ) -> dict:
        self.review_calls += 1
        return {
            "issues": [{
                "severity": "major",
                "field": "relationships[0].desired_arc",
                "description": (
                    candidate["relationships"][0][
                        "desired_arc"
                    ]
                ),
                "suggestion": (
                    "人物Arcに基づき書き直す"
                ),
            }]
        }

    def revision(
        self,
        stage: str,
        candidate: dict,
        critique: dict,
        context: dict,
    ) -> dict:
        self.revision_calls += 1
        revised = deepcopy(candidate)
        revised["relationships"][0]["desired_arc"] += (
            f" 修正{self.revision_calls}"
        )
        return revised


class InitialRelationshipsStageV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = load_json(
            "tests/fixtures/brief/valid.json"
        )
        self.config = load_json(
            "tests/fixtures/workspace/config.json"
        )
        self.concept = load_json(
            "tests/fixtures/initial-design/valid.json"
        )["concept"]
        self.characters_candidate = character_candidate()
        self.relationships = relationship_candidate()

    def create_workspace(self, temporary: str) -> Path:
        workspace = Path(temporary) / "novel"
        create_workspace_from_brief(
            workspace,
            workspace_id="ws-test-0001",
            brief=self.brief,
            config=self.config,
            created_at=CREATED_AT,
        )
        InputStageService(workspace).run(
            NeverCalledModel(),
            updated_at=INPUT_AT,
        )
        InitialConceptStageService(workspace).run(
            AcceptingModel(self.concept),
            updated_at=CONCEPT_AT,
        )
        InitialCharactersStageService(workspace).run(
            AcceptingModel(self.characters_candidate),
            updated_at=CHARACTERS_AT,
        )
        return workspace

    def test_generate_review_adopt_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            characters = load_json_from(
                workspace
                / "design/initial/v0001/characters.json"
            )
            model = AcceptingModel(self.relationships)

            state = InitialRelationshipsStageService(
                workspace
            ).run(
                model,
                updated_at=RELATIONSHIPS_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "initial_relationships"),
                    ("critique", "initial_relationships"),
                ],
            )
            expected_context = {
                "concept": self.concept,
                "characters": characters,
            }
            self.assertEqual(
                model.contexts,
                [expected_context, expected_context],
            )
            self.assertEqual(
                state["current_stage"],
                "initial_world",
            )
            self.assertIsNone(state["active_candidate"])

            adopted = load_json_from(
                workspace
                / "design/initial/v0001/relationships.json"
            )
            self.assertEqual(
                adopted["relationships"][0][
                    "relationship_id"
                ],
                "rel-0001",
            )
            self.assertEqual(
                adopted["relationships"][0][
                    "participant_ids"
                ],
                ["char-0001", "char-0002"],
            )
            validate_workspace_layout(workspace)

            candidate = load_json_from(
                workspace
                / "runtime/candidates/initial_relationships"
                / "candidate-000003/v0001/candidate.json"
            )
            self.assertNotIn(
                "relationship_id",
                candidate["content"]["relationships"][0],
            )

    def test_revision_creates_new_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            revised = deepcopy(self.relationships)
            revised["relationships"][0]["desired_arc"] = (
                "疑念と沈黙から、"
                "対等に真実を共有する姉妹関係へ変わる。"
            )

            state = InitialRelationshipsStageService(
                workspace
            ).run(
                RevisingModel(self.relationships, revised),
                updated_at=RELATIONSHIPS_AT,
            )

            root = (
                workspace
                / "runtime/candidates/initial_relationships"
                / "candidate-000003"
            )
            self.assertEqual(
                load_json_from(
                    root / "v0001/status.json"
                )["status"],
                "needs_revision",
            )
            self.assertEqual(
                load_json_from(
                    root / "v0002/status.json"
                )["status"],
                "accepted",
            )
            self.assertTrue(
                (root / "v0002/revision.json").is_file()
            )
            self.assertEqual(
                state["current_stage"],
                "initial_world",
            )

    def test_revision_limit_blocks_without_adoption(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            model = NeverAcceptingModel(self.relationships)

            state = InitialRelationshipsStageService(
                workspace
            ).run(
                model,
                updated_at=RELATIONSHIPS_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "revision_limit",
            )
            self.assertEqual(
                state["active_candidate"],
                {
                    "kind": "initial_relationships",
                    "candidate_id": "candidate-000003",
                    "version": 3,
                },
            )
            self.assertEqual(model.review_calls, 3)
            self.assertEqual(model.revision_calls, 2)
            self.assertFalse(
                (
                    workspace
                    / "design/initial/v0001/relationships.json"
                ).exists()
            )

    def test_invalid_generation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            invalid = deepcopy(self.relationships)
            invalid["relationships"][0][
                "participant_ids"
            ][1] = "char-9999"

            state = InitialRelationshipsStageService(
                workspace
            ).run(
                AcceptingModel(invalid),
                updated_at=RELATIONSHIPS_AT,
            )

            self.assertEqual(state["status"], "blocked")
            self.assertEqual(
                state["stop_reason"],
                "manual_review_required",
            )
            self.assertIsNone(state["active_candidate"])

    def test_workspace_rejects_invalid_adopted_relationship(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = self.create_workspace(temporary)
            InitialRelationshipsStageService(workspace).run(
                AcceptingModel(self.relationships),
                updated_at=RELATIONSHIPS_AT,
            )

            path = (
                workspace
                / "design/initial/v0001/relationships.json"
            )
            invalid = load_json_from(path)
            invalid["relationships"][0][
                "participant_ids"
            ][1] = "char-9999"
            path.write_text(
                json.dumps(
                    invalid,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
