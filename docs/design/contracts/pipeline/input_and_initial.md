# Pipeline contracts: Input and initial design

This document is the normative pipeline contract from run bootstrap through Genesis adoption:

```text
INPUT-01
INPUT-02
INPUT-03
INIT-01
INIT-02
INIT-03
INIT-04
INIT-05
INIT-06
INIT-REV
INIT-ID
```

The data produced by these stages is defined by [`../data/brief_and_initial.md`](../data/brief_and_initial.md). Candidate manifests, Run state, counters, Genesis manifests, pointers, and atomic-write rules are defined by [`../ledger/runtime_records.md`](../ledger/runtime_records.md). Canon and Story-state output contracts are defined by the Ledger documents in [`../ledger/`](../ledger/). Context builders are defined by [`../../context_contracts.md`](../../context_contracts.md). Retry, budget, and provider rules are defined by [`../../configuration_contracts.md`](../../configuration_contracts.md). Review and residual-issue records are defined by [`../data/review_and_audit.md`](../data/review_and_audit.md).

Every JSON object written by this pipeline uses `additionalProperties: false`.

---

## 1. Pipeline goals

This pipeline must produce one mechanically valid Genesis state from one user input source.

The pipeline guarantees:

```text
exactly one input mode
one immutable adopted Brief
one structurally valid integrated Initial-design bundle
one reviewed or revision-exhausted bundle
deterministic persistent-ID allocation
complete Genesis Canon records
complete Genesis Character, Relationship, and Thread State
valid sparse initial Knowledge State
valid Genesis manifests and local-key mapping
canon/HEAD = 00000000 only after durable adoption
```

The pipeline must not:

```text
use raw LLM audit output as resume state
accept unresolved local keys
let an LLM choose persistent IDs
let review output mutate a candidate
adopt a mechanically invalid bundle because revision budget is exhausted
write placeholder hashes
reuse allocated IDs
publish or generate prose
```

---

## 2. Processor and artifact classes

### 2.1 Processor types

This pipeline uses the exact Runtime processor types.

| processor type | meaning |
|---|---|
| `code` | deterministic local processing; no provider call |
| `llm_generate` | new complete candidate generation |
| `llm_review` | semantic review of one complete candidate |
| `llm_revise` | complete candidate replacement using Review issues |

`llm_extract` is not used in this pipeline.

### 2.2 Artifact classes

Only these canonical artifact classes are used:

```text
candidate
checkpoint
staged_internal
staged_internal_validation
adopted
audit
```

This pipeline uses:

| class | examples |
|---|---|
| `candidate` | Brief candidate, Concept, People, World, Arcs, integrated bundle |
| `staged_internal` | staged Genesis generation and `initial-design.json` |
| `staged_internal_validation` | Genesis validation result before pointer update |
| `adopted` | `input/keywords.json`, `input/brief.json`, Genesis generation, `canon/initial-design.json`, `canon/HEAD` |
| `audit` | LLM calls, Reviews, residual issues, code-operation records |

`review candidate`, `adopted/audit`, and any slash-combined class are forbidden.

---

## 3. Run bootstrap

Run bootstrap occurs before the first durable stage transition.

It is code-only and performs:

1. acquire `.storycraft.lock`;
2. validate CLI syntax and select exactly one input mode;
3. normalize the user-provided source to the applicable content Schema;
4. materialize and validate `runtime/effective-config.json`;
5. resolve the credential environment-variable name without persisting its value;
6. initialize `runtime/counters.json` when this is a new workspace;
7. create immutable `runtime/run-manifest.json`;
8. create `runtime/run-state.json` with:
   - `run_status=initialized`;
   - `last_completed_stage=null`;
   - `next_stage=INPUT-01`;
   - `current_head_generation=null` for a new story;
   - `active_candidate_manifest_path=null`;
9. write one bootstrap operation-audit record.

The normalized source bytes and their SHA-256 must already be available in memory when the Run manifest is created.

A crash before INPUT-01 completes does not create a resumable input pipeline. Startup may remove or quarantine the incomplete run after verifying that no adopted input source exists. The caller repeats the invocation with the original input.

A new run is rejected when a valid `canon/HEAD` already exists, unless a separate explicitly supported new-project command selected a different workspace.

---

## 4. Input-mode branch

Exactly one branch is used.

### 4.1 Brief mode

Input is one complete Brief content candidate from `brief_and_initial.md`.

```text
INPUT-01
→ INIT-01
```

`INPUT-02` and `INPUT-03` are skipped.

INPUT-01 writes the adopted `input/brief.json` directly because no LLM-generated Brief candidate is required.

### 4.2 Keywords mode

Input is one Keyword-source object.

```text
INPUT-01
→ INPUT-02
→ INPUT-03
→ INIT-01
```

INPUT-01 writes `input/keywords.json`.

INPUT-02 generates a Brief content candidate.

INPUT-03 adopts `input/brief.json`.

### 4.3 Skip recording

Skipped stages are not marked completed.

Run state records the actual transition:

```text
brief mode:
  last_completed_stage = INPUT-01
  next_stage = INIT-01

keywords mode:
  last_completed_stage = INPUT-01
  next_stage = INPUT-02
```

