# Pipeline contracts index and stage registry

This document is the normative integration contract and complete stage registry for the Storycraft version-1 pipeline.

It defines:

- the exact set and order of the 50 canonical Stage IDs;
- processor types, operation keys, target identities, Context builders, and artifact classes;
- common LLM generation, extraction, Review, and Revision semantics;
- Candidate, Checkpoint, staging, adoption, Completion, and Publication boundaries;
- normal transitions, conditional routes, terminal stops, and resume authorities;
- cross-family source-generation and pointer invariants;
- which detailed Pipeline document owns each stage family;
- forbidden transitions and implementation shortcuts.

Detailed stage contracts are authoritative in:

- [`contracts/pipeline/input_and_initial.md`](contracts/pipeline/input_and_initial.md)
- [`contracts/pipeline/planning.md`](contracts/pipeline/planning.md)
- [`contracts/pipeline/scene_generation.md`](contracts/pipeline/scene_generation.md)
- [`contracts/pipeline/commit_and_output.md`](contracts/pipeline/commit_and_output.md)

Supporting authorities are:

- [`configuration_contracts.md`](configuration_contracts.md)
- [`context_contracts.md`](context_contracts.md)
- [`ledger_contracts.md`](ledger_contracts.md)
- [`workspace_layout.md`](workspace_layout.md)
- [`runtime_and_recovery.md`](runtime_and_recovery.md)
- [`contracts/data/review_and_audit.md`](contracts/data/review_and_audit.md)
- [`implementation_acceptance.md`](implementation_acceptance.md)

This index does not weaken or replace the field-level contracts in those documents.

---

## 1. Canonical pipeline

The normal lifecycle is:

```text
Input
→ Initial design
→ Series planning
→ Volume planning
→ Chapter planning
→ Scene-card generation
→ prose generation
→ continuity extraction
→ Scene commit
→ next Scene / next Chapter / Volume Handoff
→ next Volume or Completion
→ Publication build
→ Publication Gate
→ Publication adoption
→ completed
```

The implementation must not skip a canonical stage because a downstream artifact appears easy to synthesize.

---

## 2. Exact stage count

Version 1 contains exactly:

```text
50 canonical stages
```

Distribution:

| family | stage count |
|---|---:|
| Input | 3 |
| Initial design | 8 |
| Planning | 12 |
| Scene generation | 12 |
| Scene commit | 4 |
| Volume Handoff | 4 |
| Completion | 3 |
| Publication | 4 |
| total | 50 |

A new Stage ID requires a design-contract revision.

A helper function, provider HTTP attempt, validation substep, or crash-recovery action is not automatically a Stage ID.

---

## 3. Canonical Stage-ID registry

