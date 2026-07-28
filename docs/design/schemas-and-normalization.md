# 共通スキーマと正規化

## 1. 目的

この文書は V1 の保存 JSON と LLM 応答の共通規則を決めます。各スキーマは `schema_version` を必須とします。未知項目は拒否します。保存 JSON は UTF-8、オブジェクト、末尾改行ありとします。

ID 接頭辞の完全一覧と通番桁数:

| 接頭辞 | 例 | 通番桁数 | 用途 |
|---|---|---|---|
| `gen-` | `gen-000001` | 6桁 | LLM生成記録（generation） |
| `settings-` | `settings-000001` | 6桁 | 設定 |
| `keywords-` | `keywords-000001` | 6桁 | キーワード入力記録 |
| `volume-pub-v` | `volume-pub-v01-000001` | 6桁 | 巻公開 |
| `selection-` | `selection-000001` | 6桁 | 選択スナップショット |
| `call-` | `call-000001` | 6桁 | LLM呼出し記録 |
| `validation-` | `validation-000001` | 6桁 | 検証記録 |
| `quality-` | `quality-000001` | 6桁 | 品質判定 |
| `series-plan-` | `series-plan-000001` | 6桁 | シリーズ計画 |
| `volume-plan-v` | `volume-plan-v01` | 2桁巻号＋通番なし | 巻計画 |
| `chapter-plan-v` | `chapter-plan-v01-c01` | 2桁巻号＋2桁章番号 | 章計画 |
| `scene-plan-v` | `scene-plan-v01-c01-s01` | 2桁巻＋2桁章＋2桁場面 | 場面計画 |
| `scene-v` | `scene-v01-c01-s01` | 同上 | 場面確定単位 |

欠番は許可する。予約済み ID は再利用しない。カウンタは `runtime/counters.json` で種類ごとに独立管理し、起動時に読み込み・次の値を予約・使用後に更新する。

```json
{
  "gen": 1,
  "settings": 1,
  "keywords": 1,
  "volume_pub": 1,
  "selection": 1,
  "call": 1,
  "validation": 1,
  "quality": 1,
  "series_plan": 1
}
```

巻計画・章計画・場面計画・場面確定は座標エンコード型 ID を使うためカウンタ不要。

各工程は生成前に、system prompt、user prompt、応答スキーマ、メタデータを連結したリクエスト全体の Unicode code point 数が `max_input_chars` 以下であることを実測で検証し、超過なら LLM を呼ばず `internal_error` とする。settings の `max_input_chars` は 50000〜200000 の整数かつ `scene_text_char_range[1] * 4 + 40000` 以上とする。概算式による事前カウントは行わない。

## 2. 共通値

| 値 | 形式 |
|---|---|
| ID | 種類ごとの固定接頭辞 + ASCII 英数字と `-`。空白なし。接頭辞一覧: `gen-` `settings-` `keywords-` `volume-pub-vNN-` `selection-` `call-` `validation-` `quality-` `series-plan-` `volume-plan-vNN` `chapter-plan-vNN-cMM` `scene-plan-vNN-cMM-sKK` `scene-vNN-cMM-sKK` `scene-card-vNN-cMM-sKK` `continuity-vNN-cMM-sKK` `request-` `initial-design-` `scene-commit-` 通番は6桁ゼロ埋め、巻・章・場面番号は2桁ゼロ埋め |
| 時刻 | UTC の RFC 3339 文字列 |
| スキーマ版 | 正の整数。LLM 応答だけ `*-v1` 文字列 |
| 成果物参照 | `artifact_type` と `artifact_id` のオブジェクト |
| 座標 | `volume_number`、`chapter_number`、`scene_number`。すべて 1 以上の整数 |
| 根拠位置 | JSON パス（`$.path` 形式）、段落番号（0始まり整数）、本文位置（Unicode code point オフセット、0始まり整数）のいずれか。対象本文・JSON に解決できる値 |

配列の ID は重複不可です。列挙値外、参照先なし、座標不一致、未知項目は形式不正です。

## 3. 保存成果物の共通外枠

採用済みの内容成果物だけは、種類ごとの内容に加えて次を持ちます。選択スナップショット、公開記録、停止状態、候補・確認・呼出し・検証の監査記録はこの外枠の対象外であり、それぞれの個別記録形式を持ちます。

```json
{
  "schema_version": 1,
  "artifact_id": "string",
  "artifact_kind": "request | initial-design | series-plan | volume-plan | chapter-plan | scene-plan | scene-card | scene-prose | continuity-update | generation | scene | volume-publication | quality-disposition",
  "selection_id": "string",
  "created_at": "RFC3339",
  "content": {}
}
```

**`artifact_kind` 完全列挙**:

| 成果物種別 | artifact_kind 値 | 主要スロット名 |
|---|---|---|
| 依頼文 | `request` | `request` |
| 初期設計 | `initial-design` | `initial_design` |
| シリーズ計画 | `series-plan` | `series_plan` |
| 巻計画 | `volume-plan` | `volume_plan.vNN` |
| 章計画 | `chapter-plan` | `chapter_plan.vNN.cMM` |
| 場面計画 | `scene-plan` | `scene_plan.vNN.cMM.sKK` |
| 場面カード | `scene-card` | `scene_card.vNN.cMM.sKK` |
| 場面本文 | `scene-prose` | `scene_prose.vNN.cMM.sKK` |
| 継続性更新 | `continuity-update` | `continuity_update.vNN.cMM.sKK` |
| LLM生成記録 | `generation` | `generation-XXXXXX` |
| 場面確定単位 | `scene` | `scene.vNN.cMM.sKK` |
| 巻公開 | `volume-publication` | `volume_publication.vNN` |
| 品質判定 | `quality-disposition` | `quality-{6桁}` |

各成果物の `content` スキーマは個別契約書（`initial-design-contract.md`、`planning-contract.md`、`scene-production-contract.md`、`volume-publication.md`）で定義します。

`generation` は共通外枠を持つ採用済み内容成果物で、`artifact_kind="generation"`、`artifact_id="gen-{通番6桁}"`、`input_selection_id`、初期設計または直前場面確定に対応する `payload` を持ちます。初期 `generation` の `input_selection_id` は、初期設計工程への入力である依頼採用済み最初の selection ID です。初期設計採用で確定する後続 selection は、その `generation` を `current_state` slot に追加します。

`keywords` は selection 前の不変初期入力記録で、`inputs/keywords-{通番6桁}/record.json` に保存します。`keywords_id`、`schema_version`、正規化済みキーワード配列、`language`、`created_at` を必須とし、`input_selection_id` は持ちません。selection 前の候補・確認・呼出し記録は `keywords_id` と `settings_id` を必ず参照し、採用済み作品成果物は参照しません。

`init --config FILE` は作業場所を作る前に設定を検証し、不変 `settings` を初期化時に確定します。キーワード入口の候補生成・確認・修正は、その `settings` を直接参照し、選択スナップショットはまだ持ちません。採用済み `request` は、直接依頼でもキーワードから採用した依頼でも、最初の選択スナップショットより前に確定する唯一の内容成果物であり、`input_selection_id=null` を許します。依頼採用時に、既存の `settings` と `request` をスロットに持つ最初の選択スナップショットを同じ adoption manifest で原子的に確定します。以後の成果物はこのスナップショットまたはその後続を `input_selection_id` にします。`settings` は `settings_id`、固定設定内容、`created_at` を持つ不変 JSON です。

## 3.1 `init` 入力

`--request FILE`、`--keywords FILE`、`--config FILE` は UTF-8・末尾改行ありの JSON object だけを受け付け、未知項目を拒否します。文字列は前後空白を除去し Unicode NFC に正規化します。正規化後に空なら拒否し、エラーは JSON pointer を `message` に含めます。

- `request`: `title`、`genre`、`premise`、`required_elements`、`forbidden_elements`、`ending_preference`、`volume_count`、`language`。内容制約は依頼入口の契約に従う。
- `keywords`: `{ "keywords": ["1〜80文字の文字列を1〜12個"], "language": "ja" }`。正規化後の重複、空文字、制御文字を拒否する。
- `config`: `{ "provider": "ollama", "endpoint": "http://127.0.0.1:11434", "model": "空でない文字列", "technical_retry_limit": "1〜5", "quality_revision_limit": "0〜5", "volume_chapter_range": [1, 20], "chapter_scene_range": [1, 20], "scene_text_char_range": [1000, 12000], "max_input_chars": 200000 }`。各 range は整数の昇順ペア、`max_input_chars` は 50000〜200000 の整数かつ `scene_text_char_range[1] * 4 + 40000` 以上。この下限は、最大場面本文文字数の4倍（Ollama 日本語トークン概算：1文字≒0.25トークン、安全係数4）にシステム/ユーザー/スキーマ/メタデータ固定予約40000を加えた値であり、**Unicode code point 数**で数える。endpoint は loopback HTTP だけを許可し、remote host、proxy、認証情報・header・credential 項目を拒否する。loopback 判定は：IPv4 `127.0.0.0/8`、IPv6 `::1`、ホスト名 `localhost` 解決結果のいずれかに一致し、ポートは `1〜65535`。

## 4. LLM 応答

LLM は JSON オブジェクトを返し、未知項目は拒否します。保存成果物は `schema_version` を必須とします。

### 4.1 CandidateResponse (生成・修正の応答)

