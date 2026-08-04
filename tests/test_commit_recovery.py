from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from storycraft.commit_recovery import recover_pending_commit
from storycraft.run_state import RunStateStore
from storycraft.series_contracts import ContractError

NOW = "2026-07-29T00:00:00Z"
REQUEST = {"title": "t", "genre": ["g"], "premise": "p", "required_elements": [], "avoid": [], "ending_preference": "e", "volume_count": 4, "language": "ja"}


def write_record(root: Path, relative: str, record: dict) -> None:
    path = root / relative / "record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def target(artifact_id: str, artifact_kind: str, staging_path: str, final_path: str, status: str = "pending") -> dict:
    role = {
        "adoption": "adoption_record",
        "selection": "selection_snapshot",
        "scene-commit": "scene_commit_record",
        "volume-publication": "publication_directory",
    }.get(artifact_kind, "content_artifact")
    return {
        "artifact_id": artifact_id,
        "target_kind": role,
        "artifact_kind": artifact_kind if role == "content_artifact" else None,
        "staging_path": staging_path,
        "final_path": final_path,
        "status": status,
    }


def base_state() -> dict:
    return {"schema_version": 3, "workspace_id": "ws-000001", "status": "running", "last_error": None, "current_stage": "request_intake", "current_target": {}, "current_selection_id": None, "pending_commit": {"kind": "candidate_adoption", "staging_path": "runtime/staging/adopt", "input_selection_id": None, "output_selection_id": "selection-000001", "state_update": {"current_selection_id": "selection-000001", "current_stage": "initial_design", "current_target": {}}, "targets": [target("request-000001", "request", "runtime/staging/adopt/inputs/request-000001", "inputs/request-000001"), target("adoption-000001", "adoption", "runtime/staging/adopt/runtime/adoptions/adoption-000001", "runtime/adoptions/adoption-000001"), target("selection-000001", "selection", "runtime/staging/adopt/runtime/selections/selection-000001", "runtime/selections/selection-000001")]}, "published_volumes": [], "created_at": NOW, "updated_at": NOW}


def populate_staging(root: Path) -> None:
    write_record(root, "runtime/staging/adopt/inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
    write_record(root, "runtime/staging/adopt/runtime/adoptions/adoption-000001", {"schema_version": 1, "adoption_id": "adoption-000001", "source_kind": "direct_request", "candidate_id": None, "quality_id": None, "output_content_artifact_ids": ["request-000001"], "output_selection_id": "selection-000001", "input_selection_id": None, "created_at": NOW})
    write_record(root, "runtime/staging/adopt/runtime/selections/selection-000001", {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"request": "request-000001", "settings": "settings-000001"}, "created_at": NOW})


def candidate_adoption_state() -> dict:
    state = base_state()
    state.update(current_stage="series_plan", current_selection_id="selection-000001")
    staging = "runtime/staging/candidate-adoption"
    state["pending_commit"] = {
        "kind": "candidate_adoption", "staging_path": staging, "input_selection_id": "selection-000001", "output_selection_id": "selection-000002",
        "state_update": {"current_selection_id": "selection-000002", "current_stage": "volume_plan", "current_target": {"volume_number": 1}},
        "targets": [
            target("series-plan-000001", "series-plan", f"{staging}/series-plan-000001", "design/series-plans/series-plan-000001"),
            target("adoption-000001", "adoption", f"{staging}/adoption-000001", "runtime/adoptions/adoption-000001"),
            target("selection-000002", "selection", f"{staging}/selection-000002", "runtime/selections/selection-000002"),
        ],
    }
    return state


