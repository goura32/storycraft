from __future__ import annotations

import unittest

from storycraft.review_contracts import (
    evidence_location_kind,
    field_tokens,
    validate_critique_fields,
    validate_revision_scope,
)
from storycraft.series_contracts import ContractError


class ReviewContractsTest(unittest.TestCase):
    def test_evidence_location_is_closed_to_canonical_forms(self) -> None:
        self.assertEqual(evidence_location_kind("$.text"), "json")
        self.assertEqual(evidence_location_kind("prose:0"), "prose")
        self.assertEqual(evidence_location_kind("paragraph:0"), "paragraph")
        for location in ("text", "offset:0", "$.", "$.text.", "prose:-1", "paragraph:x"):
            with self.subTest(location=location):
                with self.assertRaises(ContractError):
                    evidence_location_kind(location)

    def test_critique_rejects_bare_evidence_field(self) -> None:
        with self.assertRaises(ContractError):
            validate_critique_fields(
                {"issues": [{"evidence_locations": ["text"]}]},
                {"text": "本文"},
            )

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
        # JSON string: items["escaped\"key"] -> in Python source: 'items["escaped\\"key"]'
        # The parser should decode the escaped quote
        self.assertEqual(
            field_tokens(r'items["escaped\"key"]'),
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
                    "evidence_locations": ["$.brief.premise"],
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
                    "evidence_locations": ["$.characters[0].emotion"],
                }
            ]
        }

        validate_revision_scope(
            candidate,
            revised,
            critique,
        )

    def test_revision_allows_uncited_changes_per_v1_spec(
        self,
    ) -> None:
        """V1 spec: revisions can replace entire artifact, not restricted to cited fields.
        指摘は優先して直すべき問題を示しますが、修正可能範囲を制限しません。
        全体の整合性または品質改善のため、指摘対象外も変更できます。"""
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
                    "goal": "手紙を探す",  # 未指摘のフィールドも変更可
                }
            ]
        }
        critique = {
            "issues": [
                {
                    "evidence_locations": ["$.characters[0].emotion"],
                }
            ]
        }

        # V1 では uncited change も許可される（形式・必須項目・識別子・参照・更新可能範囲の契約は別途検証）
        validate_revision_scope(
            candidate,
            revised,
            critique,
        )


if __name__ == "__main__":
    unittest.main()