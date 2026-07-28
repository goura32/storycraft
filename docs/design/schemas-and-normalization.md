# 共通スキーマと正規化

## 1. 目的

この文書は V1 の保存 JSON と LLM 応答の共通規則を決めます。各スキーマは `schema_version` を必須とします。未知項目は拒否します。保存 JSON は UTF-8、オブジェクト、末尾改行ありとします。

ID はコードだけが採番します。LLM は新しい ID を返しません。LLM が既存 ID を返せるのは、入力カタログにある ID を選ぶときだけです。

## 2. 共通値

| 値 | 形式 |
|---|---|
| ID | 種類ごとの固定接頭辞 + ASCII 英数字と `-`。空白なし |
| 時刻 | UTC の RFC 3339 文字列 |
| スキーマ版 | 正の整数。LLM 応答だけ `*-v1` 文字列 |
| 成果物参照 | `artifact_type` と `artifact_id` のオブジェクト |
| 座標 | `volume_number`、`chapter_number`、`scene_number`。すべて 1 以上の整数 |
| 根拠位置 | JSON パス、段落番号、本文位置のいずれか。対象本文・JSON に解決できる値 |

配列の ID は重複不可です。列挙値外、参照先なし、座標不一致、未知項目は形式不正です。

## 3. 保存成果物の共通外枠

保存する候補、採用物、記録は、種類ごとの内容に加えて次を持ちます。

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

直接依頼の `request` は初期化時成果物であり、`input_selection_id=null` を許します。それ以外の保存成果物は入力選択を必須とします。依頼採用時に、`request` と `settings` をスロットに持つ最初の選択スナップショットを原子的に確定します。以後の成果物はこのスナップショットまたはその後続を `input_selection_id` にします。

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

`payload` は対象種類の完全内容です。差分、ID、新規 ID を示す項目は返しません。修正の親候補、確認記録、呼出し、選択はコードが候補記録に保存します。

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

`pass` の `issues` は空、`issues` は1件以上です。ID、確認観点、対象候補、除外指摘はコードが確認記録に保存します。

## 5. 新規要素の正規化

LLM は新規人物と新規未解決事項を意味内容で返します。

- 人物: `name`、役割、説明、関係先の名前
- 未解決事項: 短い名称、種別、説明、結末必須性

コードは候補全体を検証後、出現順に ID を採番します。関係・達成条件の名前は、同じ候補内の一意な名称へ解決します。同名、空名、解決不能、重複する名称は形式不正です。

後続工程は新規 ID を作りません。人物・未解決事項を扱うときは、入力カタログの既存 ID を選びます。カタログは ID、種別、短い説明を持ち、返却値がカタログ外なら形式不正です。

## 6. 各内容の最低項目

| 種類 | 必須内容項目 |
|---|---|
| 依頼 | 題名、ジャンル、前提、required_elements、forbidden_elements、ending_preference、volume_count、言語 |
| initial-design | core、cast、world、knowledge_model、unresolved_threads、ending_conditions |
| 作品状態 | story_facts、character_knowledge、reader_disclosures、unresolved_thread_states、timeline_position |
| series-plan | 巻一覧、thread_allocations |
| volume-plan | volume_number、chapters、thread_allocations |
| chapter-plan | volume_number、chapter_number、scenes、thread_allocations |
| scene-plan | 座標、purpose、characters、thread_allocations、planned_fact_changes、next_scene_conditions |
| scene-card | 座標、pov_character、allowed_facts、allowed_knowledge、allowed_disclosures、forbidden_disclosures、allowed_updates、prose_conditions |
| scene-prose | 座標、base_generation、scene_card、text |
| continuity-update | 座標、base_generation、scene_prose、changes |
| 場面 | 座標、scene_prose、continuity_update、base_generation |
| 選択 | selection_id、input_selection_id、slots、created_at |
| 品質判定 | selected_candidate、review_records、revision_limit、revision_count、result、remaining_major_issues、notice_type |

各種類の型、列挙値、相関制約は対応する工程契約で定めます。ここにない項目を保存スキーマに追加するには、この表と工程契約を同時に更新します。

## 7. 正規化後の検証

コードは、LLM 応答を解析してから次の順に検証します。

1. 応答スキーマと成果物種類。
2. 未知項目、型、列挙値、必須項目。
3. 新規要素の名称一意性と参照解決。
4. ID 採番またはカタログ選択の妥当性。
5. 工程固有の内容制約。
6. 保存成果物共通外枠と入力選択の一致。

失敗は `invalid_response_limit` の形式不正として扱います。
