# Pipeline contracts: Commit, handoff, completion, and output

This document is the normative pipeline contract for:

```text
COMMIT-01
COMMIT-02
COMMIT-03
COMMIT-04

VH-01
VH-02
VH-REV
VH-ID

COMP-PRE
COMP-AUDIT
COMP-SAVE

OUT-01
OUT-02
COMP-PUBLISH
OUT-03
```

Scene checkpoints and Scene artifacts are defined by [`../data/scene_artifacts.md`](../data/scene_artifacts.md). Continuity candidates, Evidence records, and committed deltas are defined by [`../ledger/evidence_and_updates.md`](../ledger/evidence_and_updates.md). Canon and Story-state contracts are defined by the Ledger documents under [`../ledger/`](../ledger/). Runtime manifests, counters, pointer files, atomic-write rules, and publication records are defined by [`../ledger/runtime_records.md`](../ledger/runtime_records.md). Completion Review and audit data is defined by [`../data/review_and_audit.md`](../data/review_and_audit.md). Context views are defined by [`../../context_contracts.md`](../../context_contracts.md). Retry, budget, pricing, and profile settings are defined by [`../../configuration_contracts.md`](../../configuration_contracts.md). Planning artifacts are defined by [`../data/planning_artifacts.md`](../data/planning_artifacts.md).

Every JSON object written by this pipeline uses `additionalProperties: false`.

---

## 1. Pipeline purpose

This pipeline:

1. converts one `DELTA_ACCEPTED` Scene checkpoint into one immutable Scene commit;
2. adopts one private Volume handoff after the last Scene of every Volume;
3. stores Thread `volume_disposition` values in a new immutable generation;
4. performs one mechanically gated Completion audit;
5. constructs a deterministic local publication;
6. validates and gates that publication;
7. atomically changes `output/CURRENT`;
8. marks the run completed only after publication adoption.

The pipeline guarantees:

```text
no adopted generation is modified in place
no adopted Scene artifact is modified in place
persistent and Evidence IDs are allocated by code only
Scene commit changes are exactly represented by committed continuity delta
Volume handoff State changes occur through a dedicated immutable commit
Completion audit does not revise story content
a semantically incomplete audit is saved but cannot pass publication Gate
COMP-PUBLISH adopts nothing
OUT-03 alone adopts a publication and changes output/CURRENT
canon/HEAD and output/CURRENT are changed only after their targets are durable
```

---

## 2. Required Runtime-record extension

Thread `volume_disposition` is stored in `story-state.json` and is code-owned by `VH-ID`. Therefore `VH-ID` cannot mutate the current adopted generation in place.

This pipeline requires the Runtime record registry to support:

```text
commit_type:
  initial_design
  scene
  volume_handoff
```

For a `volume_handoff` Commit:

```text
scene_id = null
scene_card_sha256 = null
prose_sha256 = null
continuity_delta_sha256 = null
scene_manifest_sha256 = null

volume_handoff_path = artifacts/handoffs/vNN.json
volume_handoff_sha256 = adopted handoff hash

current_order = parent current_order
local_key_mappings = []
evidence_ids = []
```

A Generation created by a Volume-handoff Commit has:

```text
source_scene_id = null
source_scene_manifest_path = null
source_scene_manifest_sha256 = null

source_volume_handoff_path = artifacts/handoffs/vNN.json
source_volume_handoff_sha256 = adopted handoff hash
```

For Genesis and Scene commits, the Volume-handoff fields are null.

These conditional fields must be reflected in the corresponding Commit- and Generation-manifest Schemas. The rest of this document treats them as normative.

---

## 3. Processor types and artifact classes

### 3.1 Processor types

| stages | processor type |
|---|---|
| `COMMIT-01` through `COMMIT-04` | `code` |
| `VH-01` | `llm_generate` |
| `VH-02` | `llm_review` |
| `VH-REV` | `llm_revise` |
| `VH-ID` | `code` |
| `COMP-PRE` | `code` |
| `COMP-AUDIT` | `llm_generate` |
| `COMP-SAVE` | `code` |
| `OUT-01`, `OUT-02`, `COMP-PUBLISH`, `OUT-03` | `code` |

No stage in this document uses `llm_extract`.

### 3.2 Artifact classes

| artifact | class |
|---|---|
| Commit plan and frozen Scene checkpoint files | `checkpoint` |
| Commit/Handoff/Publication staging files | `staged_internal` |
| Commit/Handoff/Publication staged validation | `staged_internal_validation` |
| Volume-handoff and Completion-audit candidates | `candidate` |
| adopted generation, Scene artifact, Volume handoff, publication | `adopted` |
| Reviews, LLM calls, Completion records, Gate results, operation records | `audit` |

Forbidden:

```text
review candidate
adopted/audit
checkpoint/audit
staged/adopted
any slash-combined class
```

---

# Part I: Scene commit

## 4. Scene-commit entry conditions

`COMMIT-01` may start only when:

```text
Run-state next_stage = COMMIT-01
scene_phase = DELTA_ACCEPTED
active_candidate_manifest_path = null
active_checkpoint_manifest_path is non-null
Checkpoint manifest phase = DELTA_ACCEPTED
frozen Scene card exists and hashes correctly
frozen prose exists and hashes correctly
candidate continuity delta exists and hashes correctly
checkpoint source generation equals canon/HEAD
source Generation and Commit manifests validate
target Scene artifact does not already exist
no conflicting Scene-commit staging transaction exists
workspace lock is held
```

If the target Scene is already adopted and the resulting HEAD chain validates, startup reconciles the adopted commit instead of running `COMMIT-01`.

---

## 5. Commit route after the Scene

Code derives one route from the adopted Chapter and Volume designs.

### 5.1 Route enum

```text
next_scene
next_chapter
volume_handoff
```

### 5.2 Commit route object

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `route_type` | enum `scene_commit_route` | yes | no | none | code | one permitted value |
| `next_stage` | Stage ID | yes | no | none | code | route-compatible |
| `next_target_id` | string | yes | no | none | code | route-compatible target |
| `next_volume_number` | integer | yes | no | none | code | `>=1` |
| `next_chapter_number` | integer | yes | yes | none | code | null iff route is `volume_handoff` |
| `next_scene_number` | integer | yes | yes | none | code | non-null iff route is `next_scene` |

### 5.3 Route derivation

If:

```text
scene_number < Chapter design target_scene_count
```

then:

```text
route_type = next_scene
next_stage = SC-01
next target = same Volume/Chapter, scene_number + 1
```

Else, if:

```text
scene_number = target_scene_count
chapter_number < Volume design target_chapter_count
```

then:

```text
route_type = next_chapter
next_stage = CH-01
next target = same Volume, chapter_number + 1
```

Else:

```text
scene_number = target_scene_count
chapter_number = target_chapter_count
route_type = volume_handoff
next_stage = VH-01
next target = completed Volume
```

The `chapter_completion_role` of the final Scene must be `resolution`, but the role alone does not determine the route.

A Scene commit never routes directly to `COMP-PRE`. Every Volume, including the final Volume, adopts a Volume handoff first.

---

## 6. COMMIT-01 — Dry validation and commit plan

### 6.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact classes | `checkpoint` and separate `audit` |
| LLM call | none |
| input authority | `DELTA_ACCEPTED` Checkpoint manifest and current HEAD |
| output | `commit-plan.json` |
| next stage | `COMMIT-02` |
| ID allocation | forbidden |

### 6.2 Output path

```text
runtime/checkpoints/scenes/vNN/cNNN/sNNN/commit-plan.json
```

The Checkpoint manifest remains at phase `DELTA_ACCEPTED`.

### 6.3 Commit-plan check result

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `check_id` | string | yes | no | none | code | `[A-Z][A-Z0-9_]{2,63}`; unique |
| `status` | enum | yes | no | none | code | `pass` or `fail` |
| `artifact_path` | workspace-relative path | yes | yes | `null` | code | null or checked file |
| `artifact_sha256` | SHA-256 | yes | yes | `null` | code | null iff artifact path null |
| `message` | string | yes | no | none | code | sanitized NFC `1..1000` |

### 6.4 Allocation request

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `allocation_type` | enum `allocation_type` | yes | no | none | code | compatible with proposal type |
| `local_key` | candidate local key | yes | no | none | code from validated delta | unique by `(allocation_type,local_key)` |
| `source_pointer` | JSON Pointer string | yes | no | none | code | points to the creating proposal |
| `sort_order` | integer | yes | no | none | code | contiguous from `1` in deterministic allocation order |

### 6.5 Evidence allocation request

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `source_pointer` | JSON Pointer string | yes | no | none | code | points to one Evidence proposal |
| `target_kind` | string | yes | no | none | code | compatible with originating proposal/update |
| `quote` | string | yes | no | none | code from candidate | exact unique prose substring |
| `relation` | enum `evidence_relation` | yes | no | none | code from candidate | valid for target |
| `sort_order` | integer | yes | no | none | code | contiguous from `1` in committed-delta canonical order |

