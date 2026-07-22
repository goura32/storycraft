# Pipeline contracts: Scene generation

This document is the normative pipeline contract for producing one frozen Scene card, one frozen prose artifact, and one validated candidate continuity delta:

```text
SC-01
SC-02
SC-REV
SC-CHK

PROSE-01
PROSE-02
PROSE-REV
PROSE-CHK

DELTA-01
DELTA-02
DELTA-REV
DELTA-CHK
```

Scene data contracts are defined by [`../data/scene_artifacts.md`](../data/scene_artifacts.md). Continuity candidates and committed deltas are defined by [`../ledger/evidence_and_updates.md`](../ledger/evidence_and_updates.md). Canon and Story-state contracts are defined by the Ledger documents under [`../ledger/`](../ledger/). Runtime candidate manifests, checkpoints, Run state, and atomic-write rules are defined by [`../ledger/runtime_records.md`](../ledger/runtime_records.md). Context views are defined by [`../../context_contracts.md`](../../context_contracts.md). Retry, budget, provider, token, and profile rules are defined by [`../../configuration_contracts.md`](../../configuration_contracts.md). Review and residual-issue records are defined by [`../data/review_and_audit.md`](../data/review_and_audit.md).

Every JSON object written by this pipeline uses `additionalProperties: false`.

---

## 1. Pipeline purpose

This pipeline prepares one scene for atomic commit without modifying Canon, Story state, Evidence index, `canon/HEAD`, or adopted Scene artifacts.

It guarantees:

```text
one frozen Scene card derived from one Chapter Scene-function target
one frozen canonical prose body
one validated candidate continuity delta grounded in that prose
one checkpoint manifest with exact source-generation and artifact hashes
complete semantic Review or revision-exhaustion handling for each candidate family
no persistent-ID allocation for new scene-derived records
no Evidence-ID, offset, or hash generation before commit
```

The pipeline ends at:

```text
checkpoint phase = DELTA_ACCEPTED
Run-state next_stage = COMMIT-01
```

The commit pipeline alone transforms the candidate delta, allocates IDs, creates Evidence records, constructs the adopted Scene artifact set, updates the generation, and changes `canon/HEAD`.

---

## 2. Stage families

| family | generation | review | revision | checkpoint |
|---|---|---|---|---|
| Scene card | `SC-01` | `SC-02` | `SC-REV` | `SC-CHK` |
| Prose | `PROSE-01` | `PROSE-02` | `PROSE-REV` | `PROSE-CHK` |
| Continuity delta | `DELTA-01` | `DELTA-02` | `DELTA-REV` | `DELTA-CHK` |

Processor types:

| stage | processor type |
|---|---|
| `SC-01` | `llm_generate` |
| `SC-02` | `llm_review` |
| `SC-REV` | `llm_revise` |
| `SC-CHK` | `code` |
| `PROSE-01` | `llm_generate` |
| `PROSE-02` | `llm_review` |
| `PROSE-REV` | `llm_revise` |
| `PROSE-CHK` | `code` |
| `DELTA-01` | `llm_extract` |
| `DELTA-02` | `llm_review` |
| `DELTA-REV` | `llm_revise` |
| `DELTA-CHK` | `code` |

No other processor type is permitted for these stages.

---

## 3. Artifact classes

Only canonical artifact classes are used.

| artifact | class |
|---|---|
| unreviewed/revised Scene-card content | `candidate` |
| unreviewed/revised prose | `candidate` |
| unreviewed/revised continuity delta | `candidate` |
| frozen Scene card, prose, candidate delta, Checkpoint manifest | `checkpoint` |
| Review, residual Issue, LLM-call, and operation records | `audit` |

This pipeline does not create:

```text
staged_internal
staged_internal_validation
adopted
```

Those classes are used by the later commit pipeline.

Forbidden artifact classes:

```text
review candidate
checkpoint/audit
candidate/checkpoint
adopted/audit
```

---

## 4. Scene target identity

### 4.1 Target ID

Every stage in this pipeline uses:

```text
target_id = scene_id = vNN-cNNN-sNNN
```

Example:

```text
v04-c003-s002
```

### 4.2 Coordinates

Run state must contain:

```text
current_target_id = scene_id
current_volume_number
current_chapter_number
current_scene_number
```

All values must match:

```text
adopted Chapter-design path
Chapter-design volume_number/chapter_number
target Scene-function scene_number
checkpoint directory
Scene ID components
```

The LLM never emits the Scene ID or numeric coordinates.

### 4.3 Entry phase

Normal entry from `CH-ID` or the previous scene commit is:

```text
scene_phase = SCENE_NOT_STARTED
next_stage = SC-01
active_candidate_manifest_path = null
active_checkpoint_manifest_path = null
```

A checkpoint directory for the same Scene must not already exist unless the Runtime reconciliation rules identify it as a valid resumable checkpoint.

---

## 5. Scene entry conditions

SC-01 may begin only when:

```text
valid canon/HEAD exists
valid HEAD Generation and Commit manifests exist
adopted Chapter design exists
target Scene-function entry exists
target Scene has no adopted Scene artifact
target Scene number is the next uncommitted Scene in the Chapter
current Story-clock position is compatible with the target
workspace lock is held
Run and Effective-config compatibility passes
```

For Scene 1 of a Chapter:

- the Chapter design is already adopted;
- the current HEAD is the Chapter-start source generation.

For Scene `>1`:

- the previous Scene must be adopted;
- current HEAD must be the previous Scene's adopted generation;
- the immediately previous Scene manifest and committed-delta `handoff_summary` are available to Context Builder.

Scene generation never selects the next Scene by scanning filesystem modification times.

---

## 6. Source-generation invariant

SC-01 fixes one pre-scene source generation:

```text
source_generation_id = current canon/HEAD
```

The same source generation must remain current through:

```text
SC-01
SC-02
SC-REV
SC-CHK
PROSE-01
PROSE-02
PROSE-REV
PROSE-CHK
DELTA-01
DELTA-02
DELTA-REV
DELTA-CHK
COMMIT-01 preflight
```

