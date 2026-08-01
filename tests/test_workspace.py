"""v2 新規 workspace 初期化の最小不変契約。"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from storycraft.run_state import RunStateStore
from storycraft.selection_snapshot import SelectionSnapshotStore
from storycraft.publication_builder import build_volume_publication_files
from storycraft.workspace import create_workspace, validate_workspace


class WorkspaceV2Tests(unittest.TestCase):
    def _write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")

    def _create_workspace(self, root: Path) -> None:
        create_workspace(
            root,
            workspace_id="ws-test",
            request={"title": "題名", "genre": "幻想", "premise": "前提", "required_elements": [], "forbidden_elements": [], "ending_preference": "希望", "volume_count": 4, "language": "ja"},
            settings={"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1000, 1000]},
            created_at="2026-07-28T00:00:00Z",
        )

    def test_creates_fresh_v2_workspace_with_request_settings_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            create_workspace(
                root,
                workspace_id="ws-test",
                request={"title": "題名", "genre": "幻想", "premise": "前提", "required_elements": [], "forbidden_elements": [], "ending_preference": "希望", "volume_count": 4, "language": "ja"},
                settings={"provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "test", "technical_retry_limit": 1, "quality_revision_limit": 0, "invalid_response_limit": 1, "chapter_per_volume_range": [1, 1], "chapter_scene_range": [1, 1], "scene_text_char_range": [1000, 1000]},
                created_at="2026-07-28T00:00:00Z",
            )
            state = RunStateStore(root).load()
            self.assertEqual(state["schema_version"], 3)
            self.assertEqual(state["current_stage"], "initial_design")
            self.assertNotIn("active_candidate", state)
            self.assertNotIn("active_scene_id", state)
            for relative in ("candidates", "reviews", "runtime", "runtime/adoptions", "design/scene-cards"):
                self.assertTrue((root / relative).is_dir(), relative)
            snapshot = SelectionSnapshotStore(root).load(state["current_selection_id"])
            self.assertEqual(set(snapshot["slots"]), {"request", "settings"})
            validate_workspace(root)

    def test_refuses_existing_workspace_without_mutating_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            root.mkdir()
            marker = root / "marker"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "既に存在"):
                create_workspace(root, workspace_id="ws-test", request={}, settings={}, created_at="2026-07-28T00:00:00Z")
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_validation_traverses_unselected_candidate_audit_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            self._create_workspace(root)
            candidate = {
                "schema_version": 1, "candidate_id": "candidate-000001", "artifact_kind": "initial-design",
                "input_selection_id": "selection-000001", "keywords_id": None, "settings_id": "settings-000001",
                "payload": {}, "parent_candidate_id": None, "review_record_id": None,
                "call_id": "call-000001", "created_at": "2026-07-28T00:00:00Z",
            }
            path = root / "candidates/candidate-000001/record.json"
            path.parent.mkdir()
            path.write_text(json.dumps(candidate), encoding="utf-8")
            with self.assertRaises(Exception):
                validate_workspace(root)

    def test_validation_rejects_corrupt_ancestor_selection_even_when_current_slots_resolve(self) -> None:
        """The parent selection chain is immutable evidence, not optional metadata."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            self._create_workspace(root)
            initial = RunStateStore(root).load()
            current = SelectionSnapshotStore(root).create(
                input_selection_id=initial["current_selection_id"],
                slots={"request": "request-000001", "settings": "settings-000001"},
                created_at="2026-07-28T00:00:00Z",
            )
            initial["current_selection_id"] = current["selection_id"]
            RunStateStore(root).save(initial)
            historic_path = root / "runtime/selections/selection-000001/record.json"
            historic = json.loads(historic_path.read_text(encoding="utf-8"))
            historic["input_selection_id"] = "selection-000099"
            historic_path.write_text(json.dumps(historic), encoding="utf-8")

            with self.assertRaisesRegex(Exception, "ancestor.*selection"):
                validate_workspace(root)

    def test_rejects_quality_reviews_from_a_different_candidate_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            self._create_workspace(root)
            now = "2026-07-28T00:00:00Z"

            def write_record(relative: str, identifier: str, record: dict) -> None:
                path = root / relative / identifier / "record.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(record), encoding="utf-8")

            def call(call_id: str, operation: str, target: str | None) -> None:
                write_record("runtime/calls", call_id, {
                    "schema_version": 1, "call_id": call_id, "operation": operation,
                    "role": "provider", "target_candidate_id": target, "input_refs": ["selection-000001"] + ([target] if target else []),
                    "technical_attempt": 1, "format_attempt": 1, "seed": 1,
                    "endpoint": "http://127.0.0.1:11434/v1", "model": "test",
                    "settings_id": "settings-000001", "request": "{}", "response": "{}",
                    "transport": "success",
                    "validation": {"result": "valid", "checks": [], "failure_code": None},
                })

            for number in (1, 2):
                candidate_id, call_id = f"candidate-{number:06d}", f"call-{number:06d}"
                call(call_id, "generate", None)
                write_record("candidates", candidate_id, {
                    "schema_version": 1, "candidate_id": candidate_id, "artifact_kind": "initial-design",
                    "input_selection_id": "selection-000001", "keywords_id": None,
                    "settings_id": "settings-000001", "payload": {}, "parent_candidate_id": None,
                    "review_record_id": None, "call_id": call_id, "created_at": now,
                })
            call("call-000003", "review", "candidate-000002")
            write_record("reviews", "review-000001", {
                "schema_version": 1, "review_id": "review-000001", "candidate_id": "candidate-000002",
                "response": {"schema_version": "review-response-v1", "decision": "pass", "issues": []},
                "call_id": "call-000003", "created_at": now,
            })
            write_record("quality", "quality-000001", {
                "schema_version": 1, "quality_id": "quality-000001", "candidate_id": "candidate-000001",
                "review_record_ids": ["review-000001"], "revision_count": 0, "result": "accepted",
                "remaining_major_issues": [], "created_at": now,
            })

            with self.assertRaisesRegex(Exception, "quality.*review.*candidate"):
                validate_workspace(root)

    def test_validation_rejects_a_symlinked_artifact_record_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            self._create_workspace(root)
            external = Path(temporary) / "external-scene-cards"
            external.mkdir()
            (root / "design/scene-cards").rmdir()
            (root / "design/scene-cards").symlink_to(external, target_is_directory=True)

            with self.assertRaisesRegex(Exception, "artifact record"):
                validate_workspace(root)

    def test_completed_workspace_requires_exact_published_records_and_manuscripts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "novel"
            self._create_workspace(root)
            initial = RunStateStore(root).load()
            series_id, completed_selection = "series-plan-000001", "selection-000002"

            # Valid initial-design content per closed schema
            initial_design_content = {
                "core": "英雄の旅",
                "cast": [{"name": "主人公", "role": "英雄"}],
                "world": "剣と魔法の世界",
                "knowledge_model": {},
                "unresolved_threads": [],
                "ending_conditions": ["塔を登頂する"]
            }

            # Valid series-plan content per closed schema
            series_plan_content = {
                "volume_count": 4, "series_objectives": ["完結"],
                "volume_summaries": [{"volume_number": n, "purpose": f"巻{n}", "ending_change": "変化"} for n in range(1, 5)],
                "character_arc_map": {"char-main": [1]}, "relationship_arc_map": {"rel-main": [1]}, "thread_progression": {"thread-main": [1]},
                "revelation_schedule": [{"volume_number": 1, "knowledge_id": "know-main"}], "ending_path": "完結", "global_constraints": []
            }

            volume_plan_content = {
                "title": "第一巻", "starting_state_summary": "開始", "volume_purpose": "目的", "central_conflict": "対立",
                "character_changes": {"char-main": "変化"}, "relationship_changes": {"rel-main": "変化"}, "thread_goals": {"thread-main": "進展"}, "revelations": [],
                "chapter_summaries": [{"chapter_number": 1, "purpose": "章1"}], "required_end_state": "次へ", "handoff_expectations": []
            }

            chapter_plan_content = {
                "title": "第一章", "chapter_purpose": "目的", "starting_conditions": ["開始"], "ending_changes": ["変化"],
                "scene_summaries": [{"scene_number": 1, "purpose": "場面1"}], "required_revelations": [], "constraints": []
            }

            # Valid scene-card content per closed schema
            scene_card_content = {
        "pov_character_id": "char-main", "participant_ids": ["char-main"], "location_id": "loc-main", "story_time": "夜", "purpose": "展開", "opening_state": "開始",
                "required_beats": [{"beat_id": "beat-01", "description": "展開", "required": True, "order_hint": 1}], "conflict": "対立", "allowed_revelations": [], "required_revelations": [], "forbidden_revelations": [], "allowed_updates": [], "ending_state_targets": ["変化"], "style_constraints": ["簡潔"]
            }
            self._write_json(root / "design/scene-cards/scene-card-v01-c01-s01-000001/record.json", {
                "schema_version": 1, "artifact_id": "scene-card-v01-c01-s01-000001", "artifact_kind": "scene-card",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": scene_card_content,
            })

            # Write series-plan record
            self._write_json(root / "design/series-plans/series-plan-000001/record.json", {
                "schema_version": 1, "artifact_id": "series-plan-000001", "artifact_kind": "series-plan",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": series_plan_content,
            })

            # Write volume-plan record
            self._write_json(root / "design/volume-plans/volume-plan-v01-000001/record.json", {
                "schema_version": 1, "artifact_id": "volume-plan-v01-000001", "artifact_kind": "volume-plan",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": volume_plan_content,
            })

            # Write chapter-plan record
            self._write_json(root / "design/chapter-plans/chapter-plan-v01-c01-000001/record.json", {
                "schema_version": 1, "artifact_id": "chapter-plan-v01-c01-000001", "artifact_kind": "chapter-plan",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": chapter_plan_content,
            })

            # Valid continuity-update content per closed schema
            continuity_update_content = {
                "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
                "changes": []
            }
            self._write_json(root / "scenes/continuity-v01-c01-s01-000001/record.json", {
                "schema_version": 1, "artifact_id": "continuity-v01-c01-s01-000001", "artifact_kind": "continuity-update",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": continuity_update_content,
            })

            # Valid scene-prose content per closed schema
            scene_prose_content = {
                "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
                "text": "本文"
            }
            self._write_json(root / "scenes/scene-prose-v01-c01-s01-000001/record.json", {
                "schema_version": 1, "artifact_id": "scene-prose-v01-c01-s01-000001", "artifact_kind": "scene-prose",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": scene_prose_content,
            })

            # Valid scene artifact content per closed schema
            scene_content = {
                "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
                "scene_prose_id": "scene-prose-v01-c01-s01-000001",
                "scene_card_id": "scene-card-v01-c01-s01-000001",
                "continuity_update_id": "continuity-v01-c01-s01-000001",
                "current_state_id": "gen-000001",
                "quality_disposition_id": "quality-000001",
            }
            self._write_json(root / "scenes/scene-v01-c01-s01-000001/record.json", {
                "schema_version": 1, "artifact_id": "scene-v01-c01-s01-000001", "artifact_kind": "scene",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": scene_content,
            })

            # Valid generation content per closed schema
            generation_content = {
                "story_facts": [],
                "character_knowledge": {},
                "reader_disclosures": "",
                "unresolved_thread_states": {},
                "timeline_position": 0
            }
            self._write_json(root / "generations/gen-000001/record.json", {
                "schema_version": 1, "artifact_id": "gen-000001", "artifact_kind": "generation",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": generation_content,
            })

            # Valid scene-commit content per closed schema
            scene_commit_content = {
                "schema_version": 1,
                "scene_commit_id": "scene-commit-v01-c01-s01-000001",
                "scene_id": "scene-v01-c01-s01-000001",  # points to the scene artifact
                "scene_card_id": "scene-card-v01-c01-s01-000001",
                "scene_prose_id": "scene-prose-v01-c01-s01-000001",
                "continuity_update_id": "continuity-v01-c01-s01-000001",
                "current_state_id": "gen-000001",
                "quality_disposition_id": "quality-000001",
                "volume_number": 1,
                "chapter_number": 1,
                "scene_number": 1,
                "created_at": "2026-07-28T00:00:00Z",
            }
            self._write_json(root / "scenes/scene-commit-v01-c01-s01-000001/record.json", scene_commit_content)

            # Write quality disposition record
            self._write_json(root / "quality/quality-000001/record.json", {
                "schema_version": 1, "quality_id": "quality-000001", "candidate_id": "candidate-000001",
                "review_record_ids": ["review-000001"], "revision_count": 0, "result": "accepted",
                "remaining_major_issues": [], "created_at": "2026-07-28T00:00:00Z",
            })

            # Write review record
            self._write_json(root / "reviews/review-000001/record.json", {
                "schema_version": 1, "review_id": "review-000001", "candidate_id": "candidate-000001",
                "response": {"schema_version": "review-response-v1", "decision": "pass", "issues": []},
                "call_id": "call-000002", "created_at": "2026-07-28T00:00:00Z",
            })

            # Write candidate record
            self._write_json(root / "candidates/candidate-000001/record.json", {
                "schema_version": 1, "candidate_id": "candidate-000001", "artifact_kind": "scene-prose",
                "input_selection_id": initial["current_selection_id"], "keywords_id": None, "settings_id": "settings-000001",
                "payload": scene_prose_content, "parent_candidate_id": None, "review_record_id": None,
                "call_id": "call-000001", "created_at": "2026-07-28T00:00:00Z",
            })

            # Write call record
            self._write_json(root / "runtime/calls/call-000001/record.json", {
                "schema_version": 1, "call_id": "call-000001", "operation": "generate",
                "role": "scene_prose", "target_candidate_id": None, "input_refs": ["selection-000001"],
                "technical_attempt": 1, "format_attempt": 1, "seed": 1,
                "endpoint": "injected", "model": "test", "settings_id": "settings-000001",
                "request": "{}", "response": "{}", "transport": "success",
                "validation": {"result": "valid", "checks": [], "failure_code": None},
            })
            self._write_json(root / "runtime/calls/call-000002/record.json", {
                "schema_version": 1, "call_id": "call-000002", "operation": "review",
                "role": "scene_prose", "target_candidate_id": "candidate-000001", "input_refs": ["selection-000001", "candidate-000001"],
                "technical_attempt": 1, "format_attempt": 1, "seed": 1,
                "endpoint": "injected", "model": "test", "settings_id": "settings-000001",
                "request": "{}", "response": "{}", "transport": "success",
                "validation": {"result": "valid", "checks": [], "failure_code": None},
            })

            # Write series-plan record
            self._write_json(root / "design/series-plans/series-plan-000001/record.json", {
                "schema_version": 1, "artifact_id": "series-plan-000001", "artifact_kind": "series-plan",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": series_plan_content,
            })

            # Write volume-plan record
            self._write_json(root / "design/volume-plans/volume-plan-v01-000001/record.json", {
                "schema_version": 1, "artifact_id": "volume-plan-v01-000001", "artifact_kind": "volume-plan",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": volume_plan_content,
            })

            # Write chapter-plan record
            self._write_json(root / "design/chapter-plans/chapter-plan-v01-c01-000001/record.json", {
                "schema_version": 1, "artifact_id": "chapter-plan-v01-c01-000001", "artifact_kind": "chapter-plan",
                "input_selection_id": initial["current_selection_id"], "created_at": "2026-07-28T00:00:00Z",
                "content": chapter_plan_content,
            })


            # Create completed selection snapshot
            slots = SelectionSnapshotStore(root).load(initial["current_selection_id"])["slots"]
            completed_snapshot = {
                "schema_version": 1, "selection_id": completed_selection,
                "input_selection_id": initial["current_selection_id"],
                "slots": {**slots, "series_plan": series_id, "volume_plan.v01": "volume-plan-v01-000001",
                          "chapter_plan.v01.c01": "chapter-plan-v01-c01-000001",
                          "scene.v01.c01.s01": "scene-v01-c01-s01-000001",
                          "scene_prose.v01.c01.s01": "scene-prose-v01-c01-s01-000001",
                          "scene_card.v01.c01.s01": "scene-card-v01-c01-s01-000001",
                          "continuity_update.v01.c01.s01": "continuity-v01-c01-s01-000001",
                          "scene_prose_disposition.v01.c01.s01": "quality-000001", "current_state": "gen-000001"},
                "created_at": "2026-07-28T00:00:00Z"
            }
            selection_path = root / "runtime/selections" / completed_selection / "record.json"
            selection_path.parent.mkdir()
            selection_path.write_text(json.dumps(completed_snapshot), encoding="utf-8")
            publication_id = "volume-pub-v01-000001"
            files = build_volume_publication_files(
                publication_id=publication_id,
                volume_number=1,
                input_selection_id=completed_selection,
                settings_id="settings-000001",
                series_plan_id=series_id,
                volume_plan_id="volume-plan-v01-000001",
                current_state_id="gen-000001",
                chapter_plan_ids=["chapter-plan-v01-c01-000001"],
                scene_ids=["scene-v01-c01-s01-000001"],
                quality_disposition_refs=["quality-000001"],
                scenes=[{"scene_id": "scene-v01-c01-s01-000001", "prose": "本文"}],
                created_at="2026-07-28T00:00:00Z"
            )
            publication = root / "publications" / publication_id
            publication.mkdir()
            for name, value in files.items():
                (publication / name).write_text(
                    value if isinstance(value, str) else json.dumps(value),
                    encoding="utf-8"
                )
            initial.update(
                status="completed",
                current_stage=None,
                current_target=None,
                pending_commit=None,
                current_selection_id=completed_selection,
                published_volumes=[{"volume_number": 1, "publication_id": publication_id}]
            )
            RunStateStore(root).save(initial)
            with self.assertRaisesRegex(Exception, "completedのpublished_volumes"):
                validate_workspace(root)
    def test_running_workspace_validates_each_declared_published_volume(self) -> None:
        """Published volumes remain immutable evidence while later volumes are active."""
        from tests.test_volume_publication_service import workspace
        from storycraft.volume_publication_stage import VolumePublicationStageService

        temporary, root = workspace(volume_count=2)
        self.addCleanup(temporary.cleanup)
        state = VolumePublicationStageService(root).run(updated_at="2026-07-31T00:00:00Z")
        self.assertEqual(state["status"], "running")
        extraneous = root / "publications/volume-pub-v99-000001"
        extraneous.mkdir()
        with self.assertRaisesRegex(Exception, "published_volumes"):
            validate_workspace(root)
        extraneous.rmdir()
        publication = root / "publications/volume-pub-v01-000001/manuscript.md"
        publication.write_text("改竄された原稿\n", encoding="utf-8")

        with self.assertRaisesRegex(Exception, "巻公開"):
            validate_workspace(root)