### 6.6 Commit-plan root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | exact |
| `scene_id` | Scene ID | yes | no | none | code | target Scene |
| `checkpoint_manifest_path` | workspace-relative path | yes | no | none | code | active Checkpoint manifest |
| `checkpoint_manifest_sha256` | SHA-256 | yes | no | none | code | matches |
| `source_generation_id` | Generation ID | yes | no | none | code | current HEAD |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | source Generation manifest |
| `source_commit_id` | Commit ID | yes | no | none | code | source Commit manifest |
| `source_current_order` | integer | yes | no | none | code | source Story clock |
| `expected_after_current_order` | integer | yes | no | none | code | source order + 1 |
| `scene_card_path` | workspace-relative path | yes | no | none | code | checkpoint Scene card |
| `scene_card_sha256` | SHA-256 | yes | no | none | code | matches |
| `prose_path` | workspace-relative path | yes | no | none | code | checkpoint prose |
| `prose_sha256` | SHA-256 | yes | no | none | code | matches |
| `candidate_delta_path` | workspace-relative path | yes | no | none | code | checkpoint candidate delta |
| `candidate_delta_sha256` | SHA-256 | yes | no | none | code | matches |
| `record_allocation_requests` | array<Allocation request> | yes | no | `[]` | code | deterministic, unique, sorted by `sort_order` |
| `evidence_allocation_requests` | array<Evidence allocation request> | yes | no | `[]` | code | complete and sorted |
| `route_after_commit` | Commit route object | yes | no | none | code | Section 5 |
| `checks` | array<Commit-plan check result> | yes | no | none | code | nonempty; sorted by check ID |
| `all_checks_pass` | boolean | yes | no | none | code | true iff every check passes |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

### 6.7 Minimum COMMIT-01 checks

```text
Checkpoint manifest and all checkpoint hashes
source HEAD and Generation/Commit chain
Scene ID and plan coordinates
target Scene not already adopted
Scene-card source generation and Chapter-design hash
prose canonical form and character count
candidate-delta exact Schema
candidate before values equal HEAD
all existing target/field/operation authorizations
all new local-key references
all new-record complete initial State
Knowledge and Thread transition matrices
required Major Thread retirement rejection
new-item count/type/scope
Evidence quote unique occurrence
Evidence quote and relation compatibility
Ending-target authorization
time-update authorization
handoff_summary prose grounding
delta-to-projected-after-State dry merge
no unknown or code-owned candidate fields
commit route
counter preconditions
storage-space and staging-path availability
```

`all_checks_pass=false` stops mechanically. It never proceeds by revision exhaustion.

### 6.8 Postcondition

After a passing plan is durable:

```text
Run last_completed_stage = COMMIT-01
Run next_stage = COMMIT-02
scene_phase = DELTA_ACCEPTED
```

No counter is incremented and no staging generation exists yet.

---

## 7. COMMIT-02 — Allocate and construct staged generation roots

### 7.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `staged_internal` and separate `audit` |
| LLM call | none |
| input | passing Commit plan |
| output | allocated transaction and staged root generation files |
| next stage | `COMMIT-03` |

### 7.2 Staging layout

```text
.staging/scene-commits/<scene-id>/
  transaction-manifest.json
  merge-plan.json
  generation/<generation-id>/
    current-canon.json
    knowledge-items.json
    story-state.json
    evidence-index.json
  scene/
```

`scene/` may be empty until COMMIT-03.

### 7.3 Allocation order

Under the workspace lock, code:

1. allocates and persists one Commit ID;
2. derives the Generation ID from the Commit numeric suffix;
3. allocates all persistent record IDs in Commit-plan `sort_order`;
4. allocates all Evidence IDs in Commit-plan `sort_order`;
5. never reuses an allocated value after any later failure.

The Commit ID and Generation ID are allocated even when the scene creates no new story records.

### 7.4 Evidence source mapping

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `source_pointer` | JSON Pointer string | yes | no | none | code | Commit-plan Evidence request |
| `evidence_id` | Evidence ID | yes | no | none | code | newly allocated |
| `start_offset` | integer | yes | no | none | code | Unicode code-point offset |
| `end_offset` | integer | yes | no | none | code | exclusive and valid |
| `quote_sha256` | SHA-256 | yes | no | none | code | exact quote |
| `prose_sha256` | SHA-256 | yes | no | none | code | checkpoint prose |

### 7.5 Merge plan

`merge-plan.json` is internal and contains:

```text
schema_version
scene_id
commit_id
before_generation
after_generation
parent_commit_id
current_order_before
current_order_after
local_key_mappings
evidence_source_mappings
normalized existing updates
normalized new Canon records
normalized new Knowledge records
normalized Character/Relationship/Thread initial State rows
normalized Knowledge updates
normalized Thread updates
normalized Story-clock update
resulting route
created_at
```

Every normalized update includes its exact `before`, `after`, and Evidence IDs.

The merge plan contains no unresolved local key except the `local_key` preserved in the mapping record itself.

### 7.6 Staged generation construction

Code:

1. copy-on-write loads the source generation;
2. applies new Canon records;
3. applies mutable Canon/Knowledge metadata updates;
4. applies new and updated Story-state rows;
5. appends new immutable Evidence records;
6. increments Story-clock `current_order` by exactly one;
7. sets Scene position to the committed Scene;
8. retains all unchanged canonical records;
9. writes four staged root files;
10. validates all root and cross-record contracts;
11. calculates all root hashes.

The staged root files do not yet contain Commit or Generation manifests.