Code rechecks:

```text
canon/HEAD
source Generation-manifest hash
```

before every generation, Review, revision, checkpoint, and commit-preparation stage.

A mismatch invalidates the active checkpoint and all downstream candidates. Code does not rebase the Scene card, prose, or delta.

Under the single-writer normal pipeline, a mismatch indicates:

```text
manual modification
crash-recovery anomaly
incorrect concurrent writer
implementation defect
```

Recovery is defined in Section 38.

---

## 7. Candidate version directories

Each candidate family has its own immutable version history.

### 7.1 Scene-card paths

```text
runtime/candidates/scenes/vNN/cNNN/sNNN/scene-card/v0001/
  scene-card.json
  review.json
  candidate-manifest.json
```

### 7.2 Prose paths

```text
runtime/candidates/scenes/vNN/cNNN/sNNN/prose/v0001/
  prose.md
  review.json
  candidate-manifest.json
```

### 7.3 Continuity paths

```text
runtime/candidates/scenes/vNN/cNNN/sNNN/continuity/v0001/
  continuity-delta.json
  review.json
  candidate-manifest.json
```

### 7.4 Version rules

- `v0001` is created by the family generation owner.
- A successful semantic revision creates `v0002`, then `v0003`, and so on.
- A version directory is never overwritten or reused.
- `review.json` exists only after that exact version is reviewed.
- Older versions and Reviews remain immutable.
- Run state points only to the active version's Candidate manifest.
- Checkpoint stages read the exact active ready version.
- No stage selects “the newest” candidate by filename or filesystem timestamp.

### 7.5 Logical owners

| candidate family | owner operation | owner processor |
|---|---|---|
| Scene card | `SC-01` | `llm_generate` |
| prose | `PROSE-01` | `llm_generate` |
| continuity delta | `DELTA-01` | `llm_extract` |

A revised version retains the logical owner fields in its Candidate manifest.

The actual revision call is recorded through:

```text
new candidate version
revision_rounds_used
last_call_id
unique LLM-call audit role = revise
Revision Context snapshot
```

---

## 8. Common provider-call behavior

Every generation, Review, and revision stage follows the provider-call rules in `configuration_contracts.md`.

Before each provider request, code validates:

```text
workspace lock
Run-state next_stage and scene target
source-generation equality
required parent plan/checkpoint artifacts
required Context snapshot and hash
Effective-config compatibility
provider credential availability
context hard input limit
call, token, cost, time, and audit-storage budget
candidate-version destination availability
```

For every provider HTTP attempt, code:

1. persists a new Call ID;
2. creates a unique redacted LLM-call audit;
3. applies transport timeout and retry rules;
4. persists actual or estimated usage before response routing;
5. performs structural validation.

A structurally invalid response never creates a candidate or Review file.

---

## 9. Structural failure versus semantic issue

### 9.1 Structural/conditional failure

Examples:

```text
invalid JSON
unknown field
wrong enum
missing required field
wrong target ID
unresolved persistent reference
retired record reference
invalid Thread transition
invalid Knowledge transition
Scene-card policy exceeds configuration
prose is empty or uses forbidden markup
Evidence quote is absent or non-unique
delta target is not Scene-card-authorized
candidate before value differs from HEAD
new persistent ID, Evidence ID, offset, or hash injected
```

These consume response-structure retries.

### 9.2 Semantic issue

Examples:

```text
weak Scene purpose
unclear emotional change
required beat handled poorly
voice inconsistency
insufficient dramatic tension
prose target not convincingly achieved
continuity interpretation is plausible but incomplete
```

These appear in a structurally valid Review and consume semantic revision rounds.

### 9.3 Revision exhaustion

Only a structurally and mechanically valid candidate may proceed after revision exhaustion.

A mechanical defect never becomes a residual semantic issue.

---

## 10. Common Candidate-manifest lifecycle

### 10.1 New version

Before the accepted response is durable:

```text
candidate_version = version-directory number
candidate_status = initialized
candidate_path = null
candidate_sha256 = null
review_path = null
review_sha256 = null
last_structurally_valid = false
```

After one structurally valid candidate is durable:

```text
candidate_status = candidate_valid
candidate_path = exact family candidate path
candidate_sha256 = canonical candidate hash
last_structurally_valid = true
review_path = null
review_sha256 = null
last_call_id = accepted Call ID
next_stage = family Review stage
```

### 10.2 After Review

After `review.json` is durable:

```text
candidate_status = reviewed
review_path = exact Review path
review_sha256 = exact Review hash
```

Code then persists the routing result.

### 10.3 Ready for checkpoint

A candidate uses Runtime status:

```text
ready_for_adoption
```

to mean ready for its family checkpoint stage.

It requires:

```text
candidate remains structurally valid
Review path/hash match candidate version
issues are empty
OR revision budget is exhausted and residual Issues are durable
source generation and upstream frozen artifacts remain unchanged
```

The word `adoption` in Candidate status does not mean the story artifact is adopted. The checkpoint stage only freezes it.

### 10.4 Superseded version

When a new revision version becomes active:

- the prior version's manifest is frozen;
- Run state moves only after the new candidate and manifest are durable;
- the prior Review remains immutable;
- no checkpoint stage may use the prior version.

---

## 11. Common Review contract

| family | review stage | reviewed artifact role |
|---|---|---|
| Scene card | `SC-02` | `scene_card` |
| prose | `PROSE-02` | `prose` |
| continuity | `DELTA-02` | `continuity_delta` |

The Review View includes:

```text
complete active candidate
exact generator Context snapshot payload
candidate and Context hashes
artifact-specific Review rules
private extensions only where required
prior Review for revised candidate
```

Review output:

```text
summary
issues
```

The Review never:

```text
returns a corrected candidate
changes checkpoint files
allocates IDs
changes source generation
modifies Run counters
chooses publication
```

---

## 12. Common revision contract

| family | revision stage | owner retained | response |
|---|---|---|---|
| Scene card | `SC-REV` | `SC-01` | complete Scene-card content candidate |
| prose | `PROSE-REV` | `PROSE-01` | complete prose body |
| continuity | `DELTA-REV` | `DELTA-01` | complete candidate continuity delta |

