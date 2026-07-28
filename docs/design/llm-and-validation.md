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

`candidate.generate`、`candidate.review`、`candidate.revision` は別々の operation です。技術失敗は応答本文がないため、形式不正5回を消費しません。形式不正の各回は別の seed を使い、すべての物理呼出しを記録します。

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

構造有効な候補だけを独立 LLM が確認します。

```text
生成 → 決定的検証 → 独立確認
  ├─ 重大なし: clean 採用
  ├─ 重大あり・上限前: 修正 → 決定的検証 → 再確認
  └─ 重大あり・上限到達: 最後の構造有効版を注意付き採用
```

工程別の `quality.max_revision_passes` は作業場所作成時に `runtime/config.json` へ固定し、途中で変えません。品質上限は停止理由ではありません。

修正は候補全体を置き換えられます。ただし schema、ID、参照、更新可能範囲、作品状態の根拠契約は必ず再検証します。既存の確定物を、望む結果を探すために再生成・上書きしてはなりません。

レビュー重要度は `重大`、`注意`、`参考` の三値です。LLM は提案し、コードが値と根拠位置を検証します。存在しない JSON path、paragraph index、本文 offset を持つ指摘は `invalid_evidence_location` として除外し、修正入力・重大判定・公開注意の根拠に使いません。

品質上限で重大指摘が残った選択結果は `accepted_with_notice` とします。通常の上限到達による注意種別は `編集` です。LLM が `表現` を提案する場合も、許可された enum と根拠位置をコードが検証したときだけ `表現` を選べます。どちらも巻公開時の定型文以外を読者原稿へ出しません。

## 4. 生成・修正の共通候補 schema

生成と修正は、**全工程で同じ `CandidateEnvelope` schema** を返します。工程ごとに異なるのは `artifact_kind` が示す `payload` schema だけです。修正専用 schema、差分だけを返す schema、部分成果物だけを返す schema は持ちません。

```json
{
  "schema_version": "candidate-envelope-v1",
  "candidate_id": "candidate-...",
  "artifact_kind": "initial-design | series-plan | volume-plan | chapter-plan | scene-plan | scene-card | scene-prose | continuity-update",
  "payload": { "artifact_kind ごとの完全な候補内容" },
  "base_selection_id": "selection-...",
  "parent_candidate_id": null,
  "review_record_ids": []
}
```

初回生成は `parent_candidate_id=null`、`review_record_ids=[]` です。修正は同じ schema を使い、元候補 ID と修正根拠となる有効 review record ID を入れます。`payload` は必ず同じ artifact kind の完全 schema を満たし、partial patch を返してはなりません。`scene-prose` を修正した場合は、新候補採用後に対応する continuity update を新たに生成します。

## 5. 全工程共通の確認 schema

独立 LLM 確認は、**全工程で同じ `ReviewRecordEnvelope` schema** を返します。工程固有の評価基準は `review_profile_id` が定義し、確認応答の構造を変えません。

```json
{
  "schema_version": "review-record-envelope-v1",
  "review_record_id": "review-...",
  "candidate_id": "candidate-...",
  "candidate_version": 1,
  "artifact_kind": "...",
  "review_profile_id": "...",
  "decision": "pass | issues",
  "issues": [{
    "issue_id": "issue-...",
    "severity": "重大 | 注意 | 参考",
    "evidence_locations": ["JSON path | paragraph index | prose offset"],
    "explanation": "..."
  }],
  "excluded_issues": []
}
```

コードは candidate ID・artifact kind・version、`decision`、severity enum、issue ID 一意性、根拠位置の実在と解決可能性を検証します。`pass` は有効 issue が空、`issues` は有効 issue が一件以上でなければなりません。根拠位置が不正な issue は `excluded_issues` に移し、修正入力・重大判定・公開注意の根拠に使いません。

`review_profile_id` は、たとえば初期設計の物語的整合、計画の親計画整合、本文の視点・開示・文体、継続性更新の本文根拠を定めます。profile は評価観点だけを変え、ReviewRecordEnvelope の field・enum・根拠表現を変えません。

## 6. 最小記録形式

`call-record.json` は operation、role、対象候補、技術的試行番号、形式試行番号、seed、Ollama endpoint、model identifier、設定スナップショット ID、入力成果物 ID、要求・応答本文、transport 結果を持ちます。

`validation-record.json` は operation、call ID、validator kind、`valid|invalid`、各 check、failure code を持ちます。

`quality-disposition.json` は selected version、修正上限、使用回数、review refs、`accepted_clean|accepted_with_notice|blocked`、残存重大指摘、注意種別、reason code を持ちます。

`status` と `validate` は Provider を呼ばず、これらの参照、形式、試行上限、seed 重複、採用連鎖を再検証します。
