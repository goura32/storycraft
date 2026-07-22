# Runtime and recovery

This document is the normative operational contract for Storycraft startup, single-writer locking, durable stage boundaries, resume, crash reconciliation, transaction recovery, budget stop/resume, orphan quarantine, and explicit manual-intervention boundaries.

Field-level Runtime records are defined by [`contracts/ledger/runtime_records.md`](contracts/ledger/runtime_records.md). Managed paths are defined by [`workspace_layout.md`](workspace_layout.md). Stage-specific transitions are defined by [`pipeline_contracts.md`](pipeline_contracts.md) and the documents under [`contracts/pipeline/`](contracts/pipeline/). Configuration compatibility and budget behavior are defined by [`configuration_contracts.md`](configuration_contracts.md). Review, LLM-call audit, Completion audit, and Publication Gate records are defined by [`contracts/data/review_and_audit.md`](contracts/data/review_and_audit.md).

This document does not redefine those JSON Schemas. It defines how the implementation uses them when a process starts, stops, crashes, resumes, or discovers inconsistent durable files.

---

## 1. Runtime principles

### 1.1 Durable artifacts, not process memory

After a process exits, only durable workspace artifacts have authority.

The implementation must not depend on:

```text
in-memory stage variables
in-memory provider response
in-memory retry count
in-memory ID reservation
in-memory hash
in-memory transaction route
in-memory "last successful step"
```

Every resumable fact must be represented by an authoritative file defined by the Runtime or Pipeline contracts.

### 1.2 Pointer reachability

Adoption is determined by pointer and manifest reachability.

```text
canon/HEAD
→ current Generation
→ Commit
→ conditional Scene or Volume Handoff

output/CURRENT
→ current Publication
→ Publication manifest
→ complete final file set
```

A complete-looking directory outside these graphs is not adopted.

### 1.3 No inference from recency

Recovery must never select a file by:

```text
newest modification time
newest creation time
highest numeric ID alone
last directory returned by the filesystem
largest file
first valid JSON
most plausible story content
```

### 1.4 Single writer

All mutation and recovery actions require the workspace-wide lock.

Read-only tools may inspect without the lock only when they:

- tolerate atomic pointer changes;
- do not claim a multi-file snapshot unless they validate one;
- never mutate or quarantine content.

### 1.5 Idempotent durable boundaries

A stage boundary is idempotent when repeating its startup reconciliation:

- does not allocate a new ID;
- does not call an LLM;
- does not alter an adopted artifact;
- produces the same Run-state conclusion.

New semantic work begins only after reconciliation has identified the exact next stage.

### 1.6 Never repair story meaning during recovery

Recovery may repair execution metadata or resume a transaction.

It must not:

```text
invent missing story fields
change a candidate's meaning
rewrite prose
change a Review result
alter Canon to fit a delta
alter a plan to fit adopted prose
mark an incomplete Completion audit complete
```

Story-semantic correction requires the normal generation/revision pipeline or explicit human intervention.

---

## 2. Recovery action classes

Every startup finding is assigned exactly one action class.

### 2.1 `reconcile`

Use when an authoritative adoption or checkpoint boundary completed, but Run state is behind.

Examples:

```text
HEAD changed but Run state still says COMMIT-04
CURRENT changed but Run state is not completed
Checkpoint manifest advanced but Run state is behind
adopted immutable plan exists but Run state still points to its adoption stage
```

Reconciliation performs no LLM call and no new ID allocation.

### 2.2 `resume`

Use when an unadopted transaction has a complete valid resume manifest.

Examples:

```text
active Candidate manifest and candidate are valid
valid Checkpoint manifest identifies the frozen Scene phase
complete Scene transaction staging is referenced by COMMIT_PREPARED
complete Planning staging remains before final-plan move
finalized Publication staging and passing Gate remain before OUT-03
```

### 2.3 `regenerate`

Use when a candidate-level artifact is missing, stale, or untrusted, but an earlier adopted/checkpoint authority is valid.

Examples:

```text
candidate file exists without a valid Candidate manifest
Candidate manifest hash mismatch
Review exists without a manifest reference
provider call succeeded in audit but candidate was never durably saved
candidate source generation changed
```

Regeneration creates a new candidate version and may make a new provider call.

It never reconstructs candidate content from raw LLM-call audit.

### 2.4 `quarantine`

Use when content is not reachable from an adopted pointer or valid resume manifest and cannot safely be used.

Examples:

```text
HEAD-unreachable Generation
unreferenced adopted-looking Scene
standalone Handoff with no Handoff Commit
partial candidate version
unreferenced later-phase checkpoint file
abandoned staging
unadopted Publication directory
```

### 2.5 `explicit_recovery`

Use when an operation can be completed safely but requires deliberate operator authorization because a pointer-changing boundary was partially crossed.

Version-1 primary case:

```text
Publication directory was renamed to publications/<id>
but output/CURRENT was not changed
```

Explicit OUT-03 recovery is permitted only with the original passing Gate and exact rename-stable snapshot.

### 2.6 `manual_intervention`

Use when automatic correctness cannot be established.

Examples:

```text
invalid canon/HEAD target
invalid output/CURRENT target
counter lower than observed allocated IDs
immutable configuration mismatch without supported migration
two conflicting final plans at one canonical path
both staging and final Publication roots exist
adopted manifest hash graph conflict
valid semantic Completion result = incomplete
```

---

## 3. Durable boundary hierarchy

When files disagree, the implementation uses this hierarchy.

### 3.1 Story adoption hierarchy

```text
canon/HEAD
HEAD Generation manifest
HEAD Commit manifest
HEAD conditional source artifact
Generation root files
```

A lower-level file cannot override a higher-level valid pointer/manifest decision.

### 3.2 Publication adoption hierarchy

```text
output/CURRENT
CURRENT Publication manifest
Publication files listed by the manifest
Publication Validation
external Publication Gate
```

The external Gate proves that publication was eligible for adoption. `output/CURRENT` proves that adoption occurred.

### 3.3 Active execution hierarchy

```text
valid adopted pointers
Run state
active Checkpoint manifest
active Candidate manifest
transaction manifest referenced by checkpoint/run state
versioned candidate files
Context snapshots
audit files
normal logs
```

Special rule:

- a valid adopted pointer overrides a Run state that is behind;
- a valid Checkpoint manifest may reconcile a Run state that is behind for the same deterministically derived Scene target;
- a Candidate file without a valid active Candidate manifest is not promoted.

### 3.4 Audit position

Audit artifacts prove what was attempted or decided.

They do not become:

```text
candidate content
Review resume content
checkpoint content
Canon
Story state
publication payload
```

---

## 4. Process startup modes

The runtime recognizes four conceptual startup modes.

### 4.1 New run

Conditions:

```text
no valid Run manifest
no valid canon/HEAD
no adopted input for another story
caller supplies a supported input source
```

The input pipeline performs bootstrap.

### 4.2 Normal resume

Conditions:

```text
valid Run manifest exists
run_status is initialized, running, or paused
or a stopped/failed run has received explicit resume authorization
workspace compatibility passes
```

