# 状態と遷移の設計

## 1. 対象

この文書は実行状態、工程遷移、停止と保護された解決記録登録を定めます。作品状態、計画、本文、公開原稿の内容は [成果物と保存](artifacts-and-storage.md) に従います。

## 2. 実行状態 v2

`runtime/run-state.json` は実行位置と参照だけを持ちます。作品の事実、計画本文、公開原稿、LLM 応答は複写しません。

```json
{
  "schema_version": 2,
  "workspace_id": "ws-000001",
  "run_id": "run-000001",
  "status": "running",
  "stop_reason": null,
  "last_error": null,
  "current_stage": "scene_plan",
  "current_target": {"volume_number": 1, "chapter_number": 1, "scene_number": 2},
  "current_generation_id": "gen-000001",
  "current_selection_id": "selection-000001",
  "active_candidate": null,
  "active_scene_id": null,
  "pending_commit": null,
  "published_volumes": [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
  "last_resolution_id": null,
  "created_at": "2026-07-28T00:00:00Z",
  "updated_at": "2026-07-28T00:00:00Z"
}
```

### 2.1 上位状態

| 値 | 意味 | 不変条件 |
|---|---|---|
| `running` | 次工程または確定・復旧を実行できる | `stop_reason` は `null` |
| `blocked` | 人手確認待ち | `stop_reason` は必ず `manual_review_required` |
| `completed` | 最終巻が公開済み | `stop_reason`、候補、場面、保留中確定はすべて `null` |

`initializing`、`stopping`、`stopped`、`failed` は v2 の保存値にしません。作業場所作成は、作成用一時場所を検証してから、最初から `running` の v2 状態を確定します。

`published_volumes` は巻番号の昇順で、重複なく `1..N` の連続列にします。各 ID は巻公開記録を参照します。単一の `current_publication_id` は廃止します。

`completed` は、保留中確定がなく、公開済み巻がシリーズ計画の全巻と一致し、最後の公開済み巻が最終巻であるときだけ許可します。

### 2.2 現在対象と保留中確定

`current_selection_id` は不変の選択スナップショットを指します。下流工程は、このスナップショットのスロットだけを入力権限として読みます。`current_generation_id` は現在状態スロットと一致するための簡便な整合性項目であり、単独で下流入力を決めません。

`current_target` は未完工程の座標と入力参照だけを持つ stage-local な値です。各工程の検証器が許可項目を閉じます。正本の内容を埋め込みません。

`pending_commit` は種類ごとの段階列挙値を使います。

| `kind` | 許可段階 | 収束処理 |
|---|---|---|
| `candidate_adoption` | `prepared` / `artifact_finalized` | 候補版と採用参照を検証し、参照更新だけを完了する |
| `scene_commit` | `prepared` / `scene_finalized` / `generation_finalized` | 場面・更新・作品状態を検証し、二重確定せず前進する |
| `volume_publication` | `prepared` / `publication_finalized` | 巻公開物を検証し、公開記録追記と次巻または完了へ収束する |
| `resolution_application` | `prepared` / `record_finalized` | 解決記録を検証し、許可された安全工程だけへ戻す |

最終成果物がない、または一時保存と最終配置がともに存在する・不整合である場合は、自動選択・自動削除をせず `blocked` にします。

## 3. 工程遷移

工程名は以下を残します。

`request_intake` はキーワード入口だけの保存工程です。直接依頼では `initial_design` を最初の工程とします。

```text
`input → request_intake → initial_design → series_plan → volume_plan → chapter_plan → scene_plan`
→ scene_card → scene_prose → scene_continuity → scene_commit
→ volume_publication
```

`volume_handoff` と `completion` は削除します。`volume_publication` は巻公開準備・確定を表す唯一の終盤工程です。

```text
scene_commit
  → scene_plan       同章の次場面
  → chapter_plan     同巻の次章
  → volume_publication  当該巻の全場面と継続性更新が確定済み

volume_publication
  → volume_plan      次巻がある場合。直前巻の公開確定後だけ
  → completed        最終巻の場合。次の工程を作らない
```

`volume_publication` は最終巻以外では終端工程ではありません。最終巻だけ、同じ工程で公開確定後に `status` を `completed` にします。これにより、独立した完結工程・完結成果物を作りません。

