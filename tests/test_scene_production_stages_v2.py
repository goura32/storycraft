from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from typing import Any

from storycraft.artifact_ids import initial_counters
from storycraft.artifact_registry import artifact_directory
from storycraft.run_state import RunStateStore
from storycraft.selection_authority import resolve_selection
from storycraft.scene_card_stage import SceneCardStageService
from storycraft.scene_commit_stage import SceneCommitStageService
from storycraft.scene_continuity_stage import SceneContinuityStageService
from storycraft.scene_prose_stage import SceneProseStageService
from storycraft.selection_snapshot import SelectionSnapshotStore
from storycraft.workspace import validate_workspace

NOW = "2026-07-31T00:00:00Z"
COORDINATE = {"volume_number": 3, "chapter_number": 2, "scene_number": 4}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_content(root: Path, kind: str, artifact_id: str, selection_id: str, content: dict[str, Any]) -> None:
    write_json(root / artifact_directory(kind, artifact_id) / "record.json", {
        "schema_version": 1, "artifact_id": artifact_id, "artifact_kind": kind,
        "input_selection_id": selection_id, "created_at": NOW, "content": content,
    })


class Model:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.contexts: dict[str, dict[str, Any]] = {}
        self.last_call_id: str | None = None

    def _record_physical_call(self, operation: str, stage: str, response: object) -> None:
        call_id = f"call-{len(list((self.root / 'runtime/calls').iterdir())) + 1:06d}"
        selection_id = RunStateStore(self.root).load()["current_selection_id"]
        candidates = sorted(path.name for path in (self.root / "candidates").iterdir())
        candidate_id = candidates[-1] if candidates else None
        write_json(self.root / "runtime/calls" / call_id / "record.json", {
            "schema_version": 1, "call_id": call_id, "operation": operation,
            "role": "test-model", "target_candidate_id": candidate_id if operation in {"review", "revise"} else None,
            "input_refs": [selection_id, *([candidate_id] if operation in {"review", "revise"} else [])],
            "technical_attempt": 1, "format_attempt": 1, "seed": 1,
            "endpoint": "injected", "model": "test", "settings_id": "settings-000001",
            "request": json.dumps({"stage": stage, "operation": operation}, ensure_ascii=False, sort_keys=True),
            "response": json.dumps(response, ensure_ascii=False, sort_keys=True), "transport": "success",
            "validation": {"result": "valid", "checks": [], "failure_code": None},
        })
        self.last_call_id = call_id

    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        self.contexts[stage] = context
        payloads = {
            "scene_card": {"pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main", "story_time": "夜", "purpose": "展開", "opening_state": "開始", "required_beats": [{"beat_id": "beat-01", "description": "展開", "required": True, "order_hint": 1}], "conflict": "対立", "allowed_revelations": [], "required_revelations": [], "forbidden_revelations": [], "allowed_updates": [], "ending_state_targets": ["変化"], "style_constraints": ["簡潔"]},
            "scene_continuity": {"coordinate": COORDINATE, "changes": [{"op": "set", "target": "timeline_position", "path": "$.timeline_position", "value": 1, "evidence_locations": ["prose:0"]}]},
        }
        if stage == "scene_card":
            payloads[stage]["purpose"] = context["scene_plan"]["purpose"]
            payloads[stage]["allowed_updates"] = [{"target_type": "timeline_position", "target_id": "timeline_position", "allowed_fields": ["value"]}]
        kinds = {"scene_card": "scene-card", "scene_continuity": "continuity-update"}
        response = {"schema_version": "candidate-response-v1", "artifact_kind": kinds[stage], "payload": payloads[stage]}
        self._record_physical_call("generate", stage, response)
        return response

    def generate_prose(self, stage: str, context: dict[str, Any]) -> str:
        self.contexts[stage] = context
        self._record_physical_call("generate", stage, "場面本文")
        return "場面本文"

    def critique_prose(self, stage: str, candidate: str, context: dict[str, Any]) -> dict[str, Any]:
        del candidate, context
        response = {"schema_version": "review-response-v1", "decision": "pass", "issues": []}
        self._record_physical_call("review", stage, response)
        return response

    def revision_prose(self, stage: str, candidate: str, review: dict[str, Any], context: dict[str, Any]) -> str:
        del candidate, review, context
        raise AssertionError("passing prose review must not revise")

    def review(self, stage: str, context: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        response = {"schema_version": "review-response-v1", "decision": "pass", "issues": []}
        self._record_physical_call("review", stage, response)
        return response

    def revise(self, stage: str, context: dict[str, Any], candidate: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
        self._record_physical_call("revise", stage, candidate)
        raise AssertionError("passing review must not revise")


class SceneProductionStagesV2Tests(unittest.TestCase):
    def _workspace(self, root: Path) -> None:
        for directory in ("inputs", "runtime/settings", "runtime/selections", "runtime/staging", "runtime/adoptions", "runtime/calls", "candidates", "reviews", "quality", "design/initial", "design/series-plans", "design/volume-plans", "design/chapter-plans", "design/scene-plans", "design/scene-cards", "generations", "scenes", "publications"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        write_json(root / "runtime/counters.json", initial_counters())
        write_json(root / "inputs/request-000001/record.json", {"schema_version": 1, "artifact_id": "request-000001", "artifact_kind": "request", "input_selection_id": None, "created_at": NOW, "content": {"title": "題", "genre": ["fantasy"], "premise": "前提", "required_elements": [], "avoid": [], "ending_preference": "希望", "volume_count": 4, "language": "ja"}})
        write_json(root / "runtime/settings/settings-000001/record.json", {"schema_version": 1, "settings_id": "settings-000001", "payload": {"endpoint": "injected", "model": "test", "quality_revision_limit": 1, "invalid_response_limit": 5, "scene_text_char_range": [1, 100]}, "created_at": NOW})
        selections = SelectionSnapshotStore(root)
        base = selections.create(input_selection_id=None, created_at=NOW, slots={"request": "request-000001", "settings": "settings-000001"})
        
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
            "character_arc_map": {"char-main": [1]}, "relationship_arc_map": {"rel-main": [1]}, "thread_progression": {"thread-main": [1]},
            "revelation_schedule": [{"volume_number": 1, "knowledge_id": "know-main"}], "ending_path": "完結", "global_constraints": []
        }
        volume_plan_content = {
            "title": "第三巻", "starting_state_summary": "開始", "volume_purpose": "目的", "central_conflict": "対立",
            "character_changes": {"char-main": "変化"}, "relationship_changes": {"rel-main": "変化"}, "thread_goals": {"thread-main": "進展"}, "revelations": [],
            "chapter_summaries": [{"chapter_number": n, "purpose": f"章{n}"} for n in range(1, 4)], "required_end_state": "次へ", "handoff_expectations": []
        }
        chapter_plan_content = {
            "title": "第二章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"],
            "scene_summaries": [{"scene_number": n, "purpose": f"場面{n}"} for n in range(1, 5)], "required_revelations": [], "constraints": []
        }
        
        # Valid scene-plan content per closed schema
        scene_plan_content = {
            "purpose": "場面4",
            "pov_character_id": "char-main",
            "participant_ids": ["char-main"],
            "location_id": "loc-main",
            "starting_conditions": ["開始"],
            "intended_beats": ["展開"],
            "intended_revelations": [],
            "intended_changes": ["変化"],
            "prohibited_disclosures": []
        }
        
        # Valid generation content per closed schema
        generation_content = {
            "story_facts": [{"fact_id": "fact-000001", "value": "開始"}],
            "character_knowledge": {"char-main": []},
            "reader_disclosures": [],
            "unresolved_thread_states": {},
            "timeline_position": 0,
        }
        
        records = {
            "initial-design": ("initial-design-000001", initial_design_content),
            "series-plan": ("series-plan-000001", series_plan_content),
            "volume-plan": ("volume-plan-v03-000001", volume_plan_content),
            "chapter-plan": ("chapter-plan-v03-c02-000001", chapter_plan_content),
            "scene-plan": ("scene-plan-v03-c02-s04-000001", scene_plan_content),
            "generation": ("gen-000001", generation_content),
        }
        for kind, (artifact_id, content) in records.items():
            write_content(root, kind, artifact_id, base["selection_id"], content)
        parent = selections.create(input_selection_id=base["selection_id"], created_at=NOW, slots={
            "request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001",
            "series_plan": "series-plan-000001", "volume_plan.v03": "volume-plan-v03-000001",
            "chapter_plan.v03.c02": "chapter-plan-v03-c02-000001", "current_state": "gen-000001",
        })
        scene_plan_path = root / artifact_directory("scene-plan", "scene-plan-v03-c02-s04-000001") / "record.json"
        scene_plan_record = json.loads(scene_plan_path.read_text(encoding="utf-8"))
        scene_plan_record["input_selection_id"] = parent["selection_id"]
        write_json(scene_plan_path, scene_plan_record)
        current = selections.create(input_selection_id=parent["selection_id"], created_at=NOW, slots={
            "request": "request-000001", "settings": "settings-000001", "initial_design": "initial-design-000001",
            "series_plan": "series-plan-000001", "volume_plan.v03": "volume-plan-v03-000001",
            "chapter_plan.v03.c02": "chapter-plan-v03-c02-000001", "scene_plan.v03.c02.s04": "scene-plan-v03-c02-s04-000001",
            "scene_plan_adoption.v03.c02.s04": "adoption-000009",
            "current_state": "gen-000001",
        })
        write_json(root / "runtime/adoptions/adoption-000009/record.json", {"schema_version": 1, "adoption_id": "adoption-000009", "source_kind": "direct_request", "candidate_id": None, "quality_id": None, "output_content_artifact_ids": ["request-000001"], "output_selection_id": current["selection_id"], "input_selection_id": None, "created_at": NOW})
        RunStateStore(root).save({"schema_version": 3, "workspace_id": "ws-000001", "status": "running", "last_error": None, "current_stage": "scene_card", "current_target": COORDINATE, "current_selection_id": current["selection_id"], "pending_commit": None, "published_volumes": [], "created_at": NOW, "updated_at": NOW})

    def test_real_candidate_adoptions_chain_scene_card_to_prose_to_continuity_to_scene_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._workspace(root)
            model = Model(root)

            card_state = SceneCardStageService(root).run(model, workspace_already_validated=True, updated_at=NOW)
            self.assertEqual(card_state["current_stage"], "scene_prose")
            prose_state = SceneProseStageService(root).run(model, workspace_already_validated=True, updated_at=NOW)
            self.assertEqual(prose_state["current_stage"], "scene_continuity")
            prose_selection = SelectionSnapshotStore(root).load(prose_state["current_selection_id"])
            self.assertEqual(prose_selection["slots"]["scene_prose.v03.c02.s04"], "scene-prose-v03-c02-s04-000001")
            self.assertEqual(prose_selection["slots"]["scene_prose_adoption.v03.c02.s04"], "adoption-000002")
            self.assertEqual(prose_selection["slots"]["scene_prose_disposition.v03.c02.s04"], "quality-000002")

            continuity_state = SceneContinuityStageService(root).run(model, workspace_already_validated=True, updated_at=NOW)
            self.assertEqual(continuity_state["current_stage"], "scene_commit")
            continuity_selection = SelectionSnapshotStore(root).load(continuity_state["current_selection_id"])
            self.assertEqual(continuity_selection["slots"]["continuity_update.v03.c02.s04"], "continuity-v03-c02-s04-000001")
            self.assertEqual(continuity_selection["slots"]["continuity_adoption.v03.c02.s04"], "adoption-000003")
            self.assertEqual(continuity_selection["slots"]["continuity_disposition.v03.c02.s04"], "quality-000003")

            resolved = resolve_selection(
                root, SelectionSnapshotStore(root).load(continuity_state["current_selection_id"]),
            )
            commit_inputs = SceneCommitStageService._inputs(resolved, 3, 2, 4)
            self.assertEqual(commit_inputs["scene_prose"]["artifact_id"], "scene-prose-v03-c02-s04-000001")
            self.assertEqual(commit_inputs["continuity_update"]["artifact_id"], "continuity-v03-c02-s04-000001")
            self.assertEqual(commit_inputs["scene_prose_disposition"]["quality_id"], "quality-000002")
            self.assertEqual(model.contexts["scene_prose"].keys(), {"settings", "current_state", "scene_plan", "scene_card", "volume_number", "chapter_number", "scene_number"})
            self.assertEqual(model.contexts["scene_continuity"].keys(), {"settings", "current_state", "scene_plan", "scene_card", "scene_prose", "volume_number", "chapter_number", "scene_number"})
            validate_workspace(root)


if __name__ == "__main__":
    unittest.main()
