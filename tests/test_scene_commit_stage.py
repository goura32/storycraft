from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.artifact_ids import initial_counters
from storycraft.run_state import RunStateStore
from storycraft.scene_commit_stage import SceneCommitStageService, slots_to_ids
from storycraft.selection_snapshot import SelectionSnapshotStore
from storycraft.series_contracts import ContractError

NOW = "2026-07-31T00:00:00Z"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def content_record(artifact_id: str, artifact_kind: str, input_selection_id: str | None, content: dict) -> dict:
    return {
        "schema_version": 1,
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "input_selection_id": input_selection_id,
        "created_at": NOW,
        "content": content,
    }


def write_content(root: Path, directory: str, artifact_id: str, kind: str, input_selection_id: str, content: dict) -> None:
    write_json(root / directory / artifact_id / "record.json", content_record(artifact_id, kind, input_selection_id, content))


def write_clean_quality(root: Path, quality_id: str, candidate_id: str, prose: dict) -> None:
    write_json(root / "candidates" / candidate_id / "record.json", {
        "schema_version": 1, "candidate_id": candidate_id, "artifact_kind": "scene-prose",
        "input_selection_id": "selection-000001", "keywords_id": None, "settings_id": "settings-000001",
        "payload": prose, "parent_candidate_id": None, "review_record_id": None,
        "call_id": "call-000001", "created_at": NOW,
    })
    review_id = candidate_id.replace("candidate-", "review-")
    write_json(root / "reviews" / review_id / "record.json", {
        "schema_version": 1, "review_id": review_id, "candidate_id": candidate_id,
        "response": {"schema_version": "review-response-v1", "decision": "pass", "issues": []},
        "call_id": "call-000002", "created_at": NOW,
    })
    write_json(root / "quality" / quality_id / "record.json", {
        "schema_version": 1, "quality_id": quality_id, "candidate_id": candidate_id,
        "review_record_ids": [review_id], "revision_count": 0, "result": "accepted",
        "remaining_major_issues": [], "created_at": NOW,
    })