No fake Review, candidate, or audit file is created for a skipped stage.

---

## 5. Candidate version directories

Every logical candidate is stored inside a version directory.

### 5.1 Path form

```text
runtime/candidates/<logical-candidate-root>/vNNNN/
  <operation-specific candidate filename>
  review.json                         # only after a Review stage
  candidate-manifest.json
```

`vNNNN` is four-digit, one-based, and contiguous for that logical candidate.

Examples:

```text
runtime/candidates/input/brief/v0001/brief.json
runtime/candidates/initial-design/concept/v0001/concept.json
runtime/candidates/initial-design/people/v0001/people.json
runtime/candidates/initial-design/world/v0001/world.json
runtime/candidates/initial-design/arcs/v0001/arcs.json
runtime/candidates/initial-design/bundle/v0001/bundle.json
runtime/candidates/initial-design/bundle/v0002/bundle.json
```

### 5.2 Logical owner

The Candidate manifest `operation_id` identifies the stage that owns the logical candidate:

| logical candidate | owner `operation_id` | owner processor |
|---|---|---|
| generated Brief | `INPUT-02` | `llm_generate` |
| Concept | `INIT-01` | `llm_generate` |
| People | `INIT-02` | `llm_generate` |
| World | `INIT-03` | `llm_generate` |
| Arcs | `INIT-04` | `llm_generate` |
| integrated bundle | `INIT-05` | `llm_generate` |

A revised integrated bundle remains owned by `INIT-05`. The `INIT-REV` call is identified by:

```text
the new version directory
candidate_version
revision_rounds_used
last_call_id
the unique LLM-call audit role = revise
the Revision Context snapshot
```

The owner fields are not rewritten to `INIT-REV`.

### 5.3 Version lifecycle

- `v0001` is created by the logical owner generation stage.
- A revision creates a new complete version directory.
- A version directory is never reused.
- An older version remains immutable and retains its `review.json`.
- Run state `active_candidate_manifest_path` points only to the active version.
- The active version's Candidate manifest may be atomically updated while that version is active.
- Once superseded, its Candidate manifest is frozen.
- Adoption or downstream integration refers to the exact active candidate path and hash.

This version-directory rule prevents Review history from being overwritten while preserving the fixed filename `review.json`.

---

## 6. Common LLM-stage execution

Every `llm_generate`, `llm_review`, and `llm_revise` stage follows this order.

### 6.1 Preflight

Code validates:

```text
Run-state next_stage equals the stage
workspace lock is held
Run and Effective-config compatibility
required source artifacts and hashes
required Context snapshot
provider credential availability
context hard input limit
call, token, time, cost, and audit-storage budgets
```

Failure before a provider request is a mechanical stop and does not consume an LLM call.

### 6.2 Provider call

For each HTTP/provider attempt:

1. allocate and persist one Call ID;
2. write the unique request audit after strict redaction preparation;
3. perform the call with configured timeout and transport retry;
4. persist actual or estimated usage before response validation;
5. write the complete immutable LLM-call audit.

### 6.3 Structural validation

A successful transport response is accepted only after:

```text
UTF-8 validation
JSON parsing for structured stages
exact response Schema
unknown-field rejection
all field conditions
all mechanically checkable cross-reference conditions
operation-specific content restrictions
canonical normalization
```

Structural failure consumes response-structure retry budget.

A structurally invalid response never creates or replaces a candidate artifact.

### 6.4 Durable success

After one structurally valid response:

- write the complete candidate or Review artifact to a temporary same-directory file;
- calculate its canonical SHA-256;
- atomically replace the destination;
- update the Candidate manifest;
- update Run state only after the candidate/Review and manifest are durable.

### 6.5 Exhaustion

If transport or response-structure retries are exhausted:

```text
run_status = failed
stop_reason_code = mechanical_error
next_stage = null
```

The last structurally valid candidate remains available when one existed before the failed revision/review attempt.

Normal resume requires explicit operator action and the Runtime recoverability rules.

---

## 7. Common candidate-manifest rules

### 7.1 Initial generation

For a new version:

```text
candidate_version = version-directory number
candidate_status = initialized
candidate_path = null
candidate_sha256 = null
review_path = null
review_sha256 = null
last_structurally_valid = false
```

After a structurally valid candidate is written:

```text
candidate_status = candidate_valid
candidate_path = exact version candidate path
candidate_sha256 = exact canonical hash
last_structurally_valid = true
last_call_id = accepted response Call ID
```

### 7.2 Intermediate unreviewed candidates

Brief, Concept, People, World, and Arcs candidates have no dedicated semantic Review stage.

After their complete mechanical validation:

```text
candidate_status = candidate_valid
review_path = null
review_sha256 = null
next_stage = exact downstream stage
```

Their Candidate manifest is the sole resume authority for that intermediate output.

### 7.3 Integrated-bundle Review

After INIT-06 saves `review.json`:

```text
candidate_status = reviewed
review_path = exact review path
review_sha256 = exact review hash
```

Then code derives the durable routing state described in Section 20.

### 7.4 Manifest/source equality

A downstream stage may read a candidate only when:

