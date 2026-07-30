"""巻公開の reader-facing 成果物契約。"""
from __future__ import annotations

import unittest

from storycraft.publication_builder import build_volume_publication_files
from storycraft.series_contracts import ContractError


class VolumePublicationV2Tests(unittest.TestCase):
    def test_builds_only_record_and_manuscript_for_one_volume(self) -> None:
        files = build_volume_publication_files(
            publication_id="volume-pub-v01-000001",
            volume_number=1,
            input_selection_id="selection-000010",
            settings_id="settings-000001",
            series_plan_id="series-plan-000001",
            volume_plan_id="volume-plan-v01-000001",
            current_state_id="gen-000010",
            chapter_plan_ids=["chapter-plan-v01c01-000001"],
            scene_ids=["scene-v01c01s01-000001"],
            quality_disposition_refs=["quality-000001"],
            scenes=[{"scene_id": "scene-v01c01s01-000001", "prose": "本文です。"}],
            created_at="2026-07-28T00:00:00Z",
        )
        self.assertEqual(set(files), {"record.json", "manuscript.md"})
        record = files["record.json"]
        self.assertEqual(record["volume_publication_id"], "volume-pub-v01-000001")
        self.assertNotIn("publication_notice_type", record)
        self.assertEqual(files["manuscript.md"], "本文です。\n")
        from storycraft.publication_builder import validate_volume_publication_files
        validate_volume_publication_files(files)

    def test_adds_editing_notice_only_when_major_issues_remain(self) -> None:
        files = build_volume_publication_files(
            publication_id="volume-pub-v01-000001",
            volume_number=1,
            input_selection_id="selection-000010",
            settings_id="settings-000001",
            series_plan_id="series-plan-000001",
            volume_plan_id="volume-plan-v01-000001",
            current_state_id="gen-000010",
            chapter_plan_ids=["chapter-plan-v01c01-000001"],
            scene_ids=["scene-v01c01s01-000001"],
            quality_disposition_refs=["quality-000001"],
            scenes=[{"scene_id": "scene-v01c01s01-000001", "prose": "本文です。"}],
            remaining_major_issues=True,
            created_at="2026-07-28T00:00:00Z",
        )
        self.assertEqual(files["record.json"]["publication_notice_type"], "編集")
        self.assertEqual(files["manuscript.md"], "編集上の注意があります。\n\n本文です。\n")

    def test_rejects_mismatched_scene_and_quality_references(self) -> None:
        with self.assertRaisesRegex(ContractError, "quality_disposition_refs"):
            build_volume_publication_files(
                publication_id="volume-pub-v01-000001",
                volume_number=1,
                input_selection_id="selection-000010",
                settings_id="settings-000001",
                series_plan_id="series-plan-000001",
                volume_plan_id="volume-plan-v01-000001",
                current_state_id="gen-000010",
                chapter_plan_ids=["chapter-plan-v01c01-000001"],
                scene_ids=["scene-v01c01s01-000001"],
                quality_disposition_refs=[],
                scenes=[{"scene_id": "scene-v01c01s01-000001", "prose": "本文です。"}],
                created_at="2026-07-28T00:00:00Z",
            )
