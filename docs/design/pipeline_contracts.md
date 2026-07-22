# Pipeline contracts

> 全stage個別契約の唯一の正本。fieldの完全定義は[ledger contracts](ledger_contracts.md)、checkpointは[runtime and recovery](runtime_and_recovery.md)、pathは[workspace layout](workspace_layout.md)を参照する。

## Shared rules

LLM only returns candidates, review issues, or audit assessments. Code validates IDs, structure, evidence, adoption, state merge, retry, and storage. A transport retry is connection/HTTP/stream/timeout only. A response structure retry is JSON parse/Schema/missing-required/enum failure only. Revision round is consumed only by a structurally valid review with issues. Every review and revision structure retry uses `max_response_structure_retries`; exhaustion stops. Quality issues never by themselves stop a valid last candidate.

All stage outputs use `additionalProperties:false`; field-level objects are defined in the linked ledger. Candidate fields are never authoritative until the stated adoption stage. Audit records are JSON gzip under `audit/`; review fields are `review_id,target_operation_id,target_id,issues`, and each issue is `code,severity,path,description,evidence,suggested_change`.

## Stage contracts

### INPUT-01 — brief読込

- **目的:** brief読込。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** input/brief.json.
- **入力正本:** 利用者入力.
- **出力field:** brief; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** コード.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INPUT-03.

### INPUT-02 — keywordsからbrief生成

- **目的:** keywordsからbrief生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** keywords.
- **入力正本:** 利用者keywords.
- **出力field:** brief candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: brief fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INPUT-03.

### INPUT-03 — brief検証・採用

- **目的:** brief検証・採用。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** brief candidate.
- **入力正本:** INPUT-01またはINPUT-02.
- **出力field:** adopted brief; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** コード: hash/adopted_at.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INIT-01.

### INIT-01 — concept生成

- **目的:** concept生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** adopted brief.
- **入力正本:** brief.
- **出力field:** concept candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: concept fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INIT-02.

### INIT-02 — characters/relationships生成

- **目的:** characters/relationships生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** concept candidate, adopted brief.
- **入力正本:** INIT-01.
- **出力field:** character/relationship candidates; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: field-level ledger candidates.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INIT-03.

### INIT-03 — world/temporal生成

- **目的:** world/temporal生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** initial candidates.
- **入力正本:** INIT-01..02.
- **出力field:** world/rule candidates; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: field-level ledger candidates.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INIT-04.

### INIT-04 — arcs/threads/ending生成

- **目的:** arcs/threads/ending生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** initial candidates.
- **入力正本:** INIT-01..03.
- **出力field:** arc/thread/ending candidates; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: field-level ledger candidates.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INIT-05.

### INIT-05 — bundle統合

- **目的:** bundle統合。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** all INIT candidates.
- **入力正本:** INIT-01..04.
- **出力field:** initial design bundle candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: ordered references only.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INIT-06.

### INIT-06 — bundle全体レビュー

- **目的:** bundle全体レビュー。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** bundle candidate.
- **入力正本:** INIT-05.
- **出力field:** review result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: review issue fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INIT-REV or INIT-ID.

### INIT-REV — bundle全体修正

- **目的:** bundle全体修正。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** candidate and review issues.
- **入力正本:** INIT-05/06.
- **出力field:** revised bundle candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: bundle fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: one on entry.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** INIT-06.

### INIT-ID — ID採番・genesis採用

- **目的:** ID採番・genesis採用。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** valid bundle.
- **入力正本:** final bundle.
- **出力field:** adopted initial design and genesis; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: permanent IDs, mapping, manifest.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** SERIES-01.

### SERIES-01 — series map生成

- **目的:** series map生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** initial design.
- **入力正本:** adopted initial design.
- **出力field:** series map candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: per-volume design content; code supplies volume number.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** SERIES-02.

### SERIES-02 — series mapレビュー

- **目的:** series mapレビュー。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** map candidate.
- **入力正本:** SERIES-01.
- **出力field:** review result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: review issue fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** SERIES-REV or SERIES-ID.

### SERIES-REV — series map修正

- **目的:** series map修正。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** map candidate and issues.
- **入力正本:** SERIES-01/02.
- **出力field:** revised map candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: map content, no numbering.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: one on entry.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** SERIES-02.

### SERIES-ID — series map採用

- **目的:** series map採用。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** valid map.
- **入力正本:** final map.
- **出力field:** adopted immutable map; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: fixed 1..brief.volumes numbering/hash.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** VOL-01.

### VOL-01 — 巻設計生成

