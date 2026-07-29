# 通常 CLI と受入確認の契約

## 1. 失敗時の扱い

V1 は一人だけが一つのローカル作業場所を扱う。正本、参照、確定物、一時保存の不整合を検出した作業場所は `blocked` のままとし、復旧・参照選び直し・直接編集による再開を行わない。利用者は `status` と `validate` で診断を確認し、必要なら新しい作業場所を作る。

`run` は `blocked` を解除しない。`status` と `validate` だけが停止中に許可され、状態を変更しない。

## 2. 通常 CLI

```text
storycraft init --workspace PATH (--request FILE | --keywords FILE) --config FILE
storycraft run --workspace PATH
storycraft status --workspace PATH --json
storycraft validate --workspace PATH --json
```

`init` は作業場所が存在しないときだけ作成する。既存なら終了コード `2` で変更しない。`--request` と `--keywords` は排他。設定は Ollama 専用で、設定不正なら作業場所を作らず終了コード `2` にする。

`run` は健全で一意な保留中確定を収束してから完了まで実行し、停止中になった場合は終了コード `4`。停止中の `run` は終了コード `4` で変更しない。`status` と `validate` は提供者を初期化せず、状態を書き換えず、書込み lock を取得・読取・削除しない。

|| コード | 意味 |
||---|---|
|| 0 | `run` が完了した |
|| 2 | 引数、作業場所、設定不正 |
|| 4 | 停止中、または実行不能な状態 |
|| 5 | validate 不合格 |
|| 75 | ロック取得不能 |
|| 70 | 内部エラー |

`--json` の成功時標準出力は一行オブジェクト、未知項目なし。これは run-state の公開用射影であり、内部 run-state や manifest をそのまま出力しない。共通項目は `workspace_id`、`status`、`current_stage`、`current_target`、`current_selection_id`、`stop_reason`、`pending_commit`。`pending_commit` は `null`、または `{ "kind": "candidate_adoption | scene_commit | volume_publication", "pending_target_count": 0, "finalized_target_count": 0 }` とする。内部 manifest のパス、ダイジェスト、target ID、staging 相対パス、最終パスは出力しない。`completed` の `current_target` と `pending_commit` は `null`、その他の状態の `current_target` は run-state の値をそのまま出力する。非 JSON の成功時標準出力は人間用表示だけ。エラー時は `--json` の有無にかかわらず、標準出力は空、標準エラー出力は一行 JSON `{"ok":false,"code":"...","message":"..."}` とする。`code` は `invalid_argument`（終了コード `2`）、`blocked`（`4`）、`validation_failed`（`5`）、`internal_error`（`70`）、`lock_unavailable`（`75`）、`invalid_response_limit`（`4`）、`technical_retry_exhausted`（`4`）、`authority_inconsistency`（`4`）、`publication_invalid`（`4`）のいずれかだけを許可する。実行中に `blocked` を正常に保存できた失敗は終了コード `4` を優先し、状態保存そのものに失敗した内部エラーだけを `70` とする。

**エラー message 形式**: `message` には JSON pointer（`#/field/subfield` 形式）または人間用短文を入れる。`init --config` 設定検証エラー時は `#/config/field` を含める。

**`status --json` 固有項目**: 共通項目だけを出力する。内部パスとロック内部情報は出力しない。

**`validate --json` 固有項目**: 共通項目に加え、`checks: [ {name: string, passed: bool, detail?: string} ]` を出力する。

**`init` 成功時出力**: `--json` 指定時 `{workspace_id, status: "created", run_id, current_selection_id}`、非指定時は人間用メッセージのみ。

**`run` 完了時（exit 0）**: `--json` 指定時は `status --json` と同一形式。非指定時は人間用完了メッセージのみ。

**人間用表示フォーマット**: `status`、`validate`、`run` は `workspace: PATH / status: running|blocked|completed / stage: XXX / target: YYY / selection: ZZZ` の1行要約を標準出力に書く。`init` は作成完了メッセージのみを出す。詳細は `status --json` を参照させる。