Inputs:

```text
complete active candidate
complete saved Review
exact generator Context payload
next revision-round number
whole-replacement rules
```

Forbidden revision responses:

```text
JSON Patch
merge patch
diff
edit instructions
only changed fields
references to unchanged text
new source generation
new Scene target
```

A structurally invalid revision does not create a new version directory.

---

## 13. Revised-version manifest

For a successful revision:

```text
candidate_version = prior candidate_version + 1
revision_rounds_used = prior revision_rounds_used + 1
candidate_status = candidate_valid
review_path = null
review_sha256 = null
next_stage = family Review stage
last_call_id = accepted revision Call ID
```

The new Candidate manifest retains the family owner operation and processor.

The new manifest `input_snapshot_sha256` is the Revision Context snapshot hash. That snapshot references the original generator Context.

---

## 14. Common Review routing

### 14.1 No issues

```text
review.issue_counts.total = 0
```

Result:

```text
candidate_status = ready_for_adoption
residual_issues_path = null
next_stage = family checkpoint stage
```

### 14.2 Issues and revision remains

```text
review.issue_counts.total > 0
revision_rounds_used < max_revision_rounds
```

Result:

```text
candidate_status = revision_required
next_stage = family revision stage
```

### 14.3 Issues and revision exhausted

```text
review.issue_counts.total > 0
revision_rounds_used >= max_revision_rounds
```

Code:

1. marks the version `exhausted`;
2. appends one residual Issue record per normalized Issue;
3. validates residual durability;
4. marks the version `ready_for_adoption`;
5. routes to the family checkpoint stage.

Only semantic issues use this path.

### 14.4 Zero revision rounds

When `max_revision_rounds=0`:

- the initial family candidate is reviewed once;
- semantic issues become residual;
- the revision stage is skipped;
- the checkpoint stage still performs complete mechanical validation.

---

# Part I: Scene-card pipeline

## 15. SC-01 — Generate Scene-card content

### 15.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `scene_card` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `scene_planner_builder` |
| logical owner | `SC-01` |
| target ID | Scene ID |
| response Schema | Scene-card content candidate |
| next stage | `SC-02` |

### 15.2 Authoritative inputs

```text
adopted Chapter design
exact target Scene-function entry
current HEAD Generation/Canon/Knowledge/State
adopted parent Volume design
adopted Series map
adopted Brief and Initial design
immediately previous safe handoff when present
Effective Editorial profile
Scene-card contract rules
```

The Scene planner receives a private Planner Author view and may see selected author truth needed to plan withholding.

The Scene-card output contract forbids that private truth.

### 15.3 Output

```text
runtime/candidates/scenes/vNN/cNNN/sNNN/scene-card/v0001/scene-card.json
runtime/candidates/scenes/vNN/cNNN/sNNN/scene-card/v0001/candidate-manifest.json
```

### 15.4 Mechanical validation

In addition to exact Schema:

```text
POV matches Chapter Scene-function target
required cast is included
all participant IDs resolve and are not retired
Location and World references resolve
Temporal rules resolve
time-relation matrix
required beats preserve Chapter order and meaning
Relationship targets resolve and are feasible
Thread targets use valid operation results from current State
Knowledge target transitions are valid from explicit/implicit current State
Ending targets are parent-plan compatible
Canon-metadata targets use permitted paths/operations
new-item policy type/count/scope constraints
max_items <= Effective-config max_new_items_per_scene
no secret author truth
no code-owned Scene metadata
```

Code obtains current Thread and Knowledge start values separately. An LLM copy is not part of the SC-01 Schema.

### 15.5 Success state

Candidate manifest:

```text
candidate_status = candidate_valid
next_stage = SC-02
```

Run state:

```text
last_completed_stage = SC-01
next_stage = SC-02
active_candidate_manifest_path =
  .../scene-card/v0001/candidate-manifest.json
scene_phase = SCENE_NOT_STARTED
```

---

## 16. SC-02 — Review Scene-card content

### 16.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_review` |
| operation key | `scene_card` |
| artifact class | `audit` |
| Context builder | `review_builder` |
| reviewed role | `scene_card` |
| next stage | routing result |

### 16.2 Required Review coverage

```text
Chapter Scene-function preservation
POV and participant feasibility
Location and time feasibility
required-beat completeness
emotional-change clarity
Relationship-change feasibility
Thread operation validity
Knowledge transition and disclosure validity
Ending-target safety
Canon-metadata change necessity
new-item policy necessity and bounds
forbidden-disclosure risk
absence of author-truth leakage
```

### 16.3 Output

```text
active Scene-card version/review.json
```

Routing follows Section 14.

The reviewer may identify cross-artifact context in the Issue location, but the suggested correction must be expressible as a replacement Scene-card candidate. It must not request a parent Chapter-plan rewrite inside this pipeline.

---

## 17. SC-REV — Replace Scene-card content

### 17.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_revise` |
| operation key | `scene_card` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `revision_builder` |
| owner retained | `SC-01` |
| response Schema | complete Scene-card content candidate |
| next stage | `SC-02` |

### 17.2 Restrictions

Revision may not change:

```text
Scene target coordinates
parent Chapter Scene-function identity
source generation
adopted persistent IDs to unknown IDs
configured maximum new-item count
```

It may replace every candidate field required to resolve Review issues.

---

## 18. SC-CHK — Freeze Scene card

### 18.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `checkpoint` plus separate `audit` |
| LLM call | none |
| source | active ready Scene-card candidate |
| next stage | `PROSE-01` |

### 18.2 Preconditions

```text
Run-state next_stage = SC-CHK
scene_phase = SCENE_NOT_STARTED
active Scene-card candidate is ready_for_adoption
candidate and Review hashes validate
source generation still equals HEAD
Chapter-design path/hash unchanged
target Scene has no adopted artifact
checkpoint path is absent or validly resumable
```

### 18.3 Frozen-card construction

Code:

1. revalidates the SC candidate;
2. injects Scene ID and coordinates;
3. injects source Generation path/hash identity;
4. injects Chapter-design path/hash;
5. injects accepted candidate hash;
6. reads exact current Thread start status/progress;
7. reads exact explicit or implicit Knowledge start statuses;
8. derives safe forbidden-disclosure records;
9. derives deterministic `allowed_update_targets`;
10. injects Effective-config length guidance;
11. copies `chapter_completion_role`;
12. writes code-owned timestamp;
13. validates the complete frozen Scene-card Schema;
14. canonicalizes and hashes the card.

### 18.4 Checkpoint write

Canonical path:

```text
runtime/checkpoints/scenes/vNN/cNNN/sNNN/scene-card.json
```

Code creates or atomically updates:

```text
runtime/checkpoints/scenes/vNN/cNNN/sNNN/checkpoint-manifest.json
```

Manifest phase:

```text
CARD_ACCEPTED
```

The manifest records the exact Scene-card Candidate manifest path and frozen-card hash.

### 18.5 Postconditions

Run state becomes:

```text
last_completed_stage = SC-CHK
next_stage = PROSE-01
scene_phase = CARD_ACCEPTED
active_candidate_manifest_path = null
active_checkpoint_manifest_path =
  runtime/checkpoints/scenes/vNN/cNNN/sNNN/checkpoint-manifest.json
```

The frozen Scene card is immutable after this stage.

---

# Part II: Prose pipeline

## 19. PROSE-01 — Generate prose

### 19.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `prose` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `prose_writer_builder` |
| logical owner | `PROSE-01` |
| target ID | Scene ID |
| response format | canonicalizable narrative Markdown text |
| response Schema version | null |
| next stage | `PROSE-02` |

### 19.2 Preconditions

```text
scene_phase = CARD_ACCEPTED
valid Checkpoint manifest phase = CARD_ACCEPTED
frozen Scene card exists and hashes
source generation still equals HEAD
no checkpoint prose exists
```

### 19.3 Authoritative inputs

```text
Writer-safe frozen Scene-card projection
Writer View
safe previous handoff
Effective Editorial profile
prose output-format rules
```

The prose generator does not receive:

```text
Thread author_truth
Thread resolution_condition
Knowledge author_truth
Ending source text
raw Review issues
allowed-update target mechanics
future Scene detail
Publishing profile
```

### 19.4 Output

```text
runtime/candidates/scenes/vNN/cNNN/sNNN/prose/v0001/prose.md
runtime/candidates/scenes/vNN/cNNN/sNNN/prose/v0001/candidate-manifest.json
```

### 19.5 Structural validation

Code validates and canonicalizes:

```text
valid UTF-8
NFC
permitted prose-only Markdown
no front matter, heading, list, table, code, HTML, link, or metadata
at least one non-whitespace code point
no explicit persistent-ID tokens in narrative text
canonical line endings and trailing LF
```

Length guidance is not a hard structural limit.

The Candidate manifest hash identifies canonical candidate prose bytes.

### 19.6 Success state

Run state:

```text
last_completed_stage = PROSE-01
next_stage = PROSE-02
active_candidate_manifest_path =
  .../prose/v0001/candidate-manifest.json
scene_phase = CARD_ACCEPTED
```

---

## 20. PROSE-02 — Review prose

### 20.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_review` |
| operation key | `prose` |
| artifact class | `audit` |
| Context builder | `review_builder` |
| reviewed role | `prose` |
| next stage | routing result |

### 20.2 Review inputs

```text
complete canonical prose candidate
exact Writer Context used for generation
private disclosure-check extension
frozen Scene-card identity
prior Review when revised
prose Review rules
```

The private reviewer may see minimum hidden facts required to detect forbidden disclosure. That private extension is never passed to PROSE-REV as writing content except through safe Issue descriptions and the original Writer Context.

### 20.3 Required Review coverage

```text
POV consistency
Scene purpose
required beats
emotional-change target
Relationship targets
Thread targets
Character Knowledge targets
Reader disclosures
Ending targets
Location and time consistency
forbidden disclosures
immutable-fact consistency
speech anchors and characterization
prose-only format
unsupported persistent detail
editorial profile
```

### 20.4 Output

```text
active prose version/review.json
```

Routing follows Section 14.

A Review Issue must be actionable through prose replacement. It cannot request a frozen Scene-card edit as the normal route.

---

## 21. PROSE-REV — Replace prose

### 21.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_revise` |
| operation key | `prose` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `revision_builder` |
| owner retained | `PROSE-01` |
| response format | complete replacement prose |
| response Schema version | null |
| next stage | `PROSE-02` |

### 21.2 Inputs

```text
complete current prose
complete saved Review
exact Writer Context
safe replacement rules
revision round
```

The revision response contains only the complete narrative body.

Forbidden:

```text
diff
editor notes
explanation
quoted old text plus instructions
only changed paragraphs
metadata
```

### 21.3 Validation

The replacement undergoes the same canonicalization and structural checks as PROSE-01.

The frozen Scene card does not change.

---

## 22. PROSE-CHK — Freeze prose

### 22.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `checkpoint` plus separate `audit` |
| LLM call | none |
| source | active ready prose candidate |
| next stage | `DELTA-01` |

### 22.2 Preconditions

```text
scene_phase = CARD_ACCEPTED
Checkpoint phase = CARD_ACCEPTED
frozen Scene-card hash unchanged
source generation still equals HEAD
active prose candidate is ready_for_adoption
candidate and Review hashes validate
checkpoint prose path does not yet exist
```

### 22.3 Behavior

Code:

1. revalidates canonical prose format;
2. calculates prose SHA-256;
3. calculates Unicode code-point `character_count` excluding final LF;
4. writes exact canonical bytes to checkpoint `prose.md`;
5. updates Checkpoint manifest with prose candidate manifest path, prose path/hash, and:
   ```text
   phase = PROSE_FROZEN
   ```
6. writes an operation audit with the character count.

### 22.4 Postconditions

Run state becomes:

