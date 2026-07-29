"""selection snapshot に基づく巻公開 service の回帰。"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from storycraft.publication_recovery import execute_publication_recovery
from storycraft.run_state import RunStateStore
from storycraft.selection_snapshot import SelectionSnapshotStore
from storycraft.workflow_v2 import run_v2
from storycraft.volume_publication_stage import VolumePublicationStageService


NOW = "2026-07-28T00:00:00Z"


def write_record(root: Path, directory: str, artifact_id: str, record: dict) -> None:
    path = root / directory / artifact_id / "record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def workspace(*, volume_count: int) -> tuple[tempfile.TemporaryDirectory[str], Path, dict]:
    temporary = tempfile.TemporaryDirectory()
    root = Path(temporary.name)
    settings_id = "settings-000001"
    series_id = "series-plan-000001"
    volume_id = "volume-plan-v01-000001"
    chapter_id = "chapter-plan-v01c01-000001"
    scene_id = "scene-v01c01s01-000001"
    quality_id = "quality-000001"
    state_id = "gen-000001"
    write_record(root, "runtime/settings", settings_id, {"settings_id": settings_id})
    write_record(root, "design/series-plans", series_id, {"series_plan_id": series_id, "volume_count": volume_count})
    write_record(root, "design/volume-plans", volume_id, {"volume_plan_id": volume_id, "volume_number": 1})
    write_record(root, "design/chapter-plans", chapter_id, {"chapter_plan_id": chapter_id, "volume_number": 1, "chapter_number": 1})
    write_record(root, "scenes", scene_id, {"scene_id": scene_id, "volume_number": 1, "chapter_number": 1, "scene_number": 1, "prose": "第一巻の本文。"})
    write_record(root, "quality", quality_id, {"quality_id": quality_id, "result": "accepted", "remaining_major_issues": []})
    write_record(root, "generations", state_id, {"generation_id": state_id})
    selection = SelectionSnapshotStore(root).create(
        slots={
            "settings": settings_id, "series_plan": series_id, "volume_plan.v01": volume_id,
            "chapter_plan.v01.c01": chapter_id, "scene.v01.c01.s01": scene_id,
            "scene_prose_disposition.v01.c01.s01": quality_id, "current_state": state_id,
        },
        created_at=NOW,
    )
    state = {
        "schema_version": 2, "workspace_id": "ws-test", "run_id": "run-test",
        "status": "running", "stop_reason": None, "last_error": None,
        "current_stage": "volume_publication", "current_target": {"volume_number": 1},
        "current_selection_id": selection["selection_id"], "active_candidate": None,
        "active_scene_id": None, "pending_commit": None, "published_volumes": [],
        "created_at": NOW, "updated_at": NOW,
    }
    RunStateStore(root).save(state)
    (root / "runtime" / "lock").touch()
    return temporary, root, state


class VolumePublicationServiceV2Tests(unittest.TestCase):
    def test_non_final_volume_publishes_one_volume_then_moves_to_next_plan(self) -> None:
        temporary, root, _ = workspace(volume_count=2)
        self.addCleanup(temporary.cleanup)
        state = VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertEqual(state["current_stage"], "volume_plan")
        self.assertEqual(state["current_target"], {"volume_number": 2})
        self.assertEqual(state["published_volumes"], [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}])
        self.assertTrue((root / "publications/volume-pub-v01-000001/record.json").is_file())
        self.assertFalse((root / "completion").exists())

    def test_workflow_dispatches_volume_publication_without_provider(self) -> None:
        temporary, root, _ = workspace(volume_count=2)
        self.addCleanup(temporary.cleanup)
        state = run_v2(root)
        self.assertEqual(state["current_stage"], "volume_plan")
        self.assertEqual(len(state["published_volumes"]), 1)

    def test_final_volume_completes_after_publication(self) -> None:
        temporary, root, _ = workspace(volume_count=1)
        self.addCleanup(temporary.cleanup)
        state = VolumePublicationStageService(root).run(updated_at=NOW)
        self.assertEqual(state["status"], "completed")
        self.assertIsNone(state["current_stage"])
        self.assertEqual(state["published_volumes"][0]["publication_id"], "volume-pub-v01-000001")

    def test_recovery_of_finalized_directory_advances_state_without_republishing(self) -> None:
        temporary, root, initial = workspace(volume_count=2)
        self.addCleanup(temporary.cleanup)
        completed = VolumePublicationStageService(root).run(updated_at=NOW)
        publication_id = completed["published_volumes"][0]["publication_id"]
        final = root / "publications" / publication_id
        record = json.loads((final / "record.json").read_text(encoding="utf-8"))
        manuscript = (final / "manuscript.md").read_text(encoding="utf-8")
        digest = VolumePublicationStageService(root)._digest({"record.json": record, "manuscript.md": manuscript})
        initial["pending_commit"] = {
            "kind": "volume_publication", "staging_path": f"runtime/staging/volume-publication-{publication_id}",
            "input_selection_id": initial["current_selection_id"], "output_selection_id": None,
            "state_update": {"volume_number": 1, "publication_id": publication_id},
            "targets": [{"artifact_id": publication_id, "artifact_kind": "volume_publication", "staging_path": f"runtime/staging/volume-publication-{publication_id}", "final_path": f"publications/{publication_id}", "sha256": digest, "status": "pending"}],
        }
        RunStateStore(root).save(initial)
        recovered = execute_publication_recovery(root, initial)
        self.assertEqual(recovered["published_volumes"], [{"volume_number": 1, "publication_id": publication_id}])
        self.assertEqual(recovered["current_target"], {"volume_number": 2})
        self.assertTrue(final.is_dir())