| # | Stage ID | family | processor | operation key | target | artifact classes | Context builder | normal/conditional next |
|---:|---|---|---|---|---|---|---|---|
| 01 | `INPUT-01` | Input | `code` | `—` | `input` | adopted + audit | `—` | INPUT-02 (Keywords) / INIT-01 (Brief) |
| 02 | `INPUT-02` | Input | `llm_generate` | `brief` | `brief` | candidate + audit | `input_brief_builder` | INPUT-03 |
| 03 | `INPUT-03` | Input | `code` | `—` | `brief` | adopted + audit | `—` | INIT-01 |
| 04 | `INIT-01` | Initial design | `llm_generate` | `initial_design` | `concept` | candidate + audit | `init_concept_builder` | INIT-02 |
| 05 | `INIT-02` | Initial design | `llm_generate` | `initial_design` | `people` | candidate + audit | `init_people_builder` | INIT-03 |
| 06 | `INIT-03` | Initial design | `llm_generate` | `initial_design` | `world` | candidate + audit | `init_world_builder` | INIT-04 |
| 07 | `INIT-04` | Initial design | `llm_generate` | `initial_design` | `arcs` | candidate + audit | `init_arcs_builder` | INIT-05 |
| 08 | `INIT-05` | Initial design | `llm_generate` | `initial_design` | `bundle` | candidate + audit | `init_integrator_builder` | INIT-06 |
| 09 | `INIT-06` | Initial design | `llm_review` | `initial_design` | `bundle` | audit | `review_builder` | INIT-REV / INIT-ID |
| 10 | `INIT-REV` | Initial design | `llm_revise` | `initial_design` | `bundle` | candidate + audit | `revision_builder` | INIT-06 |
| 11 | `INIT-ID` | Initial design | `code` | `—` | `genesis` | staged_internal + staged_internal_validation + adopted + audit | `—` | SERIES-01 |
| 12 | `SERIES-01` | Planning | `llm_generate` | `series_map` | `series` | candidate + audit | `series_planner_builder` | SERIES-02 |
| 13 | `SERIES-02` | Planning | `llm_review` | `series_map` | `series` | audit | `review_builder` | SERIES-REV / SERIES-ID |
| 14 | `SERIES-REV` | Planning | `llm_revise` | `series_map` | `series` | candidate + audit | `revision_builder` | SERIES-02 |
| 15 | `SERIES-ID` | Planning | `code` | `—` | `series` | staged_internal + staged_internal_validation + adopted + audit | `—` | VOL-01 |
| 16 | `VOL-01` | Planning | `llm_generate` | `volume_design` | `vNN` | candidate + audit | `volume_planner_builder` | VOL-02 |
| 17 | `VOL-02` | Planning | `llm_review` | `volume_design` | `vNN` | audit | `review_builder` | VOL-REV / VOL-ID |
| 18 | `VOL-REV` | Planning | `llm_revise` | `volume_design` | `vNN` | candidate + audit | `revision_builder` | VOL-02 |
| 19 | `VOL-ID` | Planning | `code` | `—` | `vNN` | staged_internal + staged_internal_validation + adopted + audit | `—` | CH-01 |
| 20 | `CH-01` | Planning | `llm_generate` | `chapter_design` | `vNN-cNNN` | candidate + audit | `chapter_planner_builder` | CH-02 |
| 21 | `CH-02` | Planning | `llm_review` | `chapter_design` | `vNN-cNNN` | audit | `review_builder` | CH-REV / CH-ID |
| 22 | `CH-REV` | Planning | `llm_revise` | `chapter_design` | `vNN-cNNN` | candidate + audit | `revision_builder` | CH-02 |
| 23 | `CH-ID` | Planning | `code` | `—` | `vNN-cNNN` | staged_internal + staged_internal_validation + adopted + audit | `—` | SC-01 |
| 24 | `SC-01` | Scene generation | `llm_generate` | `scene_card` | `Scene ID` | candidate + audit | `scene_planner_builder` | SC-02 |
| 25 | `SC-02` | Scene generation | `llm_review` | `scene_card` | `Scene ID` | audit | `review_builder` | SC-REV / SC-CHK |
| 26 | `SC-REV` | Scene generation | `llm_revise` | `scene_card` | `Scene ID` | candidate + audit | `revision_builder` | SC-02 |
| 27 | `SC-CHK` | Scene generation | `code` | `—` | `Scene ID` | checkpoint + audit | `—` | PROSE-01 |
| 28 | `PROSE-01` | Scene generation | `llm_generate` | `prose` | `Scene ID` | candidate + audit | `prose_writer_builder` | PROSE-02 |
| 29 | `PROSE-02` | Scene generation | `llm_review` | `prose` | `Scene ID` | audit | `review_builder` | PROSE-REV / PROSE-CHK |
| 30 | `PROSE-REV` | Scene generation | `llm_revise` | `prose` | `Scene ID` | candidate + audit | `revision_builder` | PROSE-02 |
| 31 | `PROSE-CHK` | Scene generation | `code` | `—` | `Scene ID` | checkpoint + audit | `—` | DELTA-01 |
| 32 | `DELTA-01` | Scene generation | `llm_extract` | `continuity_delta` | `Scene ID` | candidate + audit | `continuity_builder` | DELTA-02 |
| 33 | `DELTA-02` | Scene generation | `llm_review` | `continuity_delta` | `Scene ID` | audit | `review_builder` | DELTA-REV / DELTA-CHK |
| 34 | `DELTA-REV` | Scene generation | `llm_revise` | `continuity_delta` | `Scene ID` | candidate + audit | `revision_builder` | DELTA-02 |
| 35 | `DELTA-CHK` | Scene generation | `code` | `—` | `Scene ID` | checkpoint + audit | `—` | COMMIT-01 |
| 36 | `COMMIT-01` | Scene commit | `code` | `—` | `Scene ID` | checkpoint + audit | `—` | COMMIT-02 |
| 37 | `COMMIT-02` | Scene commit | `code` | `—` | `Scene ID` | staged_internal + audit | `—` | COMMIT-03 |
| 38 | `COMMIT-03` | Scene commit | `code` | `—` | `Scene ID` | staged_internal + staged_internal_validation + audit | `—` | COMMIT-04 |
| 39 | `COMMIT-04` | Scene commit | `code` | `—` | `Scene ID` | adopted + audit | `—` | SC-01 / CH-01 / VH-01 |
| 40 | `VH-01` | Volume handoff | `llm_generate` | `volume_handoff` | `vNN` | candidate + audit | `volume_handoff_builder` | VH-02 |
| 41 | `VH-02` | Volume handoff | `llm_review` | `volume_handoff` | `vNN` | audit | `review_builder` | VH-REV / VH-ID |
| 42 | `VH-REV` | Volume handoff | `llm_revise` | `volume_handoff` | `vNN` | candidate + audit | `revision_builder` | VH-02 |
| 43 | `VH-ID` | Volume handoff | `code` | `—` | `vNN` | staged_internal + staged_internal_validation + adopted + audit | `—` | VOL-01 / COMP-PRE |
| 44 | `COMP-PRE` | Completion | `code` | `—` | `completion` | audit | `completion_builder (after precondition)` | COMP-AUDIT |
| 45 | `COMP-AUDIT` | Completion | `llm_generate` | `completion_audit` | `completion` | candidate + audit | `completion_builder` | COMP-SAVE |
| 46 | `COMP-SAVE` | Completion | `code` | `—` | `completion` | audit | `—` | OUT-01 |
| 47 | `OUT-01` | Publication | `code` | `—` | `pub-NNNNNN` | staged_internal + audit | `—` | OUT-02 |
| 48 | `OUT-02` | Publication | `code` | `—` | `pub-NNNNNN` | staged_internal_validation + staged_internal + audit | `—` | COMP-PUBLISH |
| 49 | `COMP-PUBLISH` | Publication | `code` | `—` | `pub-NNNNNN` | audit | `—` | OUT-03 / terminal stop |
| 50 | `OUT-03` | Publication | `code` | `—` | `pub-NNNNNN` | adopted + audit | `—` | completed |

The registry order is normative for documentation, traces, tests, and stage enumeration.

Runtime progression follows transitions, not ordinal arithmetic.

---

## 4. Stage-ID syntax

Canonical Stage IDs are uppercase ASCII and use one hyphen:

```text
PREFIX-SUFFIX
```

Examples:

```text
INPUT-01
INIT-REV
COMMIT-04
COMP-PUBLISH
```

Rules:

- exact case;
- no spaces;
- no underscore;
- no alias;
- no numeric truncation;
- no unregistered suffix.

Forbidden aliases include:

```text
CRITIQUE
REVIEW-01
CONTINUITY
PUBLISH
COMMIT
```

---

## 5. Processor types

The only canonical processor types are:

```text
code
llm_generate
llm_extract
llm_review
llm_revise
```

### 5.1 `code`

Deterministic local processing.

It may:

```text
normalize
validate
allocate IDs
calculate hashes/offsets
build Context
construct roots/manifests
stage and atomically adopt
reconcile Run state
```

It does not call an LLM.

### 5.2 `llm_generate`

Creates a new semantic candidate or Completion assessment from an immutable Context snapshot.

### 5.3 `llm_extract`

Extracts structured continuity proposals from exact frozen prose.

It remains an LLM stage but has stricter code-owned-field boundaries.

### 5.4 `llm_review`

Returns only Review content:

```text
summary
issues
```

It does not return routing or a corrected candidate.

### 5.5 `llm_revise`

Returns a complete replacement candidate.

It never returns a patch, diff, or partial branch.

