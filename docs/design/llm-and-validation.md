# LLM と検証の設計

## 1. 責務の分離

|| 層 | 責務 | 採用可否 |
||---|---|---|
|| `LLMClient` | Ollama の送受信、通信失敗、時間切れ、技術的再試行、シード、呼出し保存 | 決めない |
|| `StructuredOperation` | JSON 解析、スキーマ、ID、参照、更新範囲、**形式不正上限回数まで** | 形式有効だけを決める |
|| `QualityLoop` | 生成、独立確認、修正、再確認、品質上限時の注意付き採用 | 通常工程の候補を採用する |
|| `ArtifactState` | 不変確定、採用参照、停止、復旧 | LLM 記録を物語正本にしない |

### 7. LLMClient.invoke インターフェース契約（仕様レベル）

`LLMClient` は Ollama との通信のみを担当し、シード・タイムアウト・技術的再試行を制御します。実装インターフェースの詳細（引数順・戻り値構造・リトライ待機秒数）はコード側で定義し、契約には「Ollama 専用」「技術的再試行上限 `technical_retry_limit` 回まで」「失敗時は `internal_error`」のみを記述します。

### 8. StructuredOperation.parse_and_validate 契約（仕様レベル）

JSON 解析・スキーマ検証・ID形式・参照存在・更新範囲・根拠位置解決を決定的に行います。実装関数シグネチャはコード側で定義し、契約には「未知項目拒否」「スキーマ・ID・参照・範囲・根拠位置の 5 観点で検証」「不合格は形式不正 1 回と数える」のみを記述します。

### 9. QualityLoop.run_stage 契約（仕様レベル）

生成・確認・修正・再確認の 4 段階ループを回し、品質修正上限到達時は注意付き採用、形式不正上限到達時は `blocked/manual_review_required` とします。実装詳細はコード側で定義し、契約には「重大/注意の二段階」「上限 0以上」「形式不正上限回数」のみを記述します。

V1 の提供者は `ollama` だけです。設定検証器は他の提供者を拒否します。

## 2. 二種類の再試行

技術的再試行と形式不正再呼出しを混ぜません。

| 区分 | 対象 | 上限 | 上限到達 |
|---|---|---|---|
| 技術的再試行 | 接続不能、提供者エラー、初回・idle 時間切れ、ストリーム中断 | `technical_retry_limit`。作業場所作成時に固定 | `blocked/manual_review_required` |
| 形式不正再呼出し | 空応答、解析失敗、非オブジェクト、スキーマ・参照・根拠・更新範囲の不適合、次必須呼出しの入力上限超過 | 各論理処理で初回を含め**上限回数** | 原則 `blocked/manual_review_required`。ただし無制限品質修正中で、すでに形式有効な候補がある改稿だけは、その候補を `accepted_with_notice` として採用 |

`candidate.generate`、`candidate.review`、`candidate.revision` は別々の処理です。`request` を含むすべての CandidateResponse 種類に同じ品質ループを適用します。技術失敗は応答本文がないため、形式不正再呼出しを消費しません。形式不正の各回は別のシードを使い、すべての物理呼出しを記録します。

```python
def invoke_structured(operation):
    for structural_attempt in range(1, settings.invalid_response_limit + 1):
        response = call_with_technical_retries(operation, structural_attempt)
        parsed = parse_and_validate(response)
        if parsed.valid:
            return parsed.value
        persist_invalid_validation(operation, structural_attempt, parsed.error)
    block("manual_review_required", "MALFORMED_OUTPUT_EXHAUSTED")
```

## 3. 通常の品質ループ

構造有効な候補だけを独立 LLM が確認します。各論理工程の生成入力束を `generation_context`、その応答を `candidate_response`、確認応答を `review_response` と呼びます。ID は呼出し側が束縛し、LLM 応答には含めません。

| 処理 | LLM への必須入力 |
|---|---|
| 生成 | `generation_context`（スナップショットから組み立てた当該工程の正本入力、固定設定、許可済み文脈） |
| 確認 | **同じ `generation_context` + 確認対象 `candidate_response`** |
| 修正 | **同じ `generation_context` + 現在の `candidate_response` + 有効な `review_response`** |
| 再確認 | **同じ `generation_context` + 修正後 `candidate_response`** |

`request_intake` だけは selection 前の例外です。`generation_context` は不変 `keywords` と不変 `settings` をこの順で用い、他の工程と同じ生成・確認・修正の入力規則を適用します。その他の工程では工程契約の必須入力スロットを表の順番で、各 slot の採用成果物を **決定的 JSON 形式（キー昇順、空白なし、ASCII エスケープ）または本文では UTF-8 文字列として連結** して作る。明示参照が許される場合は工程契約に slot 名と成果物 ID を列挙し、その後に同じ形式で加える。各生成・確認・修正の最終 request 全体について、この context と candidate/review、system 指示文、user 指示文、応答 schema、固定メタデータを **同じ決定的 JSON 形式で順に連結した UTF-8 byte 数を算定し**、**`max_input_chars` を超えた時点で LLM を呼ばず `internal_error` にする**。したがって、2回目以降の確認は前回の修正出力 `candidate(r)` を必ず含み、2回目以降の修正は前回の修正出力 `candidate(r)` と今回の確認出力 `review(r)` を必ず含みます。初回生成 `candidate(0)` や過去の確認を、直前候補・今回確認の代わりに使うことはできません。確認応答に無効な根拠位置の指摘があれば、システムが除外した後の有効指摘だけを修正入力に渡します。

```text
生成(generation_context) → 決定的検証 → 確認(generation_context + candidate)
  ├─ 重大なし: clean 採用
  ├─ 重大あり・上限前: 修正(generation_context + candidate + review)
  │                         → 決定的検証
  │                         → 再確認(generation_context + revised candidate)
  重大あり・上限到達: 最後の構造有効版を注意付き採用。構造有効版が一度も生成されていない場合（**形式不正再呼出し上限**すべて形式不正）は、`blocked` / `manual_review_required` とする。
```