```text
last_completed_stage = PROSE-CHK
next_stage = DELTA-01
scene_phase = PROSE_FROZEN
active_candidate_manifest_path = null
active_checkpoint_manifest_path unchanged
```

The frozen prose is immutable after this stage.

A later Delta or commit stage may not rewrite, normalize differently, or append metadata to it.

---

# Part III: Continuity pipeline

## 23. DELTA-01 — Extract continuity candidate

### 23.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_extract` |
| operation key | `continuity_delta` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `continuity_builder` |
| logical owner | `DELTA-01` |
| target ID | Scene ID |
| response Schema | validated-candidate continuity root before code injection |
| next stage | `DELTA-02` |

### 23.2 Preconditions

```text
scene_phase = PROSE_FROZEN
Checkpoint phase = PROSE_FROZEN
frozen Scene card and prose exist and hash
source generation still equals HEAD
no checkpoint continuity delta exists
```

### 23.3 Authoritative inputs

```text
exact frozen Scene card
exact frozen canonical prose
exact allowed-target baselines
relevant writer-safe record catalog
selected safe Knowledge labels and statuses
selected safe Thread descriptions and statuses
selected Ending criteria descriptions
new-item policy
continuity contract rules
```

The Continuity View contains no hidden author truth.

### 23.4 LLM output ownership

The LLM may propose:

```text
existing item after-values
new record local keys and candidate fields
new Knowledge-item local keys and safe fields
Knowledge transitions
Thread operations
Ending evidence relations
time update
literal Evidence quotes
handoff_summary
```

The LLM must not provide:

```text
new persistent IDs
Evidence IDs
Commit/Generation IDs
offsets
hashes
timestamps
code-owned source metadata
```

### 23.5 Output

```text
runtime/candidates/scenes/vNN/cNNN/sNNN/continuity/v0001/continuity-delta.json
runtime/candidates/scenes/vNN/cNNN/sNNN/continuity/v0001/candidate-manifest.json
```

### 23.6 Code normalization before candidate write

After exact response Schema validation, code:

1. injects `schema_version`;
2. injects `delta_status=candidate`;
3. injects `scene_id`;
4. injects/verifies exact HEAD `before` values;
5. normalizes array ordering;
6. validates all local-key syntax and uniqueness;
7. validates all adopted references;
8. validates all Scene-card authorizations;
9. validates all transition matrices;
10. validates Evidence quotes against frozen prose;
11. validates `handoff_summary`;
12. writes only the normalized validated candidate.

The saved candidate therefore matches the checkpoint candidate-delta Schema from `evidence_and_updates.md`.

### 23.7 Mechanical validation

Code verifies at least:

```text
candidate root exact
Scene ID and source checkpoint
existing target/field/operation authorization
HEAD before-value equality
no-op rejection
Character and Relationship State field types
scope/lifecycle/related_ids rules
new-item policy type/count/scope
new local-key uniqueness and reference graph
new Character/Relationship/Thread State initialization
Knowledge-item fact uniqueness
Knowledge transition matrix
Thread operation matrix
required Major Thread retirement rejection
Ending target/relation authorization
time-update target values
Evidence quote unique occurrence
no code-owned ID/hash/offset field
handoff summary contains no future plan or author truth
```

A failure consumes response-structure/conditional-rule retry budget.

### 23.8 Success state

Run state:

```text
last_completed_stage = DELTA-01
next_stage = DELTA-02
active_candidate_manifest_path =
  .../continuity/v0001/candidate-manifest.json
scene_phase = PROSE_FROZEN
```

---

## 24. DELTA-02 — Review continuity candidate

### 24.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_review` |
| operation key | `continuity_delta` |
| artifact class | `audit` |
| Context builder | `review_builder` |
| reviewed role | `continuity_delta` |
| next stage | routing result |

### 24.2 Review inputs

```text
complete normalized continuity candidate
exact Continuity Context
frozen Scene-card/prose hashes
private author extension only to detect contradiction
prior Review when revised
continuity Review rules
```

The private reviewer may see selected hidden truth to detect a false canonical proposal. The candidate and revision generator remain limited to safe Continuity Context.

### 24.3 Required Review coverage

```text
all meaningful persistent changes captured
no unsupported persistent change
Evidence quote actually supports the proposed change
new records are persistence-worthy
new record fields do not overclaim beyond prose
Knowledge facts and transitions are safe and correct
Thread operation meaning matches prose
Ending evidence is materially related
time interpretation is semantically sound
handoff summary reflects only established prose
no author-truth leakage
no incidental detail incorrectly promoted
```

### 24.4 Output

```text
active continuity version/review.json
```

Routing follows Section 14.

---

## 25. DELTA-REV — Replace continuity candidate

### 25.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_revise` |
| operation key | `continuity_delta` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `revision_builder` |
| owner retained | `DELTA-01` |
| response Schema | complete continuity response candidate |
| next stage | `DELTA-02` |

### 25.2 Inputs

```text
complete current normalized candidate
complete saved Review
exact Continuity Context
replacement rules
revision round
```

The LLM returns one complete candidate response without code-owned fields.

Code then repeats the DELTA-01 normalization and validation pipeline before writing the new version.

### 25.3 Immutable upstream artifacts

DELTA-REV may not change:

```text
frozen Scene card
frozen prose
source generation
allowed-update targets
new-item policy
Scene ID
```

If a Review Issue cannot be resolved without changing frozen prose or Scene card, it remains a residual semantic issue or triggers explicit checkpoint invalidation under Section 38. Code never edits an upstream checkpoint inside DELTA-REV.

---

## 26. DELTA-CHK — Freeze validated candidate delta

### 26.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `checkpoint` plus separate `audit` |
| LLM call | none |
| source | active ready continuity candidate |
| next stage | `COMMIT-01` |

### 26.2 Preconditions

```text
scene_phase = PROSE_FROZEN
Checkpoint phase = PROSE_FROZEN
frozen Scene-card and prose hashes unchanged
source generation still equals HEAD
active continuity candidate is ready_for_adoption
candidate and Review hashes validate
checkpoint continuity-delta path does not yet exist
```

