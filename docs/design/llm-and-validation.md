# LLM と検証の設計

## 1. 責務の分離

| 層 | 責務 | 採用可否 |
|---|---|---|
| `LLMClient` | Ollama の送受信、通信失敗、timeout、技術的再試行、seed、呼出し保存 | 決めない |
| `StructuredOperation` | JSON parse、schema、ID、参照、更新範囲、形式不正5回 | 形式有効だけを決める |
| `QualityLoop` | 生成、独立確認、修正、再確認、品質上限時の注意付き採用 | 通常工程の候補を採用する |
| `ArtifactState` | 不変確定、採用参照、停止、復旧 | LLM 記録を物語正本にしない |

V1 の Provider は `ollama` だけです。設定 validator は他の provider を拒否します。

## 2. 二種類の再試行

技術的再試行と形式不正再呼出しを混ぜません。

| 区分 | 対象 | 上限 | 上限到達 |
|---|---|---|---|
| 技術的再試行 | 接続不能、Provider エラー、初回・idle timeout、ストリーム中断 | `retry.technical_max_attempts`。作業場所作成時に固定 | `blocked/manual_review_required` |
| 形式不正再呼出し | 空応答、parse失敗、非 object、schema・参照・根拠・更新範囲の不適合 | 各論理 operation で初回を含め固定5回 | `blocked/manual_review_required` |

`candidate.generate`、`candidate.review`、`candidate.revision` は別々の operation です。`request` を含むすべての CandidateResponse kind に同じ品質ループを適用します。技術失敗は応答本文がないため、形式不正5回を消費しません。形式不正の各回は別の seed を使い、すべての物理呼出しを記録します。

```python
def invoke_structured(operation):
    for structural_attempt in range(1, 6):
        response = call_with_technical_retries(operation, structural_attempt)
        parsed = parse_and_validate(response)
        if parsed.valid:
            return parsed.value
        persist_invalid_validation(operation, structural_attempt, parsed.error)
    block("manual_review_required", "MALFORMED_OUTPUT_EXHAUSTED")
```

## 3. 通常の品質ループ

構造有効な候補だけを独立 LLM が確認します。各論理工程の生成入力束を `generation_context`、その応答を `candidate_response`、確認応答を `review_response` と呼びます。ID は呼出し側が束縛し、LLM 応答には含めません。

| operation | LLM への必須入力 |
|---|---|
| 生成 | `generation_context`（snapshot から組み立てた当該工程の正本入力、固定設定、許可済み context） |
| 確認 | **同じ `generation_context` + 確認対象 `candidate_response`** |
| 修正 | **同じ `generation_context` + 現在の `candidate_response` + 有効な `review_response`** |
| 再確認 | **同じ `generation_context` + 修正後 `candidate_response`** |

確認・修正・再確認は、生成時の入力束を省略、置換、最新探索してはなりません。反復番号を `r=0` を生成、`r>=1` を修正とすると、確認 `review(r)` の入力候補は `candidate(r)`、修正 `candidate(r+1)` の入力候補は **直前の `candidate(r)`**、修正入力の確認結果は **今回の `review(r)`** です。したがって、2回目以降の確認は前回の修正出力 `candidate(r)` を必ず含み、2回目以降の修正は前回の修正出力 `candidate(r)` と今回の確認出力 `review(r)` を必ず含みます。初回生成 `candidate(0)` や過去の review を、直前候補・今回確認の代わりに使うことはできません。確認応答に無効な根拠位置の issue があれば、システムが除外した後の有効 issue だけを修正入力に渡します。

```text
生成(generation_context) → 決定的検証 → 確認(generation_context + candidate)
  ├─ 重大なし: clean 採用
  ├─ 重大あり・上限前: 修正(generation_context + candidate + review)
  │                         → 決定的検証
  │                         → 再確認(generation_context + revised candidate)
  └─ 重大あり・上限到達: 最後の構造有効版を注意付き採用
```

工程別の `quality.max_revision_passes` は作業場所作成時に `runtime/config.json` へ固定し、途中で変えません。品質上限は停止理由ではありません。

修正は候補全体を置き換えられます。ただし schema、ID、参照、更新可能範囲、作品状態の根拠契約は必ず再検証します。既存の確定物を、望む結果を探すために再生成・上書きしてはなりません。

レビュー重要度は `重大`、`注意`、`参考` の三値です。LLM は提案し、コードが値と根拠位置を検証します。存在しない JSON path、paragraph index、本文 offset を持つ指摘は `invalid_evidence_location` として除外し、修正入力・重大判定・公開注意の根拠に使いません。