- **目的:** 巻設計生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** map row, HEAD canon/state, prior handoff.
- **入力正本:** adopted map/current HEAD.
- **出力field:** volume candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: volume design fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** VOL-02.

### VOL-02 — 巻設計レビュー

- **目的:** 巻設計レビュー。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** volume candidate.
- **入力正本:** VOL-01.
- **出力field:** review result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: review issue fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** VOL-REV or VOL-ID.

### VOL-REV — 巻設計修正

- **目的:** 巻設計修正。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** volume candidate and issues.
- **入力正本:** VOL-01/02.
- **出力field:** revised volume candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: volume fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: one on entry.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** VOL-02.

### VOL-ID — 巻設計採用

- **目的:** 巻設計採用。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** valid volume candidate.
- **入力正本:** final candidate.
- **出力field:** adopted volume design; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: hash/adopted metadata.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** CH-01.

### CH-01 — 章設計生成

- **目的:** 章設計生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** volume design and HEAD.
- **入力正本:** adopted volume/current HEAD.
- **出力field:** chapter candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: chapter design fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** CH-02.

### CH-02 — 章設計レビュー

- **目的:** 章設計レビュー。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** chapter candidate.
- **入力正本:** CH-01.
- **出力field:** review result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: review issue fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** CH-REV or CH-ID.

### CH-REV — 章設計修正

- **目的:** 章設計修正。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** chapter candidate and issues.
- **入力正本:** CH-01/02.
- **出力field:** revised chapter candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: chapter fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: one on entry.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** CH-02.

### CH-ID — 章設計採用

- **目的:** 章設計採用。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** valid chapter candidate.
- **入力正本:** final candidate.
- **出力field:** adopted chapter design; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: ordered chapter metadata.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** the named -ID only.
- **保存先:** `plans/, canon/initial-design.json, or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** SC-01.

### SC-01 — 場面カード生成

- **目的:** 場面カード生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** chapter, HEAD, assignment.
- **入力正本:** adopted chapter/current HEAD.
- **出力field:** scene card candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: content fields; code supplies scene_id/volume/chapter/scene number.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** raw prose and unadopted candidate; planner secret access follows Context contract.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity; code-supplied coordinate equality; LLM cannot create scene ID/number.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** SC-02.

### SC-02 — 場面カードレビュー

- **目的:** 場面カードレビュー。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** scene card candidate.
- **入力正本:** SC-01.
- **出力field:** review result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: review issue fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** SC-REV or SC-CHK.

### SC-REV — 場面カード修正

- **目的:** 場面カード修正。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** card candidate and issues.
- **入力正本:** SC-01/02.
- **出力field:** revised card candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: card content fields, code coordinates fixed.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity; code-supplied coordinate equality; LLM cannot create scene ID/number.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: one on entry.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** SC-02.

### SC-CHK — 場面カードcheckpoint

- **目的:** 場面カードcheckpoint。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** valid card.
- **入力正本:** valid card.
- **出力field:** CARD_ACCEPTED checkpoint; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: canonical hash/checkpoint manifest.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** checkpoint only; formal artifact remains absent.
- **保存先:** `runtime/checkpoints/scenes/v01/c001/s001/scene-card.json`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** PROSE-01.

### PROSE-01 — 本文生成

- **目的:** 本文生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** adopted card and writer context.
- **入力正本:** checkpoint card/context.
- **出力field:** prose candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: manuscript text only.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** author truth, resolution condition, private other-character knowledge, future details, secret ending, unadopted candidate.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** PROSE-02.

### PROSE-02 — 本文レビュー

- **目的:** 本文レビュー。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** prose and card.
- **入力正本:** PROSE-01.
- **出力field:** review result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: review issue fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** PROSE-REV or PROSE-CHK.

### PROSE-REV — 本文修正

- **目的:** 本文修正。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** prose candidate and issues.
- **入力正本:** PROSE-01/02.
- **出力field:** revised prose; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: manuscript text only.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: one on entry.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** PROSE-02.

### PROSE-CHK — 本文checkpoint

- **目的:** 本文checkpoint。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** valid prose.
- **入力正本:** valid prose.
- **出力field:** PROSE_FROZEN checkpoint; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: canonical prose hash.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** checkpoint only; formal artifact remains absent.
- **保存先:** `runtime/checkpoints/scenes/v01/c001/s001/prose.md`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** DELTA-01.

### DELTA-01 — 差分抽出

- **目的:** 差分抽出。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** frozen prose, pre-scene HEAD, policy.
- **入力正本:** checkpoint prose/pre-scene HEAD.
- **出力field:** delta candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: typed delta proposal.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** permanent ID allocation and prose-origin author truth.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity; before/evidence exactness, allowed operation, lifecycle/knowledge-origin rules.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** DELTA-02.

### DELTA-02 — 差分レビュー

- **目的:** 差分レビュー。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** delta and frozen prose.
- **入力正本:** DELTA-01.
- **出力field:** review result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: review issue fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** DELTA-REV or DELTA-CHK.

### DELTA-REV — 差分修正

- **目的:** 差分修正。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** delta candidate and issues.
- **入力正本:** DELTA-01/02.
- **出力field:** revised delta; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: typed delta proposal.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity; before/evidence exactness, allowed operation, lifecycle/knowledge-origin rules.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: one on entry.
- **採用条件:** INPUT-03 only.
- **保存先:** `input/ or audit/llm-calls/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** DELTA-02.

