"""Volume-publication stage contracts: registry inputs and generic recovery."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from storycraft.artifact_ids import initial_counters
from storycraft.commit_recovery import recover_pending_commit
from storycraft.publication_recovery import execute_publication_recovery
from storycraft.run_state import RunStateStore
from storycraft.selection_snapshot import SelectionSnapshotStore
from storycraft.series_contracts import ContractError
from storycraft.volume_publication_stage import VolumePublicationStageService
from storycraft.volume_plan_stage import VolumePlanStageService

NOW = "2026-07-31T00:00:00Z"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def content_record(artifact_id: str, kind: str, selection_id: str, content: dict) -> dict:
    return {
        "schema_version": 1, "artifact_id": artifact_id, "artifact_kind": kind,
        "input_selection_id": selection_id, "created_at": NOW, "content": content,
    }


def write_content(root: Path, artifact_id: str, kind: str, selection_id: str, content: dict) -> None:
    locations = {
        "initial-design": "design/initial",
        "series-plan": "design/series-plans", "volume-plan": "design/volume-plans",
        "chapter-plan": "design/chapter-plans", "scene-plan": "design/scene-plans", "scene-card": "design/scene-cards",
        "scene-prose": "scenes", "scene": "scenes", "continuity-update": "scenes",
        "generation": "generations",
    }
    write_json(root / locations[kind] / artifact_id / "record.json", content_record(artifact_id, kind, selection_id, content))


def quality_record(quality_id: str, candidate_id: str, review_id: str, *, notice: bool = False) -> dict:
    return {
        "schema_version": 1, "quality_id": quality_id, "candidate_id": candidate_id,
        "review_record_ids": [review_id], "revision_count": 0,
        "result": "accepted_with_notice" if notice else "accepted",
        "remaining_major_issues": [{"code": "quality.critical", "message": "編集上の注意", "evidence_locations": ["$.text"]}] if notice else [],
        **({"notice_type": "編集"} if notice else {}), "created_at": NOW,
    }


def write_quality_audit(root: Path, quality_id: str, payload: dict, *, notice: bool, artifact_kind: str = "scene-prose", input_selection_id: str = "selection-000001") -> None:
    suffix = quality_id.rsplit("-", 1)[1]
    candidate_id, review_id = f"candidate-{suffix}", f"review-{suffix}"
    generate_call_id, review_call_id = f"call-{suffix}", f"call-{900000 + int(suffix):06d}"
    write_json(root / "runtime/calls" / generate_call_id / "record.json", {
        "schema_version": 1, "call_id": generate_call_id, "operation": "generate", "role": artifact_kind,
        "target_candidate_id": None, "input_refs": [input_selection_id], "technical_attempt": 1, "format_attempt": 1,
        "seed": 1, "endpoint": "injected", "model": "test", "settings_id": "settings-000001",
        "request": "{}", "response": "{}", "transport": "success",
        "validation": {"result": "valid", "checks": [], "failure_code": None},
    })
    write_json(root / "candidates" / candidate_id / "record.json", {
        "schema_version": 1, "candidate_id": candidate_id, "artifact_kind": artifact_kind,
        "input_selection_id": input_selection_id, "keywords_id": None, "settings_id": "settings-000001",
        "payload": payload, "parent_candidate_id": None, "review_record_id": None,
        "call_id": generate_call_id, "created_at": NOW,
    })
    response = (
        {"schema_version": "review-response-v1", "decision": "issues", "issues": [{"severity": "critical", "evidence_locations": ["$.text"], "explanation": "編集上の注意"}]}
        if notice else {"schema_version": "review-response-v1", "decision": "pass", "issues": []}
    )
    write_json(root / "reviews" / review_id / "record.json", {
        "schema_version": 1, "review_id": review_id, "candidate_id": candidate_id,
        "response": response, "call_id": review_call_id, "created_at": NOW,
    })
    write_json(root / "runtime/calls" / review_call_id / "record.json", {
        "schema_version": 1, "call_id": review_call_id, "operation": "review", "role": artifact_kind,
        "target_candidate_id": candidate_id, "input_refs": [candidate_id], "technical_attempt": 1, "format_attempt": 1,
        "seed": 1, "endpoint": "injected", "model": "test", "settings_id": "settings-000001",
        "request": "{}", "response": "{}", "transport": "success",
        "validation": {"result": "valid", "checks": [], "failure_code": None},
    })
    write_json(root / "quality" / quality_id / "record.json", quality_record(quality_id, candidate_id, review_id, notice=notice))


def workspace(*, volume_count: int = 2, omit_scene_source: bool = False) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    for relative in (
        "inputs", "quality", "candidates", "reviews", "runtime", "runtime/settings",
        "runtime/staging", "runtime/selections", "runtime/calls",
        "runtime/adoptions", "design", "design/initial", "design/series-plans",
        "design/volume-plans", "design/chapter-plans", "design/scene-plans", "design/scene-cards", "generations",
        "scenes", "publications",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    write_json(root / "runtime/counters.json", initial_counters())
    write_json(root / "runtime/settings/settings-000001/record.json", {
        "schema_version": 1, "settings_id": "settings-000001", "payload": {"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 1, "invalid_response_limit": 5, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1, 100]}, "created_at": NOW,
    })
    selections = SelectionSnapshotStore(root)
    base = selections.create(slots={"settings": "settings-000001"}, created_at=NOW)
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
    write_content(root, "initial-design-000001", "initial-design", base_id, initial_design_content)

    # Valid series-plan content per closed schema
    series_plan_content = {
        "volume_count": 4, "series_objectives": ["完結"],
        "volume_summaries": [{"volume_number": n, "purpose": f"巻{n}", "ending_change": "変化"} for n in range(1, 5)],
        "character_arc_map": {"char-main": [1]}, "relationship_arc_map": {"rel-main": [1]}, "thread_progression": {"塔の試練": [1]},
        "revelation_schedule": [{"volume_number": 1, "knowledge_id": "know-main"}], "ending_path": "完結", "global_constraints": []
    }
    write_content(root, "series-plan-000001", "series-plan", base_id, series_plan_content)

    volume_plan_content = {
        "title": "第一巻", "volume_purpose": "目的", "central_conflict": "対立",
        "character_changes": {"char-main": "変化"}, "relationship_changes": {"rel-main": "変化"}, "thread_goals": {"塔の試練": "進展"}, "revelations": [],
        "chapter_summaries": [{"chapter_number": n, "purpose": f"章{n}"} for n in range(1, 3)], "required_end_state": "次へ"
    }
    write_content(root, "volume-plan-v01-000001", "volume-plan", base_id, volume_plan_content)

    chapter_plan_c01 = {
        "title": "第一章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"],
        "scene_summaries": [{"scene_number": n, "purpose": f"場面{n}"} for n in range(1, 3)], "required_revelations": [], "constraints": []
    }
    write_content(root, "chapter-plan-v01-c01-000001", "chapter-plan", base_id, chapter_plan_c01)

    chapter_plan_c02 = {
        "title": "第二章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"],
        "scene_summaries": [{"scene_number": 1, "purpose": "場面1"}], "required_revelations": [], "constraints": []
    }
    write_content(root, "chapter-plan-v01-c02-000001", "chapter-plan", base_id, chapter_plan_c02)

    slots = {"settings": "settings-000001", "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001",
             "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "chapter_plan.v01.c02": "chapter-plan-v01-c02-000001"}
    # Scene records consume the selection that already contains the current
    # generation.  The publication selection is a later child of this source
    # selection, so publication can distinguish input state from final state.
    generation_content = {
        "story_facts": [{"fact_id": "fact-000001", "value": "開始"}],
        "character_knowledge": {"char-main": []},
        "reader_disclosures": [],
        "unresolved_thread_states": {"塔の試練": {"status": "open"}},
        "timeline_position": 0,
    }
    write_content(root, "gen-000001", "generation", base_id, generation_content)
    source_selection = selections.create(
        input_selection_id=base_id,
        slots={"settings": "settings-000001", "initial_design": "initial-design-000001", "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001", "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "chapter_plan.v01.c02": "chapter-plan-v01-c02-000001", "current_state": "gen-000001"},
        created_at=NOW,
    )
    source_selection_id = source_selection["selection_id"]
    for chapter, scenes in ((1, (1, 2)), (2, (1,))):
        for scene in scenes:
            prose_id = f"scene-prose-v01-c{chapter:02d}-s{scene:02d}-000001"
            committed_id = f"scene-v01-c{chapter:02d}-s{scene:02d}-000001"
            card_id = f"scene-card-v01-c{chapter:02d}-s{scene:02d}-000001"
            continuity_id = f"continuity-v01-c{chapter:02d}-s{scene:02d}-000001"
            quality_id = f"quality-{chapter * 10 + scene:06d}"
            continuity_quality_id = f"quality-{100 + chapter * 10 + scene:06d}"
            if not (omit_scene_source and chapter == 2 and scene == 1):
                # Valid scene-prose content per closed schema
                prose_content = {
                    "coordinate": {"volume_number": 1, "chapter_number": chapter, "scene_number": scene},
                    "text": f"本文 {chapter}-{scene}"
                }
                write_content(root, prose_id, "scene-prose", base_id, prose_content)
            plan_id = f"scene-plan-v01-c{chapter:02d}-s{scene:02d}-000001"
            write_content(root, plan_id, "scene-plan", source_selection_id, {
                "purpose": f"場面{scene}", "pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main",
                "starting_conditions": ["開始"], "intended_beats": ["展開"], "intended_revelations": [], "intended_changes": ["変化"], "prohibited_disclosures": [],
            })
            # Valid scene content per closed schema
            write_content(root, card_id, "scene-card", source_selection_id, {"pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main", "story_time": "夜", "purpose": f"場面{scene}", "opening_state": "開始", "required_beats": [{"beat_id": "beat-01", "description": "展開", "required": True, "order_hint": 1}], "conflict": "対立", "allowed_revelations": [], "required_revelations": [], "forbidden_revelations": [], "allowed_updates": [], "ending_state_targets": ["変化"], "style_constraints": ["簡潔"]})
            write_content(root, continuity_id, "continuity-update", source_selection_id, {"coordinate": {"volume_number": 1, "chapter_number": chapter, "scene_number": scene}, "changes": []})
            scene_content = {
                "coordinate": {"volume_number": 1, "chapter_number": chapter, "scene_number": scene},
                "scene_prose_id": prose_id, "scene_card_id": card_id, "continuity_update_id": continuity_id,
                "current_state_id": "gen-000001", "quality_disposition_id": quality_id,
            }
            write_content(root, committed_id, "scene", source_selection_id, scene_content)
            prose = {"coordinate": {"volume_number": 1, "chapter_number": chapter, "scene_number": scene}, "text": f"本文 {chapter}-{scene}"}
            write_quality_audit(root, quality_id, prose, notice=(chapter == 1 and scene == 2))
            write_quality_audit(root, continuity_quality_id, prose, notice=False)
            coordinate = f"v01.c{chapter:02d}.s{scene:02d}"
            slots[f"scene.{coordinate}"] = committed_id
            slots[f"scene_card.{coordinate}"] = card_id
            slots[f"continuity_update.{coordinate}"] = continuity_id
            slots[f"scene_prose.{coordinate}"] = prose_id
            slots[f"scene_prose_disposition.{coordinate}"] = quality_id
            slots[f"continuity_disposition.{coordinate}"] = continuity_quality_id
            slots[f"scene_plan.{coordinate}"] = plan_id
    slots["current_state"] = "gen-000001"
    scene_selection = selections.create(
        input_selection_id=source_selection_id,
        slots={**source_selection["slots"], **{slot: artifact_id for slot, artifact_id in slots.items() if slot.startswith("scene_plan.")}},
        created_at=NOW,
    )
    scene_input_slots = {**scene_selection["slots"], **{slot: artifact_id for slot, artifact_id in slots.items() if slot.startswith(("scene_card.", "scene_prose."))}}
    scene_inputs = selections.create(
        input_selection_id=scene_selection["selection_id"], slots=scene_input_slots, created_at=NOW,
    )
    for slot, artifact_id in slots.items():
        if slot.startswith(("scene_card.", "scene_prose.", "continuity_update.")):
            directory = "design/scene-cards" if slot.startswith("scene_card.") else "scenes"
            record_path = root / directory / artifact_id / "record.json"
            if not record_path.exists():
                continue
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["input_selection_id"] = (
                scene_selection["selection_id"]
                if slot.startswith(("scene_card.", "scene_prose."))
                else scene_inputs["selection_id"]
            )
            write_json(record_path, record)
    current_selection_id = scene_inputs["selection_id"]
    current_slots = dict(scene_inputs["slots"])
    adoption_number = 1
    scene_order = [(chapter, scene) for chapter, scenes in ((1, (1, 2)), (2, (1,))) for scene in scenes]
    for chapter, scene in scene_order:
        coordinate = f"v01.c{chapter:02d}.s{scene:02d}"
        prose_id = slots[f"scene_prose.{coordinate}"]
        prose_quality_id = slots[f"scene_prose_disposition.{coordinate}"]
        prose_suffix = prose_quality_id.rsplit("-", 1)[1]
        prose_candidate_id = f"candidate-{prose_suffix}"
        prose_candidate_path = root / "candidates" / prose_candidate_id / "record.json"
        prose_candidate = json.loads(prose_candidate_path.read_text(encoding="utf-8"))
        prose_candidate["input_selection_id"] = current_selection_id
        write_json(prose_candidate_path, prose_candidate)
        prose_call_path = root / "runtime/calls" / prose_candidate["call_id"] / "record.json"
        prose_call = json.loads(prose_call_path.read_text(encoding="utf-8"))
        prose_call["input_refs"] = [current_selection_id]
        write_json(prose_call_path, prose_call)
        prose_adoption_id = f"adoption-{adoption_number:06d}"
        adoption_number += 1
        prose_slots = dict(current_slots)
        prose_slots[f"scene_prose_adoption.{coordinate}"] = prose_adoption_id
        prose_slots[f"scene_prose_disposition.{coordinate}"] = prose_quality_id
        prose_selection = selections.create(input_selection_id=current_selection_id, slots=prose_slots, created_at=NOW)
        write_json(root / "runtime/adoptions" / prose_adoption_id / "record.json", {
            "schema_version": 1, "adoption_id": prose_adoption_id, "source_kind": "candidate",
            "input_selection_id": current_selection_id, "output_selection_id": prose_selection["selection_id"],
            "candidate_id": prose_candidate_id, "quality_id": prose_quality_id,
            "output_content_artifact_ids": [prose_id], "created_at": NOW,
        })
        current_selection_id, current_slots = prose_selection["selection_id"], prose_selection["slots"]

        continuity_id = slots[f"continuity_update.{coordinate}"]
        continuity_quality_id = slots[f"continuity_disposition.{coordinate}"]
        continuity_suffix = continuity_quality_id.rsplit("-", 1)[1]
        continuity_candidate_id = f"candidate-{continuity_suffix}"
        continuity_candidate_path = root / "candidates" / continuity_candidate_id / "record.json"
        continuity_candidate = json.loads(continuity_candidate_path.read_text(encoding="utf-8"))
        continuity_candidate["artifact_kind"] = "continuity-update"
        continuity_candidate["input_selection_id"] = current_selection_id
        continuity_candidate["payload"] = json.loads((root / "scenes" / continuity_id / "record.json").read_text(encoding="utf-8"))["content"]
        write_json(continuity_candidate_path, continuity_candidate)
        continuity_call_path = root / "runtime/calls" / continuity_candidate["call_id"] / "record.json"
        continuity_call = json.loads(continuity_call_path.read_text(encoding="utf-8"))
        continuity_call["role"] = "continuity-update"
        continuity_call["input_refs"] = [current_selection_id]
        write_json(continuity_call_path, continuity_call)
        continuity_adoption_id = f"adoption-{adoption_number:06d}"
        adoption_number += 1
        continuity_slots = dict(current_slots)
        continuity_slots[f"continuity_update.{coordinate}"] = continuity_id
        continuity_slots[f"continuity_adoption.{coordinate}"] = continuity_adoption_id
        continuity_slots[f"continuity_disposition.{coordinate}"] = continuity_quality_id
        continuity_selection = selections.create(input_selection_id=current_selection_id, slots=continuity_slots, created_at=NOW)
        write_json(root / "runtime/adoptions" / continuity_adoption_id / "record.json", {
            "schema_version": 1, "adoption_id": continuity_adoption_id, "source_kind": "candidate",
            "input_selection_id": current_selection_id, "output_selection_id": continuity_selection["selection_id"],
            "candidate_id": continuity_candidate_id, "quality_id": continuity_quality_id,
            "output_content_artifact_ids": [continuity_id], "created_at": NOW,
        })
        current_selection_id, current_slots = continuity_selection["selection_id"], continuity_selection["slots"]

    final_slots = dict(current_slots)
    for slot, artifact_id in slots.items():
        if slot.startswith("scene.") or slot.startswith("scene_commit.") or slot.startswith("continuity_update."):
            final_slots[slot] = artifact_id
    for chapter, scene in scene_order:
        coordinate = f"v01.c{chapter:02d}.s{scene:02d}"
        committed_id = slots[f"scene.{coordinate}"]
        scene_path = root / "scenes" / committed_id / "record.json"
        scene_record = json.loads(scene_path.read_text(encoding="utf-8"))
        scene_record["input_selection_id"] = current_selection_id
        write_json(scene_path, scene_record)
        commit_id = f"scene-commit-v01-c{chapter:02d}-s{scene:02d}-000001"
        write_json(root / "scenes" / commit_id / "record.json", {
            "schema_version": 1, "scene_commit_id": commit_id, "scene_id": committed_id,
            "scene_card_id": slots[f"scene_card.{coordinate}"], "scene_prose_id": slots[f"scene_prose.{coordinate}"],
            "continuity_update_id": slots[f"continuity_update.{coordinate}"], "current_state_id": "gen-000001",
            "quality_disposition_id": slots[f"scene_prose_disposition.{coordinate}"],
            "volume_number": 1, "chapter_number": chapter, "scene_number": scene, "created_at": NOW,
        })
        final_slots[f"scene_commit.{coordinate}"] = commit_id
    selection = selections.create(input_selection_id=current_selection_id, slots=final_slots, created_at=NOW)
    RunStateStore(root).save({
        "schema_version": 3, "workspace_id": "ws-000001", "status": "running", "last_error": None,
        "current_stage": "volume_publication", "current_target": {"volume_number": 1},
        "current_selection_id": selection["selection_id"], "pending_commit": None, "published_volumes": [],
        "created_at": NOW, "updated_at": NOW,
    })
    return temporary, root


class VolumePublicationServiceTests(unittest.TestCase):
    def test_publication_accepts_scene_input_state_when_current_state_has_advanced(self) -> None:
        temporary, root = workspace()
        self.addCleanup(temporary.cleanup)
        state = RunStateStore(root).load()
        current_selection_id = state["current_selection_id"]
        current_selection = SelectionSnapshotStore(root).load(current_selection_id)
        source_selection_id = current_selection["input_selection_id"]
        assert isinstance(source_selection_id, str)
        write_content(root, "gen-000002", "generation", source_selection_id, {
            "story_facts": [{"fact_id": "fact-000001", "value": "場面後"}],
            "character_knowledge": {"char-main": []},
            "reader_disclosures": [],
            "unresolved_thread_states": {"塔の試練": {"status": "open"}},
            "timeline_position": 1,
        })
        advanced = SelectionSnapshotStore(root).create(
            input_selection_id=current_selection_id,
            slots={**current_selection["slots"], "current_state": "gen-000002"},
            created_at=NOW,
        )
        state["current_selection_id"] = advanced["selection_id"]
        RunStateStore(root).save(state)

        with patch("storycraft.volume_publication_stage.recover_pending_commit", return_value={"recovered": True}):
            result = VolumePublicationStageService(root).run(updated_at=NOW)

        self.assertEqual(result, {"recovered": True})
        pending = RunStateStore(root).load()["pending_commit"]
        assert isinstance(pending, dict)
        self.assertEqual(pending["kind"], "volume_publication")

    def test_stages_single_publication_target_and_uses_generic_recovery(self) -> None:
        temporary, root = workspace()
        self.addCleanup(temporary.cleanup)
        with patch("storycraft.volume_publication_stage.recover_pending_commit", return_value={"recovered": True}) as recover:
            result = VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertEqual(result, {"recovered": True})
        recover.assert_called_once_with(root)
        pending = RunStateStore(root).load()["pending_commit"]
        assert isinstance(pending, dict)
        self.assertEqual(pending["kind"], "volume_publication")
        self.assertIsNone(pending["output_selection_id"])
        self.assertEqual(pending["state_update"], {
            "current_selection_id": "selection-000011", "current_stage": "volume_plan",
            "current_target": {"volume_number": 2},
            "published_volumes": [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
        })
        self.assertEqual(set(pending["targets"][0]), {"artifact_id", "target_kind", "artifact_kind", "staging_path", "final_path", "status"})
        self.assertEqual(pending["targets"][0]["target_kind"], "publication_directory")
        self.assertIsNone(pending["targets"][0]["artifact_kind"])
        record = json.loads((root / "runtime/staging/volume-publication-volume-pub-v01-000001/volume-pub-v01-000001/record.json").read_text(encoding="utf-8"))
        self.assertIn(set(record), [{"schema_version", "volume_publication_id", "volume_number", "input_selection_id", "created_at"}, {"schema_version", "volume_publication_id", "volume_number", "input_selection_id", "created_at", "publication_notice_type"}])

    def test_generic_recovery_publishes_sources_in_chapter_scene_order_and_moves_nonfinal_to_next_plan(self) -> None:
        temporary, root = workspace()
        self.addCleanup(temporary.cleanup)
        state = VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertEqual(state["current_stage"], "volume_plan")
        self.assertEqual(state["current_target"], {"volume_number": 2})
        self.assertEqual(state["current_selection_id"], "selection-000011")
        publication = root / "publications/volume-pub-v01-000001"
        self.assertTrue(publication.is_dir())
        manuscript = (publication / "manuscript.md").read_text(encoding="utf-8")
        self.assertEqual(manuscript, "編集上の注意があります。\n\n本文 1-1\n\n本文 1-2\n\n本文 2-1\n")

    def test_recovery_rejects_a_forged_publication_source_reference(self) -> None:
        temporary, root = workspace()
        self.addCleanup(temporary.cleanup)
        with patch("storycraft.volume_publication_stage.recover_pending_commit", side_effect=RuntimeError("staged")):
            with self.assertRaisesRegex(RuntimeError, "staged"):
                VolumePublicationStageService(root).run(updated_at=NOW)
        pending = RunStateStore(root).load()["pending_commit"]
        assert isinstance(pending, dict)
        record_path = root / pending["targets"][0]["staging_path"] / "record.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["input_selection_id"] = "selection-999999"
        record_path.write_text(json.dumps(record), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "manifestと一致"):
            recover_pending_commit(root)

    def test_recovery_rejects_a_publication_record_bound_to_another_valid_selection(self) -> None:
        temporary, root = workspace()
        self.addCleanup(temporary.cleanup)
        with patch("storycraft.volume_publication_stage.recover_pending_commit", side_effect=RuntimeError("staged")):
            with self.assertRaisesRegex(RuntimeError, "staged"):
                VolumePublicationStageService(root).run(updated_at=NOW)
        state = RunStateStore(root).load()
        current_selection_id = state["current_selection_id"]
        current_selection = SelectionSnapshotStore(root).load(current_selection_id)
        alternate = SelectionSnapshotStore(root).create(
            input_selection_id=current_selection_id,
            slots=current_selection["slots"],
            created_at=NOW,
        )
        pending = state["pending_commit"]
        assert isinstance(pending, dict)
        record_path = root / pending["targets"][0]["staging_path"] / "record.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["input_selection_id"] = alternate["selection_id"]
        record_path.write_text(json.dumps(record), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "manifestと一致"):
            recover_pending_commit(root)

        self.assertIsNotNone(RunStateStore(root).load()["pending_commit"])
        self.assertFalse((root / "publications/volume-pub-v01-000001").exists())

    def test_public_recovery_converges_a_staged_publication_on_disk(self) -> None:
        temporary, root = workspace()
        self.addCleanup(temporary.cleanup)
        with patch("storycraft.volume_publication_stage.recover_pending_commit", side_effect=RuntimeError("staged")):
            with self.assertRaisesRegex(RuntimeError, "staged"):
                VolumePublicationStageService(root).run(updated_at=NOW)

        recovered = execute_publication_recovery(root)

        self.assertIsNone(recovered["pending_commit"])
        self.assertEqual(recovered["published_volumes"], [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}])
        self.assertTrue((root / "publications/volume-pub-v01-000001/record.json").is_file())
        self.assertFalse((root / "runtime/staging/volume-publication-volume-pub-v01-000001/volume-pub-v01-000001").exists())

    def test_rejects_each_committed_scene_when_its_selected_source_is_missing(self) -> None:
        temporary, root = workspace(omit_scene_source=True)
        self.addCleanup(temporary.cleanup)
        with self.assertRaises(ContractError):
            VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertIsNone(RunStateStore(root).load()["pending_commit"])

    def test_first_volume_of_four_volume_series_remains_running_after_generic_recovery(self) -> None:
        temporary, root = workspace(volume_count=4)
        self.addCleanup(temporary.cleanup)
        state = VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertEqual(state["status"], "running")
        self.assertEqual(state["current_stage"], "volume_plan")
        self.assertEqual(state["current_target"], {"volume_number": 2})
        self.assertIsNone(state["pending_commit"])
        self.assertEqual(state["published_volumes"], [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}])

    def test_published_volume_one_can_start_volume_two_plan_from_canonical_prior_slot(self) -> None:
        temporary, root = workspace(volume_count=4)
        self.addCleanup(temporary.cleanup)

        state = VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertEqual(state["current_stage"], "volume_plan")
        self.assertEqual(state["current_target"], {"volume_number": 2})
        selection = SelectionSnapshotStore(root).load(state["current_selection_id"])
        self.assertEqual(selection["slots"]["volume_plan.v01"], "volume-plan-v01-000001")
        self.assertNotIn("prior_volume_plan", selection["slots"])

        with patch("storycraft.volume_plan_stage.CandidateStageRunner.run", return_value={"started": True}) as run:
            result = VolumePlanStageService(root).run(None, updated_at=NOW)

        self.assertEqual(result, {"started": True})
        context = run.call_args.kwargs["context"]
        self.assertEqual(context["prior_volume_plan"]["title"], "第一巻")
        self.assertEqual(context["volume_number"], 2)

    def test_final_volume_stages_completed_state_in_its_manifest_before_generic_recovery(self) -> None:
        temporary, root = workspace(volume_count=1)
        self.addCleanup(temporary.cleanup)
        inputs = {
            "settings_id": "settings-000001", "series_plan_id": "series-plan-000001",
            "volume_plan_id": "volume-plan-v01-000001", "current_state_id": "gen-000001",
            "chapter_plan_ids": ["chapter-plan-v01-c01-000001"],
            "scene_ids": ["scene-v01-c01-s01-000001"],
            "quality_ids": ["quality-000001"],
            "scenes": [{"scene_id": "scene-v01-c01-s01-000001", "prose": "本文です。"}],
            "has_remaining_major_issues": False, "volume_count": 1,
        }
        with (
            patch("storycraft.volume_publication_stage.resolve_selection", return_value={}),
            patch.object(VolumePublicationStageService, "_publication_inputs", return_value=inputs),
            patch("storycraft.volume_publication_stage.recover_pending_commit", side_effect=RuntimeError("stop after staging")),
        ):
            with self.assertRaisesRegex(RuntimeError, "stop after staging"):
                VolumePublicationStageService(root).run(workspace_already_validated=True, updated_at=NOW)
        pending = RunStateStore(root).load()["pending_commit"]
        assert isinstance(pending, dict)
        self.assertEqual(pending["state_update"], {
            "status": "completed",
            "last_error": None,
            "current_selection_id": "selection-000011",
            "current_stage": None,
            "current_target": None,
            "published_volumes": [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
        })


if __name__ == "__main__":
    unittest.main()
