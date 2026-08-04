from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.candidate_stage import CandidateStageRunner
from storycraft.scene_continuity_stage import SceneContinuityStageService
from storycraft.selection_authority import DEFAULT_CONTENT_VALIDATORS, resolve_selection
from storycraft.series_contracts import ContractError


NOW = "2026-07-29T00:00:00Z"
REQUEST = {"title": "t", "genre": ["g"], "premise": "p", "required_elements": [], "avoid": [], "ending_preference": "e", "volume_count": 4, "language": "ja"}


def write_record(root: Path, directory: str, artifact_id: str, record: dict) -> None:
    path = root / directory / artifact_id / "record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def snapshot(selection_id: str, slots: dict[str, str], parent: str | None = None) -> dict:
    return {"schema_version": 1, "selection_id": selection_id, "input_selection_id": parent, "slots": slots, "created_at": NOW}


class SelectionAuthorityTests(unittest.TestCase):
    def test_review_prose_evidence_uses_utf8_byte_boundaries(self) -> None:
        review = {
            "schema_version": "review-response-v1", "decision": "issues",
            "issues": [{"severity": "notice", "evidence_locations": ["prose:3"], "explanation": "n"}],
        }
        self.assertEqual(CandidateStageRunner._review_with_evidence(review, {"text": "本文"}), review)
        bad = json.loads(json.dumps(review).replace("prose:3", "prose:1"))
        with self.assertRaises(ContractError):
            CandidateStageRunner._review_with_evidence(bad, {"text": "本文"})
        legacy = json.loads(json.dumps(review).replace("prose:3", "offset:0"))
        with self.assertRaises(ContractError):
            CandidateStageRunner._review_with_evidence(legacy, {"text": "本文"})
        bare_field = json.loads(json.dumps(review).replace("prose:3", "text"))
        with self.assertRaises(ContractError):
            CandidateStageRunner._review_with_evidence(bare_field, {"text": "本文"})
        paragraph_review = {
            "schema_version": "review-response-v1", "decision": "issues",
            "issues": [{"severity": "notice", "evidence_locations": ["paragraph:1"], "explanation": "n"}],
        }
        paragraph_text = {"text": "第一\n\n第二"}
        self.assertEqual(CandidateStageRunner._review_with_evidence(paragraph_review, paragraph_text), paragraph_review)
        self.assertTrue(SceneContinuityStageService._evidence_is_in_prose("paragraph:1", paragraph_text["text"]))
        with self.assertRaises(ContractError):
            CandidateStageRunner._review_with_evidence(
                json.loads(json.dumps(paragraph_review).replace("paragraph:1", "paragraph:2")), paragraph_text,
            )

    @staticmethod
    def _scene_plan() -> dict:
        return {
            "purpose": "場面",
            "pov_character_id": "char-main",
            "participant_ids": ["char-main"],
            "location_id": "loc-main",
            "starting_conditions": ["開始"],
            "intended_beats": ["展開"],
            "intended_revelations": [],
            "intended_changes": ["変化"],
            "prohibited_disclosures": [],
        }

    def test_scene_plan_is_bound_to_the_coordinate_and_parent_plans(self) -> None:
        parents = {
            "__current_slot__": "scene_plan.v01.c01.s01",
            "chapter_plan.v01.c01": {"content": {"scene_summaries": [{"scene_number": 1, "purpose": "場面"}], "ending_changes": ["変化"], "required_revelations": []}},
            "volume_plan.v01": {"content": {"chapter_summaries": [{"chapter_number": 1, "purpose": "章"}]}},
            "series_plan": {"content": {"volume_summaries": [{"volume_number": 1, "purpose": "巻", "ending_change": "変化"}]}},
        }
        DEFAULT_CONTENT_VALIDATORS["scene-plan"](self._scene_plan(), parents)
        invalid = self._scene_plan()
        invalid["purpose"] = "親にない目的"
        with self.assertRaisesRegex(ContractError, "purpose"):
            DEFAULT_CONTENT_VALIDATORS["scene-plan"](invalid, parents)

    def test_scene_card_is_bound_to_the_coordinate_scene_plan(self) -> None:
        card = {
            "pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main",
            "story_time": "夜", "purpose": "場面", "opening_state": "開始",
            "required_beats": [{"beat_id": "beat-01", "description": "展開", "required": True, "order_hint": 1}],
            "conflict": "対立", "allowed_revelations": [], "required_revelations": [], "forbidden_revelations": [],
            "allowed_updates": [], "ending_state_targets": ["変化"], "style_constraints": ["簡潔"],
        }
        inputs = {
            "__current_slot__": "scene_card.v01.c01.s01",
            "scene_plan.v01.c01.s01": {"content": self._scene_plan()},
        }
        DEFAULT_CONTENT_VALIDATORS["scene-card"](card, inputs)
        invalid = dict(card, pov_character_id="char-other")
        with self.assertRaisesRegex(ContractError, "pov_character_id"):
            DEFAULT_CONTENT_VALIDATORS["scene-card"](invalid, inputs)
        invalid_thread = dict(
            card,
            allowed_updates=[{"target_type": "unresolved_thread_states", "target_id": "未知のthread", "allowed_fields": ["status"]}],
        )
        with self.assertRaisesRegex(ContractError, "canonical thread_name"):
            DEFAULT_CONTENT_VALIDATORS["scene-card"](
                invalid_thread,
                {**inputs, "current_state": {"content": {"unresolved_thread_states": {"塔の試練": {"status": "open"}}}}},
            )

    def test_continuity_candidate_enforces_timeline_allowed_update_and_evidence(self) -> None:
        target = {"volume_number": 1, "chapter_number": 1, "scene_number": 1}
        inputs = {
            "current_state": {"content": {"story_facts": [{}], "character_knowledge": {}, "reader_disclosures": [], "unresolved_thread_states": {"塔の試練": {"status": "open"}}, "timeline_position": 2}},
            "scene_card.v01.c01.s01": {"content": {"allowed_updates": [{"target_type": "timeline_position", "target_id": "timeline_position", "allowed_fields": ["value"]}]}},
            "scene_prose.v01.c01.s01": {"content": {"text": "本文"}},
        }
        valid = {"coordinate": target, "changes": [{"op": "set", "target": "timeline_position", "path": "$.timeline_position", "value": 3, "evidence_locations": ["prose:0"]}]}
        SceneContinuityStageService._validate_content(valid, target, inputs)
        self.assertTrue(SceneContinuityStageService._evidence_is_in_prose("prose:3", "本文"))
        self.assertFalse(SceneContinuityStageService._evidence_is_in_prose("prose:4", "本文"))
        with self.assertRaisesRegex(ContractError, "timeline_position"):
            SceneContinuityStageService._validate_content({**valid, "changes": [{**valid["changes"][0], "value": 1}]}, target, inputs)
        with self.assertRaisesRegex(ContractError, "allowed_updates"):
            SceneContinuityStageService._validate_content({**valid, "changes": [{**valid["changes"][0], "target": "reader_disclosures", "path": "$.reader_disclosures.item", "value": "x"}]}, target, inputs)
        with self.assertRaisesRegex(ContractError, "evidence"):
            SceneContinuityStageService._validate_content({**valid, "changes": [{**valid["changes"][0], "evidence_locations": ["prose:99"]}]}, target, inputs)

        thread_inputs = {
            "current_state": {"content": {"story_facts": [{}], "character_knowledge": {}, "reader_disclosures": [], "unresolved_thread_states": {"塔の試練": {"status": "open"}}, "timeline_position": 2}},
            "scene_card.v01.c01.s01": {"content": {"allowed_updates": [{"target_type": "unresolved_thread_states", "target_id": "未知のthread", "allowed_fields": ["status"]}]}},
            "scene_prose.v01.c01.s01": {"content": {"text": "本文"}},
        }
        invalid_thread = {"coordinate": target, "changes": [{"op": "set", "target": "unresolved_thread_states", "path": "$.unresolved_thread_states.未知のthread.status", "value": "resolved", "evidence_locations": ["prose:0"]}]}
        with self.assertRaisesRegex(ContractError, "canonical"):
            SceneContinuityStageService._validate_content(invalid_thread, target, thread_inputs)
        canonical_thread_inputs = {
            **thread_inputs,
            "scene_card.v01.c01.s01": {"content": {"allowed_updates": [{"target_type": "unresolved_thread_states", "target_id": "塔の試練", "allowed_fields": ["status"]}]}},
        }
        for operation, value in (("add", "progressed"), ("remove", None), ("set", "invalid")):
            bad_change = {"op": operation, "target": "unresolved_thread_states", "path": "$.unresolved_thread_states.塔の試練.status", "value": value, "evidence_locations": ["prose:0"]}
            with self.assertRaisesRegex(ContractError, "canonical"):
                SceneContinuityStageService._validate_content({"coordinate": target, "changes": [bad_change]}, target, canonical_thread_inputs)

    def test_rejects_generation_thread_aliases_against_initial_design(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            settings = {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}
            write_record(root, "runtime/settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": settings, "created_at": NOW})
            parent = snapshot("selection-000001", {"request": "request-000001", "settings": "settings-000001"})
            write_record(root, "runtime/selections", "selection-000001", parent)
            initial_design = {
                "schema_version": 1,
                "core": {"logline": "英雄の旅", "premise": "選択の物語", "central_question": "何を守るのか", "themes": ["選択"], "dramatic_engine": "選択が障害を生む", "tone": ["希望"], "reader_promise": "人物の選択が結末を変える", "ending_direction": "責任を引き受ける"},
                "cast": [{"name": "主人公", "role": "英雄", "description": "選択を迫られる", "relationships": []}],
                "world": {"settings": ["剣と魔法"], "constraints": ["契約を破れない"], "institutions": ["王国"]},
                "knowledge_model": {"author_knows": ["秘密"], "character_knows": {"主人公": ["目的"]}, "reader_knows": ["目的"]},
                "unresolved_threads": [{"name": "塔の試練", "type": "goal", "required_for_ending": True, "description": "塔を登頂する"}],
                "ending_conditions": [{"thread_name": "塔の試練", "condition": "塔を登頂する"}],
            }
            write_record(root, "design/initial", "initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000001", "artifact_kind": "initial-design", "input_selection_id": "selection-000001", "created_at": NOW, "content": initial_design})
            generation = {"story_facts": [{"fact_id": "fact-000001", "value": "開始"}], "character_knowledge": {"char-main": []}, "reader_disclosures": [], "unresolved_thread_states": {"未知のthread": {"status": "open"}}, "timeline_position": 0}
            write_record(root, "generations", "gen-000001", {"schema_version": 1, "artifact_id": "gen-000001", "artifact_kind": "generation", "input_selection_id": "selection-000001", "created_at": NOW, "content": generation})
            child = snapshot("selection-000002", {"request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001", "current_state": "gen-000001"}, "selection-000001")
            with self.assertRaisesRegex(ContractError, "canonical thread_name"):
                resolve_selection(root, child)

    def test_rejects_volume_thread_goal_not_allocated_by_series_plan(self) -> None:
        series = {
            "volume_count": 4, "series_objectives": ["完結"],
            "volume_summaries": [{"volume_number": n, "purpose": f"巻{n}", "ending_change": "変化"} for n in range(1, 5)],
            "character_arc_map": {"char-main": [1]}, "relationship_arc_map": {"rel-main": [1]}, "thread_progression": {"塔の試練": [1]},
            "revelation_schedule": [], "ending_path": "完結", "global_constraints": [],
        }
        volume = {
            "title": "第一巻", "starting_state_summary": "開始", "volume_purpose": "目的", "central_conflict": "対立",
            "character_changes": {"char-main": "変化"}, "relationship_changes": {"rel-main": "変化"}, "thread_goals": {"未知のthread": "進展"}, "revelations": [],
            "chapter_summaries": [{"chapter_number": 1, "purpose": "章"}], "required_end_state": "終了", "handoff_expectations": [],
        }
        with self.assertRaisesRegex(ContractError, "canonical thread_name"):
            DEFAULT_CONTENT_VALIDATORS["volume-plan"](volume, {"__current_slot__": "volume_plan.v01", "series_plan": {"content": series}})

    def test_resolves_bootstrap_enveloped_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            value = snapshot("selection-000001", {"request": "request-000001", "settings": "settings-000001"})
            self.assertEqual(set(resolve_selection(root, value)), {"request", "settings"})

    def test_rejects_missing_authority_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = snapshot("selection-000001", {"request": "request-000001"})
            with self.assertRaises(ContractError):
                resolve_selection(root, value)

    def test_rejects_a_symlinked_selected_artifact_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            external = root / "external-request"
            write_record(root, "external", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            external.mkdir(exist_ok=True)
            (root / "inputs").mkdir()
            (root / "inputs/request-000001").symlink_to(root / "external/request-000001", target_is_directory=True)
            value = snapshot("selection-000001", {"request": "request-000001"})

            with self.assertRaisesRegex(ContractError, "directory"):
                resolve_selection(root, value)

    def test_reapplies_the_request_content_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": {"title": "t"}})
            value = snapshot("selection-000001", {"request": "request-000001"})
            with self.assertRaisesRegex(ContractError, "request content"):
                resolve_selection(root, value)

    def test_default_resolver_rejects_an_empty_selected_initial_design(self) -> None:
        """Envelope validity alone must not make a selected stage artifact usable."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            parent = snapshot("selection-000001", {"request": "request-000001", "settings": "settings-000001"})
            write_record(root, "runtime/selections", "selection-000001", parent)
            write_record(root, "design/initial", "initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000001", "artifact_kind": "initial-design", "input_selection_id": "selection-000001", "created_at": NOW, "content": {}})
            child = snapshot("selection-000002", {"initial_design": "initial-design-000001"}, "selection-000001")

            with self.assertRaisesRegex(ContractError, "initial-design content"):
                resolve_selection(root, child)

    def test_rejects_planning_count_and_coordinate_gaps(self) -> None:
        series = {"volume_count": 4, "series_objectives": ["完結"], "volume_summaries": [{"volume_number": n, "purpose": "p", "ending_change": "c"} for n in (1, 2, 3, 5)], "character_arc_map": {"c": [1]}, "relationship_arc_map": {"r": [1]}, "thread_progression": {"t": [1]}, "revelation_schedule": [{"volume_number": 1, "knowledge_id": "k"}], "ending_path": "完結", "global_constraints": []}
        volume = {"title": "巻", "starting_state_summary": "開始", "volume_purpose": "目的", "central_conflict": "対立", "character_changes": {"c": "変化"}, "relationship_changes": {"r": "変化"}, "thread_goals": {"t": "進展"}, "revelations": [], "chapter_summaries": [{"chapter_number": 1, "purpose": "章"}, {"chapter_number": 3, "purpose": "章"}], "required_end_state": "終了", "handoff_expectations": []}
        chapter = {"title": "章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"], "scene_summaries": [{"scene_number": 1, "purpose": "場面"}, {"scene_number": 3, "purpose": "場面"}], "required_revelations": [], "constraints": []}
        with self.assertRaises(ContractError):
            DEFAULT_CONTENT_VALIDATORS["series-plan"](series, {})
        with self.assertRaises(ContractError):
            DEFAULT_CONTENT_VALIDATORS["volume-plan"](volume, {})
        with self.assertRaises(ContractError):
            DEFAULT_CONTENT_VALIDATORS["chapter-plan"](chapter, {})

    def test_accepts_the_shipped_rich_initial_design_schema_and_cross_references(self) -> None:
        initial_design = {
            "schema_version": 1,
            "core": {
                "logline": "選択の代償",
                "premise": "主人公が選択の結果を引き受ける",
                "central_question": "何を守るのか",
                "themes": ["選択"],
                "dramatic_engine": "選択の結果が次の障害を生む",
                "tone": ["希望"],
                "reader_promise": "人物の選択が結末を変える",
                "ending_direction": "責任を引き受ける",
            },
            "cast": [{"name": "主人公", "role": "英雄", "description": "選択を迫られる", "relationships": []}],
            "world": {"settings": ["剣と魔法"], "constraints": ["契約を破れない"], "institutions": ["王国"]},
            "knowledge_model": {
                "author_knows": ["主人公の秘密"],
                "character_knows": {"主人公": ["自分の目的"]},
                "reader_knows": ["主人公の目的"],
            },
            "unresolved_threads": [{"name": "塔の試練", "type": "goal", "required_for_ending": True, "description": "塔を登頂する"}],
            "ending_conditions": [{"thread_name": "塔の試練", "condition": "塔を登頂する"}],
        }
        DEFAULT_CONTENT_VALIDATORS["initial-design"](initial_design, {})

    def test_default_resolver_registers_every_selected_content_kind(self) -> None:
        self.assertEqual(
            set(DEFAULT_CONTENT_VALIDATORS),
            {"request", "initial-design", "series-plan", "volume-plan", "chapter-plan", "scene-plan", "scene-card", "scene-prose", "continuity-update", "generation", "scene"},
        )

    def test_reapplies_kind_content_validator_using_the_artifact_input_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_record(root, "inputs", "request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings", "settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            parent = snapshot("selection-000001", {"request": "request-000001", "settings": "settings-000001"})
            write_record(root, "runtime/selections", "selection-000001", parent)
            write_record(root, "design/initial", "initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000001", "artifact_kind": "initial-design", "input_selection_id": "selection-000001", "created_at": NOW, "content": {"valid": False}})
            child = snapshot("selection-000002", {"initial_design": "initial-design-000001"}, "selection-000001")
            seen: list[tuple[dict, dict]] = []
            def validator(content: dict, inputs: dict) -> None:
                seen.append((content, inputs))
                if content["valid"] is not True:
                    raise ContractError("content rejected")
            with self.assertRaisesRegex(ContractError, "content rejected"):
                resolve_selection(root, child, content_validators={"initial-design": validator})
            self.assertEqual(seen[0][1]["request"]["content"], REQUEST)