### 7.7 Transaction-manifest root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | exact |
| `transaction_type` | constant `scene_commit` | yes | no | exact | code | exact |
| `transaction_status` | enum | yes | no | `generation_built` | code | `generation_built`, `scene_built`, or `validated` |
| `scene_id` | Scene ID | yes | no | none | code | target |
| `commit_id` | Commit ID | yes | no | none | code | allocated |
| `before_generation` | Generation ID | yes | no | none | code | Commit plan |
| `after_generation` | Generation ID | yes | no | none | code | Commit suffix |
| `commit_plan_path` | workspace-relative path | yes | no | none | code | checkpoint Commit plan |
| `commit_plan_sha256` | SHA-256 | yes | no | none | code | matches |
| `merge_plan_path` | workspace-relative path | yes | no | none | code | staged merge plan |
| `merge_plan_sha256` | SHA-256 | yes | no | none | code | matches |
| `local_key_mappings` | array<Local-key mapping> | yes | no | `[]` | code | exact allocations |
| `evidence_source_mappings` | array<Evidence source mapping> | yes | no | `[]` | code | exact allocations and offsets |
| `staged_generation_path` | workspace-relative path | yes | no | none | code | staged generation directory |
| `current_canon_sha256` | SHA-256 | yes | no | none | code | staged root |
| `knowledge_items_sha256` | SHA-256 | yes | no | none | code | staged root |
| `story_state_sha256` | SHA-256 | yes | no | none | code | staged root |
| `evidence_index_sha256` | SHA-256 | yes | no | none | code | staged root |
| `staged_scene_path` | workspace-relative path | yes | no | none | code | staged Scene directory |
| `scene_manifest_sha256` | SHA-256 | yes | yes | `null` | code | null until COMMIT-03 |
| `commit_manifest_sha256` | SHA-256 | yes | yes | `null` | code | null until COMMIT-03 |
| `generation_manifest_sha256` | SHA-256 | yes | yes | `null` | code | null until COMMIT-03 |
| `validation_path` | workspace-relative path | yes | yes | `null` | code | null until COMMIT-03 |
| `validation_sha256` | SHA-256 | yes | yes | `null` | code | null iff validation path null |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |
| `updated_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

### 7.8 Postcondition

```text
Run last_completed_stage = COMMIT-02
Run next_stage = COMMIT-03
scene_phase = DELTA_ACCEPTED
```

The Checkpoint manifest still has phase `DELTA_ACCEPTED`.

---

## 8. COMMIT-03 — Construct Scene artifact and complete staged transaction

### 8.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact classes | `staged_internal`, `staged_internal_validation`, and separate `audit` |
| LLM call | none |
| input | staged generation, merge plan, frozen checkpoint |
| output | complete staged Scene/generation manifests and transaction validation |
| next stage | `COMMIT-04` |

### 8.2 Staged Scene construction

Code writes under staged `scene/`:

```text
scene-card.json
prose.md
continuity-delta.json
scene-manifest.json
```

Rules:

- staged Scene-card bytes equal checkpoint Scene-card bytes;
- staged prose bytes equal checkpoint prose bytes;
- committed delta is code-generated from the merge plan;
- all local references are resolved;
- all Evidence proposal objects are replaced by Evidence IDs;
- all committed arrays use canonical target ordering;
- committed delta exactly describes the staged generation changes;
- Scene manifest paths point to final `artifacts/scenes/...` paths.

### 8.3 Manifest construction order

To avoid hash cycles:

1. write staged Scene card, prose, and committed delta;
2. write Scene manifest;
3. write Commit manifest with Scene-manifest hash;
4. write Generation manifest with Commit- and Scene-manifest hashes.

The Scene manifest does not contain Commit- or Generation-manifest hashes.

### 8.4 Commit manifest

The Scene Commit manifest uses:

```text
commit_type = scene
scene_id = target Scene
before_generation = transaction before generation
after_generation = transaction after generation
current_order = prior + 1
scene hashes and Scene-manifest hash are non-null
volume_handoff_path = null
volume_handoff_sha256 = null
```

### 8.5 Generation manifest

The Scene Generation manifest uses:

```text
parent_generation_id = before generation
source_scene_id = target Scene
source_scene_manifest_path = final adopted Scene-manifest path
source_scene_manifest_sha256 = staged Scene-manifest hash
source_volume_handoff_path = null
source_volume_handoff_sha256 = null
```

### 8.6 Transaction-validation result

Path:

```text
.staging/scene-commits/<scene-id>/transaction-validation.json
```

Root:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | exact |
| `transaction_type` | constant `scene_commit` | yes | no | exact | code | exact |
| `scene_id` | Scene ID | yes | no | none | code | target |
| `commit_id` | Commit ID | yes | no | none | code | transaction |
| `before_generation` | Generation ID | yes | no | none | code | transaction |
| `after_generation` | Generation ID | yes | no | none | code | transaction |
| `checks` | array<Commit-plan check result> | yes | no | none | code | nonempty and sorted |
| `all_checks_pass` | boolean | yes | no | none | code | true iff all pass |
| `staged_refs` | array<Audit artifact reference> | yes | no | none | code | complete staged final set |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

Minimum checks:

```text
all staged file Schemas and hashes
Scene-card and prose checkpoint byte equality
committed-delta Schema
no unresolved local keys
all Evidence IDs exist in staged Evidence index
Evidence offsets and hashes
committed-delta to staged root correspondence
no staged root change omitted from delta
Scene-manifest final paths
Commit/Generation conditional fields
Commit/Generation hash graph
Story-clock order and position
route_after_commit
no staging/checkpoint path in adopted manifests
no placeholder hash
```

### 8.7 Complete transaction

After validation passes, code:

1. updates Transaction manifest:
   ```text
   transaction_status = validated
   scene_manifest_sha256 = ...
   commit_manifest_sha256 = ...
   generation_manifest_sha256 = ...
   validation_path = ...
   validation_sha256 = ...
   ```
2. atomically updates Checkpoint manifest:
   ```text
   phase = COMMIT_PREPARED
   staging_transaction_path =
     .staging/scene-commits/<scene-id>/transaction-manifest.json
   ```
3. atomically updates Run state.

Postcondition:

```text
Run last_completed_stage = COMMIT-03
Run next_stage = COMMIT-04
scene_phase = COMMIT_PREPARED
```

---

## 9. COMMIT-04 — Adopt generation and Scene

### 9.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `adopted` and separate `audit` |
| LLM call | none |
| input | valid COMMIT_PREPARED checkpoint and complete staged transaction |
| output | adopted generation, adopted Scene, changed `canon/HEAD` |
| next stage | Commit-plan route |

### 9.2 Final pre-adoption validation

Immediately before rename:

```text
workspace lock is held
canon/HEAD still equals before_generation
source Generation-manifest hash still matches
Checkpoint phase = COMMIT_PREPARED
Transaction manifest status = validated
transaction-validation all_checks_pass = true
all staged hashes still match
final generation path absent
final Scene path absent
route_after_commit still matches immutable plans
```

A mismatch stops before adoption.

### 9.3 Adoption order

1. `fsync` all staged files and directories;
2. atomically rename staged generation to:
   ```text
   canon/generations/<after-generation>
   ```
3. atomically rename staged Scene directory to:
   ```text
   artifacts/scenes/vNN/cNNN/sNNN
   ```
4. revalidate both adopted directories;
5. atomically replace:
   ```text
   canon/HEAD = "<after-generation>\n"
   ```
6. atomically update Run state;
7. increment `successful_scene_commits`;
8. write successful operation audit;
9. remove checkpoint and remaining staging.

`canon/HEAD` is the Scene-commit adoption point.

### 9.4 Run-state routing

Common fields:

```text
last_completed_stage = COMMIT-04
current_head_generation = after_generation
last_commit_id = commit_id
active_candidate_manifest_path = null
active_checkpoint_manifest_path = null
scene_phase = SCENE_COMMITTED
```

Then route:

#### Next Scene

```text
next_stage = SC-01
current_target_id = next Scene ID
current_volume_number = same
current_chapter_number = same
current_scene_number = next
scene_phase = SCENE_NOT_STARTED
```

#### Next Chapter

```text
next_stage = CH-01
current_target_id = next Chapter target
current_volume_number = same
current_chapter_number = next
current_scene_number = null
scene_phase = null
```

#### Volume handoff

```text
next_stage = VH-01
current_target_id = completed Volume target
current_volume_number = completed Volume
current_chapter_number = null
current_scene_number = null
scene_phase = null
```

### 9.5 Counter invariant

After Run-state reconciliation:

```text
successful_scene_commits
  =
HEAD Story-clock current_order
```

Volume-handoff commits do not increment either value.

---

## 10. Scene-commit crash semantics

### 10.1 Before any adopted rename

Only staging exists.

Startup revalidates complete staging or quarantines it. HEAD and adopted Scene remain unchanged.

### 10.2 Generation renamed, Scene not renamed, HEAD unchanged

The generation is unreachable and unadopted.

Startup quarantines the generation and remaining staging. It does not promote it.

### 10.3 Generation and Scene renamed, HEAD unchanged

Both are unadopted orphans.

Startup quarantines them after proving they are not reachable from valid HEAD.

### 10.4 HEAD changed, Run state or cleanup incomplete

The commit is adopted.

Startup:

- validates HEAD Generation, Commit, and Scene manifests;
- reconciles Run state to the route in the Commit plan or immutable plan data;
- increments/reconciles successful Scene count;
- removes leftover checkpoint/staging.

No LLM stage is repeated.

---

# Part II: Volume handoff

## 11. Volume-handoff purpose

A Volume handoff is a private immutable summary of the actual end-of-Volume state and the constraints that later planning must preserve.

It is not reader-facing publication content.

`VH-ID` additionally writes Thread `volume_disposition` values through a dedicated `volume_handoff` Commit and generation.

A handoff does not:

```text
create new Canon records
change Character or Relationship State
change Knowledge State
change Thread status or progress
change Story clock
create Evidence
rewrite prose
rewrite Volume or Series plans
```

Its only Story-state changes are permitted `thread_states[].volume_disposition` values.

---

## 12. Volume-handoff candidate version paths

```text
runtime/candidates/handoffs/vNN/v0001/
  volume-handoff.json
  review.json
  candidate-manifest.json