```text
candidate-manifest path is the active/expected path
candidate_path exists
candidate_sha256 matches
input_snapshot_sha256 matches the Context snapshot
last_structurally_valid = true
candidate version is not superseded
```

Raw audit content is never substituted for a missing candidate.

---

# Part I: Input stages

## 8. INPUT-01 — Normalize and adopt input source

### 8.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `adopted` plus separate `audit` |
| run when | every new run |
| LLM call | none |
| resume source | adopted input source plus Run state |
| failure class | mechanical |

### 8.2 Inputs

```text
selected input mode from Run manifest
normalized source bytes from bootstrap
Effective config
Run manifest
```

### 8.3 Brief-mode behavior

Code:

1. validates the complete Brief content candidate;
2. validates `volumes` against Publishing profile;
3. confirms no code-owned Brief metadata was supplied as user content;
4. adds profile IDs, `brief_version`, `source_type=brief`, `source_hash`, and `created_at`;
5. writes canonical `input/brief.json`;
6. calculates complete adopted Brief SHA-256;
7. updates Run state:
   - `adopted_brief_path=input/brief.json`;
   - `adopted_brief_sha256=<complete hash>`;
   - `last_completed_stage=INPUT-01`;
   - `next_stage=INIT-01`;
   - `run_status=running`.

No candidate directory is created.

### 8.4 Keywords-mode behavior

Code:

1. validates the Keyword-source object;
2. writes canonical `input/keywords.json`;
3. verifies its hash equals Run-manifest `input_source_sha256`;
4. updates Run state:
   - Brief fields remain null;
   - `last_completed_stage=INPUT-01`;
   - `next_stage=INPUT-02`;
   - `run_status=running`.

### 8.5 Durable completion

INPUT-01 is complete only when:

```text
the adopted source file exists and hashes correctly
Run manifest source path/hash agree
Run state points to the correct next stage
the operation audit is durable
```

### 8.6 Resume

If Run state says INPUT-01 completed:

- validate the adopted source file and hash;
- never rebuild it from CLI text;
- continue to the recorded next stage.

If no valid adopted source exists, the incomplete bootstrap is not resumed.

---

## 9. INPUT-02 — Generate Brief content from keywords

### 9.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `brief` |
| artifact class | `candidate` plus separate `audit` |
| run when | keywords mode only |
| Context builder | `input_brief_builder` |
| logical candidate owner | `INPUT-02` |
| response Schema | Brief content candidate |
| next stage | `INPUT-03` |

### 9.2 Authoritative inputs

```text
input/keywords.json
runtime/effective-config.json
```

The Context snapshot contains only the Keyword source and complete Editorial/Publishing profiles.

### 9.3 Output paths

```text
runtime/candidates/input/brief/v0001/brief.json
runtime/candidates/input/brief/v0001/candidate-manifest.json
```

`review.json` is not created.

### 9.4 Additional mechanical validation

After exact Schema validation, code verifies:

```text
volumes_hint equality when non-null
title/genre/ending hints honored when non-null
every source avoid item retained
volume range and Publishing-profile compatibility
no profile ID
no source hash
no metadata or persistent ID
```

A failure is a response-structure/conditional-rule failure and may be retried within configured budget.

### 9.5 Success state

Candidate manifest:

```text
candidate_status = candidate_valid
candidate_version = 1
next_stage = INPUT-03
```

Run state:

```text
last_completed_stage = INPUT-02
next_stage = INPUT-03
active_candidate_manifest_path =
  runtime/candidates/input/brief/v0001/candidate-manifest.json
```

---

## 10. INPUT-03 — Adopt generated Brief

### 10.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact class | `adopted` plus separate `audit` |
| run when | keywords mode only |
| LLM call | none |
| source | active valid INPUT-02 candidate |
| next stage | `INIT-01` |

### 10.2 Behavior

Under the workspace lock, code:

1. validates the INPUT-02 Candidate manifest and candidate hash;
2. revalidates the Brief content candidate against `input/keywords.json`;
3. confirms Effective-config profile IDs and volume constraints;
4. constructs the adopted Brief;
5. sets:
   - `source_type=keywords`;
   - `source_hash=SHA-256(input/keywords.json)`;
   - profile IDs from Effective config;
   - code-owned version and timestamp;
6. writes canonical `input/brief.json`;
7. re-reads and validates the saved bytes;
8. updates Run state:
   - adopted Brief path/hash;
   - active candidate path cleared;
   - `last_completed_stage=INPUT-03`;
   - `next_stage=INIT-01`.

### 10.3 Failure behavior

A deterministic mismatch between the candidate and source constraints indicates corruption or an implementation defect because INPUT-02 already validated it.

INPUT-03 does not call INPUT-02 again automatically. It fails mechanically with evidence in a code-operation audit.

### 10.4 Resume

When the adopted Brief exists and its hash equals Run state, resume proceeds to INIT-01.

A leftover valid Brief candidate does not override an adopted Brief.

---

# Part II: Initial-design generation

## 11. Common INIT source rules

Every INIT generation stage receives the exact adopted Brief.

Candidate dependencies are explicit:

