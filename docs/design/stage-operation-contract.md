# 工程処理と確定点

## 1. 共通処理

各候補工程は次の処理を持ちます。

| 処理 | 入力 | 出力 | 確定点 |
|---|---|---|---|
| `generate` | 生成入力束 | `candidate(0)` | `candidate_saved` |
| `review(r)` | 生成入力束 + `candidate(r)` | `ReviewResponse` | `review_saved` |
| `revise(r+1)` | 生成入力束 + `candidate(r)` + `review(r)` | `candidate(r+1)` | `candidate_saved` |
| `adopt` | 選択候補、品質判定 | 不変成果物、採用記録、後続スナップショット | `adopted` |

未採用候補の途中位置は run-state に保存しない。候補工程での中断は工程先頭から新しい呼出しとして実行し、採用済み成果物だけを `pending_commit` で収束する。

## 2. 工程表

| 工程 | 開始条件 | 内容種類 | 確認観点 | 採用後の次工程 |
|---|---|---|---|---|
| `request_intake` | キーワード入口 | 依頼 | 依頼 | `initial_design` |
| `initial_design` | 依頼採用済み | initial-design + 作品状態 | initial-design | `series_plan` |
| `series_plan` | 初期設計採用済み | series-plan | series-plan | `volume_plan` |
| `volume_plan` | 対象巻が次の未公開巻 | volume-plan | volume-plan | `chapter_plan` |
| `chapter_plan` | 対象章が次の未確定章 | chapter-plan | chapter-plan | `scene_plan` |
| `scene_plan` | 対象場面が次の未確定場面 | scene-plan | scene-plan | `scene_card` |
| `scene_card` | 場面計画採用済み | scene-card | scene-card | `scene_prose` |
| `scene_prose` | 場面カード採用済み | scene-prose | scene-prose | `scene_continuity` |
| `scene_continuity` | 場面本文採用済み | continuity-update | 継続性 | `scene_commit` |
| `scene_commit` | 更新採用済み | 場面 + 作品状態 | 決定的検証だけ | 次座標または `volume_publication` |
| `volume_publication` | 対象巻の全場面確定済み | 巻公開 | 決定的検証だけ | 次巻または `completed` |

初期設計以外の候補工程は一つの成果物種類を採用します。初期設計だけは initial-design と最初の作品状態を同じ採用記録で確定します。

## 3. 現在対象

`current_target` は工程ごとに次だけを持ちます。

| 工程 | 必須対象 |
|---|---|
| request_intake / initial_design / series_plan | 空オブジェクト |
| volume_plan | 巻番号 |
| chapter_plan | 巻番号、章番号 |
| scene_plan から scene_commit | 巻番号、章番号、場面番号 |
| volume_publication | 巻番号 |

他項目は拒否します。座標は親計画とスナップショットスロットの座標に一致しなければなりません。

## 4. 実行

`run` は `completed` または `blocked` まで確定点を連続実行し、健全で一意な保留中確定を先に収束します。`status` と `validate` は確定点を変更せず提供者を初期化しません。

## 5. 失敗と停止

| 失敗 | 記録 | 状態 |
|---|---|---|
| 形式不正**上限回数** | 対応する call-record の checks、有効候補 | `blocked`。last_error は `invalid_response_limit` |
| 技術再試行上限 | 呼出し記録群 | `blocked`。last_error は `technical_retry_exhausted` |
| 検証器の内部失敗 | run-state.last_error | `blocked`。last_error は `internal_error` |
| スナップショット参照不整合 | run-state.last_error の evidence_refs | `blocked`。last_error は `authority_inconsistency` |
| 公開検証器不合格 | run-state.last_error の evidence_refs | `blocked`。last_error は `publication_invalid` |

設定不正は `init` 前に終了コード `2` で拒否し、作業場所を作りません。停止時は有効候補と保留中確定を保持します。通常 CLI は停止中を解除せず、その作業場所は再開しません。
