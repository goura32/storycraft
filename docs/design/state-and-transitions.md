# 状態と遷移の設計

## 1. 対象

この文書は実行状態、工程遷移、確定途中の収束、停止を定めます。作品状態、計画、本文、公開原稿の内容は [成果物と保存](artifacts-and-storage.md) に従います。

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
  "current_selection_id": "selection-000001",
  "active_candidate": null,
  "active_scene_id": null,
  "pending_commit": null,
  "published_volumes": [{"volume_number": 1, "publication_id": "volume-pub-v01-000001"}],
  "created_at": "2026-07-28T00:00:00Z",
  "updated_at": "2026-07-28T00:00:00Z"
}
```

| 値 | 意味 | 不変条件 |
|---|---|---|
| `running` | 次工程または確定途中の収束を実行できる | `stop_reason` は `null` |
| `blocked` | 人手確認待ちの終端状態 | `stop_reason` は必ず `manual_review_required`。通常操作で `running` に戻さない |
| `completed` | 最終巻が公開済み | `stop_reason`、`current_stage`、`current_target`、候補、場面、保留中確定はすべて `null` |

`initializing`、`stopping`、`stopped`、`failed` は v2 の保存値にしません。作業場所作成は、作成用一時場所を検証してから、最初から `running` の v2 状態を確定します。

`published_volumes` は巻番号の昇順で、重複なく `1..N` の連続列にします。各 ID は巻公開記録を参照します。単一の `current_publication_id` は廃止します。

`completed` は、保留中確定がなく、`current_stage` と `current_target` が `null` で、公開済み巻がシリーズ計画の全巻と一致し、最後の公開済み巻が最終巻であるときだけ許可します。

### 2.1 現在対象と保留中確定

`current_selection_id` は `request_intake` だけ最初の選択前に `null` を許します。この値は `request_intake` の `running` または `blocked` だけで許可し、採用後の `initial_design` 以降は必ず不変選択を指します。

`last_error` は `null` または `{ "code": "固定診断コード", "message": "短い説明", "evidence_refs": ["validation/call/artifact ID"], "occurred_at": "UTC 時刻" }` です。`blocked` では必須で、`code` は `invalid_response_limit`、`technical_retry_exhausted`、`internal_error`、`authority_inconsistency`、`publication_invalid` のいずれかとします。これは `status` と `validate` の診断用であり、CLI stderr の error `code` enum とは別です。

`current_target` は `running` で未完工程の座標だけを持つ工程内の値です。座標を持たない `request_intake`、`initial_design`、`series_plan` では空オブジェクト `{}`、`completed` では `null` とします。`blocked` は停止時点の対象を保持します。各工程の検証器が許可項目を閉じ、正本の内容と入力参照を埋め込みません。CLI `--json` は run-state の値をそのまま出力します。

`pending_commit` は `kind`、`staging_path`、更新前後の selection ID、状態更新内容、`targets` を持つ manifest です。`targets` の各要素は成果物 ID、成果物種類、staging からの相対パス、最終パス、内容ダイジェスト、`pending | finalized` を持ちます。復旧は manifest と実在する target だけを読み、種別・ID・ダイジェストを再検証して `pending` の対象を順に確定します。すべての対象が `finalized` で状態更新前なら状態を更新し、状態更新後なら manifest を消します。manifest と target が一致しない場合だけ `blocked` にします。

| `kind` | targets | 収束処理 |
|---|---|---|
| `candidate_adoption` | 採用する内容成果物、採用記録、後続選択 | `targets` を順に確定してから参照更新を完了する。依頼採用では `request`、初期設計採用では `initial_design` と最初の `generation` を含む |
| `scene_commit` | 場面、作品状態、場面確定、後続選択 | `targets` を順に確定してから状態更新を完了する |
| `volume_publication` | 公開ディレクトリ | 公開ディレクトリを一 target として確定してから公開記録追記と次巻または完了へ収束する |

manifest に載っていない最終配置、target ごとに staging と最終配置がともにある、または種別・ID・内容ダイジェストが一致しない場合は、自動選択・自動削除をせず `blocked` にします。`pending` target の staging と、別の `finalized` target の最終配置が同時にあること、または `pending` target の有効な最終配置だけがあることは正常な中断状態です。

## 3. 工程遷移

`request_intake` はキーワード入口だけの保存工程です。直接依頼では `initial_design` を最初の工程とします。

```text
input → request_intake → initial_design → series_plan → volume_plan → chapter_plan → scene_plan
→ scene_card → scene_prose → scene_continuity → scene_commit → volume_publication
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

## 4. 確定途中の収束と停止

`run` は `running` のときだけ、LLM の初期化・次工程開始の前に保存済みの確定点を共通収束表で収束させてから工程を進めます。`blocked` のときは `status` と `validate` だけを許可します。提供者を呼ばない収束処理では LLM を初期化しません。

失敗応答、壊れた候補、公開済み巻を、再開時に採用・公開・直接編集してはなりません。不整合、形式不正の固定5回、技術再試行上限、内部エラー、公開検証不合格では `blocked/manual_review_required` にして停止します。停止した作業場所は再開せず、新しい作業場所でやり直します。