---

## 6. Operation-key registry

The exact configuration operation keys are:

```text
brief
initial_design
series_map
volume_design
chapter_design
scene_card
prose
continuity_delta
volume_handoff
completion_audit
```

Every LLM stage maps to exactly one key.

Code stages have no operation key.

An unknown or missing key is a configuration error before provider execution.

---

## 7. Artifact-class registry

The only artifact classes are:

```text
candidate
checkpoint
staged_internal
staged_internal_validation
adopted
audit
```

Meaning:

| class | meaning |
|---|---|
| `candidate` | structurally valid generated/revised content not yet adopted |
| `checkpoint` | frozen Scene transaction input and phase authority |
| `staged_internal` | unadopted deterministic transaction content |
| `staged_internal_validation` | unadopted code validation result |
| `adopted` | immutable artifact reachable from its adoption point |
| `audit` | immutable Review/call/operation/completion/gate evidence |

A stage may produce multiple separate artifacts with different classes.

Composite class strings are forbidden.

---

## 8. Target identities

| family | target form |
|---|---|
| Input source | `input` |
| Brief | `brief` |
| Initial components | `concept`, `people`, `world`, `arcs`, `bundle`, `genesis` |
| Series map | `series` |
| Volume design/Handoff | `vNN` |
| Chapter design | `vNN-cNNN` |
| Scene families/Commit | `vNN-cNNN-sNNN` |
| Completion | `completion` |
| Publication | `pub-NNNNNN` after allocation |

The target in Run state, Candidate manifest, Context snapshot, Review, audit filename, and artifact path must agree.

---

# Part I: Universal stage execution

## 9. Stage entry

Before any stage begins, code validates:

```text
workspace lock for mutation
Run manifest
Run state
Effective config and compatibility
next_stage equals requested stage
target identity and coordinates
current HEAD/CURRENT where applicable
active Candidate/Checkpoint references
required source paths and hashes
budget and audit capacity
```

A CLI `step` command may execute at most one canonical stage boundary.

---

## 10. Source snapshot

Every LLM call uses one immutable Context snapshot.

The snapshot binds:

```text
operation
target
source Generation
source artifact refs/hashes
Effective-config hash
prompt version
response-Schema version
token budget
view type and sensitivity
payload
```

The filename equals the Context SHA-256.

The snapshot has no timestamp and no self-hash.

---

## 11. Source-generation recheck

A candidate may be generated from one source Generation and reviewed later.

Before each of these boundaries, code rechecks source identity:

```text
Context construction
provider call reuse
Checkpoint freeze
plan adoption
Scene commit
Handoff adoption
Completion precondition
Publication build/Gate
```

If a required source changed:

- do not rebase the candidate;
- mark/invalidate it as stale history;
- regenerate from the current authority;
- do not count the regeneration as semantic Revision.

---

## 12. Call-ID allocation

Before a provider request:

1. validate preflight and token budget;
2. allocate a new Call ID;
3. persist the counter increment;
4. construct the unique LLM-call audit filename;
5. send the request.

A failed or ambiguous call consumes its Call ID.

No Call ID is reused.

---

## 13. Transport retry

Transport retry covers:

```text
connection/TLS failure
connect timeout
first-event timeout
idle timeout
total-call timeout
registered retryable HTTP status/provider error
```

It does not cover:

```text
invalid JSON
Schema failure
semantic Review issue
Completion incomplete
```

Every provider HTTP attempt receives a distinct Call ID and audit record.

---

## 14. Response-structure retry

Response-structure retry covers:

```text
invalid UTF-8 response
invalid JSON
response-Schema failure
prose-format structural failure
unknown field
wrong discriminator branch
```

It remains within one logical candidate/Completion attempt according to the detailed contract.

It does not consume a semantic revision round.

---

## 15. Semantic issue

A structurally valid candidate may have semantic Review issues.

This is not a provider/response error.

It routes through the Review/Revision state machine.

The original candidate and Review remain immutable history.

---

## 16. Durable LLM success

An LLM generation/extraction/revision stage is complete only when:

```text
response was structurally valid
code normalization/validation passed
candidate bytes are durable
Candidate manifest is durable
Context and audit references are durable
Run state records the next stage
```

A successful provider response alone is not stage completion.

---

## 17. Audit is not candidate authority

A raw provider response in an LLM-call audit is never promoted during recovery.

If audit says success but candidate/manifest durability did not complete:

```text
preserve usage and Call IDs
repeat the provider operation with a new Call ID
```

This conservative rule prevents ambiguous audit-to-candidate promotion.

---

# Part II: Candidate lifecycle

## 18. Versioned candidate paths

Most candidate families use:

```text
runtime/candidates/<logical-target>/v0001/
runtime/candidates/<logical-target>/v0002/
...
```

Every version contains its own:

```text
candidate artifact
review.json when reviewed
candidate-manifest.json
```

A revision creates the next version.

No earlier candidate or Review is overwritten.

Completion attempts are the registered exception and use `attempt-NN.json`.

---

## 19. Logical candidate owner

The logical owner remains the original generation/extraction stage.

Examples:

```text
INIT-REV version owner = INIT-05
SERIES-REV owner = SERIES-01
PROSE-REV owner = PROSE-01
DELTA-REV owner = DELTA-01
VH-REV owner = VH-01
```

The Candidate manifest records the owner processor type.

Revision does not change a candidate into an `llm_revise`-owned artifact.

---

## 20. Candidate-manifest authority

Only:

```text
runtime/run-state.json.active_candidate_manifest_path
```

selects the active candidate.

A directory scan, highest version number, or newest file does not select it.

The active manifest binds:

```text
operation/owner
target
Context path/hash
candidate path/hash
Review path/hash
version and previous version
retry/revision counters
status
next stage
```

---

## 21. Candidate statuses

Canonical status meanings include:

```text
initialized
candidate_valid
reviewed
revision_required
ready_for_adoption
exhausted
failed
```

The exact enum and required fields are owned by `runtime_records.md`.

A status transition requires a complete atomic Candidate-manifest replacement.

---

## 22. Mechanical validation before Review

Review runs only on a mechanically valid candidate.

