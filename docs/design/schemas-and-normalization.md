# 共通 schema と正規化

## 1. 目的

この文書は V1 の保存 JSON と LLM 応答の共通規則を決めます。各 schema は `schema_version` を必須とします。未知 field は拒否します。保存 JSON は UTF-8、object、末尾改行ありとします。

ID はコードだけが採番します。LLM は新しい ID を返しません。LLM が既存 ID を返せるのは、入力 catalog にある ID を選ぶときだけです。

## 2. 共通値

| 値 | 形式 |
|---|---|
| ID | kind ごとの固定接頭辞 + ASCII 英数字と `-`。空白なし |
| 時刻 | UTC の RFC 3339 文字列 |
| schema version | 正の整数。LLM 応答だけ `*-v1` 文字列 |
| artifact ref | `artifact_type` と `artifact_id` の object |
| 座標 | `volume_number`、`chapter_number`、`scene_number`。すべて 1 以上の整数 |
| 根拠位置 | JSON path、paragraph index、prose offset のいずれか。対象本文・JSON に解決できる値 |

配列の ID は重複不可です。enum 外、参照先なし、座標不一致、未知 field は形式不正です。

## 3. 保存 artifact の共通 envelope

保存する候補、採用物、記録は、種類ごとの payload に加えて次を持ちます。

```json
{
  "schema_version": 1,
  "artifact_id": "コード採番 ID",
  "artifact_kind": "固定 enum",
  "created_at": "UTC 時刻",
  "input_selection_id": "入力 snapshot ID",
  "payload": {}
}
```

直接依頼の `request` は bootstrap artifact であり、`input_selection_id=null` を許します。それ以外の保存 artifact は input selection を必須とします。request 採用時に、`request` と `settings` を slot に持つ最初の selection snapshot を原子的に確定します。以後の artifact はこの snapshot またはその successor を `input_selection_id` にします。

## 4. LLM 応答

### 4.1 生成と修正

生成と修正は同じ `CandidateResponse` を返します。

```json
{
  "schema_version": "candidate-response-v1",
  "artifact_kind": "request | initial-design | series-plan | volume-plan | chapter-plan | scene-plan | scene-card | scene-prose | continuity-update",
  "payload": {}
}
```

`payload` は対象 kind の完全内容です。差分 patch、ID、新規 ID を示す field は返しません。修正の親候補、確認記録、call、selection はコードが candidate record に保存します。

### 4.2 確認

全工程の確認は同じ `ReviewResponse` を返します。

```json
{
  "schema_version": "review-response-v1",
  "decision": "pass | issues",
  "issues": [{
    "severity": "重大 | 注意 | 参考",
    "evidence_locations": ["対象候補で解決できる位置"],
    "explanation": "短い説明"
  }]
}
```

`pass` の `issues` は空、`issues` は1件以上です。ID、review profile、対象候補、除外 issue はコードが review record に保存します。

## 5. 新規 entity の正規化

LLM は新規人物と新規 thread を意味内容で返します。

- 人物: `name`、役割、説明、関係先の名前
- thread: 短い名称、種別、説明、結末必須性

コードは候補全体を検証後、出現順に ID を採番します。関係・達成条件の名前は、同じ候補内の一意な名称へ解決します。同名、空名、解決不能、重複する名称は形式不正です。

後続工程は新規 ID を作りません。人物・thread を扱うときは、入力 catalog の既存 ID を選びます。catalog は ID、種別、短い説明を持ち、返却値が catalog 外なら形式不正です。

## 6. 各 payload の最低 field

| kind | 必須 payload field |
|---|---|
| request | title、genre、premise、required_elements、forbidden_elements、ending_preference、volume_count、language |
| initial-design | core、cast、world、knowledge_model、unresolved_threads、ending_conditions |
| generation | story_facts、character_knowledge、reader_disclosures、unresolved_thread_states、timeline_position |
| series-plan | volumes、thread_allocations |
| volume-plan | volume_number、chapters、thread_allocations |
| chapter-plan | volume_number、chapter_number、scenes、thread_allocations |
| scene-plan | coordinate、purpose、characters、thread_allocations、planned_fact_changes、next_scene_conditions |
| scene-card | coordinate、pov_character、allowed_facts、allowed_knowledge、allowed_disclosures、forbidden_disclosures、allowed_updates、prose_conditions |
| scene-prose | coordinate、base_generation、scene_card、text |
| continuity-update | coordinate、base_generation、scene_prose、changes |
| scene | coordinate、scene_prose、continuity_update、base_generation |
| selection | selection_id、input_selection_id、slots、created_at |
| quality disposition | selected_candidate、review_records、revision_limit、revision_count、result、remaining_major_issues、notice_type |

各 kind の型、enum、相関制約は対応する工程契約で定めます。ここにない field を保存 schema に追加するには、この表と工程契約を同時に更新します。

## 7. 正規化後の検証

コードは、LLM 応答を parse してから次の順に検証します。

1. response schema と artifact kind。
2. unknown field、型、enum、必須 field。
3. 新規 entity の名称一意性と参照解決。
4. ID 採番または catalog 選択の妥当性。
5. 工程固有の payload 制約。
6. 保存 artifact envelope と input selection の一致。

失敗は `invalid_response_limit` の形式不正として扱います。
