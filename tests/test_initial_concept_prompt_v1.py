"""Initial Concept Promptの動的保持規則。"""
from __future__ import annotations

import unittest

from storycraft.series_model import OpenAIStoryModel


class InitialConceptPromptTests(
    unittest.TestCase
):
    def test_generate_requires_exact_brief_tones(
        self,
    ) -> None:
        prompt = OpenAIStoryModel._render(
            "generate",
            "initial_concept",
            context={
                "brief": {
                    "tone": [
                        "静かな緊張",
                        "希望のある結末",
                    ],
                },
            },
        )

        self.assertIn(
            "文字列を一切変更せず",
            prompt,
        )
        self.assertIn(
            "完全一致",
            prompt,
        )
        self.assertIn(
            "語句結合",
            prompt,
        )

    def test_critique_checks_exact_brief_tones(
        self,
    ) -> None:
        prompt = OpenAIStoryModel._render(
            "critique",
            "initial_concept",
            context={
                "brief": {
                    "tone": [
                        "静かな緊張",
                    ],
                },
            },
            candidate={},
        )

        self.assertIn(
            "Briefの`tone`の全要素",
            prompt,
        )
        self.assertIn(
            "完全一致",
            prompt,
        )
        self.assertIn(
            "静かな緊張感",
            prompt,
        )

    def test_revision_preserves_exact_brief_tones(
        self,
    ) -> None:
        prompt = OpenAIStoryModel._render(
            "revision",
            "initial_concept",
            context={
                "brief": {
                    "tone": [
                        "静かな緊張",
                    ],
                },
            },
            candidate={},
            critique={},
        )

        self.assertIn(
            "文字列完全一致",
            prompt,
        )
        self.assertIn(
            "類義語化",
            prompt,
        )
        self.assertIn(
            "削除してはならない",
            prompt,
        )
        self.assertIn(
            "指定されたfieldだけを変更",
            prompt,
        )
        self.assertIn(
            "一字一句そのままコピー",
            prompt,
        )
        self.assertIn(
            "field単位で比較",
            prompt,
        )


    def test_generate_requires_full_field_self_check(
        self,
    ) -> None:
        prompt = OpenAIStoryModel._render(
            "generate",
            "initial_concept",
            context={
                "brief": {
                    "tone": [
                        "静かな緊張",
                        "希望のある結末",
                    ],
                },
            },
        )

        self.assertIn(
            "生成した全fieldを一度読み直す",
            prompt,
        )
        self.assertIn(
            "助詞、語順、役割名、複合語",
            prompt,
        )
        self.assertIn(
            "関連組織",
            prompt,
        )
        self.assertIn(
            "中国語の簡体字",
            prompt,
        )

    def test_critique_requires_exhaustive_grounding(
        self,
    ) -> None:
        prompt = OpenAIStoryModel._render(
            "critique",
            "initial_concept",
            context={
                "brief": {
                    "tone": [
                        "静かな緊張",
                    ],
                },
            },
            candidate={
                "logline": "候補本文",
            },
        )

        self.assertIn(
            "全fieldをそれぞれ確認",
            prompt,
        )
        self.assertIn(
            "すべて報告する",
            prompt,
        )
        self.assertIn(
            "一字一句そのまま引用",
            prompt,
        )
        self.assertIn(
            "candidateにない誤記",
            prompt,
        )
        self.assertIn(
            "issues`を空にするのは",
            prompt,
        )
        self.assertIn(
            "トップレベルfield名だけ",
            prompt,
        )
        self.assertIn(
            "`candidate.`接頭辞を付けない",
            prompt,
        )


if __name__ == "__main__":
    unittest.main()