## 3. 模擬 Ollama と受入試験（仕様レベル）

模擬 Ollama は HTTP サーバー。依頼はモデル、シード、Thinking有効化、モデル最大値の `options.num_ctx`、system 指示文、user 指示文、応答スキーマを検査する。応答は設定した `CandidateResponse` または `ReviewResponse` を返す。試験は受信依頼の入力成果物参照とシードを記録し、確認・修正が生成入力束を保つことを検証する。設定で明示されない温度等の `options` が送られないことも検証する。

**模擬 Ollama 契約**: OpenAI 互換の Ollama `/v1/chat/completions` エンドポイントを提供し、モデル最大コンテキスト長を返す OpenAI 互換のモデル情報応答も提供する。`messages`、`think: true`、シード、`options.num_ctx`、JSON Schema の `response_format` を検査し、`choices[0].message.content` に応答を返す。温度等は設定で指定された場合だけ検査する。実装クラス・メソッドシグネチャはコード側で定義。

**設定検証契約**: `init --config FILE` は JSON がスキーマ（§3.1）と範囲制約に従うかのみ検査。provider/endpoint/model/技術的再試行上限/品質修正上限/各rangeが必須で、`request_options` は任意。未知項目・型不一致・range順序違反で終了コード 2。**provider は `ollama` 固定。endpoint は OpenAI 互換 API を提供する loopback HTTP のみ許可（`127.0.0.0/8`、`::1`、`localhost` 解決先）。invalid_response_limit は形式不正再呼出しの上限回数（1以上の整数）。**

**受入試験シナリオ（10件、仕様レベル）**:

| # | 名称 | 目的 | 成功基準 |
|---|------|------|----------|
| 1 | 依頼入口 | 依頼・キーワード排他・依頼採用 | `--request` と `--keywords` 同時指定で exit 2。片方のみで `request` 成果物確定、`current_stage=initial_design` |
| 2 | 4巻完走 | 全工程正常遷移 | 各巻公開後だけ次巻、最終巻で `completed` |
| 3 | 品質上限到達 | 重大指摘上限到達時の注意付き採用 | `quality_revision_limit=2` で3回重大指摘 → `accepted_with_notice`、品質判定に `notice_type=編集` |
| 4 | 品質無制限時の修正安全上限 | 最後の形式有効候補がある場合の注意付き採用 | `quality_revision_limit=0`、有効候補への修正が `invalid_response_limit=2` 回連続で形式不正 → 直前の有効候補を `accepted_with_notice` として採用 |
| 5 | 形式不正上限到達 | 形式不正**上限回数**の停止 | 初回から**上限回数**連続 `valid=false` → exit 4, `stop_reason=manual_review_required` |
| 6 | 技術的再試行上限 | 技術的失敗上限到達の停止 | `technical_retry_limit=2` で3回失敗 → exit 4 |
| 7 | 最大コンテキスト超過 | 提供者のコンテキスト超過を技術的失敗として扱う | 指定モデルの最大コンテキスト超過を返す → 技術的再試行、上限到達で exit 4 |
| 8 | 中断収束 | 異常終了後の健全pending収束 | `scene_commit` staging残存 → `run` でmanifest検証→確定→次scene_plan |
| 9 | 巻公開決定的検証 | 公開注意あり/なしの原稿出力分岐 | 重大指摘あり → `publication_notice_type=編集`、冒頭に定型文 |
| 10 | validate 包括検証 | 全検証項目 passed | `validate --json` で schema/id/ref/range/evidence 全チェック passed |

**試験共通検証項目**: 期待終了コード、`status`/`validate` 標準出力 JSON、run-state、選択スナップショット、成果物 ID の明示比較。模擬 Ollama への依頼が停止中にゼロであること。
