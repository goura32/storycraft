# 工程処理と確定点

## 1. 共通処理

各候補工程は次の処理を持ちます。

| 処理 | 入力 | 出力 | 確定点 |
|---|---|---|---|
| `generate` | 生成入力束 | `candidate(0)` | `candidate_saved` |
| `review(r)` | 生成入力束 + `candidate(r)` | `ReviewResponse` | `review_saved` |
| `revise(r+1)` | 生成入力束 + `candidate(r)` + `review(r)` | `candidate(r+1)` | `candidate_saved` |
| `adopt` | 選択候補、品質判定 | 不変成果物、採用記録、後続スナップショット | `adopted` |

`active_candidate` は候補記録 ID、反復番号、生成入力束の成果物参照、直前確認記録 ID を持つ。候補・確認が保存済みなら、`resume` は提供者を呼ばず次の未実行処理から再開します。

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

## 4. step と resume

`step` は現在工程の次の一つの永続的な確定点まで進みます。確定点は候補保存、確認保存、採用記録確定、場面確定確定、巻公開確定です。

`run` は `completed` または `blocked` まで確定点を連続実行します。`resume` は保留中確定を先に収束し、その後 `run` と同じです。`status` と `validate` は確定点を変更せず提供者を初期化しません。

## 5. 失敗と停止

| 失敗 | 記録 | 状態 |
|---|---|---|
| 形式不正5回 | 検証記録群、有効候補 | `blocked`。`stop_reason=manual_review_required`、blocked-state 原因=`invalid_response_limit` |
| 技術再試行上限 | 呼出し記録群 | `blocked`。`stop_reason=manual_review_required`、blocked-state 原因=`technical_retry_exhausted` |
| 設定不正 | 検証記録 | `blocked`。`stop_reason=manual_review_required`、blocked-state 原因=`provider_configuration_invalid` |
| 検証器の内部失敗 | エラー記録 | `blocked`。`stop_reason=manual_review_required`、blocked-state 原因=`internal_error` |
| スナップショット参照不整合 | 検証記録 | `blocked`。`stop_reason=manual_review_required`、blocked-state 原因=`authority_reference_inconsistency` |
| 公開検証器不合格 | 検証記録 | `blocked`。`stop_reason=manual_review_required`、blocked-state 原因=`volume_publication_invalid` |

停止時は blocked-state を確定し、有効候補と保留中確定を保持します。通常 CLI は停止中を解除できません。
