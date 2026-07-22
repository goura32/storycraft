# Pipeline contracts: Planning

This document is the normative pipeline contract for adopting the Series map, each Volume design, and each Chapter design:

```text
SERIES-01
SERIES-02
SERIES-REV
SERIES-ID

VOL-01
VOL-02
VOL-REV
VOL-ID

CH-01
CH-02
CH-REV
CH-ID
```

Planning data contracts are defined by [`../data/planning_artifacts.md`](../data/planning_artifacts.md). The adopted Brief and Initial design are defined by [`../data/brief_and_initial.md`](../data/brief_and_initial.md). Runtime candidate manifests, Run state, pointers, counters, and atomic-write rules are defined by [`../ledger/runtime_records.md`](../ledger/runtime_records.md). Context views are defined by [`../../context_contracts.md`](../../context_contracts.md). Retry, budget, and provider rules are defined by [`../../configuration_contracts.md`](../../configuration_contracts.md). Review and residual-issue records are defined by [`../data/review_and_audit.md`](../data/review_and_audit.md).

Every JSON object written by this pipeline uses `additionalProperties: false`.

---

## 1. Pipeline purpose

Planning converts the adopted Brief, Initial design, current generation, and earlier adopted plans into immutable intended-structure artifacts.

The pipeline guarantees:

```text
one Series map for the story
one Volume design for every planned Volume
one Chapter design for every planned Chapter
parent-plan and source-generation hashes
complete semantic Review or revision-exhaustion handling
mechanical validation before Review and again before adoption
immutable adopted planning files
deterministic target selection
no hidden author truth copied into writer-facing plan fields
```

Planning artifacts describe intent. They never override adopted Canon, Story state, Evidence, or prose.

The pipeline must not:

```text
rewrite an adopted plan after scenes begin
select a candidate by modification time
use raw LLM audit output as resume state
allocate story-record IDs
modify Canon or Story state
publish content
generate prose
treat semantic Review issues as structural response failures
adopt a mechanically invalid plan because revision budget is exhausted
```

---

## 2. Stage families

| family | generation | review | revision | adoption |
|---|---|---|---|---|
| Series | `SERIES-01` | `SERIES-02` | `SERIES-REV` | `SERIES-ID` |
| Volume | `VOL-01` | `VOL-02` | `VOL-REV` | `VOL-ID` |
| Chapter | `CH-01` | `CH-02` | `CH-REV` | `CH-ID` |

Processor types:

| stage kind | processor type |
|---|---|
| generation | `llm_generate` |
| review | `llm_review` |
| revision | `llm_revise` |
| adoption | `code` |

No planning stage uses `llm_extract`.

---

## 3. Artifact classes

Only canonical artifact-class values are used.

| artifact | class |
|---|---|
| unadopted Series/Volume/Chapter content | `candidate` |
| plan adoption staging file | `staged_internal` |
| staged plan-validation report | `staged_internal_validation` |
| final plan under `plans/` | `adopted` |
| Review, LLM-call, residual-issue, and operation records | `audit` |

Forbidden:

```text
review candidate
adopted/audit
plan/review
any slash-combined class
```

A candidate and its Review are separate artifacts with separate paths and hashes.

---

## 4. Planning target identity

### 4.1 Series target

```text
target_id = series
```

There is exactly one Series target.

### 4.2 Volume target

```text
target_id = vNN
```

Example:

```text
v04
```

The numeric value equals Run-state `current_volume_number`.

### 4.3 Chapter target

```text
target_id = vNN-cNNN
```

Example:

```text
v04-c003
```

The numeric values equal Run-state `current_volume_number` and `current_chapter_number`.

### 4.4 Target selection authority

Normal target selection is code-owned:

| entry point | target selection |
|---|---|
| after `INIT-ID` | Series |
| after `SERIES-ID` | Volume 1 |
| after `VOL-ID` | Chapter 1 of that Volume |
| after a completed nonfinal Chapter | next Chapter number from adopted Volume design |
| after `VH-ID` for a nonfinal Volume | next Volume number from adopted Series map |

Downstream scene/commit/handoff stages set Run state to the correct planning entry point. Planning stages do not infer progress by scanning filenames.

Before any planning call, code verifies Run-state target coordinates against parent adopted plans and the current Story-clock position.

---

## 5. Plan immutability and temporal scope

### 5.1 Series map

The Series map is adopted once after Genesis and before Volume planning.

Its source generation is:

```text
00000000
```

A normal run never regenerates it.

### 5.2 Volume design

A Volume design is adopted once:

- before the first Chapter design of that Volume;
- before any Scene of that Volume is adopted;
- using the current HEAD at the start of the Volume;
- using the preceding Volume handoff for Volume `>1`.

After the first Scene of the Volume is adopted, that Volume design is immutable.

### 5.3 Chapter design

A Chapter design is adopted once:

- before the first Scene card of that Chapter;
- using the current HEAD at the start of the Chapter;
- using the immediately preceding safe handoff when available.

After the first Scene of the Chapter is adopted, that Chapter design is immutable.

