# 共通スキーマと正規化

## 1. 目的

この文書は V1 の保存 JSON と LLM 応答の共通規則を決めます。各スキーマは `schema_version` を必須とします。未知項目は拒否します。保存 JSON は UTF-8、オブジェクト、末尾改行ありとします。

成果物 ID の形式・カウンタ・配置の唯一の正本は [成果物と保存](artifacts-and-storage.md#2-配置と-id) の表とする。すべての成果物 ID は、同表の通番6桁を含む形式を使う。座標は巻・章・場面を2桁ゼロ埋めし、予約済み ID は再利用しない。カウンタは `runtime/counters.json` で独立管理する。

```json
{
  "<counter_key defined by the ID table>": 1
}
```

`invalid_response_limit` は `config` の必須項目で、形式不正再呼出しの上限回数（1以上の整数）です。省略による既定値への正規化は行いません。検証済みの値を `settings.payload` に保存し、全工程がその値だけを参照します。

| 値 | 形式 |
|---|---|
| ID | [成果物と保存](artifacts-and-storage.md#2-配置と-id) の形式。ASCII 英数字と `-` だけを使い、通番は6桁、巻・章・場面番号は2桁ゼロ埋め |
| 時刻 | UTC の RFC 3339 文字列 |
| スキーマ版 | 正の整数。LLM 応答だけ `*-v1` 文字列 |
| 成果物参照 | `artifact_kind` と `artifact_id` のオブジェクト |
| 座標 | `volume_number`、`chapter_number`、`scene_number`。すべて 1 以上の整数 |
| 根拠位置 | `$.path`（JSON パス）、`paragraph:N`（空行区切りの0始まり段落番号）、`prose:N`（本文のUTF-8 byte オフセット、0始まり）のいずれか。対象本文・JSON に解決できる値 |

配列の ID は重複不可です。列挙値外、参照先なし、座標不一致、未知項目は形式不正です。

## 2. 保存成果物の共通外枠

採用済みの内容成果物だけは、種類ごとの内容に加えて次を持ちます。選択スナップショット、公開記録、停止状態、候補・確認・呼出し・検証の監査記録はこの外枠の対象外であり、それぞれの個別記録形式を持ちます。

```json
{
  "schema_version": 1,
  "artifact_id": "string",
  "artifact_kind": "request | initial-design | series-plan | volume-plan | chapter-plan | scene-plan | scene-card | scene-prose | continuity-update | generation | scene",
  "input_selection_id": "string | null",
  "created_at": "RFC3339",
  "content": {}
}
```

**共通外枠を持つ内容成果物の種類**:

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
| 現在作品状態 | `generation` | `current_state` |
| 場面確定単位 | `scene` | `scene.vNN.cMM.sKK` |

この表は共通外枠を持つ内容成果物だけを列挙します。`keywords`、`volume-publication`、`quality-disposition`、`scene-commit`、selection、candidate、review、call、adoption、run-state はこの `artifact_kind` 列挙の値ではなく、それぞれの個別記録形式を持ちます。

各成果物の `content` は任意 object ではない。`artifact_kind`、`input_selection_id` が指す不変 selection、工程契約が定める必須入力スロットから一意に組み立てる閉じた入力束に対し、採用時と同じ種別別内容検証器を通る object だけを許可する。直接依頼と `request_intake` の request は bootstrap 例外で `input_selection_id=null` とし、不変 settings と入口入力だけから同じ入力束を組み立てる。種別別内容検証器は、工程契約の必須項目、型、列挙、座標、参照、相関制約、未知項目を決定的に検証する。採用済み内容を検証するときも、当該 artifact の input selection と工程スロットから同じ入力束を復元して再適用する。任意の入れ子を巨大な共通 JSON Schema に複写せず、種別別内容検証器を `content` の唯一の正本とする。

| `artifact_kind` | 検証責務 | 閉じた入力束 |
|---|---|---|
| `request` | 入口の型・未知項目・相関制約 | 正規化済み入口入力、settings |
| `initial-design` | 人物・世界・知識・未解決事項・結末条件の ID、参照、相関 | request、settings |
| `series-plan` | 巻順、未解決事項割当、解決巻の一意性 | request、settings、initial_design、current_state |
| `volume-plan` | 対象巻、章構成、シリーズ計画との一致 | settings、current_state、series_plan、第2巻以降は直前に公開された巻番号を `NN` とする `volume_plan.vNN` |
| `chapter-plan` | 章・場面順、親巻計画との一致 | settings、initial_design、current_state、series_plan、volume_plan |
| `scene-plan` | 座標、人物・未解決事項割当、親計画との一致 | settings、initial_design、current_state、series_plan、volume_plan、chapter_plan |
| `scene-card` | 座標、視点、開示、許可更新、場面計画・状態との一致 | settings、initial_design、current_state、scene_plan |
| `scene-prose` | 座標、本文型・長さ、基準状態・カードへの束縛 | settings、current_state、scene_plan、scene_card、カードの文脈参照 |
| `continuity-update` | 座標、更新範囲、本文根拠位置、未解決事項操作 | settings、current_state、scene_plan、scene_card、scene_prose |
| `generation` | 初期設計または場面確定からの決定的状態構築 | initial_design または基準 generation と確定 scene |
| `scene` | 本文・更新・基準状態・カードの同一座標、後続 generation との整合 | current_state、scene_plan、scene_card、scene_prose、continuity_update |

`validate` は現在 selection から到達する内容成果物だけを ID 順に同じ検証器へ渡す。固定パス・最新探索・未選択履歴・candidate・review・call record による補完、LLM 呼出し、意味品質評価はしない。不合格時は artifact ID、`schema | id | reference | range | evidence` の検査観点、および JSON path または論理項目を返す。実行前検証で同じ不合格を検出した場合は `authority_inconsistency` として `blocked` にする。

`generation` は共通外枠を持つ採用済みの**現在作品状態**で、`artifact_kind="generation"`、`artifact_id="gen-{通番6桁}"`、`input_selection_id`、初期設計または直前場面確定に対応する状態を **`content`** に持ちます。LLM 呼出し記録ではありません。初期 `generation` の `input_selection_id` は、初期設計工程への入力である依頼採用済み最初の selection ID です。初期設計採用で確定する後続 selection は、その `generation` を `current_state` slot に追加します。

`keywords` は selection 前の不変初期入力記録で、`inputs/keywords-{通番6桁}/record.json` に保存します。`keywords_id`、`schema_version`、正規化済みキーワード配列、`language`、`created_at` を必須とし、`input_selection_id` は持ちません。selection 前の候補記録は `keywords_id` と `settings_id` を持ち、確認記録は候補IDとcall IDで候補へ結び付き、呼出し記録は `settings_id` と `input_refs` でkeywords/settingsを参照します。確認・呼出し記録に候補のprovenanceフィールドを重複保存せず、採用済み作品成果物は参照しません。

`init --config FILE` は作業場所を作る前に設定を検証し、不変 `settings` を初期化時に確定します。キーワード入口の候補生成・確認・修正は、その `settings` を直接参照し、選択スナップショットはまだ持ちません。採用済み `request` は、直接依頼でもキーワードから採用した依頼でも、最初の選択スナップショットより前に確定する唯一の内容成果物であり、`input_selection_id=null` を必須とする。他の採用済み内容成果物は、すでに確定した入力 selection ID を必須とする。依頼採用時に、既存の `settings` と `request` をスロットに持つ最初の選択スナップショットを同じ adoption manifest で原子的に確定します。以後の成果物はこのスナップショットまたはその後続を `input_selection_id` にします。`settings` は `settings_id`、固定設定内容、`created_at` を持つ不変 JSON です。
`settings` は `{ "schema_version": 1, "settings_id": "settings-000001", "payload": <§2.2 config>, "created_at": "RFC3339" }` の未知項目を拒否する不変 JSON である。`payload` は §2.2 の `config` と同じ閉じたスキーマ・型・範囲・相関制約に従い、初期化後に変更しない。

### 2.1 候補・確認記録

`candidates/<candidate-id>/record.json` は `{schema_version, candidate_id, artifact_kind, input_selection_id, keywords_id|null, settings_id, payload, parent_candidate_id|null, review_record_id|null, call_id, created_at}`、`reviews/<review-id>/record.json` は `{schema_version, review_id, candidate_id, response, call_id, created_at}` を必須とし、未知項目を拒否する。初回生成候補は `parent_candidate_id=null` と `review_record_id=null`、修正候補は両方を必須とし、review は親 candidate を参照しなければならない。`request_intake` の候補だけは `input_selection_id=null`、`keywords_id` と `settings_id` を必須参照とする。同工程のreviewは候補ID・call IDで入力源を再構成し、callは`settings_id`と`input_refs`（keywords/settingsを含む）で入力源を記録する。採用済み成果物 IDをrequest_intakeの記録へ入れてはならない。その他の工程では `input_selection_id` を必須とし、`keywords_id=null` とする。

### 2.2 `init` 入力

`--request FILE`、`--keywords FILE`、`--config FILE` は UTF-8・末尾改行ありの JSON object だけを受け付け、未知項目を拒否します。文字列は前後空白を除去し Unicode NFC に正規化します。正規化後に空なら拒否し、エラーは JSON pointer を `message` に含めます。

- `request`: `title`、`genre`、`premise`、`required_elements`、`avoid`、`ending_preference`、`volume_count`、`language`。`genre` は正規化後に空でない文字列を1個以上持つ配列、`required_elements` と `avoid` は空配列を許可する文字列配列とする。要素が存在する場合は空文字・制御文字・重複を拒否する。文字数・件数の固定上限は設けない。この受理条件は LLM 処理の完走を保証せず、実際のコンテキスト超過は技術的失敗として扱う。
- `keywords`: `{ "keywords": ["空でない文字列を1個以上"], "language": "ja" }`。正規化後の重複、空文字、制御文字を拒否する。文字数・件数の固定上限は設けない。この受理条件は LLM 処理の完走を保証せず、実際のコンテキスト超過は技術的失敗として扱う。
- `config`: `{ "provider": "ollama", "endpoint": "http://192.168.1.50:11434", "model": "空でない文字列", "technical_retry_limit": 3, "quality_revision_limit": 0, "invalid_response_limit": 3, "chapter_per_volume_range": [1, 20], "chapter_scene_range": [1, 20], "scene_text_char_range": [1000, 12000] }`。`quality_revision_limit`、`technical_retry_limit`、`invalid_response_limit` は JSON integer（booleanを除く）で、前者は0以上、後二者は1以上とする。負値、小数、文字列、booleanは不正で、JSON pointer `#/config/<field>` を含む `invalid_argument` としてworkspace未作成のまま終了コード2にする。各 range は**1以上の整数**の昇順ペア。`scene_text_char_range` は本文 `text` の Unicode コードポイント数を採用前と修正後に検証する。`endpoint` は userinfo、query、fragment を含まない OpenAI 互換 API の HTTP URL を許可する。host は loopback、RFC1918 プライベート IPv4、または ULA（`fc00::/7`）に限り、ホスト名を使う場合も DNS 解決先がすべてその範囲でなければならない。公開アドレス、link-local、userinfo、query、fragment は拒否する。`technical_retry_limit` と `invalid_response_limit` は1以上の整数。`request_options` は任意の object だが、許可キーは `temperature`（0以上2以下の有限数）、`top_p`（0より大きく1以下の有限数）、`top_k`（1以上の整数）、`repeat_penalty`（0より大きい有限数）だけとする。未知キー、`think`、`num_ctx` は拒否する。省略時は request にこれらのキーを送らない。許可キーだけを `options` に追加し、`think` と `num_ctx` はLLM境界の契約に従いシステムが固定する。

## 3. LLM 応答

構造化工程のLLMはJSONオブジェクトを返し、未知項目は拒否します。場面本文の生成・修正だけはraw textを返し、コードが座標付きscene-prose payloadへ包んでから共通候補検証へ渡します。保存成果物は `schema_version` を必須とします。

### 3.1 CandidateResponse (生成・修正の応答)

```json
{
  "schema_version": "candidate-response-v1",
  "artifact_kind": "request | initial-design | series-plan | volume-plan | chapter-plan | scene-plan | scene-card | scene-prose | continuity-update",
  "payload": {}
}
```

- `artifact_kind`: LLM が生成・修正する候補種類だけを許可する。`generation`（現在作品状態）と `scene`（場面確定）はコードが決定的に作るため、LLM 応答には含めない。
- `payload`: 成果物種別ごとのスキーマ（後述）に従う。

### 3.2 ReviewResponse (確認の応答)

ここに記す `ReviewResponse` が唯一のスキーマ正本である。品質ループ上の利用規則は `llm-and-validation.md` を参照する。

```json
{
  "schema_version": "review-response-v1",
  "decision": "pass | issues",
  "issues": [{
    "severity": "critical | notice",
    "evidence_locations": ["$.path | paragraph:N | prose:N"],
    "explanation": "..."
  }]
}
```

- `decision`: `pass` は有効指摘が空、`issues` は有効指摘が 1 件以上でなければならない。`issues` の全件が根拠位置不正で除外された応答は `issues` の条件を満たさない形式不正として扱い、`invalid_response_limit` を消費する。`pass` へ正規化して採用してはならない
- `severity`: `critical`（修正必須・上限判定対象）、`notice`（採用可・注意記録のみ）
- `evidence_locations`: `$.path`、`paragraph:N`、`prose:N` のいずれか。`N` は0始まりで、`paragraph` は空行区切りの段落番号、`prose` は本文のUTF-8 byte オフセット。対象本文・JSON に解決できない値は形式不正
- `code`、`affected_artifact_ids`、`disposition`、`revision_instruction` はシステム側が確認記録作成時に付与し、LLM 応答には含めない
### 3.3 quality-disposition (品質判定記録) — `quality/{id}/record.json`

```json
{
  "schema_version": 1,
  "quality_id": "quality-000001",
  "candidate_id": "candidate-000123",

  "review_record_ids": ["review-000001", "review-000002"],
  "revision_count": 2,
  "result": "accepted_with_notice",
  "remaining_major_issues": [
    {"code": "quality.contradiction", "message": "string", "evidence_locations": ["$.path"]}
  ],
  "notice_type": "編集",
  "created_at": "RFC3339"
}
```

- `result`: `accepted`（重大指摘なし）または `accepted_with_notice`（品質修正上限に達して重大指摘が残った、または `quality_revision_limit=0` の既存有効候補への修正中に形式不正上限へ達した）。正の品質修正上限で形式不正上限へ達した場合は採用せず `blocked` とする。初回生成・確認で有効候補がないまま形式不正上限に達したときも、採用も品質判定も作らず、call record と run-state の `blocked` だけで記録する。
- `remaining_major_issues` は既存recordのフィールド名を維持した名称であり、意味は `ReviewResponse.issues[].severity="critical"` の残存指摘だけとする。`notice` はこの配列に入れず、`major` という第三の重要度は存在しない。相関制約は `accepted ⇔ remaining_major_issues=[]`、`accepted_with_notice ⇔ remaining_major_issues` が1件以上、`notice_type="編集"` とする。
- `quality.candidate_id` は採用対象の最終形式有効候補IDと一致し、`quality.review_record_ids` の全reviewは同じcandidate IDを参照しなければならない。改稿で旧候補から新候補へ進んだ場合、旧候補のreview IDを最終qualityへ混ぜず、最終候補に対して新たに作ったreviewだけを列挙する。
- `notice_type`: `accepted_with_notice` のときだけ `編集` を保存する。`accepted` ではキーを省略する。巻公開時は値を変換せず `publication_notice_type` へ転写する。

### 3.4 scene ペイロード (場面確定用複合成果物)

```json
{
  "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
  "scene_prose_id": "scene-prose-v01-c01-s01-000001",
  "continuity_update_id": "continuity-v01-c01-s01-000001",
  "current_state_id": "gen-000123",
  "scene_card_id": "scene-card-v01-c01-s01-000001",
  "quality_disposition_id": "quality-000001"
}
```

### 3.5 continuity-update ペイロード

```json
{
  "coordinate": {"volume_number": 1, "chapter_number": 1, "scene_number": 1},
  "changes": [
    {
      "op": "set | add | remove",
      "target": "story_facts | character_knowledge | reader_disclosures | unresolved_thread_states | timeline_position",
      "path": "$.character_knowledge.character-000001",
      "value": "new value",
      "evidence_locations": ["prose:456"]
    }
  ]
}
```

`timeline_position` は正本作品状態の非負整数です。`scene_continuity` の変更でこのtargetを指定する場合、`op="set"`、`path="$.timeline_position"`、`value` はbooleanでない非負整数とし、適用後の値は適用前以上でなければなりません。`add`、`remove`、任意の深いpath、後退値は形式不正です。物語上の回想・フラッシュバックは本文の `story_time` と根拠で表し、正本の現在時系列値を後退させません。

### 3.6 scene-card ペイロード

```json
{
  "pov_character_id": "char-main",
  "participant_ids": ["char-main"],
  "location_id": "loc-main",
  "story_time": "夜",
  "purpose": "展開",
  "opening_state": "開始",
  "required_beats": [{"beat_id": "beat-01", "description": "展開", "required": true, "order_hint": 1}],
  "conflict": "対立",
  "allowed_revelations": [],
  "required_revelations": [],
  "forbidden_revelations": [],
  "allowed_updates": [{"target_type": "timeline_position", "target_id": "timeline_position", "allowed_fields": ["value"]}],
  "ending_state_targets": ["変化"],
  "style_constraints": ["簡潔"]
}
```

`scene-card`の対象座標はpayloadに重複保持しない。対象scene slot、artifact ID、input selection、親scene-planのselection lineageで一意に束縛する。`pov_character_id`、`participant_ids`、`location_id`、`story_time`、状態、beats、開示制約、許可更新、終了状態、文体制約はすべてLLMが返し、正本JSON Schemaで検証する。

`scene-plan` は場面の意図（目的、開始条件、`intended_beats`、予定する開示・変化）を所有し、`scene-card` はそれを本文用の局所制約（opening state、`required_beats`、許可更新、`ending_state_targets`、文体）へ具体化する。`required_beats` と `ending_state_targets` はscene-cardだけが保存する派生値であり、カードが計画にない物語目的、未解決事項、解決条件を追加することはできない。`pov_character_id`、`participant_ids`、`location_id` は計画の束縛をそのまま引き継ぐ識別項目であり、両者が異なる場合は形式不正とする。`purpose` は計画の目的をカード向けに具体化した表現で、別の物語目的を追加してはならない。両成果物は独立した正本ではなく、scene-planが意図、scene-cardが実行制約をそれぞれ一度だけ所有する。

### 3.7 call record（呼出し記録）

call record は `runtime/calls/call-{通番6桁}/record.json` のみに保存する監査記録で、共通成果物外枠を持たない。未知項目を拒否し、次を必須とする。

```json
{
  "schema_version": 1,
  "call_id": "call-000001",
  "operation": "model_capability | generate | review | revise",
  "role": "候補生成または確認の役割名",
  "target_candidate_id": "candidate-000001 | null",
  "input_refs": ["artifact ID"],
  "technical_attempt": 1,
  "format_attempt": 1,
  "seed": 1,
  "endpoint": "loopback or private-LAN OpenAI-compatible URL",
  "model": "model identifier",
  "settings_id": "settings-000001",
  "request": "送信本文 | null",
  "response": "受信本文 | null",
  "transport": "success | failure",
  "validation": {"result": "valid | invalid | not_applicable", "checks": [], "failure_code": "string | null"}
}
```

`technical_attempt` と `format_attempt` は1以上の整数、`input_refs` は重複なしの既存ID、`transport="success"` では `response` が必須、`transport="failure"` では `response=null` とする。`request_intake` のcallは `input_selection_id` を持たず、`input_refs` にkeywords IDとsettings IDを含める。`validation.result="valid"` では `failure_code=null`、`invalid` では `json_parse`、`schema_invalid`、`reference_invalid`、`evidence_invalid`、`range_invalid` のいずれかを必須とする。`transport="failure"` では `validation.result="not_applicable"` と `failure_code=null` を必須とし、技術的再試行だけを消費する。認証情報と接続秘密値は request・response・endpoint を含めどのフィールドにも保存しない。`target_candidate_id` は `review` と `revise` で必須、`generate` と `model_capability` では `null` とする。`model_capability` は `GET /v1/models/{model}` の各物理試行を記録し、`input_refs=[]`、`format_attempt` は当該形式不正再試行の通番（1から `invalid_response_limit` まで）、`request=null` とする。

### 3.8 adoption record（採用記録）

`runtime/adoptions/adoption-{通番6桁}/record.json` は未知項目を拒否し、`{schema_version: 1, adoption_id, source_kind: "candidate | direct_request", candidate_id|null, quality_id|null, output_content_artifact_ids: [1件以上のID], output_selection_id, input_selection_id|null, created_at}` を必須とする。`source_kind="candidate"` では candidate は quality の `candidate_id` と一致し、両IDを必須とする。`source_kind="direct_request"` は `init --request` だけで許可し、candidate ID と quality ID は `null`、`output_content_artifact_ids` は request だけとする。直接依頼、または `request_intake` が採用する request candidate だけは `input_selection_id=null` で、output selection は確定済み settings と採用 request を最初の slots として持つ。後者では candidate と quality ID を必須とする。その他の `source_kind="candidate"` の output selection は input selection を複写して当該採用の slot だけを追加・置換した不変 selection でなければならない。`output_content_artifact_ids` は同じ採用manifestの内容成果物 target と完全一致する。adoption record と selection target 自身はこの配列に含めない。

## 4. 新規要素の正規化

LLM は新規人物と新規未解決事項を意味内容で返します。

- 人物: `name`、役割、説明、関係先の名前
- 未解決事項: 短い名称、種別、説明、結末必須性

コードは候補全体を検証後、出現順に ID を採番します。関係・達成条件の名前は、同じ候補内の一意な名称へ解決します。同名、空名、解決不能、重複する名称は形式不正です。

後続工程は新規 ID を作りません。人物・未解決事項を扱うときは、入力カタログの既存 ID を選びます。カタログは ID、種別、短い説明を持ち、返却値がカタログ外なら形式不正です。

**重要度の二段階化に合わせて**：`ReviewResponse.issues[].severity` は `critical` と `notice` のみを許可します（`reference` は廃止）。

## 5. 内容成果物の閉じた検証境界

| 種類 | 種別別内容検証器が検証する必須内容項目 |
|---|---|
| 依頼 | 題名、ジャンル、前提、required_elements、avoid、ending_preference、volume_count、言語 |
| initial-design | core、cast、world、knowledge_model、unresolved_threads、ending_conditions |
| 作品状態 | story_facts、character_knowledge、reader_disclosures、unresolved_thread_states、timeline_position |
| series-plan | `volume_count`、`series_objectives`、`volume_summaries`、character/relationship arc、thread progression、revelation schedule、ending path、global constraints |
| volume-plan | title、volume_purpose、central_conflict、character/relationship changes、thread goals、revelations、`chapter_summaries`、required_end_state |
| chapter-plan | title、chapter_purpose、starting_conditions、ending_changes、`scene_summaries`、required_revelations、constraints |
| scene-plan | purpose、pov_character_id、participant_ids、location_id、starting_conditions、intended_beats、intended_revelations、intended_changes、prohibited_disclosures（座標はpayloadに含めずselection slotで束縛） |
| scene-card | pov_character_id、participant_ids、location_id、story_time、purpose、opening_state、required_beats、conflict、allowed/required/forbidden_revelations、allowed_updates、ending_state_targets、style_constraints（座標はpayloadに含めずselection slotで束縛） |
| scene-prose | 座標、text |
| continuity-update | 座標、changes |
| scene | scene_prose_id、continuity_update_id、current_state_id、scene_card_id、quality_disposition_id、座標 |

`volume-plan` の開始状態は `current_state` slot、直前巻の計画は直前に公開された巻番号を `NN` とする既存の `volume_plan.vNN` slot から直接参照する。正本を代替する開始状態の要約や巻引継ぎを別フィールドとして持たない。

この表は共通外枠の `content` だけに適用する。selection、quality、candidate、review、adoption、call、run-state、公開 record は `content` を持たない別記録であり、それぞれの専用スキーマに従う。表の列挙以外の `content` top-level 項目は拒否する。各項目の型、列挙値、null 可否、配列要素、入れ子、参照、相関制約は対応する工程契約の種別別内容検証器が定める。これらの検証規則は候補の採用前、staging、最終配置、`validate` のすべてで同一に適用する。ここにない項目を保存スキーマに追加するには、この表と工程契約の種別別内容検証器を同時に更新する。

`scene-prose` と `continuity-update` の `base_generation`、`scene_card`、`scene_prose` は LLM 応答 payload に含めません。候補記録と採用済み成果物の外枠に、工程の固定入力束からシステムが一意に束縛します。

## 6. 正規化後の検証

1. 応答スキーマと成果物種類。
2. 未知項目、型、列挙値、必須項目。
3. 新規要素の名称一意性と参照解決。
4. ID 採番またはカタログ選択の妥当性。
5. 工程固有の内容制約。
6. 保存成果物共通外枠と入力選択の一致。

失敗は `invalid_response_limit` の形式不正として扱います。
