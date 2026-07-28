# Storycraft V1 実装状況

> この文書は時点付きの実装・検証記録であり、仕様正本ではありません。現在の契約は[仕様書](SPECIFICATION.md)に従います。

最終確認日: 2026-07-26
確認対象 branch: `audit/v1-only-contracts`

## 確認済みの範囲

- Brief／Keywords 入力から Markdown Publication までの V1 workflow
- `run`、`resume`、`step`、`status`、`validate`
- Candidate Adoption、Scene Commit、Publication の atomic 確定と Recovery
- workspace lock、immutable 成果物、Provider 非依存の検証・復旧処理
- structured output、Review／Revision、変更範囲制約、Call audit
- 自動試験 527 件と隔離 wheel build／install smoke

## 実LLM確認

Initial Concept を対象に、structured output、批評・改稿ループ、Brief の `tone` 保持、Revision の変更範囲制約を確認済みです。

Stage別 critique schema 追加後の最終実LLM再試験は、費用と実行時間を考慮して実施していません。この未実施は自動試験または wheel smoke の失敗を意味しません。

## 記録上の注意

この記録は上記日付・branch 時点の結果です。Release 判断では、現在の仕様、現在の実装、現在の自動試験と smoke を改めて確認します。