Before Review, code validates:

```text
exact Schema/format
unknown-field rejection
target/path identity
source/hash identity
cross-reference resolvability
required counts/coverage
authorization and before values where applicable
```

A mechanically invalid candidate uses response-structure retry or fails after exhaustion.

It is not sent to semantic Review.

---

# Part III: Review and Revision

## 23. Review response

The LLM returns exactly:

```text
summary
issues
```

Code adds:

```text
operation/role/target
candidate identity and version
Context hash
normalized issue IDs/order/counts
review_status
Call ID
timestamp
```

Review is an `audit` artifact.

---

## 24. Review decision

For normal reviewed candidate families:

```text
issues empty
→ ready_for_adoption
→ Checkpoint or *-ID stage

issues nonempty and revision budget remains
→ revision_required
→ *-REV

issues nonempty and revision budget exhausted
→ append normalized residual issues
→ candidate remains mechanically valid
→ exhausted/ready_for_adoption
→ Checkpoint or *-ID stage
```

A mechanical defect never becomes a residual semantic issue.

---

## 25. Revision input

Revision Context includes:

```text
complete current candidate
complete Review
applicable source snapshot
allowed change constraints
residual constraints
```

The LLM returns a complete replacement.

Code creates the next immutable candidate version.

---

## 26. Revision count

`max_revision_rounds` counts successful structurally valid semantic replacement rounds.

It does not count:

```text
transport retry
response-structure retry
staleness regeneration
initial generation
Review call
```

Zero revision rounds is valid.

---

## 27. Residual issues

After semantic Revision exhaustion:

- issue records are normalized;
- exact duplicate-safe JSONL records are appended;
- later Context may receive safe residual constraints;
- raw private Review content is not copied into Writer view or publication.

Residual issues do not waive mechanical constraints.

---

## 28. Completion exception

Completion audit does not use the ordinary Review/Revision loop.

Rules:

```text
COMP-PRE produces a mechanical precondition first
Completion Context is built after that precondition
COMP-AUDIT may use bounded transport/structure retries and bounded attempt-NN files
the first structurally valid Completion assessment stops attempts
complete, complete_with_residual_issues, and incomplete are all valid semantic results
valid incomplete is never retried to obtain complete
COMP-SAVE stores the selected result unchanged
```

---

# Part IV: Code-only freeze and adoption stages

## 29. Checkpoint stages

Code-only checkpoint stages are:

```text
SC-CHK
PROSE-CHK
DELTA-CHK
COMMIT-01
COMMIT-03 phase advance
```

The Scene Checkpoint manifest is the phase authority.

A later-phase file without a matching manifest phase is not promoted.

---

## 30. Plan adoption stages

Plan adoption stages are:

```text
SERIES-ID
VOL-ID
CH-ID
```

They:

1. validate the ready candidate and Review;
2. recheck source HEAD and parent-plan hashes;
3. create deterministic adopted metadata;
4. write staging and Validation;
5. move the immutable plan to its final path;
6. update Run state.

They do not change `canon/HEAD`.

---

## 31. Story adoption stages

Story adoption stages are:

```text
INIT-ID
COMMIT-04
VH-ID
```

Their story adoption point is:

```text
canon/HEAD
```

All Generation and conditional Scene/Handoff artifacts must be durable before HEAD changes.

---

## 32. Publication adoption stage

Only:

```text
OUT-03
```

adopts a Publication.

Its adoption point is:

```text
output/CURRENT
```

COMP-PUBLISH only writes an external Gate and must not rename or change CURRENT.

---

## 33. ID allocation boundaries

| ID category | allocation stage |
|---|---|
| Genesis story IDs | `INIT-ID` after complete dry validation |
| Scene Commit/Generation ID | `COMMIT-02` |
| Scene-created persistent IDs | `COMMIT-02` |
| Scene Evidence IDs | `COMMIT-02` |
| Handoff Commit/Generation ID | `VH-ID` transaction preparation |
| Publication ID | `OUT-01` |
| Call ID | immediately before each provider HTTP attempt |

`COMMIT-01` allocates nothing.

All allocations are persist-before-use and never reused.

---

# Part V: Family contracts

## 34. Input branch

### Brief mode

```text
INPUT-01
→ INIT-01
```

INPUT-01 normalizes and adopts the supplied Brief.

### Keywords mode

```text
INPUT-01
→ INPUT-02
→ INPUT-03
→ INIT-01
```

INPUT-02 generates content only.

INPUT-03 adds code-owned source/profile/timestamp metadata and adopts `input/brief.json`.

Exactly one input mode is permitted.

---

## 35. Initial-design sequence

```text
INIT-01 Concept
→ INIT-02 People
→ INIT-03 World/time
→ INIT-04 arcs/Threads/Ending/Knowledge
→ INIT-05 integrated bundle
→ INIT-06 Review
→ INIT-REV or INIT-ID
```

INIT-01 through INIT-04 have distinct response roots.

INIT-05 must produce a complete independently valid integrated bundle.

INIT-ID creates Genesis and writes HEAD last.

---

## 36. Genesis postcondition

A successful INIT-ID guarantees:

```text
canon/HEAD = 00000000
Commit = commit-00000000
current_order = 0
successful_scene_commits = 0
complete Character/Relationship/Major-Thread State
sparse nondefault Knowledge State
empty Evidence index
Story-clock position fields null
```

Next stage:

```text
SERIES-01
```

---

## 37. Series planning sequence

```text
SERIES-01
→ SERIES-02
→ SERIES-REV or SERIES-ID
```

Series planning source Generation is fixed to Genesis.

The Series map covers all Volumes, required Major Thread continuity, final required resolution, and Ending-criterion chain.

After SERIES-ID:

```text
next_stage = VOL-01
target = v01
```

---

## 38. Volume planning sequence

```text
VOL-01
→ VOL-02
→ VOL-REV or VOL-ID
```

Source Generation is HEAD at the start of that Volume.

For Volume greater than one, Context includes the adopted previous Volume Handoff.

After VOL-ID:

```text
next_stage = CH-01
target = vNN-c001
```

---

## 39. Chapter planning sequence

```text
CH-01
→ CH-02
→ CH-REV or CH-ID
```

