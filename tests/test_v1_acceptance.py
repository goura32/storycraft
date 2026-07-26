"""Storycraft V1全工程Acceptance試験。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from typing import Any

from storycraft.run_state import RunStateStore
from storycraft.v1_workflow import V1WorkflowService
from storycraft.workspace import (
    create_workspace_from_brief,
    validate_workspace_layout,
)

from tests.test_chapter_plan_schema_v1 import (
    chapter_plan_candidate,
)
from tests.test_initial_characters_schema_v1 import (
    candidate_fixture as characters_candidate,
)
from tests.test_initial_ending_schema_v1 import (
    ending_candidate,
)
from tests.test_initial_integrate_schema_v1 import (
    integrated_candidate,
)
from tests.test_initial_knowledge_schema_v1 import (
    knowledge_candidate,
)
from tests.test_initial_relationships_schema_v1 import (
    relationships_fixture,
)
from tests.test_initial_threads_schema_v1 import (
    thread_candidate,
)
from tests.test_initial_world_schema_v1 import (
    world_candidate,
)
from tests.test_scene_plan_schema_v1 import (
    scene_plan_candidate,
)
from tests.test_series_plan_schema_v1 import (
    series_plan_candidate,
)
from tests.test_volume_plan_schema_v1 import (
    volume_plan_candidate,
)
from tests.support.validation_controls import (
    defer_workspace_validation,
)


ROOT = Path(__file__).parent.parent
CREATED_AT = "2026-07-25T03:00:00Z"

VOLUME_TITLES = {
    1: "帰郷",
    2: "欠けた記録",
    3: "火の記憶",
    4: "同じ灯",
}

CHAPTER_TITLES = {
    1: "灯台",
    2: "保管庫",
    3: "目撃",
    4: "朝の灯台",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


class AcceptanceModel:
    """V1全工程へ決定的な有効応答を返すModel。"""

    def __init__(self) -> None:
        design = load_json(
            ROOT
            / "tests/fixtures/initial-design/valid.json"
        )

        self.initial_candidates = {
            "initial_concept": design["concept"],
            "initial_characters": characters_candidate(),
            "initial_relationships": (
                relationships_fixture()
            ),
            "initial_world": world_candidate(),
            "initial_knowledge": knowledge_candidate(),
            "initial_threads": thread_candidate(),
            "initial_ending": ending_candidate(),
            "initial_integrate": integrated_candidate(),
        }

        self.calls: list[tuple[str, str]] = []
        self.prose_quotes: dict[
            str,
            list[str],
        ] = {}

    def generate(
        self,
        stage: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(("generate", stage))

        if stage in self.initial_candidates:
            return deepcopy(
                self.initial_candidates[stage]
            )

        if stage == "series_plan":
            return self._series_plan()

        if stage == "volume_plan":
            return self._volume_plan(context)

        if stage == "chapter_plan":
            return self._chapter_plan(context)

        if stage == "scene_plan":
            return self._scene_plan(context)

        if stage == "scene_card_v1":
            return self._scene_card(context)

        if stage == "scene_continuity_v1":
            return self._scene_continuity(context)

        if stage == "volume_handoff":
            return self._volume_handoff(context)

        if stage == "completion":
            return self._completion(context)

        raise AssertionError(
            f"unexpected generate stage: {stage}"
        )

    def critique(
        self,
        stage: str,
        candidate: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(("critique", stage))
        return {"issues": []}

    def revision(
        self,
        stage: str,
        candidate: dict[str, Any],
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        raise AssertionError(
            f"revision must not be called: {stage}"
        )

    def generate_prose(
        self,
        stage: str,
        context: dict[str, Any],
    ) -> str:
        self.calls.append(("generate", stage))

        if stage != "scene_prose_v1":
            raise AssertionError(
                f"unexpected prose stage: {stage}"
            )

        card = context["scene_card"]
        story_time = card["story_time"]
        volume_number = int(
            story_time.split("第", 1)[1]
            .split("巻", 1)[0]
        )
        volume_key = f"v{volume_number:02d}"

        paragraphs = [
            (
                f"第{volume_number}巻の物語は、"
                "静かな灯台の前で一歩進んだ。"
            ),
        ]

        quotes: list[str] = []

        if volume_number == 4:
            # Thread IDは本文へ出せないため、
            # Continuityで順番に対応付けられる
            # 一意な自然文を十分な数だけ用意する。
            for index in range(1, 33):
                quote = (
                    f"{index}番目の謎は、"
                    "ここですべて明らかになった。"
                )
                paragraphs.append(quote)
                quotes.append(quote)

        self.prose_quotes[volume_key] = quotes
        return "\n\n".join(paragraphs)

    def critique_prose(
        self,
        stage: str,
        candidate: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(("critique", stage))
        return {"issues": []}

    def revision_prose(
        self,
        stage: str,
        candidate: str,
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        raise AssertionError(
            f"prose revision must not be called: {stage}"
        )

    @staticmethod
    def _series_plan() -> dict[str, Any]:
        candidate = series_plan_candidate()
        return deepcopy(candidate)

    @staticmethod
    def _volume_plan(
        context: dict[str, Any],
    ) -> dict[str, Any]:
        volume_number = context[
            "target_volume_number"
        ]
        series_plan = context["series_plan"]
        summary = series_plan["volume_summaries"][
            volume_number - 1
        ]

        candidate = volume_plan_candidate()
        candidate["title"] = VOLUME_TITLES[
            volume_number
        ]
        candidate["volume_purpose"] = summary[
            "purpose"
        ]
        candidate["required_end_state"] = summary[
            "ending_change"
        ]
        candidate["chapter_summaries"] = [{
            "chapter_number": 1,
            "purpose": (
                f"第{volume_number}巻の主要変化を"
                "一章で描く。"
            ),
        }]

        revelation_count = sum(
            1
            for record in series_plan[
                "revelation_schedule"
            ]
            if (
                record["volume_number"]
                == volume_number
            )
        )
        candidate["revelations"] = [
            f"第{volume_number}巻の予定開示{index}。"
            for index in range(
                1,
                revelation_count + 1,
            )
        ]

        candidate["handoff_expectations"] = (
            []
            if (
                volume_number
                == series_plan["volume_count"]
            )
            else [
                (
                    f"第{volume_number + 1}巻へ"
                    "状態を引き継ぐ。"
                ),
            ]
        )

        return candidate

    @staticmethod
    def _chapter_plan(
        context: dict[str, Any],
    ) -> dict[str, Any]:
        volume_number = context[
            "target_volume_number"
        ]

        candidate = chapter_plan_candidate()
        candidate["title"] = CHAPTER_TITLES[
            volume_number
        ]
        candidate["chapter_purpose"] = (
            f"第{volume_number}巻の目的を"
            "一章で達成する。"
        )
        candidate["scene_summaries"] = [{
            "scene_number": 1,
            "purpose": (
                f"第{volume_number}巻の変化を"
                "一Sceneで確定する。"
            ),
        }]
        candidate["required_revelations"] = []

        return candidate

    @staticmethod
    def _scene_plan(
        context: dict[str, Any],
    ) -> dict[str, Any]:
        volume_number = context[
            "target_volume_number"
        ]

        candidate = scene_plan_candidate()
        candidate["purpose"] = (
            f"第{volume_number}巻の主要変化を描く。"
        )
        candidate["intended_revelations"] = []
        candidate["intended_changes"] = [
            f"第{volume_number}巻の状態を前進させる。",
        ]

        return candidate

    @staticmethod
    def _scene_card(
        context: dict[str, Any],
    ) -> dict[str, Any]:
        scene_plan = context["scene_plan"]
        volume_number = scene_plan["volume_number"]
        final_volume = volume_number == 4

        allowed_updates: list[dict[str, Any]] = []

        if final_volume:
            for thread in context[
                "relevant_design"
            ]["threads"]:
                allowed_updates.append({
                    "target_type": "thread_state",
                    "target_id": thread["thread_id"],
                    "allowed_fields": ["status"],
                })

        return {
            "pov_character_id": (
                scene_plan["pov_character_id"]
            ),
            "participant_ids": deepcopy(
                scene_plan["participant_ids"]
            ),
            "location_id": scene_plan["location_id"],
            "story_time": (
                f"第{volume_number}巻の終盤"
            ),
            "purpose": scene_plan["purpose"],
            "opening_state": (
                "登場人物は灯台の前で答えを求めている。"
            ),
            "required_beats": [
                {
                    "beat_id": f"beat-{index:02d}",
                    "description": beat,
                    "required": True,
                    "order_hint": index,
                }
                for index, beat in enumerate(
                    scene_plan["intended_beats"],
                    1,
                )
            ],
            "conflict": (
                "真実を語る決意と沈黙が衝突する。"
            ),
            "allowed_revelations": [],
            "required_revelations": [],
            "forbidden_revelations": [],
            "allowed_updates": allowed_updates,
            "ending_state_targets": [
                (
                    f"第{volume_number}巻の主要変化が"
                    "確定する。"
                ),
            ],
            "style_constraints": [
                "三人称一元視点",
            ],
        }

    def _scene_continuity(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        scene_id = context["scene_id"]
        volume_key = scene_id.split("-", 2)[1]
        quotes = self.prose_quotes.get(
            volume_key,
            [],
        )

        operations: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []

        thread_update_index = 0

        for allowed in context["allowed_updates"]:
            if (
                allowed["target_type"]
                != "thread_state"
                or "status"
                not in allowed["allowed_fields"]
            ):
                continue

            thread_id = allowed["target_id"]
            old_status = allowed[
                "current_value"
            ]["status"]

            if old_status == "resolved":
                continue

            if thread_update_index >= len(quotes):
                raise AssertionError(
                    "Thread更新に対応する本文引用がありません"
                )

            quote = quotes[thread_update_index]
            thread_update_index += 1
            evidence_index = len(evidence)

            evidence.append({
                "quote": quote,
                "occurrence": 1,
                "context_before": "",
                "context_after": "",
                "target_type": "thread_state",
                "target_id": thread_id,
                "change_summary": (
                    "最終SceneでThreadを解決する。"
                ),
            })
            operations.append({
                "target_type": "thread_state",
                "target_id": thread_id,
                "field": "status",
                "operation": "set",
                "old_value": old_status,
                "new_value": "resolved",
                "reason": (
                    "本文で謎の解決が明示された。"
                ),
                "evidence_indices": [
                    evidence_index,
                ],
            })

        return {
            "summary": (
                "本文で確定した変化だけを反映する。"
            ),
            "operations": operations,
            "evidence": evidence,
            "unchanged_assertions": [],
        }

    @staticmethod
    def _volume_handoff(
        context: dict[str, Any],
    ) -> dict[str, Any]:
        state = context[
            "current_generation"
        ]["state.json"]
        volume_number = context[
            "target_volume_number"
        ]
        final_volume = context["is_final_volume"]

        resolved_threads = [
            thread_id
            for thread_id, value
            in state["threads"].items()
            if value["status"] == "resolved"
        ]
        open_threads = [
            thread_id
            for thread_id
            in state["threads"]
            if thread_id not in resolved_threads
        ]

        return {
            "character_states": {
                character_id: (
                    f"第{volume_number}巻末の人物状態。"
                )
                for character_id
                in state["characters"]
            },
            "relationship_states": {
                relationship_id: (
                    f"第{volume_number}巻末の関係状態。"
                )
                for relationship_id
                in state["relationships"]
            },
            "resolved_threads": resolved_threads,
            "open_threads": open_threads,
            "new_constraints": [],
            "ending_progress": (
                f"第{volume_number}巻まで進行した。"
            ),
            "next_volume_requirements": (
                []
                if final_volume
                else [
                    (
                        f"第{volume_number + 1}巻で"
                        "物語を継続する。"
                    ),
                ]
            ),
            "issues": [],
        }

    @staticmethod
    def _completion(
        context: dict[str, Any],
    ) -> dict[str, Any]:
        design = context["initial_design"]
        ending = design["ending"]
        state = context[
            "current_generation"
        ]["state.json"]
        final_scene_id = context[
            "completed_scene_ids"
        ][-1]

        thread_checks = []
        for thread_id in ending[
            "thread_requirements"
        ]:
            thread_checks.append({
                "thread_id": thread_id,
                "required_for_completion": True,
                "status": state["threads"][
                    thread_id
                ]["status"],
                "evidence_scene_ids": [
                    final_scene_id,
                ],
                "assessment": (
                    "最終Sceneで解決を確認した。"
                ),
                "issues": [],
            })

        ending_requirement_ids = [
            "ending-desired-effect",
        ]
        ending_requirement_ids.extend(
            (
                "ending-required-outcome-"
                f"{index:03d}"
            )
            for index, _ in enumerate(
                ending["required_outcomes"],
                1,
            )
        )
        ending_requirement_ids.extend(
            (
                "ending-forbidden-outcome-"
                f"{index:03d}"
            )
            for index, _ in enumerate(
                ending["forbidden_outcomes"],
                1,
            )
        )
        ending_requirement_ids.extend(
            (
                "ending-final-revelation-"
                f"{index:03d}"
            )
            for index, _ in enumerate(
                ending["final_revelations"],
                1,
            )
        )

        return {
            "status": "complete",
            "summary": (
                "全必須ThreadとEnding条件を満たした。"
            ),
            "thread_checks": thread_checks,
            "ending_checks": [
                {
                    "requirement_id": requirement_id,
                    "status": "satisfied",
                    "evidence_scene_ids": [
                        final_scene_id,
                    ],
                    "assessment": (
                        "最終Sceneで条件達成を確認した。"
                    ),
                    "issues": [],
                }
                for requirement_id
                in ending_requirement_ids
            ],
            "character_arc_checks": [
                {
                    "character_id": character_id,
                    "planned_end_state": planned,
                    "actual_end_state": (
                        "計画された終了状態へ到達した。"
                    ),
                    "status": "satisfied",
                    "evidence_scene_ids": [
                        final_scene_id,
                    ],
                    "assessment": (
                        "人物Arcを達成した。"
                    ),
                }
                for character_id, planned
                in ending[
                    "character_end_states"
                ].items()
            ],
            "relationship_arc_checks": [
                {
                    "relationship_id": relationship_id,
                    "planned_end_state": planned,
                    "actual_end_state": (
                        "計画された関係状態へ到達した。"
                    ),
                    "status": "satisfied",
                    "evidence_scene_ids": [
                        final_scene_id,
                    ],
                    "assessment": (
                        "Relationship Arcを達成した。"
                    ),
                }
                for relationship_id, planned
                in ending[
                    "relationship_end_states"
                ].items()
            ],
            "issues": [],
        }


class V1AcceptanceTests(unittest.TestCase):
    @defer_workspace_validation()
    def test_brief_to_publication_completes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = (
                Path(temporary)
                / "acceptance-workspace"
            )
            brief = load_json(
                ROOT / "tests/fixtures/brief/valid.json"
            )
            config = load_json(
                ROOT
                / "tests/fixtures/workspace/config.json"
            )

            create_workspace_from_brief(
                workspace,
                workspace_id="ws-acceptance-0001",
                brief=brief,
                config=config,
                created_at=CREATED_AT,
            )

            model = AcceptanceModel()
            factory_calls: list[AcceptanceModel] = []

            def model_factory() -> AcceptanceModel:
                factory_calls.append(model)
                return model

            workflow = V1WorkflowService(
                workspace,
                model_factory=model_factory,
            )

            base = datetime(
                2026,
                7,
                25,
                3,
                0,
                tzinfo=timezone.utc,
            )
            states: list[dict[str, Any]] = []

            for step_number in range(1, 101):
                timestamp = (
                    base
                    + timedelta(seconds=step_number)
                ).isoformat().replace(
                    "+00:00",
                    "Z",
                )
                state = workflow.step(
                    updated_at=timestamp
                )
                states.append(state)

                if state["status"] == "completed":
                    break
                if state["status"] not in {
                    "initializing",
                    "running",
                }:
                    self.fail(
                        "workflow stopped before completion: "
                        f"{state}"
                    )
            else:
                self.fail(
                    "workflow did not finish within 100 steps"
                )

            final_state = states[-1]

            self.assertEqual(
                final_state["status"],
                "completed",
            )
            self.assertEqual(
                final_state["current_stage"],
                "publication",
            )
            self.assertEqual(
                final_state[
                    "current_publication_id"
                ],
                "pub-000001",
            )
            self.assertIsNone(
                final_state["active_candidate"]
            )
            self.assertIsNone(
                final_state["active_scene_id"]
            )
            self.assertIsNone(
                final_state["pending_commit"]
            )
            self.assertIsNone(
                final_state["stop_reason"]
            )
            self.assertIsNone(
                final_state["last_error"]
            )

            self.assertEqual(
                len(factory_calls),
                38,
            )
            self.assertTrue(
                all(
                    value is model
                    for value in factory_calls
                )
            )
            self.assertEqual(
                len(model.calls),
                76,
            )
            self.assertFalse(
                any(
                    kind == "revision"
                    for kind, _stage
                    in model.calls
                )
            )

            expected_scenes = [
                (
                    f"scene-v{volume_number:02d}"
                    "-c001-s001"
                )
                for volume_number in range(1, 5)
            ]
            self.assertEqual(
                sorted(
                    path.name
                    for path
                    in (workspace / "scenes").iterdir()
                ),
                expected_scenes,
            )

            self.assertEqual(
                sorted(
                    path.name
                    for path
                    in (workspace / "handoffs").iterdir()
                ),
                [
                    "handoff-v01",
                    "handoff-v02",
                    "handoff-v03",
                    "handoff-v04",
                ],
            )

            completion = load_json(
                workspace
                / "completion/completion-000001/"
                / "result.json"
            )
            self.assertEqual(
                completion["status"],
                "complete",
            )
            self.assertTrue(
                all(
                    check["status"] == "resolved"
                    for check
                    in completion["thread_checks"]
                )
            )

            publication = (
                workspace
                / "publications/pub-000001"
            )
            metadata = load_json(
                publication / "metadata.json"
            )
            series_markdown = (
                publication / "series.md"
            ).read_text(encoding="utf-8")

            self.assertEqual(
                metadata["volume_count"],
                4,
            )
            self.assertEqual(
                metadata["series_character_count"],
                len(series_markdown),
            )
            self.assertEqual(
                metadata["series_sha256"],
                hashlib.sha256(
                    series_markdown.encode("utf-8")
                ).hexdigest(),
            )

            for volume_number in range(1, 5):
                name = f"v{volume_number:02d}.md"
                markdown = (
                    publication / name
                ).read_text(encoding="utf-8")

                entry = metadata[
                    "volume_entries"
                ][volume_number - 1]

                self.assertEqual(
                    entry["output_name"],
                    name,
                )
                self.assertEqual(
                    entry["chapter_count"],
                    1,
                )
                self.assertEqual(
                    entry["scene_count"],
                    1,
                )
                self.assertEqual(
                    entry["character_count"],
                    len(markdown),
                )
                self.assertEqual(
                    entry["sha256"],
                    hashlib.sha256(
                        markdown.encode("utf-8")
                    ).hexdigest(),
                )
                self.assertIn(
                    VOLUME_TITLES[
                        volume_number
                    ],
                    markdown,
                )
                self.assertIn(
                    CHAPTER_TITLES[
                        volume_number
                    ],
                    markdown,
                )

            counters = load_json(
                workspace / "runtime/counters.json"
            )
            self.assertEqual(
                counters["next_candidate"],
                39,
            )
            self.assertEqual(
                counters["next_review"],
                39,
            )
            self.assertEqual(
                counters["next_revision"],
                1,
            )
            self.assertEqual(
                counters["next_generation"],
                6,
            )
            self.assertEqual(
                counters["next_completion"],
                2,
            )
            self.assertEqual(
                counters["next_publication"],
                2,
            )

            validate_workspace_layout(workspace)


if __name__ == "__main__":
    unittest.main()