### 26.3 Final pre-checkpoint validation

Code repeats every mechanical DELTA validation against:

```text
current HEAD
frozen Scene card
frozen prose
current Canon/Knowledge/Story state
Effective new-item limit
candidate Review/residual status
```

This catches corruption or source changes after DELTA Review.

No persistent IDs, Evidence IDs, offsets, or hashes are allocated.

### 26.4 Checkpoint write

Code writes the exact normalized candidate to:

```text
runtime/checkpoints/scenes/vNN/cNNN/sNNN/continuity-delta.json
```

It atomically updates the Checkpoint manifest:

```text
continuity_candidate_manifest_path = active candidate manifest
continuity_delta_path = checkpoint candidate delta
continuity_delta_sha256 = exact hash
phase = DELTA_ACCEPTED
```

### 26.5 Postconditions

Run state becomes:

```text
last_completed_stage = DELTA-CHK
next_stage = COMMIT-01
scene_phase = DELTA_ACCEPTED
active_candidate_manifest_path = null
active_checkpoint_manifest_path unchanged
```

The checkpoint now contains the complete commit input set:

```text
scene-card.json
prose.md
continuity-delta.json
checkpoint-manifest.json
```

---

# Part IV: Checkpoint rules

## 27. Checkpoint phase matrix

| phase | required files | next generation family |
|---|---|---|
| `CARD_ACCEPTED` | Scene card, Checkpoint manifest | prose |
| `PROSE_FROZEN` | Scene card, prose, Checkpoint manifest | continuity |
| `DELTA_ACCEPTED` | Scene card, prose, candidate delta, Checkpoint manifest | commit |

`COMMIT_PREPARED` is created by the commit pipeline, not this document.

### 27.1 Phase monotonicity

Normal progression:

```text
CARD_ACCEPTED
→ PROSE_FROZEN
→ DELTA_ACCEPTED
```

No in-place backward phase transition is permitted.

### 27.2 File immutability

Once the phase requiring a file is reached:

| file | immutable from |
|---|---|
| `scene-card.json` | `CARD_ACCEPTED` |
| `prose.md` | `PROSE_FROZEN` |
| `continuity-delta.json` | `DELTA_ACCEPTED` |

A changed byte requires invalidating the checkpoint and restarting from the appropriate source stage. Code never overwrites a frozen file.

### 27.3 Manifest update order

For each checkpoint stage:

1. write the new checkpoint artifact through a temporary same-directory file;
2. `fsync` and atomically place it;
3. validate and hash the final bytes;
4. atomically replace the Checkpoint manifest with the new phase;
5. atomically update Run state.

A crash between artifact placement and manifest replacement leaves an unreferenced checkpoint file. Startup validates or quarantines it; it is not trusted automatically.

---

## 28. Candidate and checkpoint relationship

A checkpoint records the exact Candidate manifest path used to freeze each artifact.

The following must remain reconstructible:

```text
Scene-card candidate path/hash and Review
prose candidate path/hash and Review
continuity candidate path/hash and Review
frozen artifact path/hash
source generation
Effective-config hash
```

Candidate artifacts remain immutable audit/resume history after checkpointing.

The checkpoint file, not the old candidate file, is the source for the next family.

---

## 29. Residual issues and checkpoints

When semantic issues remain after revision exhaustion:

- one residual Issue record is written per Issue;
- the checkpoint stage may freeze the mechanically valid candidate;
- the Checkpoint manifest does not embed Issue text;
- the Candidate manifest points to the residual issue audit path;
- downstream Context Builders receive only applicable safe residual constraints.

For prose:

- the frozen prose bytes remain the reviewed text;
- later Delta extraction may only adopt changes actually evidenced in that text.

For Scene card:

- required targets remain semantic targets;
- later code never fabricates prose or continuity changes.

For Delta:

- only mechanically and evidentially valid changes survive checkpoint validation.

---

## 30. Upstream artifact immutability

### 30.1 During prose stages

The following are immutable:

```text
source generation
Chapter design
frozen Scene card
previous handoff source
Editorial profile
```

A changed input makes the prose candidate stale.

### 30.2 During continuity stages

The following are immutable:

```text
source generation
frozen Scene card
frozen prose
allowed-update targets
new-item policy
```

A changed input makes the continuity candidate stale.

### 30.3 No silent repair

The pipeline never:

```text
changes the Scene card to fit prose
changes prose to fit Delta
changes HEAD to fit a candidate
changes allowed targets after prose
adds an Evidence quote not present in prose
```

---

# Part V: Resume and recovery

## 31. Candidate resume

A candidate version is reusable only when:

```text
Candidate manifest validates
candidate path exists
candidate hash matches
Context snapshot hash matches
source generation and upstream hashes match
last_structurally_valid = true
candidate is not superseded
next_stage is valid
```

Raw LLM-call audits are never candidate sources.

If a candidate version is valid and Run state is behind, startup reconciles Run state to its durable next stage.

---

## 32. Review resume

If `review.json` exists and matches the active Candidate manifest:

- do not call the reviewer again;
- recompute routing from saved Issue count and revision counters;
- write any missing residual Issue records only after duplicate-safe validation;
- update Run state.

If Review is absent or mismatched, run the family Review stage.

An older version's Review never applies to the active candidate.

---

## 33. Revision resume

If the next version directory contains a complete valid candidate and Candidate manifest:

- activate it;
- route to the family Review stage.

If the version directory is partial:

- quarantine it;
- do not reconstruct the candidate from raw audit output;
- repeat the revision call only when no durable valid candidate exists and budget permits.

The prior reviewed version is never overwritten.

---

## 34. Checkpoint resume

### 34.1 Valid CARD_ACCEPTED

Resume at:

```text
PROSE-01
```

unless a valid active prose candidate/Review indicates a later prose stage.

### 34.2 Valid PROSE_FROZEN

Resume at:

```text
DELTA-01
```

unless a valid active continuity candidate/Review indicates a later Delta stage.

### 34.3 Valid DELTA_ACCEPTED

