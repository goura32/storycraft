# 確定とクラッシュ復旧の契約

## 1. 共通前提

一つの作業場所は一つの書込みロックだけが変更できます。ロックは `runtime/lock` にあり、作業場所ID、run ID、PID、取得時刻を持ちます。`run` はロックを取れなければ終了コード `75` で何も変更しません。

ID 予約、一時保存作成、最終配置への原子的な名前変更、run-state 更新は同じファイルシステムで行います。ID の欠番は許可します。予約済み ID は再利用しません。

## 2. 共通収束表

`pending_commit` があるとき、提供者を呼ぶ前に manifest の `targets` と最終配置を照合して収束します。

| manifest の各 target | 最終配置 | 状態参照 | 処理 |
|---|---|---|---|
| `pending` | その target の最終配置なし・staging target 有効 | 更新前 | staging target を最終配置へ原子的に名前変更し、manifest を `finalized` に更新 |
| `pending` | その target の最終配置が有効・staging target なし | 更新前 | rename 後の正常な中断として、最終配置の種類・ID・ダイジェストを再検証し manifest を `finalized` に更新 |
| `finalized` | その target の最終配置が有効・staging target なし | 更新前 | 最終配置を再検証し、全 target 完了後に状態を更新 |
| 全て `finalized` | 全 target が有効 | 更新後 | 最終配置と状態の参照を検証して保留中を消す |
| manifest と target が不一致 | 任意 | 任意 | `blocked`。`stop_reason=manual_review_required` |

「有効」はスキーマ、参照、入力選択、種類ごとの不変条件に通ることです。自動削除、自動選択、LLM 再呼出しはしません。

## 3. 種類ごとの状態更新

| 種類 | 最終配置後に一回だけ行う状態更新 |
|---|---|
| 候補採用 | 採用記録と後続選択を現在選択にする。次工程 / 対象を更新 |
| 場面確定 | 場面、作品状態、場面確定、後続選択を参照し、現在の作品状態 / 選択と次対象を更新 |
| 巻公開 | 公開記録、原稿を参照し、公開済み巻と次巻対象または完了を更新 |

状態更新前に最終配置の成果物が不正なら停止します。状態更新後に最終配置の成果物が失われた場合も停止します。

## 4. 候補採用の詳細

候補採用の一時保存は、採用する内容成果物、採用記録、後続選択だけを含みます。初期依頼採用では `request`、初期設計採用では `initial-design` と最初の `generation` も含みます。すでに不変確定した候補、確認記録、品質判定は移動・複写せず、その ID を参照します。

## 5. 場面確定の詳細

場面確定の一時保存は場面、後続の作品状態、確定記録、後続選択を含みます。すべてが同じ基準作品状態、場面座標、場面本文、継続性更新を参照しなければなりません。作品状態の更新は一度だけ適用します。

## 6. 巻公開の詳細

巻公開の一時保存は公開記録と原稿を含みます。記録は全場面、品質判定、計画、現在状態、設定を現在選択のスロットと照合します。公開は選択スナップショットのスロットを変更しないため、後続選択を作りません。最終配置への原子的な名前変更後だけ公開済み巻を追加します。

`pending_commit` manifest の完全スキーマ:

```json
{
  "schema_version": 1,
  "manifest_id": "manifest-XXXXXX",
  "workspace_id": "ws-XXXXXX",
  "run_id": "run-XXXXXX",
  "status": "staged | committed | rolled_back",
  "targets": [
    {
      "artifact_id": "string",
      "artifact_kind": "string",
      "staging_rel_path": "string",
      "final_rel_path": "string",
      "digest": "sha256-hex",
      "status": "staged | committed | failed"
    }
  ],
  "selection_updates": {
    "added_slots": ["slot_name"],
    "replaced_slots": ["slot_name"]
  },
  "state_update": {
    "next_status": "running | blocked",
    "next_stage": "string",
    "next_target": "string",
    "stop_reason": "string | null"
  },
  "created_at": "RFC3339",
  "committed_at": "RFC3339 | null"
}
```

