# Implementation acceptance

> Future implementation acceptance uses deterministic fakes. Each check asserts artifact contents, field values, paths, counters, and state transitions; it does not merely assert headings or labels.

## Revision and pipeline

- For INIT, SERIES, VOL, CH, SC, PROSE, DELTA, and VH, a structurally valid candidate with residual issues is adopted after `revision_rounds_used` reaches `max_revision_rounds`.
- Residual issues are appended, without overwrite, to `audit/residual-issues.jsonl`; the row includes stage, target, candidate hash, round, issues, and acceptance reason.
- INIT-05 has processor type `LLM generate`, calls the LLM, uses transport and response-structure retries, consumes no revision round, and rejects invalid local references, duplicates, missing required records, and forbidden references.
- `passed`, review severity, and clean-review wording do not independently control adoption.
- Every code-only stage has no LLM call and no retry counters.

## Data contracts

- Brief title, genre, target reader, avoid array, volumes 4..10, key people count, and canonical raw source hash are checked.
- INIT-01 through INIT-04 field lists, temporal rule mapping, and every local key mapping are checked.
- Series map, volume design, chapter design, scene card child records, `new_item_policy` record, and every continuity-delta child record are checked.
- `new_item_policy.max_items` is no greater than configured `max_new_items_per_scene`; its forbidden form has empty allowed types and zero maximum.
- Record, relationship, knowledge, reader knowledge, time relation, and chapter completion enums are checked.

## Candidate, runtime, and completion

- Every candidate directory has `candidate.json` or prose `candidate.md`, `review.json`, and `candidate-manifest.json`; candidate manifest is the resume source.
- run-manifest, run-state, counters, candidate, checkpoint, scene, commit, generation, and publication manifest field sets are validated.
- Completion attempts use `runtime/candidates/completion/attempt-NN.json`; malformed, decode-failed, empty, and whitespace-only responses exhaust response-structure retry separately from completion attempt count.
- A structurally valid completion audit advances to COMP-SAVE. Exhausted attempts without any valid audit cause a mechanical stop.
- Output order is COMP-PRE, COMP-AUDIT, COMP-SAVE, OUT-01 staging, OUT-02 validation, COMP-PUBLISH gate, OUT-03 adoption/CURRENT. `.staging/` is never adopted.

## Fixture and publication

- Genesis fixture checks raw source hash, brief, initial design, current canon, knowledge items, story state, evidence index, generation manifest, HEAD, series/volume/chapter plans, temporal rule, and all local key mappings.
- Scene and completion fixtures check direct baseline chains, before/after identity, quote offset/hash, artifact hashes, unique audit filenames, and distinct relationship participants.
- Completion fixture checks `v04/c003/s002` paths, story position 4/3/2, final time consistency, knowledge `before` consistency, final scene chapter resolution, and pre-completion generation 00000047 order 47.
- Public audit and publication exclude author truth, resolution conditions, raw prompt/response, secret prose, and workspace paths.