| stage | earlier candidates permitted |
|---|---|
| `INIT-01` | none |
| `INIT-02` | Concept |
| `INIT-03` | Concept, People |
| `INIT-04` | Concept, People, World |
| `INIT-05` | Concept, People, World, Arcs |

An INIT stage must not search a candidate directory for “latest” files.

It reads exact paths/hashes from:

```text
Run state active stage
the preceding Candidate manifests
the Context snapshot source_refs
```

All dependency version directories are immutable.

---

## 12. INIT-01 — Generate Concept

### 12.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `initial_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `init_concept_builder` |
| logical owner | `INIT-01` |
| response Schema | INIT-01 Concept candidate |
| next stage | `INIT-02` |

### 12.2 Inputs

```text
input/brief.json
Editorial profile
Publishing profile
Concept contract rules
```

### 12.3 Output

```text
runtime/candidates/initial-design/concept/v0001/concept.json
runtime/candidates/initial-design/concept/v0001/candidate-manifest.json
```

### 12.4 Validation

In addition to exact Schema:

```text
Brief genre and ending compatibility
no protagonist replacement
no Brief avoid violation
no nested people/world/arc objects
no persistent IDs or planning coordinates
```

### 12.5 Success transition

```text
Candidate status = candidate_valid
Run last_completed_stage = INIT-01
Run next_stage = INIT-02
```

---

## 13. INIT-02 — Generate People

### 13.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `initial_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `init_people_builder` |
| logical owner | `INIT-02` |
| response Schema | INIT-02 People candidate |
| next stage | `INIT-03` |

### 13.2 Inputs

```text
adopted Brief
exact valid Concept candidate
Editorial profile
People contract rules
```

### 13.3 Output

```text
runtime/candidates/initial-design/people/v0001/people.json
runtime/candidates/initial-design/people/v0001/candidate-manifest.json
```

### 13.4 Validation

Code verifies:

```text
exactly one protagonist
protagonist name equals Brief protagonist
every Brief key person represented exactly once
Character local-key uniqueness
Relationship local-key uniqueness
global uniqueness against Concept-defined local keys, if any
Relationship endpoints resolve to People Characters
Relationship endpoints differ
normalized Character names and aliases do not conflict
primary Relationships are series-scoped
starting Location references use syntactically valid forward local keys
no persistent IDs
```

A forward Location local key is allowed even though INIT-03 has not yet produced it. It is recorded as an unresolved typed forward reference for later integration.

### 13.5 Success transition

```text
Candidate status = candidate_valid
Run last_completed_stage = INIT-02
Run next_stage = INIT-03
```

---

## 14. INIT-03 — Generate World and time rules

### 14.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `initial_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `init_world_builder` |
| logical owner | `INIT-03` |
| response Schema | INIT-03 World candidate |
| next stage | `INIT-04` |

### 14.2 Inputs

```text
adopted Brief
valid Concept candidate
valid People candidate
Editorial profile
World contract rules
```

### 14.3 Output

```text
runtime/candidates/initial-design/world/v0001/world.json
runtime/candidates/initial-design/world/v0001/candidate-manifest.json
```

### 14.4 Validation

Code verifies:

```text
World and Temporal local-key uniqueness
global uniqueness against People local keys
normalized (kind,name) uniqueness
all Character starting Location forward references now resolve
resolved starting locations are kind=location
Temporal related keys resolve when their target type already exists
remaining forward Thread/Ending references are syntactically typed and deferred to INIT-04
initial Story time contract
no Story-clock order or scene position
no persistent IDs
```

A missing Character starting Location target is a conditional-rule failure and may consume a response-structure retry.

### 14.5 Success transition

```text
Candidate status = candidate_valid
Run last_completed_stage = INIT-03
Run next_stage = INIT-04
```

---

## 15. INIT-04 — Generate arcs, Major Threads, Ending criteria, and initial Knowledge

### 15.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `initial_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `init_arcs_builder` |
| logical owner | `INIT-04` |
| response Schema | INIT-04 Arc candidate |
| next stage | `INIT-05` |

### 15.2 Inputs

```text
adopted Brief
valid Concept candidate
valid People candidate
valid World candidate
Editorial profile
Publishing profile
Arc/Thread/Ending/Knowledge contract rules
```

### 15.3 Output

```text
runtime/candidates/initial-design/arcs/v0001/arcs.json
runtime/candidates/initial-design/arcs/v0001/candidate-manifest.json
```

### 15.4 Validation

Code verifies:

```text
protagonist arc targets the sole protagonist
Relationship arcs target known Relationships
turning-point sequences are contiguous
Major Thread local keys are globally unique
every Major Thread is required=true and scope=series
every Major Thread has non-null author truth and resolution condition
Ending local keys are globally unique
at least one required Ending criterion
every source_ending_text is an exact Brief-ending substring
Knowledge local keys are globally unique
Knowledge subjects resolve by compatible type
Knowledge fact triples are unique
initial Knowledge-state fact/audience references resolve
only non-default Knowledge states are explicit
all deferred Temporal related keys resolve
no persistent IDs
```

### 15.5 Success transition

```text
Candidate status = candidate_valid
Run last_completed_stage = INIT-04
Run next_stage = INIT-05
```

---

## 16. INIT-05 — Integrate complete Initial-design bundle

