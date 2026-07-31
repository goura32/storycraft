# Storycraft V1 実装状況

> この文書は確認時点の実装・検証記録であり、**仕様正本ではありません**。現在の契約は[仕様書](SPECIFICATION.md)に従います。ここに記す差分は**仕様を弱めるものではなく**、実装が仕様を満たしていない既知の箇所を時点付きで記録するものです。

## 現在の仕様との差分（2026-07-30）

この節は、仕様書と現行コードを読み合わせた記録です。以下はコード・試験・テスト用資料を変更せずに確認した差分であり、仕様を弱めるものではありません。

- V1 の規範 provider は `ollama` だけである。**差分:** 配布 console entry point は起動不能であるため、現行 `cli.py` の provider 拒否は公開 CLI の実証済み能力ではない。旧到達不能モジュールに残る provider 列挙も公開機能ではない。
- 注意付き巻公開の `publication_notice_type="編集"` と原稿冒頭の定型文は実装・試験済み。**差分:** 現行の公開 `record.json` は仕様にない参照フィールドを必須にし、仕様が拒否する `publication_notice_type: null` を受理する。閉じた公開記録スキーマと `null` 拒否は未実装である。
- 形式不正再呼出し上限到達、修正上限時の注意付き採用、品質上限で停止しない遷移は実装済み。`quality_revision_limit = 0`（無制限）時は安全上限として `invalid_response_limit` 回を超える修正は行わず、最後の形式有効版を注意付き採用して次工程へ進む。
- 指摘対象だけに修正範囲を制限せず、成果物全体の整合性・品質改善のために置き換える契約は実装済み。`validate_revision_scope` は指摘フィールドの存在確認のみを行い、修正範囲を制限しない。
- run-state は V1 仕様の schema version `3` を使用。`run_id` と `stop_reason` は保存しない。**差分:** 現行実装は仕様にない `active_candidate` と `active_scene_id` を保存し、未採用候補の再開に使う。これらの可変カーソルを廃止して、進捗を stage・target・不変 selection と健全な `pending_commit` だけで表す契約は未実装である。
- **差分:** 現行 `pending_commit` は target に仕様が廃止した `sha256` を持ち、bootstrap の `input_selection_id=null`、kind ごとの閉じた `state_update`、target 集合の完全一致を実装していない。クラッシュ収束の manifest は仕様未達である。
- **差分:** 現行 scene commit は本文・カード・更新を確定記録へ複写し、仕様が要求する ID 参照だけの `scenes/<scene-commit-id>/record.json` と品質判定参照を実装していない。
- **差分:** console script は存在しない `storycraft.cli_v2:console_main` を指すため、配布済み CLI は起動できない。現行実装の `cli.py` にある `init`、`run`、`status`、`validate` と `--workspace`／`--json` は、entry point を接続するまで公開機能ではない。さらに lock 取得失敗は現行 `70` だが、仕様は `lock_unavailable` に `75` を要求する。この終了コードと配布 entry point は未修正である。
- 正本・参照・確定物の不整合を `blocked` のまま再開せず新しい作業場所でやり直す V1 契約は実装済み。`blocked` 状態の workspace は `run` できず `RunUnavailable` を投げる。
- 現行実装の公開工程名は `volume_publication` である。旧 `publication` を使うテスト用資料は現行契約の根拠にしない。
- **差分:** `ollama_v2.py` は存在せず、現行公開経路は指定された OpenAI 互換境界を実装していない。`ollama.py` は capability の `context_length` 欠落時に `2048` を補完し、設定由来の `num_ctx` を優先するため、公開モデルの最大コンテキストを使う契約も未実装である。さらに現行設定入口は unknown field、非 loopback endpoint、userinfo/query/fragment、`[0,0]` range を受理する。これらの設定検証、`think: true`、最大コンテキスト取得、`options.num_ctx` 固定、構造化応答境界は未実装である。
- **差分:** 現行 `scene_commit` は常に `volume_publication` へ遷移する。仕様が要求する同一章の次場面、次章、巻内全場面・継続性更新の確定後の公開、前巻公開後だけの次巻計画、最終巻公開時の `completed` は未実装である。

**確認時点で全 67 テストが通過しています。**

これらは実装修正が完了した時点の記録です。実装の公開判断は、現在の仕様、実装、試験、配布物を確認して行います。