Startup reconciles and continues from an authoritative boundary.

### 4.3 Explicit recovery

Used only for a registered partial-adoption case or a registered recoverable failed state.

The operator action must identify:

```text
workspace
run ID
recovery category
target transaction or Publication ID when applicable
```

A generic “use whatever looks latest” recovery is forbidden.

### 4.4 Read-only inspection

A read-only command:

- does not take ownership of a stale transaction;
- does not change Run state;
- does not quarantine;
- may report inconsistencies;
- must label a multi-file result as unstable unless it validates a pointer-selected snapshot.

---

## 5. Workspace lock

### 5.1 Lock path

```text
.storycraft.lock
```

### 5.2 Required lock scope

The exclusive lock is required before changing:

```text
runtime/run-state.json
runtime/counters.json
runtime/effective-config.json
runtime/candidates/
runtime/checkpoints/
runtime/orphans/
canon/
plans/
artifacts/
audit/residual-issues.jsonl
.staging/
publications/
output/CURRENT
```

Unique immutable LLM-call and operation-audit files are also written under the lock in version 1 so their counters and filenames remain consistent.

### 5.3 Acquisition order

The process:

1. resolves the workspace root securely;
2. opens the canonical lock path without following an external symlink;
3. acquires an OS-supported exclusive lock;
4. validates optional diagnostic lock content;
5. writes current diagnostic metadata only after ownership is obtained;
6. performs startup reconciliation.

### 5.4 Diagnostic content

Lock-file content may include:

```text
process ID
host name
run ID
acquired_at
code version
```

It is not proof of ownership.

The operating-system lock is authoritative.

### 5.5 Stale-looking lock

A lock is not removed because:

```text
its timestamp is old
its process ID is not found in a local namespace
its host name differs
the previous process probably crashed
```

The implementation uses platform-appropriate lock semantics.

If ownership cannot be established safely, startup stops with manual intervention.

### 5.6 Network filesystems

Network and distributed filesystems are outside version 1.

Startup must reject or warn-and-stop when atomic rename, file locking, or durability semantics cannot meet the configured workspace requirements.

It must not silently downgrade to best-effort locking.

---

## 6. Startup security preflight

Before trusting workspace content, code validates:

```text
workspace root is a directory
managed top-level names have canonical case
no managed path component escapes through symlink, junction, or reparse point
no absolute persisted managed path is accepted
no path traversal survives normalization
temporary-file names are not mistaken for final artifacts
```

A security-boundary violation is a mechanical failure.

Recovery does not follow a suspicious path to inspect whether the content “looks correct.”

---

## 7. Startup validation phases

Startup proceeds through ordered phases.

### 7.1 Phase A — foundational records

Validate when present:

```text
runtime/run-manifest.json
runtime/effective-config.json
runtime/counters.json
runtime/run-state.json
```

A malformed Run state does not invalidate a valid adopted HEAD or CURRENT pointer. It prevents candidate-level resume until Run state is reconstructed or reset from a durable adopted/checkpoint boundary.

### 7.2 Phase B — adopted story pointer

Validate:

```text
canon/HEAD
HEAD Generation directory
Generation manifest
Commit manifest
four root files
conditional Scene or Handoff source
```

### 7.3 Phase C — adopted publication pointer

Validate:

```text
output/CURRENT
CURRENT Publication directory
Publication manifest
Validation file
every listed file and hash
payload/content-set hashes
```

### 7.4 Phase D — Run-state comparison

Compare Run state to:

```text
HEAD generation
HEAD Commit
Story-clock current_order
output/CURRENT
current Publication
```

### 7.5 Phase E — active resume artifacts

Validate only the paths explicitly selected by Run state:

```text
active Candidate manifest
active Checkpoint manifest
referenced Context snapshots
referenced staged transaction
```

### 7.6 Phase F — deterministic expected-path reconciliation

When Run state is behind or partially missing, inspect only canonical paths derived from valid adopted plans and pointers.

Examples:

```text
the exact expected Scene checkpoint path
the exact expected adopted Series/Volume/Chapter plan path
the exact Handoff path for the HEAD Handoff commit
the exact Publication directory named by CURRENT
```

### 7.7 Phase G — orphan scan

After authority and resume paths are known, scan unmanaged leftovers and quarantine items proven unreferenced.

Quarantine must not run before reachability analysis.

---

# Part I: Adopted pointer validation

## 8. `canon/HEAD` validation

### 8.1 Missing HEAD

A missing HEAD is valid only before Genesis adoption.

If Run state claims Genesis or a later stage completed, the workspace is inconsistent.

### 8.2 HEAD bytes

Valid bytes:

```text
<eight-digit-generation-id>\n
```

No BOM, whitespace, comment, or additional line is permitted.

### 8.3 HEAD target

The named Generation directory must contain exactly:

```text
current-canon.json
knowledge-items.json
story-state.json
evidence-index.json
commit-manifest.json
generation-manifest.json
```

### 8.4 Manifest graph

Code validates:

```text
Generation ID equals directory
Generation Commit ID suffix equals Generation ID
Commit after_generation equals Generation ID
Commit root hashes equal Generation root hashes
Generation Commit-manifest path/hash
parent Generation when non-null
current_order equality
commit-type conditional fields
```

### 8.5 Commit-type branch

#### `initial_design`

Required:

```text
generation_id = 00000000
parent_generation_id = null
no Scene source
no Handoff source
current_order = 0
```

#### `scene`

Required:

```text
source Scene ID/path/hash
adopted Scene manifest
committed delta
Story-clock current_order = parent + 1
```

#### `volume_handoff`

Required:

```text
source Handoff path/hash
no Scene source
Story-clock current_order = parent current_order
only permitted volume_disposition changes
```

### 8.6 Invalid HEAD

If HEAD bytes or its reachable graph are invalid:

- do not choose another Generation;
- do not use the numerically highest Generation;
- do not rewrite HEAD automatically;
- set/retain a mechanical failure state when Run state is writable;
- require manual intervention.

---

## 9. `output/CURRENT` validation

### 9.1 Missing CURRENT

A missing CURRENT is valid before the first publication.

It is invalid when Run state claims:

```text
last_completed_stage = OUT-03
run_status = completed
current_publication_id != null
```

### 9.2 CURRENT bytes

Valid bytes:

```text
<publication-id>\n
```

### 9.3 CURRENT target

The named directory must contain:

```text
publication-manifest.json
every file listed by the Manifest
```

It must not contain:

```text
publication-build-manifest.json
```

### 9.4 Hash validation

Code validates:

```text
Publication ID
source generation identity
Validation relative path/hash
safe Completion-report relative path/hash
files array
content_set_sha256
Validation payload_set_sha256
all file hashes/sizes/media types/roles
```

### 9.5 Invalid CURRENT

If CURRENT is invalid:

- do not select another publication;
- do not select the highest Publication ID;
- do not use a passing Gate to change CURRENT automatically during ordinary startup;
- stop mechanically.

An explicit registered repair procedure is required.

---

## 10. Pointer and Run-state reconciliation

