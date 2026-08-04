from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any
import unittest
from unittest.mock import patch

from storycraft.artifact_ids import initial_counters
from storycraft.artifact_registry import artifact_directory, ARTIFACT_SPECS
from storycraft.chapter_plan_stage import ChapterPlanStageService
from storycraft.run_state import RunStateStore
from storycraft.scene_card_stage import SceneCardStageService
from storycraft.scene_plan_stage import ScenePlanStageService
from storycraft.selection_snapshot import SelectionSnapshotStore
from storycraft.series_contracts import ContractError
from storycraft.series_plan_stage import SeriesPlanStageService
from storycraft.volume_plan_stage import VolumePlanStageService
from storycraft.workspace import validate_workspace

NOW = "2026-07-31T00:00:00Z"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_content(root: Path, kind: str, artifact_id: str, selection_id: str, content: dict[str, Any]) -> None:
    write_json(root / artifact_directory(kind, artifact_id) / "record.json", {
        "schema_version": 1,
        "artifact_id": artifact_id,
        "artifact_kind": kind,
        "input_selection_id": selection_id,
        "created_at": NOW,
        "content": content,
    })


def write_adoption(root: Path, artifact_id: str, source_kind: str, output_content_artifact_ids: list[str],
                  input_selection_id: str | None, output_selection_id: str = "selection-000002") -> None:
    """Write a flat adoption record (no content wrapper)."""
    content = {
        "schema_version": 1,
        "adoption_id": artifact_id,
        "source_kind": source_kind,
        "candidate_id": None if source_kind == "direct_request" else "candidate-000001",
        "quality_id": None if source_kind == "direct_request" else "quality-000001",
        "output_content_artifact_ids": output_content_artifact_ids,
        "output_selection_id": output_selection_id,
        "input_selection_id": input_selection_id,
        "created_at": NOW,
    }
    write_json(root / artifact_directory("adoption", artifact_id) / "record.json", content)


