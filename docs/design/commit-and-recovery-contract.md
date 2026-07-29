# 確定とクラッシュ復旧の契約

## 1. 共通前提

一つの作業場所は一つの書込みロックだけが変更できます。ロックは `runtime/lock` にあり、作業場所ID、run ID、PID、取得時刻を持ちます。`run` はロックを取れなければ終了コード `75` で何も変更しません。

ID 予約、一時保存作成、最終配置への原子的な名前変更、run-state 更新は同じファイルシステムで行います。ID の欠番は許可します。予約済み ID は再利用しません。

## 2. 共通収束表

`pending_commit` があるとき、提供者を呼ぶ前に manifest の `targets` と最終配置を照合して収束します。

| manifest の各 target | 最終配置 | 状態参照 | 処理 |
|---|---|---|---|
| `pending` | その target の最終配置なし・staging target 有効 | 更新前 | staging target を最終配置へ原子的に名前変更し、manifest を `finalized` に更新 |
| `pending` | その target の最終配置が有効・staging target なし | 更新前 | rename 後の正常な中断として、最終配置の種類・ID・ダイジェストを再検証し manifest を `finalized` に更新 |
| `finalized` | その target の最終配置が有効・staging target なし | 更新前 | 最終配置を再検証し、全 target 完了後に状態を更新 |
| 全て `finalized` | 全 target が有効 | 更新後 | 最終配置と状態の参照を検証して保留中を消す |
| manifest と target が不一致 | 任意 | 任意 | `blocked`。`stop_reason=manual_review_required` |

「有効」はスキーマ、参照、入力選択、種類ごとの不変条件に通ることです。自動削除、自動選択、LLM 再呼出しはしません。

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

巻公開の一時保存は公開記録と原稿を含みます。記録は全場面、品質判定、計画、現在状態、設定を現在選択のスロットと照合します。公開は選択スナップショットのスロットを変更しないため、後続選択を作りません。最終配置への原子的な名前変更後だけ公開済み巻を追加します。

`pending_commit` manifest の契約（仕様レベル）:

- manifest には target ごとに `artifact_id`、`artifact_kind`、ステージング相対パス、最終配置相対パス、SHA-256 ダイジェスト、状態を持つ
- `run` 起動時に manifest の target と最終配置を照合し、種類・ID・ダイジェストが一致しない target は「不整合」として扱う
- 不整合 target がある場合、自動削除・自動選択・LLM 再呼出しはせず、`blocked` にする
- 正常 target は最終配置へ原子的リネーム（同一ファイルシステム上）し、manifest を `committed` に更新、run-state を進める

lock レコードの契約（仕様レベル）:

- `runtime/lock` に workspace_id、run_id、pid、取得時刻を持つ
- PID 存在・ID 一致で有効、それ以外は残存とみなす
- 有効 lock がある間は `run` は `lock_unavailable` で終了する。**`status`/`validate` は lock を取得せず、残存 lock の有無も確認せず、状態を変更せずに実行する。**
- `run` は起動時に残存 lock を検査し、無効なら削除して継続、有効なら `lock_unavailable` で終了

選択スナップショット `slots` キー命名規則（仕様レベル）:

- 単一成果物: `^[a-z_]+$`（例: `request`, `settings`, `series_plan`, `initial_design`, `current_state`）
- 座標付き成果物: `^[a-z_]+\\.v[0-9]{2}(\\.c[0-9]{2})?(\\.s[0-9]{2})?$`
- 品質判定: `^quality_disposition\\.quality-[0-9]{6}$`
- 巻公開入力: `^prior_volume_plan$`

選択スナップショットの状態遷移（仕様レベル）:

- 最初の selection は `input_selection_id=null`、依頼採用時に `request` と `settings` スロットを持つ
- `initial_design` 採用で `initial_design`、`current_state`（最初の generation）、`initial_design_adoption` を追加
- `series_plan`、`volume_plan`、`chapter_plan`、`scene_plan`、`scene_card` 採用で各スロットを追加
- `scene_prose`/`scene_continuity`/`scene_commit` 採用で `scene`、`current_state`（新 generation）、`scene_commit`、`prior_volume_plan`（当該巻の volume_plan）を追加
- `volume_publication` 採用で `volume_publication` を追加、スロット変更なしで次巻へ
- 新 selection は不変ファイルとして作成し、`runtime/run-state.json` の `current_selection_id` を原子的に書き換え
