# 管理 API、CLI、受入確認の契約

## 1. 管理 server

管理 server は workspace 外の Unix domain socket を一つ使います。socket path、allowlist path、Ed25519 private key は `storycraft-admin` の設定だけが読む。通常の `storycraft` は socket path と鍵を受け取らない。grant の署名対象は、`version`、`grant_id`、`operator_id`、`workspace_id`、`blocked_state_id`、`cause`、`issued_at`、`expires_at` をキー昇順・空白なし UTF-8 JSON にした bytes です。public key は admin 設定にあり、workspace は署名と canonical bytes を検証します。

request は UTF-8 JSON、1行、未知 field 拒否です。

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

server は peer UID が allowlist にあり、blocked state が存在し、cause が一致するときだけ grant を返します。

```json
{
  "version": 1,
  "ok": true,
  "grant_id": "grant-...",
  "expires_at": "UTC 時刻",
  "signature": "base64url"
}
```

grant は一回だけ使えます。server は grant ID、workspace、blocked state、cause、失効、状態（`issued|reserved|consumed`）を immutable ledger に保存します。workspace は resolution staging を検証した後、server の `reserve_grant` を呼びます。server は未失効の `issued` grant だけを同じ grant ID・workspace・blocked state・cause で `reserved` にします。workspace が resolution record と successor selection を final 確定し、run-state を更新した後に `consume_grant` を呼びます。consume は同じ reservation token の `reserved` grant だけを `consumed` にする原子的操作です。

crash recovery は resolution record と successor selection が有効で run-state 更新済みなら、同じ reservation token で consume を再試行します。final 確定前なら server に `release_grant` を要求して `issued` へ戻し、workspace は blocked を維持します。期限切れ、使用済み、署名不正、UID 不一致、reservation token 不一致は拒否します。

## 2. storycraft-admin

```text
storycraft-admin register-resolution --workspace PATH --record FILE
```

`record` は cause、subject refs、evidence refs、selected authority refs、recovery stage、recovery target、rationale を持つ JSON です。CLI は server から grant を取得し、workspace lock を取り、resolution application を確定します。

exit code:

| code | 意味 |
|---|---|
| 0 | 成功 |
| 2 | 引数または入力 JSON 不正 |
| 3 | grant 拒否 |
| 4 | blocked state または recovery 契約不一致 |
| 75 | lock 取得不能 |
| 70 | 内部エラー |

成功時 stdout は `{"ok":true,"resolution_id":"..."}` の一行です。失敗時 stdout は空、stderr は一行 JSON です。

## 3. 通常 CLI

```text
storycraft run --workspace PATH
storycraft resume --workspace PATH
storycraft step --workspace PATH
storycraft status --workspace PATH --json
storycraft validate --workspace PATH --json
storycraft init --workspace PATH (--request FILE | --keywords FILE) --config FILE
```

`init` は workspace が存在しないときだけ作成します。既存なら exit code `2` で変更しません。`--request` と `--keywords` は排他です。config は Ollama 専用設定です。

`run` は completed まで実行し、実行中に blocked になった場合は exit code `4` を返します。`resume` は pending commit を収束してから run と同じです。`step` は一つの durable checkpoint だけ進めます。blocked の `run`、`resume`、`step` は exit code `4` で変更しません。`status` と `validate` は Provider を初期化しません。

exit code:

| code | 意味 |
|---|---|
| 0 | 成功。`run` が completed、または `step` が checkpoint に到達 |
| 2 | 引数、workspace、config 不正 |
| 4 | blocked、または実行不能な状態 |
| 5 | validate 不合格 |
| 75 | lock 取得不能 |
| 70 | 内部エラー |

`--json` の stdout は一行 object、未知 field なしです。共通 field は `workspace_id`、`status`、`current_stage`、`current_target`、`current_selection_id`、`stop_reason`、`pending_commit`。非 JSON の stdout は人間用表示だけです。stderr は error object 一行です。

## 4. fake Ollama

fake Ollama は HTTP server です。request は model、seed、system prompt、user prompt、response schema を検査します。応答は設定した `CandidateResponse` または `ReviewResponse` を返します。test は受信 request の入力 artifact refs と seed を記録し、確認・修正が generation context を保つことを検証します。

## 5. 最小受入確認

各受入は隔離 v2 workspace、fake Ollama、subprocess CLI で行います。

| 名称 | 入力 | 期待結果 |
|---|---|---|
| request 入口 | request と keywords | 排他、request 採用、initial design へ遷移 |
| 4巻完走 | 有効な fake 応答 | 各巻公開後だけ次巻、最終巻で completed |
| 修正反復 | 重大 issue を2回返す fake | review(r) と revise(r+1) の入力系譜が一致 |
| ID 禁止 | 新規 ID を返す fake | 5回後 blocked、採用なし |
| thread 解決 | resolve 本文根拠あり／なし | ありは公開可、なしは publication invalid |
| crash 収束 | 各 kind の staging/final/state 組合せ | 共通収束表どおり。二重確定なし |
| 公開不変性 | 公開後に参照変更を要求 | 拒否 |
| admin 復旧 | fake authorizer の grant | 有効 grant だけ running へ戻る |
| Provider 非初期化 | blocked / validate / status | fake Ollama への request 0 |

各 test は期待 exit code、stdout JSON、run-state、selection、artifact ID を明示比較します。
