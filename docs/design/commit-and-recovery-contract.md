# 確定とクラッシュ復旧の契約

## 1. 共通前提

一つの作業場所は一つの書込みロックだけが変更できます。`run` は作業場所内のロック対象へOSの非ブロッキング排他ロックを取得し、プロセス終了時に自動解放します。取得できなければ終了コード `75` で何も変更しません。

ID 予約、一時保存作成、最終配置への原子的な名前変更、run-state 更新は同じファイルシステムで行います。ID の欠番は許可します。予約済み ID は再利用しません。

## 2. 共通収束表

`pending_commit` があるとき、提供者を呼ぶ前に manifest の `input_selection_id`（bootstrap request adoption の `null` を除く）が `run-state.current_selection_id` と一致することを確認し、publication targetの`record.json.input_selection_id`も同じmanifest入力へ束縛したうえで、`targets` と最終配置を照合して収束します。すべての target の staging/finalの存在、型、内容、cross-target lineage、final親directory、同一filesystem上のrename前提を移動前に検証し、検証に失敗した場合は一つも移動しません。manifest の唯一のスキーマ、収束表、`blocked` 条件は[状態と遷移](state-and-transitions.md#21-現在対象と保留中確定)に従います。「有効」はスキーマ、参照、入力選択、種類ごとの不変条件に通ることです。自動削除、自動選択、LLM 再呼出しはしません。

## 3. 種類ごとの状態更新

| 種類 | 最終配置後に一回だけ行う状態更新 |
|---|---|
| 候補採用 | 採用記録と後続選択を現在選択にする。次工程 / 対象を更新 |
| 場面確定 | 場面、作品状態、場面確定、後続選択を参照し、現在の作品状態 / 選択と次対象を更新 |
| 巻公開 | 公開記録、原稿を参照し、公開済み巻と次巻対象または完了を更新 |

状態更新前に最終配置の成果物が不正なら停止します。状態更新後に最終配置の成果物が失われた場合も停止します。

## 4. 候補採用の詳細

候補採用の一時保存は、採用する内容成果物、採用記録、後続選択だけを含みます。初期依頼採用では `request`、初期設計採用では `initial-design` と最初の `generation` も含みます。すでに不変確定した候補、確認記録、品質判定は移動・複写せず、その ID を参照します。

## 5. 場面確定の詳細

場面確定の一時保存は場面、後続の作品状態、確定記録、後続選択を含みます。すべてが同じ基準作品状態、場面座標、場面本文、継続性更新を参照しなければなりません。作品状態の更新は一度だけ適用します。

## 6. 巻公開の詳細

巻公開の一時保存は公開記録と原稿を含みます。公開時は `input_selection_id` から全場面、品質判定、計画、現在状態、設定を導出して現在選択のスロットと照合します。導出可能な ID 群を公開記録へ複写しません。公開は選択スナップショットのスロットを変更しないため、後続選択を作りません。最終配置への原子的な名前変更後だけ公開済み巻を追加します。

ロックの契約（仕様レベル）:

- `run` だけがOSの非ブロッキング排他ロックを取得する。取得中の別 `run` があれば `lock_unavailable` で終了する。
- `status` と `validate` はロックを取得・読取・削除せず、状態を変更しない。
- PID、取得時刻、run ID、残存lock判定・削除は持たない。プロセス終了後はOSロックが解放される。

選択スナップショット `slots` キー命名規則（仕様レベル）:

- 単一成果物: `^[a-z_]+$`（例: `request`, `settings`, `series_plan`, `initial_design`, `current_state`）
- 座標付き成果物: `^[a-z_]+\.v[0-9]{2}(\.c[0-9]{2})?(\.s[0-9]{2})?$`
- 本文品質判定: `^scene_prose_disposition\.v[0-9]{2}\.c[0-9]{2}\.s[0-9]{2}$`

選択スナップショットの状態遷移（仕様レベル）:

- 最初の selection は `input_selection_id=null`、依頼採用時に `request` と `settings` スロットを持つ
- `initial_design` 採用で `initial_design`、`current_state`（最初の generation）、`initial_design_adoption` を追加
- `series_plan`、`volume_plan`、`chapter_plan`、`scene_plan`、`scene_card` 採用で各スロットを追加
- `scene_prose` と `scene_continuity` の採用では、対応する内容、採用記録、品質判定の各スロットだけを追加し、`scene_commit` の確定でだけ `scene`、`current_state`（新 generation）、`scene_commit` を追加する。当該巻の `volume_plan.vNN` は同じ selection lineage に残す
- `volume_publication` は入力 selection を変更せず、公開記録を `published_volumes` にだけ追加して次巻または完了へ進む
- 新 selection を作る工程だけが不変ファイルを作成し、`runtime/run-state.json` の `current_selection_id` を原子的に書き換える