### 16.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_generate` |
| operation key | `initial_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `init_integrator_builder` |
| logical owner | `INIT-05` |
| response Schema | integrated Initial-design bundle |
| next stage | `INIT-06` |

### 16.2 Inputs

Exact immutable candidate versions:

```text
Concept
People
World
Arcs
adopted Brief
Editorial profile
Publishing profile
integration rules
```

### 16.3 Initial output

```text
runtime/candidates/initial-design/bundle/v0001/bundle.json
runtime/candidates/initial-design/bundle/v0001/candidate-manifest.json
```

### 16.4 Mechanical bundle validation

The integrated bundle is accepted only when it independently passes:

```text
exact concept/people/world/arcs root
all child Schemas
global local-key uniqueness
all local-reference resolution
type-compatible references
one protagonist
Brief person coverage
Character starting State completeness
Relationship starting State completeness
all Major Thread fixed conditions
all required Ending criteria
initial Knowledge fact uniqueness
initial Knowledge-state sparse/default rules
Story-time initialization
no persistent ID
no planning coordinate
no code-owned Canon metadata
```

This is response conditional validation.

An unresolved reference or incomplete State object is not deferred to INIT-ID and not treated as a semantic Review issue. It consumes response-structure retry budget.

### 16.5 Success transition

Candidate manifest:

```text
candidate_version = 1
candidate_status = candidate_valid
review_path = null
next_stage = INIT-06
```

Run state:

```text
last_completed_stage = INIT-05
next_stage = INIT-06
active_candidate_manifest_path =
  runtime/candidates/initial-design/bundle/v0001/candidate-manifest.json
```

---

# Part III: Review and revision

## 17. INIT-06 — Review integrated bundle

### 17.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_review` |
| operation key | `initial_design` |
| artifact class | `audit` |
| Context builder | `review_builder` |
| reviewed artifact role | `initial_design` |
| candidate owner | `INIT-05` |
| response Schema | generic Review content |
| next stage | derived from Review and revision budget |

The reviewed bundle remains a `candidate`. The Review file is an `audit` artifact.

### 17.2 Inputs

```text
active bundle candidate version
bundle candidate SHA-256
exact INIT-05 generation Context snapshot
private Initial-design Review extensions
Initial-design review rules
prior Review only when this is a revised bundle
```

The candidate hash in Review context must equal the active Candidate manifest.

### 17.3 Output

Within the active version directory:

```text
review.json
```

Example:

```text
runtime/candidates/initial-design/bundle/v0001/review.json
```

The Candidate manifest is atomically updated with the Review path/hash.

### 17.4 Required Review coverage

The reviewer must assess at least:

```text
Brief fidelity
Concept coherence
protagonist and key-person coverage
Character fixed facts and starting State
Relationship direction and starting State
World and Temporal consistency
Major Thread trackability and resolution conditions
Ending criterion auditability
Knowledge facts, safe labels, and initial audience states
arc compatibility
disclosure risks
genre and reader promise
initial Story-time feasibility
```

### 17.5 Structural and semantic distinction

Invalid Review JSON or Issue structure:

```text
response-structure retry
```

Valid Review with issues:

```text
semantic result
no response retry
```

Valid Review with no issues:

```text
candidate becomes ready_for_adoption
next = INIT-ID
```

---

## 18. INIT-REV — Replace integrated bundle

### 18.1 Stage definition

| property | contract |
|---|---|
| processor | `llm_revise` |
| operation key | `initial_design` |
| artifact class | `candidate` plus separate `audit` |
| Context builder | `revision_builder` |
| logical candidate owner | remains `INIT-05` |
| response Schema | complete integrated Initial-design bundle |
| next stage | `INIT-06` |

### 18.2 Run condition

INIT-REV runs only when:

```text
active Review status = issues_found
revision_rounds_used < max_revision_rounds
Candidate manifest durable routing status = revision_required
```

### 18.3 Inputs

```text
complete active bundle
complete saved Review
exact INIT-05 generator Context payload
replacement contract rules
revision_round = prior revision_rounds_used + 1
```

### 18.4 Output version

For revision round `r`, code creates:

```text
candidate_version = r + 1
version directory = v(candidate_version padded to four digits)
```

Example first revision:

```text
runtime/candidates/initial-design/bundle/v0002/bundle.json
runtime/candidates/initial-design/bundle/v0002/candidate-manifest.json
```

The new version contains no `review.json` until INIT-06 reviews it.

### 18.5 Validation

The revision response must be:

```text
one complete replacement bundle
exact INIT-05 Schema
mechanically cross-reference valid
Brief-compatible
free of patches, diffs, or omitted unchanged fields
```

A structurally invalid revision response does not create `vNNNN`.

### 18.6 New Candidate manifest

The new manifest copies immutable logical-owner and input identity required by Runtime and sets:

```text
operation_id = INIT-05
processor_type = llm_generate
candidate_version = previous + 1
revision_rounds_used = previous + 1
candidate_status = candidate_valid
candidate_path = new bundle path
candidate_sha256 = new hash
review_path = null
review_sha256 = null
last_call_id = accepted INIT-REV Call ID
next_stage = INIT-06
```

The previous version remains frozen with its Review.