### 5.4 Later HEAD movement

An adopted plan remains valid as a historical intended plan when later Scene commits advance HEAD.

Source-generation equality is required:

```text
before candidate generation/reuse
before plan adoption
```

It is not required after plan adoption.

---

## 6. Candidate version directories

Every logical planning candidate uses immutable version directories.

### 6.1 Series paths

```text
runtime/candidates/planning/series-map/v0001/
  series-map.json
  review.json
  candidate-manifest.json
```

A revision creates `v0002`, then `v0003`, and so on.

### 6.2 Volume paths

```text
runtime/candidates/planning/volumes/v01/v0001/
  volume-design.json
  review.json
  candidate-manifest.json
```

### 6.3 Chapter paths

```text
runtime/candidates/planning/volumes/v01/chapters/c001/v0001/
  chapter-design.json
  review.json
  candidate-manifest.json
```

### 6.4 Version rules

- `v0001` is created by the generation owner stage.
- Each successful semantic revision creates the next complete version directory.
- A version directory is never overwritten or reused.
- `review.json` exists only after that exact version is reviewed.
- Older versions and their Reviews remain immutable.
- Run state points only to the active version's Candidate manifest.
- A downstream adoption stage reads the exact active version, never a filesystem “latest” result.

### 6.5 Logical owners

| logical candidate | owner operation | owner processor |
|---|---|---|
| Series map | `SERIES-01` | `llm_generate` |
| Volume design | `VOL-01` | `llm_generate` |
| Chapter design | `CH-01` | `llm_generate` |

A revised version retains the logical owner in its Candidate manifest. The actual revision call is recorded by:

```text
unique LLM-call audit role = revise
revision Context snapshot
candidate_version
revision_rounds_used
last_call_id
```

---

## 7. Common provider-call behavior

Every generation, Review, and revision stage follows the provider-call and retry rules in `configuration_contracts.md`.

Before a provider request, code validates:

```text
workspace lock
Run-state stage and target
Run/Effective-config compatibility
required source paths and hashes
source-generation equality
Context snapshot and token budget
provider credential availability
call/token/time/cost/audit-storage budget
candidate-version destination availability
```

For every provider HTTP attempt, code:

1. persists a new Call ID;
2. writes the unique redacted LLM-call audit;
3. applies transport timeout/retry classification;
4. persists usage and cost before semantic routing;
5. validates the successful response structurally.

A structurally invalid response never creates a candidate or Review artifact.

---

## 8. Common planning-candidate validation

Before a planning candidate is written, code validates:

```text
exact candidate root and child Schemas
unknown-field rejection
persistent-ID format
all IDs resolve in the source generation
all referenced records are not retired
parent-plan target preservation
target coordinates
enum and conditional rules
Thread status/progress/action matrices
Ending-criterion coverage rules
configured Publishing-profile rules
absence of code-owned metadata
absence of raw author truth in prohibited fields
canonical ordering
```

A failure is a response-structure or conditional-rule failure and may consume response-structure retries.

A mechanically invalid planning candidate is never sent to semantic Review.

---

## 9. Common Candidate-manifest lifecycle

### 9.1 New version initialization

```text
candidate_version = version directory number
candidate_status = initialized
candidate_path = null
candidate_sha256 = null
review_path = null
review_sha256 = null
last_structurally_valid = false
```

After one complete structurally valid candidate is durable:

```text
candidate_status = candidate_valid
candidate_path = operation-specific candidate path
candidate_sha256 = canonical candidate hash
last_structurally_valid = true
review_path = null
review_sha256 = null
last_call_id = accepted Call ID
next_stage = family Review stage
```

### 9.2 After Review

The Review stage writes `review.json`, then updates the active Candidate manifest:

```text
candidate_status = reviewed
review_path = exact path
review_sha256 = exact hash
```

Code then persists the routing state described in Section 13.

### 9.3 Ready for adoption

A planning candidate becomes `ready_for_adoption` only when:

```text
it remains structurally valid
its Review artifact matches its hash and candidate version
issues are empty
OR revision rounds are exhausted and residual issues are durable
source generation and parent plan remain unchanged
```

### 9.4 Superseded version

When a revised version becomes active:

- the earlier Candidate manifest is frozen;
- it is not marked ready for adoption;
- Run state moves to the new version only after its candidate and manifest are durable;
- its prior Review remains audit history.

---

## 10. Common Review contract

Each family Review stage uses `review_builder` and the generic Review Schema.

| family | review stage | reviewed artifact role |
|---|---|---|
| Series | `SERIES-02` | `series_map` |
| Volume | `VOL-02` | `volume_design` |
| Chapter | `CH-02` | `chapter_design` |

The Review View includes:

```text
complete active candidate
exact generator Context snapshot payload
candidate and Context hashes
artifact-specific private Author extension when required
prior Review for a revised candidate
artifact-specific Review rules
```

A valid Review:

- identifies semantic issues only;
- never returns a corrected plan;
- never chooses adoption or publication;
- never changes source generation or parent hashes.

Invalid Review JSON or invalid Issue records consume response-structure retries.

