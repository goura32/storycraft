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
| 本文と場面更新 | 確定済み場面 | 作品状態、巻公開記録 |
| 読者向け出力 | 巻公開 `manuscript.md` | 巻公開 `record.json` |
| LLM の入出力 | 呼出し記録 | 確認記録、検証記録 |
| 実行位置 | `runtime/run-state.json` | なし |

## 2. 配置と ID

```text
workspace/
  inputs/keywords-000001/record.json
  quality/quality-000001/record.json
  runtime/
    run-state.json
    settings/settings-000001/record.json
    counters.json
    staging/
    selections/selection-000001/
    calls/call-000001/
    validations/validation-000001/
  design/
    initial/...
    series-plans/...
    volume-plans/...
    chapter-plans/...
    scene-plans/...
  generations/gen-000001/
  scenes/scene-v01-c001-s001/
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
| 検証 | `validation-{通番6桁}` | `next_validation` |
| 依頼 | `request-{通番6桁}` | `next_request` |
| 初期設計 | `initial-design-{通番6桁}` | `next_initial_design` |
| シリーズ計画 | `series-plan-{通番6桁}` | `next_series_plan` |
| 巻計画 | `volume-plan-v{巻番号2桁}-{通番6桁}` | `next_volume_plan` |
| 章計画 | `chapter-plan-v{巻番号2桁}c{章番号2桁}-{通番6桁}` | `next_chapter_plan` |
| 場面計画 | `scene-plan-v{巻番号2桁}c{章番号2桁}s{場面番号2桁}-{通番6桁}` | `next_scene_plan` |
| 場面カード | `scene-card-v{巻番号2桁}c{章番号2桁}s{場面番号2桁}-{通番6桁}` | `next_scene_card` |
| 場面本文 | `scene-v{巻番号2桁}c{章番号2桁}s{場面番号2桁}-{通番6桁}` | `next_scene` |
| 継続性更新 | `continuity-v{巻番号2桁}c{章番号2桁}s{場面番号2桁}-{通番6桁}` | `next_continuity` |
| 場面確定 | `scene-commit-v{巻番号2桁}c{章番号2桁}s{場面番号2桁}-{通番6桁}` | `next_scene_commit` |

既存の `handoffs/`、`completion/`、全巻を結合した `series.md` は V1 新形式に存在しません。

## 3. 不変確定の共通手順

複数ファイル成果物は必ずディレクトリ単位で staging に作り、`pending_commit` の `targets` manifest で複数の最終配置を管理します。

1. ID を予約し、現在の選択スナップショットと必要な入力スロットを固定する。
2. `runtime/staging/<kind>-<id>/` に全ファイルを新規作成する。
3. 形式、必須項目、参照実在、採用状態、内容の内部整合を決定的に検証する。同じ manifest の target を参照する場合は、その staging target 全体を閉じた参照集合として解決する。manifest 外の参照は最終配置だけを許可する。
4. `pending_commit` manifest を保存する。manifest は kind、staging、各 target の ID・種類・staging 相対パス・最終パス・内容ダイジェスト・`pending | finalized` 状態、selection 更新、状態更新内容を持つ。
5. manifest の `pending` target を一つずつ原子的に名前変更する。再起動時に `pending` target の最終配置だけが有効なら、rename 後・manifest 更新前の正常な中断として target を `finalized` に進める。成功した target は `finalized` に更新する。異なる target の staging と最終配置が同時にあっても停止しない。
6. 全 target の種類、ID、内容ダイジェスト、参照を最終配置で再検証する。
7. 実行状態の採用参照・公開記録・次工程を更新し、`pending_commit` を消す。

最終配置が既にある場合は上書きしません。復旧時は target ごとに manifest と照合し、`pending` target の staging、`finalized` target の最終配置、または rename 後・manifest 更新前の `pending` target の有効な最終配置を許可します。同じ target の staging と最終配置が両方ある、どちらかが不正、または manifest にない配置がある場合は、自動選択せず停止します。

## 4. 呼出し・検証・品質記録

呼出し、決定的検証、LLM 確認、品質上限の結果は不変の監査記録です。作品正本を更新するのは、採用処理と場面確定だけです。

- `calls/<call-id>/record.json` と依頼/応答: 物理的な一回の提供者呼出し
- `validations/<validation-id>/record.json`: 解析、スキーマ、参照、根拠位置などの決定的評価
- 候補版の `review-record.json`: 形式有効な独立確認
- `quality/<quality-id>/record.json`: 採用候補 ID、採用記録 ID、確認記録 ID 列、修正回数、結果、残存重大指摘、注意種別を持つ不変品質判定。`quality-id` は `quality-{通番6桁}`。採用記録はこの ID を一つだけ参照し、本文採用では `scene_prose_disposition.vNN.cMM.sKK` slot に固定する。

依頼/応答に認証情報、Authorization、secret header、思考過程を保存しません。呼出し記録は作品状態や公開原稿の正本ではありません。

## 5. 入力束

LLM に渡す入力は、実行時に正本から組み立てる読み取り専用の束です。入力束自体を正本として固定保存しません。ただし呼出し記録は、どの成果物 ID、設定スナップショット、シード、要求・応答本文を用いたかを持ちます。

次巻の計画入力は、現在の選択スナップショットに固定された作品状態、シリーズ計画、直前公開巻の `volume_plan` だけを直接参照します。これらは `prior_volume_plan` slot に固定する。確定済み本文と公開記録は次巻計画の入力にしません。本文や継続性更新から巻引継ぎ要約を抽出・確定しません。