def workspace() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    for relative in ("inputs", "quality", "candidates", "reviews", "runtime/settings", "runtime/selections", "runtime/staging", "runtime/calls", "runtime/adoptions", "runtime", "design/initial", "design/series-plans", "design/volume-plans", "design/chapter-plans", "design/scene-plans", "design/scene-cards", "generations", "scenes", "publications"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    counters = initial_counters()
    counters["next_scene"] = 2  # prose already reserved scene-v...-000001
    counters["next_generation"] = 2  # current state is gen-000001
    write_json(root / "runtime/counters.json", counters)
    write_json(root / "inputs/request-000001/record.json", {
        "schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request",
        "input_selection_id": None, "created_at": NOW,
        "content": {"title": "題", "genre": ["fantasy"], "premise": "前提", "required_elements": [], "avoid": [], "ending_preference": "希望", "volume_count": 4, "language": "ja"},
    })
    write_json(root / "runtime/settings/settings-000001/record.json", {
        "schema_version": 1, "settings_id": "settings-000001", "payload": {
            "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "m",
            "technical_retry_limit": 3, "quality_revision_limit": 1, "invalid_response_limit": 5,
            "chapter_per_volume_range": [1, 2], "chapter_scene_range": [1, 2], "scene_text_char_range": [1, 100]
        }, "created_at": NOW,
    })
    selections = SelectionSnapshotStore(root)
    base = selections.create(slots={"request": "request-000001", "settings": "settings-000001"}, created_at=NOW)
    base_id = base["selection_id"]
    
    # Valid initial-design content per closed schema
    initial_design_content = {
        "schema_version": 1,
        "core": {"logline": "英雄の旅", "premise": "選択の物語", "central_question": "何を守るのか", "themes": ["選択"], "dramatic_engine": "選択が障害を生む", "tone": ["希望"], "reader_promise": "人物の選択が結末を変える", "ending_direction": "責任を引き受ける"},
        "cast": [{"name": "主人公", "role": "英雄", "description": "選択を迫られる", "relationships": []}],
        "world": {"settings": ["剣と魔法"], "constraints": ["契約を破れない"], "institutions": ["王国"]},
        "knowledge_model": {"author_knows": ["秘密"], "character_knows": {"主人公": ["目的"]}, "reader_knows": ["目的"]},
        "unresolved_threads": [{"name": "塔の試練", "type": "goal", "required_for_ending": True, "description": "塔を登頂する"}],
        "ending_conditions": [{"thread_name": "塔の試練", "condition": "塔を登頂する"}],
    }
    
    # Valid series-plan content per closed schema
    series_plan_content = {
        "volume_count": 4, "series_objectives": ["完結"],
        "volume_summaries": [{"volume_number": n, "purpose": f"巻{n}", "ending_change": "変化"} for n in range(1, 5)],
        "character_arc_map": {"char-main": [1]}, "relationship_arc_map": {"rel-main": [1]}, "thread_progression": {"塔の試練": [1]},
        "revelation_schedule": [{"volume_number": 1, "knowledge_id": "know-main"}], "ending_path": "完結", "global_constraints": []
    }

    # Valid volume-plan content per closed schema
    volume_plan_content = {
        "title": "第一巻", "volume_purpose": "目的", "central_conflict": "対立",
        "character_changes": {"char-main": "変化"}, "relationship_changes": {"rel-main": "変化"}, "thread_goals": {"塔の試練": "進展"}, "revelations": [],
        "chapter_summaries": [{"chapter_number": n, "purpose": f"章{n}"} for n in range(1, 3)], "required_end_state": "次へ"
    }

    # Valid chapter-plan content per closed schema
    chapter_plan_content = {
        "title": "第一章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"],
        "scene_summaries": [{"scene_number": n, "purpose": f"場面{n}"} for n in range(1, 3)], "required_revelations": [], "constraints": []
    }
    
    # Valid scene-plan content per closed schema
    scene_plan_content = {
        "purpose": "場面1", "pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main",
        "starting_conditions": ["開始"], "intended_beats": ["展開"], "intended_revelations": [], "intended_changes": ["変化"], "prohibited_disclosures": []
    }
    
    # Valid scene-card content per closed schema
    scene_card_content = {
        "pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main", "story_time": "夜", "purpose": "場面1", "opening_state": "開始",
        "required_beats": [{"beat_id": "beat-01", "description": "展開", "required": True, "order_hint": 1}], "conflict": "対立", "allowed_revelations": [], "required_revelations": [], "forbidden_revelations": [],
        "allowed_updates": [{"target_type": "timeline_position", "target_id": "timeline_position", "allowed_fields": ["value"]}], "ending_state_targets": ["変化"], "style_constraints": ["簡潔"]
    }
    
    # Valid scene-prose content per closed schema
    scene_prose_content = {
        "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
        "text": "本文"
    }
    
    # Valid continuity-update content per closed schema
    continuity_content = {
        "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
        "changes": [{"op": "set", "target": "timeline_position", "path": "$.timeline_position", "value": 1, "evidence_locations": ["prose:0"]}]
    }
    
    # Valid generation content per closed schema
    generation_content = {
        "story_facts": [{"fact_id": "fact-000001", "value": "開始"}],
        "character_knowledge": {"char-main": []},
        "reader_disclosures": [],
        "unresolved_thread_states": {"塔の試練": {"status": "open"}},
        "timeline_position": 0,
    }
    
    records = [
        ("design/initial", "initial-design-000001", "initial-design", initial_design_content),
        ("design/series-plans", "series-plan-000001", "series-plan", series_plan_content),
        ("design/volume-plans", "volume-plan-v01-000001", "volume-plan", volume_plan_content),
        ("design/chapter-plans", "chapter-plan-v01-c01-000001", "chapter-plan", chapter_plan_content),
        ("design/scene-plans", "scene-plan-v01-c01-s01-000001", "scene-plan", scene_plan_content),
        ("design/scene-cards", "scene-card-v01-c01-s01-000001", "scene-card", scene_card_content),
        ("scenes", "scene-prose-v01-c01-s01-000001", "scene-prose", scene_prose_content),
        ("scenes", "continuity-v01-c01-s01-000001", "continuity-update", continuity_content),
        ("generations", "gen-000001", "generation", generation_content),
    ]
    for directory, artifact_id, kind, content in records:
        write_content(root, directory, artifact_id, kind, base_id, content)
    write_clean_quality(root, "quality-000001", "candidate-000001", {"coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1}, "text": "本文"})
    write_clean_quality(root, "quality-000002", "candidate-000002", {"coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1}, "text": "本文"})
    parent = selections.create(input_selection_id=base_id, created_at=NOW, slots={
        "request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001",
        "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001",
        "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "current_state": "gen-000001",
    })
    scene_plan_selection = selections.create(input_selection_id=parent["selection_id"], created_at=NOW, slots={
        "request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001",
        "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001",
        "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "scene_plan.v01.c01.s01": "scene-plan-v01-c01-s01-000001",
        "current_state": "gen-000001",
    })
    scene_plan_record_path = root / "design/scene-plans/scene-plan-v01-c01-s01-000001/record.json"
    scene_plan_record = json.loads(scene_plan_record_path.read_text(encoding="utf-8"))
    scene_plan_record["input_selection_id"] = parent["selection_id"]
    write_json(scene_plan_record_path, scene_plan_record)
    scene_inputs = selections.create(input_selection_id=scene_plan_selection["selection_id"], created_at=NOW, slots={
        "request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001",
        "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001",
        "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "scene_plan.v01.c01.s01": "scene-plan-v01-c01-s01-000001",
        "scene_card.v01.c01.s01": "scene-card-v01-c01-s01-000001", "scene_prose.v01.c01.s01": "scene-prose-v01-c01-s01-000001",
        "current_state": "gen-000001",
    })
    current = selections.create(input_selection_id=scene_inputs["selection_id"], created_at=NOW, slots={
        "request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001",
        "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001",
        "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "scene_plan.v01.c01.s01": "scene-plan-v01-c01-s01-000001",
        "scene_card.v01.c01.s01": "scene-card-v01-c01-s01-000001", "scene_prose.v01.c01.s01": "scene-prose-v01-c01-s01-000001",
        "scene_prose_disposition.v01.c01.s01": "quality-000001", "scene_prose_adoption.v01.c01.s01": "adoption-000001", "continuity_update.v01.c01.s01": "continuity-v01-c01-s01-000001",
        "continuity_disposition.v01.c01.s01": "quality-000002", "continuity_adoption.v01.c01.s01": "adoption-000002",
        "current_state": "gen-000001",
    })
    write_json(root / "runtime/adoptions/adoption-000001/record.json", {
        "schema_version": 1, "adoption_id": "adoption-000001", "source_kind": "candidate", "candidate_id": "candidate-000001", "quality_id": "quality-000001",
        "output_content_artifact_ids": ["scene-prose-v01-c01-s01-000001"], "output_selection_id": current["selection_id"], "input_selection_id": scene_inputs["selection_id"], "created_at": NOW,
    })
    write_json(root / "runtime/adoptions/adoption-000002/record.json", {
        "schema_version": 1, "adoption_id": "adoption-000002", "source_kind": "candidate", "candidate_id": "candidate-000002", "quality_id": "quality-000002",
        "output_content_artifact_ids": ["continuity-v01-c01-s01-000001"], "output_selection_id": current["selection_id"], "input_selection_id": scene_inputs["selection_id"], "created_at": NOW,
    })
    for artifact_id in ("scene-card-v01-c01-s01-000001", "scene-prose-v01-c01-s01-000001", "continuity-v01-c01-s01-000001"):
        directory = "design/scene-cards" if artifact_id.startswith("scene-card") else "scenes"
        record_path = root / directory / artifact_id / "record.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["input_selection_id"] = (
            scene_plan_selection["selection_id"]
            if artifact_id.startswith(("scene-card", "scene-prose"))
            else scene_inputs["selection_id"]
        )
        write_json(record_path, record)
    RunStateStore(root).save({
        "schema_version": 3, "workspace_id": "ws-000001", "status": "running", "last_error": None,
        "current_stage": "scene_commit", "current_target": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
        "current_selection_id": current["selection_id"], "pending_commit": None, "published_volumes": [],
        "created_at": NOW, "updated_at": NOW,
    })
    return temporary, root


class SceneCommitStageTests(unittest.TestCase):
    def test_timeline_position_is_monotonic_integer_set_only(self) -> None:
        old_state = {"story_facts": [], "character_knowledge": {}, "reader_disclosures": [], "unresolved_thread_states": {"塔の試練": {"status": "open"}}, "timeline_position": 2}
        with self.assertRaisesRegex(ContractError, "timeline_position"):
            SceneCommitStageService._apply_continuity(old_state, {"changes": [{"op": "set", "target": "timeline_position", "path": "$.timeline_position", "value": 1, "evidence_locations": ["prose:0"]}]})
        with self.assertRaisesRegex(ContractError, "timeline_position"):
            SceneCommitStageService._apply_continuity(old_state, {"changes": [{"op": "add", "target": "timeline_position", "path": "$.timeline_position", "value": 3, "evidence_locations": ["prose:0"]}]})

    def test_slots_to_ids_preserves_canonical_record_ids(self) -> None:
        self.assertEqual(
            slots_to_ids({"initial_design_adoption": {"adoption_id": "adoption-000002", "quality_id": "quality-000002"}}),
            {"initial_design_adoption": "adoption-000002"},
        )
        self.assertEqual(
            slots_to_ids({"scene_commit.v01.c01.s01": {"scene_commit_id": "scene-commit-v01-c01-s01-000001"}}),
            {"scene_commit.v01.c01.s01": "scene-commit-v01-c01-s01-000001"},
        )

    def test_commits_selected_scene_once_with_prose_disposition_and_advances_to_next_scene(self) -> None:
        temporary, root = workspace()
        self.addCleanup(temporary.cleanup)

        with patch("storycraft.scene_commit_stage.recover_pending_commit", return_value={"recovered": True}) as recover:
            result = SceneCommitStageService(root).run(workspace_already_validated=True, updated_at=NOW)

        self.assertEqual(result, {"recovered": True})
        recover.assert_called_once_with(root)
        pending = RunStateStore(root).load()["pending_commit"]
        assert isinstance(pending, dict)
        self.assertEqual(pending["kind"], "scene_commit")
        self.assertEqual(pending["state_update"], {
            "current_selection_id": "selection-000006", "current_stage": "scene_plan",
            "current_target": {"volume_number": 1, "chapter_number": 1, "scene_number": 2},
        })
        scene = json.loads((root / "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001/scene-v01-c01-s01-000002/record.json").read_text(encoding="utf-8"))
        self.assertEqual(scene["content"]["quality_disposition_id"], "quality-000001")
        self.assertEqual(scene["content"]["continuity_update_id"], "continuity-v01-c01-s01-000001")
        state = json.loads((root / "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001/gen-000002/record.json").read_text(encoding="utf-8"))
        self.assertEqual(state["content"]["timeline_position"], 1)
        commit = json.loads((root / "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001/scene-commit-v01-c01-s01-000001/record.json").read_text(encoding="utf-8"))
        self.assertEqual(set(commit), {"schema_version", "scene_commit_id", "scene_id", "scene_card_id", "scene_prose_id", "continuity_update_id", "current_state_id", "quality_disposition_id", "volume_number", "chapter_number", "scene_number", "created_at"})
        selection = json.loads((root / "runtime/staging/scene-commit-scene-commit-v01-c01-s01-000001/selection-000006/record.json").read_text(encoding="utf-8"))
        self.assertEqual(selection["slots"]["scene_prose_disposition.v01.c01.s01"], "quality-000001")
        self.assertEqual(selection["slots"]["scene_commit.v01.c01.s01"], "scene-commit-v01-c01-s01-000001")


if __name__ == "__main__":
    unittest.main()
