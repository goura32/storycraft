"""Storycraft V1 Completion契約試験。"""
from __future__ import annotations

from copy import deepcopy
import unittest

from jsonschema import Draft202012Validator

from storycraft.prompt_template import get_template_loader
from storycraft.series_contracts import (
    ContractError,
    ContractValidator,
)
from storycraft.stages import Stage, V1_TEMPLATE_STAGES


GENERATION_ID = "gen-000002"
SCENE_ID = "scene-v01-c001-s001"


def current_generation(
    *,
    thread_status: str = "resolved",
) -> dict:
    return {
        "canon.json": {
            "schema_version": 1,
            "generation_id": GENERATION_ID,
        },
        "state.json": {
            "schema_version": 1,
            "generation_id": GENERATION_ID,
            "characters": {
                "char-mio": {
                    "current_location_id": "loc-lighthouse",
                },
            },
            "relationships": {
                "rel-mio-nagi": {
                    "status": "truth_shared",
                },
            },
            "threads": {
                "thread-sister-trust": {
                    "status": thread_status,
                },
            },
        },
        "evidence.json": {
            "schema_version": 1,
            "generation_id": GENERATION_ID,
            "evidence": [],
        },
        "commit.json": {
            "schema_version": 1,
            "generation_id": GENERATION_ID,
            "commit_type": "scene",
            "source_artifact_type": "scene",
            "source_artifact_id": SCENE_ID,
        },
    }


def initial_design() -> dict:
    return {
        "ending": {
            "ending_id": "ending-0001",
            "desired_effect": "救いのある静かな帰結。",
            "required_outcomes": [
                "姉妹が真実を共有する。",
            ],
            "forbidden_outcomes": [],
            "character_end_states": {
                "char-mio": (
                    "記憶の不完全さを受け入れ、"
                    "町に残る。"
                ),
            },
            "relationship_end_states": {
                "rel-mio-nagi": (
                    "互いの秘密を共有する関係。"
                ),
            },
            "thread_requirements": [
                "thread-sister-trust",
            ],
            "final_revelations": [],
            "private_notes": None,
        },
        "long_term_arcs": [],
    }


def series_plan() -> dict:
    return {
        "series_plan_id": "series-plan-0001",
        "volume_count": 1,
    }


def handoffs() -> list[dict]:
    return [{
        "schema_version": 1,
        "handoff_id": "handoff-v01",
        "volume_number": 1,
        "basis_generation_id": GENERATION_ID,
        "completed_chapter_ids": [
            "chapter-v01-c001",
        ],
        "completed_scene_ids": [SCENE_ID],
    }]


def completion_candidate() -> dict:
    return {
        "status": "complete",
        "summary": (
            "完結必須ThreadとEnding条件を満たした。"
        ),
        "thread_checks": [{
            "thread_id": "thread-sister-trust",
            "required_for_completion": True,
            "status": "resolved",
            "evidence_scene_ids": [SCENE_ID],
            "assessment": (
                "姉妹は互いの秘密を共有した。"
            ),
            "issues": [],
        }],
        "ending_checks": [
            {
                "requirement_id": (
                    "ending-desired-effect"
                ),
                "status": "satisfied",
                "evidence_scene_ids": [SCENE_ID],
                "assessment": (
                    "救いのある静かな帰結に到達した。"
                ),
                "issues": [],
            },
            {
                "requirement_id": (
                    "ending-required-outcome-001"
                ),
                "status": "satisfied",
                "evidence_scene_ids": [SCENE_ID],
                "assessment": (
                    "姉妹が真実を共有した。"
                ),
                "issues": [],
            },
        ],
        "character_arc_checks": [{
            "character_id": "char-mio",
            "planned_end_state": (
                "記憶の不完全さを受け入れ、"
                "町に残る。"
            ),
            "actual_end_state": (
                "不完全な記憶を受け入れ、"
                "町に残った。"
            ),
            "status": "satisfied",
            "evidence_scene_ids": [SCENE_ID],
            "assessment": "主要Arcを達成した。",
        }],
        "relationship_arc_checks": [{
            "relationship_id": "rel-mio-nagi",
            "planned_end_state": (
                "互いの秘密を共有する関係。"
            ),
            "actual_end_state": (
                "互いの秘密を共有する関係になった。"
            ),
            "status": "satisfied",
            "evidence_scene_ids": [SCENE_ID],
            "assessment": "主要Arcを達成した。",
        }],
        "issues": [],
    }


