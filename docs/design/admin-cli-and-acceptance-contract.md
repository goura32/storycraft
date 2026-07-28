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

`--json` の成功時標準出力は一行オブジェクト、未知項目なし。共通項目は `workspace_id`、`status`、`current_stage`、`current_target`、`current_selection_id`、`stop_reason`、`pending_commit`。`pending_commit` は `null`、または `{ "kind": "candidate_adoption | scene_commit | volume_publication", "pending_target_count": 0, "finalized_target_count": 0, "targets": [ { "artifact_id": "string", "artifact_kind": "string", "staging_rel_path": "string", "final_path": "string", "digest": "string", "status": "staged | finalized | skipped" } ] }` とする。内部 manifest のパス、ダイジェスト、target ID は出力しない。`completed` の `current_target` と `pending_commit` は `null`、その他の状態の `current_target` は run-state の値をそのまま出力する。非 JSON の成功時標準出力は人間用表示だけ。エラー時は `--json` の有無にかかわらず、標準出力は空、標準エラー出力は一行 JSON `{"ok":false,"code":"...","message":"..."}` とする。`code` は `invalid_argument`（終了コード `2`）、`blocked`（`4`）、`validation_failed`（`5`）、`internal_error`（`70`）、`lock_unavailable`（`75`）のいずれかだけを許可する。実行中に `blocked` を正常に保存できた失敗は終了コード `4` を優先し、状態保存そのものに失敗した内部エラーだけを `70` とする。

**エラー message 形式**: `message` には JSON pointer（`#/field/subfield` 形式）または人間用短文を入れる。`init --config` 設定検証エラー時は `#/config/field` を含める。

**`status --json` 固有項目**: 共通項目に加え、`runtime_lock`（`null` または `{pid, acquired_at}`）、`run_state_path`、`manifest_path`（`pending_commit` 由来）を出力する。

**`validate --json` 固有項目**: 共通項目に加え、`checks: [ {name: string, passed: bool, detail?: string} ]` を出力する。

**`init` 成功時出力**: `--json` 指定時 `{workspace_id, status: "created", run_id, current_selection_id}`、非指定時は人間用メッセージのみ。

**`run` 完了時（exit 0）**: `--json` 指定時は `status --json` と同一形式。非指定時は人間用完了メッセージのみ。

**人間用表示フォーマット**: 各コマンド共通で `workspace: PATH / status: RUNNING|BLOCKED|COMPLETED / stage: XXX / target: YYY / selection: ZZZ` の1行要約を標準出力に書く。詳細は `status --json` を参照させる。

## 3. 模擬 Ollama

模擬 Ollama は HTTP サーバー。依頼はモデル、シード、system 指示文、user 指示文、応答スキーマを検査する。応答は設定した `CandidateResponse` または `ReviewResponse` を返す。試験は受信依頼の入力成果物参照とシードを記録し、確認・修正が生成入力束を保つことを検証する。

### 3.1 模擬 Ollama インターフェース

```python
class MockOllama:
    def __init__(self):
        self.received_requests = []

    def generate(self, request: dict) -> dict:
        """request: {model, seed, system, prompt, format, options}"""
        self.received_requests.append(request)
        return self._next_response()

    def _next_response(self) -> dict:
        # configured CandidateResponse or ReviewResponse
        pass
```

### 3.2 設定ファイル完全定義

`init --config FILE` が受け付ける設定 JSON の完全スキーマ:

```json
{
  "provider": "ollama",
  "endpoint": "http://127.0.0.1:11434",
  "model": "string (non-empty)",
  "technical_retry_limit": 3,
  "quality_revision_limit": 3,
  "volume_chapter_range": [1, 20],
  "chapter_scene_range": [1, 20],
  "scene_text_char_range": [1000, 12000],
  "max_input_chars": 200000
}
```

すべて必須。未知項目・型不一致・range順序違反・max_input_chars下限違反で `init` は終了コード 2。

### 3.3 受入テストシナリオ詳細 (9シナリオ)

| # | 名称 | 入力データ | 期待出力 | 検証手順 |
|---|------|-----------|---------|---------|
| 1 | 依頼入口 | 依頼JSON / キーワードJSON | 排他、依頼採用、初期設計へ遷移 | `--request` と `--keywords` 同時指定でexit 2。片方のみで `request` 成果物確定、`current_stage=initial-design` |
| 2 | 4巻完走 | 有効模擬応答 | 各巻公開後だけ次巻、最終巻で完了 | 4巻分の scene_commit → volume_publication → volume_plan 遷移。最終巻で `completed` |
| 3 | 品質上限到達 | 重大指摘を含む模擬応答 (6回目) | 最後の形式有効版を注意付き採用 | `quality_revision_limit=2` で3回重大指摘 → `accepted_with_notice`、品質判定に `notice_type=edit` |
| 4 | 形式不正5回到達 | 解析失敗応答 × 5 | `blocked/manual_review_required` | 5回連続 `valid=false` → exit 4, `stop_reason=manual_review_required` |
| 5 | 技術的再試行上限 | 接続失続 × N+1 | `blocked/manual_review_required` | `technical_retry_limit=2` で3回失敗 → exit 4 |
| 6 | max_input_chars超過 | 長大プロンプト構築 | `internal_error` 即座停止 | プロンプト結合サイズ > max_input_chars で LLM未呼出、exit 70 |
| 7 | 中断収束 | 途中 kill した作業場所で run | 健全pendingのみ収束、続行 | `scene_commit` staging残存 → `run` でmanifest検証→コミット→次scene_plan |
| 8 | 巻公開決定的検証 | 公開注意あり/なし | 原稿冒頭に定型文/なし | `quality-...` に重大指摘あり → `publication_notice_type=edit`、冒頭に「編集上の注意があります。」 |
| 9 | validate 包括検証 | 正常作業場所 | `checks` 全 passed | `validate --json` で schema/id/ref/range/evidence 全チェック passed |

### 3.4 模擬 Ollama 応答シーケンス制御

```json
{
  "sequences": [
    {"stage": "initial-design.generate", "responses": ["gen-1", "gen-2"]},
    {"stage": "initial-design.review", "responses": ["review-1"]}
  ]
}
```
| 修正反復 | 重大指摘を2回返す模擬 | 確認(r) と revise(r+1) の入力系譜が一致 |
| ID 禁止 | 新規 ID を返す模擬 | 5回後停止中、採用なし |
| 未解決事項の解決 | 解決本文根拠あり／なし | ありは公開可、なしは公開不正 |
| 異常終了収束 | 各種類の一時保存／最終配置／状態組合せ | 共通収束表どおり。二重確定なし |
| 公開不変性 | 公開後に参照変更を要求 | 拒否 |
| 不整合停止 | 参照・確定物の不整合 | `blocked` のまま。通常操作で再開不可 |
| 提供者非初期化 | 停止中 / validate / status | 模擬 Ollama への依頼 0 |

各試験は期待終了コード、`status`／`validate` の標準出力 JSON、全コマンドの run-state、選択、成果物 ID を明示比較する。