A valid Review with issues consumes no response retry.

---

## 11. Common revision contract

Each family revision stage returns one complete replacement candidate with the exact original candidate Schema.

| family | revision stage | owner retained |
|---|---|---|
| Series | `SERIES-REV` | `SERIES-01` |
| Volume | `VOL-REV` | `VOL-01` |
| Chapter | `CH-REV` | `CH-01` |

Inputs:

```text
complete active candidate
complete saved Review
exact generator Context payload
whole-replacement contract rules
next revision-round number
```

Forbidden revision responses:

```text
JSON Patch
merge patch
diff
edit instructions
only changed fields
reference to unchanged fields
new source generation
new target number
```

A structurally invalid revision does not create a new version directory.

---

## 12. Revised-version manifest

For a successful revision:

```text
new candidate_version = prior candidate_version + 1
new revision_rounds_used = prior revision_rounds_used + 1
new candidate_status = candidate_valid
new review_path = null
new review_sha256 = null
new next_stage = family Review stage
```

The Candidate manifest retains:

```text
owner operation_id
owner processor_type = llm_generate
target_id
logical input identity required by Runtime
```

It records the accepted revision call through `last_call_id`.

The new version's `input_snapshot_sha256` is the Revision Context snapshot hash. The original generation Context remains referenced from that Revision snapshot.

---

## 13. Common Review routing

After a structurally valid saved Review:

### 13.1 No issues

Condition:

```text
review.issue_counts.total = 0
```

Result:

```text
candidate_status = ready_for_adoption
residual_issues_path = null
next_stage = family adoption stage
```

### 13.2 Issues and revision remains

Condition:

```text
review.issue_counts.total > 0
revision_rounds_used < max_revision_rounds
```

Result:

```text
candidate_status = revision_required
next_stage = family revision stage
```

### 13.3 Issues and revision exhausted

Condition:

```text
review.issue_counts.total > 0
revision_rounds_used >= max_revision_rounds
```

Code:

1. marks the active version `exhausted`;
2. appends one private residual-issue record per normalized Issue;
3. validates that the residual records are durable;
4. marks the candidate `ready_for_adoption`;
5. routes to the family adoption stage.

Only semantic Review issues may use this path.

A broken reference, invalid Thread transition, missing Chapter entry, or other mechanical defect still blocks adoption.

### 13.4 Zero revision rounds

When `max_revision_rounds=0`:

- the initial candidate is reviewed once;
- issues are recorded as residual;
- no revision stage is called;
- mechanical adoption validation still applies.

---

## 14. Common plan-adoption staging

Each adoption stage is code-only.

It creates:

```text
one staged final plan artifact
one staged plan-validation report
```

The staged final plan contains code-owned metadata from `planning_artifacts.md`, including:

```text
schema_version
source generation path/hash identity
Brief/Initial-design/parent-plan hashes as applicable
accepted_candidate_sha256
created_at
```

The Candidate content remains unchanged inside its corresponding adopted content fields.

No Review or residual Issue text is copied into the adopted plan.

---

## 15. Plan-validation report

Each staged plan-validation report contains:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | exact |
| `run_id` | Run ID | yes | no | none | code | active run |
| `operation_id` | adoption Stage ID | yes | no | none | code | `SERIES-ID`, `VOL-ID`, or `CH-ID` |
| `target_id` | planning target ID | yes | no | none | code | stage target |
| `candidate_path` | workspace-relative path | yes | no | none | code | active candidate |
| `candidate_sha256` | SHA-256 | yes | no | none | code | candidate hash |
| `review_path` | workspace-relative path | yes | no | none | code | active Review |
| `review_sha256` | SHA-256 | yes | no | none | code | Review hash |
| `source_generation_id` | Generation ID | yes | no | none | code | generation used for adoption |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | source generation |
| `parent_plan_path` | workspace-relative path | yes | yes | `null` | code | null for Series; required for Volume/Chapter |
| `parent_plan_sha256` | SHA-256 | yes | yes | `null` | code | null iff parent path null |
| `checks` | array<Plan check result> | yes | no | none | code | nonempty and sorted |
| `all_checks_pass` | boolean | yes | no | none | code | true iff all pass |
| `staged_plan_path` | workspace-relative path | yes | no | none | code | exact staged artifact |
| `staged_plan_sha256` | SHA-256 | yes | no | none | code | matches staged plan |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

Plan check result:

```text
check_id
status = pass | fail
artifact_path
artifact_sha256
message
```

Minimum common checks:

```text
candidate and Review hashes
ready-for-adoption state
residual record durability when applicable
source-generation equality to current HEAD
source Generation manifest validity
parent-plan path/hash
exact adopted root Schema
all persistent references
retired-reference rejection
Thread transition validity
Ending-profile validity
unknown-field rejection
canonical hash
no placeholder hash
no candidate/review/audit path inside adopted content
```

Adoption requires `all_checks_pass=true`.

---

## 16. Plan adoption transaction

For a new immutable final plan:

1. validate that the final adopted path does not already exist;
2. build the staged artifact and validation report;
3. `fsync` staged files;
4. atomically move the staged plan to the final `plans/` path;
5. re-read and validate the adopted file and hash;
6. atomically update Run state to the family postcondition;
7. write a unique successful operation-audit record;
8. remove staging.

The final plan path is the adoption point.

Because normal planning never replaces an adopted plan, an existing final path causes:

```text
valid same artifact:
  reconcile Run state, do not overwrite

different or invalid artifact:
  mechanical corruption stop
```

---

## 17. Adoption crash semantics

### 17.1 Before final plan move

Only staging exists.

Startup quarantines abandoned staging and resumes from the ready candidate.

### 17.2 After final plan move but before Run-state update

The plan is adopted.

Startup:

- validates the final plan;
- reconciles Run state to the adoption stage completed;
- clears the active Candidate path;
- routes to the correct next stage;
- removes remaining staging.

### 17.3 Partial or invalid final file

Atomic final move prevents partial bytes. If the final file exists but fails validation, startup stops mechanically and never regenerates over it.

---

# Part I: Series planning

## 18. SERIES-01 — Generate Series map

### 18.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `series_map` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `series_planner_builder` |
| logical owner | `SERIES-01` |
| target ID | `series` |
| response Schema | Series-map candidate |
| next stage | `SERIES-02` |

### 18.2 Preconditions

```text
Run-state next_stage = SERIES-01
valid canon/HEAD = 00000000
valid Genesis Generation and Commit manifests
valid input/brief.json
valid canon/initial-design.json
plans/series-map.json does not exist
current_volume_number is null or 1
current_chapter_number is null
current_scene_number is null
```

A non-Genesis HEAD before Series-map adoption is a mechanical pipeline-order violation.

### 18.3 Authoritative inputs

```text
adopted Brief
adopted Initial design
Genesis current Canon
Genesis Knowledge items
Genesis Story state
Genesis Generation manifest
Effective Editorial and Publishing profiles
Series-map contract rules
```

The Planner Author view includes every required Major Thread and Ending criterion.

### 18.4 Output

```text
runtime/candidates/planning/series-map/v0001/series-map.json
runtime/candidates/planning/series-map/v0001/candidate-manifest.json
```

### 18.5 Mechanical validation

In addition to the common rules:

```text
Volume array length equals Brief volumes
Volume numbers contiguous from 1
Volume 1 role = opening
last Volume role = final
midpoint/pre_final role placement
one protagonist ID and continuous start/end targets
Relationship target continuity
Major Thread start/action/target chains
no retirement of required Major Thread
all required Major Threads end resolved/4
all required Ending criteria listed
all required final criteria use satisfy
nonfinal reader questions when required
final reader question may be null
final local resolution and protagonist end compatibility
```

### 18.6 Success transition

```text
Candidate status = candidate_valid
Run last_completed_stage = SERIES-01
Run next_stage = SERIES-02
Run active_candidate_manifest_path =
  runtime/candidates/planning/series-map/v0001/candidate-manifest.json
```

---

## 19. SERIES-02 — Review Series map

### 19.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_review` |
| operation key | `series_map` |
| artifact class | `audit` |
| Context builder | `review_builder` |
| reviewed role | `series_map` |
| next stage | routing result |

### 19.2 Required Review coverage

```text
Brief and Initial-design fidelity
Volume count and sequence
Volume structural roles
protagonist progression continuity
Relationship progression continuity
Major Thread operation continuity
required Major Thread final resolution
Ending-criterion coverage
Volume-local payoff
nonfinal continuation questions
final ending compatibility
secret-author-truth leakage into general plan fields
```

### 19.3 Output

```text
active Series candidate directory/review.json
```

Routing follows Section 13.

---

## 20. SERIES-REV — Replace Series map

### 20.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_revise` |
| operation key | `series_map` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `revision_builder` |
| owner retained | `SERIES-01` |
| response Schema | complete Series-map candidate |
| next stage | `SERIES-02` |

### 20.2 Output example

First revision:

```text
runtime/candidates/planning/series-map/v0002/series-map.json
runtime/candidates/planning/series-map/v0002/candidate-manifest.json
```

A revision may correct targets and wording, but it may not change:

```text
Brief Volume count
protagonist identity
adopted record IDs
source generation
required Ending-criterion set
```

---

## 21. SERIES-ID — Adopt Series map

### 21.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact classes | `staged_internal`, `staged_internal_validation`, `adopted`, separate `audit` |
| LLM call | none |
| source | active ready Series candidate |
| final path | `plans/series-map.json` |
| next stage | `VOL-01` |

### 21.2 Staging

```text
.staging/planning/series-map/<run-id>/
  series-map.json
  plan-validation.json
```

### 21.3 Adopted metadata

Code adds:

```text
schema_version = 1.0
source_generation_id = 00000000
source_generation_manifest_sha256
brief_sha256
initial_design_sha256
accepted_candidate_sha256
created_at
```

### 21.4 Postconditions

Run state becomes:

```text
last_completed_stage = SERIES-ID
next_stage = VOL-01
current_target_id = v01
current_volume_number = 1
current_chapter_number = null
current_scene_number = null
active_candidate_manifest_path = null
```

`plans/series-map.json` is immutable after adoption.

---

# Part II: Volume planning

## 22. Volume entry conditions

VOL-01 may begin only when:

```text
plans/series-map.json validates
target Volume exists in the Series map
no adopted Volume design exists for that target
the target Volume has no adopted Scene artifacts
current HEAD is valid
target Volume is 1
OR the preceding Volume has completed VH-ID
```

For Volume `>1`, code requires the previous Volume handoff at the canonical path defined by `commit_and_output.md`.

The Volume source generation is the HEAD generation at entry.

---

## 23. VOL-01 — Generate Volume design

### 23.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `volume_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `volume_planner_builder` |
| logical owner | `VOL-01` |
| target ID | `vNN` |
| response Schema | Volume-design candidate |
| next stage | `VOL-02` |

### 23.2 Authoritative inputs

```text
adopted Series map
exact target Series Volume entry
current HEAD Generation/Canon/Knowledge/State
adopted Brief and Initial design
preceding Volume handoff when target > 1
Effective profiles and planning targets
Volume-design contract rules
```

The preceding Volume handoff is null for Volume 1.

### 23.3 Output

For Volume 4:

```text
runtime/candidates/planning/volumes/v04/v0001/volume-design.json
runtime/candidates/planning/volumes/v04/v0001/candidate-manifest.json
```

### 23.4 Mechanical validation

In addition to common rules:

```text
candidate volume_number equals target
title and volume promise are nonempty
starting State is compatible with actual current HEAD/handoff
protagonist target conforms to Series entry
Relationship targets conform to Series entry
Thread start values equal actual State or exact carried plan baseline
Thread actions are valid
Ending targets conform to Series entry
reader question follows nonfinal/final rules
major conflict is complete
target_chapter_count equals Chapter-function count
Chapter numbers contiguous
Chapter functions cover every required turn and Thread action
final/nonfinal Volume ending-function conditions
```

### 23.5 Success transition

```text
Candidate status = candidate_valid
Run last_completed_stage = VOL-01
Run next_stage = VOL-02
Run active_candidate_manifest_path =
  runtime/candidates/planning/volumes/vNN/v0001/candidate-manifest.json
```

The Candidate Context snapshot fixes the exact source generation.

---

## 24. VOL-02 — Review Volume design

### 24.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_review` |
| operation key | `volume_design` |
| artifact class | `audit` |
| Context builder | `review_builder` |
| reviewed role | `volume_design` |
| next stage | routing result |

### 24.2 Required Review coverage

```text
Series target preservation
actual start-State compatibility
protagonist and Relationship change coherence
Thread action validity
Ending-target safety and coverage
major conflict and stakes
required-turn distribution
Chapter-function coverage
local Volume resolution
nonfinal/final boundary behavior
title and reader promise
secret-author-truth leakage
```

### 24.3 Output

```text
active Volume candidate directory/review.json
```

Routing follows Section 13.

---

## 25. VOL-REV — Replace Volume design

### 25.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_revise` |
| operation key | `volume_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `revision_builder` |
| owner retained | `VOL-01` |
| response Schema | complete Volume-design candidate |
| next stage | `VOL-02` |

### 25.2 Restrictions

The revision may not change:

```text
target volume_number
parent Series-map entry
source generation
preceding handoff source
protagonist identity
parent required Thread and Ending targets
```

It returns the entire Volume design.

---

## 26. VOL-ID — Adopt Volume design

### 26.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact classes | `staged_internal`, `staged_internal_validation`, `adopted`, separate `audit` |
| LLM call | none |
| source | active ready Volume candidate |
| final path | `plans/volumes/vNN/volume-design.json` |
| next stage | `CH-01` |

### 26.2 Staging

```text
.staging/planning/volumes/vNN/<run-id>/
  volume-design.json
  plan-validation.json
```

### 26.3 Adopted metadata

Code adds:

```text
schema_version = 1.0
source_generation_id
source_generation_manifest_sha256
series_map_sha256
preceding_volume_handoff_path
preceding_volume_handoff_sha256
accepted_candidate_sha256
created_at
```

For Volume 1, both preceding-handoff fields are null.

### 26.4 Additional adoption checks

```text
current HEAD still equals candidate source generation
target Volume still has no adopted Scene
Series-map hash unchanged
preceding handoff hash unchanged
target Chapter count and functions valid
no final Volume design exists already
```

### 26.5 Postconditions

Run state becomes:

```text
last_completed_stage = VOL-ID
next_stage = CH-01
current_target_id = vNN-c001
current_volume_number = target Volume
current_chapter_number = 1
current_scene_number = null
active_candidate_manifest_path = null
```

---

# Part III: Chapter planning

## 27. Chapter entry conditions

CH-01 may begin only when:

```text
parent Volume design validates
target Chapter-function entry exists
no adopted Chapter design exists for that target
the target Chapter has no adopted Scene artifacts
current HEAD is valid
current Story-clock is before the first Scene of the target Chapter
```

For Chapter 1:

- the preceding Chapter handoff path is null;
- the Volume start is represented by the current generation and preceding Volume handoff already incorporated into the Volume design.

For Chapter `>1` in version 1:

- `prior_chapter_handoff_path` remains null;
- the Context Builder uses the current HEAD and the immediately preceding Chapter's final adopted Scene manifest, committed delta `handoff_summary`, and safe previous-handoff projection.

A future explicit Chapter-handoff artifact may populate the nullable metadata fields without changing the candidate Schema.

---

## 28. CH-01 — Generate Chapter design

### 28.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `chapter_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `chapter_planner_builder` |
| logical owner | `CH-01` |
| target ID | `vNN-cNNN` |
| response Schema | Chapter-design candidate |
| next stage | `CH-02` |

