"""V2 volume-publication stage contracts: registry inputs and generic recovery."""
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
        "initial-design": "design/initial-designs",
        "series-plan": "design/series-plans", "volume-plan": "design/volume-plans",
        "chapter-plan": "design/chapter-plans", "scene-prose": "scenes", "scene": "scenes",
        "generation": "generations",
    }
    write_json(root / locations[kind] / artifact_id / "record.json", content_record(artifact_id, kind, selection_id, content))


def quality_record(quality_id: str, candidate_id: str, review_id: str, *, notice: bool = False) -> dict:
    return {
        "schema_version": 1, "quality_id": quality_id, "candidate_id": candidate_id,
        "review_record_ids": [review_id], "revision_count": 0,
        "result": "accepted_with_notice" if notice else "accepted",
        "remaining_major_issues": ["remaining"] if notice else [],
        **({"notice_type": "編集"} if notice else {}), "created_at": NOW,
    }


def write_quality_audit(root: Path, quality_id: str, prose: dict, *, notice: bool) -> None:
    suffix = quality_id.rsplit("-", 1)[1]
    candidate_id, review_id = f"candidate-{suffix}", f"review-{suffix}"
    generate_call_id, review_call_id = f"call-{suffix}", f"call-{900000 + int(suffix):06d}"
    write_json(root / "runtime/calls" / generate_call_id / "record.json", {
        "schema_version": 1, "call_id": generate_call_id, "operation": "generate", "role": "scene_prose",
        "target_candidate_id": None, "input_refs": [], "technical_attempt": 1, "format_attempt": 1,
        "seed": 1, "endpoint": "injected", "model": "test", "settings_id": "settings-000001",
        "request": "{}", "response": "{}", "transport": "success",
        "validation": {"result": "valid", "checks": [], "failure_code": None},
    })
    write_json(root / "candidates" / candidate_id / "record.json", {
        "schema_version": 1, "candidate_id": candidate_id, "artifact_kind": "scene-prose",
        "input_selection_id": "selection-000001", "keywords_id": None, "settings_id": "settings-000001",
        "payload": prose, "parent_candidate_id": None, "review_record_id": None,
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
        "schema_version": 1, "call_id": review_call_id, "operation": "review", "role": "scene_prose",
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
        "runtime/staging", "runtime/selections", "runtime/calls", "runtime/validations",
        "runtime/adoptions", "design", "design/initial", "design/series-plans",
        "design/volume-plans", "design/chapter-plans", "design/scene-plans", "generations",
        "scenes", "publications",
    ):
        (root / relative).mkdir(parents=True, exist_ok=True)
    write_json(root / "runtime/counters.json", initial_counters())
    write_json(root / "runtime/settings/settings-000001/record.json", {
        "schema_version": 1, "settings_id": "settings-000001", "payload": {"invalid_response_limit": 5}, "created_at": NOW,
    })
    selections = SelectionSnapshotStore(root)
    base = selections.create(slots={"settings": "settings-000001"}, created_at=NOW)
    base_id = base["selection_id"]

    # Valid initial-design content per closed schema
    initial_design_content = {
        "core": "英雄の旅",
        "cast": [{"name": "主人公", "role": "英雄"}],
        "world": "剣と魔法の世界",
        "knowledge_model": {},
        "unresolved_threads": [],
        "ending_conditions": ["塔を登頂する"]
    }
    write_content(root, "initial-design-000001", "initial-design", base_id, initial_design_content)

    # Valid series-plan content per closed schema
    series_plan_content = {
        "volumes": [{"volume_number": n} for n in range(1, volume_count + 1)],
        "thread_allocations": []
    }
    write_content(root, "series-plan-000001", "series-plan", base_id, series_plan_content)

    # Valid volume-plan content per closed schema
    volume_plan_content = {
        "volume_number": 1,
        "chapters": [{"chapter_number": n} for n in range(1, 3)],
        "thread_allocations": []
    }
    write_content(root, "volume-plan-v01-000001", "volume-plan", base_id, volume_plan_content)

    # Valid chapter-plan content per closed schema
    chapter_plan_c01 = {
        "volume_number": 1,
        "chapter_number": 1,
        "scenes": [{"scene_number": n} for n in range(1, 3)],
        "thread_allocations": []
    }
    write_content(root, "chapter-plan-v01-c01-000001", "chapter-plan", base_id, chapter_plan_c01)

    chapter_plan_c02 = {
        "volume_number": 1,
        "chapter_number": 2,
        "scenes": [{"scene_number": n} for n in range(1, 2)],
        "thread_allocations": []
    }
    write_content(root, "chapter-plan-v01-c02-000001", "chapter-plan", base_id, chapter_plan_c02)

    slots = {"settings": "settings-000001", "series_plan": "series-plan-000001", "volume_plan.v01": "volume-plan-v01-000001",
             "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001", "chapter_plan.v01.c02": "chapter-plan-v01-c02-000001"}
    for chapter, scenes in ((1, (1, 2)), (2, (1,))):
        for scene in scenes:
            prose_id = f"scene-v01-c{chapter:02d}-s{scene:02d}-000001"
            committed_id = f"scene-artifact-v01-c{chapter:02d}-s{scene:02d}-000001"
            quality_id = f"quality-{chapter * 10 + scene:06d}"
            if not (omit_scene_source and chapter == 2 and scene == 1):
                # Valid scene-prose content per closed schema
                prose_content = {
                    "coordinate": {"volume_number": 1, "chapter_number": chapter, "scene_number": scene},
                    "text": f"本文 {chapter}-{scene}"
                }
                write_content(root, prose_id, "scene-prose", base_id, prose_content)
            # Valid scene content per closed schema
            scene_content = {
                "coordinate": {"volume_number": 1, "chapter_number": chapter, "scene_number": scene},
                "scene_prose_id": prose_id, "quality_disposition_id": quality_id,
            }
            write_content(root, committed_id, "scene", base_id, scene_content)
            prose = {"coordinate": {"volume_number": 1, "chapter_number": chapter, "scene_number": scene}, "text": f"本文 {chapter}-{scene}"}
            write_quality_audit(root, quality_id, prose, notice=(chapter == 1 and scene == 2))
            coordinate = f"v01.c{chapter:02d}.s{scene:02d}"
            slots[f"scene.{coordinate}"] = committed_id
            slots[f"scene_prose.{coordinate}"] = prose_id
            slots[f"scene_prose_disposition.{coordinate}"] = quality_id
    # Valid generation content per closed schema
    generation_content = {
        "story_facts": [],
        "character_states": {},
        "world_states": {},
        "open_threads": [],
        "last_scene_summary": ""
    }
    write_content(root, "gen-000001", "generation", base_id, generation_content)
    slots["current_state"] = "gen-000001"
    selection = selections.create(input_selection_id=base_id, slots=slots, created_at=NOW)
    RunStateStore(root).save({
        "schema_version": 3, "workspace_id": "ws-000001", "status": "running", "last_error": None,
        "current_stage": "volume_publication", "current_target": {"volume_number": 1},
        "current_selection_id": selection["selection_id"], "pending_commit": None, "published_volumes": [],
        "created_at": NOW, "updated_at": NOW,
    })
    return temporary, root


class VolumePublicationServiceV2Tests(unittest.TestCase):
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
            "current_selection_id": "selection-000002", "current_stage": "volume_plan",
            "current_target": {"volume_number": 2},
            "published_volumes": [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
        })
        self.assertEqual(set(pending["targets"][0]), {"artifact_id", "artifact_kind", "staging_path", "final_path", "status"})
        self.assertEqual(pending["targets"][0]["artifact_kind"], "volume-publication")
        record = json.loads((root / "runtime/staging/volume-publication-volume-pub-v01-000001/volume-pub-v01-000001/record.json").read_text(encoding="utf-8"))
        self.assertEqual(record["scene_ids"], [
            "scene-artifact-v01-c01-s01-000001", "scene-artifact-v01-c01-s02-000001", "scene-artifact-v01-c02-s01-000001",
        ])

    def test_generic_recovery_publishes_sources_in_chapter_scene_order_and_moves_nonfinal_to_next_plan(self) -> None:
        temporary, root = workspace()
        self.addCleanup(temporary.cleanup)
        state = VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertEqual(state["current_stage"], "volume_plan")
        self.assertEqual(state["current_target"], {"volume_number": 2})
        self.assertEqual(state["current_selection_id"], "selection-000002")
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
        record["scene_ids"][0] = "scene-artifact-v01-c01-s01-999999"
        record_path.write_text(json.dumps(record), encoding="utf-8")

        with self.assertRaisesRegex(ContractError, "source/reference evidence"):
            recover_pending_commit(root)

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

    def test_final_volume_reaches_exact_completed_state_after_generic_recovery(self) -> None:
        temporary, root = workspace(volume_count=1)
        self.addCleanup(temporary.cleanup)
        state = VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertEqual(state["status"], "completed")
        self.assertIsNone(state["current_stage"])
        self.assertIsNone(state["current_target"])
        self.assertIsNone(state["pending_commit"])
        self.assertEqual(state["published_volumes"], [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}])

    def test_final_volume_stages_completed_state_in_its_manifest_before_generic_recovery(self) -> None:
        temporary, root = workspace(volume_count=1)
        self.addCleanup(temporary.cleanup)
        inputs = {
            "settings_id": "settings-000001", "series_plan_id": "series-plan-000001",
            "volume_plan_id": "volume-plan-v01-000001", "current_state_id": "gen-000001",
            "chapter_plan_ids": ["chapter-plan-v01-c01-000001"],
            "scene_ids": ["scene-artifact-v01-c01-s01-000001"],
            "quality_ids": ["quality-000001"],
            "scenes": [{"scene_id": "scene-artifact-v01-c01-s01-000001", "prose": "本文です。"}],
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
            "current_selection_id": "selection-000002",
            "current_stage": None,
            "current_target": None,
            "published_volumes": [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
        })


if __name__ == "__main__":
    unittest.main()
