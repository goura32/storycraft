# 依頼入口と未解決事項の解決の契約

## 1. 依頼入口

新規作品は、採用済み依頼文またはキーワード入力のどちらか一方から始めます。

| 入口 | 必須入力 | 出力 | 次工程 |
|---|---|---|---|
| 依頼文 | 依頼内容 | 不変 `request` | `initial_design` |
| キーワード | 1個以上の短いキーワード | 依頼候補、確認、採用済み `request` | `initial_design` |

キーワード起点は `request_intake` 工程です。`init` は入力 keywords を `inputs/keywords-{通番6桁}/record.json` として不変確定し、`run` がその入力記録と不変 settings を読んで生成、確認、修正を行います。入力記録は `keywords_id`、正規化したキーワード配列、言語、created_at を持ち、selection 前の候補・確認・呼出し記録は `keywords_id` と `settings_id` を必ず参照します。採用時だけ、採用済み `request` を唯一の初期化時成果物として `input_selection_id=null` で不変確定し、直後に最初の選択スナップショットを確定します。

採用済み依頼は次を満たします。

- `title`: 空でない文字列
- `genre`: 1件以上の重複しない空でない文字列配列
- `premise`: 空でない文字列
- `required_elements` と `avoid`: 文字列配列。重複なし
- `ending_preference`: 空でない文字列
- `volume_count`: 4〜10 の整数
- `language`: `ja`

直接依頼でもキーワード起点でも、依頼採用時に、採用済み `request`、依頼採用記録、`request` と `settings` をスロットに持つ最初の選択スナップショット、`current_stage=initial_design` を原子的に確定します。採用済み `request` は唯一の初期化時成果物として `input_selection_id=null` を持ちます。初期設計採用は、この最初のスナップショットの後続を作ります。

## 2. 未解決事項の正本

初期設計は、各未解決事項を未解決事項として作ります。正規形未解決事項は名称、種別、結末必須性、説明を持ちます。結末必須未解決事項は同じ`thread_name`の達成条件を一つ持ちます。

`generation.unresolved_thread_states` は各未解決事項の名称に対応して次を持ちます。

```json
{
  "status": "open | progressed | resolved"
}
```

`resolved` は結末必須未解決事項の達成条件を満たす本文根拠があると独立確認され、対応するcontinuity-updateのevidence locationが存在するときだけ許可します。

## 3. 計画payloadによる予定の連鎖

V1では、`thread_id`、`action`、`required_conditions` を持つ別個のallocation payloadや`thread_allocations`成果物は作りません。未解決事項の予定は、各計画の既存payloadへ次の粒度で表現します。

- series-plan: `thread_progression` と `revelation_schedule` が巻単位の進行・開示予定を持つ。
- volume-plan: `thread_goals` と `revelations` が章単位の目標・開示予定を持つ。
- chapter-plan: `required_revelations` と `ending_changes` が場面配分と章末状態を持つ。
- scene-plan: `intended_revelations`、`intended_changes`、`intended_beats` が当該場面の予定を持ち、座標はselection slotとartifact IDだけで束縛する。

子計画は親payloadの対象範囲を狭めて具体化し、親にない目的、開示、予定変化を追加しません。未解決事項の名称・達成条件との対応は、初期設計の`unresolved_threads`と`ending_conditions.thread_name`を読み合わせ、別名のIDや説明文の重複保存は行いません。scene-cardはscene-planの予定を`required_beats`、`ending_state_targets`、`allowed_updates`へ本文用に具体化するだけです。

## 4. 本文から解決まで

未解決事項を進行・解決する場面は、次をすべて満たす必要があります。

1. 場面本文に達成条件を満たす本文根拠がある。
2. 継続性更新が許可された状態変更を記録する。
3. 更新が本文位置をevidence locationとして記録する。
4. 場面確定がその更新を後続の作品状態へ一度だけ適用する。

`progressed` は同じ手順で記録できます。達成条件を満たした場合だけ`resolved`へ変更し、未達なら`open`または`progressed`のままにします。

コードは本文根拠位置、場面計画の操作、カードの許可更新、未解決事項状態の遷移を検証します。LLM は本文が条件を意味的に満たすかを確認します。

## 5. 巻公開の検証

巻公開は、当該巻のscene-plan、scene-card、本文、継続性更新、作品状態、品質判定のselection lineageを決定的に検証します。本文の意味的な達成判定は通常の本文品質確認で行い、上限到達時は他の本文と同じく最後の形式有効版を注意付き採用します。公開工程自身はLLMを呼びません。

最終巻でも追加の確認記録、本文再生成、注意付き公開による例外を設けません。通常の巻公開検証が成功すれば、その巻の公開がシリーズ制作完了です。

## 6. 復旧

計画・本文・継続性更新・根拠が不整合なら停止し、その作業場所を再開しません。公開済み巻の本文、場面、作品状態、公開記録は変更できません。