### 10.1 HEAD ahead of Run state

When valid HEAD proves that Genesis, a Scene commit, or a Handoff commit was adopted:

Code may update:

```text
current_head_generation
last_commit_id
successful_scene_commits
last_completed_stage
next_stage
target coordinates
scene_phase
active Candidate/Checkpoint paths
```

The route must be derived from immutable adopted plans and the HEAD Commit branch.

### 10.2 Run state ahead of HEAD

When Run state claims an adopted Generation that HEAD does not select:

- Run state is not trusted;
- inspect the stage's valid staging/checkpoint transaction;
- if HEAD was never changed, treat final-looking content as unadopted;
- reconcile Run state backward to the last valid durable boundary or stop if ambiguity remains.

### 10.3 CURRENT ahead of Run state

When CURRENT points to a valid publication but Run state is not completed:

Code reconciles:

```text
last_completed_stage = OUT-03
next_stage = null
current_publication_id = CURRENT
run_status = completed
stop_reason_code = completed
```

### 10.4 Run state ahead of CURRENT

When Run state claims completed but CURRENT is missing or different:

- do not trust Run state;
- do not rewrite CURRENT from Run state alone;
- inspect a valid OUT-03 transaction/Gate only under explicit recovery;
- otherwise stop mechanically.

---

# Part II: Run state and counters

## 11. Run-state validation

Code validates:

```text
state_version
state_revision
run ID
run-status transition
stage IDs
target/coordinate consistency
scene-phase consistency
active Candidate/Checkpoint paths
Brief path/hash
HEAD/Commit identity
CURRENT identity
Effective-config hash
stop fields
```

### 11.1 State revision

Every successful atomic Run-state replacement increments:

```text
state_revision = prior + 1
```

A non-increasing replacement detected by surrounding transaction evidence is a mechanical defect.

### 11.2 Run status

Allowed statuses are defined by `runtime_records.md`.

Operational meaning:

| status | automatic continuation |
|---|---|
| `initialized` | yes after bootstrap validation |
| `running` | yes |
| `paused` | no until explicit resume |
| `stopped` | no until explicit resume |
| `failed` | no until explicit recoverability validation |
| `completed` | never |

### 11.3 Crash while `running`

A process crash normally leaves:

```text
run_status = running
```

This is not itself an error.

Startup reconciles durable files and continues when all checks pass.

### 11.4 Null next stage

`next_stage=null` is valid only for:

```text
completed
terminal stopped state
terminal failed state
```

A running/initialized Run state with null `next_stage` is invalid.

---

## 12. Counter validation

### 12.1 Persist-before-use

For every ID:

```text
read next value
persist increment
use reserved previous value
```

A crash may create a gap.

A gap is valid.

### 12.2 Observed-ID scan

Startup calculates maxima from authoritative and retained allocation evidence.

Sources include:

```text
adopted Generations and manifests
adopted Scenes and Handoffs
valid staging transaction manifests
valid checkpoint Commit plan where IDs are already allocated by a later stage
candidate/audit IDs where the applicable counter allocates them
LLM-call audit filenames
Publication directories and Gates
```

### 12.3 Lower counter

If:

```text
next_counter <= observed maximum
```

the workspace is mechanically corrupt.

Code must not silently set the counter to `maximum + 1`.

Explicit counter repair requires:

1. complete workspace scan;
2. a repair report;
3. operator authorization;
4. atomic counter replacement;
5. immutable operation audit;
6. no reuse of any observed or potentially allocated value.

### 12.4 Higher counter

A counter greater than observed maximum is valid.

It represents:

```text
failed transaction allocation
provider call without saved candidate
quarantined unadopted content
intentional non-reuse
```

### 12.5 Usage counters

Usage counters are monotonic:

```text
llm_calls_used
transport_retries_used
response_structure_retries_used
revision_rounds_used
completion_audit_attempts_used
input_tokens_used
output_tokens_used
estimated_cost_used
active_elapsed_seconds
successful_scene_commits
```

Startup must not lower them to match surviving artifacts.

### 12.6 Scene-count invariant

After a valid HEAD is established:

```text
successful_scene_commits
=
HEAD story_clock.current_order
```

If Run counters are behind after an adopted Scene commit, reconciliation may increase `successful_scene_commits` to the exact HEAD order.

It must not decrease it.

A value greater than HEAD order is a mechanical inconsistency unless an explicit audit proves an adopted pointer rollback occurred through a supported recovery procedure. Version 1 has no automatic pointer rollback.

---

## 13. Effective-config compatibility

Before resume, code compares the current materialized Effective config and immutable Run-manifest identity.

### 13.1 Immutable mismatch

Examples:

```text
provider
model
structured-output mode
Editorial profile
Publishing profile
semantic token limits
prompt bundle
Schema bundle
Context-builder version
workspace version
immutable fingerprint
```

Unsupported mismatch causes a mechanical stop.

### 13.2 Permitted resume change

Only fields explicitly classified as resume-mutable or resume-increase-only may change.

Procedure:

1. validate the proposed new Effective config;
2. compare every field by mutability class;
3. write a config-change operation audit;
4. atomically replace `runtime/effective-config.json`;
5. atomically update Run-state config hash;
6. retain the Run manifest and immutable fingerprint;
7. re-run budget and Context compatibility checks.

### 13.3 Credential rotation

Credential values are external.

A new value under the same configured environment-variable name may be used on resume.

It does not modify persisted config and is never audited verbatim.

### 13.4 Version migration

Schema, workspace, or code-version migration is outside normal resume.

A migration tool must be separately specified and must never run implicitly during ordinary startup.

---

# Part III: Candidate and Context recovery

## 14. Active Candidate recovery

### 14.1 Valid active Candidate

A Run-state-selected Candidate is resumable only when:

```text
Candidate manifest Schema validates
manifest run/operation/target match Run state
candidate path stays in the same version directory
candidate file exists and hashes
Context snapshot path/hash validates
source artifacts still hash
candidate is not superseded
candidate status and next stage are consistent
```

### 14.2 Candidate status routing

| status | recovery route |
|---|---|
| `initialized` | no structurally valid candidate; repeat generation/revision call if allowed |
| `candidate_valid` | continue to Review |
| `reviewed` | validate Review and derive route |
| `revision_required` | continue to revision |
| `ready_for_adoption` | continue to checkpoint/adoption stage |
| `exhausted` | verify residual records, then normalize to ready/adoption route |
| `failed` | create a new version only through explicit retry/regeneration |

### 14.3 Candidate file without manifest

Do not create a manifest from the candidate file.

Actions:

```text
quarantine partial version
return to the prior authoritative source
create the next unused candidate version
```

### 14.4 Manifest without candidate

The version is invalid.

Quarantine the version and regenerate.

### 14.5 Candidate hash mismatch

Do not choose another file from the directory.

Quarantine the version and regenerate from the prior authority.

### 14.6 Candidate accepted in LLM audit but not saved

A successful provider response recorded in `audit/llm-calls/` is not candidate authority.

Startup:

- preserves the Call audit and usage counters;
- makes a new call with a new Call ID when budget permits;
- does not parse or promote the raw response body.

This may incur duplicate provider work. The rule prevents ambiguous audit-to-candidate promotion.

---

## 15. Review recovery

### 15.1 Valid referenced Review

A Review is reusable only when:

```text
Candidate manifest review path/hash match
Review candidate path/hash match the active candidate
Review input snapshot matches
Review operation/target/version match
Issue structure validates
```

Code derives the deterministic route without another Review call.

### 15.2 Review file without Candidate-manifest reference

Do not promote it.

Quarantine the unreferenced Review file or the incomplete version according to version integrity, then repeat Review.

### 15.3 Candidate manifest references missing Review

The Review boundary is incomplete.

Repeat Review if retry/budget permits.

### 15.4 Residual-issue append ambiguity

Before appending residual Issue records, code computes the exact canonical records and checks whether the same records are already durably present for:

```text
operation ID
target ID
candidate hash
Review hash
Issue ID
```

If all are present, do not append duplicates.

If only a subset is present:

- append the missing exact records under the lock;
- audit the reconciliation.

Conflicting duplicate records are mechanical corruption.

---

## 16. Candidate version recovery

### 16.1 New version number

When regeneration or revision is required, code chooses the next unused contiguous version number after validating all existing version directory names.

This is allocation of a new storage slot, not selection of candidate authority.

### 16.2 Partial next version

A directory containing any subset of:

```text
candidate
review.json
candidate-manifest.json
temporary files
```

without a valid complete Candidate version is quarantined.

The version number is not reused.

The next generation/revision creates the following version number.

### 16.3 Superseded history

Superseded valid versions are never deleted automatically.

They are not considered active unless Run state explicitly selects them and the candidate chain proves they were not superseded. A Run state pointing to a known superseded version is invalid and must fall back to a prior durable boundary.

### 16.4 Stale source

When a valid candidate's source hash changed:

- mark/freeze it as stale history through an operation audit;
- clear active Candidate path;
- regenerate from the owning generation stage;
- use the next version;
- do not increment semantic revision rounds for staleness regeneration.

---

## 17. Context-snapshot recovery

### 17.1 Valid snapshot

A Context snapshot is valid when:

```text
filename equals SHA-256 of canonical bytes
builder/version/operation/target match
source references exist and hash
Effective-config compatibility permits reuse
prompt and response-Schema versions match
token-budget record validates
```

### 17.2 Missing snapshot

A candidate whose manifest references a missing Context snapshot is not resumable for Review or Revision.

The candidate may remain history, but code regenerates from the prior authority.

### 17.3 Rebuild

A deterministic builder may rebuild a missing snapshot only when it produces the exact same hash.

If the rebuilt hash differs:

- do not alter the Candidate manifest;
- treat the candidate as stale/unrecoverable;
- generate a new candidate version.

### 17.4 Unreferenced snapshot

An unreferenced valid Context snapshot may remain as deduplicated cache/history.

It is not automatically selected.

Retention may delete it only when no retained manifest or audit references it.

---

# Part IV: Checkpoint recovery

## 18. Scene-checkpoint discovery

The exact expected Scene ID is derived from:

```text
valid HEAD
adopted plans
Run-state target when consistent
```

The canonical checkpoint path is then deterministic.

Startup does not scan all Scene checkpoint directories and choose one.

### 18.1 Valid selected checkpoint

A checkpoint is resumable when:

```text
Checkpoint manifest validates
Scene ID/path coordinates match
source generation equals current HEAD
source Generation-manifest hash matches
phase-required files exist and hash
Candidate-manifest references validate
no target Scene is already adopted
```

### 18.2 Run state behind checkpoint

When the exact expected Checkpoint manifest is valid and Run state is behind:

- reconcile Run state to the checkpoint phase;
- clear a superseded active Candidate path;
- continue from the phase's next stage;
- do not repeat completed LLM stages.

### 18.3 Run state ahead of checkpoint

If Run state claims a later Scene phase than the valid Checkpoint manifest:

- inspect a valid Scene transaction or adopted Scene;
- if neither proves the later phase, Run state is rolled back to the valid checkpoint phase through reconciliation;
- if ambiguity remains, stop mechanically.

### 18.4 Invalid Checkpoint manifest

Quarantine the entire checkpoint directory.

Return to:

```text
SC-01
```

using the current valid HEAD and adopted Chapter design.

Frozen-looking files are not promoted without the manifest.

---

## 19. Unreferenced checkpoint files

Examples:

```text
prose.md exists while phase = CARD_ACCEPTED
continuity-delta.json exists while phase = PROSE_FROZEN
commit-plan.json exists while phase = DELTA_ACCEPTED but no COMMIT-01 completion reference
```

Procedure:

1. validate the earlier manifest phase;
2. prove the extra file is not referenced by an adopted or staged transaction;
3. quarantine the extra file;
4. retain the valid earlier checkpoint;
5. resume from the phase's next stage.

The entire checkpoint is invalidated when the extra file indicates conflicting source/hash identity.

---

## 20. Checkpoint source-generation mismatch

If current HEAD differs from checkpoint source generation:

1. verify whether the target Scene was already adopted;
2. if adopted, treat checkpoint as cleanup residue;
3. otherwise write a checkpoint-invalidation audit;
4. quarantine the complete checkpoint directory;
5. clear active Candidate/Checkpoint paths;
6. derive the expected current Scene target;
7. restart from `SC-01`.

No Scene-card, prose, or candidate delta is rebased.

---

## 21. Checkpoint after adopted Scene

When the target Scene is validly adopted and HEAD-reachable:

- the checkpoint is no longer authoritative;
- remove it after validating adopted Scene and Run-state reconciliation;
- if cleanup cannot complete, leave it as identified cleanup residue rather than repeating the Scene pipeline.

A mismatching leftover checkpoint for an adopted Scene is quarantined.

---

# Part V: Transaction recovery

## 22. Genesis recovery

### 22.1 Staging only

When:

```text
.staging/genesis/<run-id> exists
canon/HEAD is absent
canon/generations/00000000 is absent
```

validate staged Genesis.

If complete and Run state identifies `INIT-ID`, resume the adoption transaction.

Otherwise quarantine staging.

### 22.2 Generation renamed, HEAD absent

`canon/generations/00000000` is unadopted.

Any staged or final-looking `canon/initial-design.json` associated with it is also unadopted.

Quarantine them.

Do not write HEAD by inference.

### 22.3 HEAD points to Genesis, Run state behind

Genesis is adopted.

Validate:

```text
Generation
Commit
initial-design snapshot
Brief references
```

Then reconcile Run state to `INIT-ID` completed and the exact next planning stage.

### 22.4 Conflicting Genesis

These require manual intervention:

```text
HEAD absent but multiple Genesis-looking roots
HEAD points to nonzero Generation without valid Genesis chain
different valid initial-design snapshot conflicts with HEAD Genesis Commit
```

---

## 23. Plan-adoption recovery

### 23.1 Staging before final move

A valid planning staging directory may resume only when:

```text
Run state identifies the exact adoption stage/target
active ready Candidate and Review validate
source HEAD/parent-plan hashes remain valid
plan-validation report passes
final plan path is absent
```

Otherwise quarantine staging.

### 23.2 Final plan exists, Run state behind

The final plan path is the planning adoption point.

When the file validates and matches the deterministic target/parent/source:

- reconcile Run state to the plan adoption postcondition;
- clear active Candidate path;
- remove staging.

### 23.3 Conflicting final plan

If a final canonical plan path contains different or invalid bytes:

- never overwrite it;
- stop mechanically;
- require manual intervention.

### 23.4 Future plan found

A valid-looking plan for a future target is not automatically adopted into execution order.

If it violates parent/entry ordering, quarantine or stop according to whether it is referenced by any valid adopted plan transaction.

---

## 24. Scene-commit recovery

Scene adoption point:

```text
canon/HEAD
```

The presence of final Generation/Scene directories before HEAD does not adopt them.

### 24.1 Before COMMIT-02 allocation

A passing `commit-plan.json` may be reused when:

```text
checkpoint remains DELTA_ACCEPTED
source HEAD remains unchanged
Commit plan hashes validate
no transaction IDs were allocated
```

Resume at `COMMIT-02`.

### 24.2 Allocated transaction staging

A staged transaction may resume when:

```text
Transaction manifest validates
Commit/Generation IDs match counters/history
merge plan validates
checkpoint and Commit plan hashes match
source HEAD unchanged
transaction status identifies a valid next COMMIT stage
```

Do not allocate replacement IDs for the same valid transaction.

### 24.3 Generation built, Scene not built

Resume at COMMIT-03 after revalidating staged roots and merge plan.

### 24.4 Transaction validated and checkpoint COMMIT_PREPARED

Resume at COMMIT-04.

### 24.5 Generation renamed, Scene not renamed, HEAD unchanged

The Generation is unadopted and unreachable.

Quarantine:

```text
Generation directory
remaining transaction staging
```

Return to a valid checkpoint boundary.

Allocated IDs remain consumed.

### 24.6 Generation and Scene renamed, HEAD unchanged

Both final-looking directories are unadopted.

Ordinary startup quarantines them.

It does not complete HEAD by inference.

### 24.7 HEAD changed, Run state behind

The Scene commit is adopted.

Validate:

```text
HEAD Generation
Scene Commit
Scene manifest
committed delta
root hashes
Story-clock order
route from immutable plans
```

Then reconcile Run state to the derived route and remove checkpoint/staging residue.

### 24.8 Partial adopted graph after HEAD

If HEAD points to a Generation whose required Scene artifact is missing or invalid:

- HEAD graph is invalid;
- do not roll HEAD backward automatically;
- require manual intervention.

---

## 25. Volume-handoff recovery

Handoff adoption point:

```text
canon/HEAD
```

### 25.1 Candidate/Review recovery

Uses the same versioned Candidate rules as planning and Scene families.

### 25.2 Staging before rename

A complete Handoff staging transaction may resume when:

```text
active ready Handoff candidate validates
source HEAD is still the final Scene generation
Handoff validation passes
allocated Commit/Generation IDs match transaction
final Handoff path and final Generation path are absent
```

### 25.3 Generation or Handoff placed, HEAD unchanged

The placed content is unadopted.

Quarantine it.

Do not write HEAD by inference.

### 25.4 HEAD changed, Run state behind

The Handoff commit is adopted.

Validate:

```text
Commit type = volume_handoff
Handoff hash/path
only Thread volume_disposition changed
Story clock/current_order unchanged
Generation hash graph
next Volume or Completion route
```

Then reconcile Run state.

### 25.5 Standalone Handoff

A Handoff file not referenced by a HEAD-reachable Handoff Commit is an orphan and never a planning authority.

---

## 26. Completion recovery

### 26.1 Passing precondition

A valid `completion-precondition.json` may be reused only when:

```text
source generation still equals HEAD
all source hashes remain valid
Completion Context snapshot hashes
all_checks_pass = true
```

### 26.2 Precondition failure

A failed precondition is a durable mechanical result.

Do not call the Completion auditor.

Resume requires fixing the underlying workspace and explicitly rerunning COMP-PRE.

### 26.3 Completion attempt ambiguity

A saved `attempt-NN.json` is reusable only when the Completion Candidate manifest selects it and its hash validates.

A raw successful LLM-call audit without a saved attempt is not promoted.

### 26.4 Valid incomplete audit

A structurally valid:

```text
overall_assessment = incomplete
```

is final for that Completion context.

It:

- is saved by COMP-SAVE;
- is not retried;
- may allow OUT-01/OUT-02 diagnostic publication staging;
- must fail COMP-PUBLISH;
- ends in `manual_intervention`.

### 26.5 Completion source changes

If HEAD changes after COMP-PRE or COMP-AUDIT:

- all Completion candidate/audit staging for the prior generation is stale;
- do not rebase;
- restart from COMP-PRE for the new final generation.

A previously accepted private audit remains immutable history.

---

## 27. Publication recovery

Publication adoption point:

```text
output/CURRENT
```

### 27.1 OUT-01 partial payload staging

If the provisional build manifest is missing or invalid:

- quarantine staging;
- allocate a new Publication ID for a new OUT-01 build;
- never reuse the Publication ID.

If the build manifest and every expected payload file validate, resume OUT-02.

### 27.2 OUT-02 validation failure

A failed Publication Validation is a durable mechanical result.

Do not create a passing Manifest or Gate.

After correcting the underlying implementation/data defect, start a new Publication ID. Version 1 does not mutate a failed finalized payload into a new publication transaction.

### 27.3 Finalized staging before Gate

When:

```text
publication-build-manifest.json is absent
Validation passes
Manifest and complete files validate
```

resume COMP-PUBLISH.

### 27.4 Passing Gate before rename

Resume OUT-03 only when the staging root reproduces:

```text
Validation hash
Manifest hash
payload_set_sha256
content_set_sha256
publication_snapshot_sha256
```

### 27.5 Directory renamed, CURRENT unchanged

The final directory is unadopted.

Ordinary startup does not publish it by inference.

Explicit OUT-03 recovery is permitted only when:

```text
Run state identifies exact OUT-03 and Publication ID
original passing Gate validates
staging root is absent
exact final root exists
CURRENT still equals Manifest current_pointer_before
final root reproduces publication_snapshot_sha256
no conflicting root exists
```

### 27.6 CURRENT changed, Run state behind

The publication is adopted.

Validate CURRENT target and reconcile Run state to completed.

### 27.7 Both staging and final roots exist

This is a mechanical conflict.

Do not delete or select either automatically.

Require manual intervention.

### 27.8 Final directory without Gate

A final Publication directory without its exact valid Gate is unadopted and cannot use explicit OUT-03 recovery.

Quarantine it after proving CURRENT does not reference it.

---

# Part VI: Provider-call and audit recovery

## 28. Provider-call crash points

### 28.1 Before Call-ID allocation

No call occurred.

The stage may start normally.

