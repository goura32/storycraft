# 成果物と保存の設計

## 1. 正本と凍結した選択スナップショット

成果物の内容を複写して別の正本にしません。下流工程は、固定パス、最新探索、成果物ごとの可変な `selected` フラグを使わず、`logical slot → artifact ID` を持つ不変の選択スナップショットだけを入力権限にします。

```text
runtime/selections/selection-000001/record.json
```

```json
{
  "schema_version": 1,
  "selection_id": "selection-000001",
  "input_selection_id": null,
  "slots": {
    "request": "request-000001",
    "settings": "settings-000001"
  },
  "created_at": "..."
}
```

依頼採用後に最初のスナップショットを作り、計画採用・場面候補採用・場面確定のたびに、前スナップショットを入力として新スナップショットを確定します。

実行状態は現在の `selection_id` だけを参照します。作品の事実、計画本文、公開原稿、LLM 応答は複写しません。

| 情報 | 正本 | 参照だけを持つもの |
|---|---|---|
| 作品の事実 | 確定済み作品状態 | 計画、場面、確認記録 |
| 物語の意図 | 採用済み計画・場面カード | 次工程の入力束 |
| 本文と場面更新 | 確定済み場面 | 作品状態、巻公開原稿の組立入力 |
| 読者向け出力 | 巻公開 `manuscript.md` | 巻公開 `record.json` |
| LLM の入出力 | 呼出し記録 | 確認記録、検証記録 |
| 実行位置 | `runtime/run-state.json` | なし |

## 2. 配置と ID

```text
workspace/
  inputs/keywords-000001/record.json
  inputs/request-000001/record.json
  quality/quality-000001/record.json
  candidates/candidate-000001/record.json
  reviews/review-000001/record.json
  runtime/
    run-state.json
    settings/settings-000001/record.json
    counters.json
    staging/
    selections/selection-000001/
    calls/call-000001/
    adoptions/adoption-000001/record.json
  design/
    initial/...
    series-plans/...
    volume-plans/...
    chapter-plans/...
    scene-plans/...
    scene-cards/...
  generations/gen-000001/
  scenes/scene-prose-v01-c01-s01-000001/record.json
  scenes/continuity-v01-c01-s01-000001/record.json
  scenes/scene-v01-c01-s01-000001/record.json
  scenes/scene-commit-v01-c01-s01-000001/record.json
  publications/volume-pub-v01-000001/
```

ID は採番後に変更しません。

| 種類 | 形式 | カウンタ |
|---|---|---|
| 品質判定 | `quality-{通番6桁}` | `next_quality` |
| キーワード入力 | `keywords-{通番6桁}` | `next_keywords` |
| 作品状態 | `gen-{通番6桁}` | `next_generation` |
| 設定 | `settings-{通番6桁}` | `next_settings` |
| 巻公開 | `volume-pub-v{巻番号2桁}-{通番6桁}` | `next_volume_publication` |
| 選択スナップショット | `selection-{通番6桁}` | `next_selection` |
| 呼出し | `call-{通番6桁}` | `next_call` |

| 候補 | `candidate-{通番6桁}` | `next_candidate` |
| 採用記録 | `adoption-{通番6桁}` | `next_adoption` |
| 確認記録 | `review-{通番6桁}` | `next_review` |
| 依頼 | `request-{通番6桁}` | `next_request` |
| 初期設計 | `initial-design-{通番6桁}` | `next_initial_design` |
| シリーズ計画 | `series-plan-{通番6桁}` | `next_series_plan` |
| 巻計画 | `volume-plan-v{巻番号2桁}-{通番6桁}` | `next_volume_plan` |
| 章計画 | `chapter-plan-v{巻番号2桁}-c{章番号2桁}-{通番6桁}` | `next_chapter_plan` |
| 場面計画 | `scene-plan-v{巻番号2桁}-c{章番号2桁}-s{場面番号2桁}-{通番6桁}` | `next_scene_plan` |
| 場面カード | `scene-card-v{巻番号2桁}-c{章番号2桁}-s{場面番号2桁}-{通番6桁}` | `next_scene_card` |
| 場面本文 | `scene-prose-v{巻番号2桁}-c{章番号2桁}-s{場面番号2桁}-{通番6桁}` | `next_scene_prose` |
| 継続性更新 | `continuity-v{巻番号2桁}-c{章番号2桁}-s{場面番号2桁}-{通番6桁}` | `next_continuity` |
| 場面確定単位 | `scene-v{巻番号2桁}-c{章番号2桁}-s{場面番号2桁}-{通番6桁}` | `next_scene` |
| 場面確定記録 | `scene-commit-v{巻番号2桁}-c{章番号2桁}-s{場面番号2桁}-{通番6桁}` | `next_scene_commit` |

V1 の workspace には、未定義の巻間要約、シリーズ完結成果物、全巻を結合した原稿を保存しません。

## 3. 不変確定の共通手順

複数ファイル成果物は必ずディレクトリ単位で staging に作り、`pending_commit` の `targets` manifest で複数の最終配置を管理します。

