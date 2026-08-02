# Storycraft V1 実装状況

> この文書は確認時点の実装・検証記録であり、**仕様正本ではありません**。現在の契約は[仕様書](SPECIFICATION.md)に従います。ここに記す差分は**仕様を弱めるものではなく**、実装が仕様を満たしていない既知の箇所を時点付きで記録するものです。

## 現在の仕様との差分（2026-08-02）

この節は、仕様書と現行コードを読み合わせた記録です。以下はコード・試験・テスト用資料を変更せずに確認した差分であり、仕様を弱めるものではありません。

- V1 の規範 provider は `ollama` だけである。
- planning成果物（series-plan、volume-plan、chapter-plan）は正本JSON Schemaのmodern形式を使用し、旧 `volumes` / `chapters` / `scenes` / `thread_allocations` payloadは採用しない。
- series planは4〜10巻、`volume_summaries`はseriesの巻数と一致する。巻・章・場面の座標はartifact envelopeとselection slotで管理し、planning payloadへ重複保存しない。
- 注意付き巻公開の `publication_notice_type="編集"` と原稿冒頭の定型文は実装・試験済み。公開 `record.json` は閉じたスキーマで、`publication_notice_type: null` は拒否される。
- 形式不正再呼出し上限到達、修正上限時の注意付き採用、品質上限で停止しない遷移は実装済み。`quality_revision_limit = 0`（無制限）時は、形式有効な品質修正を上限なしで継続し、形式不正の再呼出しだけを `invalid_response_limit` で制限する。
- 指摘対象だけに修正範囲を制限せず、成果物全体の整合性・品質改善のために置き換える契約は実装済み。`validate_revision_scope` は指摘フィールドの存在確認のみを行い、修正範囲を制限しない。
- run-state は V1仕様の schema version `3` を使用。`run_id` と `stop_reason` は保存しない。`active_candidate` と `active_scene_id` は廃止済み。進捗を stage・target・不変 selectionと健全な `pending_commit` だけで表す契約を満たす。
- `pending_commit` は仕様通りの閉じた構造で、`sha256` を持たず、bootstrapの`input_selection_id=null`、kindごとの閉じた`state_update`、target集合の完全一致を実装。クラッシュ収束のmanifestは仕様達成済み。
- scene commitは本文・カード・更新を複写せず、仕様通りID参照だけの`scenes/<scene-commit-id>/record.json`と品質判定参照を実装。
- console scriptは`storycraft.cli:console_main`を指し、配布CLIは起動可能。lock取得失敗は仕様通り`75`で返す。
- 正本・参照・確定物の不整合を`blocked`のまま再開せず新しい作業場所でやり直すV1契約は実装済み。`blocked`状態のworkspaceは`run`できず`RunUnavailable`を投げる。
- 現行実装の公開工程名は`volume_publication`である。旧`publication`を使うテスト用資料は現行契約の根拠にしない。
- `ollama.py`は指定されたOpenAI互換境界を実装。モデル能力の`context_length`を取得し、`options.num_ctx`に反映し、`think: true`、`stream: false`、`response_format: json_schema`を使用。設定検証でunknown field、公開・link-local endpoint、userinfo/query/fragment、`[0,0]` rangeを拒否し、loopbackまたはプライベートLAN endpointを許可。
- `scene_commit`は仕様通り同一章の次場面、次章、巻内全場面・継続性更新の確定後の公開、前巻公開後だけの次巻計画、最終巻公開時の`completed`を実装。

**確認時点で146テスト、74 subtestsが通過しています。**

これらは実装修正が完了した時点の記録です。実装の公開判断は、現在の仕様、実装、試験、配布物を確認して行います。
