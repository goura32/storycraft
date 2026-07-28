# 巻公開と最終巻確認の設計

## 1. 公開単位

読者向け出力は巻だけです。各巻の公開は、当該巻の全計画、全場面、継続性更新が確定した後に一度だけ確定します。全巻結合の原稿、シリーズ公開、完結結果、巻引継ぎは作りません。

```text
scene_commit
  → volume_publication(vN)
  → volume_plan(vN+1)  # N が最終巻でない
  → completed          # N が最終巻
```

## 2. 巻公開成果物

```text
publications/volume-pub-v04-000004/
  record.json
  manuscript.md
```

`manuscript.md` は読者向け唯一の出力です。当該巻の採用済み場面本文だけを巻・章・場面の計画順で決定的に並べます。新しい本文・設定・作者用情報・内部指摘・要約は生成・出力しません。

`record.json` は不変の公開記録です。

```json
{
  "schema_version": 1,
  "volume_publication_id": "volume-pub-v04-000004",
  "volume_number": 4,
  "series_plan_id": "series-plan-0001",
  "volume_plan_id": "volume-plan-v04",
  "basis_generation_id": "gen-000123",
  "input_selection_id": "selection-000077",
  "source_refs": {
    "series_plan_id": "series-plan-0001",
    "volume_plan_id": "volume-plan-v04",
    "current_state_id": "gen-000123",
    "scene_commit_ids": ["scene-v04-c001-s001"]
  },
  "chapter_plan_ids": ["chapter-plan-v04-c001"],
  "scene_ids": ["scene-v04-c001-s001"],
  "publication_notice_type": null,
  "final_confirmation_id": "final-confirmation-v04-000001",
  "created_at": "..."
}
```

非最終巻の `final_confirmation_id` は `null` です。`publication_notice_type` は `null`、`表現`、`編集` だけを許可します。非 `null` なら原稿先頭に、仕様書で定めた対応する一文を置きます。

コードは input selection を読み、公開記録の `source_refs`、chapter plan、scene、scene commit が対応する snapshot slot と ID が完全一致し、欠落・余剰 slot がないことを検証します。その後に計画順、ID の集合と重複、全場面の採用済み状態、決定的に構築した原稿、公開注意、作者用情報の不在を検証します。

## 3. 最終確認記録

最終巻だけ、公開前に次の記録を確定します。

```text
final-confirmations/final-confirmation-v04-000001/
  record.json
```

これは完結要約、抽出成果物、別の物語正本ではありません。初期設計、現在の作品状態、確定本文、LLM 呼出し記録への参照と判定だけを持ちます。

```json
{
  "schema_version": 1,
  "final_confirmation_id": "final-confirmation-v04-000001",
  "volume_number": 4,
  "basis_generation_id": "gen-000123",
  "input_selection_id": "selection-000077",
  "initial_design_id": "initial-design-v0001",
  "current_state_id": "gen-000123",
  "required_thread_checks": [{
    "thread_id": "thread-001",
    "condition_ref": {"condition_id": "ending-condition-001", "location": {"json_pointer": "/required_threads/0/acceptance_condition"}},
    "resolution_scene_id": "scene-v04-c003-s002",
    "evidence_reference": {"scene_id": "scene-v04-c003-s002", "location": {"paragraph_index": 3}},
    "deterministic_valid": true,
    "semantic_decision": "confirmed"
  }],
  "semantic_decision": "confirmed",
  "llm_call_id": "call-000456",
  "created_at": "..."
}
```

コードは `input_selection_id` を先に読み、`initial_design_id`、`current_state_id`、必須事項、条件 ID、解決状態、根拠本文、採用参照の全 ID が対応する snapshot slot と完全一致し、欠落・余剰参照がないことを検証します。`llm_call_id` は snapshot 入力ではなく、最終確認後に作られる監査記録として保存済みの call record を指す ID です。その後に重複と根拠位置を検証します。独立 LLM は、各本文根拠が参照された達成条件を実際に満たすかだけを確認します。生応答は呼出し記録を正本とし、この記録へ複写しません。

未達、確認否定、形式不正5回、参照不一致では公開物を作らず `blocked/manual_review_required` にします。注意付き公開では回避できません。

## 4. 確定と復旧

1. 巻の入力を決定的に検証する。
2. 最終巻なら最終確認を実行・検証・不変確定する。
3. staging に公開記録と原稿を作る。
4. 内容、参照、注意文を検証し `volume_publication/prepared` を保存する。
5. staging を公開先へ原子的に rename する。
6. `publication_finalized` を保存する。
7. `published_volumes` を更新し、次巻または `completed` へ収束する。

staging 完全かつ final 不在なら確定を続行し、final 完全かつ staging 不在なら状態だけを前進します。双方がある、または不正なら自動的に削除・再選択せず停止します。公開済み巻、公開原稿、構成元の採用参照は変更できません。