class Model:
    def __init__(self, root: Path, kind: str) -> None:
        self.root = root
        self.kind = kind
        self.contexts: list[dict[str, Any]] = []
        self.last_call_id: str | None = None

    def _record_physical_call(self, operation: str, response: object) -> None:
        call_id = f"call-{len(list((self.root / 'runtime/calls').iterdir())) + 1:06d}"
        selection_id = RunStateStore(self.root).load()["current_selection_id"]
        candidates = sorted(path.name for path in (self.root / "candidates").iterdir())
        candidate_id = candidates[-1] if candidates else None
        write_json(self.root / "runtime/calls" / call_id / "record.json", {
            "schema_version": 1,
            "call_id": call_id,
            "operation": operation,
            "role": "test-model",
            "target_candidate_id": candidate_id if operation in {"review", "revise"} else None,
            "input_refs": [selection_id, *([candidate_id] if operation in {"review", "revise"} else [])],
            "technical_attempt": 1,
            "format_attempt": 1,
            "seed": 1,
            "endpoint": "injected",
            "model": "fake",
            "settings_id": "settings-000001",
            "request": json.dumps({"stage": self.kind, "operation": operation}, ensure_ascii=False, sort_keys=True),
            "response": json.dumps(response, ensure_ascii=False, sort_keys=True),
            "transport": "success",
            "validation": {"result": "valid", "checks": [], "failure_code": None},
        })
        self.last_call_id = call_id

    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        self.contexts.append(context)
        payloads = {
            "series-plan": {"volume_count": 4, "series_objectives": ["完結"], "volume_summaries": [{"volume_number": n, "purpose": f"巻{n}", "ending_change": "変化"} for n in range(1, 5)], "character_arc_map": {"char-main": [1]}, "relationship_arc_map": {"rel-main": [1]}, "thread_progression": {"塔の試練": [1]}, "revelation_schedule": [{"volume_number": 1, "knowledge_id": "know-main"}], "ending_path": "完結", "global_constraints": []},
            "volume-plan": {"title": "巻", "starting_state_summary": "開始", "volume_purpose": "目的", "central_conflict": "対立", "character_changes": {"char-main": "変化"}, "relationship_changes": {"rel-main": "変化"}, "thread_goals": {"thread-main": "進展"}, "revelations": [], "chapter_summaries": [{"chapter_number": 1, "purpose": "章"}], "required_end_state": "終了", "handoff_expectations": []},
            "chapter-plan": {"title": "章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"], "scene_summaries": [{"scene_number": 1, "purpose": "展開"}], "required_revelations": [], "constraints": []},
            "scene-plan": {"purpose": "場面4", "pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main", "starting_conditions": ["開始"], "intended_beats": ["展開"], "intended_revelations": [], "intended_changes": ["変化"], "prohibited_disclosures": []},
            "scene-card": {"pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main", "story_time": "夜", "purpose": "場面4", "opening_state": "開始", "required_beats": [{"beat_id": "beat-01", "description": "展開", "required": True, "order_hint": 1}], "conflict": "対立", "allowed_revelations": [], "required_revelations": [], "forbidden_revelations": [], "allowed_updates": [{"target_type": "timeline_position", "target_id": "timeline_position", "allowed_fields": ["value"]}], "ending_state_targets": ["変化"], "style_constraints": ["簡潔"]},
        }
        if self.kind == "scene-plan":
            payloads["scene-plan"]["purpose"] = f"場面{self.contexts[-1]['scene_number']}"
        if self.kind == "scene-card":
            payloads["scene-card"]["purpose"] = self.contexts[-1]["scene_plan"]["purpose"]
        response = {"schema_version": "candidate-response-v1", "artifact_kind": self.kind, "payload": payloads.get(self.kind, {"stage": stage})}
        self._record_physical_call("generate", response)
        return response

    def review(self, stage: str, context: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        response = {"schema_version": "review-response-v1", "decision": "pass", "issues": []}
        self._record_physical_call("review", response)
        return response

    def revise(self, stage: str, context: dict[str, Any], candidate: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
        self._record_physical_call("revise", candidate)
        raise AssertionError("a passing review must not revise")


class PlanningStagesV2Tests(unittest.TestCase):
    def _workspace(self, root: Path, *, stage: str, target: dict[str, int], slots: dict[str, str], skip_final: str | None = None, expected_id: str | None = None) -> None:
        for directory in ("inputs", "runtime/settings", "runtime/selections", "runtime/staging", "runtime/adoptions", "runtime/calls", "candidates", "reviews", "quality", "design/initial", "design/series-plans", "design/volume-plans", "design/chapter-plans", "design/scene-plans", "design/scene-cards", "generations", "scenes", "publications"):
            (root / directory).mkdir(parents=True, exist_ok=True)

        # Define content for each kind
        initial_design_content = {
            "schema_version": 1,
            "core": {"logline": "英雄の旅", "premise": "選択の物語", "central_question": "何を守るのか", "themes": ["選択"], "dramatic_engine": "選択が障害を生む", "tone": ["希望"], "reader_promise": "人物の選択が結末を変える", "ending_direction": "責任を引き受ける"},
            "cast": [{"name": "主人公", "role": "英雄", "description": "選択を迫られる", "relationships": []}],
            "world": {"settings": ["剣と魔法"], "constraints": ["契約を破れない"], "institutions": ["王国"]},
            "knowledge_model": {"author_knows": ["秘密"], "character_knows": {"主人公": ["目的"]}, "reader_knows": ["目的"]},
            "unresolved_threads": [{"name": "塔の試練", "type": "goal", "required_for_ending": True, "description": "塔を登頂する"}],
            "ending_conditions": [{"thread_name": "塔の試練", "condition": "塔を登頂する"}],
        }
        generation_content = {
            "story_facts": [{"fact_id": "fact-000001", "value": "開始"}],
            "character_knowledge": {"char-main": []},
            "reader_disclosures": [],
            "unresolved_thread_states": {},
            "timeline_position": 0,
        }
        series_plan_content = {
            "volume_count": 4,
            "series_objectives": ["完結"],
            "volume_summaries": [{"volume_number": n, "purpose": f"巻{n}", "ending_change": "変化"} for n in range(1, 5)],
            "character_arc_map": {"char-main": [1]},
            "relationship_arc_map": {"rel-main": [1]},
            "thread_progression": {"thread-main": [1]},
            "revelation_schedule": [{"volume_number": 1, "knowledge_id": "know-main"}],
            "ending_path": "完結",
            "global_constraints": []
        }
        volume_plan_v03_content = {
            "title": "第三巻", "starting_state_summary": "開始", "volume_purpose": "目的", "central_conflict": "対立",
            "character_changes": {"char-main": "変化"}, "relationship_changes": {"rel-main": "変化"},
            "thread_goals": {"thread-main": "進展"}, "revelations": [],
            "chapter_summaries": [{"chapter_number": n, "purpose": f"章{n}"} for n in range(1, 4)],
            "required_end_state": "次へ", "handoff_expectations": []
        }
        volume_plan_v02_content = {**volume_plan_v03_content, "title": "第二巻", "chapter_summaries": [{"chapter_number": n, "purpose": f"章{n}"} for n in range(1, 3)]}
        chapter_plan_content = {
            "title": "第三章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"],
            "scene_summaries": [{"scene_number": n, "purpose": f"場面{n}"} for n in range(1, 5)],
            "required_revelations": [], "constraints": []
        }
        scene_plan_content = {
            "purpose": "場面4",
            "pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main",
            "starting_conditions": ["開始"], "intended_beats": ["展開"], "intended_revelations": [], "intended_changes": ["変化"], "prohibited_disclosures": []
        }
        KIND_TO_CONTENT = {
            "initial-design": initial_design_content,
            "generation": generation_content,
            "series-plan": series_plan_content,
            "volume-plan": volume_plan_v03_content,
            "chapter-plan": chapter_plan_content,
            "scene-plan": scene_plan_content,
        }

        # Always write request and settings
        write_json(root / "runtime/counters.json", initial_counters())
        write_json(root / "inputs/request-000001/record.json", {
            "schema_version": 1,
            "artifact_id": "request-000001",
            "artifact_kind": "request",
            "input_selection_id": None,
            "created_at": NOW,
            "content": {
                "title": "t", "genre": ["f"], "premise": "p", "required_elements": [],
                "avoid": [], "ending_preference": "e", "volume_count": 4,
                "language": "ja"
            }
        })
        write_json(root / "runtime/settings/settings-000001/record.json", {
            "schema_version": 1,
            "settings_id": "settings-000001",
            "payload": {"endpoint": "injected", "model": "fake", "quality_revision_limit": 1, "invalid_response_limit": 5},
            "created_at": NOW
        })

        # Write artifacts based on slots
        base = SelectionSnapshotStore(root).create(input_selection_id=None, created_at=NOW, slots={"request": "request-000001", "settings": "settings-000001"})
        assert base["selection_id"] == "selection-000001"

        for slot, artifact_id in slots.items():
            if slot in ("request", "settings"):
                continue
            # Determine kind from slot
            prefix = slot.split('.')[0]
            slot_to_kind = {
                "initial_design": "initial-design",
                "generation": "generation",
                "series_plan": "series-plan",
                "volume_plan": "volume-plan",
                "chapter_plan": "chapter-plan",
                "scene_plan": "scene-plan",
                "scene_card": "scene-card",
                "scene_prose": "scene-prose",
                "continuity_update": "continuity-update",
                "quality_disposition": "quality-disposition",
                "current_state": "generation",
                "initial_design_adoption": "adoption",
                "scene_plan_adoption": "adoption",
            }
            kind = slot_to_kind.get(prefix)
            if kind is None:
                kind = prefix.replace('_', '-')

            # Ensure the directory for this artifact exists
            artifact_dir = root / artifact_directory(kind, artifact_id)
            artifact_dir.mkdir(parents=True, exist_ok=True)

            # Skip writing if this artifact is the final output of the stage under test
            if artifact_id == expected_id:
                continue

            written = False  # track whether we wrote anything for this slot

            if kind == "volume-plan":
                if artifact_id.endswith("v02"):
                    write_content(root, "volume-plan", artifact_id, base["selection_id"], volume_plan_v02_content)
                else:
                    write_content(root, "volume-plan", artifact_id, base["selection_id"], volume_plan_v03_content)
                written = True

            if not written:
                if kind == "adoption":
                    # Direct-request adoption: needs a real content id reference for validation.
                    write_adoption(root, artifact_id, source_kind="direct_request",
                                   output_content_artifact_ids=["request-000001"], input_selection_id=base["selection_id"],
                                   output_selection_id=base["selection_id"])
                    written = True

                if not written and kind in KIND_TO_CONTENT:
                    write_content(root, kind, artifact_id, base["selection_id"], KIND_TO_CONTENT[kind])
                    written = True

        # Write standard baseline artifacts that every test workspace needs:
        if skip_final != "initial-design":
            write_content(root, "initial-design", "initial-design-000001", base["selection_id"], initial_design_content)
        if skip_final != "generation":
            write_content(root, "generation", "gen-000001", base["selection_id"], generation_content)
        if skip_final != "series-plan":
            write_content(root, "series-plan", "series-plan-000001", base["selection_id"], series_plan_content)
        if skip_final != "volume-plan":
            write_content(root, "volume-plan", "volume-plan-v03-000001", base["selection_id"], volume_plan_v03_content)
            write_content(root, "volume-plan", "volume-plan-v02-000001", base["selection_id"], volume_plan_v02_content)
        if skip_final != "chapter-plan":
            write_content(root, "chapter-plan", "chapter-plan-v03-c03-000001", base["selection_id"], chapter_plan_content)
        if skip_final != "scene-plan":
            write_content(root, "scene-plan", "scene-plan-v03-c03-s04-000001", base["selection_id"], scene_plan_content)

        slot_kinds = {
            "request": "request", "settings": "settings", "initial_design": "initial-design", "current_state": "generation",
            "series_plan": "series-plan", "volume_plan": "volume-plan", "chapter_plan": "chapter-plan",
            "initial_design_adoption": "adoption",
        }
        parent_slots = {
            slot: artifact_id for slot, artifact_id in slots.items()
            if not slot.startswith("scene_plan")
            and slot.split(".")[0] in slot_kinds
            and (root / artifact_directory(slot_kinds[slot.split(".")[0]], artifact_id) / "record.json").is_file()
        }
        if any(slot.startswith("scene_plan") for slot in slots):
            for slot, kind, artifact_id in (
                ("series_plan", "series-plan", "series-plan-000001"),
                ("volume_plan.v03", "volume-plan", "volume-plan-v03-000001"),
                ("chapter_plan.v03.c03", "chapter-plan", "chapter-plan-v03-c03-000001"),
            ):
                if (root / artifact_directory(kind, artifact_id) / "record.json").is_file():
                    parent_slots[slot] = artifact_id
        parent = SelectionSnapshotStore(root).create(input_selection_id=base["selection_id"], created_at=NOW, slots=parent_slots)
        scene_plan_id = slots.get("scene_plan.v03.c03.s04")
        if scene_plan_id:
            scene_plan_path = root / artifact_directory("scene-plan", scene_plan_id) / "record.json"
            scene_plan_record = json.loads(scene_plan_path.read_text(encoding="utf-8"))
            scene_plan_record["input_selection_id"] = parent["selection_id"]
            write_json(scene_plan_path, scene_plan_record)
        if any(slot.startswith("scene_plan") for slot in slots):
            selection = SelectionSnapshotStore(root).create(input_selection_id=parent["selection_id"], created_at=NOW, slots=slots)
        else:
            selection = parent
        RunStateStore(root).save({
            "schema_version": 3,
            "workspace_id": "ws-000001",
            "status": "running",
            "last_error": None,
            "current_stage": stage,
            "current_target": target,
            "current_selection_id": selection["selection_id"],
            "pending_commit": None,
            "published_volumes": (
                [{"volume_number": number, "publication_id": f"volume-pub-v{number:02d}-000001"}
                 for number in range(1, target.get("volume_number", 1))]
                if stage == "volume_plan" else []
            ),
            "created_at": NOW,
            "updated_at": NOW
        })

    def _assert_stage(self, service: Any, kind: str, stage: str, target: dict[str, int], slots: dict[str, str],
                      expected_context_keys: set[str], next_stage: str, next_target: dict[str, int], expected_id: str,
                      *, staged_only: bool = False) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._workspace(root, stage=stage, target=target, slots=slots, skip_final=kind, expected_id=expected_id)
            model = Model(root, kind.replace('_', '-'))
            input_selection_id = RunStateStore(root).load()["current_selection_id"]
            if staged_only:
                with patch("storycraft.candidate_stage.recover_pending_commit", side_effect=lambda _: RunStateStore(root).load()):
                    result = service(root).run(model, workspace_already_validated=True, updated_at=NOW)
            else:
                result = service(root).run(model, workspace_already_validated=True, updated_at=NOW)
            self.assertEqual(set(model.contexts[0]), expected_context_keys)
            if staged_only:
                manifest = result["pending_commit"]
                assert isinstance(manifest, dict)
                next_selection_id = manifest["state_update"]["current_selection_id"]
                self.assertEqual(manifest["state_update"], {
                    "current_selection_id": next_selection_id,
                    "current_stage": next_stage,
                    "current_target": next_target
                })
                next_selection = json.loads((root / manifest["staging_path"] / f"{next_selection_id}/record.json").read_text(encoding="utf-8"))
            else:
                self.assertEqual(result["current_stage"], next_stage)
                self.assertEqual(result["current_target"], next_target)
                self.assertIsNone(result["pending_commit"])
                next_selection = SelectionSnapshotStore(root).load(result["current_selection_id"])
                validate_workspace(root)
            self.assertEqual(next_selection["input_selection_id"], input_selection_id)
            self.assertEqual(next_selection["slots"][next(slot for slot in next_selection["slots"] if next_selection["slots"][slot] == expected_id)], expected_id)

    def test_series_plan_uses_required_selection_slots_and_transitions(self) -> None:
        self._assert_stage(
            service=SeriesPlanStageService, kind="series-plan", stage="series_plan", target={},
            slots={
                "request": "request-000001",
                "settings": "settings-000001",
                "initial_design": "initial-design-000001",
                "current_state": "gen-000001",
                "initial_design_adoption": "adoption-000009"
            },
            expected_context_keys={"request", "settings", "initial_design", "current_state"},
            next_stage="volume_plan", next_target={"volume_number": 1},
            expected_id="series-plan-000001", staged_only=True
        )

    def test_volume_plan_uses_current_bundle_and_coordinate(self) -> None:
        self._assert_stage(
            service=VolumePlanStageService, kind="volume-plan", stage="volume_plan", target={"volume_number": 3},
            slots={
                "settings": "settings-000001",
                "current_state": "gen-000001",
                "series_plan": "series-plan-000001",
                "volume_plan.v02": "volume-plan-v02-000001"
            },
            expected_context_keys={"settings", "current_state", "series_plan", "prior_volume_plan", "volume_number"},
            next_stage="chapter_plan", next_target={"volume_number": 3, "chapter_number": 1},
            expected_id="volume-plan-v03-000001", staged_only=True
        )

    def test_volume_plan_rejects_a_target_that_skips_unpublished_volumes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._workspace(
                root,
                stage="volume_plan",
                target={"volume_number": 3},
                slots={
                    "settings": "settings-000001",
                    "current_state": "gen-000001",
                    "series_plan": "series-plan-000001",
                    "volume_plan.v02": "volume-plan-v02-000001",
                },
            )
            state = RunStateStore(root).load()
            state["published_volumes"] = []
            RunStateStore(root).save(state)
            with self.assertRaisesRegex(ContractError, "公開済み巻"):
                VolumePlanStageService(root).run(None, workspace_already_validated=True, updated_at=NOW)

    def test_volume_plan_rejects_a_prior_plan_with_the_wrong_coordinate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._workspace(
                root,
                stage="volume_plan",
                target={"volume_number": 3},
                slots={
                    "settings": "settings-000001",
                    "current_state": "gen-000001",
                    "series_plan": "series-plan-000001",
                    "volume_plan.v02": "volume-plan-v03-000001",
                },
            )
            with self.assertRaisesRegex(ContractError, "selection slot"):
                VolumePlanStageService(root).run(None, workspace_already_validated=True, updated_at=NOW)

    def test_volume_plan_rejects_regeneration_when_target_slot_is_already_present(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._workspace(
                root,
                stage="volume_plan",
                target={"volume_number": 3},
                slots={
                    "settings": "settings-000001",
                    "current_state": "gen-000001",
                    "series_plan": "series-plan-000001",
                    "volume_plan.v02": "volume-plan-v02-000001",
                    "volume_plan.v03": "volume-plan-v03-000001",
                },
            )
            with self.assertRaisesRegex(ContractError, "既にselection"):
                VolumePlanStageService(root).run(None, workspace_already_validated=True, updated_at=NOW)

    def test_chapter_plan_uses_current_bundle_and_coordinate(self) -> None:
        self._assert_stage(
            service=ChapterPlanStageService, kind="chapter-plan", stage="chapter_plan",
            target={"volume_number": 3, "chapter_number": 3},
            slots={
                "settings": "settings-000001",
                "initial_design": "initial-design-000001",
                "current_state": "gen-000001",
                "series_plan": "series-plan-000001",
                "volume_plan.v03": "volume-plan-v03-000001"
            },
            expected_context_keys={"settings", "initial_design", "current_state", "series_plan", "volume_plan", "volume_number", "chapter_number"},
            next_stage="scene_plan", next_target={"volume_number": 3, "chapter_number": 3, "scene_number": 1},
            expected_id="chapter-plan-v03-c03-000001"
        )

    def test_scene_plan_uses_current_bundle_and_coordinate(self) -> None:
        self._assert_stage(
            service=ScenePlanStageService, kind="scene-plan", stage="scene_plan",
            target={"volume_number": 3, "chapter_number": 3, "scene_number": 4},
            slots={
                "settings": "settings-000001",
                "initial_design": "initial-design-000001",
                "current_state": "gen-000001",
                "series_plan": "series-plan-000001",
                "volume_plan.v03": "volume-plan-v03-000001",
                "chapter_plan.v03.c03": "chapter-plan-v03-c03-000001"
            },
            expected_context_keys={"settings", "initial_design", "current_state", "series_plan", "volume_plan", "chapter_plan", "volume_number", "chapter_number", "scene_number"},
            next_stage="scene_card", next_target={"volume_number": 3, "chapter_number": 3, "scene_number": 4},
            expected_id="scene-plan-v03-c03-s04-000001"
        )

    def test_scene_card_requires_the_selected_scene_plan_adoption(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._workspace(root, stage="scene_card", target={
                "volume_number": 3, "chapter_number": 3, "scene_number": 4
            }, slots={
                "settings": "settings-000001",
                "initial_design": "initial-design-000001",
                "current_state": "gen-000001",
                "scene_plan.v03.c03.s04": "scene-plan-v03-c03-s04-000001"
            })
            with self.assertRaisesRegex(Exception, "必須slot"):
                SceneCardStageService(root).run(Model(root, "scene-card"), workspace_already_validated=True, updated_at=NOW)

    def test_scene_card_uses_current_bundle_and_coordinate(self) -> None:
        self._assert_stage(
            service=SceneCardStageService, kind="scene-card", stage="scene_card",
            target={"volume_number": 3, "chapter_number": 3, "scene_number": 4},
            slots={
                "settings": "settings-000001",
                "initial_design": "initial-design-000001",
                "current_state": "gen-000001",
                "scene_plan.v03.c03.s04": "scene-plan-v03-c03-s04-000001",
                "scene_plan_adoption.v03.c03.s04": "adoption-000009"
            },
            expected_context_keys={"settings", "initial_design", "current_state", "scene_plan", "volume_number", "chapter_number", "scene_number"},
            next_stage="scene_prose", next_target={"volume_number": 3, "chapter_number": 3, "scene_number": 4},
            expected_id="scene-card-v03-c03-s04-000001"
        )
