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

`run` は健全で一意な保留中確定を収束してから完了まで実行し、停止中になった場合は終了コード `4`。停止中の `run` は終了コード `4` で変更しない。`status` と `validate` は提供者を初期化せず、状態を書き換えず、書込み lock も取得せず、残存 lock の有無も確認しない。

| コード | 意味 |
|---|---|
| 0 | `run` が完了した |
| 2 | 引数、作業場所、設定不正 |
| 4 | 停止中、または実行不能な状態 |
| 5 | validate 不合格 |
| 75 | ロック取得不能 |
| 70 | 内部エラー |

`--json` の成功時標準出力は一行オブジェクト、未知項目なし。共通項目は `workspace_id`、`status`、`current_stage`、`current_target`、`current_selection_id`、`stop_reason`、`pending_commit`。`pending_commit` は `null`、または `{ "kind": "candidate_adoption | scene_commit | volume_publication", "pending_target_count": 0, "finalized_target_count": 0 }` とする。内部 manifest のパス、ダイジェスト、target ID は出力しない。`completed` の `current_target` と `pending_commit` は `null`、その他の状態の `current_target` は run-state の値をそのまま出力する。非 JSON の成功時標準出力は人間用表示だけ。エラー時は `--json` の有無にかかわらず、標準出力は空、標準エラー出力は一行 JSON `{"ok":false,"code":"...","message":"..."}` とする。`code` は `invalid_argument`（終了コード `2`）、`blocked`（`4`）、`validation_failed`（`5`）、`internal_error`（`70`）、`lock_unavailable`（`75`）のいずれかだけを許可する。実行中に `blocked` を正常に保存できた失敗は終了コード `4` を優先し、状態保存そのものに失敗した内部エラーだけを `70` とする。

## 3. 模擬 Ollama

模擬 Ollama は HTTP サーバー。依頼はモデル、シード、system 指示文、user 指示文、応答スキーマを検査する。応答は設定した `CandidateResponse` または `ReviewResponse` を返す。試験は受信依頼の入力成果物参照とシードを記録し、確認・修正が生成入力束を保つことを検証する。

## 4. 最小受入確認

各受入は隔離した v2 作業場所、模擬 Ollama、子プロセス CLI で行う。

| 名称 | 入力 | 期待結果 |
|---|---|---|
| 依頼入口 | 依頼とキーワード | 排他、依頼採用、初期設計へ遷移 |
| 4巻完走 | 有効な模擬応答 | 各巻公開後だけ次巻、最終巻で完了 |
| 修正反復 | 重大指摘を2回返す模擬 | 確認(r) と revise(r+1) の入力系譜が一致 |
| ID 禁止 | 新規 ID を返す模擬 | 5回後停止中、採用なし |
| 未解決事項の解決 | 解決本文根拠あり／なし | ありは公開可、なしは公開不正 |
| 異常終了収束 | 各種類の一時保存／最終配置／状態組合せ | 共通収束表どおり。二重確定なし |
| 公開不変性 | 公開後に参照変更を要求 | 拒否 |
| 不整合停止 | 参照・確定物の不整合 | `blocked` のまま。通常操作で再開不可 |
| 提供者非初期化 | 停止中 / validate / status | 模擬 Ollama への依頼 0 |

各試験は期待終了コード、`status`／`validate` の標準出力 JSON、全コマンドの run-state、選択、成果物 ID を明示比較する。
