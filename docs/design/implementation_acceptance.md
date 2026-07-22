# Implementation acceptance

> Future implementation acceptance uses deterministic fakes. Each check asserts paths, stored values, hashes, counters, and transitions rather than merely a successful exit.

## Required scenarios

- Every candidate, review, and revision stage resumes only from `candidate-manifest.json`.
- Candidate content and manifests use distinct paths; completion attempts use incrementing `attempt-NN.json` files.
- Completion structure retry is bounded inside an attempt; exhausted structure retries create a new completion attempt; exhausted attempts without a valid result mechanically stop.
- OUT-01 progresses to OUT-02, OUT-02 progresses to COMP-PUBLISH, and neither self-loops.
- COMP-PUBLISH writes only `gate-result.json`, adopts no publication directory, and OUT-03 atomically renames staging then replaces `output/CURRENT`.
- COMMIT-04, VH-ID, and OUT-03 are `adopted`; COMMIT-02/03 and OUT-01 are `staged_internal`; OUT-02 is `staged_internal_validation`; COMP-SAVE and COMP-PUBLISH are `audit`.
- Every revision-limit adoption appends the exact residual-issue record to `audit/residual-issues.jsonl`.
- INIT candidate tables, Writer View child records, Volume Handoff child records, and Completion Audit child records reject unknown fields.
- Continuity delta fields are accepted only when conforming to `evidence_and_updates.md`; a generic payload field is rejected.
- Enum registry values are enforced, including lifecycle and thread status separation.
- `max_new_items_per_scene` is required, defaults to 2, and rejects values outside 0..20.
- Every runtime manifest and every counter field is present and typed.
- Audit filenames contain call ID, operation ID, target ID, role, attempt, and revision round when applicable; two calls cannot collide.
- Initial, scene, and completion fixtures parse, resolve IDs, preserve before-state equality, satisfy quote/offset/hash validation, and use matching artifact hashes.
- Completion baseline is generation 47/order 47 and names the preceding scene, while final state is v04/c003/s002 at `最終日の夜`.
- Product retry, lifecycle, and current-data terminology matches the enum and runtime contracts.
