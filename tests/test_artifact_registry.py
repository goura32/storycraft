"""V2 成果物 registry の ID・保存先・selection slot 契約。"""
from __future__ import annotations

import unittest

from storycraft.artifact_registry import (
    ARTIFACT_SPECS,
    artifact_directory,
    canonical_slot,
    validate_artifact_reference,
)
from storycraft.series_contracts import ContractError


class ArtifactRegistryV2Tests(unittest.TestCase):
    def test_each_v2_artifact_kind_has_its_canonical_id_directory_and_slot(self) -> None:
        cases = (
            ("request", "request-000001", "inputs/request-000001", "request"),
            ("keywords", "keywords-000001", "inputs/keywords-000001", "keywords"),
            ("settings", "settings-000001", "runtime/settings/settings-000001", "settings"),
            ("initial-design", "initial-design-000001", "design/initial/initial-design-000001", "initial_design"),
            ("series-plan", "series-plan-000001", "design/series-plans/series-plan-000001", "series_plan"),
            ("volume-plan", "volume-plan-v01-000001", "design/volume-plans/volume-plan-v01-000001", "volume_plan.v01"),
            ("chapter-plan", "chapter-plan-v01-c02-000001", "design/chapter-plans/chapter-plan-v01-c02-000001", "chapter_plan.v01.c02"),
            ("scene-plan", "scene-plan-v01-c02-s03-000001", "design/scene-plans/scene-plan-v01-c02-s03-000001", "scene_plan.v01.c02.s03"),
            ("scene-card", "scene-card-v01-c02-s03-000001", "design/scene-cards/scene-card-v01-c02-s03-000001", "scene_card.v01.c02.s03"),
            ("scene-prose", "scene-prose-v01-c02-s03-000001", "scenes/scene-prose-v01-c02-s03-000001", "scene_prose.v01.c02.s03"),
            ("continuity-update", "continuity-v01-c02-s03-000001", "scenes/continuity-v01-c02-s03-000001", "continuity_update.v01.c02.s03"),
            ("generation", "gen-000001", "generations/gen-000001", "current_state"),
            ("scene", "scene-v01-c02-s03-000001", "scenes/scene-v01-c02-s03-000001", "scene.v01.c02.s03"),
            ("scene-commit", "scene-commit-v01-c02-s03-000001", "scenes/scene-commit-v01-c02-s03-000001", "scene_commit.v01.c02.s03"),
            ("selection", "selection-000001", "runtime/selections/selection-000001", None),
            ("adoption", "adoption-000001", "runtime/adoptions/adoption-000001", None),
            ("volume-publication", "volume-pub-v01-000001", "publications/volume-pub-v01-000001", "volume_publication.v01"),
        )

        self.assertEqual(set(ARTIFACT_SPECS), {kind for kind, *_ in cases} | {"quality-disposition"})
        for kind, artifact_id, directory, slot in cases:
            with self.subTest(kind=kind):
                if slot is not None:
                    validate_artifact_reference(kind, artifact_id, slot)
                self.assertEqual(artifact_directory(kind, artifact_id).as_posix(), directory)
                if slot is None:
                    with self.assertRaises(ContractError):
                        canonical_slot(kind, artifact_id)
                else:
                    self.assertEqual(canonical_slot(kind, artifact_id), slot)

    def test_scene_and_scene_commit_use_distinct_ids_and_final_directories(self) -> None:
        scene_id = "scene-v01-c01-s01-000001"
        commit_id = "scene-commit-v01-c01-s01-000001"
        self.assertNotEqual(scene_id, commit_id)
        self.assertNotEqual(
            artifact_directory("scene", scene_id),
            artifact_directory("scene-commit", commit_id),
        )

    def test_rejects_unknown_kind_mismatched_coordinates_and_invalid_slot(self) -> None:
        cases = (
            ("unknown", "request-000001", "request"),
            ("request", "request-000001", "series_plan"),
            ("chapter-plan", "chapter-plan-v01-c02-000001", "chapter_plan.v01.c03"),
            ("scene-card", "scene-card-v01-c02-s03-000001", "scene_card.v01.c02"),
            ("scene-plan", "scene-plan-v1-c02-s03-000001", "scene_plan.v01.c02.s03"),
            ("volume-plan", "volume-plan-v01-00001", "volume_plan.v01"),
            ("generation", "gen-000001", "generation.v01"),
        )
        for kind, artifact_id, slot in cases:
            with self.subTest(kind=kind, artifact_id=artifact_id, slot=slot):
                with self.assertRaises(ContractError):
                    validate_artifact_reference(kind, artifact_id, slot)


if __name__ == "__main__":
    unittest.main()
