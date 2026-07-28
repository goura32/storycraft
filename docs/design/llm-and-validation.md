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

## 4. 最小記録形式

`call-record.json` は operation、role、対象候補、技術的試行番号、形式試行番号、seed、Ollama endpoint、model identifier、設定スナップショット ID、入力成果物 ID、要求・応答本文、transport 結果を持ちます。

`validation-record.json` は operation、call ID、validator kind、`valid|invalid`、各 check、failure code を持ちます。

`review-record.json` は candidate ID と版、review kind、call ID、根拠位置が検証済みの issue、除外された issue を持ちます。

`quality-disposition.json` は selected version、修正上限、使用回数、review refs、`accepted_clean|accepted_with_notice|blocked`、残存重大指摘、注意種別、reason code を持ちます。

`status` と `validate` は Provider を呼ばず、これらの参照、形式、試行上限、seed 重複、採用連鎖を再検証します。