def populate_candidate_adoption_staging(root: Path) -> None:
    staging = "runtime/staging/candidate-adoption"
    write_record(root, "runtime/selections/selection-000001", {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": {"request": "request-000001", "settings": "settings-000001"}, "created_at": NOW})
    write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
    write_record(root, "runtime/calls/call-000001", {"schema_version": 1, "call_id": "call-000001", "operation": "generate", "role": "writer", "target_candidate_id": None, "input_refs": [], "technical_attempt": 1, "format_attempt": 1, "seed": 1, "endpoint": "http://127.0.0.1", "model": "test", "settings_id": "settings-000001", "request": "request", "response": "response", "transport": "success", "validation": {"result": "valid", "checks": [], "failure_code": None}})
    write_record(root, "runtime/calls/call-000002", {"schema_version": 1, "call_id": "call-000002", "operation": "review", "role": "reviewer", "target_candidate_id": "candidate-000001", "input_refs": [], "technical_attempt": 1, "format_attempt": 1, "seed": 1, "endpoint": "http://127.0.0.1", "model": "test", "settings_id": "settings-000001", "request": "request", "response": "response", "transport": "success", "validation": {"result": "valid", "checks": [], "failure_code": None}})
    write_record(root, "candidates/candidate-000001", {"schema_version": 1, "candidate_id": "candidate-000001", "artifact_kind": "series-plan", "input_selection_id": "selection-000001", "keywords_id": None, "settings_id": "settings-000001", "payload": {"title": "plan"}, "parent_candidate_id": None, "review_record_id": None, "call_id": "call-000001", "created_at": NOW})
    write_record(root, "reviews/review-000001", {"schema_version": 1, "review_id": "review-000001", "candidate_id": "candidate-000001", "response": {"schema_version": "review-response-v1", "decision": "pass", "issues": []}, "call_id": "call-000002", "created_at": NOW})
    write_record(root, "quality/quality-000001", {"schema_version": 1, "quality_id": "quality-000001", "candidate_id": "candidate-000001", "review_record_ids": ["review-000001"], "revision_count": 0, "result": "accepted", "remaining_major_issues": [], "created_at": NOW})
    write_record(root, f"{staging}/series-plan-000001", {"schema_version": 1, "artifact_id": "series-plan-000001", "artifact_kind": "series-plan", "input_selection_id": "selection-000001", "created_at": NOW, "content": {"title": "plan"}})
    write_record(root, f"{staging}/adoption-000001", {"schema_version": 1, "adoption_id": "adoption-000001", "source_kind": "candidate", "candidate_id": "candidate-000001", "quality_id": "quality-000001", "output_content_artifact_ids": ["series-plan-000001"], "output_selection_id": "selection-000002", "input_selection_id": "selection-000001", "created_at": NOW})
    write_record(root, f"{staging}/selection-000002", {"schema_version": 1, "selection_id": "selection-000002", "input_selection_id": "selection-000001", "slots": {"request": "request-000001", "settings": "settings-000001", "series_plan": "series-plan-000001"}, "created_at": NOW})


def scene_commit_state() -> dict:
    state = base_state()
    state.update(current_stage="scene_commit", current_target={"volume_number": 1, "chapter_number": 1, "scene_number": 1}, current_selection_id="selection-000001")
    staging = "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001"
    state["pending_commit"] = {
        "kind": "scene_commit", "staging_path": staging,
        "input_selection_id": "selection-000001", "output_selection_id": "selection-000002",
        "state_update": {"current_selection_id": "selection-000002", "current_stage": "scene_plan", "current_target": {"volume_number": 1, "chapter_number": 1, "scene_number": 2}},
        "targets": [
            target("scene-v01-c01-s01-000002", "scene", f"{staging}/scene-v01-c01-s01-000002", "scenes/scene-v01-c01-s01-000002"),
            target("gen-000002", "generation", f"{staging}/gen-000002", "generations/gen-000002"),
            target("scene-commit-v01-c01-s01-000001", "scene-commit", f"{staging}/scene-commit-v01-c01-s01-000001", "scenes/scene-commit-v01-c01-s01-000001"),
            target("selection-000002", "selection", f"{staging}/selection-000002", "runtime/selections/selection-000002"),
        ],
    }
    return state


def populate_scene_commit_staging(root: Path) -> None:
    # Write the request record (required for selection-000001)
    write_record(root, "inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
    write_record(root, "runtime/selections/selection-666666", {"schema_version": 1, "selection_id": "selection-666666", "input_selection_id": None, "slots": {"request": "request-000001", "settings": "settings-000001"}, "created_at": NOW})
    write_record(root, "design/initial/initial-design-000001", {"schema_version": 1, "artifact_id": "initial-design-000001", "artifact_kind": "initial-design", "input_selection_id": "selection-666666", "created_at": NOW, "content": {"schema_version": 1, "core": {"logline": "英雄の旅", "premise": "選択の物語", "central_question": "何を守るのか", "themes": ["選択"], "dramatic_engine": "選択が障害を生む", "tone": ["希望"], "reader_promise": "人物の選択が結末を変える", "ending_direction": "責任を引き受ける"}, "cast": [{"name": "主人公", "role": "英雄", "description": "選択を迫られる", "relationships": []}], "world": {"settings": ["剣と魔法"], "constraints": ["契約を破れない"], "institutions": ["王国"]}, "knowledge_model": {"author_knows": ["秘密"], "character_knows": {"主人公": ["目的"]}, "reader_knows": ["目的"]}, "unresolved_threads": [{"name": "塔の試練", "type": "goal", "required_for_ending": True, "description": "塔を登頂する"}], "ending_conditions": [{"thread_name": "塔の試練", "condition": "塔を登頂する"}]}})
    write_record(root, "generations/gen-000001", {"schema_version": 1, "artifact_id": "gen-000001", "artifact_kind": "generation", "input_selection_id": "selection-666666", "created_at": NOW, "content": {"story_facts": [{"fact_id": "fact-000001", "value": "開始"}], "character_knowledge": {"char-main": []}, "reader_disclosures": [], "unresolved_thread_states": {}, "timeline_position": 0}})
    write_record(root, "design/series-plans/series-plan-000001", {"schema_version": 1, "artifact_id": "series-plan-000001", "artifact_kind": "series-plan", "input_selection_id": "selection-666666", "created_at": NOW, "content": {"volume_count": 4, "series_objectives": ["完結"], "volume_summaries": [{"volume_number": n, "purpose": f"巻{n}", "ending_change": "変化"} for n in range(1, 5)], "character_arc_map": {"char-main": [1]}, "relationship_arc_map": {"rel-main": [1]}, "thread_progression": {"thread-main": [1]}, "revelation_schedule": [{"volume_number": 1, "knowledge_id": "know-main"}], "ending_path": "完結", "global_constraints": []}})
    write_record(root, "design/volume-plans/volume-plan-v01-000001", {"schema_version": 1, "artifact_id": "volume-plan-v01-000001", "artifact_kind": "volume-plan", "input_selection_id": "selection-777777", "created_at": NOW, "content": {"title": "第一巻", "starting_state_summary": "開始", "volume_purpose": "目的", "central_conflict": "対立", "character_changes": {"char-main": "変化"}, "relationship_changes": {"rel-main": "変化"}, "thread_goals": {"thread-main": "進展"}, "revelations": [], "chapter_summaries": [{"chapter_number": 1, "purpose": "章1"}], "required_end_state": "次へ", "handoff_expectations": []}})
    write_record(root, "design/chapter-plans/chapter-plan-v01-c01-000001", {"schema_version": 1, "artifact_id": "chapter-plan-v01-c01-000001", "artifact_kind": "chapter-plan", "input_selection_id": "selection-888888", "created_at": NOW, "content": {"title": "第一章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"], "scene_summaries": [{"scene_number": 1, "purpose": "場面1"}], "required_revelations": [], "constraints": []}})
    write_record(root, "design/scene-plans/scene-plan-v01-c01-s01-000001", {"schema_version": 1, "artifact_id": "scene-plan-v01-c01-s01-000001", "artifact_kind": "scene-plan", "input_selection_id": "selection-999999", "created_at": NOW, "content": {"purpose": "場面1", "pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main", "starting_conditions": ["開始"], "intended_beats": ["展開"], "intended_revelations": [], "intended_changes": ["変化"], "prohibited_disclosures": []}})
    write_record(root, "runtime/selections/selection-777777", {"schema_version": 1, "selection_id": "selection-777777", "input_selection_id": "selection-666666", "slots": {"request": "request-000001", "settings": "settings-000001", "series_plan": "series-plan-000001"}, "created_at": NOW})
    write_record(root, "runtime/selections/selection-888888", {"schema_version": 1, "selection_id": "selection-888888", "input_selection_id": "selection-777777", "slots": {"request": "request-000001", "settings": "settings-000001", "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001"}, "created_at": NOW})
    write_record(root, "runtime/selections/selection-888886", {"schema_version": 1, "selection_id": "selection-888886", "input_selection_id": "selection-999999", "slots": {"request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001", "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001", "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "scene_plan.v01.c01.s01": "scene-plan-v01-c01-s01-000001", "current_state": "gen-000001"}, "created_at": NOW})
    write_record(root, "runtime/selections/selection-888885", {"schema_version": 1, "selection_id": "selection-888885", "input_selection_id": "selection-888886", "slots": {"request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001", "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001", "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "scene_plan.v01.c01.s01": "scene-plan-v01-c01-s01-000001", "current_state": "gen-000001", "scene_card.v01.c01.s01": "scene-card-v01-c01-s01-000001", "scene_prose.v01.c01.s01": "scene-prose-v01-c01-s01-000001"}, "created_at": NOW})
    write_record(root, "runtime/selections/selection-999999", {"schema_version": 1, "selection_id": "selection-999999", "input_selection_id": "selection-888888", "slots": {"request": "request-000001", "settings": "settings-000001", "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001", "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001"}, "created_at": NOW})
    # Write the selection-000001 record (which depends on the request and settings)
    input_slots = {"request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001", "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001", "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "scene_plan.v01.c01.s01": "scene-plan-v01-c01-s01-000001", "scene_card.v01.c01.s01": "scene-card-v01-c01-s01-000001", "scene_prose.v01.c01.s01": "scene-prose-v01-c01-s01-000001", "continuity_update.v01.c01.s01": "continuity-v01-c01-s01-000001", "scene_prose_adoption.v01.c01.s01": "adoption-000001", "continuity_adoption.v01.c01.s01": "adoption-000002", "scene_prose_disposition.v01.c01.s01": "quality-000001", "continuity_disposition.v01.c01.s01": "quality-000001", "current_state": "gen-000001"}
    write_record(root, "runtime/selections/selection-000001", {"schema_version": 1, "selection_id": "selection-000001", "input_selection_id": None, "slots": input_slots, "created_at": NOW})
    staging = "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001"
    write_record(root, f"{staging}/scene-v01-c01-s01-000002", {"schema_version": 1, "artifact_id": "scene-v01-c01-s01-000002", "artifact_kind": "scene", "input_selection_id": "selection-999999", "created_at": NOW, "content": {"coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1}, "scene_prose_id": "scene-prose-v01-c01-s01-000001", "continuity_update_id": "continuity-v01-c01-s01-000001", "current_state_id": "gen-000001", "scene_card_id": "scene-card-v01-c01-s01-000001", "quality_disposition_id": "quality-000001"}})
    write_record(root, f"{staging}/gen-000002", {"schema_version": 1, "artifact_id": "gen-000002", "artifact_kind": "generation", "input_selection_id": "selection-999999", "created_at": NOW, "content": {"story_facts": [{"fact_id": "fact-000001", "value": "更新"}], "character_knowledge": {"char-main": []}, "reader_disclosures": [], "unresolved_thread_states": {}, "timeline_position": 1}})
    for directory, artifact_kind, identifier in (
        ("design/scene-cards", "scene-card", "scene-card-v01-c01-s01-000001"),
        ("scenes", "scene-prose", "scene-prose-v01-c01-s01-000001"),
        ("scenes", "continuity-update", "continuity-v01-c01-s01-000001"),
        ("quality", "quality-disposition", "quality-000001"),
    ):
        input_selection_id = "selection-888886" if artifact_kind in {"scene-card", "scene-prose"} else "selection-888885" if artifact_kind == "continuity-update" else None
        record = {"schema_version": 1, "artifact_id": identifier, "artifact_kind": artifact_kind, "input_selection_id": input_selection_id, "created_at": NOW, "content": {}}
        if artifact_kind == "scene-prose":
            record["content"] = {"coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1}, "text": "本文"}
        elif artifact_kind == "continuity-update":
            record["content"] = {"coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1}, "changes": []}
        elif artifact_kind == "scene-card":
            record["content"] = {"pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main", "story_time": "夜", "purpose": "場面1", "opening_state": "開始", "required_beats": [{"beat_id": "beat-01", "description": "展開", "required": True, "order_hint": 1}], "conflict": "対立", "allowed_revelations": [], "required_revelations": [], "forbidden_revelations": [], "allowed_updates": [], "ending_state_targets": ["変化"], "style_constraints": ["簡潔"]}
        if artifact_kind == "quality-disposition":
            record = {"schema_version": 1, "quality_id": identifier, "candidate_id": "candidate-000001", "review_record_ids": ["review-000001"], "revision_count": 0, "result": "accepted", "remaining_major_issues": [], "created_at": NOW}
        write_record(root, f"{directory}/{identifier}", record)
    for adoption_id, content_id in (("adoption-000001", "scene-prose-v01-c01-s01-000001"), ("adoption-000002", "continuity-v01-c01-s01-000001")):
        write_record(root, f"runtime/adoptions/{adoption_id}", {"schema_version": 1, "adoption_id": adoption_id, "source_kind": "candidate", "candidate_id": "candidate-000001", "quality_id": "quality-000001", "output_content_artifact_ids": [content_id], "output_selection_id": "selection-000001", "input_selection_id": "selection-999999", "created_at": NOW})
    write_record(root, f"{staging}/scene-commit-v01-c01-s01-000001", {"schema_version": 1,
        "scene_commit_id": "scene-commit-v01-c01-s01-000001",
        "scene_id": "scene-v01-c01-s01-000002",
        "scene_card_id": "scene-card-v01-c01-s01-000001",
        "scene_prose_id": "scene-prose-v01-c01-s01-000001",
        "continuity_update_id": "continuity-v01-c01-s01-000001",
        "current_state_id": "gen-000002",
        "quality_disposition_id": "quality-000001",
        "volume_number": 1,
        "chapter_number": 1,
        "scene_number": 1,
        "created_at": NOW,
    })
    write_record(root, f"{staging}/selection-000002", {"schema_version": 1, "selection_id": "selection-000002", "input_selection_id": "selection-000001", "slots": {**input_slots, "scene.v01.c01.s01": "scene-v01-c01-s01-000002", "current_state": "gen-000002", "scene_commit.v01.c01.s01": "scene-commit-v01-c01-s01-000001"}, "created_at": NOW})


class CommitRecoveryTests(unittest.TestCase):
    def test_recovery_rejects_manifest_input_selection_different_from_run_state_without_moving_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = candidate_adoption_state()
            state["current_selection_id"] = "selection-000009"
            state_path = root / "runtime/run-state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            populate_candidate_adoption_staging(root)

            with self.assertRaisesRegex(ContractError, "current_selection_id"):
                recover_pending_commit(root)

            self.assertFalse((root / "design/series-plans/series-plan-000001").exists())
            self.assertTrue((root / "runtime/staging/candidate-adoption/series-plan-000001").exists())

    def test_recovery_preflights_a_later_invalid_final_before_moving_an_earlier_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = candidate_adoption_state()
            state_path = root / "runtime/run-state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            populate_candidate_adoption_staging(root)
            (root / "design/series-plans").mkdir(parents=True)
            (root / "runtime/adoptions").mkdir(parents=True)
            final_selection = root / "runtime/selections/selection-000002"
            final_selection.mkdir(parents=True)
            (final_selection / "record.json").write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(ContractError, "stagingとfinal"):
                recover_pending_commit(root)

            self.assertFalse((root / "design/series-plans/series-plan-000001").exists())
            self.assertTrue((root / "runtime/staging/candidate-adoption/series-plan-000001").exists())

    def test_recovery_preflights_candidate_lineage_before_moving_any_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = candidate_adoption_state()
            state_path = root / "runtime/run-state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            populate_candidate_adoption_staging(root)
            (root / "design/series-plans").mkdir(parents=True)
            (root / "runtime/adoptions").mkdir(parents=True)
            quality_path = root / "quality/quality-000001/record.json"
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
            quality["candidate_id"] = "candidate-999999"
            quality_path.write_text(json.dumps(quality), encoding="utf-8")

            with self.assertRaisesRegex(ContractError, "quality candidate"):
                recover_pending_commit(root)

            self.assertIsNotNone(RunStateStore(root).load()["pending_commit"])
            self.assertTrue((root / "runtime/staging/candidate-adoption/series-plan-000001").exists())
            self.assertFalse((root / "design/series-plans/series-plan-000001").exists())
            self.assertFalse((root / "runtime/adoptions/adoption-000001").exists())
            self.assertFalse((root / "runtime/selections/selection-000002").exists())

    def test_recovery_preflights_all_final_parents_before_moving_any_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = candidate_adoption_state()
            state_path = root / "runtime/run-state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state), encoding="utf-8")
            populate_candidate_adoption_staging(root)
            (root / "design/series-plans").mkdir(parents=True)

            with self.assertRaisesRegex(ContractError, "final directoryの親directory"):
                recover_pending_commit(root)

            self.assertTrue((root / "runtime/staging/candidate-adoption/series-plan-000001").exists())
            self.assertFalse((root / "design/series-plans/series-plan-000001").exists())
            self.assertTrue((root / "runtime/staging/candidate-adoption/adoption-000001").exists())

    def test_recovery_target_status_location_matrix_uses_real_filesystem(self) -> None:
        """Each target's declared status and on-disk location converges or blocks.

        The other manifest targets remain staged so a successful case proves that
        recovery continues through the whole manifest and applies its state update.
        """
        cases = (
            ("pending", "missing", False, "pending.*staging"),
            ("pending", "staging", True, None),
            ("pending", "final", True, None),
            ("pending", "both", False, "stagingとfinal"),
            ("pending", "invalid-final", False, "field構成"),
            ("finalized", "missing", False, "finalized.*final"),
            ("finalized", "staging", False, "finalized.*final"),
            ("finalized", "final", True, None),
            ("finalized", "both", False, "stagingとfinal"),
            ("finalized", "invalid-final", False, "field構成"),
        )
        for status, location, succeeds, message in cases:
            with self.subTest(status=status, location=location), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                state = base_state()
                state["pending_commit"]["targets"][0]["status"] = status
                populate_staging(root)
                for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                    (root / parent).mkdir(parents=True)
                write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
                staging = root / "runtime/staging/adopt/inputs/request-000001"
                final = root / "inputs/request-000001"
                if location in {"final", "invalid-final", "both"}:
                    final.parent.mkdir(parents=True, exist_ok=True)
                    if location == "both":
                        final.mkdir()
                        (final / "record.json").write_text(staging.joinpath("record.json").read_text(encoding="utf-8"), encoding="utf-8")
                    else:
                        staging.rename(final)
                if location == "missing":
                    staging.rename(root / "removed-target")
                if location == "invalid-final":
                    (final / "record.json").write_text("{}", encoding="utf-8")
                RunStateStore(root).save(state)

                if succeeds:
                    recovered = recover_pending_commit(root)
                    self.assertIsNone(recovered["pending_commit"])
                    self.assertEqual(recovered["current_stage"], "initial_design")
                    self.assertTrue((root / "inputs/request-000001/record.json").is_file())
                else:
                    assert message is not None
                    with self.assertRaisesRegex(ContractError, message):
                        recover_pending_commit(root)

    def test_recovery_allows_pending_staging_alongside_another_finalized_target(self) -> None:
        """Different targets may occupy their normal interrupted locations together."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = base_state()
            state["pending_commit"]["targets"][1]["status"] = "finalized"
            populate_staging(root)
            for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            (root / "runtime/staging/adopt/runtime/adoptions/adoption-000001").rename(root / "runtime/adoptions/adoption-000001")
            RunStateStore(root).save(state)

            recovered = recover_pending_commit(root)

            self.assertIsNone(recovered["pending_commit"])
            self.assertTrue((root / "inputs/request-000001/record.json").is_file())
            self.assertTrue((root / "runtime/adoptions/adoption-000001/record.json").is_file())

    def test_rejects_finalized_target_that_only_has_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            populate_staging(root)
            state = base_state()
            state["pending_commit"]["targets"][0]["status"] = "finalized"
            RunStateStore(root).save(state)

            with self.assertRaisesRegex(ContractError, "finalized.*final"):
                recover_pending_commit(root)

    def test_finalizes_only_manifest_target_directories_validates_then_applies_update_and_clears_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = base_state()
            populate_staging(root)
            for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            RunStateStore(root).save(state)
            recovered = recover_pending_commit(root)
            self.assertIsNone(recovered["pending_commit"])
            self.assertEqual(recovered["current_selection_id"], "selection-000001")
            self.assertEqual(recovered["current_stage"], "initial_design")
            self.assertTrue((root / "inputs/request-000001/record.json").is_file())
            self.assertFalse((root / "runtime/staging/adopt/inputs/request-000001").exists())

    def test_rejects_an_unlisted_directory_under_the_manifest_staging_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            populate_staging(root)
            (root / "runtime/staging/adopt/unlisted").mkdir()
            RunStateStore(root).save(base_state())
            with self.assertRaisesRegex(ContractError, "manifest外"):
                recover_pending_commit(root)

    def test_recovery_rejects_symlinked_staging_components_without_renaming_external_source(self) -> None:
        """A symlinked ancestor must not turn a manifest rename into an external move."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            populate_staging(root)
            for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            external = root / "external-source"
            (root / "runtime/staging/adopt/inputs").rename(external)
            (root / "runtime/staging/adopt/inputs").symlink_to(external, target_is_directory=True)
            RunStateStore(root).save(base_state())

            with self.assertRaisesRegex(ContractError, "symlink"):
                recover_pending_commit(root)

            self.assertTrue((external / "request-000001/record.json").is_file())
            self.assertFalse((root / "inputs/request-000001").exists())

    def test_recovery_rejects_symlinked_final_ancestor_without_renaming_into_external_tree(self) -> None:
        """Checking only final.parent misses a symlink higher in the final path."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("inputs", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            populate_candidate_adoption_staging(root)
            external_design = root / "external-design"
            (external_design / "series-plans").mkdir(parents=True)
            (root / "design").symlink_to(external_design, target_is_directory=True)
            RunStateStore(root).save(candidate_adoption_state())

            with self.assertRaisesRegex(ContractError, "symlink"):
                recover_pending_commit(root)

            self.assertTrue((root / "runtime/staging/candidate-adoption/series-plan-000001/record.json").is_file())
            self.assertFalse((external_design / "series-plans/series-plan-000001").exists())

    def test_recovery_rejects_a_candidate_adoption_when_quality_points_to_another_candidate_without_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("inputs", "design/series-plans", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            populate_candidate_adoption_staging(root)
            quality = root / "quality/quality-000001/record.json"
            value = json.loads(quality.read_text(encoding="utf-8"))
            value["candidate_id"] = "candidate-000002"
            quality.write_text(json.dumps(value), encoding="utf-8")
            RunStateStore(root).save(candidate_adoption_state())

            with self.assertRaisesRegex(ContractError, "quality candidate参照"):
                recover_pending_commit(root)

    def test_recovery_rejects_a_candidate_adoption_with_a_non_delta_output_selection_without_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("inputs", "design/series-plans", "runtime/adoptions", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "inputs/request-000001", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": REQUEST})
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            populate_candidate_adoption_staging(root)
            selection = root / "runtime/staging/candidate-adoption/selection-000002/record.json"
            value = json.loads(selection.read_text(encoding="utf-8"))
            value["slots"]["unexpected"] = "request-000001"
            selection.write_text(json.dumps(value), encoding="utf-8")
            RunStateStore(root).save(candidate_adoption_state())

            with self.assertRaisesRegex(ContractError, "slots"):
                recover_pending_commit(root)

    def test_recovers_a_real_closed_scene_commit_manifest_without_mocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("scenes", "generations", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            populate_scene_commit_staging(root)
            RunStateStore(root).save(scene_commit_state())

            recovered = recover_pending_commit(root)

            self.assertIsNone(recovered["pending_commit"])
            self.assertEqual(recovered["current_stage"], "scene_plan")
            self.assertTrue((root / "scenes/scene-commit-v01-c01-s01-000001/record.json").is_file())

    def test_scene_commit_recovery_rejects_output_selection_slot_deletion_before_move(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("scenes", "generations", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            populate_scene_commit_staging(root)
            RunStateStore(root).save(scene_commit_state())
            selection_path = root / "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001/selection-000002/record.json"
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            del selection["slots"]["scene_card.v01.c01.s01"]
            selection_path.write_text(json.dumps(selection) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ContractError, "slot delta"):
                recover_pending_commit(root)
            self.assertFalse((root / "scenes/scene-v01-c01-s01-000002").exists())
            self.assertTrue(selection_path.is_file())

    def test_scene_commit_recovery_rejects_missing_referenced_artifact_before_state_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("scenes", "generations", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            populate_scene_commit_staging(root)
            RunStateStore(root).save(scene_commit_state())
            (root / "design/scene-cards/scene-card-v01-c01-s01-000001/record.json").unlink()
            with self.assertRaisesRegex(ContractError, "immutable target"):
                recover_pending_commit(root)
            state = RunStateStore(root).load_recovery()
            self.assertIsNotNone(state["pending_commit"])
            self.assertEqual(state["current_stage"], "scene_commit")

    def test_scene_commit_recovery_rejects_wrong_input_selection_before_state_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("scenes", "generations", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            populate_scene_commit_staging(root)
            card = root / "design/scene-cards/scene-card-v01-c01-s01-000001/record.json"
            value = json.loads(card.read_text(encoding="utf-8"))
            value["input_selection_id"] = "selection-000999"
            card.write_text(json.dumps(value), encoding="utf-8")
            selection = root / "runtime/selections/selection-000001/record.json"
            selection_value = json.loads(selection.read_text(encoding="utf-8"))
            selection_value["slots"]["scene_card.v01.c01.s01"] = "scene-card-v01-c01-s01-000999"
            selection.write_text(json.dumps(selection_value), encoding="utf-8")
            RunStateStore(root).save(scene_commit_state())
            with self.assertRaisesRegex(ContractError, "input selection"):
                recover_pending_commit(root)
            state = RunStateStore(root).load_recovery()
            self.assertIsNotNone(state["pending_commit"])
            self.assertEqual(state["current_stage"], "scene_commit")

    def test_rejects_scene_commit_record_with_unknown_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for parent in ("scenes", "generations", "runtime/selections"):
                (root / parent).mkdir(parents=True)
            write_record(root, "runtime/settings/settings-000001", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW})
            populate_scene_commit_staging(root)
            commit = root / "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001/scene-commit-v01-c01-s01-000001/record.json"
            value = json.loads(commit.read_text(encoding="utf-8"))
            value["unexpected"] = True
            commit.write_text(json.dumps(value), encoding="utf-8")
            RunStateStore(root).save(scene_commit_state())

            with self.assertRaisesRegex(ContractError, "scene_commit record"):
                recover_pending_commit(root)