Source Generation is HEAD at Chapter start.

For Chapter greater than one, Context uses the previous Chapter's final adopted Scene and safe handoff summary.

After CH-ID:

```text
next_stage = SC-01
target = first Scene of Chapter
```

---

## 40. Plan immutability

An adopted plan is never rewritten because later prose or State differs.

Later divergence is represented by:

```text
Review/residual issues
adopted prose
committed continuity delta
Volume Handoff
Completion audit
```

A conflicting file already at the final plan path is a mechanical stop.

---

## 41. Scene source-generation invariant

For one Scene lifecycle:

```text
SC-01 source Generation
=
PROSE-01 source Generation
=
DELTA-01 source Generation
=
COMMIT-01 source Generation
```

The source remains fixed through COMMIT-01 preflight.

If HEAD changes before adoption and the Scene is not already adopted:

```text
invalidate the full Scene candidate/checkpoint chain
restart at SC-01
```

No rebase is permitted.

---

## 42. Scene-card sequence

```text
SC-01
→ SC-02
→ SC-REV or SC-CHK
```

SC-01 returns content only.

SC-CHK injects and freezes:

```text
Scene identity
source Generation and plan hashes
starting Thread/Knowledge values
allowed_update_targets
safe forbidden disclosures
new-item policy
length guidance
created timestamp
```

Checkpoint phase becomes:

```text
CARD_ACCEPTED
```

---

## 43. Prose sequence

```text
PROSE-01
→ PROSE-02
→ PROSE-REV or PROSE-CHK
```

PROSE calls use Writer-safe Context.

They must not receive:

```text
Thread author truth/resolution condition
Knowledge author truth
Ending source text
private non-POV goal/pressure/emotion
update mechanics
```

PROSE-CHK freezes canonical prose and advances to:

```text
PROSE_FROZEN
```

---

## 44. Continuity sequence

```text
DELTA-01
→ DELTA-02
→ DELTA-REV or DELTA-CHK
```

DELTA-01 is `llm_extract`.

The provider response does not contain:

```text
before values
persistent IDs
Evidence IDs
offsets/hashes
Commit/Generation IDs
timestamps
```

Code injects before values and validates authorization.

DELTA-CHK advances to:

```text
DELTA_ACCEPTED
```

No story/Evidence ID is allocated yet.

---

## 45. Scene commit sequence

```text
COMMIT-01
→ COMMIT-02
→ COMMIT-03
→ COMMIT-04
```

### COMMIT-01

Dry validation and deterministic allocation requests.

No allocation.

### COMMIT-02

Persist IDs, resolve local keys, create Evidence mappings, merge plan, and staged after roots.

### COMMIT-03

Create committed delta, Evidence index, Scene/Commit/Generation manifests, Validation, and `COMMIT_PREPARED`.

### COMMIT-04

Rename Generation and Scene, revalidate, replace HEAD last, then update Run state.

---

## 46. Scene post-commit route

COMMIT-04 derives exactly one route from immutable plans.

### Next Scene

```text
COMMIT-04
→ SC-01
```

### Next Chapter

```text
COMMIT-04
→ CH-01
```

### Volume complete

```text
COMMIT-04
→ VH-01
```

A route is not chosen from directory presence.

---

## 47. Volume-handoff sequence

```text
VH-01
→ VH-02
→ VH-REV or VH-ID
```

The candidate summarizes actual adopted Volume ending State and selects Thread dispositions.

VH-ID creates:

```text
artifacts/handoffs/vNN.json
new Commit/Generation with commit_type=volume_handoff
```

Only:

```text
thread_states[].volume_disposition
```

may change.

Story clock/order and successful Scene count do not change.

---

## 48. Handoff post-adoption route

### Nonfinal Volume

```text
VH-ID
→ VOL-01
target = next Volume
```

### Final Volume

```text
VH-ID
→ COMP-PRE
```

Completion always starts from the final Handoff HEAD, not directly from the final Scene Generation.

---

## 49. Completion precondition and Context order

COMP-PRE performs all mechanical checks before a Completion call.

Required noncyclic order:

```text
Completion precondition is constructed and hashed
→ Completion Context includes the passing precondition and is hashed
→ COMP-AUDIT saved attempt refers to both hashes
```

The precondition does not contain the Context hash.

If the precondition fails:

```text
no Completion LLM call
run fails mechanically
```

---

## 50. Completion assessment

COMP-AUDIT returns exactly one structurally valid semantic assessment per accepted attempt:

```text
complete
complete_with_residual_issues
incomplete
```

COMP-SAVE stores the selected private audit.

A valid `incomplete` result:

- is not retried;
- may proceed through deterministic diagnostic publication build/Validation;
- must fail COMP-PUBLISH;
- ends in manual intervention without publication adoption.

---

## 51. Publication build sequence

```text
OUT-01
→ OUT-02
→ COMP-PUBLISH
→ OUT-03
```

OUT-01 allocates the Publication ID and builds payload plus a provisional build manifest.

OUT-02 validates payload, writes Publication Validation, builds final Manifest, and removes the provisional file.

COMP-PUBLISH writes the rename-stable Gate.

OUT-03 adopts pointer-last.

---

## 52. Publication hash order

Noncyclic order:

```text
payload files
→ payload_set_sha256
→ Publication Validation
→ Validation file reference
→ Manifest.files
→ content_set_sha256
→ Publication manifest
→ Gate publication_snapshot_sha256
```

The Manifest does not list itself.

The Validation does not hash the Manifest.

---

## 53. Gate semantics

Gate passes only when:

```text
Completion assessment is complete or complete_with_residual_issues
and
all mechanical Completion/Publication checks pass
```

Gate fail categories:

```text
semantic incomplete
mechanical mismatch
```

COMP-PUBLISH changes no adopted pointer or file.

---

## 54. Publication adoption

OUT-03 validates the same Gate snapshot:

1. before normal staging rename;
2. after rename under the final root;
3. before CURRENT replacement.

Explicit post-rename recovery is allowed only with the exact original passing Gate and Run-state transaction identity.

After CURRENT changes, Run state is completed.

---

# Part VI: Normal transition graph