```

A revision creates the next complete version directory.

Logical owner:

```text
operation_id = VH-01
processor_type = llm_generate
```

A revised version retains that owner.

---

## 13. Volume-handoff enums

### 13.1 Carry-over importance

```text
required
important
optional
```

### 13.2 Handoff risk severity

```text
warning
error
```

### 13.3 Constraint category

```text
character
relationship
thread
knowledge
world
time
ending
continuity
```

---

## 14. VH-01 LLM content candidate

The LLM returns exactly:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `volume_number` | integer | yes | no | none | LLM | completed Volume |
| `ending_state_summary` | string | yes | no | none | LLM | NFC `1..4000`; actual adopted ending only |
| `local_resolution_summary` | string | yes | no | none | LLM | NFC `1..2000`; assesses Volume-local payoff |
| `character_carryovers` | array<Character carry-over content> | yes | no | `[]` | LLM | unique Character IDs |
| `relationship_carryovers` | array<Relationship carry-over content> | yes | no | `[]` | LLM | unique Relationship IDs |
| `thread_decisions` | array<Thread decision content> | yes | no | none | LLM | Section 17 coverage |
| `knowledge_carryovers` | array<Knowledge carry-over content> | yes | no | `[]` | LLM | unique fact IDs |
| `world_carryovers` | array<World carry-over content> | yes | no | `[]` | LLM | unique World IDs |
| `next_volume_constraints` | array<Next-Volume constraint> | yes | no | `[]` | LLM | nonfinal Volume requirements |
| `series_transition_summary` | string | yes | yes | none | LLM | non-null for nonfinal Volume; null for final Volume |
| `residual_risks` | array<Handoff risk> | yes | no | `[]` | LLM | unique risk codes |

The LLM does not output:

```text
schema version
source/adopted generation IDs
hashes
timestamps
Commit ID
Story-clock object
Thread status/progress
Thread record lifecycle
Review or residual Issue records
```

---

## 15. Character carry-over content

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `character_id` | Character ID | yes | no | none | LLM | adopted active/inactive Character |
| `public_state_summary` | string | yes | no | none | LLM | NFC `1..1500`; externally observable state |
| `private_state_summary` | string | yes | yes | `null` | LLM | NFC `1..1500`; private planner-only state |
| `knowledge_fact_ids` | array<Knowledge item ID> | yes | no | `[]` | LLM | only facts with non-default Character state or next-volume relevance |
| `next_volume_relevance` | string | yes | yes | `null` | LLM | required for selected nonfinal carry-over |
| `importance` | enum `carry_over_importance` | yes | no | none | LLM | registry value |

The code validates summaries against current Character and Knowledge states. The handoff does not become their State authority.

---

## 16. Relationship carry-over content

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `relationship_id` | Relationship ID | yes | no | none | LLM | adopted active/inactive Relationship |
| `public_state_summary` | string | yes | no | none | LLM | NFC `1..1500` |
| `private_state_summary` | string | yes | yes | `null` | LLM | NFC `1..1500`; private planner-only |
| `next_volume_relevance` | string | yes | yes | `null` | LLM | required for selected nonfinal carry-over |
| `importance` | enum `carry_over_importance` | yes | no | none | LLM | registry value |

The code validates the summaries against current directional Relationship State.

---

## 17. Thread decision content

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `thread_id` | Thread ID | yes | no | none | LLM | adopted Thread State exists |
| `disposition` | enum `volume_disposition` | yes | yes | none | LLM | matrix below |
| `summary` | string | yes | no | none | LLM | NFC `1..1500`; actual end state |
| `evidence_ids` | array<Evidence ID> | yes | no | `[]` | LLM | relevant adopted Evidence only |
| `next_volume_constraint` | string | yes | yes | `null` | LLM | required iff disposition is `carry_over` |
| `importance` | enum `carry_over_importance` | yes | no | none | LLM | required Major Thread normally `required` |

Disposition rules against code-injected current State:

| current Thread state | permitted disposition |
|---|---|
| `open / 0` | `null` only |
| `in_progress / 1..3` and scope `series` | `carry_over` |
| `resolved / 4` | `resolve` |
| `retired / 0..3` | `retire` |
| required Major Thread | never `retire` |
| Volume-scope unresolved Thread | cannot `carry_over`; must already be resolved or retired before handoff |

Coverage rules:

- every required Major Thread appears;
- every Thread changed or evidenced in the completed Volume appears;
- every Thread targeted by the next Series Volume entry appears;
- other inactive/irrelevant Supporting Threads may be omitted;
- final Volume requires every required Major Thread to use `resolve`.

A null disposition does not change the Story-state field.

---

## 18. Knowledge carry-over content

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `fact_id` | Knowledge item ID | yes | no | none | LLM | adopted non-retired fact |
| `relevance_summary` | string | yes | no | none | LLM | NFC `1..1000`; private safe summary |
| `relevant_character_ids` | array<Character ID> | yes | no | `[]` | LLM | actual non-default or next-target audiences |
| `reader_status` | enum `reader_knowledge_status` | yes | no | none | LLM | exact current explicit or implicit status |
| `next_volume_constraint` | string | yes | yes | `null` | LLM | null for final Volume or irrelevant fact |
| `importance` | enum `carry_over_importance` | yes | no | none | LLM | registry value |

The full Knowledge-item author truth is not copied into this child. The private Context Builder can retrieve it by ID when later planning needs it.

---

## 19. World carry-over content

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `world_entity_id` | World entity ID | yes | no | none | LLM | adopted non-retired World entity |
| `relevance_summary` | string | yes | no | none | LLM | NFC `1..1000` |
| `next_volume_constraint` | string | yes | yes | `null` | LLM | next-volume requirement |
| `importance` | enum `carry_over_importance` | yes | no | none | LLM | registry value |

Temporary world conditions remain Knowledge items or prose-derived context; the World record itself is not mutated by the handoff.

---

## 20. Next-Volume constraint

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `code` | string | yes | no | none | LLM | `[A-Z][A-Z0-9_]{2,63}`; unique |
| `category` | enum `handoff_constraint_category` | yes | no | none | LLM | registry value |
| `description` | string | yes | no | none | LLM | NFC `1..1500`; actionable, abstract, non-prose |
| `related_ids` | array<persistent ID> | yes | no | `[]` | LLM | unique and sorted |
| `required` | boolean | yes | no | `true` | LLM | boolean |

Constraints must not contain future Scene prose or unsupported new facts.

Final Volume requires:

```text
next_volume_constraints = []
series_transition_summary = null
```

---

## 21. Handoff risk

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `code` | string | yes | no | none | LLM | `[A-Z][A-Z0-9_]{2,63}`; unique |
| `severity` | enum `handoff_risk_severity` | yes | no | none | LLM | `warning` or `error` |
| `description` | string | yes | no | none | LLM | NFC `1..1500` |
| `related_ids` | array<persistent ID or Scene ID> | yes | no | `[]` | LLM | unique and sorted |
| `evidence_ids` | array<Evidence ID> | yes | no | `[]` | LLM | adopted Evidence only |

An error risk is still a semantic Review issue, not a structural failure, when the handoff candidate remains mechanically valid.

---

## 22. Normalized handoff candidate

Before writing the candidate, code adds:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | exact |
| `source_generation_id` | Generation ID | yes | no | none | code | current final-Scene HEAD |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | matches |
| `volume_design_path` | workspace-relative path | yes | no | none | code | completed Volume design |
| `volume_design_sha256` | SHA-256 | yes | no | none | code | matches |
| `series_map_sha256` | SHA-256 | yes | no | none | code | adopted Series map |
| all LLM content fields | Sections 14–21 | yes | as defined | as defined | code from LLM | content validation |
| `thread_decisions` | array<Normalized Thread decision> | yes | no | none | code | complete coverage and current State injection |
| `story_clock` | exact Story-clock object | yes | no | none | code | source generation |
| `accepted_response_sha256` | SHA-256 | yes | no | none | code | canonical LLM content response |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | candidate-normalization time |

A normalized Thread decision contains all content fields plus:

```text
thread_type
required
scope
record_lifecycle
thread_status
progress
prior_volume_disposition
```

All injected fields equal the source generation.

The versioned candidate file is the normalized candidate. VH-REV returns LLM content only; code repeats normalization.

---

## 23. VH-01 — Generate Volume handoff

### 23.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `volume_handoff` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `volume_handoff_builder` |
| logical owner | `VH-01` |
| target ID | `vNN` |
| output | normalized Volume-handoff candidate |
| next stage | `VH-02` |

### 23.2 Preconditions

```text
Run-state next_stage = VH-01
last Scene of target Volume is adopted
current HEAD equals that Scene's adopted generation
all Chapters and Scenes in Volume design are adopted
no adopted handoff exists for the Volume
no future Volume design is adopted
```

### 23.3 Output

```text
runtime/candidates/handoffs/vNN/v0001/volume-handoff.json
runtime/candidates/handoffs/vNN/v0001/candidate-manifest.json
```

### 23.4 Mechanical validation

```text
exact content and normalized candidate Schemas
volume number and source generation
Volume-local resolution fields
every referenced ID resolves
Story-clock exact equality
Thread-decision coverage
Thread disposition matrix
Evidence IDs and target relevance
Character/Relationship summaries match current State
Knowledge statuses match explicit/implicit current State
nonfinal/final conditional rules
next-Volume target compatibility
no future prose
no code-owned fields in LLM response
no provider/runtime/publication metadata
```

### 23.5 Postcondition

```text
Run last_completed_stage = VH-01
Run next_stage = VH-02
active_candidate_manifest_path =
  runtime/candidates/handoffs/vNN/v0001/candidate-manifest.json
```

---

## 24. VH-02 — Review Volume handoff

### 24.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_review` |
| operation key | `volume_handoff` |
| artifact class | `audit` |
| Context builder | `review_builder` |
| reviewed role | `volume_handoff` |
| next stage | routing result |

### 24.2 Required Review coverage

```text
actual end-State fidelity
Volume-local resolution
Character and Relationship carry-over accuracy
Thread disposition correctness
required Major Thread treatment
Evidence relevance
Knowledge and reader-status accuracy
next-Volume constraints
Series-map transition compatibility
final-Volume no-next constraints
hidden-truth and future-prose leakage
residual risk completeness
```

### 24.3 Output

```text
active handoff candidate directory/review.json
```

Review/routing uses the same version, residual, and whole-replacement rules as the other pipelines.

---

## 25. VH-REV — Replace Volume handoff

### 25.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_revise` |
| operation key | `volume_handoff` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `revision_builder` |
| owner retained | `VH-01` |
| response | complete Handoff LLM content candidate |
| next stage | `VH-02` |

A successful revision creates the next immutable version directory.

It cannot change:

```text
volume number
source generation
current Thread State
current Story clock
parent Series/Volume plan hashes
adopted Evidence IDs
```

Code repeats complete normalized-candidate construction.

---

## 26. Handoff Review routing

### 26.1 No issues

```text
candidate_status = ready_for_adoption
next_stage = VH-ID
```

### 26.2 Issues and revision remains

```text
candidate_status = revision_required
next_stage = VH-REV
```

### 26.3 Issues and revision exhausted

Code:

1. records residual issues;
2. preserves the mechanically valid normalized candidate;
3. marks it `ready_for_adoption`;
4. routes to `VH-ID`.

A disposition-matrix defect, stale HEAD, unresolved ID, or missing required Thread is mechanical and never proceeds by exhaustion.

---

## 27. VH-ID — Adopt handoff and disposition generation

### 27.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact classes | `staged_internal`, `staged_internal_validation`, `adopted`, and separate `audit` |
| LLM call | none |
| source | active ready handoff candidate |
| output | adopted handoff and new `volume_handoff` generation |
| next stage | `VOL-01` or `COMP-PRE` |

### 27.2 Preconditions

```text
current HEAD equals handoff source_generation_id
source Generation-manifest hash matches
candidate/Review/residual records validate
last Scene of Volume remains the HEAD Story-clock last_scene_id
adopted handoff path absent
no next Volume design has been adopted
```

### 27.3 Staging layout

```text
.staging/handoffs/vNN/<run-id>/
  handoff.json
  handoff-validation.json
  generation/<generation-id>/
    current-canon.json
    knowledge-items.json
    story-state.json
    evidence-index.json
    commit-manifest.json
    generation-manifest.json
```

### 27.4 Allocation

Code allocates and persists:

```text
one Commit ID
one matching Generation ID
```

It allocates no story-record or Evidence IDs.

### 27.5 Handoff adopted root

Code adds to the normalized candidate:

| field | type | required | nullable | creator | validation |
|---|---|---:|---:|---|---|
| `handoff_version` | constant string `1.0` | yes | no | code | exact |
| `commit_id` | Commit ID | yes | no | code | Handoff Commit |
| `adopted_generation_id` | Generation ID | yes | no | code | Handoff generation |
| `accepted_candidate_path` | workspace-relative path | yes | no | code | active candidate |
| `accepted_candidate_sha256` | SHA-256 | yes | no | code | matches |
| `review_path` | workspace-relative path | yes | no | code | active Review |
| `review_sha256` | SHA-256 | yes | no | code | matches |
| `adopted_at` | RFC 3339 UTC timestamp | yes | no | code | Commit time |

Final path:

```text
artifacts/handoffs/vNN.json
```

The adopted root contains no candidate, Review, or runtime paths except the two explicit private audit-trace paths above. These fields are private and must be removed from safe handoff projection.

### 27.6 Story-state update

Code clones the source generation.

For each normalized Thread decision:

- non-null `disposition` replaces `thread_state.volume_disposition`;
- null `disposition` leaves the prior value unchanged;
- status and progress remain unchanged.

No other Story-state field changes.

Current Canon, Knowledge items, and Evidence index bytes remain identical to the parent generation.

Story-clock bytes remain identical.

### 27.7 Handoff Commit manifest

```text
commit_type = volume_handoff
scene_id = null
before_generation = source generation
after_generation = allocated generation
current_order = unchanged
all four root hashes
all Scene fields null
volume_handoff_path = artifacts/handoffs/vNN.json
volume_handoff_sha256 = staged final handoff hash
local_key_mappings = []
evidence_ids = []
```

### 27.8 Handoff Generation manifest

```text
parent_generation_id = source generation
current_order = unchanged
source_scene fields = null
source_volume_handoff_path = artifacts/handoffs/vNN.json
source_volume_handoff_sha256 = handoff hash
```

### 27.9 Handoff validation

Minimum checks:

```text
source HEAD and final Scene
candidate/Review/residual hashes
handoff exact adopted Schema
Thread decision coverage
disposition matrix
only volume_disposition fields changed
unchanged current Canon bytes
unchanged Knowledge-item bytes
unchanged Evidence-index bytes
unchanged Story-clock bytes
Commit/Generation conditional fields
Commit/Generation hash graph
final handoff path
no staging path
no placeholder hash
```

### 27.10 Adoption order

1. `fsync` staged files;
2. atomically rename staged generation to `canon/generations/<id>`;
3. atomically place staged handoff at `artifacts/handoffs/vNN.json`;
4. revalidate both;
5. atomically replace `canon/HEAD`;
6. atomically update Run state;
7. write operation audit;
8. remove staging and active candidate pointer.

`canon/HEAD` is the Handoff-commit adoption point.

### 27.11 Postconditions

Common:

```text
last_completed_stage = VH-ID
current_head_generation = adopted_generation_id
last_commit_id = handoff commit ID
active_candidate_manifest_path = null
scene_phase = null
```

If another Volume remains:

```text
next_stage = VOL-01
current_target_id = next vNN
current_volume_number = next Volume
current_chapter_number = null
current_scene_number = null
```

If the final Volume completed:

```text
next_stage = COMP-PRE
current_target_id = completion
current_volume_number = final Volume
current_chapter_number = null
current_scene_number = null
```

### 27.12 Handoff crash semantics

- Before any adopted rename: staging only; resume/quarantine.
- Generation or handoff placed but HEAD unchanged: both are unadopted orphans.
- HEAD changed: Handoff commit is adopted; reconcile Run state and route.
- A handoff file without its HEAD-reachable Handoff generation is not authoritative.

---

# Part III: Completion audit

## 28. Completion entry conditions

`COMP-PRE` may start only when:

```text
final Volume handoff is adopted
current HEAD is the final Volume-handoff generation
all planned Volumes and Chapters are adopted
all planned Scenes are adopted
no active candidate or Scene checkpoint exists
no unresolved staging transaction exists
workspace lock is held
```

Completion audit evaluates the story as adopted. It does not generate or revise prose.

---

## 29. COMP-PRE — Mechanical completion precondition

### 29.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `audit` |
| LLM call | none |
| output | Completion-precondition report and immutable Completion Context snapshot |
| next stage | `COMP-AUDIT` when passing |

### 29.2 Output path

```text
audit/completion/<generation-id>/completion-precondition.json
```

The complete report contract is defined in `review_and_audit.md`.

### 29.3 Minimum checks

```text
valid final HEAD Generation/Commit chain
final Commit type = volume_handoff
final adopted handoff
Brief Volume count
Series map and all Volume/Chapter plans
all planned Scene artifacts in order
final Story-clock Volume/Chapter/Scene position
current_order equals successful Scene count
all required Major Thread records and final State rows
all required Ending criteria
Evidence-index record integrity and quote validation
all Evidence target references
all Volume handoffs
all residual-issue audit integrity
no active checkpoint, candidate, or staging transaction
current output/CURRENT validity when it exists
Completion Context mandatory-set fit
```

### 29.4 Failure

When any check fails:

```text
all_checks_pass = false
Run status = failed
stop_reason_code = mechanical_error
next_stage = null
```

`COMP-AUDIT` is not called.

### 29.5 Passing postcondition

```text
Run last_completed_stage = COMP-PRE
Run next_stage = COMP-AUDIT
```

The Completion Context snapshot is immutable and reused by every audit attempt.

---

## 30. COMP-AUDIT — Completion audit attempts

### 30.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `completion_audit` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `completion_builder` |
| target ID | `completion` |
| response Schema | Completion-audit content candidate |
| revision rounds | never consumed |
| next stage | `COMP-SAVE` after first structurally valid attempt |

### 30.2 Candidate paths

```text
runtime/candidates/completion/
  candidate-manifest.json
  attempt-01.json
  attempt-02.json
```

There is one fixed Candidate manifest for the Completion operation.

### 30.3 Attempt semantics

For audit attempt `N`:

1. use the unchanged passing COMP-PRE Context snapshot;
2. initialize/update Candidate manifest `completion_audit_attempt=N`;
3. make one logical Completion call with configured response-structure retries;
4. preserve every provider attempt in unique LLM-call audits;
5. save `attempt-NN.json` only when one response is structurally valid;
6. route immediately to COMP-SAVE after the first valid attempt.

A structurally invalid logical audit attempt consumes one Completion-audit attempt after its response-structure retries are exhausted.

When another attempt remains, increment:

```text
completion_audit_attempts_used
```

and rerun with the identical Context snapshot.

### 30.4 Structurally valid semantic result

All values are valid candidates:

```text
complete
complete_with_residual_issues
incomplete
```

A valid `incomplete` result:

- is not response-retried;
- does not start another Completion-audit attempt;
- proceeds to COMP-SAVE;
- later fails COMP-PUBLISH.

### 30.5 Candidate-manifest success

```text
candidate_status = ready_for_adoption
candidate_path = attempt-NN.json
candidate_sha256 = exact attempt hash
last_structurally_valid = true
completion_audit_attempt = N
last_call_id = accepted Call ID
next_stage = COMP-SAVE
```

### 30.6 Exhaustion without valid attempt

If all Completion attempts fail structurally:

```text
run_status = failed
stop_reason_code = mechanical_error
next_stage = null
```

No private Completion audit is saved.

---

## 31. COMP-SAVE — Save accepted private audit

### 31.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `audit` |
| LLM call | none |
| source | Candidate-manifest-selected valid attempt |
| output | accepted private Completion audit |
| next stage | `OUT-01` |

### 31.2 Output path

```text
audit/completion/<generation-id>/completion-audit.json
```

### 31.3 Behavior

Code:

1. validates the Candidate manifest and selected attempt;
2. verifies source generation and Context hash;
3. verifies complete criterion and required-Thread coverage;
4. verifies the derived overall-assessment rules;
5. writes the accepted private audit with accepted-attempt metadata;
6. calculates its canonical hash;
7. clears the active Completion Candidate path;
8. updates Run state.

It does not change the semantic result.

### 31.4 Postcondition

```text
Run last_completed_stage = COMP-SAVE
Run next_stage = OUT-01
active_candidate_manifest_path = null
```

Even `incomplete` proceeds to deterministic output staging so validation reports can be inspected. It cannot be published.

---

# Part IV: Publication staging and adoption

## 32. Publication identifier and staging

OUT-01 allocates and persists one Publication ID before creating its staging directory.

```text
.staging/publication/<publication-id>/
```

An allocated Publication ID is never reused.

If staging later fails, the ID remains consumed.

The publication root is not stored inside publication-internal references.

Before adoption, code resolves publication-relative paths against:

```text
.staging/publication/<publication-id>/
```

After adoption, the same paths resolve against:

```text
publications/<publication-id>/
```

No final Publication manifest, Publication Validation, or Publication Gate field stores either root prefix.

---

## 33. Publication file sets and hashes

Publication construction uses three distinct file sets.

### 33.1 Provisional build set

During OUT-01, staging contains final payload files plus:

```text
publication-build-manifest.json
```

The provisional build manifest is internal transaction state and is never adopted.

### 33.2 Payload set

The payload set contains every intended final publication file except:

```text
publication-validation.json
publication-manifest.json
publication-build-manifest.json
```

It normally contains:

```text
manuscript files
metadata files
publication-safe reports
other Publishing-profile-defined final payload files
```

