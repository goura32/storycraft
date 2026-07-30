# Storycraft V1 実装状況

> この文書は確認時点の実装・検証記録であり、**仕様正本ではありません**。現在の契約は[仕様書](SPECIFICATION.md)に従います。ここに記す差分は**仕様を弱めるものではなく**、実装が仕様を満たしていない既知の箇所を時点付きで記録するものです。

## 現在の仕様との差分（2026-07-30）

この節は、仕様書と現行コードを読み合わせた記録です。以下はコード・試験・テスト用資料を変更せずに確認した差分であり、仕様を弱めるものではありません。

- V1 はローカル LLM 専用であり、公開 v2 CLI も `ollama` 以外の provider を `init` で拒否する。旧到達不能モジュールに残る provider 列挙は公開CLIの機能ではない。
- 注意付き巻公開の `publication_notice_type="編集"` と原稿冒頭の定型文は実装・試験済み。品質判定の全件参照とV1の選択スナップショット整合を含む公開契約全体は実装・試験済み。
- 形式不正再呼出し上限到達、修正上限時の注意付き採用、品質上限で停止しない遷移は実装済み。`quality_revision_limit = 0`（無制限）時は安全上限として `invalid_response_limit` 回を超える修正は行わず、最後の形式有効版を注意付き採用して次工程へ進む。
- 指摘対象だけに修正範囲を制限せず、成果物全体の整合性・品質改善のために置き換える契約は実装済み。`validate_revision_scope` は指摘フィールドの存在確認のみを行い、修正範囲を制限しない。
- run-state は V1 仕様の schema version `3` を使用。不要な `run_id`、`stop_reason`、未採用候補の再開情報は保存しない。停止診断は `last_error`、採用済み確定途中だけは `pending_commit` で表す。
- v2 CLI は `init`、`run`、`status`、`validate` と `--workspace`／`--json` を公開する。`init --json` は `workspace_id`、`status=created`、`current_selection_id` のみを出力（`run_id` なし）。`validate --json` は必須の `schema`、`id`、`reference`、`range`、`evidence` の固定5検査を返す。`status --json` は内部情報を隠す V1 の公開用 JSON 射影に準拠。lock 取得失敗の stderr `code` は `lock_unavailable`、終了コード `70`。診断別終了コード `2|4|5|70` を実装。
- 正本・参照・確定物の不整合を `blocked` のまま再開せず新しい作業場所でやり直す V1 契約は実装済み。`blocked` 状態の workspace は `run` できず `RunUnavailable` を投げる。
- 現行実装の公開工程名は `volume_publication` である。旧 `publication` を使うテスト用資料は現行契約の根拠にしない。
- OpenAI互換Ollamaの `/v1/chat/completions`、`messages`、構造化 `response_format`、および `choices[0].message.content` の抽出は実装済み。`GET /v1/models/{model}` による最大コンテキスト取得、`think: true`、`options.num_ctx`、未指定 `request_options` を送らずOllama既定値を使う契約は実装済み（`ollama_v2.py`）。`init` は V1 にない必須 `max_input_chars` を要求せず、V1 で任意の `request_options` を受け入れる。
- 巻の引継ぎを作らず、各巻の全場面と継続性更新の確定後に同じ巻単位で公開準備・確定と巻公開用原稿作成を行い、最終巻公開で完了する遷移は実装済み（`volume_publication_stage.py`, `VolumePublicationStageService`）。次の巻へは前巻の公開済み後にのみ進み、最終巻公開で `completed` となる。

**全 66 テストが通過しています。**

これらは実装修正が完了した時点の記録です。実装の公開判断は、現在の仕様、実装、試験、配布物を確認して行います。