Run state moves `active_candidate_manifest_path` to the new version only after its bundle and manifest are durable.

---

## 19. Review routing and revision exhaustion

After one valid INIT-06 Review, code routes as follows.

### 19.1 No issues

Condition:

```text
review.issue_counts.total = 0
```

Durable result:

```text
candidate_status = ready_for_adoption
residual_issues_path = null
next_stage = INIT-ID
```

Run state:

```text
last_completed_stage = INIT-06
next_stage = INIT-ID
```

### 19.2 Issues and revision remains

Condition:

```text
review.issue_counts.total > 0
revision_rounds_used < max_revision_rounds
```

Durable result:

```text
candidate_status = revision_required
next_stage = INIT-REV
```

Run state:

```text
last_completed_stage = INIT-06
next_stage = INIT-REV
```

### 19.3 Issues and revision exhausted

Condition:

```text
review.issue_counts.total > 0
revision_rounds_used >= max_revision_rounds
```

Code:

1. durably marks the active version `exhausted`;
2. appends one residual-issue JSONL record per Issue;
3. records the residual path/hash information required by the Candidate manifest;
4. durably marks the candidate `ready_for_adoption`;
5. sets `next_stage=INIT-ID`.

The final durable Candidate status is `ready_for_adoption`.

Mechanical defects can never use this route. Only a mechanically valid bundle with semantic Review issues may proceed.

### 19.4 `max_revision_rounds=0`

The initial `v0001` bundle is reviewed once.

- no issues: proceed;
- issues: write residual issues and proceed;
- INIT-REV is never called.

---

## 20. Review resume

When resuming INIT-06 routing:

- if `review.json` exists and its hash matches Candidate manifest, do not call the reviewer again;
- recompute routing from the saved Review and counters;
- if Review is absent or mismatched, call INIT-06 according to retry/budget rules;
- never read an older superseded version's Review as the active result.

When resuming INIT-REV:

- if the next version directory already contains a valid complete candidate and manifest, activate it and continue to INIT-06;
- if creation was partial, quarantine the incomplete version and repeat the revision call only if budget and call-audit state permit;
- never overwrite the previous reviewed version.

---

# Part IV: Genesis adoption

## 21. INIT-ID — Validate, allocate, and adopt Genesis

### 21.1 Stage definition

| property | contract |
|---|---|
| processor | `code` |
| artifact classes | `staged_internal`, `staged_internal_validation`, `adopted`, and separate `audit` |
| LLM call | none |
| source | active `ready_for_adoption` INIT-05 bundle version |
| successful next stage | `SERIES-01` |
| failure class | mechanical |

### 21.2 Preconditions

Under the workspace lock, code validates:

```text
Run-state next_stage = INIT-ID
no valid canon/HEAD exists
adopted Brief path/hash
active bundle Candidate manifest
candidate_status = ready_for_adoption
candidate path/hash
Review path/hash
Review targets current candidate version
revision counters and residual path
Effective-config and Run compatibility
counters exceed all observed IDs
no conflicting Genesis staging/adopted directory
```

The Review may contain issues. The bundle must still pass every mechanical data-contract rule.

### 21.3 Final pre-allocation validation

Before allocating any persistent ID, code performs a complete dry validation:

```text
all bundle child Schemas
global local-key uniqueness
all typed references
one protagonist and Brief coverage
all Character initial State rows
all Relationship initial State rows
all Major Thread initial State rows
all Knowledge definitions and sparse initial State
all enum and fixed-field conditions
all Canon/State boundary rules
initial Story clock
deterministic allocation order
expected output-key inventory
```

A failure stops without allocating IDs and indicates an implementation defect or corrupted candidate state.

### 21.4 Persistent-ID allocation

After dry validation succeeds, code allocates IDs in the exact order from `brief_and_initial.md`.

For every ID:

```text
persist counter increment
then use the reserved prior value
never roll back or reuse
```

The complete local-key mapping is built in memory and later written to the Genesis Commit manifest.

### 21.5 Genesis staging path

```text
.staging/genesis/<run-id>/
  initial-design.json
  generation/00000000/
    current-canon.json
    knowledge-items.json
    story-state.json
    evidence-index.json
    commit-manifest.json
    generation-manifest.json
  genesis-validation.json
```

No staged path appears in an adopted manifest.

---

## 22. Genesis construction order

Code constructs staged artifacts in this order.

### 22.1 Fixed records

Build:

```text
current-canon.json
knowledge-items.json
```

using:

```text
persistent IDs
record_origin = initial_design
record_lifecycle = active
created_scene_id = null
resolved persistent references
canonical ordering
```

### 22.2 Mutable initial values

Build `story-state.json` with:

```text
one Character state per Character
one Relationship state per Relationship
one Thread state per Major Thread
only non-default Knowledge-state rows
one complete Genesis Story clock
```

### 22.3 Evidence

Build:

```json
{"records":[]}
```

Initial design does not create prose Evidence.

### 22.4 Initial-design snapshot

Build `canon/initial-design.json` content with:

```text
Brief path/hash
accepted bundle hash
Concept
persistent-ID protagonist and Relationship arcs
complete adopted ID lists
genesis_commit_id = commit-00000000
```