```json
{
  "schema_version": 1,
  "artifact_kind": "request | initial-design | series-plan | volume-plan | chapter-plan | scene-plan | scene-card | scene-prose | continuity-update | generation | scene",
  "payload": {}
}
```

- `artifact_kind`: 列挙値のいずれか。`generation` は初期設計確認用の内部記録、`scene` は場面確定時の本文・更新・状態をまとめた複合成果物。
- `payload`: 成果物種別ごとのスキーマ（後述）に従う。

### 4.2 ReviewResponse (確認の応答)

```json
{
  "schema_version": 1,
  "review_profile_id": "string",
  "findings": [
    {
      "severity": "critical | notice | reference",
      "code": "string",
      "message": "string",
      "evidence_locations": ["$.path", "paragraph:0", "prose:123"],
      "affected_artifact_ids": ["artifact-id"]
    }
  ],
  "disposition": "accept | revise | reject",
  "revision_instruction": "string | null"
}
```

- `severity`: `critical`（修正必須・上限判定対象）、`notice`（採用可・注意記録）、`reference`（参考・制御影響なし）
- `code`: 検証器内部エラーコード（例: `schema.missing_field`, `ref.unresolved`, `quality.contradiction`）
- `evidence_locations`: 根拠位置配列。JSON path / 段落番号 / 本文オフセットのいずれか。
- `affected_artifact_ids`: 指摘対象の成果物 ID（選択スナップショットの slot 経由で解決可能）
- `disposition`: `accept`（採用）、`revise`（修正再生成）、`reject`（候補却下・blocked 遷移）
- `revision_instruction`: `revise` 時のみ必須、修正指示文

### 4.3 quality-disposition (品質判定記録) — `quality/{id}/record.json`

```json
{
  "schema_version": 1,
  "quality_id": "quality-000001",
  "candidate_id": "gen-000123",
  "adoption_record_id": "adopt-000456",
  "review_record_ids": ["review-000001", "review-000002"],
  "revision_count": 2,
  "result": "accepted | accepted_with_notice | blocked_manual_review",
  "remaining_major_issues": [
    {"code": "quality.contradiction", "message": "string", "evidence_locations": []}
  ],
  "notice_type": "edit | null",
  "created_at": "RFC3339"
}
```

- `result`: `accepted`（重大指摘なし）、`accepted_with_notice`（重大指摘ありだが上限到達で注意付き採用）、`blocked_manual_review`（形式不正5回到達など）
- `notice_type`: `edit` または `null`。巻公開時に `publication_notice_type` へ転写される。

### 4.4 scene ペイロード (場面確定用複合成果物)

```json
{
  "schema_version": 1,
  "scene_prose_id": "scene-v01-c01-s01",
  "continuity_update_id": "continuity-v01-c01-s01",
  "current_state_id": "gen-000123",
  "scene_card_id": "scene-card-v01-c01-s01",
  "quality_disposition_id": "quality-000001"
}
```

### 4.5 continuity-update ペイロード

```json
{
  "schema_version": 1,
  "changes": [
    {
      "op": "set | add | remove",
      "target": "knowledge_model | cast | world | core | unresolved_threads | ending_conditions",
      "path": "$.cast[0].knowledge",
      "value": "new value",
      "evidence_locations": ["prose:456"]
    }
  ],
  "next_scene_conditions": []
}
```

### 4.6 scene-card ペイロード

```json
{
  "schema_version": 1,
  "allowed_facts": ["string"],
  "allowed_knowledge": ["string"],
  "allowed_disclosures": ["string"],
  "forbidden_disclosures": ["string"],
  "allowed_updates": ["string"],
  "prose_conditions": ["string"]
}
```

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
| scene-prose | 座標、text |
| continuity-update | 座標、changes |
| 場面 | 座標、scene_prose、continuity_update、base_generation |
| 選択 | selection_id、input_selection_id、slots、created_at |
| 品質判定 | selected_candidate、review_records、revision_limit、revision_count、result、remaining_major_issues、notice_type |

各種類の型、列挙値、相関制約は対応する工程契約で定めます。ここにない項目を保存スキーマに追加するには、この表と工程契約を同時に更新します。

`scene-prose` と `continuity-update` の `base_generation`、`scene_card`、`scene_prose` は LLM 応答 payload に含めません。候補記録と採用済み成果物の外枠に、工程の固定入力束からシステムが一意に束縛します。

## 7. 正規化後の検証

1. 応答スキーマと成果物種類。
2. 未知項目、型、列挙値、必須項目。
3. 新規要素の名称一意性と参照解決。
4. ID 採番またはカタログ選択の妥当性。
5. 工程固有の内容制約。
6. 保存成果物共通外枠と入力選択の一致。

失敗は `invalid_response_limit` の形式不正として扱います。