### 28.2 After Call-ID persistence, before request

The Call ID remains consumed.

If no provider attempt occurred, the next attempt uses a new Call ID.

### 28.3 Request sent, no complete audit outcome

The actual provider outcome may be unknowable.

Conservative behavior:

- preserve/increase consumed Call and elapsed-budget accounting;
- do not assume the provider did not bill;
- mark the attempt interrupted through a code/audit recovery record when possible;
- repeat with a new Call ID only when retry/budget permits.

### 28.4 Successful response audit, candidate missing

Do not promote audit response.

Repeat generation with a new Call ID.

### 28.5 Candidate durable, Run state behind

When Candidate file and Candidate manifest both validate:

- reconcile Run state to the Candidate manifest's next stage;
- do not call the provider again.

### 28.6 Review durable, manifest update incomplete

An unreferenced Review is not promoted under version-1 candidate-authority rules.

Repeat Review and retain/quarantine the unreferenced Review as appropriate.

---

## 29. Audit write recovery

### 29.1 Unique final audit file

A valid immutable audit file is retained.

It is never overwritten.

### 29.2 Temporary audit file

A temporary file not atomically placed at the unique final path:

- is not a valid audit record;
- is removed or quarantined;
- does not free or reuse the Call ID.

### 29.3 Filename collision

A final audit filename collision is mechanical corruption because Call IDs and operation filenames are unique.

Do not overwrite.

### 29.4 Gzip validation

LLM-call audit gzip must:

```text
decompress successfully
contain one canonical JSON object
contain no concatenated extra member
match filename Call/operation/target/role/attempt fields
```

An invalid audit may block budget reconciliation and require explicit recovery, but it is never used as candidate content.

---

## 30. Usage and budget reconciliation

### 30.1 Persist actual usage conservatively

When provider usage is available, counters use it.

When unavailable after a possibly sent call, use the registered tokenizer/fallback estimate and audit the source.

### 30.2 No counter refund

The runtime never refunds:

```text
Call count
retry count
token usage
estimated cost
active elapsed time
allocated IDs
```

because a candidate, transaction, or publication was later discarded.

### 30.3 Preflight after recovery

Before the next LLM call, recompute remaining budgets from persisted counters and current Effective config.

A recovered stage may stop for budget exhaustion even when the previous process intended to retry.

### 30.4 Audit-storage limit

When the audit-storage limit is reached:

- stop before the next provider call;
- do not disable required auditing silently;
- use `budget_exhausted` or the registered storage-limit detail;
- permit resume only after an allowed retention/config action.

---

# Part VII: Stop, pause, failure, and completion

## 31. Safe-boundary stop

A requested stop is honored only after the current atomic write/rename/pointer operation reaches a safe boundary.

Examples of indivisible boundaries:

```text
counter persist-before-use
candidate file plus Candidate-manifest transition
checkpoint artifact plus Checkpoint-manifest transition
Generation/Scene/Handoff rename sequence through pointer update
Publication rename through CURRENT update
Run-state atomic replacement
```

Code must not deliberately stop between a final directory rename and its pointer update.

A process crash may still occur there; transaction recovery handles it.

---

## 32. `paused`

`paused` means temporary operator-controlled suspension.

Requirements:

```text
next_stage remains known
stop_reason_code = null
authoritative resume artifacts remain valid
```

Resume requires explicit operator action and full compatibility validation.

Version 1 may omit a public pause command; if supported, these semantics apply.

---

## 33. `stopped`

Registered stop reasons include:

```text
user_stop
budget_exhausted
manual_intervention
```

### 33.1 User stop

Resume is allowed after:

- explicit request;
- workspace validation;
- unchanged or permitted config;
- exact durable boundary discovery.

### 33.2 Budget exhausted

Resume is allowed only when:

```text
a resume-increase-only budget was increased
or retention released required audit capacity
or no further LLM call is required and the prior stop detail permits code-only continuation
```

Budget counters remain unchanged.

### 33.3 Manual intervention

No automatic continuation.

A human or registered repair tool must resolve the stated condition and produce an audit trail.

A semantic Completion `incomplete` result uses this reason.

---

## 34. `failed`

`failed` represents a mechanical or provider-processing failure.

### 34.1 Recoverable failed state

Explicit resume may change `failed → running` only when:

```text
the failure category is registered as recoverable
underlying source artifacts validate
no immutable adopted artifact is inconsistent
the exact retry/regeneration stage is known
budget permits continuation
```

Examples:

```text
temporary provider outage after retry exhaustion
disk-space issue resolved before adoption
missing candidate due interrupted write
abandoned staging safely quarantined
```

### 34.2 Nonrecoverable automatic state

Manual intervention is required for:

```text
invalid HEAD graph
invalid CURRENT graph
counter regression
conflicting adopted plan
conflicting final publication roots
immutable version/config mismatch
adopted manifest missing required source artifact
```

### 34.3 Error detail

`stop_reason_detail` and error audits are sanitized.

They must not contain:

```text
credential value
raw prompt
raw provider response
private author truth not needed for diagnosis
absolute external path
```

---

## 35. `completed`

A run is completed only when:

```text
last_completed_stage = OUT-03
next_stage = null
output/CURRENT is valid
current_publication_id = CURRENT
run_status = completed
stop_reason_code = completed
```

A completed run cannot resume normal story generation.

Creating another publication or modifying the story requires a separately specified new operation/run mode. Version 1 normal run does not reopen completed execution.

---

# Part VIII: Orphans, cleanup, and repair

## 36. Orphan classification

Supported reasons include:

```text
head_unreachable_generation
unreferenced_scene_artifact
unreferenced_volume_handoff
unadopted_publication
abandoned_staging
invalid_pointer_target
```

Operational subcategories may be recorded in the orphan item's diagnostic message or a registered extension, but the canonical enum remains defined by `runtime_records.md`.

### 36.1 Reachability proof

Before quarantine, code records:

```text
valid HEAD at discovery
valid CURRENT at discovery
candidate/checkpoint/transaction references checked
original path
reason
related IDs
file hash or directory inventory hash when configured
```

### 36.2 Atomic quarantine move

When possible, quarantine uses an atomic rename within the same filesystem.

When an atomic move is unavailable:

- stop rather than perform a non-atomic copy/delete of authoritative-looking content;
- require explicit recovery tooling.

### 36.3 Overlap

One path must not be included in two quarantine batches.

### 36.4 Quarantine failure

If quarantine cannot be completed:

- do not continue a transaction that could collide with the item;
- mark the run failed/manual as appropriate;
- leave the original content untouched.

---

## 37. Cleanup categories

### 37.1 Safe automatic cleanup

After validation, code may remove:

```text
same-directory temporary files
empty staging parent directories
checkpoint for an adopted Scene
staging residue for an adopted HEAD/CURRENT transaction
empty unused directories
```

### 37.2 Quarantine before cleanup

Use quarantine for:

```text
nonempty partial version directory
HEAD-unreachable Generation
unreferenced Scene/Handoff
unadopted Publication directory
conflicting later-phase checkpoint file
```

