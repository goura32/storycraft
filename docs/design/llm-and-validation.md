# LLM と検証の設計

## 1. 責務の分離

| 層 | 責務 | 採用可否 |
|---|---|---|
| `LLMClient` | Ollama の送受信、通信失敗、時間切れ、技術的再試行、シード、呼出し保存 | 決めない |
| `StructuredOperation` | JSON 解析、スキーマ、ID、参照、更新範囲、形式不正5回 | 形式有効だけを決める |
| `QualityLoop` | 生成、独立確認、修正、再確認、品質上限時の注意付き採用 | 通常工程の候補を採用する |
| `ArtifactState` | 不変確定、採用参照、停止、復旧 | LLM 記録を物語正本にしない |

V1 の提供者は `ollama` だけです。設定検証器は他の提供者を拒否します。

## 2. 二種類の再試行

技術的再試行と形式不正再呼出しを混ぜません。

| 区分 | 対象 | 上限 | 上限到達 |
|---|---|---|---|
| 技術的再試行 | 接続不能、提供者エラー、初回・idle 時間切れ、ストリーム中断 | `retry.technical_max_attempts`。作業場所作成時に固定 | `blocked/manual_review_required` |
| 形式不正再呼出し | 空応答、解析失敗、非オブジェクト、スキーマ・参照・根拠・更新範囲の不適合 | 各論理処理で初回を含め固定5回 | `blocked/manual_review_required` |

`candidate.generate`、`candidate.review`、`candidate.revision` は別々の処理です。`request` を含むすべての CandidateResponse 種類に同じ品質ループを適用します。技術失敗は応答本文がないため、形式不正5回を消費しません。形式不正の各回は別のシードを使い、すべての物理呼出しを記録します。

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

| 処理 | LLM への必須入力 |
|---|---|
| 生成 | `generation_context`（スナップショットから組み立てた当該工程の正本入力、固定設定、許可済み文脈） |
| 確認 | **同じ `generation_context` + 確認対象 `candidate_response`** |
| 修正 | **同じ `generation_context` + 現在の `candidate_response` + 有効な `review_response`** |
| 再確認 | **同じ `generation_context` + 修正後 `candidate_response`** |

確認・修正・再確認は、生成時の入力束を省略、置換、最新探索してはなりません。反復番号を `r=0` を生成、`r>=1` を修正とすると、確認 `review(r)` の入力候補は `candidate(r)`、修正 `candidate(r+1)` の入力候補は **直前の `candidate(r)`**、修正入力の確認結果は **今回の `review(r)`** です。したがって、2回目以降の確認は前回の修正出力 `candidate(r)` を必ず含み、2回目以降の修正は前回の修正出力 `candidate(r)` と今回の確認出力 `review(r)` を必ず含みます。初回生成 `candidate(0)` や過去の確認を、直前候補・今回確認の代わりに使うことはできません。確認応答に無効な根拠位置の指摘があれば、システムが除外した後の有効指摘だけを修正入力に渡します。

```text
生成(generation_context) → 決定的検証 → 確認(generation_context + candidate)
  ├─ 重大なし: clean 採用
  ├─ 重大あり・上限前: 修正(generation_context + candidate + review)
  │                         → 決定的検証
  │                         → 再確認(generation_context + revised candidate)
  └─ 重大あり・上限到達: 最後の構造有効版を注意付き採用
```

工程別の `quality.max_revision_passes` は作業場所作成時に `runtime/config.json` へ固定し、途中で変えません。品質上限は停止理由ではありません。

修正は候補全体を置き換えられます。ただしスキーマ、ID、参照、更新可能範囲、作品状態の根拠契約は必ず再検証します。既存の確定物を、望む結果を探すために再生成・上書きしてはなりません。

レビュー重要度は `重大`、`注意`、`参考` の三値です。LLM は提案し、コードが値と根拠位置を検証します。存在しない JSON パス、段落番号、本文位置を持つ指摘は `invalid_evidence_location` として除外し、修正入力・重大判定・公開注意の根拠に使いません。

品質上限で重大指摘が残った選択結果は `accepted_with_notice` とします。通常の上限到達による注意種別は `編集` です。LLM が `表現` を提案する場合も、許可された列挙値と根拠位置をコードが検証したときだけ `表現` を選べます。どちらも巻公開時の定型文以外を読者原稿へ出しません。

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
  "payload": { "artifact_kind ごとの完全な候補内容。新規 ID は含めない" }
}
```

生成と修正の LLM 応答は完全に同じスキーマであり、元候補 ID、対象確認記録 ID、基準選択 ID を含めません。これらは LLM 呼出しの入力コンテキストと、応答保存時にシステムが作る候補記録にだけ保持します。`payload` は必ず同じ成果物種類の完全スキーマを満たし、部分差分を返してはなりません。`scene-prose` を修正した場合は、新候補採用後に対応する継続性更新を新たに生成します。

## 6. 全工程共通の確認スキーマ

独立 LLM 確認は、**全工程で同じ ID なしの `ReviewResponse` スキーマ** を返します。工程固有の評価基準は呼出し側が固定する `review_profile_id` で定義し、確認応答の構造を変えません。

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

候補 ID・候補版・成果物種類・確認観点 ID・確認記録 ID・指摘 ID・除外指摘は呼出し側と永続化層が付与します。コードは、対象候補と確認観点を呼出し記録により束縛し、`decision`、重要度列挙値、根拠位置の実在と解決可能性を検証してから指摘 ID を採番します。`pass` は有効指摘が空、`issues` は有効指摘が一件以上でなければなりません。根拠位置が不正な指摘は、システム生成の確認記録の `excluded_issues` に移し、修正入力・重大判定・公開注意の根拠に使いません。

`review_profile_id` は、たとえば初期設計の物語的整合、計画の親計画整合、本文の視点・開示・文体、継続性更新の本文根拠を定めます。確認観点は評価観点だけを変え、ReviewResponse の項目・列挙値・根拠表現を変えません。

## 7. 最小記録形式

`call-record.json` は処理、役割、対象候補、技術的試行番号、形式試行番号、シード、Ollama endpoint、モデル identifier、設定スナップショット ID、入力成果物 ID、要求・応答本文、通信結果を持ちます。

`validation-record.json` は処理、呼出し ID、検証器種類、`valid|invalid`、各 check、失敗コードを持ちます。

`quality-disposition.json` は選択済み版、修正上限、使用回数、確認参照、`accepted_clean|accepted_with_notice|blocked`、残存重大指摘、注意種別、理由コードを持ちます。

`status` と `validate` は提供者を呼ばず、これらの参照、形式、試行上限、シード重複、採用連鎖を再検証します。