For each payload file, code creates one Publication file-reference record:

```text
relative_path
sha256
size_bytes
media_type
role
```

Records are unique and sorted by `relative_path`.

`payload_set_sha256` is SHA-256 over the canonical JSON array of those sorted records.

### 33.3 Final referenced file set

After OUT-02 writes a passing `publication-validation.json`, the final Publication-manifest `files` array contains:

```text
every payload-set file reference
the publication-validation.json file reference
```

It excludes:

```text
publication-manifest.json
publication-build-manifest.json
```

`content_set_sha256` is SHA-256 over the canonical JSON array of the complete sorted `files` records.

This two-level design avoids a hash cycle:

```text
Publication Validation:
  hashes payload-set records only

Publication manifest:
  hashes payload records plus the finalized Validation record
  does not hash itself
```

### 33.4 Rename stability

All records in both hash sets use publication-root-relative paths.

Therefore these hashes remain unchanged when:

```text
.staging/publication/<publication-id>/
→
publications/<publication-id>/
```

---

## 34. Default publication file layout

The default KDP local publication contains:

```text
manuscript/
  series.md
  v01.md
  v02.md
  ...

metadata/
  series.json
  volumes/
    v01.json
    v02.json
    ...

reports/
  completion-audit.json

publication-validation.json
publication-manifest.json
```

The following must not exist in a valid final staged or adopted publication:

```text
publication-build-manifest.json
private Completion-audit file
candidate or Review file
Context snapshot
LLM-call audit
workspace pointer file
```

A Publishing profile may add registered payload roles and paths. It may not remove the required Validation or Manifest files.

---

## 35. Deterministic manuscript assembly

OUT-01 builds reader-facing manuscript text from adopted prose only.

### 35.1 Ordering

```text
Series-map Volume order
Volume-design Chapter order
Chapter-design Scene order
```

Every Scene manifest and prose hash must validate before inclusion.

No filesystem modification time or directory enumeration order affects manuscript order.

### 35.2 Generated headings

Code may add deterministic headings derived from adopted plan titles:

```text
series title
Volume title
Chapter title
```

Generated headings:

- are not part of Scene prose;
- do not become prose Evidence;
- do not alter Scene character counts;
- must be reproduced byte-for-byte by the same code/profile version.

### 35.3 `manuscript/series.md`

Contains all Volumes in canonical order with deterministic Volume and Chapter headings.

### 35.4 `manuscript/vNN.md`

Contains one Volume with all Chapters and Scenes in canonical order.

### 35.5 Reader-facing exclusions

Manuscript files must not contain:

```text
persistent record IDs
Scene IDs
Commit or Generation IDs
Evidence IDs
internal workspace paths
candidate/checkpoint/staging paths
Review or residual-Issue text
Completion-audit commentary
provider/runtime metadata
author truth not present in adopted prose
```

An internal identifier that appears coincidentally as ordinary prose is rejected only when it exactly matches a known allocated identifier token and appears outside a quoted story-use exception registered by the Publishing profile.

---

## 36. Publication metadata

### 36.1 Series metadata

`metadata/series.json` contains exactly:

```text
schema_version
title
genre
target_reader
volume_count
editorial_profile_id
publishing_profile_id
source_generation_id
source_generation_manifest_sha256
completion_overall_assessment
created_at
```

It contains no:

```text
Brief avoid list
private ending text
Thread author truth
private Completion-audit path
workspace path
```

### 36.2 Volume metadata

Each `metadata/volumes/vNN.json` contains exactly:

```text
schema_version
volume_number
title
chapter_count
scene_count
character_count
source_volume_design_sha256
source_handoff_sha256
manuscript_relative_path
manuscript_sha256
created_at
```

`character_count` is the sum of adopted Scene-manifest prose character counts for that Volume.

Generated publication headings are excluded.

### 36.3 Relative paths

Every metadata path is relative to the publication root.

Forbidden examples:

```text
.staging/publication/pub-000001/manuscript/v01.md
publications/pub-000001/manuscript/v01.md
/mnt/work/story/manuscript/v01.md
```

Required form:

```text
manuscript/v01.md
```

---

## 37. Provisional build manifest

OUT-01 writes:

```text
publication-build-manifest.json
```

This file has artifact class `staged_internal`.

It contains:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | exact |
| `publication_id` | Publication ID | yes | no | none | code | staging target |
| `source_generation_id` | Generation ID | yes | no | none | code | current HEAD |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | source generation |
| `private_completion_audit_path` | workspace-relative path | yes | no | none | code | accepted private audit |
| `private_completion_audit_sha256` | SHA-256 | yes | no | none | code | matches |
| `completion_precondition_path` | workspace-relative path | yes | no | none | code | passing report |
| `completion_precondition_sha256` | SHA-256 | yes | no | none | code | matches |
| `expected_payload_file_refs` | array<Publication file reference> | yes | no | none | code | exact OUT-01 payload set |
| `payload_set_sha256` | SHA-256 | yes | no | none | code | expected payload-set hash |
| `current_pointer_before` | Publication ID | yes | yes | `null` | code | exact `output/CURRENT` before build |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

The private Completion-audit path is permitted only in this provisional internal file.

The build manifest is not referenced by:

```text
publication-validation.json
publication-manifest.json
Publication Gate
adopted publication metadata
```

OUT-02 removes it before declaring the final staged publication valid.

---

## 38. OUT-01 — Build publication payload staging

### 38.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `staged_internal` and separate `audit` |
| LLM call | none |
| input | accepted private Completion audit and all adopted story artifacts |
| output | payload files and provisional build manifest |
| next stage | `OUT-02` |

### 38.2 Preconditions

```text
Run-state next_stage = OUT-01
accepted private Completion audit exists and hashes
passing Completion precondition exists and hashes
source generation equals current canon/HEAD
source Generation manifest validates
no active candidate or Scene checkpoint
no conflicting publication staging for the allocated Publication ID
output/CURRENT is valid when it exists
workspace lock is held
```

### 38.3 Behavior

Code:

1. allocates and persists one Publication ID;
2. records the exact prior `output/CURRENT` value or null;
3. creates the staging directory;
4. assembles deterministic manuscript files;
5. creates Series and Volume metadata;
6. creates the publication-safe Completion report;
7. validates each payload file's canonical bytes;
8. creates sorted payload file references;
9. calculates `payload_set_sha256`;
10. writes the provisional build manifest;
11. re-reads and validates every payload file and the build manifest;
12. atomically updates Run state.

### 38.4 OUT-01 restrictions

OUT-01 does not write:

```text
publication-validation.json
publication-manifest.json
Publication Gate
publications/<publication-id>/
output/CURRENT
```

### 38.5 Postcondition

```text
Run last_completed_stage = OUT-01
Run next_stage = OUT-02
```

No adopted publication or pointer changes.

---

## 39. OUT-02 — Validate payload and finalize staged publication

### 39.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact classes | `staged_internal_validation`, `staged_internal`, and separate `audit` |
| LLM call | none |
| input | complete OUT-01 payload staging and build manifest |
| output | finalized Validation and Publication manifest |
| next stage | `COMP-PUBLISH` when passing |

### 39.2 Pre-validation

Code validates:

```text
Run-state next_stage = OUT-02
Publication ID and staging root
build-manifest hash and exact fields
source generation still equals canon/HEAD
private Completion-audit and precondition hashes
current output/CURRENT still equals current_pointer_before
expected payload file set
absence of an existing final Publication manifest from another transaction
```

### 39.3 Payload validation

OUT-02 performs every check required by `review_and_audit.md`, including:

```text
all expected Volumes present
Volume/Chapter/Scene ordering
nonempty manuscript files
adopted prose hash and character-count reconciliation
generated-heading determinism
metadata completeness
publication-safe Completion report
no private author truth
no credentials, prompts, or raw provider responses
no candidate/checkpoint/staging or absolute path in final payload
no internal IDs in reader-facing manuscript
Publishing-profile constraints
payload file hashes, sizes, media types, and roles
```

Code independently reconstructs the sorted payload references.

It verifies:

```text
recomputed payload_set_sha256
  ==
build-manifest payload_set_sha256
```

### 39.4 Validation-file construction

Code writes canonical:

```text
publication-validation.json
```

The record contains:

```text
publication_id
source generation identity
Publishing-profile ID
complete sorted checks
validation_status
validated_payload_file_count
payload_set_sha256
created_at
```

It contains no:

```text
staging-root path
Publication-manifest hash
content_set_sha256
private Completion-audit path
```

### 39.5 Validation failure

When any check fails:

1. write a valid `publication-validation.json` with `validation_status=fail`;
2. do not write a passing `publication-manifest.json`;
3. leave the provisional build manifest for diagnosis or quarantine;
4. write an operation audit;
5. set:
   ```text
   run_status = failed
   stop_reason_code = mechanical_error
   next_stage = null
   ```

A previous partial `publication-manifest.json` in staging is quarantined or removed only after proving it was never Gate-referenced or adopted.

### 39.6 Final Publication-manifest construction

Only after Validation passes, code:

1. hashes finalized `publication-validation.json`;
2. creates its Publication file reference with role `validation`;
3. combines:
   ```text
   payload references
   Validation reference
   ```