### 28.2 Authoritative inputs

```text
adopted parent Volume design
exact target Chapter-function entry
current HEAD Generation/Canon/Knowledge/State
adopted Series map
adopted Brief and Initial design
immediately preceding safe Scene/Chapter handoff when available
Effective editorial and length settings
Chapter-design contract rules
```

### 28.3 Output

For Volume 4, Chapter 3:

```text
runtime/candidates/planning/volumes/v04/chapters/c003/v0001/chapter-design.json
runtime/candidates/planning/volumes/v04/chapters/c003/v0001/candidate-manifest.json
```

### 28.4 Mechanical validation

In addition to common rules:

```text
candidate Volume/Chapter coordinates equal target
title and purpose are nonempty
purpose and chapter_end_function match parent Chapter-function target
start State is compatible with actual HEAD
active cast/Relationships/Threads resolve
time and Location references are compatible
primary change target matches parent plan
Thread actions are valid and parent-compatible
Ending targets are parent-compatible
required World entities resolve
target_scene_count equals Scene-plan length
Scene numbers are contiguous from 1
first Scene role = opening
last Scene role = resolution
optional climax placement
every Scene POV resolves and appears in required cast
every required beat list is nonempty
Chapter handoff requirement follows final/nonfinal boundary
```

### 28.5 Success transition

```text
Candidate status = candidate_valid
Run last_completed_stage = CH-01
Run next_stage = CH-02
Run active_candidate_manifest_path =
  runtime/candidates/planning/volumes/vNN/chapters/cNNN/v0001/candidate-manifest.json
```

---

## 29. CH-02 — Review Chapter design

### 29.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_review` |
| operation key | `chapter_design` |
| artifact class | `audit` |
| Context builder | `review_builder` |
| reviewed role | `chapter_design` |
| next stage | routing result |

### 29.2 Required Review coverage

```text
Volume Chapter-function preservation
actual start-State compatibility
primary change clarity
cast and POV feasibility
Location/time feasibility
Thread action validity
Ending-target safety
Scene-function sequence
required beat coverage
emotional progression
Chapter ending and next handoff
secret-author-truth leakage
```

### 29.3 Output

```text
active Chapter candidate directory/review.json
```

Routing follows Section 13.

---

## 30. CH-REV — Replace Chapter design

### 30.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_revise` |
| operation key | `chapter_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `revision_builder` |
| owner retained | `CH-01` |
| response Schema | complete Chapter-design candidate |
| next stage | `CH-02` |

### 30.2 Restrictions

The revision may not change:

```text
target Volume/Chapter coordinates
parent Volume-design target entry
source generation
protagonist identity
parent-required Thread actions
parent chapter-end function
```

It may revise the complete Scene-function sequence when the parent requirements remain satisfied.

---

## 31. CH-ID — Adopt Chapter design

### 31.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact classes | `staged_internal`, `staged_internal_validation`, `adopted`, separate `audit` |
| LLM call | none |
| source | active ready Chapter candidate |
| final path | `plans/volumes/vNN/chapters/cNNN/chapter-design.json` |
| next stage | `SC-01` |

### 31.2 Staging

```text
.staging/planning/chapters/vNN/cNNN/<run-id>/
  chapter-design.json
  plan-validation.json
