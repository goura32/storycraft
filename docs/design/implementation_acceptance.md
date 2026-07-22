# Implementation acceptance

> 次期実装の受入試験の唯一の正本。すべてdeterministic fakeで実行し、実LLMを必要としない。

## Schema and plan

- all stored objects reject unknown fields;
- every named enum and null/default rule in [ledger contracts](ledger_contracts.md) is tested;
- ID format, six-digit counters, gaps, no reuse, and `ev-000001` are tested;
- series map has all volumes once and consecutively; VOL-01 fails without adopted series map;
- all major output field tables accept valid fixtures and reject missing fields;
- thread progress validates 0..4 and status matrix;
- nested relationship path accepts `a_to_b.trust` and rejects flat paths;
- delta rejects free JSON Patch, before mismatch, unknown ID, unauthorized field, and non-verbatim evidence.

## Context and knowledge

- identical snapshot/config returns identical context hash and order;
- writer receives suspects/misunderstands/partially_knows with status and visible label;
- writer never receives author truth, resolution condition, other private knowledge, future plan, or unadopted candidate;
- hard limit uses model window/reserved output/protocol overhead; fallback estimator equals `ceil(code_points/1.5)`;
- every Builder overflow ordering is deterministic, JSON remains whole, and mandatory overflow stops;
- handoff context excludes full volume prose;
- completion audit context contains adopted manuscript artifacts, volume handoffs, current canon, story state, evidence index, initial design, series map.

## Generation, crash, and orphan recovery

- INIT-ID creates genesis generation `00000000`, matching initial manifest, then HEAD;
- startup rejects absent HEAD;
- crash at CARD_ACCEPTED, PROSE_FROZEN, DELTA_ACCEPTED, COMMIT_PREPARED, pre-HEAD, post-HEAD resumes at the documented phase and never duplicates commit;
- generation outside HEAD chain is moved to `runtime/orphans/`;
- scene artifact with a commit ID outside HEAD chain is moved to `runtime/orphans/`;
- reachable generation/artifact is never deleted;
- incompatible run manifest/config rejects resume.

## Timeout and budget

- connect/first-event/idle/total timeout closes stream and worker;
- transport retry never counts invalid JSON; invalid JSON/Schema consumes response-structure retry;
- every call attempt including retry and invalid structure consumes call/token/cost budget;
- provider usage absence uses configured estimator;
- unknown-price model with non-null maximum cost rejects startup;
- active elapsed accumulates across resume and excludes paused time.

## Publication and audit

- audit call/review/revision filenames are unique and match the canonical forms;
- crash immediately before publication pointer retains old `output/CURRENT`;
- crash immediately after pointer uses a complete renamed publication;
- output Markdown is ordered, nonempty, and excludes raw prompts, author truth, unadopted text, JSON, and scene boundary internals;
- completion with no structurally valid audit stops; valid audit with residual issues may publish;
- `completion-audit-final.json` selects only last valid audit.

## Samples and E2E

- every sample JSON parses;
- fixture/baseline references resolve;
- before/after snapshots and deltas match;
- evidence quote, offset, hash, and semantic claim validate;
- commit example updates HEAD only after new generation and manifest;
- publication example changes `output/CURRENT` only after destination exists;
- execute minimum one-volume, multi-volume, and interrupted-resume fake runs.