Resume at:

```text
COMMIT-01
```

### 34.4 Run-state reconciliation

When the Checkpoint manifest is valid but Run state is behind:

- Checkpoint manifest and frozen artifact hashes are authoritative;
- Run state is advanced to the phase's postcondition;
- no LLM call is repeated.

When Run state claims a later phase than the valid Checkpoint manifest, startup stops mechanically unless an adopted Scene commit proves that the checkpoint was already consumed.

---

## 35. Orphan checkpoint files

Examples:

```text
prose.md exists but Checkpoint phase = CARD_ACCEPTED
continuity-delta.json exists but phase = PROSE_FROZEN
```

Startup:

1. verifies the unreferenced file is not part of an adopted Scene;
2. moves it to Runtime orphan quarantine;
3. retains the valid earlier checkpoint phase;
4. resumes from the stage following that phase.

It never promotes an unreferenced file solely because its bytes parse.

---

## 36. Adopted Scene found during resume

If the target Scene artifact and resulting HEAD commit already validate:

- the scene commit is adopted;
- leftover checkpoint is cleanup residue;
- startup follows the commit pipeline's Run-state reconciliation;
- no SC/PROSE/DELTA stage is repeated.

This pipeline never overwrites an adopted Scene artifact.

---

## 37. Stale candidate handling

A candidate becomes stale when any semantic source changes.

### 37.1 Scene-card candidate staleness

```text
HEAD generation/hash
Chapter-design hash
target Scene-function entry
previous handoff hash
Brief/Initial-design/parent-plan hash
semantic Effective config
prompt/Schema/Context-builder version
```

### 37.2 Prose candidate staleness

```text
frozen Scene-card hash
source generation/hash
safe handoff hash
Editorial profile
prompt/Context-builder version
```

### 37.3 Continuity candidate staleness

```text
frozen Scene-card hash
frozen prose hash
source generation/hash
new-item configuration
prompt/Schema/Context-builder version
```

A stale uncheckpointed candidate is frozen as history and regenerated in the next version directory by its owner stage.

Staleness regeneration is not a semantic revision and does not increment `revision_rounds_used`.

---

## 38. Full checkpoint invalidation

A full invalidation is required when:

```text
source generation no longer equals HEAD
Chapter design or target Scene-function changed
frozen Scene-card bytes/hash are invalid
frozen prose bytes/hash are invalid
Checkpoint manifest source/hash graph is inconsistent
an upstream defect cannot be resolved by the current candidate family
```

Under the workspace lock, code:

1. writes an invalidation operation audit;
2. moves the entire checkpoint directory to Runtime orphan quarantine;
3. clears `active_checkpoint_manifest_path`;
4. clears `active_candidate_manifest_path`;
5. leaves all candidate version directories immutable;
6. sets:
   ```text
   scene_phase = SCENE_NOT_STARTED
   last_completed_stage = preceding durable planning/commit stage
   next_stage = SC-01
   ```
7. rebuilds from current valid HEAD and adopted Chapter design.

Code does not partially retain frozen prose or Delta from an invalidated checkpoint.

An upstream semantic defect that cannot be expressed as a current-family replacement may require `manual_intervention` rather than automatic invalidation. Automatic invalidation is permitted only when the affected authoritative input has actually changed or failed mechanical validation.

---

# Part VI: Stage transitions

## 39. Scene-card transitions

| current stage | condition | next stage |
|---|---|---|
| `SC-01` | valid candidate | `SC-02` |
| `SC-02` | no issues | `SC-CHK` |
| `SC-02` | issues, revision remains | `SC-REV` |
| `SC-02` | issues, revision exhausted | `SC-CHK` |
| `SC-REV` | valid complete replacement | `SC-02` |
| `SC-CHK` | frozen card valid | `PROSE-01` |

---

## 40. Prose transitions

| current stage | condition | next stage |
|---|---|---|
| `PROSE-01` | valid prose candidate | `PROSE-02` |
| `PROSE-02` | no issues | `PROSE-CHK` |
| `PROSE-02` | issues, revision remains | `PROSE-REV` |
| `PROSE-02` | issues, revision exhausted | `PROSE-CHK` |
| `PROSE-REV` | valid complete replacement | `PROSE-02` |
| `PROSE-CHK` | frozen prose valid | `DELTA-01` |

---

## 41. Continuity transitions

| current stage | condition | next stage |
|---|---|---|
| `DELTA-01` | valid candidate | `DELTA-02` |
| `DELTA-02` | no issues | `DELTA-CHK` |
| `DELTA-02` | issues, revision remains | `DELTA-REV` |
| `DELTA-02` | issues, revision exhausted | `DELTA-CHK` |
| `DELTA-REV` | valid complete replacement | `DELTA-02` |
| `DELTA-CHK` | checkpoint candidate valid | `COMMIT-01` |

No other normal transition is permitted.

---

## 42. Scene-phase transitions

| stage completion | resulting `scene_phase` |
|---|---|
| scene entry / generation / Review / revision before SC-CHK | `SCENE_NOT_STARTED` |
| `SC-CHK` | `CARD_ACCEPTED` |
| prose generation / Review / revision | `CARD_ACCEPTED` |
| `PROSE-CHK` | `PROSE_FROZEN` |
| Delta generation / Review / revision | `PROSE_FROZEN` |
| `DELTA-CHK` | `DELTA_ACCEPTED` |

`COMMIT_PREPARED` and `SCENE_COMMITTED` are set by the commit pipeline.

---

## 43. Error transitions

| failure | result |
|---|---|
| provider transport retry exhausted | Run failed; no automatic next stage |
| response-structure retry exhausted | Run failed; no automatic next stage |
| valid semantic Review issues | route by revision budget |
| mechanical candidate invalid | candidate not written |
| checkpoint validation fails | Run failed or full checkpoint invalidation; no frozen overwrite |
| source generation changes | full checkpoint invalidation and restart from SC-01 |
| budget preflight fails | Run stopped with `budget_exhausted` |
| audit storage maximum reached | Run stopped before next LLM call |
| explicit safe-boundary user stop | Run stopped with `user_stop` |
| unresolvable upstream semantic defect | Run stopped with `manual_intervention` |