## 4. 通常の復旧

`resume` と `step` は `running` のときだけ、保存済みの確定点を収束させた後に工程を進めます。`blocked` のときは `status` と `validate` だけを通常操作として許可します。提供者を呼ばない収束処理では LLM を初期化しません。

失敗応答、壊れた候補、公開済み巻を、再開時に採用・公開・直接編集してはなりません。

## 5. 保護された解決記録登録

通常の `run`、`resume`、`step`、`status`、`validate` は解決記録を作れません。内部処理 `register_resolution_record` だけが登録できます。

### 5.1 認可境界

V1 のローカル作業場所では、同じ OS 利用者による直接ファイル編集を暗号学的に防ぐことは目的にしません。ここでの保護は、通常の制作 CLI から復帰を実行できない操作境界です。

実装は `ResolutionAuthorizer` を注入し、作業場所外部の管理用 Unix domain ソケットを通じて署名済みの `ResolutionGrant` を検証します。標準の利用者向け `storycraft` CLI はこのソケットを持たず、登録を拒否します。別 executable `storycraft-admin register-resolution` だけがソケットへ要求を送り、サーバーは接続元 OS UID を外部の運用者許可一覧と照合して許可証を発行します。許可証は `grant_id`、`operator_id`、`workspace_id`、`blocked_state_id`、許可 `cause`、発行時刻、失効時刻、署名を持ちます。許可証本体は管理サーバーの不変台帳に保管し、作業場所の解決記録は `grant_id` だけを参照します。サーバーが未設定・許可証が期限切れ・署名不正なら、登録せず `blocked` を維持します。試験では明示的な模擬認可器を注入します。

### 5.2 記録形式と手順

解決記録は `runtime/resolutions/resolution-000001/record.json` に不変確定します。

```json
{
  "schema_version": 1,
  "resolution_id": "resolution-000001",
  "workspace_id": "ws-000001",
  "operator_id": "operator-a",
  "authorization_grant_id": "grant-000001",
  "created_at": "2026-07-28T00:00:00Z",
  "blocked_state_id": "blocked-state-000001",
  "cause": "authority_reference_inconsistency",
  "subject_refs": [{"artifact_type": "scene", "artifact_id": "scene-v02-c01-s03"}],
  "evidence_refs": [{"artifact_type": "scene", "artifact_id": "scene-v02-c01-s03"}],
  "selected_authority_refs": [],
  "recovery_stage": "scene_plan",
  "recovery_target": {"volume_number": 2, "chapter_number": 1, "scene_number": 3},
  "rationale": "..."
}
```

`cause` は `invalid_response_limit`、`technical_retry_exhausted`、`provider_configuration_invalid`、`internal_error`、`authority_reference_inconsistency`、`volume_publication_invalid` のいずれかに閉じます。

停止時には、停止理由、現在選択、工程、対象、保留中確定を内容とする不変の `blocked-state-{通番}` 記録を確定する。許可証はこの `blocked_state_id` に署名で束縛する。登録は、ロック取得→`blocked/manual_review_required` と blocked-state ID の照合→認可器検証→原因別入力検証→`resolution_application/prepared` 保存→解決記録の不変確定→`record_finalized` 保存→未公開部分の `selected_authority_refs` から新しい選択スナップショットを不変確定→新スナップショットのスロット・公開済み巻の固定参照を検証→`current_selection_id` と戻り先を同じ状態更新で切替→`running` 復帰、の順です。異常終了復旧は記録と新スナップショットがともに確定済みのときだけ状態を収束し、片方がない・不整合なら `blocked` を維持します。

`selected_authority_refs` を許すのは整合性不一致だけで、未公開の論理位置に限ります。公開済み巻、その原稿、原稿の構成元への参照は選び直せません。選び直す成果物が未公開の下流成果物の入力なら、解決記録はその成果物から未公開の依存グラフ末端までを置換または除外する閉包を示します。新スナップショットは閉包外の旧下流スロットを残してはなりません。閉包を作れない、または `recovery_stage` と `recovery_target` が新スナップショットの次に必要なスロットと一致しない場合は、`blocked` を維持します。