## 55. Full graph

```text
INPUT-01
├─ Brief mode ───────────────────────────────→ INIT-01
└─ Keywords mode → INPUT-02 → INPUT-03 ─────→ INIT-01

INIT-01 → INIT-02 → INIT-03 → INIT-04 → INIT-05 → INIT-06
                                                       ├─ issues/revision available → INIT-REV → INIT-06
                                                       └─ ready/exhausted-valid ─────→ INIT-ID

INIT-ID → SERIES-01 → SERIES-02
                         ├─ revise → SERIES-REV → SERIES-02
                         └─ ready ─→ SERIES-ID

SERIES-ID → VOL-01 → VOL-02
                         ├─ revise → VOL-REV → VOL-02
                         └─ ready ─→ VOL-ID

VOL-ID → CH-01 → CH-02
                   ├─ revise → CH-REV → CH-02
                   └─ ready ─→ CH-ID

CH-ID → SC-01 → SC-02
                   ├─ revise → SC-REV → SC-02
                   └─ ready ─→ SC-CHK

SC-CHK → PROSE-01 → PROSE-02
                         ├─ revise → PROSE-REV → PROSE-02
                         └─ ready ─→ PROSE-CHK

PROSE-CHK → DELTA-01 → DELTA-02
                           ├─ revise → DELTA-REV → DELTA-02
                           └─ ready ─→ DELTA-CHK

DELTA-CHK → COMMIT-01 → COMMIT-02 → COMMIT-03 → COMMIT-04
                                                        ├─ next Scene ─→ SC-01
                                                        ├─ next Chapter → CH-01
                                                        └─ Volume done ─→ VH-01

VH-01 → VH-02
          ├─ revise → VH-REV → VH-02
          └─ ready ─→ VH-ID
                         ├─ next Volume → VOL-01
                         └─ final Volume → COMP-PRE

COMP-PRE → COMP-AUDIT → COMP-SAVE → OUT-01 → OUT-02 → COMP-PUBLISH
                                                                   ├─ pass → OUT-03 → completed
                                                                   └─ fail → terminal stopped/failed
```

---

## 56. Transition ownership

Only the completing stage writes its postcondition and `next_stage`.

A stage must not pre-complete the next stage.

Examples:

```text
SC-CHK may set next_stage=PROSE-01
but may not create a prose candidate

COMP-PUBLISH may set next_stage=OUT-03
but may not rename the publication

COMMIT-03 may set next_stage=COMMIT-04
but may not change HEAD
```

---

## 57. Unknown transition

Any transition not present in the detailed contracts is invalid.

The implementation must reject:

```text
INIT-05 → INIT-ID without INIT-06 Review
SC-02 → PROSE-01 without SC-CHK
PROSE-CHK → COMMIT-01
DELTA-CHK → COMMIT-02
COMMIT-03 → SC-01
VH-02 → VOL-01
COMP-SAVE → COMP-PUBLISH
OUT-02 → OUT-03
COMP-PUBLISH → completed
```

---

# Part VII: Resume sources

## 58. Per-stage resume authority

| Stage | authoritative resume source |
|---|---|
| `INPUT-01` | adopted input source + Run state |
| `INPUT-02` | active Candidate manifest, else adopted Keyword source |
| `INPUT-03` | active valid INPUT-02 candidate + Run state |
| `INIT-01` | active Candidate manifest, else adopted Brief |
| `INIT-02` | active Candidate manifest, else Brief + INIT-01 |
| `INIT-03` | active Candidate manifest, else Brief + earlier INIT candidates |
| `INIT-04` | active Candidate manifest, else Brief + earlier INIT candidates |
| `INIT-05` | active bundle Candidate manifest, else fixed INIT-01..04 versions |
| `INIT-06` | active bundle candidate + referenced Review when durable |
| `INIT-REV` | active reviewed version + Revision Context |
| `INIT-ID` | ready bundle + Genesis staging, or valid Genesis HEAD |
| `SERIES-01` | active Candidate manifest, else Genesis HEAD + Initial design |
| `SERIES-02` | active Series candidate + referenced Review |
| `SERIES-REV` | active reviewed Series version |
| `SERIES-ID` | ready Series candidate + plan staging, or adopted Series map |
| `VOL-01` | active Candidate manifest, else Volume-start HEAD + Series map + prior Handoff |
| `VOL-02` | active Volume candidate + referenced Review |
| `VOL-REV` | active reviewed Volume version |
| `VOL-ID` | ready Volume candidate + plan staging, or adopted Volume design |
| `CH-01` | active Candidate manifest, else Chapter-start HEAD + parent plans |
| `CH-02` | active Chapter candidate + referenced Review |
| `CH-REV` | active reviewed Chapter version |
| `CH-ID` | ready Chapter candidate + plan staging, or adopted Chapter design |
| `SC-01` | active Candidate manifest, else exact Scene-entry HEAD/plans |
| `SC-02` | active Scene-card candidate + referenced Review |
| `SC-REV` | active reviewed Scene-card version |
| `SC-CHK` | ready Scene-card candidate or valid CARD_ACCEPTED checkpoint |
| `PROSE-01` | active Candidate manifest, else CARD_ACCEPTED checkpoint |
| `PROSE-02` | active prose candidate + referenced Review |
| `PROSE-REV` | active reviewed prose version |
| `PROSE-CHK` | ready prose candidate or valid PROSE_FROZEN checkpoint |
| `DELTA-01` | active Candidate manifest, else PROSE_FROZEN checkpoint |
| `DELTA-02` | active continuity candidate + referenced Review |
| `DELTA-REV` | active reviewed continuity version |
| `DELTA-CHK` | ready continuity candidate or valid DELTA_ACCEPTED checkpoint |
| `COMMIT-01` | DELTA_ACCEPTED checkpoint + current HEAD |
| `COMMIT-02` | passing Commit plan + referenced transaction |
| `COMMIT-03` | transaction manifest + merge plan + checkpoint |
| `COMMIT-04` | COMMIT_PREPARED transaction, or valid HEAD Scene commit |
| `VH-01` | active Candidate manifest, else final-Scene HEAD + Volume plans |
| `VH-02` | active Handoff candidate + referenced Review |
| `VH-REV` | active reviewed Handoff version |
| `VH-ID` | ready Handoff candidate + staging, or valid HEAD Handoff commit |
| `COMP-PRE` | final Handoff HEAD + passing precondition/Context when valid |
| `COMP-AUDIT` | passing precondition + exact Completion Context + Candidate manifest |
| `COMP-SAVE` | Candidate-manifest-selected valid attempt or saved private audit |
| `OUT-01` | accepted private audit + valid provisional staging |
| `OUT-02` | payload staging + provisional build manifest, or finalized staging |
| `COMP-PUBLISH` | Completion records + finalized staged publication + existing Gate |
| `OUT-03` | passing Gate + selected staging/final root, or valid CURRENT |