### 37.3 Never automatic delete

Never automatically delete:

```text
HEAD-reachable Generation
CURRENT publication
adopted plan
HEAD-reachable Scene/Handoff
candidate history
referenced Context snapshot
valid Checkpoint for an uncommitted Scene
residual Issue audit
passing Gate for a retained Publication
```

---

## 38. Explicit repair boundaries

Version-1 ordinary startup must not perform these repairs automatically:

```text
rewrite canon/HEAD to another Generation
rewrite output/CURRENT to another Publication
recreate missing adopted Scene/Handoff from a Commit manifest
change an adopted manifest hash
recalculate and replace an adopted Canon root
renumber an allocated persistent ID
decrement a counter
merge two candidate histories
replace a conflicting adopted plan
change a Completion assessment
```

A future repair tool must:

1. declare the exact repair operation;
2. run under the workspace lock;
3. create a pre-repair snapshot/inventory;
4. validate the proposed post-repair graph;
5. preserve non-reused IDs;
6. write immutable repair audit;
7. never hide semantic data loss.

---

# Part IX: Deterministic next-stage reconstruction

## 39. Reconstruction from Genesis HEAD

When HEAD is Genesis:

1. validate adopted Brief and Initial-design snapshot;
2. inspect exactly `plans/series-map.json`;
3. if absent:
   ```text
   next_stage = SERIES-01
   target = series
   ```
4. if valid:
   - inspect exact Volume-1 design;
   - if absent, route `VOL-01`, target `v01`;
   - if valid, inspect exact Chapter-1 design;
   - if absent, route `CH-01`, target `v01-c001`;
   - if valid, derive Scene 1 and inspect its exact checkpoint/adopted status.

Unexpected later plans do not change this ordered reconstruction.

---

## 40. Reconstruction from Scene HEAD

From the HEAD Scene Commit:

1. read the source Scene ID;
2. validate its adopted Chapter and Volume designs;
3. compare Scene number to Chapter `target_scene_count`;
4. compare Chapter number to Volume `target_chapter_count`;
5. derive exactly:
   ```text
   next Scene
   next Chapter
   Volume handoff
   ```
6. inspect only the exact expected adopted plan/checkpoint/candidate boundary;
7. reconcile Run state.

A later unrelated plan or candidate does not override this route.

---

## 41. Reconstruction from Handoff HEAD

From the HEAD Handoff Commit:

1. read the Handoff Volume number;
2. validate Series map;
3. if another Volume remains:
   ```text
   next_stage = VOL-01
   target = next Volume
   ```
4. otherwise:
   ```text
   next_stage = COMP-PRE
   target = completion
   ```

If the exact next Volume design already validates, reconcile through its adoption boundary and continue to the exact first Chapter.

---

## 42. Reconstruction from valid Scene checkpoint

For the exact expected uncommitted Scene:

| checkpoint phase | next stage |
|---|---|
| `CARD_ACCEPTED` | `PROSE-01` or later valid active prose boundary |
| `PROSE_FROZEN` | `DELTA-01` or later valid active continuity boundary |
| `DELTA_ACCEPTED` | `COMMIT-01` |
| `COMMIT_PREPARED` | `COMMIT-04` |

Candidate-level advancement beyond the phase requires a valid Run-state-selected Candidate manifest.

Without it, return to the phase's family start rather than selecting a candidate by scanning.

---

## 43. Reconstruction from CURRENT

When valid CURRENT exists:

- it reconciles publication identity;
- if Run state is not completed and the story run reached OUT-03, mark completed;
- it does not imply Canon HEAD should change;
- it does not permit restarting story generation.

A valid CURRENT may coexist with a valid non-current older Publication directory.

---

# Part X: Operational algorithms

## 44. Exact startup algorithm

Under the workspace lock:

1. validate workspace path security;
2. read Run manifest when present;
3. read Effective config and compare immutable identity;
4. read counters and validate basic Schema;
5. read and validate HEAD when present;
6. validate the complete HEAD graph;
7. read and validate CURRENT when present;
8. validate the complete CURRENT publication;
9. read Run state when present;
10. reconcile Run-state HEAD/CURRENT fields from valid pointers;
11. validate counter lower bounds against observed IDs;
12. derive the deterministic story route from HEAD and adopted plans;
13. compare derived route with Run-state stage/target;
14. validate the Run-state-selected active Checkpoint;
15. reconcile from the exact expected valid Checkpoint when Run state is behind;
16. validate the Run-state-selected active Candidate;
17. validate referenced Context and Review artifacts;
18. validate referenced staging transaction;
19. classify leftover candidate/checkpoint/staging/adopted-looking paths;
20. quarantine proven unreferenced content;
21. remove safe temporary/empty residue;
22. update Run state for reconciliation under atomic replacement;
23. enforce stopped/paused/failed explicit-resume policy;
24. recompute remaining budgets;
25. set `run_status=running` only when continuation is authorized;
26. execute exactly `next_stage`.

If any higher-authority validation fails, lower-level discovery does not continue as a way to guess a replacement authority.

---

## 45. Atomic Run-state reconciliation

A reconciliation update includes:

```text
state_revision + 1
run status
last completed stage
next stage
target coordinates
scene phase
active Candidate/Checkpoint paths
current HEAD generation
last Commit ID
current Publication ID
Effective-config hash
stop fields
updated_at
```

Procedure:

1. construct the complete new Run state in memory;
2. validate it against the Run-state Schema and stage invariants;
3. write same-directory temporary bytes;
4. flush and atomically replace;
5. flush parent directory;
6. re-read and validate;
7. write a unique reconciliation operation audit.

A partial field patch is forbidden.

---

## 46. Recovery idempotency

Running startup reconciliation twice without intervening mutation must produce:

```text
same adopted HEAD/CURRENT conclusions
same next stage and target
no additional ID allocation
no duplicate residual Issue line
no duplicate quarantine move
no duplicate provider call
no duplicate pointer change
```

Timestamps and unique operation-audit filenames may differ only when the second run records a distinct requested inspection/recovery action. Ordinary no-op startup should avoid noisy duplicate audits where policy permits.

---

## 47. Recovery audit requirements

Write a unique operation audit for at least:

```text
lock recovery refusal
Run-state reconciliation
Candidate invalidation
Candidate staleness
unreferenced Review discarded
Checkpoint invalidation
extra checkpoint file quarantined
Genesis reconciliation
plan-adoption reconciliation
Scene-commit reconciliation
Handoff-commit reconciliation
Publication explicit post-rename recovery
completed Run reconciliation
counter-repair refusal or explicit repair
orphan quarantine batch
config resume change
budget stop/resume
manual-intervention stop
```

Audit records include:

```text
operation/target
outcome
input/output references and hashes
sanitized message
registered details
created_at
```

They do not contain raw private content unless the private audit contract explicitly permits it.

---

# Part XI: Recovery matrices

## 48. Candidate crash matrix