### 22.5 Commit manifest

Build the Genesis Commit manifest with:

```text
commit_id = commit-00000000
commit_type = initial_design
no parent generation or scene
all four root hashes
complete local-key mappings
evidence_ids = []
```

### 22.6 Generation manifest

Build the Genesis Generation manifest with:

```text
generation_id = 00000000
commit_id = commit-00000000
parent_generation_id = null
current_order = 0
four root paths/hashes
Commit-manifest path/hash
no source Scene
```

The Generation manifest does not hash itself.

---

## 23. Genesis staged validation

`genesis-validation.json` uses artifact class `staged_internal_validation`.

It contains:

```text
schema_version
run_id
accepted_bundle_path
accepted_bundle_sha256
checks
all_checks_pass
staged_file_refs
created_at
```

Each `checks` row contains:

```text
check_id
status = pass | fail
artifact_path
artifact_sha256
message
```

Minimum checks:

```text
Brief and bundle hashes
expected file set
canonical JSON parsing
all root Schemas
unknown-field rejection
persistent-ID format and uniqueness
complete local-key mapping
all references resolve
all Character/Relationship/Thread State rows
Knowledge sparse defaults
Story-clock Genesis constants
Canon/State forbidden duplication
root hashes
Commit/Generation cross-hashes
initial-design ID lists
no placeholder hash
no staging/checkpoint path in staged manifests
```

INIT-ID adoption requires `all_checks_pass=true`.

The validation file is not copied into the adopted generation. Its final immutable copy is retained as a unique code-operation audit reference.

---

## 24. Genesis adoption transaction

After staged validation passes:

1. `fsync` all staged files and directories;
2. atomically rename:
   ```text
   .staging/genesis/<run-id>/generation/00000000
   →
   canon/generations/00000000
   ```
3. atomically replace staged `initial-design.json` into:
   ```text
   canon/initial-design.json
   ```
4. revalidate adopted generation and Initial-design hashes;
5. atomically write:
   ```text
   canon/HEAD = "00000000\n"
   ```
6. atomically update Run state:
   - `last_completed_stage=INIT-ID`;
   - `next_stage=SERIES-01`;
   - `current_head_generation=00000000`;
   - `last_commit_id=commit-00000000`;
   - `active_candidate_manifest_path=null`;
   - `run_status=running`;
7. write the successful INIT-ID operation audit;
8. remove the remaining Genesis staging directory.

`canon/HEAD` is the adoption point.

---

## 25. Genesis crash semantics

### 25.1 Before generation rename

Only staging exists.

Startup quarantines or removes abandoned staging after validating it is not adopted.

### 25.2 After generation rename but before `canon/HEAD`

The generation is not adopted.

Startup quarantines:

```text
HEAD-unreachable generation 00000000
unreferenced canon/initial-design.json when present
```

It never promotes the generation by inference.

### 25.3 After `canon/HEAD` but before Run-state update

Genesis is adopted.

Startup:

- validates HEAD generation and Initial-design snapshot;
- reconciles Run state to `INIT-ID` completed;
- sets next stage `SERIES-01`;
- cleans remaining staging.

### 25.4 Counter gaps

If IDs were allocated before a later failure, gaps remain.

Resume rebuilds from the active bundle using new IDs. Allocated but unadopted IDs are never reused.

---

## 26. INIT-ID postconditions

A successful INIT-ID guarantees:

```text
canon/HEAD contains 00000000
Generation 00000000 validates
Commit commit-00000000 validates
current_order = 0
successful_scene_commits = 0
all Brief people resolve to Character IDs
all Character starting Locations resolve
all Relationship endpoints resolve
all Temporal related IDs resolve
all Major Thread State rows are open/0
all initial Knowledge State rows are non-default
Story-clock position fields are null
Evidence index is empty
Initial-design snapshot points to all adopted IDs
Run state and HEAD agree
```

SERIES-01 must not start until all postconditions pass.

---

# Part V: Stage transition matrix

## 27. Normal transitions

| current stage | condition | next stage |
|---|---|---|
| `INPUT-01` | Brief mode valid | `INIT-01` |
| `INPUT-01` | Keywords mode valid | `INPUT-02` |
| `INPUT-02` | structurally valid Brief candidate | `INPUT-03` |
| `INPUT-03` | adopted Brief valid | `INIT-01` |
| `INIT-01` | valid Concept | `INIT-02` |
| `INIT-02` | valid People | `INIT-03` |
| `INIT-03` | valid World | `INIT-04` |
| `INIT-04` | valid Arcs | `INIT-05` |
| `INIT-05` | valid integrated bundle | `INIT-06` |
| `INIT-06` | no issues | `INIT-ID` |
| `INIT-06` | issues and revision remains | `INIT-REV` |
| `INIT-06` | issues and revision exhausted | `INIT-ID` |
| `INIT-REV` | valid complete replacement | `INIT-06` |
| `INIT-ID` | Genesis adopted | `SERIES-01` |

No other normal transition is permitted.

---

## 28. Error transitions