Audit and normal log files are not authoritative resume sources.

---

## 59. Candidate-level resume

If a valid Candidate manifest is durable and Run state is behind:

```text
reconcile to the manifest's exact next stage
do not repeat the completed provider call
```

If the candidate exists without a valid manifest:

```text
quarantine/regenerate
do not synthesize a manifest
```

---

## 60. Checkpoint-level resume

For the exact expected Scene:

| phase | resume stage |
|---|---|
| `CARD_ACCEPTED` | `PROSE-01` |
| `PROSE_FROZEN` | `DELTA-01` |
| `DELTA_ACCEPTED` | `COMMIT-01` |
| `COMMIT_PREPARED` | `COMMIT-04` |

A valid active candidate may place execution later within the phase's candidate family.

---

## 61. Pointer-level reconciliation

A valid HEAD/CURRENT pointer proves adoption even when Run state is behind.

Examples:

```text
HEAD Scene Commit
→ derive next Scene/Chapter/Handoff route

HEAD Handoff Commit
→ derive next Volume/Completion route

CURRENT valid
→ reconcile Run completed
```

No LLM call or ID allocation repeats.

---

## 62. Pre-pointer final-looking content

Before HEAD/CURRENT changes:

```text
Generation/Scene/Handoff/Publication directory is unadopted
```

Ordinary startup never adopts it by inference.

Publication post-rename recovery is the only registered explicit recovery and still requires the original Gate snapshot.

---

# Part VIII: Failure and stop behavior

## 63. Mechanical failure

Examples:

```text
Schema/path/hash mismatch
invalid pointer graph
counter regression
source-generation mismatch at adoption
unauthorized continuity update
Evidence mismatch
committed-delta/root mismatch
Publication hash mismatch
```

Result:

```text
run_status = failed
stop_reason_code = mechanical_error
next_stage = null
```

when a terminal failure is required.

---

## 64. Provider exhaustion

Transport or response-structure exhaustion:

- preserves all counters/audits;
- writes no structurally invalid candidate;
- ends failed unless the detailed stage defines a recoverable boundary;
- requires explicit resume after cause/budget validation.

---

## 65. User stop

A user stop is honored at a safe durable boundary.

It does not interrupt:

```text
counter persist-before-use
atomic manifest replacement
directory rename/pointer-last transaction
```

Resume validates all authorities before setting the run back to running.

---

## 66. Budget stop

Before each LLM call, code recomputes remaining:

```text
Call
token
cost
active elapsed
audit storage
```

A budget stop occurs before the prohibited call.

Increasing an increase-only budget does not reset usage.

---

## 67. Manual intervention

Automatic continuation is forbidden for:

```text
invalid HEAD/CURRENT graph
counter lower than observed IDs
conflicting adopted plan
both staging and final Publication roots
unsupported immutable config migration
valid Completion incomplete
```

---

## 68. Completed state

Completed requires:

```text
last_completed_stage = OUT-03
next_stage = null
output/CURRENT valid
current_publication_id = CURRENT
run_status = completed
stop_reason_code = completed
```

A normal completed run does not reopen generation.

---

# Part IX: Cross-pipeline invariants

## 69. One active story target

At any time, Run state identifies at most one active semantic target:

```text
Brief
Initial bundle
one plan
one Scene family
one Volume Handoff
Completion
one Publication transaction
```

Unrelated candidate trees do not alter the route.

---

## 70. One active Scene checkpoint

At most one Scene checkpoint is active for the run.

Its Scene ID must equal Run-state target coordinates.

A future or unrelated checkpoint is not selected.

---

## 71. Plan-before-Scene

A Scene cannot start until its exact:

```text
Series map
Volume design
Chapter design
```

are adopted and hash-valid.

A Scene does not infer a plan from prose or Context.

---

## 72. Review-before-freeze/adoption

Every reviewed candidate family must have a valid Review before:

```text
SC-CHK
PROSE-CHK
DELTA-CHK
INIT-ID
SERIES-ID
VOL-ID
CH-ID
VH-ID
```

Residual-exhaustion adoption still requires the last Review and residual records.

---

## 73. Freeze-before-commit

A Scene Commit requires:

```text
frozen Scene card
frozen canonical prose
frozen validated candidate delta
DELTA_ACCEPTED checkpoint
```

No Commit stage calls an LLM or modifies frozen Scene card/prose.

---

## 74. Pointer-last

Adoption points are always last:

```text
Genesis/Scene/Handoff:
  canon/HEAD

Publication:
  output/CURRENT
```

Run-state completion/reconciliation follows pointer durability.

---

## 75. No pointer rollback

Version 1 normal execution and recovery do not roll back HEAD or CURRENT.

Corrections create new Generations/Publications through registered operations.

---

## 76. Generation/order distinction

Every Scene commit:

```text
Generation suffix +1
current_order +1
```

Every Handoff commit:

```text
Generation suffix +1
current_order unchanged
```

Therefore tests and routes must use manifests/Commit type, not suffix equality.

---

## 77. Completion is read-only for story ledgers

COMP and OUT stages never change:

```text
canon/HEAD
Canon roots
Story State
Evidence index
plans
Scene artifacts
Handoffs
```

They assess and derive publication artifacts only.

---

## 78. Private/public boundary

Private Author information may appear in:

```text
Planner Context
private Review extension
Handoff
Completion private audit
Canon author-only fields
```

It must not appear in:

