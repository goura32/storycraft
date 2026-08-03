# 計画工程の契約

## 1. 共通規則

`series_plan`、`volume_plan`、`chapter_plan`、`scene_plan` は、物語の意図と予定を作る工程です。作品事実を更新しません。各工程は候補全体を生成、決定的検証、独立 LLM 確認の順で扱い、重大な指摘があり、`quality_revision_limit` の上限前であれば候補全体を修正して再検証・再確認します。

採用時は計画成果物、採用選択、後続選択スナップショット、次の `current_target` を原子的に確定します。後続工程はスナップショットのスロットだけを読み、最新探索、可変選択済みフラグ、引継ぎ要約を使いません。

## 2. シリーズ計画

| 区分 | 内容 |
|---|---|
| 責務 | 全巻の役割、巻数、結末必須事項の進行・解決予定を作る |
| 必須入力スロット | `request`、`settings`、`initial_design`、`current_state`、`initial_design_adoption` |
| 出力成果物 | `series-plan`。`volume_count`（4〜10）、昇順の`volume_summaries`、シリーズ目的・人物/関係/未解決事項の進行・結末経路 |
| 次工程 | `volume_plan`、対象は第1巻 |

`volume_summaries`は各巻の`volume_number`を持つ昇順の配列です。巻・章・場面の座標は計画payloadへ重複保存せず、artifact IDとselection slotで束縛します。未知のplanning payload項目は拒否します。

コードは、巻数が依頼と一致すること、4〜10の範囲、巻番号の連続性、各必須未解決事項の進行、IDと配列項目の妥当性を検証します。LLMは、巻全体の役割、伏線・解決の配分、初期設計との意味的整合を確認します。

## 3. 巻計画

| 区分 | 内容 |
|---|---|
| 責務 | 一巻で扱う人物・対立・転換・未解決事項の予定と章構成を作る |
| 必須入力スロット | `settings`、第1巻は `current_state` と `series_plan`。第2巻以降はこれらに、直前に公開された巻番号を `NN` とする `volume_plan.vNN` を加える。`request` と `initial_design` はこれらの採用済み正本から必要な意味内容を読み直さない。`settings` は物語の意味内容ではなく LLM 実行設定として必須 |
| 決定的前提 | 第1巻以外は直前巻の `volume_publication` が公開済みであること |
| 次工程 | `chapter_plan`、対象は当該巻第1章 |

`volume-plan`のpayloadは巻番号を重複保持せず、`chapter_summaries`で章番号と章の目的を表します。巻番号は`volume_plan.vNN`のselection slotとartifact IDで束縛します。

コードは、対象巻がシリーズ計画の未公開の次巻であり、当該巻の`volume_plan.vNN`が現在selectionに未登録であること、直前巻が公開済みであること、割当がシリーズ計画の対象巻の範囲内であること、章番号が連続すること、章数が settings の `chapter_per_volume_range` 内であることを検証します。LLM は、正規形現在状態と採用計画に対して、巻の役割、人物・未解決事項の割当、前巻計画からの継続条件に矛盾がないかを確認します。

## 4. 章計画

| 区分 | 内容 |
|---|---|
| 責務 | 一章の目的、場面数範囲、各場面の役割と未解決事項の予定を作る |
| 必須入力スロット | `settings`、`initial_design`、`current_state`、`series_plan`、対象 `volume_plan` |
| 出力成果物 | `chapter-plan`。章の目的・状態変化・`scene_summaries`による場面構成 |
| 次工程 | `scene_plan`、対象は当該章第1場面 |

コードは、対象章が巻計画の未確定の次章であること、場面番号の連続性、場面数が settings の `chapter_scene_range` 内であること、割当が巻計画の対象範囲内であることを検証します。LLM は、章の目的と巻の役割、場面の配分、未解決事項の進行が整合することを確認します。

## 5. 場面計画

| 区分 | 内容 |
|---|---|
| 責務 | 一場面が達成する物語上の目的、未解決事項の進行・解決予定、次の場面へ渡す予定を作る |
| 必須入力スロット | `settings`、`initial_design`、`current_state`、`series_plan`、対象 `volume_plan`、対象 `chapter_plan` |
| 出力成果物 | `scene-plan`。対象座標は artifact ID と selection slot で束縛し、親計画の目的・対象人物・場所・予定する変化・開示制約の範囲内で、目的、対象人物、未解決事項割当、`intended_beats`、`intended_revelations`、`intended_changes`、`prohibited_disclosures` を具体化する。`required_beats` と `ending_state_targets` はscene-planには保存せず、次工程のscene-cardが本文用制約として派生する。scene-planもscene-cardも新しい結末条件、未解決事項、物語目的を定義しない。 |
| 次工程 | `scene_card`、同一場面座標 |

コードは、座標が章計画の未確定の次場面であること、未解決事項の予定が親計画の対象範囲内であることを検証します。LLM は、場面目的、人物の動機、予定する変化、結末条件への寄与が意味的に成立することを確認します。

## 6. 採用と選択スナップショット

各計画の採用では、入力スナップショットを複写して次のスロットを追加または置換します。

| 工程 | 追加・置換するスロット | 次工程 |
|---|---|---|
| `series_plan` | `series_plan`、`series_plan_adoption` | `volume_plan.v01` |
| `volume_plan` | `volume_plan.vNN`、`volume_plan_adoption.vNN` | `chapter_plan.vNN.c01` |
| `chapter_plan` | `chapter_plan.vNN.cMM`、`chapter_plan_adoption.vNN.cMM` | `scene_plan.vNN.cMM.s01` |
| `scene_plan` | `scene_plan.vNN.cMM.sKK`、`scene_plan_adoption.vNN.cMM.sKK` | `scene_card.vNN.cMM.sKK` |

採用記録は候補 ID と品質判定 ID を参照します。次工程は計画候補の固定パスや有効候補を読まず、このスロットを読むだけです。章・場面座標は常に二桁ゼロ埋めです。第1巻以外の `volume_plan` は、直前に公開された巻番号を `NN` とする `volume_plan.vNN` slot を必須入力とします。場面確定の selection 更新で、当該巻の計画を別名の slot に複写しません。

## 7. 修正・失敗

各計画の確認記録は対象候補 ID、指摘 ID、重要度、根拠位置を持ちます。修正の LLM 応答は同じ計画スキーマ全体だけを返します。元候補 ID と確認記録 ID はシステム側候補記録が持ちます。重大指摘が上限前なら全体修正、上限到達なら最後の形式有効候補を注意付き採用します。

生成、確認、修正の形式不正は各論理処理ごとに初回を含め `invalid_response_limit` 回まで、別シードで再呼出しします。生成または確認で有効候補がないまま上限に達した失敗時は、採用選択・後続スナップショット・次工程を確定せず、`blocked` と `last_error.code=invalid_response_limit` にします。修正中に `quality_revision_limit=0` で既存の形式有効候補がある場合だけ、その候補を注意付き採用する共通契約の例外を適用します。
