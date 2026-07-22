# Storycraft 要件

> 利用者向けの不変の約束。実装・保存・LLM呼び出し詳細は[製品仕様](SPECIFICATION.md)を正本とする。

## 目的

Storycraftは、日本語で個人出版・販売できる完結小説シリーズをLLMで自動作成する。売上は保証しない。

## 利用者の関わり方

- 利用者は開始時にbriefまたはkeywordsを一度だけ入力する。
- 通常実行では巻・章・場面ごとの確認・介入を求めず、完結監査と出力まで自動で進める。
- LLMレビューは品質改善に使うが、severity・合否だけで停止しない。
- 中断後は初回入力を再入力せず再開できる。

## 物語と出力

- 本文前に人物、関係、世界、時間規則、主要な問い、結末条件を確定し、続けて全巻の不変`series map`を生成・レビュー・採用する。各巻は採用済みseries mapを必ず参照する。
- 各巻は人物または中心関係を変化させ、最終巻は開始時の結末条件を満たす。
- 場面は、本文・handoff・差分・Canon/State更新を一体で採用する。内部checkpointだけを後続の正本にしない。
- 本文根拠が完全一致する局所Canon項目とending evidenceを保持する。ending evidence indexは完結監査に使う。
- 完結監査は意味監査であり、監査結果自体をrevisionしない。成功扱いのために監査結果を書き換えない。
- 巻別・全巻Markdown、completion audit reportを公開する。内部prompt、raw response、checkpointは公開原稿に混入させない。空本文、必要場面欠落、機械的完成条件未達は完成扱いにしない。

## 範囲外

KDP自動入稿、Web UI、RAG、途中承認UI、旧state migrationは扱わない。
