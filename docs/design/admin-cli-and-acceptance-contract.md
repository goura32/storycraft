# 管理 API、CLI、受入確認の契約

## 1. 管理サーバー

管理サーバーは作業場所外の Unix domain ソケットを一つ使います。ソケットパス、許可一覧パス、Ed25519 秘密鍵は `storycraft-admin` の設定だけが読む。通常の `storycraft` はソケットパスと鍵を受け取らない。許可証の署名対象は、`version`、`grant_id`、`operator_id`、`workspace_id`、`blocked_state_id`、`cause`、`issued_at`、`expires_at` をキー昇順・空白なし UTF-8 JSON にしたバイト列です。公開鍵は管理設定にあり、作業場所は署名と正規形バイト列を検証します。

依頼は UTF-8 JSON、1行、未知項目拒否です。

```json
{
  "version": 1,
  "command": "grant_resolution",
  "workspace_id": "ws-...",
  "blocked_state_id": "blocked-state-...",
  "cause": "固定 enum",
  "operator_id": "..."
}
```

サーバーは接続元 UID が許可一覧にあり、停止状態が存在し、原因が一致するときだけ許可証を返します。

```json
{
  "version": 1,
  "ok": true,
  "grant_id": "grant-...",
  "expires_at": "UTC 時刻",
  "signature": "base64url"
}
```

許可証は一回だけ使えます。サーバーは許可証ID、作業場所、停止状態、原因、失効、状態（`issued|reserved|consumed`）を不変台帳に保存します。作業場所は解決処理の一時保存を検証した後、サーバーの `reserve_grant` を呼びます。サーバーは未失効の `issued` 許可証だけを同じ許可証ID・作業場所・停止状態・原因で `reserved` にします。作業場所が解決記録と後続選択を最終配置確定し、run-state を更新した後に `consume_grant` を呼びます。消費は同じ予約トークンの `reserved` 許可証だけを `consumed` にする原子的操作です。

異常終了復旧は解決記録と後続選択が有効で run-state 更新済みなら、同じ予約トークンで消費を再試行します。最終配置確定前ならサーバーに `release_grant` を要求して `issued` へ戻し、作業場所は停止中を維持します。期限切れ、使用済み、署名不正、UID 不一致、予約トークン不一致は拒否します。

## 2. storycraft-admin

```text
storycraft-admin register-resolution --workspace PATH --record FILE
```

`record` は原因、対象参照、根拠参照、選択した正本参照、復旧工程、復旧対象、理由を持つ JSON です。CLI はサーバーから許可証を取得し、作業場所ロックを取り、解決適用を確定します。

終了コード:

| コード | 意味 |
|---|---|
| 0 | 成功 |
| 2 | 引数または入力 JSON 不正 |
| 3 | 許可証拒否 |
| 4 | 停止状態または復旧契約不一致 |
| 75 | ロック取得不能 |
| 70 | 内部エラー |

成功時標準出力は `{"ok":true,"resolution_id":"..."}` の一行です。失敗時標準出力は空、標準エラー出力は一行 JSON です。

## 3. 通常 CLI

```text
storycraft run --workspace PATH
storycraft resume --workspace PATH
storycraft step --workspace PATH
storycraft status --workspace PATH --json
storycraft validate --workspace PATH --json
storycraft init --workspace PATH (--request FILE | --keywords FILE) --config FILE
```

`init` は作業場所が存在しないときだけ作成します。既存なら終了コード `2` で変更しません。`--request` と `--keywords` は排他です。設定は Ollama 専用設定です。

`run` は完了まで実行し、実行中に停止中になった場合は終了コード `4` を返します。`resume` は保留中確定を収束してから run と同じです。`step` は一つの永続的な確定点だけ進めます。停止中の `run`、`resume`、`step` は終了コード `4` で変更しません。`status` と `validate` は提供者を初期化しません。

終了コード:

| コード | 意味 |
|---|---|
| 0 | 成功。`run` が完了、または `step` が確定点に到達 |
| 2 | 引数、作業場所、設定不正 |
| 4 | 停止中、または実行不能な状態 |
| 5 | validate 不合格 |
| 75 | ロック取得不能 |
| 70 | 内部エラー |

`--json` の標準出力は一行オブジェクト、未知項目なしです。共通項目は `workspace_id`、`status`、`current_stage`、`current_target`、`current_selection_id`、`stop_reason`、`pending_commit`。非 JSON の標準出力は人間用表示だけです。標準エラー出力はエラーオブジェクト一行です。

## 4. 模擬 Ollama

模擬 Ollama は HTTP サーバーです。依頼はモデル、シード、system 指示文、user 指示文、応答スキーマを検査します。応答は設定した `CandidateResponse` または `ReviewResponse` を返します。試験は受信依頼の入力成果物参照とシードを記録し、確認・修正が生成入力束を保つことを検証します。

## 5. 最小受入確認

各受入は隔離した v2 作業場所、模擬 Ollama、子プロセス CLI で行います。

| 名称 | 入力 | 期待結果 |
|---|---|---|
| 依頼入口 | 依頼とキーワード | 排他、依頼採用、初期設計へ遷移 |
| 4巻完走 | 有効な模擬応答 | 各巻公開後だけ次巻、最終巻で完了 |
| 修正反復 | 重大指摘を2回返す模擬 | 確認(r) と revise(r+1) の入力系譜が一致 |
| ID 禁止 | 新規 ID を返す模擬 | 5回後停止中、採用なし |
| 未解決事項の解決 | 解決本文根拠あり／なし | ありは公開可、なしは公開不正 |
| 異常終了収束 | 各種類の一時保存／最終配置／状態組合せ | 共通収束表どおり。二重確定なし |
| 公開不変性 | 公開後に参照変更を要求 | 拒否 |
| 管理復旧 | 模擬認可器の許可証 | 有効な許可証だけ実行中へ戻る |
| 提供者非初期化 | 停止中 / validate / status | 模擬 Ollama への依頼 0 |

各試験は期待終了コード、標準出力JSON、run-state、選択、成果物 ID を明示比較します。
