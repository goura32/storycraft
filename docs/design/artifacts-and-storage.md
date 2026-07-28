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
    "initial_design": "initial-design-v0001",
    "series_plan": "series-plan-0001",
    "current_state": "gen-000001",
    "volume_plan.v01": "volume-plan-v01",
    "scene.v01.c001.s001": "scene-v01-c001-s001"
  },
  "created_at": "..."
}
```

依頼採用後に最初のスナップショットを作り、計画採用・場面候補採用・場面確定・未公開部分の解決記録による参照変更のたびに、前スナップショットを入力として新スナップショットを確定します。公開済み巻の構成元スロットは後続スナップショットでも変更を拒否します。

実行状態は現在の `selection_id` だけを参照します。作品の事実、計画本文、公開原稿、LLM 応答は複写しません。

| 情報 | 正本 | 参照だけを持つもの |
|---|---|---|
| 作品の事実 | 確定済み作品状態 | 計画、場面、確認記録 |
| 物語の意図 | 採用済み計画・場面カード | 次工程の入力束 |
| 本文と場面更新 | 確定済み場面 | 作品状態、巻公開記録 |
| 読者向け出力 | 巻公開 `manuscript.md` | 巻公開 `record.json` |
| LLM の入出力 | 呼出し記録 | 確認記録、検証記録 |
| 実行位置 | `runtime/run-state.json` | 解決記録 |

## 2. 配置と ID

```text
workspace/
  runtime/
    run-state.json
    config.json
    counters.json
    staging/
    selections/selection-000001/
    calls/call-000001/
    validations/validation-000001/
    resolutions/resolution-000001/
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
| 巻公開 | `volume-pub-v{巻番号2桁}-{通番6桁}` | `next_volume_publication` |
| 選択スナップショット | `selection-{通番6桁}` | `next_selection` |
| 解決記録 | `resolution-{通番6桁}` | `next_resolution` |
| 呼出し | `call-{通番6桁}` | `next_call` |
| 検証 | `validation-{通番6桁}` | `next_validation` |

既存の `handoffs/`、`completion/`、全巻を結合した `series.md` は V1 新形式に存在しません。

## 3. 不変確定の共通手順

複数ファイル成果物は必ずディレクトリ単位で確定します。

1. ID を予約し、現在の選択スナップショットと必要な入力スロットを固定する。
2. `runtime/staging/<kind>-<id>/` に全ファイルを新規作成する。
3. 形式、必須項目、参照実在、採用状態、内容の内部整合を決定的に検証する。
4. `pending_commit.phase=prepared` を保存する。
5. 一時保存を最終配置へ原子的に名前変更する。場面確定は場面の名前変更後 `scene_finalized`、作品状態の名前変更後 `generation_finalized` にする。
6. 最終配置を再検証し、`candidate_adoption` は `artifact_finalized`、`volume_publication` は `publication_finalized`、`resolution_application` は `record_finalized` にする。
7. 実行状態の採用参照・公開記録・次工程を更新し、`pending_commit` を消す。

最終配置が既にある場合は上書きしません。復旧時に一時保存と最終配置の両方がある、またはどちらかが不正なら、自動選択せず停止します。

## 4. 呼出し・検証・品質記録

呼出し、決定的検証、LLM 確認、品質上限の結果は不変の監査記録です。作品正本を更新するのは、採用処理と場面確定だけです。

- `calls/<call-id>/record.json` と依頼/応答: 物理的な一回の提供者呼出し
- `validations/<validation-id>/record.json`: 解析、スキーマ、参照、根拠位置などの決定的評価
- 候補版の `review-record.json`: 形式有効な独立確認
- 候補版の `quality-disposition.json`: 選択した版、残存重大指摘、公開注意の根拠

依頼/応答に認証情報、Authorization、secret header、思考過程を保存しません。呼出し記録は作品状態や公開原稿の正本ではありません。

## 5. 入力束

LLM に渡す入力は、実行時に正本から組み立てる読み取り専用の束です。入力束自体を正本として固定保存しません。ただし呼出し記録は、どの成果物 ID、設定スナップショット、シード、要求・応答本文を用いたかを持ちます。

次巻の計画入力は、現在の選択スナップショットに固定された作品状態、シリーズ・巻・章計画、確定済み本文、公開済み巻の記録を直接参照します。本文や継続性更新から巻引継ぎ要約を抽出・確定しません。