4. sorts the complete `files` array by `relative_path`;
5. calculates `content_set_sha256`;
6. creates canonical `publication-manifest.json` using the Runtime contract;
7. sets:
   ```text
   validation_relative_path = publication-validation.json
   validation_sha256 = finalized Validation hash
   completion_audit_relative_path = reports/completion-audit.json
   completion_audit_sha256 = safe report hash
   current_pointer_before = build-manifest value
   current_pointer_after = publication_id
   ```
8. atomically writes the final Manifest;
9. removes `publication-build-manifest.json`;
10. re-scans the staging root.

### 39.7 Final staged-publication validation

After removing the provisional file, code verifies:

```text
the root contains exactly:
  publication-manifest.json
  every file listed in Manifest.files

publication-build-manifest.json is absent
every Manifest.files reference resolves under the staging root
every file hash/size/media type/role matches
Manifest validation hash matches publication-validation.json
Manifest safe Completion-report hash matches
recomputed content_set_sha256 equals Manifest value
recomputed payload_set_sha256 equals Validation value
no final file contains a staging-root prefix
```

The Manifest itself is not included in `files` or `content_set_sha256`.

### 39.8 Passing postcondition

```text
Run last_completed_stage = OUT-02
Run next_stage = COMP-PUBLISH
```

Staging is finalized but remains unadopted.

---

## 40. COMP-PUBLISH — Rename-stable Publication Gate

### 40.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `audit` |
| LLM call | none |
| input | Completion records and finalized staged publication |
| output | immutable Publication Gate result |
| adoption | forbidden |
| passing next stage | `OUT-03` |

### 40.2 Gate path

```text
audit/publication-gates/<publication-id>.json
```

### 40.3 Current publication root

At normal Gate evaluation, publication-relative references are resolved against:

```text
.staging/publication/<publication-id>/
```

The Gate stores only:

```text
publication_id
publication-root-relative paths
hashes
```

It never stores the staging root.

### 40.4 Publication snapshot

Code calculates `publication_snapshot_sha256` from canonical JSON containing exactly:

```text
publication_id
source_generation_id
source_generation_manifest_sha256
publication_validation_relative_path
publication_validation_sha256
publication_manifest_relative_path
publication_manifest_sha256
payload_set_sha256
content_set_sha256
```

Required relative paths:

```text
publication_validation_relative_path = publication-validation.json
publication_manifest_relative_path = publication-manifest.json
```

### 40.5 Gate evaluation

Code validates:

```text
Completion precondition all_checks_pass = true
Completion precondition hash
accepted private Completion-audit hash
Completion audit structural validity
Completion overall assessment
source generation still equals current canon/HEAD
source Generation-manifest hash
Publication Validation status = pass
Validation payload_set_sha256
recomputed payload-set hash
Publication Manifest hash
Manifest lists Validation with exact hash
Manifest content_set_sha256
recomputed complete files-array hash
every Manifest file reference under current publication root
absence of provisional build manifest
publication_snapshot_sha256
no conflicting final publication directory
output/CURRENT still equals Manifest current_pointer_before
```

### 40.6 Gate pass

Gate passes only when:

```text
Completion overall assessment =
  complete
  OR complete_with_residual_issues

and every mechanical Gate check passes
```

The Gate record stores all rename-stable hashes and has:

```text
gate_status = pass
failures = []
```

Postcondition:

```text
Run last_completed_stage = COMP-PUBLISH
Run next_stage = OUT-03
```

### 40.7 Semantic Gate failure

When the accepted private audit has:

```text
overall_assessment = incomplete
```

code still writes the complete Gate record with:

```text
gate_status = fail
failure code = COMPLETION_INCOMPLETE
source_role = completion_audit
```

Run state becomes:

```text
last_completed_stage = COMP-PUBLISH
run_status = stopped
stop_reason_code = manual_intervention
next_stage = null
```

The finalized staged publication remains unadopted.

No additional Completion-audit attempt is made.

### 40.8 Mechanical Gate failure

A hash, source-generation, Validation, Manifest, payload-set, content-set, pointer, or root mismatch produces a failing Gate and:

```text
run_status = failed
stop_reason_code = mechanical_error
next_stage = null
```

Publication-internal failure records use:

```text
artifact_path = null
publication_relative_path = root-relative path
```

They never persist `.staging/publication/...`.

### 40.9 COMP-PUBLISH restrictions

COMP-PUBLISH does not:

```text
rename staging
create or replace publications/<publication-id>/
change output/CURRENT
change canon/HEAD
modify publication-validation.json
modify publication-manifest.json
modify any payload file
```

---

## 41. OUT-03 — Adopt publication and change `output/CURRENT`

### 41.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `adopted` and separate `audit` |
| LLM call | none |
| input | passing rename-stable Gate |
| output | adopted publication and changed `output/CURRENT` |
| next stage | none; run completed |

### 41.2 Root-selection modes

OUT-03 selects exactly one publication root.

#### Normal mode

Condition:

```text
staging root exists
final publication root does not exist
```

Selected root:

```text
.staging/publication/<publication-id>/
```

#### Explicit post-rename recovery mode

Condition:

```text
staging root does not exist
final publication root exists
output/CURRENT does not point to publication_id
Run state and a valid passing Gate explicitly require OUT-03 recovery
```

Selected root:

```text
publications/<publication-id>/
```

The final directory is never selected merely because it exists.

#### Conflict

These are mechanical failures:

```text
both roots exist
neither root exists
final root exists in normal mode
selected root Publication ID differs
selected root fails Gate snapshot validation
```

### 41.3 Final Gate revalidation

Against the selected root, code validates:

```text
workspace lock
Gate path/hash and Gate Schema
gate_status = pass
source generation still equals canon/HEAD
Publication Validation relative path/hash
Publication Manifest relative path/hash
payload_set_sha256
content_set_sha256
publication_snapshot_sha256
every Manifest file reference/hash/size/media type/role
absence of provisional build manifest
output/CURRENT equals Manifest current_pointer_before
final publication directory conflict rules
```

The selected root must reproduce every hash stored by the Gate.

### 41.4 Normal adoption order

When the selected root is staging:

1. `fsync` all staged publication files and directories;
2. atomically rename:
   ```text
   .staging/publication/<publication-id>
   →
   publications/<publication-id>
   ```
3. re-resolve all Gate-relative paths against the final root;
4. revalidate:
   ```text
   Validation hash
   Manifest hash
   payload_set_sha256
   content_set_sha256
   publication_snapshot_sha256
   ```
5. atomically replace:
   ```text
   output/CURRENT = "<publication-id>\n"
   ```
6. atomically update Run state;
7. write the successful OUT-03 operation audit;
8. remove empty staging parent directories.

### 41.5 Explicit recovery adoption order

When the selected root is the already-renamed final directory:

1. verify the directory is not referenced by another pointer or Publication ID;
2. reproduce the passing Gate snapshot from the final root;
3. `fsync` the final directory and pointer parent;
4. atomically replace `output/CURRENT`;
5. atomically update Run state;
6. write an explicit recovery operation audit.

No directory rename occurs in this mode.

### 41.6 Adoption point

```text
output/CURRENT
```

is the publication-adoption point.

A publication directory at `publications/<publication-id>/` is not adopted until CURRENT points to it.

### 41.7 Completed Run state

```text
last_completed_stage = OUT-03
next_stage = null
current_publication_id = publication_id
run_status = completed
stop_reason_code = completed
stop_reason_detail = null
active_candidate_manifest_path = null
active_checkpoint_manifest_path = null
scene_phase = null
```

The run is not completed before the pointer and Run state are durable.

---

## 42. Publication crash semantics

### 42.1 Before directory rename

Only finalized staging exists.

Startup may resume OUT-03 only when:

```text
Run state identifies OUT-03
a passing Gate validates
the staging root reproduces the Gate snapshot
```

Otherwise staging is quarantined.

### 42.2 After directory rename but before CURRENT replacement

The final directory exists but is unadopted.

Startup does not publish it by inference.

It may perform explicit OUT-03 recovery only when:

```text
Run state identifies the exact Publication ID and OUT-03
the original passing Gate validates
the final root reproduces publication_snapshot_sha256
CURRENT still equals Manifest current_pointer_before
no conflicting staging root exists
```

Otherwise the final directory is quarantined as an unadopted publication.

### 42.3 After CURRENT replacement but before Run-state update

The publication is adopted.

Startup:

- validates `output/CURRENT`;
- validates the target Publication Manifest and complete file set;
- validates the Gate snapshot when the Gate is present;
- reconciles Run state to completed;
- writes a reconciliation operation audit;
- cleans leftover empty staging directories.

### 42.4 Invalid CURRENT target

Startup stops mechanically.

It never chooses another publication by:

```text
directory order
modification time
highest Publication ID
parse success
semantic plausibility
```

---

# Part V: Resume and transition rules

## 43. Scene-commit resume matrix

| stage | authoritative resume source |
|---|---|
| `COMMIT-01` | DELTA_ACCEPTED Checkpoint manifest and current HEAD |
| `COMMIT-02` | passing Commit plan and Transaction manifest when present |
| `COMMIT-03` | Transaction manifest, merge plan, staged root files, checkpoint |
| `COMMIT-04` | COMMIT_PREPARED Checkpoint manifest and validated transaction |
| post-crash route | valid HEAD Commit/Generation/Scene manifests |

A raw operation log is not a resume source.

---

## 44. Handoff resume matrix