```text
Writer Context
Continuity Context
reader-facing manuscript
publication-safe report
public metadata
```

---

## 79. Deterministic stage reconstruction

After a crash, next stage is reconstructed from:

```text
valid HEAD/CURRENT
Run state
exact expected Checkpoint
active Candidate manifest
referenced transaction
immutable plans
```

It is never reconstructed from the newest artifact.

---

# Part X: Detailed-contract ownership

## 80. Input and Initial ownership

Owned by:

```text
contracts/pipeline/input_and_initial.md
```

It defines:

```text
input-mode branch
Brief adoption
all INIT response roots
bundle integration/Review/revision
Genesis staging/ID allocation/adoption
```

---

## 81. Planning ownership

Owned by:

```text
contracts/pipeline/planning.md
```

It defines:

```text
Series/Volume/Chapter source-generation rules
candidate paths
Review/revision
plan Validation and immutable adoption
cross-Volume/Chapter re-entry
```

---

## 82. Scene-generation ownership

Owned by:

```text
contracts/pipeline/scene_generation.md
```

It defines:

```text
Scene-card/prose/continuity Contexts
candidate and Review loops
frozen Checkpoint fields/phases
source-generation invalidation
```

---

## 83. Commit/output ownership

Owned by:

```text
contracts/pipeline/commit_and_output.md
```

It defines:

```text
Scene Commit transaction
Volume Handoff content and adoption
Completion precondition/attempt/save
Publication payload/Validation/Manifest/Gate/adoption
crash matrices
```

---

# Part XI: Forbidden shortcuts

## 84. Stage shortcuts

Forbidden:

```text
skip Review
skip code normalization
skip Checkpoint
skip Commit plan
skip transaction Validation
skip Gate
mark completed before OUT-03
```

---

## 85. Candidate shortcuts

Forbidden:

```text
overwrite v0001 during revision
select highest candidate version
store Review result in candidate content
let Review route itself
promote audit response
patch a candidate in place
```

---

## 86. Scene shortcuts

Forbidden:

```text
give Writer private author truth
let prose carry update mechanics
let DELTA allocate IDs/hashes/offsets
commit without frozen prose
change Scene card/prose during COMMIT
rebase a stale checkpoint
```

---

## 87. Commit shortcuts

Forbidden:

```text
allocate in COMMIT-01
mutate parent Generation
create hidden State change
write HEAD before Scene/Generation durability
adopt pre-HEAD final-looking content
use Scene branch for Handoff
```

---

## 88. Completion/output shortcuts

Forbidden:

```text
call Completion before precondition passes
put Context hash inside a precondition that is embedded by the Context
retry semantic incomplete
copy private audit into publication
let Gate adopt
hash Validation/Manifest cyclically
store staging-root paths in final publication records
```

---

# Part XII: Implementation and acceptance

## 89. Stage registry implementation

Production code should use one canonical stage registry that records at least:

```text
Stage ID
processor type
operation key
target-kind resolver
Context builder
response Schema/format
artifact class set
normal next-stage function
resume authority function
```

Tests and CLI help should consume the same registry.

Duplicated independent transition tables are forbidden.

---

## 90. Transition validation

Every Run-state transition must validate:

```text
prior stage/status
completed output path/hash
target identity
next-stage edge
active Candidate/Checkpoint fields
pointer identity
stop fields
```

Unknown transitions fail before mutation.

---

## 91. Failpoint testing

Mandatory failpoints cover:

```text
candidate write/manifest boundary
Review write/manifest boundary
each Checkpoint artifact/manifest boundary
plan final move/Run-state boundary
Scene Generation rename
Scene artifact rename
HEAD replacement
Handoff Generation/artifact/HEAD
Publication payload/Validation/Manifest
Publication rename
CURRENT replacement
```

After restart, tests assert exact resume/reconcile/quarantine behavior.

---

## 92. Stage acceptance mapping

Primary acceptance groups:

| family | acceptance IDs |
|---|---|
| Input/Initial | `ACC-PIPE-INIT-*` |
| Planning | `ACC-PIPE-PLAN-*` |
| Scene generation | `ACC-PIPE-SCENE-*` |
| Scene commit | `ACC-COMMIT-*` |
| Volume Handoff | `ACC-VH-*` |
| Completion/Publication | `ACC-OUT-*` |
| Runtime recovery | `ACC-REC-*` |
| Prompt/registry | `ACC-PROMPT-*` |

All 50 Stage IDs must appear in the executable acceptance trace.

---

## 93. Mechanical acceptance conditions

This Pipeline index is acceptable only when tests demonstrate:

```text
exact 50 unique Stage IDs
exact family counts
exact processor-type registry
exact operation-key registry
exact artifact-class registry
exact target formats
one canonical stage registry in code

Context snapshot before every LLM call
source-generation/hash recheck
Call-ID persist-before-use
transport/structure/semantic counter separation
durable candidate/manifests before stage completion
raw-audit non-promotion

versioned candidate immutability
logical owner retention
Run-state active Candidate selection
mechanical validation before Review
Review exact content
Review/Revision routing
residual issue exhaustion
Completion Review-loop exception

Checkpoint phase authority
plan adoption immutability
Genesis/Scene/Handoff HEAD-last
Publication CURRENT-last
ID allocation at exact stages
COMMIT-01 no allocation

Brief/Keywords branches
distinct INIT roots
Genesis postcondition
Series/Volume/Chapter source rules
plan re-entry routes
fixed Scene source Generation
Writer/Continuity private boundary
DELTA code-owned-field exclusion
Scene commit four-stage transaction
post-commit route
Handoff disposition-only Generation
final Handoff to Completion

noncyclic Completion precondition/Context order
first valid Completion assessment
valid incomplete nonretry
Publication payload/Validation/Manifest/Gate order
Gate no-adoption
OUT-03 rename/CURRENT order

full transition graph
unknown transition rejection
per-stage resume authority
pre-pointer content nonadoption
post-pointer Run-state reconciliation
user/budget/manual/completed behavior

Generation/order distinction
Completion story-ledger read-only behavior
private/public separation
deterministic crash reconstruction
detailed-document ownership
forbidden shortcut rejection
relative-link resolution
