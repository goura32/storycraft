# Pipeline contracts index

## 目的

Stage順序、candidate/checkpoint/staged_internal/adopted/audit境界、および詳細契約の案内です。LLMはcandidate、review result、completion audit attemptだけを返し、コードがSchema、ID、hash、evidence、adoption、state merge、保存、retry、budgetを判定します。

## 変更不能な順序

```text
INPUT → INIT → SERIES → VOL → CH → SC → PROSE → DELTA → COMMIT → VH
→ COMP-PRE → COMP-AUDIT → COMP-SAVE → OUT-01 → OUT-02
→ COMP-PUBLISH → OUT-03
```

`COMP-PUBLISH`はpublic precondition gateだけでartifactを生成しません。`OUT-01`はpublication staging、`OUT-02`はstaged publication validation、`OUT-03`だけがpublication adoptionと`output/CURRENT`更新を行います。`.staging/`のartifact classは常に`staged_internal`です。

## Review decision

INIT、SERIES、VOL、CH、SC、PROSE、DELTA、VHは同一の分岐です。

```text
issues empty → ID または CHK
issues nonempty and revision_rounds_used < max_revision_rounds → REV
issues nonempty and revision_rounds_used >= max_revision_rounds → ID または CHK
```

最後の分岐は最新の構造正常candidateを採用し、全residual issueを`audit/residual-issues.jsonl`へappendします。採用条件は次だけです。

```text
structurally valid candidate exists
AND (issues are empty OR revision_rounds_used >= max_revision_rounds)
```

`passed`、issue severity、zero-issue reviewは単独の停止または採用条件ではありません。

## Audit filename

LLM auditは固定名を上書きしません。

```text
{sequence:06d}__{stage}__{target}__{kind}__{attempt-or-round}.json.gz
```

```text
000123__prose-01__v01-c003-s002__generate__attempt-02.json.gz
000124__prose-02__v01-c003-s002__review.json.gz
000125__prose-rev__v01-c003-s002__round-01.json.gz
```

## 詳細正本

| 範囲 | 詳細文書 |
|---|---|
| INPUT / INIT / SERIES | [input and initial](contracts/pipeline/input_and_initial.md) |
| VOL / CH | [planning](contracts/pipeline/planning.md) |
| SC / PROSE / DELTA | [scene generation](contracts/pipeline/scene_generation.md) |
| COMMIT / VH / completion / output | [commit and output](contracts/pipeline/commit_and_output.md) |
| candidate/resume manifest | [runtime records](contracts/ledger/runtime_records.md) |
| field contract | [data contracts index](data_contract_examples.md) |