class CompletionSchemaV1Tests(unittest.TestCase):
    def validate(
        self,
        candidate: dict,
        *,
        generation: dict | None = None,
        adopted: bool = False,
    ) -> None:
        ContractValidator._validate_completion(
            candidate,
            generation or current_generation(),
            initial_design(),
            series_plan(),
            handoffs(),
            GENERATION_ID,
            adopted=adopted,
        )

    def test_schema_accepts_complete_candidate(self) -> None:
        schema = get_template_loader().load_schema_object(
            "generate",
            "completion",
        )
        errors = list(
            Draft202012Validator(schema).iter_errors(
                completion_candidate()
            )
        )
        self.assertEqual(errors, [])

    def test_validator_accepts_complete_candidate(
        self,
    ) -> None:
        self.validate(completion_candidate())

    def test_complete_rejects_unresolved_required_thread(
        self,
    ) -> None:
        candidate = completion_candidate()
        candidate["thread_checks"][0]["status"] = (
            "progressing"
        )

        with self.assertRaisesRegex(
            ContractError,
            "status complete",
        ):
            self.validate(
                candidate,
                generation=current_generation(
                    thread_status="progressing"
                ),
            )

    def test_incomplete_is_valid_semantic_result(
        self,
    ) -> None:
        candidate = completion_candidate()
        candidate["status"] = "incomplete"
        candidate["summary"] = (
            "完結必須Threadが未解決。"
        )
        candidate["thread_checks"][0]["status"] = (
            "progressing"
        )
        candidate["thread_checks"][0]["issues"] = [
            "完結必須Threadが未解決。",
        ]
        candidate["issues"] = [{
            "category": "required_thread",
            "description": (
                "thread-sister-trustが"
                "resolvedではない。"
            ),
        }]

        self.validate(
            candidate,
            generation=current_generation(
                thread_status="progressing"
            ),
        )

    def test_missing_ending_check_is_rejected(
        self,
    ) -> None:
        candidate = completion_candidate()
        candidate["ending_checks"].pop()

        with self.assertRaisesRegex(
            ContractError,
            "全Ending条件",
        ):
            self.validate(candidate)

    def test_unknown_evidence_scene_is_rejected(
        self,
    ) -> None:
        candidate = completion_candidate()
        candidate["ending_checks"][0][
            "evidence_scene_ids"
        ] = ["scene-v01-c001-s999"]

        with self.assertRaisesRegex(
            ContractError,
            "未確定Scene",
        ):
            self.validate(candidate)

    def test_adopted_metadata_and_precheck(
        self,
    ) -> None:
        adopted = {
            "schema_version": 1,
            "completion_id": "completion-000001",
            "basis_generation_id": GENERATION_ID,
            "precheck_summary": {
                "all_volumes_complete": True,
                "all_planned_scenes_committed": True,
                "unfinished_scene_work": False,
            },
            **completion_candidate(),
            "created_at": "2026-07-24T12:00:00Z",
        }

        self.validate(adopted, adopted=True)

    def test_prompts_render_and_stage_is_registered(
        self,
    ) -> None:
        loader = get_template_loader()
        context = {
            "initial_design": initial_design(),
            "series_plan": series_plan(),
            "current_generation": current_generation(),
            "handoffs": handoffs(),
            "completed_scene_ids": [SCENE_ID],
        }
        candidate = completion_candidate()

        generated = loader.render_user(
            "generate",
            "completion",
            context=context,
        )
        critiqued = loader.render_user(
            "critique",
            "completion",
            candidate=candidate,
            context=context,
        )
        revised = loader.render_user(
            "revision",
            "completion",
            candidate=candidate,
            critique={"issues": []},
            context=context,
        )

        self.assertIn("Completion", generated)
        self.assertIn("incomplete", critiqued)
        self.assertIn("批評", revised)
        self.assertIn(
            Stage.COMPLETION.value,
            V1_TEMPLATE_STAGES,
        )


if __name__ == "__main__":
    unittest.main()