```

### 31.3 Adopted metadata

Code adds:

```text
schema_version = 1.0
source_generation_id
source_generation_manifest_sha256
volume_design_sha256
prior_chapter_handoff_path
prior_chapter_handoff_sha256
accepted_candidate_sha256
created_at
```

Version-1 normal values:

```text
prior_chapter_handoff_path = null
prior_chapter_handoff_sha256 = null
```

### 31.4 Additional adoption checks

```text
current HEAD still equals candidate source generation
parent Volume-design hash unchanged
target Chapter still has no adopted Scene
target Chapter-function entry unchanged
Scene-plan count/sequence valid
all current persistent references still resolve and are not retired
```

### 31.5 Postconditions

Run state becomes:

```text
last_completed_stage = CH-ID
next_stage = SC-01
current_target_id = vNN-cNNN-s001
current_volume_number = target Volume
current_chapter_number = target Chapter
current_scene_number = 1
scene_phase = SCENE_NOT_STARTED
active_candidate_manifest_path = null
```

The downstream Scene pipeline generates the first Scene card.

---

# Part IV: Re-entry and loop behavior

## 32. Re-entry after Chapter completion

The Scene/Commit pipeline determines Chapter completion from the adopted Chapter design and the committed final Scene number.

When a Chapter completes:

### 32.1 More Chapters remain

Run state is set to:

```text
next_stage = CH-01
current_target_id = vNN-c(next)
current_volume_number = current Volume
current_chapter_number = next Chapter
current_scene_number = null
scene_phase = null
```

CH-01 then uses the current HEAD and preceding final Scene handoff.

### 32.2 No Chapters remain

The Volume is complete.

Run state is set to:

```text
next_stage = VH-01
current_target_id = vNN
current_volume_number = completed Volume
current_chapter_number = null
current_scene_number = null
scene_phase = null
```

Planning does not generate another Chapter.

---

## 33. Re-entry after Volume handoff

After `VH-ID`:

### 33.1 More Volumes remain

Run state is set to:

```text
next_stage = VOL-01
current_target_id = v(next)
current_volume_number = next Volume
current_chapter_number = null
current_scene_number = null
```

VOL-01 requires the adopted preceding Volume handoff.

### 33.2 Final Volume completed

Run state routes to:

```text
COMP-PRE
```

VOL-01 is not called.

---

## 34. Existing adopted plan reconciliation

Before generation, code checks the final path.

### 34.1 Valid expected adopted plan exists

If:

```text
final plan validates
target and parent hashes are correct
Run state is behind the adoption stage
```

startup or stage preflight reconciles Run state to the adoption postcondition.

No new candidate or LLM call is created.

### 34.2 Valid but unexpected plan exists

Examples:

```text
Chapter design exists before parent Volume design
Volume design exists for a future Volume before preceding handoff
Series map source generation is not Genesis
```

This is a mechanical workspace-order violation. Code does not silently use the file.

### 34.3 Invalid or conflicting plan exists

Stop mechanically. Never overwrite it.

---

## 35. Candidate staleness

An unadopted planning candidate becomes stale when any semantic source changes, including:

```text
source HEAD generation
source Generation-manifest hash
Brief hash
Initial-design hash
parent-plan hash
preceding handoff hash
Effective semantic configuration
prompt bundle
Schema bundle
Context-builder version
```

A stale candidate is not reviewed, revised, or adopted.

Code:

1. records a staleness operation audit;
2. freezes/quarantines the stale active version as appropriate;
3. creates the next version directory using the owner generation stage;
4. uses a new generation Context snapshot;
5. leaves `revision_rounds_used` unchanged because this is regeneration, not semantic revision.

Under the single-writer normal pipeline, source-generation staleness should not occur. Its presence indicates crash recovery, manual modification, or an implementation defect.

---

## 36. Review and revision resume

### 36.1 Review resume

If active `review.json` exists and matches the Candidate manifest:

- do not call the reviewer again;
- recompute routing from saved issue count and revision budget;
- write missing Run-state routing only.

If Review is absent or mismatched, run the Review stage.

### 36.2 Revision resume

If the next version directory contains a valid complete candidate and Candidate manifest:

- activate it;
- route to the family Review stage.

If the next version directory is partial:

- quarantine it;
- determine from immutable Call audit and Candidate manifest whether a provider response was already accepted;
- never reconstruct the candidate from raw audit output;
- repeat the revision call only when no durable valid candidate exists and budget permits.

### 36.3 Adoption resume

If staging is complete but no final plan exists:

- revalidate staging and candidate readiness;
- continue the adoption transaction.

If the final plan exists:

- reconcile as Section 34.

---

# Part V: Transition matrices

## 37. Series transitions

| current stage | condition | next stage |
|---|---|---|
| `SERIES-01` | valid candidate | `SERIES-02` |
| `SERIES-02` | no issues | `SERIES-ID` |
| `SERIES-02` | issues, revision remains | `SERIES-REV` |
| `SERIES-02` | issues, revision exhausted | `SERIES-ID` |
| `SERIES-REV` | valid complete replacement | `SERIES-02` |
| `SERIES-ID` | plan adopted | `VOL-01` |

---

## 38. Volume transitions

| current stage | condition | next stage |
|---|---|---|
| `VOL-01` | valid candidate | `VOL-02` |
| `VOL-02` | no issues | `VOL-ID` |
| `VOL-02` | issues, revision remains | `VOL-REV` |
| `VOL-02` | issues, revision exhausted | `VOL-ID` |
| `VOL-REV` | valid complete replacement | `VOL-02` |
| `VOL-ID` | plan adopted | `CH-01` |

---

## 39. Chapter transitions

| current stage | condition | next stage |
|---|---|---|
| `CH-01` | valid candidate | `CH-02` |
| `CH-02` | no issues | `CH-ID` |
| `CH-02` | issues, revision remains | `CH-REV` |
| `CH-02` | issues, revision exhausted | `CH-ID` |
| `CH-REV` | valid complete replacement | `CH-02` |
| `CH-ID` | plan adopted | `SC-01` |

No other normal planning transition is permitted.

---

## 40. Error transitions

| failure | result |
|---|---|
| provider transport retry exhausted | Run failed; no automatic next stage |
| response-structure retry exhausted | Run failed; no automatic next stage |
| valid Review issues | revision/exhaustion routing; not failed |
| mechanical candidate invalid | candidate not written |
| mechanical plan adoption validation fails | Run failed; final plan unchanged |
| source generation changes before adoption | candidate stale; regenerate under owner stage |
| parent-plan hash changes | candidate stale or workspace corruption |
| final plan path already contains different bytes | mechanical corruption stop |
| budget preflight fails | Run stopped with `budget_exhausted` |
| explicit safe-boundary user stop | Run stopped with `user_stop` |

A user stop does not interrupt an atomic final-plan move or Run-state replacement.

---

## 41. Stage completion rule

A planning stage is complete only when:

```text
its output artifact is durable
its canonical hash is known
its Candidate/Review/validation manifest is durable
all stage-specific checks pass
Run state records last_completed_stage and next_stage
```

Receiving an LLM response is not stage completion.

For an adoption stage, the final `plans/...` file must exist and validate.

---

## 42. Resume-source matrix

| stage | authoritative resume source |
|---|---|
| `SERIES-01` | Genesis adopted sources and active Series Candidate manifest |
| `SERIES-02` | active Series candidate and its `review.json` when valid |
| `SERIES-REV` | active reviewed Series version plus Revision Context |
| `SERIES-ID` | active ready Series version, Review, residual records |
| `VOL-01` | Series map, current HEAD, preceding handoff, active Volume Candidate manifest |
| `VOL-02` | active Volume candidate and Review |
| `VOL-REV` | active reviewed Volume version plus Revision Context |
| `VOL-ID` | active ready Volume version and parent sources |
| `CH-01` | Volume design, current HEAD, prior safe Scene handoff, active Chapter Candidate manifest |
| `CH-02` | active Chapter candidate and Review |
| `CH-REV` | active reviewed Chapter version plus Revision Context |
| `CH-ID` | active ready Chapter version and parent sources |

Raw LLM call audits are never resume sources.

---

## 43. Required operation audits

Code writes unique operation-audit records for at least:

```text
planning target selected
planning Context built
candidate version activated
Review routing decision
revision version superseded
residual issues recorded
candidate declared stale
staging validation completed
Series map adopted
Volume design adopted
Chapter design adopted
adopted plan reconciled after crash
planning staging quarantined
```

Audit records may contain paths, hashes, counts, target numbers, and status. They must not contain credential values or raw private author truth.

---

## 44. Cross-plan invariants

At every adoption boundary, code verifies:

```text
Series Volume count equals Brief
Volume exists in Series map
Chapter exists in parent Volume design
parent-plan hashes match
source-generation references validate
target coordinates match Run state
all persistent IDs resolve in source generation
no retired record is newly planned as active
Thread action chains are valid
required Major Threads resolve in final Series target
required Ending criteria are covered
nonfinal/final reader-question rules
Volume Chapter-function count
Chapter Scene-function count
adopted paths contain no candidate, audit, checkpoint, or staging references
```

---

## 45. Forbidden implementation shortcuts

Forbidden:

```text
one mutable planning candidate directory without versioning
overwriting Review history
choosing the newest file by modification time
reading raw LLM audit response as a candidate
reviewing a mechanically invalid plan
treating Review issues as response-structure failures
retrying a reviewer until issues are empty
partial revision patches
changing target coordinates during revision
changing source generation during revision
adopting after HEAD changed
updating an adopted plan to match later prose
copying author truth into writer-facing plan fields
putting Review text inside an adopted plan
using artifact class "review candidate"
using artifact class "adopted/audit"
overwriting an existing conflicting final plan
```

---

## 46. Mechanical acceptance conditions

An implementation of this pipeline is acceptable only when tests demonstrate:

```text
exact stage IDs and processors
canonical artifact classes
target selection from Run state and parent plans
Series source generation fixed to Genesis
Volume source generation at Volume start
Chapter source generation at Chapter start
versioned candidate directories
immutable superseded versions and Reviews
logical owner retained across revision
Candidate-manifest-only resume
exact Series candidate validation
exact Volume candidate validation
exact Chapter candidate validation
persistent-reference and retired-record validation
Thread status/progress/action validation
Ending-criterion and Publishing-profile rules
Review structural/semantic classification
whole-candidate revision
zero revision-round behavior
residual-issue adoption routing
mechanical defect never adopted by exhaustion
stale-source regeneration
staged plan-validation report
source HEAD recheck before adoption
immutable final plan adoption
crash reconciliation after final move
existing-plan conflict rejection
Series-ID to Volume-1 routing
VOL-ID to Chapter-1 routing
CH-ID to Scene-1 routing
Chapter-completion re-entry
Volume-handoff re-entry
unknown transition rejection
unknown-field rejection
canonical hash stability
```