### DELTA-CHK — 差分checkpoint

- **目的:** 差分checkpoint。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** valid delta.
- **入力正本:** valid delta.
- **出力field:** DELTA_ACCEPTED checkpoint; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: canonical delta hash.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** checkpoint only; formal artifact remains absent.
- **保存先:** `runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** COMMIT-01.

### COMMIT-01 — 差分機械検証

- **目的:** 差分機械検証。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** three checkpoints and pre-scene HEAD.
- **入力正本:** checkpoint manifest/HEAD.
- **出力field:** validated commit plan; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: ID/before/evidence/hash/policy checks.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity; before/evidence exactness, allowed operation, lifecycle/knowledge-origin rules.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** COMMIT-04 only.
- **保存先:** `.staging/scene-commits then canon/generations and artifacts only at COMMIT-04`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** COMMIT-02.

### COMMIT-02 — ID mapping・new generation構築

- **目的:** ID mapping・new generation構築。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** validated plan.
- **入力正本:** COMMIT-01.
- **出力field:** staged generation; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: local-key mapping/new generation.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** COMMIT-04 only.
- **保存先:** `.staging/scene-commits then canon/generations and artifacts only at COMMIT-04`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** COMMIT-03.

### COMMIT-03 — scene artifact構築

- **目的:** scene artifact構築。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** staged generation and checkpoints.
- **入力正本:** COMMIT-02/checkpoints.
- **出力field:** staged scene artifact; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: adopted-byte artifact/scene manifest.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** COMMIT-04 only.
- **保存先:** `.staging/scene-commits then canon/generations and artifacts only at COMMIT-04`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** COMMIT-04.

### COMMIT-04 — HEAD更新・場面採用

- **目的:** staged generationとscene artifactを正式採用する。
- **実行条件:** COMMIT-02 generationとCOMMIT-03 artifactがともに検証済み。
- **入力field:** staged generation path, staged scene-manifest, commit ID, prior HEAD.
- **入力正本:** COMMIT-02/03 staged bytes。
- **出力field:** adopted generation, adopted scene artifact, updated HEAD.
- **出力状態:** `SCENE_COMMITTED`。
- **LLM生成field:** なし。
- **コード付与field:** adopted_at, final artifact paths, HEAD pointer timestamp。
- **参照禁止情報:** checkpointを正式artifactとして読むこと、未検証staging。
- **機械的検証:** generation/artifact rename成功、manifest/hash整合、HEAD置換前の全正本存在。
- **review観点:** なし。
- **retry種別:** なし; revision roundは消費しない。
- **採用条件:** generationとartifactをrename後、HEADを最後にatomic replaceできたこと。
- **保存先:** `canon/generations/<generation-id>/`, `artifacts/scenes/v01/c001/s001/`, `canon/HEAD`。
- **失敗時処理:** HEADを変更せずstagingをorphan判定対象にして停止。
- **次stage:** 次sceneのSC-01または巻末VH-01。

### VH-01 — 巻handoff生成

- **目的:** 巻handoff生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** adopted volume state/handoffs/evidence.
- **入力正本:** adopted artifacts/HEAD.
- **出力field:** handoff candidate; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: handoff fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** VH-ID only.
- **保存先:** `artifacts/volumes/v01/handoff.json or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** VH-02.

### VH-02 — 巻handoffレビュー

- **目的:** 巻handoffレビュー。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** handoff candidate.
- **入力正本:** VH-01.
- **出力field:** review result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: review issue fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** response structure retry; revision round: no.
- **採用条件:** VH-ID only.
- **保存先:** `artifacts/volumes/v01/handoff.json or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** VH-REV or VH-ID.

### VH-REV — 巻handoff修正

- **目的:** 巻handoff修正。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** handoff candidate and issues.
- **入力正本:** VH-01/02.
- **出力field:** revised handoff; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: handoff fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: one on entry.
- **採用条件:** VH-ID only.
- **保存先:** `artifacts/volumes/v01/handoff.json or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** VH-02.

