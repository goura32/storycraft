from __future__ import annotations

import unittest

from storycraft.review_contracts import (
    field_tokens,
    validate_critique_fields,
    validate_revision_scope,
)
from storycraft.series_contracts import ContractError


class ReviewContractsTest(unittest.TestCase):
    def test_field_tokens_supports_index_and_quoted_key(
        self,
    ) -> None:
        self.assertEqual(
            field_tokens(
                'threads[0].character_knowledge["char-0004"]'
            ),
            (
                "threads",
                0,
                "character_knowledge",
                "char-0004",
            ),
        )

    def test_field_tokens_decodes_json_escape(
        self,
    ) -> None:
        self.assertEqual(
            field_tokens('items["escaped\\\"key"]'),
            ("items", 'escaped"key'),
        )

    def test_invalid_field_path_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ContractError,
            "field パスが不正",
        ):
            field_tokens("items[invalid]")

    def test_critique_field_must_exist(
        self,
    ) -> None:
        candidate = {
            "world": [
                {
                    "stable_fact": "書店",
                }
            ]
        }
        critique = {
            "issues": [
                {
                    "field": "brief.premise",
                }
            ]
        }

        with self.assertRaisesRegex(
            ContractError,
            "候補を指しません",
        ):
            validate_critique_fields(
                critique,
                candidate,
            )

    def test_revision_may_change_cited_field(
        self,
    ) -> None:
        candidate = {
            "characters": [
                {
                    "emotion": "緊張",
                    "goal": "帰宅",
                }
            ]
        }
        revised = {
            "characters": [
                {
                    "emotion": "平静",
                    "goal": "帰宅",
                }
            ]
        }
        critique = {
            "issues": [
                {
                    "field": "characters[0].emotion",
                }
            ]
        }

        validate_revision_scope(
            candidate,
            revised,
            critique,
        )

    def test_revision_rejects_uncited_change(
        self,
    ) -> None:
        candidate = {
            "characters": [
                {
                    "emotion": "緊張",
                    "goal": "帰宅",
                }
            ]
        }
        revised = {
            "characters": [
                {
                    "emotion": "平静",
                    "goal": "手紙を探す",
                }
            ]
        }
        critique = {
            "issues": [
                {
                    "field": "characters[0].emotion",
                }
            ]
        }

        with self.assertRaisesRegex(
            ContractError,
            "引用されていないfield",
        ):
            validate_revision_scope(
                candidate,
                revised,
                critique,
            )


if __name__ == "__main__":
    unittest.main()