品質上限で重大指摘が残った選択結果は `accepted_with_notice` とします。通常の上限到達による注意種別は `編集` です。LLM が `表現` を提案する場合も、許可された enum と根拠位置をコードが検証したときだけ `表現` を選べます。どちらも巻公開時の定型文以外を読者原稿へ出しません。

## 4. LLM 応答からの ID 採番禁止

LLM は、候補、確認、修正のいずれでも、新しい artifact ID、candidate ID、review record ID、issue ID、人物 ID、thread ID、計画 ID、state ID を生成・返却してはなりません。ID は呼出し側と永続化層だけが採番し、呼出し記録、入力 selection、対象候補、確認 profile、修正系譜に束縛します。

例外は、呼出し時に読み取り専用 catalog として渡した**既存 ID の選択**だけです。選択可能 ID の全一覧、各 ID の説明、選択対象の種別を入力に含め、出力 validator は選択値がその一覧に含まれることだけを許可します。LLM が新しい ID を作る、一覧外 ID を返す、ID を推測して補うことは形式不正です。

新規人物・新規 thread のように新しい識別子が必要な候補は、LLM が名前・役割・説明・関係などの意味内容だけを返します。コードが候補全体を形式検証した後に ID を採番し、名前・関係記述を解決して canonical payload に ID を付与します。解決不能な参照、同名曖昧性、重複は形式不正です。

## 5. 生成・修正の共通候補 schema

生成と修正は、**全工程で同じ ID なしの `CandidateResponse` schema** を返します。工程ごとに異なるのは `artifact_kind` が示す `payload` schema だけです。修正専用 schema、差分だけを返す schema、部分成果物だけを返す schema は持ちません。

```json
{
  "schema_version": "candidate-response-v1",
  "artifact_kind": "initial-design | series-plan | volume-plan | chapter-plan | scene-plan | scene-card | scene-prose | continuity-update",
  "payload": { "artifact_kind ごとの完全な候補内容。新規 ID は含めない" }
}
```

生成と修正の LLM 応答は完全に同じ schema です。修正の元候補 ID、対象確認記録 ID、base selection ID は LLM 呼出しの入力コンテキストと、応答保存時にシステムが作る candidate record にだけ保持します。`payload` は必ず同じ artifact kind の完全 schema を満たし、partial patch を返してはなりません。`scene-prose` を修正した場合は、新候補採用後に対応する continuity update を新たに生成します。

## 6. 全工程共通の確認 schema

独立 LLM 確認は、**全工程で同じ ID なしの `ReviewResponse` schema** を返します。工程固有の評価基準は呼出し側が固定する `review_profile_id` で定義し、確認応答の構造を変えません。

```json
{
  "schema_version": "review-response-v1",
  "decision": "pass | issues",
  "issues": [{
    "severity": "重大 | 注意 | 参考",
    "evidence_locations": ["JSON path | paragraph index | prose offset"],
    "explanation": "..."
  }]
}
```

candidate ID・candidate version・artifact kind・review profile ID・review record ID・issue ID・除外 issue は呼出し側と永続化層が付与します。コードは、対象 candidate と profile を call record により束縛し、`decision`、severity enum、根拠位置の実在と解決可能性を検証してから issue ID を採番します。`pass` は有効 issue が空、`issues` は有効 issue が一件以上でなければなりません。根拠位置が不正な issue は、システム生成の review record の `excluded_issues` に移し、修正入力・重大判定・公開注意の根拠に使いません。

`review_profile_id` は、たとえば初期設計の物語的整合、計画の親計画整合、本文の視点・開示・文体、継続性更新の本文根拠を定めます。profile は評価観点だけを変え、ReviewResponse の field・enum・根拠表現を変えません。

## 7. 最小記録形式

`call-record.json` は operation、role、対象候補、技術的試行番号、形式試行番号、seed、Ollama endpoint、model identifier、設定スナップショット ID、入力成果物 ID、要求・応答本文、transport 結果を持ちます。

`validation-record.json` は operation、call ID、validator kind、`valid|invalid`、各 check、failure code を持ちます。

`quality-disposition.json` は selected version、修正上限、使用回数、review refs、`accepted_clean|accepted_with_notice|blocked`、残存重大指摘、注意種別、reason code を持ちます。

`status` と `validate` は Provider を呼ばず、これらの参照、形式、試行上限、seed 重複、採用連鎖を再検証します。