| failure | stage result |
|---|---|
| invalid CLI/config/bootstrap source | no resumable run; fail invocation |
| transport retries exhausted | `run_status=failed`, no automatic next stage |
| response-structure retries exhausted | `run_status=failed`, no automatic next stage |
| Review returns semantic issues | route by revision budget; not failed |
| residual semantic issues after exhaustion | proceed to INIT-ID |
| mechanical bundle validation fails | failed; never proceed by exhaustion |
| INIT-ID staged validation fails | failed; HEAD unchanged |
| pointer/adopted hash mismatch | failed and quarantine/recovery required |
| budget preflight fails | `run_status=stopped`, `stop_reason_code=budget_exhausted` |
| explicit user stop at safe boundary | `run_status=stopped`, `stop_reason_code=user_stop` |

A user stop does not interrupt an atomic file replacement or Genesis pointer transaction.

---

## 29. Stage completion rule

A stage is not complete merely because an LLM response arrived.

A stage is complete only when:

```text
its output artifact exists
its canonical hash is known
its Candidate/Review/Run manifest is durable
all stage-specific validation passes
Run state atomically records last_completed_stage and next_stage
```

For INIT-ID, completion additionally requires valid `canon/HEAD`.

---

## 30. Resume-source matrix

| stage to resume | authoritative source |
|---|---|
| `INPUT-01` | no resume before adopted input source |
| `INPUT-02` | `input/keywords.json`, INPUT-02 active Candidate manifest |
| `INPUT-03` | valid INPUT-02 Candidate manifest and candidate |
| `INIT-01` | adopted Brief and INIT-01 Candidate manifest if already valid |
| `INIT-02` | adopted Brief, Concept Candidate manifest, People Candidate manifest if already valid |
| `INIT-03` | prior candidate manifests, World Candidate manifest if already valid |
| `INIT-04` | prior candidate manifests, Arcs Candidate manifest if already valid |
| `INIT-05` | all four candidate manifests, Bundle Candidate manifest if already valid |
| `INIT-06` | active Bundle Candidate manifest and `review.json` when valid |
| `INIT-REV` | active reviewed Bundle version and immutable Revision Context snapshot |
| `INIT-ID` | active ready Bundle version, Review, residual audit when applicable |
| `SERIES-01` after crash | valid HEAD and reconciled Run state |

Audit files alone are never listed as a resume source.

---

## 31. Staleness rules

Before Genesis there is no adopted generation, so HEAD staleness does not apply to INIT candidates.

The following still invalidate a candidate:

```text
adopted Brief hash changed
Effective-config compatibility changed
prompt bundle changed
Schema bundle changed
candidate dependency path/hash changed
Context snapshot hash changed
candidate or Review hash mismatch
```

An adopted Brief is immutable. A change requires a new run/workspace, not candidate rebase.

---

## 32. Required operation audits

Code writes unique operation-audit records for at least:

```text
run bootstrap
INPUT-01 adopted source
INPUT-03 adopted Brief
candidate version activated
Review routing decision
revision version superseded
residual issues recorded
INIT-ID pre-allocation validation
persistent-ID allocation summary
Genesis staged validation
Genesis adopted
Genesis staging quarantined
Run-state reconciliation after Genesis crash
```

The audit message may include counts and hashes but not credential values or raw private content.

---

## 33. Forbidden implementation shortcuts

Forbidden:

```text
one directory with overwritten bundle.json and review.json
selecting a candidate by filesystem modification time
using audit response as candidate recovery
putting INIT-01 through INIT-04 into one undocumented free-form bundle
reviewing a mechanically invalid bundle
allowing INIT-ID to repair missing fields
allocating IDs before complete dry validation
reusing IDs after failed staging
writing HEAD before generation durability
treating review issues as response-structure errors
retrying Review until issues are empty
changing the Brief during INIT revision
persisting LLM-generated timestamps or hashes
writing a Review as artifact class "review candidate"
writing one path with artifact class "adopted/audit"
```

---

## 34. Mechanical acceptance conditions

An implementation of this pipeline is acceptable only when tests demonstrate:

```text
exactly one input mode
Brief-mode INPUT-02/03 skip
Keywords-mode full input route
INPUT-01 adopted source hash
INPUT-02 exact Brief candidate
INPUT-03 adopted Brief metadata and source hash
versioned candidate directories
immutable superseded candidate/review versions
logical owner retained across revision
Candidate-manifest-only resume
INIT stage dependency hashes
INIT-01 exact Concept route
INIT-02 Brief-person and Relationship validation
INIT-03 forward Location resolution
INIT-04 Thread/Ending/Knowledge validation
INIT-05 complete cross-reference validation
mechanically invalid bundle never reaches Review
INIT-06 generic Issue Review
semantic issue not response-retried
whole-bundle INIT-REV replacement
revision version activation after durability
zero revision-round behavior
residual Issue recording after exhaustion
mechanical defect never adopted by exhaustion
deterministic pre-allocation validation
counter persistence before ID use
complete Genesis local-key mapping
complete Canon/Knowledge/State construction
empty Genesis Evidence index
Genesis Commit and Generation hashes
staged validation before adoption
HEAD written last
crash behavior before and after HEAD
Run-state reconciliation
candidate and active-path clearing after Genesis
canonical artifact-class values
unknown transition rejection
```
