# Storycraft V1 実装状況

> この文書は確認時点の実装・検証記録であり、**仕様正本ではありません**。現在の契約は[仕様書](SPECIFICATION.md)に従います。ここに記す差分は**仕様を弱めるものではなく**、実装が仕様を満たしていない既知の箇所を時点付きで記録するものです。

## 現在の仕様との差分（2026-08-04）

この節は、仕様書と現行コードを読み合わせた記録です。以下は確認時点のコード・試験・テスト用資料との差分であり、仕様を弱めるものではありません。

- V1 の規範 provider は `ollama` だけである。
- planning成果物（series-plan、volume-plan、chapter-plan）は正本JSON Schemaのmodern形式を使用し、旧 `volumes` / `chapters` / `scenes` / `thread_allocations` payloadは採用しない。
- 旧設計の `thread_id`、`action`、`required_conditions` を持つ別個のallocation payloadは採用しない。現行modern planning payloadの `thread_progression`、`thread_goals`、`required_revelations`、`ending_changes`、`intended_revelations`、`intended_changes` をselection lineageと親計画の束縛で検証する。
- series planは4〜10巻、`volume_summaries`はseriesの巻数と一致する。巻・章・場面の座標はartifact envelopeとselection slotで管理し、planning payloadへ重複保存しない。
- 注意付き巻公開の `publication_notice_type="編集"` と原稿冒頭の定型文は実装・試験済み。公開 `record.json` は閉じたスキーマで、`publication_notice_type: null` は拒否される。
- 形式不正再呼出し上限到達、修正上限時の注意付き採用、品質上限で停止しない遷移は実装済み。`quality_revision_limit = 0`（無制限）時は、形式有効な品質修正を上限なしで継続し、形式不正の再呼出しだけを `invalid_response_limit` で制限する。正の品質上限で改稿応答が形式不正上限に達した場合は注意付き採用せず `blocked` にする。
- 指摘対象だけに修正範囲を制限せず、成果物全体の整合性・品質改善のために置き換える契約は実装済み。`validate_revision_scope` は指摘フィールドの存在確認のみを行い、修正範囲を制限しない。
- run-state は V1仕様の schema version `3` を使用。`run_id` と `stop_reason` は保存しない。`active_candidate` と `active_scene_id` は廃止済み。進捗を stage・target・不変 selectionと健全な `pending_commit` だけで表す契約を満たす。
- `pending_commit` は仕様通りの閉じた構造で、`sha256` を持たず、bootstrapの`input_selection_id=null`、kindごとの閉じた`state_update`、target集合の完全一致を実装。クラッシュ収束のmanifestは仕様達成済み。
- `scene_commit` は一場面の本文・継続性更新・後続 `generation`・次対象を原子確定する。全場面の確定後に `volume_publication` が巻を公開し、前巻公開後だけ次巻計画へ進み、最終巻の巻公開後だけ `completed` になる
- console scriptは`storycraft.cli:console_main`を指し、配布CLIは起動可能。lock取得失敗は仕様通り`75`で返す。
- 正本・参照・確定物の不整合を`blocked`のまま再開せず新しい作業場所でやり直すV1契約は実装済み。`blocked`状態のworkspaceは`run`できず`RunUnavailable`を投げる。
- 現行実装の公開工程名は`volume_publication`である。旧`publication`を使うテスト用資料は現行契約の根拠にしない。
- 初期設計のrich JSON Schema（`schema_version`、作品核、人物関係、世界、知識、未解決事項、結末条件）は実装validatorと初期作品状態生成で検証する。後続作品状態は空の旧形式を受け付けない。
- active planning schemaの人物・関係・未解決事項・知識のmap keyは固定ID形式を要求せず、入力selectionから渡されたcanonical key/nameを使う。series planの`thread_progression`は初期設計の`unresolved_threads[].name`へ決定的に束縛する。
- `scene` の基準状態は場面生成時の入力selectionから検証し、場面後に進んだ最終`current_state`と誤比較しない。場面確定と巻公開では継続性品質判定slotも必須にした。
- `scene-plan` と `scene-card` の視点人物・参加者・場所はコードで一致を検証し、`scene-card` と継続性更新の状態更新列挙をcanonicalな作品状態項目へ統一した。
- 初期設計の実LLM応答は `candidate-response-v1` envelope を検証して payload をunwrapする。review/revise prompt は正式依頼・候補・確認を固定ラベル付きJSONで渡す。本文のraw text境界はstructured JSONと分離し、空本文・形式不正は `invalid_response_limit` を消費する。
- `timeline_position` は非負整数の単調値で、scene commitは `set $.timeline_position` 以外を拒否する。品質判定は `accepted ⇔ remaining_major_issues=[]`、`accepted_with_notice ⇔ 非空 + notice_type="編集"` を検証する。request intakeの `required_elements` と `avoid` は空配列を許可する。
- `ollama.py`は指定されたOpenAI互換境界を実装。モデル能力の`context_length`を取得し、`options.num_ctx`に反映し、`think: true`、`stream: false`を使用する。構造化工程では`response_format: json_schema`を付け、scene-proseの生成・修正では付けずraw textを運ぶ。設定検証でunknown field、公開・link-local endpoint、userinfo/query/fragment、`[0,0]` rangeを拒否し、loopbackまたはプライベートLAN endpointを許可。
- OllamaのHTTP 200 `error` envelope（モデル能力・completion）はHTTP/接続失敗と同じtechnical failureとしてcall recordへ保存し、形式不正再呼出しではなくtechnical retryへ送る。
- 巻公開recordは `input_selection_id` を正本参照として持ち、公開時のsource evidenceはrecoveryでselectionから再導出する。内部検証用の入力ID群は公開recordへ保存しない。
- 次巻計画は直前公開巻のcanonicalな `volume_plan.vNN` slotを直接解決する。`prior_volume_plan` のselection aliasは生成・受理せず、巻引継ぎ要約も保存しない。
- CLI入力JSONはUTF-8・末尾改行を要求し、request/settingsの文字列をNFC・trim・制御文字拒否で正規化する。保存済みrecordはUTC RFC3339とcanonical artifact IDを検証し、publication/selection path traversalを拒否する。
- direct requestは`direct_request` adoption recordを初期selectionと同一atomic workspace creationで保存する。request-intakeのcandidate/review/adoption/revision採番は全て`counters.json`を進め、後続工程との衝突を起こさない。
- scene-proseの再生成は同一座標のcontinuity slotsだけを無効化し、確定済み過去sceneのcontinuity lineageを保持する。scene commit recoveryはinput selectionにsceneを要求せず、output scene contentの全参照・座標・selection lineageを移動前に検証する。
- quality dispositionはclosed issue object（code/message/evidence_locations）とreview/candidate payloadの証拠到達性を再検証し、selection authorityは祖先selectionの解決結果を1回のresolve処理内でmemoizeする。

**確認時点で190テスト、116 subtestsが通過しています。**

これらは実装修正が完了した時点の記録です。実装の公開判断は、現在の仕様、実装、試験、配布物を確認して行います。