1. ID を予約し、現在の選択スナップショットと必要な入力スロットを固定する。
2. `runtime/staging/<kind>-<id>/` に全ファイルを新規作成する。
3. 形式、必須項目、参照実在、採用状態、内容の内部整合を決定的に検証する。同じ manifest の target を参照する場合は、その staging target 全体を閉じた参照集合として解決する。manifest 外の参照は最終配置だけを許可する。
4. [状態と遷移](state-and-transitions.md#21-現在対象と保留中確定)で定める `pending_commit` manifest を保存する。
5. manifest の `pending` target を一つずつ原子的に名前変更する。再起動時に `pending` target の最終配置だけが有効なら、rename 後・manifest 更新前の正常な中断として target を `finalized` に進める。成功した target は `finalized` に更新する。**同一 target の staging と最終配置が同時にある場合は、manifest と配置の不整合として `blocked` にする。**
6. 全 target の種類、ID、スキーマ、参照を最終配置で再検証する。
7. 実行状態の採用参照・公開記録・次工程を更新し、`pending_commit` を消す。

最終配置が既にある場合は上書きしません。`pending_commit` の完全なスキーマと復旧可否は[状態と遷移](state-and-transitions.md#21-現在対象と保留中確定)だけに従います。

## 4. 呼出し・検証・品質記録

呼出し、決定的検証、LLM 確認、品質上限の結果は不変の監査記録です。作品正本を更新するのは、採用処理と場面確定だけです。

- `runtime/calls/<call-id>/record.json` と依頼/応答: 物理的な一回の提供者呼出しと、通信・応答 envelope・provider schema の決定的評価。selection前のrequest_intakeでは`settings_id`と`input_refs`（keywords/settings）を持つ。送受信本文は監査用の生記録であり、候補 payload、ReviewResponse、参照・根拠位置の意味検証の正本はそれぞれ候補・確認・品質記録の検証境界だけとする
- `candidates/<candidate-id>/record.json`: `schema_version`、`candidate_id`、`artifact_kind`、`input_selection_id`、`keywords_id`、`settings_id`、工程 payload、生成または修正元 candidate ID、対応する call ID、作成時刻を持つ不変候補記録。selection 前の `request_intake` だけは `keywords_id` を持ち、他工程では `null` とする。
- `reviews/<review-id>/record.json`: `schema_version`、`review_id`、対象 candidate ID、ReviewResponse、対応する call ID、作成時刻を持つ不変確認記録。selection前の入力源はcandidate IDから候補記録へ辿り、reviewへkeywords/settingsを重複保存しない
- `runtime/adoptions/<adoption-id>/record.json`: `schema_version`、`adoption_id`、採用 candidate ID、quality ID、確定する成果物 ID 列、後続 selection ID、作成時刻を持つ不変採用記録。これは内容やLLM要約の正本ではなく、候補・品質・selectionを一つの原子的確定へ束ねる監査・復旧用の参照束です。品質判定の生成は採用記録を参照しません。
- `quality/<quality-id>/record.json`: 採用候補 ID、確認記録 ID 列、修正回数、結果、残存重大指摘、注意種別を持つ不変品質判定。`quality-id` は `quality-{通番6桁}`。採用記録はこの ID を一つだけ参照し、本文採用では `scene_prose_disposition.vNN.cMM.sKK` slot、継続性更新採用では `continuity_disposition.vNN.cMM.sKK` slot に固定する。ReviewResponse 全体の正本は `reviews` 記録であり、品質判定の `remaining_major_issues` は公開可否を再検証するための critical 指摘の決定的な派生値だけを持つ。品質判定は監査記録であり、採用済み内容成果物の共通外枠を持たない。

`runtime/raw_logs/<stem>.json` と同名の `.md` は、境界処理から戻った物理呼出しの送受信を人が確認するための非正本補助ログです。形式不正で境界が例外終了した呼出しは `runtime/calls` の記録だけが残ることがあります。機械的な監査・復旧・`validate` が参照する正本は `runtime/calls/<call-id>/record.json` だけで、raw log を後続工程の入力・内容判定・公開原稿に使いません。送信内容から内部 marker 付きのメッセージと thinking 本文を除外し、認証情報は保存しません。call ID、設定参照、endpoint、model などの呼出しメタデータは補助ログに含まれ得ます。公開ディレクトリへコピーしません。

依頼/応答に認証情報、Authorization、secret header、思考過程を保存しません。呼出し記録は作品状態や公開原稿の正本ではありません。

## 5. 入力束

LLM に渡す入力は、実行時に正本から組み立てる読み取り専用の束です。入力束自体を正本として固定保存しません。ただし呼出し記録は、どの成果物 ID、設定スナップショット、シード、要求・応答本文を用いたかを持ちます。生記録を後続工程の入力や正本の内容判定に使ってはなりません。

次巻の計画入力は、現在の選択スナップショットに固定された `settings`、作品状態、シリーズ計画、直前に公開された巻番号を `NN` とする `volume_plan.vNN` slot を直接参照します。直前巻の計画を別名の slot や巻引継ぎ要約へ複写しません。確定済み本文と公開記録は次巻計画の入力にしません。本文や継続性更新から巻引継ぎ要約を抽出・確定しません。