| durable state | action |
|---|---|
| no version directory | make provider call |
| empty/temporary-only version | quarantine; allocate next version |
| candidate only | quarantine; regenerate |
| Candidate manifest only | quarantine; regenerate |
| candidate + valid manifest | reconcile to Review |
| Review file unreferenced | quarantine Review; repeat Review |
| candidate + manifest + referenced valid Review | derive route |
| ready candidate + Run state behind | reconcile to checkpoint/adoption |
| raw success audit only | repeat call; never promote audit body |

---

## 49. Scene-checkpoint crash matrix

| durable state | action |
|---|---|
| Scene card + CARD_ACCEPTED manifest | resume prose |
| prose exists, manifest still CARD_ACCEPTED | quarantine prose; resume prose |
| PROSE_FROZEN manifest | resume Delta |
| delta exists, manifest still PROSE_FROZEN | quarantine delta; resume Delta |
| DELTA_ACCEPTED manifest | resume COMMIT-01 |
| Commit plan exists but COMMIT-01 not durably recorded | validate/reference rules; otherwise quarantine and redo COMMIT-01 |
| COMMIT_PREPARED manifest | resume COMMIT-04 |
| target Scene already adopted | reconcile commit; clean checkpoint |

---

## 50. Generation transaction crash matrix

| durable state | HEAD | action |
|---|---|---|
| staging only | unchanged | resume valid staging or quarantine |
| final Generation only | unchanged | quarantine Generation |
| final Scene/Handoff only | unchanged | quarantine artifact |
| final Generation + Scene/Handoff | unchanged | quarantine both |
| complete final graph | changed | adopted; reconcile Run state |
| incomplete required graph | changed | manual intervention |

---

## 51. Publication crash matrix

| durable state | CURRENT | action |
|---|---|---|
| provisional payload staging | unchanged | resume OUT-02 or quarantine |
| finalized staging, no Gate | unchanged | resume COMP-PUBLISH |
| finalized staging + passing Gate | unchanged | resume OUT-03 |
| final Publication directory, staging absent, passing Gate, exact OUT-03 recovery state | unchanged | explicit recovery permitted |
| final Publication directory without valid Gate | unchanged | quarantine |
| staging and final directory both exist | unchanged | manual intervention |
| valid final Publication | changed to ID | adopted; reconcile completed |
| invalid CURRENT target | changed | manual intervention |

---

## 52. Stop/restart matrix

| previous status/reason | startup behavior |
|---|---|
| `running` after crash | reconcile and continue automatically |
| `initialized` | continue bootstrap when durable source permits |
| `paused` | validate but wait for explicit resume |
| `stopped/user_stop` | wait for explicit resume |
| `stopped/budget_exhausted` | require permitted budget/retention change or code-only continuation proof |
| `stopped/manual_intervention` | no automatic resume |
| `failed/mechanical_error` recoverable | explicit resume after cause resolved |
| `failed/mechanical_error` adopted-graph conflict | manual intervention |
| `completed` | validate and remain completed |

---

# Part XII: Invariants and prohibitions

## 53. Runtime invariants

A recoverable workspace satisfies:

```text
one workspace lock owner
Run manifest run_id equals Run state run_id
Run-state Effective-config hash matches
Run-state HEAD identity equals canon/HEAD
Run-state Commit identity equals HEAD Commit
Run-state CURRENT identity equals output/CURRENT
successful Scene count equals HEAD current_order

every active Candidate path is Run-state-selected
every active Candidate candidate/hash/Context validates
every selected Review targets the selected candidate
every active Checkpoint path is exact expected Scene path
Checkpoint phase files and hashes match
every referenced staging transaction matches its source pointer/manifest

every counter is greater than observed allocated values
every adopted Generation is immutable
every adopted Scene/Handoff is HEAD-reachable
every adopted Publication is CURRENT-selected
every final Manifest uses final/root-relative paths
every orphan is outside all valid authority graphs
```

---

## 54. Forbidden recovery shortcuts

Forbidden:

```text
choose latest Generation and rewrite HEAD
choose latest Publication and rewrite CURRENT
promote raw LLM audit response into a candidate
construct a Candidate manifest for an orphan candidate file
use an unreferenced Review to skip a Review call
promote an extra checkpoint file because it parses
complete HEAD after final directory rename by inference
complete CURRENT after Publication rename by inference
decrement counters or reuse gaps
refund used token/cost counters
change semantic configuration silently
migrate Schema/workspace version during normal resume
rewrite an adopted plan or Generation
repair story meaning during startup
delete unreferenced content before reachability proof
follow an external symlink for diagnosis
remove a lock based only on age
continue without required audit storage
retry Completion until it returns complete
mark a Run completed before valid CURRENT
```

---

## 55. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
workspace-wide exclusive lock
stale-lock non-age policy
network-filesystem rejection
workspace path and symlink security

ordered startup validation
HEAD exact-byte and graph validation
Genesis/Scene/Handoff Commit branch validation
CURRENT exact-byte and complete Publication validation
pointer-over-Run-state reconciliation
Run-state-ahead-of-pointer rejection

Run-state revision increment
status/next-stage consistency
crash while running resume
paused/stopped explicit-resume enforcement
completed non-resume behavior

counter persist-before-use
counter-gap acceptance
counter-lower-than-observed rejection
usage-counter non-refund
successful Scene count reconciliation

immutable-config mismatch stop
permitted resume config change
credential rotation without persisted secret
version-migration rejection

active Candidate exact-manifest recovery
candidate-only and manifest-only quarantine
raw-audit non-promotion
Review-reference recovery
residual-Issue duplicate-safe append
partial candidate-version quarantine
stale candidate regeneration without revision increment
Context hash/path and deterministic rebuild behavior

deterministic Scene-checkpoint discovery
Run-state-behind checkpoint reconciliation
extra checkpoint-file quarantine
checkpoint source-generation invalidation
adopted-Scene checkpoint cleanup

Genesis crash cases
plan-adoption crash cases
Scene-commit staging/resume cases
Generation/Scene pre-HEAD orphan handling
Scene post-HEAD reconciliation
Handoff transaction recovery
standalone Handoff rejection

Completion-precondition reuse and invalidation
Completion attempt non-promotion from audit
valid incomplete non-retry
Completion source-generation staleness

OUT-01 provisional staging recovery
OUT-02 payload Validation failure
finalized staging resume
passing Gate resume
post-rename Publication explicit recovery
final Publication without Gate rejection
both publication roots conflict
CURRENT post-adoption reconciliation

provider-call ambiguity handling
Call-ID non-reuse
audit temporary-file handling
audit filename collision rejection
usage/cost conservative reconciliation
audit-storage stop

safe-boundary user stop
budget-exhausted resume rules
recoverable failed-state resume
manual-intervention boundaries
completed-state conditions

orphan reachability proof
atomic quarantine
quarantine non-promotion
cleanup category enforcement
explicit repair prohibitions

deterministic next-stage reconstruction from Genesis
deterministic route from Scene HEAD
deterministic route from Handoff HEAD
checkpoint phase route
CURRENT reconciliation

startup idempotency
atomic full Run-state replacement
required recovery operation audits
unknown recovery class rejection
unknown-field rejection