`quality_revision_limit` を含む設定入力は `init --config FILE` だけが読み、検証済みの全設定を不変 `settings` 成果物へ一回だけ確定します。候補を形式有効とする前に、候補全体（確認時）または候補全体と有効確認応答（修正時）を含む次必須 request の実測バイト数が `max_input_chars` 以下であることを検証する。満たせない候補は形式不正であり、下流に渡さない。V1 の通常工程はこの共通上限を使います。以後の処理は選択スナップショットの `settings` スロットだけを読み、設定入力ファイルや可変 `runtime/config.json` を保存・参照しません。品質上限は停止理由ではありません。**`quality_revision_limit = 0`（無制限）の場合、安全上限として形式不正再呼出し上限 `invalid_response_limit` 回を超える修正は行わず、その時点で最後の形式有効版を注意付き採用して `blocked` としないで次工程へ進む。**

修正は候補全体を置き換えられます。ただしスキーマ、ID、参照、更新可能範囲、作品状態の根拠契約は必ず再検証します。既存の確定物を、望む結果を探すために再生成・上書きしてはなりません。

レビュー重要度は `critical`、`notice` の二値です。LLM は提案し、コードが値と根拠位置を検証します。存在しない JSON パス、段落番号、本文位置を持つ指摘は `invalid_evidence_location` として除外し、修正入力・重大判定・公開注意の根拠に使いません。

品質上限で重大指摘が残った選択結果は `accepted_with_notice` とします。通常の上限到達による注意種別は常に `編集` です。LLM が注意種別を提案・変更することはありません。巻公開時は定型文以外を読者原稿へ出しません。

## 4. LLM 応答からの ID 採番禁止

LLM は、候補、確認、修正のいずれでも、新しい成果物 ID、候補 ID、確認記録 ID、指摘 ID、人物 ID、未解決事項 ID、計画 ID、状態 ID を生成・返却してはなりません。ID は呼出し側と永続化層だけが採番し、呼出し記録、入力選択、対象候補、確認観点、修正系譜に束縛します。

例外は、呼出し時に読み取り専用カタログとして渡した**既存 ID の選択**だけです。選択可能 ID の全一覧、各 ID の説明、選択対象の種別を入力に含め、出力検証器は選択値がその一覧に含まれることだけを許可します。LLM が新しい ID を作る、一覧外 ID を返す、ID を推測して補うことは形式不正です。

新規人物・新規未解決事項のように新しい識別子が必要な候補は、LLM が名前・役割・説明・関係などの意味内容だけを返します。コードが候補全体を形式検証した後に ID を採番し、名前・関係記述を解決して正規形内容に ID を付与します。解決不能な参照、同名曖昧性、重複は形式不正です。

## 5. 生成・修正の共通候補スキーマ

生成と修正は、**全工程で同じ ID なしの `CandidateResponse` スキーマ** を返します。工程ごとに異なるのは `artifact_kind` が示す `payload` スキーマだけです。修正専用スキーマ、差分だけを返すスキーマ、部分成果物だけを返すスキーマは持ちません。

```json
{
  "schema_version": "candidate-response-v1",
  "artifact_kind": "request | initial-design | series-plan | volume-plan | chapter-plan | scene-plan | scene-card | scene-prose | continuity-update",
  "payload": { "説明": "artifact_kind ごとの完全な候補内容。新規 ID は含めない" }
}
```

生成と修正の LLM 応答は完全に同じスキーマであり、元候補 ID、対象確認記録 ID、基準選択 ID を含めません。これらは LLM 呼出しの入力コンテキストと、応答保存時にシステムが作る候補記録にだけ保持します。`payload` は必ず同じ成果物種類の完全スキーマを満たし、部分差分を返してはなりません。`generation` と `scene` はコード専用成果物であり、この応答の `artifact_kind` に含めません。`scene-prose` を修正した場合は、新候補採用後に対応する継続性更新を新たに生成します。

確認応答スキーマ（仕様正本）:

```json
{
  "schema_version": "review-response-v1",
  "decision": "pass | issues",
  "issues": [{
    "severity": "critical | notice",
    "evidence_locations": ["JSON path | paragraph index | prose offset"],
    "explanation": "..."
  }]
}
```

- `decision`: `pass` は有効指摘が空、`issues` は有効指摘が 1 件以上でなければならない
- `severity`: `critical`（修正必須・上限判定対象）、`notice`（採用可・注意記録のみ）
- `evidence_locations`: JSON path / 段落番号 / 本文オフセットのいずれか。対象本文・JSON に解決できる値
- `code`、`affected_artifact_ids`、`disposition`、`revision_instruction` はシステム側が確認記録作成時に付与し、LLM 応答には含めない

## 7. 最小記録形式

`call-record.json` は処理、役割、対象候補、技術的試行番号、形式試行番号、シード、Ollama endpoint、モデル identifier、設定スナップショット ID、入力成果物 ID、要求・応答本文、通信結果、前回失敗後の予定待機ミリ秒、実待機ミリ秒、待機結果を持ちます。

`validation-record.json` は処理、呼出し ID、検証器種類、`valid|invalid`、各 check、失敗コードを持ちます。

`quality-disposition.json` は採用済み品質判定 `quality/<quality-id>/record.json` の内容を指す名称であり、別ファイルを作らない。`quality-id` は `quality-{通番6桁}`、採用記録と本文採用 slot が同じ ID を参照する。

`status` と `validate` は提供者を呼ばず、これらの参照、形式、試行上限、シード重複、採用連鎖を再検証します。
