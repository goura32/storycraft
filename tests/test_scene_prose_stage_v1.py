"""Storycraft Version 1 scene_prose Stage契約。"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from storycraft.run_state import RunStateStore
from storycraft.scene_card_stage import SceneCardStageService
from storycraft.scene_prose_stage import SceneProseStageService
from storycraft.series_contracts import ContractError
from storycraft.workspace import validate_workspace_layout

from tests.test_initial_world_stage_v1 import (
    AcceptingModel,
    load_json_from,
)
from tests.test_scene_card_stage_v1 import (
    CARD_AT,
    create_scene_card_workspace,
    matching_card,
)


PROSE_AT = "2026-07-24T09:20:00Z"
PROSE = Path(
    "tests/fixtures/scene/prose.md"
).read_text(encoding="utf-8").strip()


def create_scene_prose_workspace(temporary: str) -> Path:
    workspace = create_scene_card_workspace(temporary)
    SceneCardStageService(workspace).run(
        AcceptingModel(matching_card()),
        updated_at=CARD_AT,
    )
    return workspace


class AcceptingProseModel:
    def __init__(self, prose: str) -> None:
        self.prose = prose
        self.calls: list[tuple[str, str]] = []
        self.generate_contexts: list[dict] = []
        self.review_contexts: list[dict] = []

    def generate_prose(
        self,
        stage: str,
        context: dict,
    ) -> str:
        self.calls.append(("generate", stage))
        self.generate_contexts.append(deepcopy(context))
        return self.prose

    def critique_prose(
        self,
        stage: str,
        candidate: str,
        context: dict,
    ) -> dict:
        self.calls.append(("critique", stage))
        self.review_contexts.append(deepcopy(context))
        return {"issues": []}

    def revision_prose(
        self,
        stage: str,
        candidate: str,
        critique: dict,
        context: dict,
    ) -> str:
        raise AssertionError("revision must not be called")


class RevisingProseModel(AcceptingProseModel):
    def __init__(self, initial: str, revised: str) -> None:
        super().__init__(initial)
        self.revised = revised
        self.reviews = 0

    def critique_prose(
        self,
        stage: str,
        candidate: str,
        context: dict,
    ) -> dict:
        self.calls.append(("critique", stage))
        self.review_contexts.append(deepcopy(context))
        self.reviews += 1
        if self.reviews == 1:
            return {
                "issues": [{
                    "severity": "major",
                    "field": "第1段落",
                    "description": "情景が不足している。",
                    "suggestion": "潮風の描写を加える。",
                }],
            }
        return {"issues": []}

    def revision_prose(
        self,
        stage: str,
        candidate: str,
        critique: dict,
        context: dict,
    ) -> str:
        self.calls.append(("revision", stage))
        return self.revised


class SceneProseStageV1Tests(unittest.TestCase):
    def test_generate_review_adopt_and_advance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_prose_workspace(temporary)
            model = AcceptingProseModel(PROSE)

            state = SceneProseStageService(workspace).run(
                model,
                updated_at=PROSE_AT,
            )

            self.assertEqual(
                model.calls,
                [
                    ("generate", "scene_prose_v1"),
                    ("critique", "scene_prose_v1"),
                ],
            )
            self.assertEqual(
                state["current_stage"],
                "scene_continuity",
            )
            self.assertEqual(
                state["active_scene_id"],
                "scene-v01-c001-s001",
            )
            self.assertEqual(
                state["current_generation_id"],
                "gen-000001",
            )
            self.assertEqual(
                state["current_target"]["prose_version"],
                1,
            )

            staging = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
            )
            self.assertEqual(
                (staging / "prose.md")
                .read_text(encoding="utf-8"),
                PROSE + "\n",
            )

            candidate_root = (
                workspace
                / "runtime/candidates/scene_prose"
                / "candidate-000014/v0001"
            )
            self.assertEqual(
                (candidate_root / "candidate.md")
                .read_text(encoding="utf-8"),
                PROSE + "\n",
            )
            metadata = load_json_from(
                candidate_root / "candidate.json"
            )
            self.assertEqual(
                metadata["content_path"],
                "candidate.md",
            )
            self.assertNotIn("content", metadata)

            writer_context = model.generate_contexts[0]
            serialized = json.dumps(
                writer_context,
                ensure_ascii=False,
            )
            self.assertIn(
                "灯台火災は単純な事故ではない。",
                serialized,
            )
            self.assertNotIn(
                "凪は澪を見捨てた。",
                serialized,
            )
            self.assertIn("失われた記憶", serialized)
            self.assertNotIn("姉妹の信頼", serialized)
            for forbidden in (
                "private_profile",
                "private_truth",
                "private_notes",
                "planned_resolution",
                "long_term_arcs",
                "火災の夜、澪を守るため証言の一部を隠した",
                "真相の所有ではなく、共有と信頼を選ぶ。",
                "保護のための沈黙をやめ、対等に真実を共有する。",
            ):
                self.assertNotIn(forbidden, serialized)

            review_serialized = json.dumps(
                model.review_contexts[0],
                ensure_ascii=False,
            )
            self.assertIn(
                "凪は澪を見捨てた。",
                review_serialized,
            )
            self.assertIn(
                "互いを守ろうとして異なる秘密を抱えている。",
                review_serialized,
            )
            validate_workspace_layout(workspace)

    def test_revision_creates_new_text_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_prose_workspace(temporary)
            revised = "潮風が灯台の扉を鳴らした。\n\n" + PROSE

            state = SceneProseStageService(workspace).run(
                RevisingProseModel(PROSE, revised),
                updated_at=PROSE_AT,
            )

            self.assertEqual(
                state["current_stage"],
                "scene_continuity",
            )
            root = (
                workspace
                / "runtime/candidates/scene_prose"
                / "candidate-000014"
            )
            self.assertEqual(
                load_json_from(root / "v0001/status.json")[
                    "status"
                ],
                "needs_revision",
            )
            self.assertEqual(
                load_json_from(root / "v0002/status.json")[
                    "status"
                ],
                "accepted",
            )
            self.assertTrue(
                (root / "v0002/revision.json").is_file()
            )

    def test_invalid_prose_blocks_without_adoption(self) -> None:
        invalid_values = (
            "",
            '{"本文": "物語"}',
            "```markdown\n物語本文\n```",
            "澪は char-0001 の記録を見た。",
            "# Scene\n\n澪は灯台へ向かった。",
        )
        for invalid in invalid_values:
            with self.subTest(invalid=invalid):
                with tempfile.TemporaryDirectory() as temporary:
                    workspace = create_scene_prose_workspace(
                        temporary
                    )

                    state = SceneProseStageService(workspace).run(
                        AcceptingProseModel(invalid),
                        updated_at=PROSE_AT,
                    )

                    self.assertEqual(state["status"], "blocked")
                    self.assertFalse(
                        (
                            workspace
                            / "runtime/staging"
                            / "scene-scene-v01-c001-s001"
                            / "prose.md"
                        ).exists()
                    )

    def test_stale_basis_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_prose_workspace(temporary)
            store = RunStateStore(workspace)
            state = store.load()
            state["current_target"][
                "basis_generation_id"
            ] = "gen-999999"
            store.save(state)

            with self.assertRaisesRegex(
                ContractError,
                "basis_generation_id",
            ):
                SceneProseStageService(workspace).run(
                    AcceptingProseModel(PROSE),
                    updated_at=PROSE_AT,
                )

    def test_existing_different_prose_cannot_be_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_prose_workspace(temporary)
            service = SceneProseStageService(workspace)
            service.run(
                AcceptingProseModel(PROSE),
                updated_at=PROSE_AT,
            )

            store = RunStateStore(workspace)
            state = store.load()
            state["current_stage"] = "scene_prose"
            state["current_target"].pop("prose_version", None)
            store.save(state)

            with self.assertRaises(ContractError):
                service.run(
                    AcceptingProseModel(
                        PROSE + "\n\n澪はさらに一歩進んだ。"
                    ),
                    updated_at=PROSE_AT,
                )

    def test_workspace_rejects_mutated_prose(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_prose_workspace(temporary)
            SceneProseStageService(workspace).run(
                AcceptingProseModel(PROSE),
                updated_at=PROSE_AT,
            )
            path = (
                workspace
                / "runtime/staging"
                / "scene-scene-v01-c001-s001"
                / "prose.md"
            )
            path.write_text(
                '{"本文": "改変"}\n',
                encoding="utf-8",
            )

            with self.assertRaises(ContractError):
                validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