A user stop does not interrupt an atomic candidate, checkpoint artifact, Checkpoint-manifest, or Run-state replacement.

---

## 44. Stage completion rule

An LLM stage is complete only when:

```text
its complete candidate or Review is durable
its canonical hash is known
its Candidate manifest is durable
all structural checks pass
Run state records last_completed_stage and next_stage
```

A checkpoint stage is complete only when:

```text
the frozen artifact is durable
its hash validates
the Checkpoint manifest records the new phase
Run state records the matching scene phase and next stage
```

Receiving a provider response is not stage completion.

---

## 45. Resume-source matrix

| stage | authoritative resume source |
|---|---|
| `SC-01` | Chapter design, current HEAD, active Scene-card Candidate manifest |
| `SC-02` | active Scene-card candidate and matching Review |
| `SC-REV` | active reviewed Scene-card version and Revision Context |
| `SC-CHK` | active ready Scene-card version and current HEAD |
| `PROSE-01` | CARD_ACCEPTED Checkpoint manifest and active prose Candidate manifest |
| `PROSE-02` | active prose candidate and matching Review |
| `PROSE-REV` | active reviewed prose version and Writer Revision Context |
| `PROSE-CHK` | active ready prose version and frozen Scene card |
| `DELTA-01` | PROSE_FROZEN Checkpoint manifest and active continuity Candidate manifest |
| `DELTA-02` | active continuity candidate and matching Review |
| `DELTA-REV` | active reviewed continuity version and Continuity Revision Context |
| `DELTA-CHK` | active ready continuity version, frozen card/prose, current HEAD |
| `COMMIT-01` | DELTA_ACCEPTED Checkpoint manifest |

Raw LLM-call audit files are never resume sources.

---

# Part VII: Audit and invariants

## 46. Required operation audits

Code writes unique operation-audit records for at least:

```text
scene target selected
Scene-planner Context built
Scene-card candidate version activated
Scene-card Review routing
Scene card frozen
Writer Context built
prose candidate version activated
prose Review routing
prose frozen with character count
Continuity Context built
continuity candidate version activated
continuity Review routing
candidate before-values injected
Evidence quotes validated
Delta frozen
residual issues recorded
candidate declared stale
checkpoint invalidated
orphan checkpoint file quarantined
Run state reconciled from Checkpoint manifest
```

Audit records may contain paths, hashes, IDs, counts, and status.

They must not expose credentials, raw hidden truth in normal messages, or publication content.

---

## 47. Cross-artifact invariants

Before COMMIT-01, code verifies:

```text
Scene ID matches Run state, Chapter plan, and checkpoint path
Checkpoint source generation equals current HEAD
Checkpoint source Generation-manifest hash validates
frozen Scene-card hash matches Checkpoint manifest
frozen prose hash matches Checkpoint manifest
frozen candidate-delta hash matches Checkpoint manifest
Scene-card Chapter-design hash validates
Scene-card source generation equals Checkpoint source generation
prose was generated/revised from the frozen Scene-card Context
continuity was generated/revised from the frozen card and prose
candidate delta Scene ID matches frozen Scene card
every delta existing target is authorized
every before value equals current HEAD
every Evidence quote occurs exactly once in frozen prose
every new proposal satisfies new-item policy
no persistent new ID, Evidence ID, offset, or hash exists in candidate delta
Run scene_phase = DELTA_ACCEPTED
Run next_stage = COMMIT-01
```

---

## 48. Forbidden implementation shortcuts

Forbidden:

```text
one mutable candidate directory without versioning
overwriting Review history
selecting candidates by modification time
using raw LLM audit output as candidate recovery
giving Author View to prose generation
giving hidden author truth to continuity extraction
letting SC-01 emit source metadata or allowed-update targets
letting PROSE-REV change the frozen Scene card
letting DELTA-REV change frozen prose
allocating persistent IDs during DELTA
creating Evidence offsets or hashes during DELTA
accepting Evidence text that is not a unique literal prose substring
treating Scene-card required=true as permission to fabricate an update
using prose length as an unconditional hard rejection
overwriting a frozen checkpoint file
promoting an unreferenced checkpoint file by inference
continuing after HEAD changed
using artifact class "review candidate"
using artifact class "candidate/checkpoint"
```

---

## 49. Mechanical acceptance conditions

An implementation of this pipeline is acceptable only when tests demonstrate:

```text
exact stage IDs and processors
canonical artifact classes
Scene target and coordinate validation
source-generation equality through DELTA-CHK
versioned Scene-card candidates
versioned prose candidates
versioned continuity candidates
immutable superseded versions and Reviews
logical owner retained across revision
Candidate-manifest-only resume
SC-01 exact candidate validation
SC Review semantic routing
SC-REV whole replacement
SC-CHK code-owned field injection
safe forbidden-disclosure derivation
deterministic allowed-update-target derivation
CARD_ACCEPTED checkpoint
Writer View author-truth exclusion
prose-only Markdown validation
prose canonicalization and hash
prose character-count calculation
PROSE Review and whole replacement
frozen prose immutability
PROSE_FROZEN checkpoint
DELTA-01 uses llm_extract
candidate before-value code injection
Scene-card authorization enforcement
new-item count/type/scope enforcement
Knowledge and Thread transition validation
Evidence quote unique-occurrence validation
no code-owned ID/hash/offset injection
DELTA Review private contradiction extension
DELTA-REV whole replacement
DELTA-CHK repeats mechanical validation
DELTA_ACCEPTED checkpoint
zero revision-round behavior
residual Issue recording
mechanical defect never frozen by exhaustion
checkpoint phase monotonicity
orphan checkpoint-file quarantine
checkpoint resume without duplicate LLM call
full invalidation on source-generation mismatch
adopted Scene detection during resume
Run-state phase reconciliation
cross-artifact hash invariants
unknown transition rejection
unknown-field rejection
canonical hash stability
```