### VH-ID — 巻handoff採用

- **目的:** 巻handoff採用。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** valid handoff.
- **入力正本:** final candidate.
- **出力field:** adopted handoff; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: hash/adopted metadata.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none; revision round: no.
- **採用条件:** VH-ID only.
- **保存先:** `artifacts/volumes/v01/handoff.json or audit/reviews/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** next VOL-01 or COMP-PRE.

### COMP-PRE — 監査前Gate

- **目的:** 監査前Gate。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** all adopted artifacts and HEAD.
- **入力正本:** HEAD/artifacts/evidence.
- **出力field:** pre-audit validation; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: completion checks.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** all planned units, nonempty prose, hash/ID integrity, required supports evidence, HEAD consistency.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none except transport for any external storage error; revision round: no.
- **採用条件:** COMP-SAVE only records; COMP-PUBLISH authorizes.
- **保存先:** `audit/completion/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** COMP-AUDIT.

### COMP-AUDIT — completion audit attempt

- **目的:** completion audit attempt。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** COMP-PRE success.
- **入力正本:** adopted manuscript/canon/state/evidence.
- **出力field:** audit attempt; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** LLM: audit fields.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** revision of manuscript/canon/audit result.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** meaning consistency, criteria and thread assessment; does not change any artifact.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** COMP-SAVE only records; COMP-PUBLISH authorizes.
- **保存先:** `audit/completion/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** COMP-SAVE or COMP-AUDIT.

### COMP-SAVE — 正常監査結果保存

- **目的:** 正常監査結果保存。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** structurally valid audit.
- **入力正本:** COMP-AUDIT.
- **出力field:** last valid audit record; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: audit hash/attempt metadata.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** transport or response structure retry; revision round: no.
- **採用条件:** COMP-SAVE only records; COMP-PUBLISH authorizes.
- **保存先:** `audit/completion/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** COMP-PUBLISH.

### COMP-PUBLISH — 公開前Gate

- **目的:** 公開前Gate。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** COMP-PRE and saved valid audit.
- **入力正本:** completion records.
- **出力field:** publish authorization; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: staging authorization.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none except transport for any external storage error; revision round: no.
- **採用条件:** COMP-SAVE only records; COMP-PUBLISH authorizes.
- **保存先:** `audit/completion/`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** OUT-01.

### OUT-01 — publication staging生成

- **目的:** publication staging生成。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** publish authorization.
- **入力正本:** adopted output sources.
- **出力field:** publication staging; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: Markdown/report/metadata.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** prompt, raw response, checkpoint, author truth, unadopted prose.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none except transport for any external storage error; revision round: no.
- **採用条件:** none.
- **保存先:** `.staging/publication`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** OUT-02.

### OUT-02 — publication検証

- **目的:** publication検証。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** staging.
- **入力正本:** OUT-01.
- **出力field:** validation result; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: hash/order/secret checks.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** output order/nonempty/hash/no forbidden internal or secret content.
- **review観点:** all target fields, state continuity, secret boundary, plan compatibility, prose evidence where applicable.
- **retry種別:** none except transport for any external storage error; revision round: no.
- **採用条件:** none.
- **保存先:** `.staging/publication/validation.json`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** OUT-03.

### OUT-03 — publication pointer更新

- **目的:** publication pointer更新。
- **実行条件:** prior stage has succeeded; required input is available.
- **入力field:** validated staging.
- **入力正本:** OUT-02.
- **出力field:** published pointer; its member fields are defined field-by-field in ledger/context/runtime contracts.
- **出力状態:** candidate, checkpoint, adopted record, or validation record as stated below.
- **LLM生成field:** code: publication ID/current pointer.
- **コード付与field:** operation ID, target ID, timestamps, hashes, retry counters, and adoption metadata; ID allocation only where this stage says code.
- **参照禁止情報:** unadopted candidate, raw prompt/response, secret configuration.
- **機械的検証:** Schema, required fields, enum, known IDs, source/hash integrity.
- **review観点:** candidate completeness and responsibility boundaries.
- **retry種別:** none except transport for any external storage error; revision round: no.
- **採用条件:** publication pointer.
- **保存先:** `publications/<publication-id> and output/CURRENT`.
- **失敗時処理:** keep last structurally valid candidate when one exists; otherwise stop without changing HEAD or formal artifact.
- **次stage:** complete.
