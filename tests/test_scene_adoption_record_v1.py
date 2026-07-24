"""Scene Commit用immutable Scene採用記録の試験。"""
from __future__ import annotations

from copy import deepcopy
import tempfile
import unittest

from storycraft.scene_adoption_record import (
    load_scene_adoption_record,
    publish_scene_adoption_record,
    restore_scene_staging_from_adoption_record,
    scene_adoption_record_path,
)
from storycraft.scene_continuity_stage import (
    SceneContinuityStageService,
)
from storycraft.series_contracts import ContractError

from tests.test_initial_world_stage_v1 import (
    load_json_from,
)
from tests.test_scene_continuity_stage_v1 import (
    AcceptingContinuityModel,
    CONTINUITY_AT,
    create_scene_continuity_workspace,
    matching_continuity,
)


SCENE_ID = "scene-v01-c001-s001"


def create_record_workspace(temporary: str):
    workspace = create_scene_continuity_workspace(
        temporary
    )
    SceneContinuityStageService(workspace).run(
        AcceptingContinuityModel(matching_continuity()),
        updated_at=CONTINUITY_AT,
    )
    return workspace


class SceneAdoptionRecordV1Test(unittest.TestCase):
    def test_continuity_adoption_publishes_record(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_record_workspace(temporary)

            record = load_scene_adoption_record(
                workspace,
                SCENE_ID,
            )
            staging = (
                workspace
                / "runtime/staging"
                / f"scene-{SCENE_ID}"
            )

            self.assertEqual(
                record.scene_card,
                load_json_from(
                    staging / "scene-card.json"
                ),
            )
            self.assertEqual(
                record.prose,
                (staging / "prose.md").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertEqual(
                record.continuity,
                load_json_from(
                    staging / "continuity.json"
                ),
            )

            path = scene_adoption_record_path(
                workspace,
                SCENE_ID,
            )
            self.assertEqual(
                {
                    entry.name
                    for entry in path.iterdir()
                },
                {
                    "scene-card.json",
                    "prose.md",
                    "continuity.json",
                },
            )

    def test_record_survives_scene_staging_loss(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_record_workspace(temporary)
            expected = load_scene_adoption_record(
                workspace,
                SCENE_ID,
            )

            staging = (
                workspace
                / "runtime/staging"
                / f"scene-{SCENE_ID}"
            )
            for entry in staging.iterdir():
                entry.unlink()
            staging.rmdir()

            self.assertEqual(
                load_scene_adoption_record(
                    workspace,
                    SCENE_ID,
                ),
                expected,
            )

    def test_record_restores_missing_scene_staging(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_record_workspace(temporary)
            expected = load_scene_adoption_record(
                workspace,
                SCENE_ID,
            )
            staging = (
                workspace
                / "runtime/staging"
                / f"scene-{SCENE_ID}"
            )

            for entry in staging.iterdir():
                entry.unlink()
            staging.rmdir()

            restored = (
                restore_scene_staging_from_adoption_record(
                    workspace,
                    SCENE_ID,
                )
            )

            self.assertEqual(restored, staging)
            self.assertEqual(
                load_json_from(
                    restored / "scene-card.json"
                ),
                expected.scene_card,
            )
            self.assertEqual(
                (
                    restored / "prose.md"
                ).read_text(encoding="utf-8"),
                expected.prose,
            )
            self.assertEqual(
                load_json_from(
                    restored / "continuity.json"
                ),
                expected.continuity,
            )

    def test_identical_record_publish_is_idempotent(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_record_workspace(temporary)
            record = load_scene_adoption_record(
                workspace,
                SCENE_ID,
            )
            expected_path = scene_adoption_record_path(
                workspace,
                SCENE_ID,
            )

            actual_path = publish_scene_adoption_record(
                workspace,
                scene_id=SCENE_ID,
                scene_card=record.scene_card,
                prose=record.prose,
                continuity=record.continuity,
            )

            self.assertEqual(actual_path, expected_path)
            self.assertEqual(
                load_scene_adoption_record(
                    workspace,
                    SCENE_ID,
                ),
                record,
            )

    def test_conflicting_record_is_not_overwritten(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_record_workspace(temporary)
            record = load_scene_adoption_record(
                workspace,
                SCENE_ID,
            )
            conflicting = deepcopy(record.continuity)
            conflicting["summary"] = "競合する採用記録。"

            with self.assertRaisesRegex(
                ContractError,
                "競合",
            ):
                publish_scene_adoption_record(
                    workspace,
                    scene_id=SCENE_ID,
                    scene_card=record.scene_card,
                    prose=record.prose,
                    continuity=conflicting,
                )

            self.assertEqual(
                load_scene_adoption_record(
                    workspace,
                    SCENE_ID,
                ),
                record,
            )


if __name__ == "__main__":
    unittest.main()
