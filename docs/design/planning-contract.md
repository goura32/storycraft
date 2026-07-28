# 計画工程の契約

## 1. 共通規則

`series_plan`、`volume_plan`、`chapter_plan`、`scene_plan` は、物語の意図と予定を作る工程です。作品事実を更新しません。各工程は候補全体を生成、決定的検証、独立 LLM 確認、必要なら候補全体の修正、再検証・再確認の順で扱います。

採用時は計画 artifact、採用選択、successor selection snapshot、次の `current_target` を原子的に確定します。後続工程は snapshot の slot だけを読み、最新探索、可変 selected flag、引継ぎ要約を使いません。

## 2. シリーズ計画

| 区分 | 内容 |
|---|---|
| 責務 | 全巻の役割、巻数、結末必須事項の進行・解決予定を作る |
| 必須入力 slot | `request`、`settings`、`initial_design`、`current_state`、`initial_design_adoption` |
| 出力 artifact | `series-plan`。巻番号順の `volumes`、各巻の役割、各必須 thread の `thread_allocations` |
| 次工程 | `volume_plan`、対象は第1巻 |

`thread_allocations` は thread ID、action（`introduce|progress|resolve`）、対象の巻・章・場面座標、当該工程で満たすべき条件を持ちます。結末必須 thread は少なくとも一つの `resolve` を持ち、`resolve` は一意です。

コードは、巻数が依頼と一致すること、巻番号の連続性、全必須 thread の割当、ID・action・座標の妥当性、`resolve` の一意性を検証します。LLM は、巻全体の役割、伏線・解決の配分、初期設計との意味的整合を確認します。

## 3. 巻計画

| 区分 | 内容 |
|---|---|
| 責務 | 一巻で扱う人物・対立・転換・thread の予定と章構成を作る |
| 必須入力 slot | `request`、`settings`、`initial_design`、`current_state`、`series_plan`、前巻までの確定 `scene` |
| 決定的前提 | 第1巻以外は直前巻の `volume_publication` が公開済みであること |
| 次工程 | `chapter_plan`、対象は当該巻第1章 |

コードは、対象巻が series plan の未公開の次巻であること、直前巻が公開済みであること、割当が series plan の対象範囲内であること、章番号と予定座標が有効であることを検証します。LLM は、確定済み本文と現在状態に対する巻の役割、人物・thread の進行が適切かを確認します。

## 4. 章計画

| 区分 | 内容 |
|---|---|
| 責務 | 一章の目的、場面数範囲、各場面の役割と thread の予定を作る |
| 必須入力 slot | `settings`、`initial_design`、`current_state`、`series_plan`、対象 `volume_plan` |
| 出力 artifact | `chapter-plan`。章番号、場面数範囲、場面役割、当該章の thread allocation |
| 次工程 | `scene_plan`、対象は当該章第1場面 |

コードは、対象章が volume plan の未確定の次章であること、場面番号の連続性、allocation が volume plan の範囲内であることを検証します。LLM は、章の目的と巻の役割、場面の配分、thread の進行が整合することを確認します。

## 5. 場面計画

| 区分 | 内容 |
|---|---|
| 責務 | 一場面が達成する物語上の目的、thread の進行・解決予定、次の場面へ渡す予定を作る |
| 必須入力 slot | `settings`、`initial_design`、`current_state`、`series_plan`、対象 `volume_plan`、対象 `chapter_plan` |
| 出力 artifact | `scene-plan`。場面座標、目的、対象人物、thread allocation、予定する事実変化、次場面条件 |
| 次工程 | `scene_card`、同一場面座標 |

コードは、座標が chapter plan の未確定の次場面であること、thread allocation が親計画の範囲内であること、`resolve` が series plan の一意の予定と一致することを検証します。LLM は、場面目的、人物の動機、予定する変化、結末条件への寄与が意味的に成立することを確認します。

## 6. 採用と selection snapshot

各計画の採用では、入力 snapshot を複写して次の slot を追加または置換します。

| 工程 | 追加・置換する slot | 次工程 |
|---|---|---|
| `series_plan` | `series_plan`、`series_plan_adoption` | `volume_plan.v01` |
| `volume_plan` | `volume_plan.vNN`、`volume_plan_adoption.vNN` | `chapter_plan.vNN.c001` |
| `chapter_plan` | `chapter_plan.vNN.cMM`、`chapter_plan_adoption.vNN.cMM` | `scene_plan.vNN.cMM.s001` |
| `scene_plan` | `scene_plan.vNN.cMM.sKK`、`scene_plan_adoption.vNN.cMM.sKK` | `scene_card.vNN.cMM.sKK` |

採用 record は候補 ID と quality disposition ID を参照します。次工程は計画候補の固定パスや active candidate を読まず、この slot を読むだけです。

## 7. 修正・失敗

各計画の確認記録は対象候補 ID、issue ID、重要度、根拠位置を持ちます。修正候補は同じ計画 schema 全体と、元候補 ID・確認記録 ID を持ちます。重大指摘が上限前なら全体修正、上限到達なら最後の形式有効候補を注意付き採用します。

生成、確認、修正の形式不正は各論理 operation ごとに初回を含め固定5回、別 seed で再呼出しします。失敗時は採用選択・successor snapshot・次工程を確定せず、共通の `blocked/manual_review_required` 契約に従います。