収束処理で「最終配置の種類・ID・ダイジェストを再検証」する際の検証項目:
1. `final_rel_path` が存在し、通常ファイルであること
2. JSON として解析可能で `schema_version` が 1 であること
3. `artifact_id` が manifest の `artifact_id` と一致すること
4. `artifact_kind` が manifest の `artifact_kind` と一致すること
5. 内容の SHA-256 ダイジェストが manifest の `digest` と一致すること
6. 参照整合性: 成果物内の全 `artifact_id` 参照が最終配置または選択スナップショットに存在すること

lock レコードの完全スキーマ (`runtime/lock`):

```json
{
  "schema_version": 1,
  "workspace_id": "ws-XXXXXX",
  "run_id": "run-XXXXXX",
  "pid": 12345,
  "acquired_at": "RFC3339"
}
```

選択スナップショット `slots` キー名の命名規則（正規表現）:
- 単一成果物: `^[a-z_]+$` （例: `request`, `settings`, `series_plan`, `initial_design`, `current_state`, `initial_design_adoption`）
- 座標付き成果物: `^[a-z_]+\\.v[0-9]{2}(\\.c[0-9]{2})?(\\.s[0-9]{2})?$` （例: `volume_plan.v01`, `chapter_plan.v01.c01`, `scene_plan.v01.c01.s01`, `scene.v01.c01.s01`）
- 品質判定: `^quality_disposition\\.v[0-9]{2}\\.c[0-9]{2}\\.s[0-9]{2}$`
- 巻公開: `^prior_volume_plan$` （第2巻以降の `volume_plan` 入力用）

`input_selection_id` が `null` を取り得るのは、依頼採用直後の最初の選択スナップショット（`request_intake` 採用時）のみ。以降の全選択スナップショットは直前の `selection_id` を必ず保持する。

---

## 8. 選択スナップショットの状態遷移図

```
[新規作成] selection-{id} (input_selection_id=null)
    |
    | request 採用時
    v
[初期状態] slots: {request, settings}
    |
    | initial_design 採用時
    v
[初期設計後] slots: {request, settings, initial_design, current_state=gen-XXXXXX, initial_design_adoption}
    |
    | series_plan 採用時
    v
[シリーズ計画後] slots: {上記 + series_plan}
    |
    | volume_plan 採用時（第1巻）
    v
[第1巻計画後] slots: {上記 + volume_plan.v01, volume_plan_adoption.v01}
    |
    | chapter_plan 採用時
    v
[第1巻章計画後] slots: {上記 + chapter_plan.v01.c01...}
    |
    | scene_plan 採用時
    v
[場面計画後] slots: {上記 + scene_plan.v01.c01.s01...}
    |
    | scene_card 採用時
    v
[場面カード後] slots: {上記 + scene_card.v01.c01.s01...}
    |
    | scene_prose / scene_continuity / scene_commit 採用時
    v
[場面確定後] slots: {上記 + scene.v01.c01.s01, current_state=gen-YYYYYY, scene_commit.v01.c01.s01, prior_volume_plan=volume_plan.v01}
    |
    | 次場面・次章... 繰り返し
    v
[巻全場面確定後]
    |
    | volume_publication 採用時
    v
[第1巻公開後] slots: {上記 + volume_publication.v01}
    |
    | 次巻 volume_plan 採用時（prior_volume_plan 参照）
    v
[第2巻計画後] slots: {上記 + volume_plan.v02, volume_plan_adoption.v02, prior_volume_plan=volume_plan.v01}
    |
    | 以下、最終巻まで繰り返し
    v
[最終巻公開後] slots: {全成果物参照}
    |
    | completed 遷移
    v
[完了]
```

**遷移規則**:
- 各遷移は「候補採用の一時保存→採用記録・成果物・後続選択スナップショット・次の current_target を原子的に確定」で行う
- `selection` ファイルは不変。更新は新ファイル作成＋ `runtime/run-state.json` の `current_selection_id` 書換え
- 後続工程は固定パス探索・最新探索・可変 selected フラグを使わず、スロットのみを参照する
