"""V1品質pass上限のworkspace設定契約。"""
from __future__ import annotations

import unittest

from storycraft.input_stage import _revision_limit
from storycraft.reviewed_candidate_stage import (
    revision_limit_from_config,
)
from storycraft.series_contracts import ContractError


class RevisionLimitConfigV1Tests(unittest.TestCase):
    def test_quality_limit_is_used_by_all_candidate_runners(
        self,
    ) -> None:
        config = {
            "retry": {
                "max_attempts": 4,
            },
            "quality": {
                "max_critique_passes": 2,
            },
        }

        self.assertEqual(
            revision_limit_from_config(config),
            2,
        )
        self.assertEqual(
            _revision_limit(config),
            2,
        )

    def test_legacy_retry_revision_is_not_used(
        self,
    ) -> None:
        config = {
            "retry": {
                "max_attempts": 4,
                "revision": 9,
            },
            "quality": {
                "max_critique_passes": 2,
            },
        }

        self.assertEqual(
            revision_limit_from_config(config),
            2,
        )
        self.assertEqual(
            _revision_limit(config),
            2,
        )

    def test_missing_quality_defaults_to_one(
        self,
    ) -> None:
        self.assertEqual(
            revision_limit_from_config({}),
            1,
        )
        self.assertEqual(
            _revision_limit({}),
            1,
        )

    def test_invalid_quality_limit_is_rejected(
        self,
    ) -> None:
        config = {
            "quality": {
                "max_critique_passes": 0,
            },
        }

        for loader in (
            revision_limit_from_config,
            _revision_limit,
        ):
            with self.subTest(loader=loader.__name__):
                with self.assertRaisesRegex(
                    ContractError,
                    "1以上の整数",
                ):
                    loader(config)


if __name__ == "__main__":
    unittest.main()
