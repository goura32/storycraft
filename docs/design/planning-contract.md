# 計画工程の契約

## 1. 共通規則

`series_plan`、`volume_plan`、`chapter_plan`、`scene_plan` は、物語の意図と予定を作る工程です。作品事実を更新しません。各工程は候補全体を生成、決定的検証、独立 LLM 確認、必要なら候補全体の修正、再検証・再確認の順で扱います。

採用時は計画成果物、採用選択、後続選択スナップショット、次の `current_target` を原子的に確定します。後続工程はスナップショットのスロットだけを読み、最新探索、可変選択済みフラグ、引継ぎ要約を使いません。

## 2. シリーズ計画

| 区分 | 内容 |
|---|---|
| 責務 | 全巻の役割、巻数、結末必須事項の進行・解決予定を作る |
| 必須入力スロット | `request`、`settings`、`initial_design`、`current_state`、`initial_design_adoption` |
| 出力成果物 | `series-plan`。巻番号順の `volumes`、各巻の役割、各必須未解決事項の `thread_allocations` |
| 次工程 | `volume_plan`、対象は第1巻 |

`thread_allocations` は未解決事項 ID、操作（`introduce|progress|resolve`）、対象巻、当該巻で満たすべき条件を持ちます。結末必須未解決事項は少なくとも一つの `resolve` を持ち、その対象巻は一意です。章・場面座標は後続計画がその巻の割当を具体化して初めて固定します。

コードは、巻数が依頼と一致すること、巻番号の連続性、全必須未解決事項の割当、ID・操作・巻番号の妥当性、`resolve` 対象巻の一意性を検証します。LLM は、巻全体の役割、伏線・解決の配分、初期設計との意味的整合を確認します。

## 3. 巻計画

| 区分 | 内容 |
|---|---|
| 責務 | 一巻で扱う人物・対立・転換・未解決事項の予定と章構成を作る |
| 必須入力スロット | 第1巻は `current_state`、`series_plan`。第2巻以降はこれらに `prior_volume_plan` を加える。`request`、`settings`、`initial_design` はこれらの採用済み正本から必要な意味内容を読み直さない |
| 決定的前提 | 第1巻以外は直前巻の `volume_publication` が公開済みであること |
| 次工程 | `chapter_plan`、対象は当該巻第1章 |

コードは、対象巻がシリーズ計画の未公開の次巻であること、直前巻が公開済みであること、割当がシリーズ計画の対象巻の範囲内であること、章番号が連続すること、章数が settings の `chapter_per_volume_range` 内であることを検証します。LLM は、正規形現在状態と採用計画だけに対する巻の役割、人物・未解決事項の進行が適切かを確認します。

## 4. 章計画

| 区分 | 内容 |
|---|---|
| 責務 | 一章の目的、場面数範囲、各場面の役割と未解決事項の予定を作る |
| 必須入力スロット | `settings`、`initial_design`、`current_state`、`series_plan`、対象 `volume_plan` |
| 出力成果物 | `chapter-plan`。章番号、場面数範囲、場面役割、当該章の未解決事項割当 |
| 次工程 | `scene_plan`、対象は当該章第1場面 |

コードは、対象章が巻計画の未確定の次章であること、場面番号の連続性、場面数が settings の `chapter_scene_range` 内であること、割当が巻計画の対象範囲内であることを検証します。LLM は、章の目的と巻の役割、場面の配分、未解決事項の進行が整合することを確認します。

## 5. 場面計画

| 区分 | 内容 |
|---|---|
| 責務 | 一場面が達成する物語上の目的、未解決事項の進行・解決予定、次の場面へ渡す予定を作る |
| 必須入力スロット | `settings`、`initial_design`、`current_state`、`series_plan`、対象 `volume_plan`、対象 `chapter_plan` |
| 出力成果物 | `scene-plan`。場面座標、目的、対象人物、未解決事項割当、予定する事実変化、次場面条件 |
| 次工程 | `scene_card`、同一場面座標 |

コードは、座標が章計画の未確定の次場面であること、未解決事項割当が親計画の対象範囲内であること、`resolve` がシリーズ計画で定めた対象巻と一致することを検証します。LLM は、場面目的、人物の動機、予定する変化、結末条件への寄与が意味的に成立することを確認します。

## 6. 採用と選択スナップショット

各計画の採用では、入力スナップショットを複写して次のスロットを追加または置換します。

| 工程 | 追加・置換するスロット | 次工程 |
|---|---|---|
| `series_plan` | `series_plan`、`series_plan_adoption` | `volume_plan.v01` |
| `volume_plan` | `volume_plan.vNN`、`volume_plan_adoption.vNN` | `chapter_plan.vNN.c001` |
| `chapter_plan` | `chapter_plan.vNN.cMM`、`chapter_plan_adoption.vNN.cMM` | `scene_plan.vNN.cMM.s001` |
| `scene_plan` | `scene_plan.vNN.cMM.sKK`、`scene_plan_adoption.vNN.cMM.sKK` | `scene_card.vNN.cMM.sKK` |

採用記録は候補 ID と品質判定 ID を参照します。次工程は計画候補の固定パスや有効候補を読まず、このスロットを読むだけです。第1巻では `prior_volume_plan` を入力にしません。場面確定の selection 更新は、当該巻の `volume_plan` を `prior_volume_plan` に固定します。第2巻以降の `volume_plan` は、この slot を必須入力とします。

## 7. 修正・失敗

各計画の確認記録は対象候補 ID、指摘 ID、重要度、根拠位置を持ちます。修正の LLM 応答は同じ計画スキーマ全体だけを返します。元候補 ID と確認記録 ID はシステム側候補記録が持ちます。重大指摘が上限前なら全体修正、上限到達なら最後の形式有効候補を注意付き採用します。

生成、確認、修正の形式不正は各論理処理ごとに初回を含め**上限回数**まで、別シードで再呼出しします。初回から有効候補がないまま上限に達した失敗時は、採用選択・後続スナップショット・次工程を確定せず、`blocked` と `last_error.code=invalid_response_limit` にします。既存有効候補がある無制限品質修正中の例外は共通契約に従います。
