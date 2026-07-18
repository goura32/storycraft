# プロンプトテンプレートと出力契約

> 製品上の正本は[製品仕様](../product/SPECIFICATION.md)、工程・正本・更新権限の設計正本は[シリーズ生成フロー設計](series_engine_flow.md)とする。

## 正本と構築責務

- 実送信プロンプトの正本は `templates/prompts/`、工程別出力スキーマの正本は `templates/prompts/schemas/` のJSONである。
- 実送信promptは工程ごとの `user/{stage}/{kind}_{stage}.j2` を正本とする。各fileはその工程の指示・入力・出力スキーマを直接記述し、`*_stage.j2` やJinja includeには依存しない。adapterは工程名で個別fileを選ぶ。
- `brief` はkeywords入力時だけ生成工程になる。採用条件は手入力briefと共通の構造・型・範囲であり、創作内容の品質やkeywordsとの意味的一致を決定的に検証しない。
- `volume_map` はCanon確定後だけに生成する。既存thread IDと `introduce` / `advance` / `resolve` を巻へ配分し、新規Canon事実を作らない。
- 批評・修正も工程ごとのtemplate入口を使い、批評には対象工程の生成スキーマも渡す。brief以外の批評は契約違反だけ、修正は対象工程の所有範囲だけを扱う。
- `PromptTemplate` はJinja標準`tojson`の `ensure_ascii=False` と `indent=2` を環境ポリシーで一元設定する。テンプレートは整形引数を指定しない。
- 有効なJSONオブジェクトだけを返す共通プロトコルは `system/common.j2` だけに置く。
- 採用可否は `series_contracts.py` の決定的検証器が決める。JSON object モードやLLM自己申告だけを信用しない。

## 実送信テンプレート

| 用途 | テンプレート | 出力スキーマ |
|---|---|---|
| 生成 | `user/{stage}/generate_{stage}.j2` | `schemas/{stage}.json` |
| 批評 | `user/{stage}/critique_{stage}.j2` | `schemas/critique.json` |
| 改訂 | `user/{stage}/revision_{stage}.j2` | 生成と同じ `schemas/{stage}.json` |

生成工程は以下である。

```text
brief / characters / relationships / world / timeline / threads / volume_map
/ volume_chapters / scene_card / scene / continuity / volume_summary / closure
```

## 工程別の決定的検証

| 工程 | 主な検証 |
|---|---|
| `brief` | 手入力briefと同じ必須項目・型・巻数範囲だけ。keywords由来の創作内容は検証・採点しない |
| `volume_map` | 4〜10巻、配列順の巻順、既存thread IDだけ、majorの `introduce → advance* → resolve` 配分、最終巻以外の `reader_question`、最終巻の空 `reader_question`。結末の正本は `brief.ending` |
| `characters` | 内容のみでIDなし、固定プロフィールと開始時状態 |
| `relationships` | 既存人物IDだけを参照し、固定意味と開始時状態を持つ |
| `world` | 内容のみでIDなし、固定事実・利用規則・開始時状態を分離 |
| `timeline` | 既知IDだけを参照し、固定規則と開始時状態を持つ |
| `threads` | 内容のみでIDなし、作者の真実・知識・開示規則・回収条件・開始状態を持つ |
| `volume_chapters` | 対象巻の章数、章番号、目的、開始・終了状態、場面数 |
| `scene_card` | 実行対象ID、既知の視点人物・開始終了時刻・場所・登場人物、必須イベント、伏線操作、開示・秘匿、場面終了時の変化、可視ID、可視IDの部分集合である更新許可ID。同じ巻で確定済みの最大終了時刻より前へ開始時刻を戻さない |
| `scene` | 空でない `content` だけ。状態更新・要約・注釈を含めない |
| `continuity` | 許可IDだけを更新し、更新根拠は凍結本文からそのままコピーした連続文字列で、完全一致する |
| `volume_summary` | 既知主要項目だけを参照する巻の引継ぎ要約 |
| `closure` | 全主要項目の回収済み状態と、本文中の結末根拠 |

## 記録と検証手順

- 生の要求・応答はシリーズ作業場所の `raw/` にJSONと同stem Markdownで残す。
- 草稿、批評、修正版、失敗理由、採用済み工程状態は `state.json` に残す。
- 各工程は検証済み草稿を先に保存する。批評または修正に失敗しても、検証済み草稿を失わない。
- テストでは、テンプレート展開、外部スキーマ、ID採番、台帳の工程順、本文根拠のない更新拒否、`resume`での採用済み台帳再生成防止を確認する。
