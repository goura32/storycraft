"""V1 Stage errorの永続化安全性試験。"""
from __future__ import annotations

import tempfile
import unittest

from storycraft.input_stage import InputStageService
from storycraft.scene_prose_stage import (
    SceneProseStageService,
)
from storycraft.series_plan_stage import (
    SeriesPlanStageService,
)

from tests.test_input_adoption_recovery_v1 import (
    UPDATED_AT,
    create_keywords_workspace,
)
from tests.test_scene_prose_stage_v1 import (
    PROSE_AT,
    create_scene_prose_workspace,
)
from tests.test_series_plan_stage_v1 import (
    PLAN_AT,
    create_series_plan_workspace,
)


_SECRET = (
    "Authorization: Bearer "
    "persistent-secret\nFORGED"
)


class ExplodingJsonModel:
    def generate(
        self,
        _stage: str,
        _context: dict,
    ) -> dict:
        raise RuntimeError(_SECRET)


class ExplodingProseModel:
    def generate_prose(
        self,
        _stage: str,
        _context: dict,
    ) -> str:
        raise RuntimeError(_SECRET)


def assert_safe_error(
    test: unittest.TestCase,
    state: dict,
) -> None:
    message = state["last_error"]["message"]

    test.assertIn("[REDACTED]", message)
    test.assertNotIn(
        "persistent-secret",
        message,
    )
    test.assertNotIn("FORGED", message)


class ErrorPersistenceV1Tests(unittest.TestCase):
    def test_json_candidate_error_is_safe(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_series_plan_workspace(
                temporary
            )

            state = SeriesPlanStageService(
                workspace
            ).run(
                ExplodingJsonModel(),
                updated_at=PLAN_AT,
            )

            assert_safe_error(self, state)

    def test_keywords_input_error_is_safe(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace, _candidate = (
                create_keywords_workspace(
                    temporary
                )
            )

            state = InputStageService(
                workspace
            ).run(
                ExplodingJsonModel(),
                updated_at=UPDATED_AT,
            )

            assert_safe_error(self, state)

    def test_prose_error_is_safe(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = create_scene_prose_workspace(
                temporary
            )

            state = SceneProseStageService(
                workspace
            ).run(
                ExplodingProseModel(),
                updated_at=PROSE_AT,
            )

            assert_safe_error(self, state)


if __name__ == "__main__":
    unittest.main()