| stage | authoritative resume source |
|---|---|
| `VH-01` | final-Scene HEAD, plans, active Handoff Candidate manifest |
| `VH-02` | active normalized Handoff candidate and matching Review |
| `VH-REV` | active reviewed candidate and Revision Context |
| `VH-ID` | active ready candidate, Review, residual issues, valid staging when present |
| post-crash route | valid HEAD Handoff Commit/Generation and adopted Handoff |

A standalone Handoff file not referenced by the valid HEAD chain is not authoritative.

---

## 45. Completion/output resume matrix

| stage | authoritative resume source |
|---|---|
| `COMP-PRE` | final Handoff HEAD and adopted story artifacts |
| `COMP-AUDIT` | passing precondition, immutable Completion Context, Completion Candidate manifest |
| `COMP-SAVE` | Candidate-manifest-selected valid attempt |
| `OUT-01` | accepted private Completion audit and passing precondition |
| `OUT-02` | payload staging and provisional build manifest |
| `COMP-PUBLISH` | private audit, precondition, finalized Validation and Manifest under staging root |
| `OUT-03` | passing Gate and one explicitly selected publication root |
| completed reconciliation | valid `output/CURRENT` target and Publication Manifest |

Raw LLM audit responses are never promoted into Completion attempt files.

---

## 46. Normal stage transitions

### 46.1 Scene commit

```text
COMMIT-01
→ COMMIT-02
→ COMMIT-03
→ COMMIT-04
```

After COMMIT-04:

```text
next Scene:
  SC-01

next Chapter:
  CH-01

Volume complete:
  VH-01
```

### 46.2 Volume handoff

```text
VH-01
→ VH-02

VH-02
→ VH-REV
  OR VH-ID

VH-REV
→ VH-02

VH-ID
→ VOL-01
  OR COMP-PRE
```

### 46.3 Completion and output

```text
COMP-PRE
→ COMP-AUDIT
→ COMP-SAVE
→ OUT-01
→ OUT-02
→ COMP-PUBLISH
→ OUT-03
```

`OUT-03` has no next stage.

No other normal transition is permitted.

---

## 47. Stage completion rule

A stage is complete only when:

```text
its output artifact exists
its canonical hash is known
its applicable manifest or Validation is durable
all stage-specific checks pass
Run state records last_completed_stage and next_stage
```

Additional adoption requirements:

| stage | adoption point |
|---|---|
| `COMMIT-04` | `canon/HEAD` changed to Scene generation |
| `VH-ID` | `canon/HEAD` changed to Handoff generation |
| `OUT-03` | `output/CURRENT` changed to Publication ID |

Receiving a provider response is never stage completion.

A passing Gate is not publication adoption.

---

## 48. Error behavior

| failure | result |
|---|---|
| Scene/Handoff mechanical validation failure | failed; pointers unchanged |
| provider transport or structure exhaustion | failed; no automatic next stage |
| Handoff semantic Review issues | revision/exhaustion routing |
| Completion precondition failure | failed; no auditor call |
| structurally valid Completion `incomplete` | save audit, build and validate staging, Gate fail, stopped |
| Completion-attempt structural exhaustion | failed |
| payload Validation failure | failed; no final passing Manifest or Gate |
| final Manifest/content-set mismatch | failed |
| Gate mechanical mismatch | failed |
| Gate semantic incomplete | stopped with manual intervention |
| OUT-03 selected-root or pointer mismatch | failed |
| budget preflight failure | stopped with budget exhausted |
| explicit safe-boundary user stop | stopped with user stop |

A user stop does not interrupt an atomic rename, pointer replacement, or manifest replacement.

---

# Part VI: Invariants and forbidden shortcuts

## 49. Scene-commit invariants

```text
one Scene checkpoint produces at most one adopted Scene
Commit before generation equals checkpoint source generation
Commit after-generation suffix equals Commit-ID suffix
Scene current_order increments exactly once
Handoff current_order never increments
committed delta contains no unresolved local key
all committed Evidence IDs exist
all Evidence quotes resolve in adopted prose
all staged State/Canon changes are represented by committed delta
all committed-delta changes appear in staged roots
Scene-manifest paths are adopted paths
HEAD is changed after generation and Scene durability
```

---

## 50. Handoff invariants

```text
one adopted Handoff per Volume
Handoff source generation is the final Scene generation of that Volume
Handoff adopted generation is a volume_handoff Commit
only Thread volume_disposition may change
Thread status/progress do not change
Story clock does not change
current_order does not change
Evidence index does not change
current Canon and Knowledge items do not change
required Major Thread is never retired
final Volume required Major Threads use resolve
nonfinal carry_over requires series scope and in_progress State
HEAD is changed after Handoff and generation durability
```

---

## 51. Completion/output invariants

```text
Completion Context uses final Handoff HEAD
every required Ending criterion is assessed
every required Major Thread is assessed
semantic incomplete is not response-retried
private Completion audit is not copied into publication
safe report contains no author truth

payload_set_sha256 covers payload files only
Publication Validation contains payload_set_sha256
Publication Validation contains no final Manifest hash
Publication Manifest files include Validation and all payload files
Publication Manifest excludes itself and provisional build manifest
content_set_sha256 covers the complete Manifest.files array
provisional build manifest is absent before Gate

Publication Validation and Manifest contain only root-relative internal paths
Gate publication-internal references are root-relative
Gate stores Publication Validation hash
Gate stores Publication Manifest hash
Gate stores payload_set_sha256
Gate stores content_set_sha256
Gate publication_snapshot_sha256 is rename-stable

COMP-PUBLISH creates no adopted artifact
Gate pass excludes incomplete
OUT-03 reproduces the Gate snapshot before adoption
OUT-03 revalidates the same snapshot after normal rename
CURRENT is changed only after publication-directory durability
Run completed iff last_completed_stage = OUT-03
```

---

## 52. Forbidden implementation shortcuts

Forbidden:

```text
mutating an adopted generation for Volume disposition
storing Volume disposition only in an unversioned mutable file
using Scene commit_type for a Handoff-only generation
allocating IDs during COMMIT-01
using placeholder IDs and repairing them later
building committed delta independently from the merge plan
omitting staged State changes from committed delta
copying checkpoint paths into adopted Scene manifest
changing HEAD before Generation/Scene/Handoff durability
using filesystem timestamp to select a transaction or candidate
overwriting an adopted Scene or Handoff
reviewing a mechanically invalid Handoff
retrying Completion until it says complete
treating semantic incomplete as response-structure error
putting private Completion audit into publication

hashing publication-validation.json inside payload_set_sha256
hashing publication-manifest.json inside content_set_sha256
making Validation hash the Manifest while Manifest hashes Validation
keeping publication-build-manifest.json in a finalized publication
writing a final Publication manifest with staging-root paths
persisting .staging/publication/... inside a Gate
recomputing Gate fields after publication rename
letting COMP-PUBLISH rename, adopt, or change CURRENT
selecting an already-renamed publication directory by inference
changing CURRENT before publication-directory durability
marking Run completed before OUT-03
using artifact class adopted/audit
using audit files as resume candidates
```

---

## 53. Mechanical acceptance conditions

An implementation of this pipeline is acceptable only when tests demonstrate:

```text
exact stage IDs and processors
canonical artifact classes

COMMIT-01 complete dry validation
no COMMIT-01 allocation
deterministic allocation requests
Commit/Generation ID allocation
persistent-ID and Evidence-ID persistence before use
merge-plan complete resolution
staged Canon/Knowledge/State/Evidence construction
committed-delta normalization
Evidence offset/hash calculation
Scene-card/prose checkpoint byte equality
committed delta to after-State bidirectional correspondence
Scene/Commit/Generation manifest hash graph
COMMIT_PREPARED checkpoint
COMMIT-04 HEAD-last adoption
next Scene/Chapter/Handoff routing
Scene-commit crash behavior

versioned Handoff candidates and Reviews
Handoff exact child Schemas
Thread-decision coverage and disposition matrix
Handoff revision whole replacement
semantic residual Handoff adoption
volume_handoff Commit type
Handoff-only Story-state change
Handoff current-order preservation
Handoff HEAD-last adoption
final Handoff to COMP-PRE routing

Completion precondition complete checks
immutable Completion Context reuse
Completion attempt and response-retry counters
valid incomplete audit does not retry
accepted private Completion audit

Publication-ID allocation and non-reuse
deterministic manuscript assembly
reader-facing internal-ID rejection
publication-safe Completion report
provisional build-manifest exact Schema
payload file-reference reconstruction
payload_set_sha256 calculation
Validation excludes Manifest/content-set hash
Validation failure prevents Gate

final Manifest includes Validation reference
content_set_sha256 calculation
Manifest excludes itself and provisional build manifest
finalized staging exact file-set validation
publication-root-relative path enforcement

Gate Publication Validation hash
Gate Publication Manifest hash
Gate payload_set_sha256
Gate content_set_sha256
Gate publication_snapshot_sha256
Gate failure relative-path records
Gate pass/fail semantics
COMP-PUBLISH no adoption or mutation

OUT-03 staging-root selection
OUT-03 explicit post-rename recovery selection
OUT-03 Gate snapshot reproduction before rename
OUT-03 Gate snapshot reproduction after rename
OUT-03 publication rename then CURRENT
publication crash reconciliation
completed Run-state conditions

unknown transition rejection
unknown-field rejection
placeholder-hash rejection
canonical hash stability
