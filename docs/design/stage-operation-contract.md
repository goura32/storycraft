# stage operation と checkpoint

## 1. 共通 operation

各 candidate stage は次の operation を持ちます。

| operation | 入力 | 出力 | checkpoint |
|---|---|---|---|
| `generate` | generation context | `candidate(0)` | `candidate_saved` |
| `review(r)` | generation context + `candidate(r)` | `ReviewResponse` | `review_saved` |
| `revise(r+1)` | generation context + `candidate(r)` + `review(r)` | `candidate(r+1)` | `candidate_saved` |
| `adopt` | 選択 candidate、quality disposition | immutable artifact、adoption、successor snapshot | `adopted` |

`active_candidate` は candidate record ID、反復番号、generation context の artifact refs、直前 review record ID を持つ。候補・review が保存済みなら、`resume` は Provider を呼ばず次の未実行 operation から再開します。

## 2. stage 表

| stage | 開始条件 | payload kind | review profile | 採用後の next stage |
|---|---|---|---|---|
| `request_intake` | keyword 入口 | request | request | `initial_design` |
| `initial_design` | request 採用済み | initial-design + generation | initial-design | `series_plan` |
| `series_plan` | initial design 採用済み | series-plan | series-plan | `volume_plan` |
| `volume_plan` | 対象巻が次の未公開巻 | volume-plan | volume-plan | `chapter_plan` |
| `chapter_plan` | 対象章が次の未確定章 | chapter-plan | chapter-plan | `scene_plan` |
| `scene_plan` | 対象場面が次の未確定場面 | scene-plan | scene-plan | `scene_card` |
| `scene_card` | scene plan 採用済み | scene-card | scene-card | `scene_prose` |
| `scene_prose` | scene card 採用済み | scene-prose | scene-prose | `scene_continuity` |
| `scene_continuity` | scene prose 採用済み | continuity-update | continuity | `scene_commit` |
| `scene_commit` | update 採用済み | scene + generation | 決定的検証だけ | 次座標または `volume_publication` |
| `volume_publication` | 対象巻の全 scene commit 済み | volume publication | 決定的検証だけ | 次巻または `completed` |

初期設計以外の candidate stage は一つの artifact kind を採用します。初期設計だけは initial-design と最初の generation を同じ adoption で確定します。

## 3. current target

`current_target` は stage ごとに次だけを持ちます。

| stage | 必須 target |
|---|---|
| request_intake / initial_design / series_plan | 空 object |
| volume_plan | volume number |
| chapter_plan | volume number、chapter number |
| scene_plan から scene_commit | volume number、chapter number、scene number |
| volume_publication | volume number |

他 field は拒否します。座標は親 plan と snapshot slot の座標に一致しなければなりません。

## 4. step と resume

`step` は current stage の次の一つの durable checkpoint まで進みます。checkpoint は candidate 保存、review 保存、adoption 確定、scene commit 確定、volume publication 確定です。

`run` は `completed` または `blocked` まで checkpoint を連続実行します。`resume` は pending commit を先に収束し、その後 `run` と同じです。`status` と `validate` は checkpoint を変更せず Provider を初期化しません。

## 5. failure と停止

| 失敗 | 記録 | 状態 |
|---|---|---|
| 形式不正5回 | validation records、active candidate | `blocked`。`stop_reason=manual_review_required`、blocked-state cause=`invalid_response_limit` |
| 技術再試行上限 | call records | `blocked`。`stop_reason=manual_review_required`、blocked-state cause=`technical_retry_exhausted` |
| 設定不正 | validation record | `blocked`。`stop_reason=manual_review_required`、blocked-state cause=`provider_configuration_invalid` |
| validator の内部失敗 | error record | `blocked`。`stop_reason=manual_review_required`、blocked-state cause=`internal_error` |
| snapshot 参照不整合 | validation record | `blocked`。`stop_reason=manual_review_required`、blocked-state cause=`authority_reference_inconsistency` |
| 公開 validator 不合格 | validation record | `blocked`。`stop_reason=manual_review_required`、blocked-state cause=`volume_publication_invalid` |

停止時は blocked-state を確定し、active candidate と pending commit を保持します。通常 CLI は blocked を解除できません。
