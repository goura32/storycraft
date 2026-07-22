# Implementation acceptance

This document is the normative executable acceptance contract for the Storycraft version-1 implementation.

It converts the design contracts into:

- stable acceptance IDs;
- required automated-test categories;
- deterministic fake and fixture requirements;
- exact positive and negative scenarios;
- crash/failpoint matrices;
- packaging and CLI release gates;
- evidence required before implementation status may be declared complete.

The implementation contracts are defined by:

- [`configuration_contracts.md`](configuration_contracts.md)
- [`context_contracts.md`](context_contracts.md)
- [`workspace_layout.md`](workspace_layout.md)
- [`runtime_and_recovery.md`](runtime_and_recovery.md)
- [`pipeline_contracts.md`](pipeline_contracts.md)
- [`ledger_contracts.md`](ledger_contracts.md)
- [`prompt_template_design.md`](prompt_template_design.md)
- the documents under [`contracts/data/`](contracts/data/)
- the documents under [`contracts/ledger/`](contracts/ledger/)
- the documents under [`contracts/pipeline/`](contracts/pipeline/)

This document does not permit a weaker implementation than those contracts. When this document and a field-level contract appear to disagree, the more specific field-level contract is authoritative and this acceptance document must be corrected before release.

---

## 1. Acceptance philosophy

### 1.1 Observable behavior over successful exit

A test does not pass merely because:

```text
the command returned zero
an LLM fake returned an object
a file exists
the final prose looks plausible
```

Acceptance tests assert exact observable effects:

```text
paths
canonical bytes
hashes
manifest fields
counter values
pointer values
stage transitions
candidate/checkpoint phases
call counts
retry categories
artifact classes
quarantine actions
absence of forbidden files and fields
```

### 1.2 Deterministic by default

All mandatory automated tests use deterministic local fakes.

The default acceptance suite must not require:

```text
network access
real OpenAI credentials
wall-clock waiting
nondeterministic random output
an external database
an external object store
a particular home directory
manual review of prose quality
```

### 1.3 Exact contracts

Every structured object is tested for:

```text
required fields
nullable fields
default materialization
enum registry
conditional fields
unknown-field rejection
cross-reference rules
canonical ordering
canonical serialization
hash stability
```

### 1.4 Positive and negative proof

Every major contract requires:

- at least one passing example;
- at least one missing-required-field failure;
- at least one unknown-field failure;
- at least one conditional-rule failure;
- at least one cross-artifact mismatch failure where applicable.

### 1.5 Crash correctness

Every atomic adoption or phase boundary is tested at failpoints immediately before and immediately after its durable steps.

The test must prove:

```text
whether adoption occurred
which pointer is authoritative
whether a provider call repeats
whether an ID is reused
whether a counter is refunded
whether an orphan is quarantined
which exact stage resumes
```

### 1.6 No hidden test-only semantics

Production and tests must use the same:

```text
validators
canonical serializers
hash functions
path normalizers
transition tables
ID allocators
Context builders
manifest readers
recovery classifiers
```

A test-only permissive Schema, alternate state machine, or simplified commit implementation is forbidden.

---

## 2. Acceptance identifiers

Every normative automated scenario in this document has a stable ID:

```text
ACC-<AREA>-<NNN>
```

Examples:

```text
ACC-CFG-001
ACC-SCENE-014
ACC-REC-027
```

### 2.1 Test traceability

Every mandatory test must expose its acceptance ID through at least one of:

```text
test function/method name
subTest label
docstring
parameter ID
generated acceptance report
```

Recommended test name:

```text
test_acc_commit_014_head_is_written_last
```

### 2.2 One test may cover multiple IDs

A test may cover multiple acceptance IDs only when:

- each ID is reported separately on failure;
- the assertions remain independently identifiable;
- one early failure does not hide all later IDs.

### 2.3 One ID may use multiple tests

An acceptance ID may require multiple tests for:

```text
operating-system branch
input mode
processor type
success/failure variant
crash point
```

### 2.4 Release trace report

The release suite must produce or make derivable a machine-readable mapping:

```text
acceptance ID
test node/name
result
duration
fixture
runtime version
Python version
```

The report may be emitted to a temporary CI artifact. It is not written into a user workspace.

---

## 3. Canonical acceptance commands

The repository must support these commands from its root.

### 3.1 Syntax/import gate

```bash
python -m compileall -q src tests
```

### 3.2 Full automated suite

Canonical dependency-minimal command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

A project may additionally support `pytest`, but the release cannot depend solely on an undeclared test runner.

### 3.3 Wheel smoke gate

```bash
bash scripts/wheel_smoke.sh
```

The script must build and install the wheel in an isolated virtual environment.

### 3.4 CLI smoke gate

After wheel installation:

```bash
storycraft --help
storycraft run --help
storycraft resume --help
storycraft step --help
```

Each command must:

- exit zero;
- avoid network access;
- show no traceback;
- load packaged prompt/Schema assets successfully.

### 3.5 Optional static gates

Static analysis may be added, but it does not replace runtime acceptance.

A release checklist must record the exact commands and versions used.

---

## 4. Required test structure

The repository must organize acceptance tests so that failures identify the owning contract.

Recommended layout:

```text
tests/
  unit/
    test_canonical_json.py
    test_hashing.py
    test_paths.py
    test_id_allocators.py
    test_transition_registry.py

  contracts/
    test_configuration_contracts.py
    test_canon_records.py
    test_story_state.py
    test_evidence_and_updates.py
    test_runtime_records.py
    test_brief_and_initial.py
    test_planning_artifacts.py
    test_scene_artifacts.py
    test_review_and_audit.py
    test_context_contracts.py

  pipeline/
    test_input_and_initial.py
    test_planning.py
    test_scene_generation.py
    test_commit_and_output.py

  recovery/
    test_runtime_startup.py
    test_candidate_recovery.py
    test_checkpoint_recovery.py
    test_transaction_recovery.py
    test_publication_recovery.py

  security/
    test_path_security.py
    test_secret_redaction.py
    test_prompt_boundaries.py

  integration/
    test_full_success.py
    test_residual_issue_run.py
    test_incomplete_completion.py
    test_budget_resume.py
    test_cli_lifecycle.py

  packaging/
    test_packaged_assets.py

  fixtures/
    ...
```

The implementation may retain a flat `tests/` directory, but the same acceptance coverage and traceability remain required.

---

## 5. Mandatory deterministic test doubles

### 5.1 Fake clock

The suite must provide a clock fake that controls:

```text
RFC 3339 timestamps
timestamp-basic filenames
elapsed monotonic time
timeout boundaries
retry backoff accounting
```

Requirements:

- no mandatory test calls real `sleep`;
- wall-clock and monotonic time are separate;
- advancing one does not implicitly advance the other unless the scenario says so;
- generated timestamps are stable across runs.

### 5.2 Scripted LLM provider

The provider fake accepts a scripted sequence of outcomes.

Each scripted item can specify:

```text
transport result
HTTP status
response body
stream event times
finish reason
usage
provider error code
billable/no-billable status when adapter knows it
```

The fake records:

```text
complete redacted request
operation
target
role
logical attempt
provider HTTP attempt
Context hash
prompt version
response-Schema version
timeout values
```

It must support:

```text
success
connection failure
TLS failure
connect timeout
first-event timeout
idle timeout
total timeout
retryable HTTP error
nonretryable HTTP error
invalid UTF-8
invalid JSON
Schema failure
valid semantic Review issues
valid semantic Completion incomplete
```

### 5.3 Deterministic tokenizer

The test tokenizer must produce stable counts for known UTF-8/Japanese inputs.

Tests must cover:

```text
provider tokenizer path
provider preflight path
fallback estimate path
mandatory Context overflow
optional deterministic exclusions
```

### 5.4 Fault-injecting filesystem

The test filesystem adapter or failpoint layer must inject failure:

```text
before temporary write
after temporary write
before file fsync
after file fsync
before atomic replace
after atomic replace
before directory fsync
after directory fsync
before directory rename
after directory rename
before pointer replace
after pointer replace
```

It must not emulate atomicity by silently completing both sides after a failure.

### 5.5 Fake credential source

The fake credential source:

- provides a value only through the configured environment-variable interface;
- records whether a credential was requested;
- never writes the value into fixtures, logs, or snapshots;
- can simulate a missing credential and a rotated credential.

### 5.6 Lock fake

The lock fake supports:

```text
successful exclusive acquisition
second-writer rejection
stale-looking metadata with live ownership
ownership loss/error
unsupported filesystem semantics
```

Tests must distinguish diagnostic lock-file content from actual lock ownership.

### 5.7 Deterministic file-space and audit-capacity fake

The suite must simulate:

```text
insufficient disk before transaction
audit-storage limit reached
capacity restored for resume
```

### 5.8 No real network

The full mandatory suite fails if an unmocked network socket is opened.

This may be enforced by:

```text
socket monkeypatch
test network namespace
CI firewall
provider adapter dependency injection
```

---

# Part I: Core serialization and path acceptance

## 6. Canonical JSON and text

### ACC-CORE-001 — Canonical JSON stability

Given the same logical object, serialization must produce identical UTF-8 bytes across repeated calls.

Assert:

```text
object key order
array order already normalized by contract
NFC strings
no insignificant whitespace
no NaN or Infinity
one exact final-byte policy
```

### ACC-CORE-002 — Hash uses canonical bytes

Every SHA-256 field must equal the hash of the contract-selected canonical bytes, not:

```text
Python repr
pretty JSON
source input before normalization
filesystem metadata
decompressed bytes when compressed bytes are specified
```

### ACC-CORE-003 — Unknown field rejection

For every exact structured root and discriminated-union branch, inject one unknown field and assert rejection.

The suite must include at least:

```text
Effective config
Candidate manifest
Run state
Canon record
Story-state row
Evidence record
Scene card
continuity delta
Review Issue
Completion assessment
Publication Validation
Publication manifest
Gate
```

### ACC-CORE-004 — Numeric strictness

Assert rejection of:

```text
boolean where integer is required
stringified integer
NaN
Infinity
negative count
fractional counter
```

### ACC-CORE-005 — Text canonicalization

For prose and text fields, test:

```text
CRLF input normalization
NFD to NFC
final LF policy
control-character rejection
BOM rejection where forbidden
```

---

## 7. Managed path security

### ACC-PATH-001 — Relative POSIX path

Persisted workspace paths use `/`, contain no leading `./`, and remain workspace-relative.

### ACC-PATH-002 — Traversal rejection

Reject:

```text
../
a/../../b
percent/escape variants after decoding
Unicode-confusable traversal when normalized to a forbidden segment
```

### ACC-PATH-003 — Absolute path rejection

Reject POSIX, Windows drive, UNC, and device paths.

### ACC-PATH-004 — Canonical case

Reject managed-path case variants such as:

```text
Canon/HEAD
canon/head
Output/CURRENT
```

even on a case-insensitive test adapter.

### ACC-PATH-005 — Symlink escape

A managed path that resolves through a symlink/junction outside the workspace is rejected without reading the external target.

### ACC-PATH-006 — Fixed-width coordinates

Accept and round-trip:

```text
v01
c001
s001
v01-c001-s001
v0001 candidate version
00000001 generation
```

Reject malformed widths and zero coordinates where prohibited.

### ACC-PATH-007 — Publication-relative stability

A Publication file reference must resolve to the same relative path before and after staging-directory rename.

No Manifest or Gate field may contain:

```text
.staging/publication/
publications/<id>/
```

as an internal publication path.

---

# Part II: Configuration acceptance

## 8. Effective configuration

### ACC-CFG-001 — Complete materialization

Materialize the complete Effective-config root with every required field and fixed operation-key map.

### ACC-CFG-002 — Secret exclusion

Given a real-looking API key, assert that it is absent from:

```text
effective-config bytes
Run manifest
Run state
Context snapshot
Candidate manifest
LLM-call audit after redaction
normal log
exception text
```

The credential environment-variable name must be present where required.

### ACC-CFG-003 — Exact operation keys

The configuration must contain exactly:

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

Missing, unknown, or legacy keys are rejected.

### ACC-CFG-004 — `max_new_items_per_scene`

Assert:

```text
required materialized value
default = 2
minimum = 0
maximum = 20
-1 rejected
21 rejected
boolean rejected
```

### ACC-CFG-005 — Revision rounds

Assert zero is valid when the contract allows no semantic revision and that negative values are rejected.

Legacy `max_critique_passes` terminology must not control the normative pipeline.

### ACC-CFG-006 — Timeout hierarchy

Test connect, first-event, idle, and total-call timeout independently.

A timeout must receive the correct transport error code and retryability.

### ACC-CFG-007 — Retry classification

Test:

```text
retryable transport error
nonretryable transport error
response-structure retry
semantic revision
Completion-audit attempt
```

Counters must change only in their own categories.

### ACC-CFG-008 — Backoff

Given deterministic retry numbers and jitter input, assert the exact configured backoff formula and active elapsed-time accounting.

### ACC-CFG-009 — Usage and cost

Test:

```text
provider usage
tokenizer-derived usage
fallback-estimated usage
zero-unbilled response
cached input
reasoning token handling
finite nonnegative estimated cost
```

### ACC-CFG-010 — Resume mutability

Assert:

```text
immutable field change rejected
resume-mutable field change accepted
resume-increase-only field increase accepted
resume-increase-only decrease rejected
credential rotation accepted without config change
```

### ACC-CFG-011 — Publishing profile

The default KDP profile must enforce:

```text
4..10 Volumes
first Volume free
later Volumes paid
local resolution
nonfinal continuation question
auto_publish = false
```

### ACC-CFG-012 — Audit limits

When required audit capacity is exhausted, the runtime stops before another LLM call and does not silently disable auditing.

---

# Part III: Ledger and data contracts

## 9. Canon records

### ACC-CANON-001 — Canon root

`current-canon.json` must be exactly:

```json
{"records":[]}
```

with records sorted by the canonical registry/order rules.

### ACC-CANON-002 — Knowledge root

`knowledge-items.json` must be exactly:

```json
{"items":[]}
```

with canonical ordering.

### ACC-CANON-003 — Enum separation

Test rejection of mixed concepts:

```text
record_origin used as Relationship origin
knowledge_record_type used as Canon record type
new-item proposal type used as adopted record type
thread status used as lifecycle
```

### ACC-CANON-004 — Origin

Accepted values:

```text
initial_design
prose
```

Legacy or free-form origin strings are rejected.

### ACC-CANON-005 — Major Thread invariants

A required Major Thread must be:

```text
importance/type = Major as defined
required = true
scope = series
non-null author truth
non-null resolution condition
complete presentation information
```

A Scene proposal may not create a Major Thread.

### ACC-CANON-006 — Ending criterion invariants

Initial required Ending criteria validate.

A Scene proposal may not create an Ending criterion.

### ACC-CANON-007 — Knowledge truth

`author_truth` is permitted only according to the Knowledge-origin rule.

Writer-safe projections never expose it.

### ACC-CANON-008 — Lifecycle

Test active, inactive/retired semantics exactly as registered and reject lifecycle/status substitution.

---

## 10. Story state

### ACC-STATE-001 — Exact root

`story-state.json` contains exactly:

```text
character_states
relationship_states
thread_states
knowledge_states
story_clock
```

No `world_states`.

### ACC-STATE-002 — Complete Genesis rows

Genesis contains:

```text
one Character State per Character
one Relationship State per Relationship
one Thread State per Major Thread
only nondefault Knowledge rows
one Genesis Story clock
```

### ACC-STATE-003 — Sparse Knowledge defaults

Missing rows derive:

```text
Character = unknown
Reader = withheld
```

Explicit rows equal to defaults are rejected.

### ACC-STATE-004 — Knowledge transition matrix

Every permitted transition passes and every forbidden backward/invalid transition fails.

Test both Character and Reader audiences.

### ACC-STATE-005 — Thread matrix

Test every permitted:

```text
introduce
advance
resolve
retire
```

combination against status/progress/type/required rules.

Required Major Thread retirement must fail.

### ACC-STATE-006 — Story clock

Test:

```text
Genesis constants
sequential Scene commit
parallel relation
time label
position fields
current_order increment
Handoff preservation
```

### ACC-STATE-007 — Volume disposition

Only VH-ID may update `volume_disposition`.

A Scene continuity delta targeting that field is rejected.

---

## 11. Evidence and continuity updates

### ACC-EVID-001 — Candidate versus committed fields

A candidate delta containing:

```text
persistent new ID
Evidence ID
Commit ID
Generation ID
offset
quote hash
prose hash
timestamp
```

must fail.

The committed delta must contain the code-owned resolved values.

### ACC-EVID-002 — Local keys

Test:

```text
syntax
global candidate uniqueness
typed reference compatibility
resolution order
unresolved local-key rejection before commit
```

### ACC-EVID-003 — Quote occurrence

Evidence quote must be an exact canonical-prose substring occurring exactly once.

Test:

```text
zero occurrence
one occurrence
two occurrences
Unicode normalization mismatch
```

### ACC-EVID-004 — Offsets

Code computes Unicode code-point offsets.

Assert the slice by `[start_offset:end_offset]` equals the quote for Japanese text containing supplementary characters and combining-source input normalized to NFC.

### ACC-EVID-005 — Quote hash

`quote_sha256` equals canonical quote bytes and `prose_sha256` equals frozen/adopted prose bytes.

### ACC-EVID-006 — Before-state equality

Every existing update candidate's code-injected `before` value equals current HEAD.

A stale/mismatched before value blocks checkpoint/commit.

### ACC-EVID-007 — Authorization

Continuity updates are accepted only when their target branch and operation are listed by frozen Scene-card `allowed_update_targets`.

### ACC-EVID-008 — New-item policy

The combined Canon + Knowledge proposal count must not exceed `max_items`.

Test type, scope, `allow_knowledge_items`, and forbidden Major Thread/Ending/Temporal creation.

### ACC-EVID-009 — Evidence index

`evidence-index.json` root is exactly:

```json
{"records":[]}
```

or a canonical ordered records array.

Evidence IDs are unique, allocated before use, and never reused.

### ACC-EVID-010 — Bidirectional merge correspondence

For a committed Scene:

- every committed delta change appears in after roots;
- every after-root change from the parent is represented by the committed delta;
- unchanged fields remain byte/logically equal as specified.

---

## 12. Brief and Initial design

### ACC-INIT-DATA-001 — Keyword source

Keyword source exact Schema, normalization, and immutable adoption.

### ACC-INIT-DATA-002 — Adopted Brief

Test Brief-mode and Keywords-mode adopted metadata and source hash.

LLM content must not include profile IDs, timestamps, or hashes.

### ACC-INIT-DATA-003 — Five-stage roots

Validate exact roots for:

```text
Concept
People
World
Arcs
integrated bundle
```

### ACC-INIT-DATA-004 — Protagonist and people coverage

Exactly one protagonist, matching the Brief, and every Brief key person represented exactly once.

### ACC-INIT-DATA-005 — Forward Location references

People may use a typed forward Location local key.

World integration must resolve it to a `location` entity.

### ACC-INIT-DATA-006 — Major Threads and Ending

The Arcs candidate must include all required complete Major Threads and at least one required Ending criterion grounded in Brief ending text.

### ACC-INIT-DATA-007 — Initial Knowledge

Test unique Knowledge facts, safe labels, subjects, and sparse initial audience states.

### ACC-INIT-DATA-008 — INIT-REV replacement

A patch/diff or partial bundle fails.

A complete replacement succeeds and receives the next candidate version.

### ACC-INIT-DATA-009 — Deterministic ID mapping

Given the same accepted integrated bundle and starting counters, persistent-ID allocation order and local-key mapping are exact.

---

## 13. Planning artifacts

### ACC-PLAN-DATA-001 — Series map

Test:

```text
Volume count = Brief
contiguous Volume numbers
structural roles
protagonist target chain
Relationship target chain
Major Thread target chain
required final resolution
Ending coverage
nonfinal/final reader-question rules
```

### ACC-PLAN-DATA-002 — Volume design

Test:

```text
target Volume identity
actual starting State
protagonist/Relationship changes
Thread actions
Ending targets
major conflict
Chapter count and functions
Volume ending function
```

### ACC-PLAN-DATA-003 — Chapter design

Test:

```text
target coordinates
purpose/start/end
primary change
Thread and Ending targets
World references
contiguous Scene plan
first/last Scene roles
POV references
```

### ACC-PLAN-DATA-004 — Adopted metadata

Adopted plan roots must contain exact source and parent hashes and no candidate/Review path in story content.

### ACC-PLAN-DATA-005 — Immutable plan

Attempting to replace an existing adopted plan with different bytes must fail.

Later HEAD movement must not rewrite the plan.

---

## 14. Scene artifacts

### ACC-SCENE-DATA-001 — Scene-card content versus frozen card

The LLM candidate excludes:

```text
Scene ID/coordinates
source generation
hashes
allowed-update-target computed baselines
code timestamps
```

SC-CHK injects and validates them.

### ACC-SCENE-DATA-002 — Writer-safe Scene projection

The Writer projection excludes update mechanics and hidden source text while retaining every required dramatic target.

### ACC-SCENE-DATA-003 — Allowed-update union

Every branch validates exactly:

```text
existing_item
knowledge_state
thread_state
story_clock
```

Unknown branch or branch-specific field leakage fails.

### ACC-SCENE-DATA-004 — Forbidden disclosure

Writer-safe records contain labels/reasons/hints but not hidden content.

Private Review extension may contain the minimum hidden content.

### ACC-SCENE-DATA-005 — Prose format

Accept canonical narrative Markdown.

Reject:

```text
front matter
heading
list
table
code fence
HTML
link
metadata preface
empty body
```

### ACC-SCENE-DATA-006 — Prose character count

Count Unicode code points excluding the required final LF.

The Scene manifest and Volume publication totals must reconcile.

### ACC-SCENE-DATA-007 — Checkpoint/adopted equality

Frozen and adopted Scene card/prose bytes must match exactly.

---

## 15. Review and audit data

### ACC-REV-001 — Generic Review root

Review LLM response contains exactly:

```text
summary
issues
```

It must not contain adoption or routing fields.

### ACC-REV-002 — Issue record

Test exact:

```text
code
severity
category
rule_id
artifact_role
location
description
suggested_change
related_ids
evidence_ids
```

### ACC-REV-003 — Issue location

Test all location branches and reject unresolved JSON pointers, missing prose quotes, and invalid cross-artifact roles.

### ACC-REV-004 — Normalization

Code canonicalizes issue order and assigns contiguous local IDs.

Counts and `review_status` must be derived exactly.

### ACC-REV-005 — Structural versus semantic

Invalid Review structure consumes response-structure retry.

Valid nonempty issues consume no response retry and route to revision/exhaustion.

### ACC-REV-006 — Residual records

After revision exhaustion, append exact duplicate-safe residual records.

A restart must not append duplicates.

### ACC-REV-007 — Completion assessment

Test complete coverage of required criteria and Major Threads and exact derivation of:

```text
complete
complete_with_residual_issues
incomplete
```

### ACC-REV-008 — Valid incomplete

A valid `incomplete` audit is saved, is not retried, and later fails Publication Gate.

### ACC-REV-009 — LLM-call audit

Audit filename and root must include and agree on:

```text
Call sequence/ID
operation
target
role
attempt
revision round when applicable
provider/model
Context hash
request/response hashes
outcome
usage
timing
error
```

Two calls cannot collide.

### ACC-REV-010 — Audit redaction

Headers, credentials, cookies, and forbidden absolute paths are absent.

Stored/nonstored body behavior and hashes match configuration.

### ACC-REV-011 — Publication Validation hashes

Validation computes `payload_set_sha256` over payload records only.

It does not hash Publication Validation, Publication manifest, or provisional build manifest.

### ACC-REV-012 — Rename-stable Gate

Gate stores root-relative internal paths and exact:

```text
Validation hash
Manifest hash
payload_set_sha256
content_set_sha256
publication_snapshot_sha256
```

The snapshot is identical before and after publication-directory rename.

---

# Part IV: Context acceptance

## 16. Context snapshot core

### ACC-CTX-001 — Hash-named deterministic snapshot

Same source bytes, builder version, operation, target, and semantic config produce identical snapshot bytes and path.

The snapshot contains no creation timestamp.

### ACC-CTX-002 — Source references

Every source reference path/hash resolves.

Missing or changed source invalidates reuse.

### ACC-CTX-003 — Candidate linkage

Candidate manifest, Review, Revision, LLM audit, and Completion precondition reference the correct Context hash.

### ACC-CTX-004 — No self-hash

The snapshot does not contain its own hash.

A self-referential hash field is rejected.

### ACC-CTX-005 — Exact view union

Every `view_type` accepts only its exact payload branch.

Cross-branch fields fail.

---

## 17. Context authority boundaries

### ACC-CTX-006 — Writer secret exclusion

Search the canonical Writer payload serialization and assert absence of:

```text
Thread author_truth
Thread resolution_condition
Knowledge author_truth
Ending source_ending_text
private non-POV goal
private non-POV pressure
raw Review Issue
future Scene prose
```

### ACC-CTX-007 — Non-POV Character filtering

The POV Character receives permitted internal State.

A non-POV Character receives only observable/safe projections.

### ACC-CTX-008 — Writer Knowledge labels

Writer sees safe labels/statuses, never raw canonical fact or author truth.

### ACC-CTX-009 — Continuity secret exclusion

Continuity View includes exact frozen card/prose and target baselines, but none of the hidden author-only fields.

### ACC-CTX-010 — Private Review extension

A prose Review receives the minimum private disclosure checks while its generator Context remains the exact Writer payload.

### ACC-CTX-011 — Planner authority

Planner Author View includes required private Thread/Ending information but the generated Scene-card content is mechanically checked for leakage.

### ACC-CTX-012 — Completion completeness

Completion View contains every required Ending criterion, every required Major Thread, final State, decisive Evidence, handoffs, and relevant residual issues.

No required item may be excluded for token budget.

---

## 18. Context overflow

### ACC-CTX-013 — Deterministic exclusion order

Given a payload over the limit, optional items are removed in the documented builder-specific order.

Repeat runs produce identical exclusions and hash.

### ACC-CTX-014 — Whole-item removal

No JSON string, array item, prose body, or UTF-8 sequence is cut arbitrarily.

### ACC-CTX-015 — Mandatory overflow stop

When mandatory data alone exceeds the input limit:

- no provider call occurs;
- no usable Context snapshot/candidate is written;
- the stage stops mechanically.

### ACC-CTX-016 — Final rendered-input check

The complete rendered request, including static prompt and Schema instructions, remains within the hard input limit.

Payload-only fit is insufficient.

---

# Part V: Runtime records and layout acceptance

## 19. Runtime roots

### ACC-RUN-001 — Complete Runtime files

Run manifest, Run state, counters, and Effective config contain every required typed field.

### ACC-RUN-002 — State revision

Every successful Run-state replacement increments `state_revision` by exactly one.

### ACC-RUN-003 — Full replacement

Run state is written as a complete validated object, never an in-place partial JSON edit.

### ACC-RUN-004 — Status/next-stage consistency

Test every status with permitted/forbidden `next_stage` and stop fields.

### ACC-RUN-005 — Artifact classes

Assert exact classes by stage:

```text
candidate
checkpoint
staged_internal
staged_internal_validation
adopted
audit
```

Reject all legacy/composite values.

---

## 20. Candidate layout and manifests

### ACC-RUN-006 — Version directory

Generation/revision creates:

```text
v0001
v0002
...
```

and never overwrites an earlier candidate or Review.

### ACC-RUN-007 — Same-directory paths

Candidate and Review paths in a Candidate manifest remain inside that exact version directory.

### ACC-RUN-008 — Logical owner

A revised candidate retains the generation owner operation/processor and records the revision through version, counters, Context, and Call ID.

### ACC-RUN-009 — Active selection

Only Run-state `active_candidate_manifest_path` selects the active candidate.

Directory scanning must not affect selection.

### ACC-RUN-010 — Completion layout

Completion uses one fixed Candidate manifest and `attempt-NN.json`, not candidate version directories.

---

## 21. Generation and manifest branches

### ACC-RUN-011 — Exact generation file set

A finalized Generation contains exactly six required files.

### ACC-RUN-012 — Genesis branch

Test all initial-design Commit/Generation conditional fields and order zero.

### ACC-RUN-013 — Scene branch

Test Scene source fields, Scene-manifest hash, parent order + 1, and null Handoff fields.

### ACC-RUN-014 — Volume-handoff branch

Test Handoff source fields, unchanged order, null Scene fields, and only permitted `volume_disposition` changes.

### ACC-RUN-015 — Hash graph

Commit and Generation manifests validate their complete noncyclic hash graph.

A one-byte mutation in every referenced artifact must be detected.

---

## 22. Publication runtime records

### ACC-RUN-016 — Publication manifest files

`files` includes:

```text
all payload files
publication-validation.json
```

It excludes:

```text
publication-manifest.json
publication-build-manifest.json
```

### ACC-RUN-017 — Content-set hash

`content_set_sha256` equals the canonical sorted `files` reference array.

### ACC-RUN-018 — Provisional removal

A finalized staged or adopted publication must not contain `publication-build-manifest.json`.

### ACC-RUN-019 — Relative paths

Every internal Publication path is root-relative and resolves under its own root.

---

# Part VI: Pipeline acceptance

## 23. Input and Initial pipeline

### ACC-PIPE-INIT-001 — Brief-mode route

Expected:

```text
INPUT-01
→ INIT-01
```

Assert no INPUT-02/INPUT-03 candidate, call, or fake completed-stage record.

### ACC-PIPE-INIT-002 — Keywords-mode route

Expected:

```text
INPUT-01
→ INPUT-02
→ INPUT-03
→ INIT-01
```

Assert exact source hashes and one adopted Brief.

### ACC-PIPE-INIT-003 — Intermediate resume

Crash after each of INIT-01 through INIT-04 candidate+manifest durability.

Restart must continue at the next INIT stage without repeating the completed provider call.

### ACC-PIPE-INIT-004 — Mechanically invalid integrated bundle

It must fail before INIT-06 Review.

Examples:

```text
unresolved local key
missing Character State
duplicate Knowledge fact
invalid Major Thread
```

### ACC-PIPE-INIT-005 — Review/revision loop

Test:

```text
no issues
one revision then no issues
revision exhaustion with residual issues
zero revision rounds
structurally invalid Review retry
structurally invalid Revision retry
```

### ACC-PIPE-INIT-006 — Genesis ID allocation

Dry validation occurs before any ID allocation.

After allocation begins, injected failure leaves gaps and retry uses new IDs.

### ACC-PIPE-INIT-007 — Genesis adoption order

Failpoints prove:

```text
Generation/Initial-design before HEAD = unadopted
HEAD changed = Genesis adopted
Run state behind HEAD = reconciled
```

---

## 24. Planning pipeline

### ACC-PIPE-PLAN-001 — Series source

SERIES-01 source generation is exactly Genesis `00000000`.

### ACC-PIPE-PLAN-002 — Volume source

VOL-01 source generation equals HEAD at Volume start and includes prior Handoff for Volume > 1.

### ACC-PIPE-PLAN-003 — Chapter source

CH-01 source generation equals HEAD at Chapter start and uses the previous final Scene handoff projection where applicable.

### ACC-PIPE-PLAN-004 — Review/revision/adoption

For Series, Volume, and Chapter, test all three Review routes and whole-candidate version replacement.

### ACC-PIPE-PLAN-005 — HEAD recheck

Change HEAD after candidate Review but before adoption.

Adoption must not occur; candidate becomes stale/regenerated according to contract.

### ACC-PIPE-PLAN-006 — Immutable final plan

Crash after final plan move but before Run-state update.

Restart reconciles without new LLM call.

A conflicting existing final plan stops mechanically.

### ACC-PIPE-PLAN-007 — Exact post-adoption route

Assert:

```text
SERIES-ID → VOL-01/v01
VOL-ID → CH-01/c001
CH-ID → SC-01/s001
```

---

## 25. Scene-generation pipeline

### ACC-PIPE-SCENE-001 — Scene-card route

Test complete SC generation/Review/revision/checkpoint paths and phase `CARD_ACCEPTED`.

### ACC-PIPE-SCENE-002 — Code-owned frozen fields

Assert LLM candidate did not provide and SC-CHK correctly injects:

```text
Scene identity
source generation
plan hashes
current Thread/Knowledge baselines
allowed update targets
forbidden disclosures
length guidance
timestamp
```

### ACC-PIPE-SCENE-003 — Frozen card immutability

After SC-CHK, PROSE stages cannot alter Scene-card bytes.

### ACC-PIPE-SCENE-004 — Writer call boundary

Capture the exact provider request and prove hidden author truth is absent.

### ACC-PIPE-SCENE-005 — Prose Review loop

Test no issues, revision, exhaustion, and format structural retry.

### ACC-PIPE-SCENE-006 — Prose checkpoint

PROSE-CHK creates exact frozen bytes, hash, and character count, then phase `PROSE_FROZEN`.

### ACC-PIPE-SCENE-007 — Delta extraction

DELTA-01 processor type is `llm_extract`, receives exact frozen prose, and writes only normalized validated candidate fields.

### ACC-PIPE-SCENE-008 — Delta invalid targets

Test rejection of:

```text
unauthorized field
stale before value
invalid Thread transition
invalid Knowledge transition
excess new items
duplicate Evidence quote
future handoff forecast
```

### ACC-PIPE-SCENE-009 — Delta Review loop

Test no issues, revision, exhaustion, and private contradiction extension.

### ACC-PIPE-SCENE-010 — Delta checkpoint

DELTA-CHK repeats mechanical validation and enters `DELTA_ACCEPTED` without allocating any story/Evidence ID.

### ACC-PIPE-SCENE-011 — Phase recovery

Crash after each checkpoint artifact write and manifest update.

Restart must trust the manifest phase, quarantine unreferenced later files, and avoid duplicate LLM calls.

### ACC-PIPE-SCENE-012 — HEAD change invalidation

Change HEAD during each Scene family.

The full checkpoint/candidate chain must be invalidated and the Scene restarts at SC-01 unless already adopted.

---

## 26. Scene commit

### ACC-COMMIT-001 — COMMIT-01 no allocation

Passing Commit plan is created with deterministic allocation requests and no counter changes.

### ACC-COMMIT-002 — Commit route

Test exact route derivation for:

```text
next Scene
next Chapter
Volume Handoff
```

### ACC-COMMIT-003 — Persist-before-use

At COMMIT-02, each Commit, record, and Evidence counter increment is durable before its value appears in a staged artifact.

### ACC-COMMIT-004 — Gap preservation

Inject failure after allocation.

Retry must not reuse any allocated ID.

### ACC-COMMIT-005 — Merge plan

Every local key resolves and every existing/new/State/Evidence operation is represented exactly.

### ACC-COMMIT-006 — Root construction

Staged after roots equal the deterministic application of the merge plan to the parent roots.

### ACC-COMMIT-007 — Committed delta

Committed delta contains resolved IDs and Evidence IDs and exactly matches the staged root difference.

### ACC-COMMIT-008 — Evidence offsets and hashes

All committed Evidence records validate against staged/adopted prose.

### ACC-COMMIT-009 — Manifest order and graph

Scene manifest, Commit manifest, and Generation manifest are built without a hash cycle and cross-validate.

### ACC-COMMIT-010 — COMMIT_PREPARED

COMMIT-03 writes passing transaction validation and atomically advances Checkpoint phase.

### ACC-COMMIT-011 — HEAD written last

Fail after Generation rename and after Scene rename but before HEAD.

Restart must treat final-looking content as unadopted and must not infer adoption.

### ACC-COMMIT-012 — Post-HEAD reconciliation

Fail after HEAD but before Run-state update.

Restart validates and reconciles the exact route without repeating the Scene or allocating IDs.

### ACC-COMMIT-013 — Scene count

After every Scene commit:

```text
successful_scene_commits
=
HEAD story_clock.current_order
```

### ACC-COMMIT-014 — Adopted equality

Adopted Scene card/prose equal checkpoint bytes; adopted committed delta differs only by code resolution/materialization rules.

---

## 27. Volume Handoff

### ACC-VH-001 — Candidate completeness

Volume Handoff child records reject unknown fields and cover required Characters/Relationships/Threads/Knowledge/World constraints.

### ACC-VH-002 — Thread disposition matrix

Test every permitted and forbidden disposition, including required Major Thread retirement failure and final-Volume resolve requirement.

### ACC-VH-003 — Handoff Review loop

Test no issues, revision, exhaustion, and mechanical-defect nonadoption.

### ACC-VH-004 — Handoff Commit branch

VH-ID allocates one Commit/Generation and no story/Evidence IDs.

### ACC-VH-005 — Only disposition changes

Diff parent and Handoff generation.

The only permitted logical changes are:

```text
thread_states[].volume_disposition
```

### ACC-VH-006 — Order preservation

Handoff generation preserves:

```text
story_clock
current_order
successful_scene_commits
```

### ACC-VH-007 — HEAD written last

Pre-HEAD Handoff Generation/file is unadopted.

Post-HEAD crash reconciles route.

### ACC-VH-008 — Route

Nonfinal Handoff routes to next VOL-01.

Final Handoff routes to COMP-PRE.

---

## 28. Completion and publication

### ACC-OUT-001 — Completion precondition

All required mechanical checks pass on the success fixture.

Any missing Scene, invalid Evidence, active checkpoint, or unresolved staging prevents the auditor call.

### ACC-OUT-002 — Attempt counters

Within one Completion attempt, response-structure retries are bounded.

After exhaustion, a new `attempt-NN` is used.

Transport/structure/attempt counters remain distinct.

### ACC-OUT-003 — First valid attempt stops attempts

The first structurally valid result proceeds to COMP-SAVE regardless of semantic assessment.

### ACC-OUT-004 — Private audit save

COMP-SAVE validates and stores the selected attempt without changing its assessment.

### ACC-OUT-005 — Deterministic manuscript

Assemble Volumes/Chapters/Scenes in plan order and produce stable bytes/hashes across repeated builds from identical sources.

### ACC-OUT-006 — Internal-ID exclusion

Reader-facing manuscript fails validation when a known internal identifier is injected outside a registered story-use exception.

### ACC-OUT-007 — Safe Completion report

The publication report contains safe summaries and excludes private author truth, raw Evidence quotes, private paths, prompts, and provider metadata.

### ACC-OUT-008 — Payload set

OUT-01 creates the exact payload set and provisional build manifest with `payload_set_sha256`.

### ACC-OUT-009 — Validation failure

Inject a bad payload file.

OUT-02 writes failing Validation, does not create a passing final Manifest/Gate, and stops mechanically.

### ACC-OUT-010 — Final Manifest

On success:

```text
Validation finalized
Validation hash recorded
files = payload + Validation
content_set_sha256 correct
build manifest removed
Manifest not self-listed
```

### ACC-OUT-011 — Gate pass

Complete/complete-with-residual audit plus matching publication hashes produces a passing Gate and no adoption mutation.

### ACC-OUT-012 — Gate incomplete

A valid incomplete audit produces `COMPLETION_INCOMPLETE`, no extra audit attempt, no adoption, and manual-intervention stop.

### ACC-OUT-013 — Rename-stable snapshot

Calculate the Gate snapshot in staging, rename the directory, and reproduce the exact snapshot under the final root.

### ACC-OUT-014 — OUT-03 normal adoption

Assert order:

```text
final staging validation
directory rename
final-root snapshot revalidation
CURRENT replacement
Run-state completion
```

### ACC-OUT-015 — OUT-03 post-rename recovery

With original passing Gate and exact Run state, recover a renamed final directory before CURRENT.

Without those conditions, automatic adoption must fail.

### ACC-OUT-016 — CURRENT written last

A final Publication directory without CURRENT remains unadopted.

A valid CURRENT with Run state behind reconciles completed state.

---

# Part VII: Runtime and recovery acceptance

## 29. Lock and startup

### ACC-REC-001 — Exclusive writer

A second writer cannot mutate while the first holds the lock.

### ACC-REC-002 — Stale metadata

Old-looking lock metadata does not allow lock stealing when OS ownership remains active.

### ACC-REC-003 — Unsupported filesystem

When required atomicity/locking cannot be guaranteed, startup stops rather than downgrading.

### ACC-REC-004 — Startup order

Instrument validation calls and assert the normative order:

```text
security
foundational records
HEAD graph
CURRENT graph
Run-state comparison
active Checkpoint
active Candidate
staging
orphan scan
```

### ACC-REC-005 — Invalid HEAD

Invalid HEAD never causes selection of another Generation.

### ACC-REC-006 — Invalid CURRENT

Invalid CURRENT never causes selection of another Publication.

---

## 30. Counter and usage recovery

### ACC-REC-007 — Higher counter accepted

Counter gaps are preserved.

### ACC-REC-008 — Lower counter rejected

A counter at or below an observed allocated maximum causes mechanical/manual repair boundary.

### ACC-REC-009 — No refunds

Discarded candidates/transactions do not lower:

```text
calls
retries
tokens
cost
elapsed time
allocated IDs
```

### ACC-REC-010 — Provider ambiguity

Crash after request send with unknown outcome uses conservative accounting and a new Call ID on retry.

---

## 31. Candidate and Review recovery

### ACC-REC-011 — Candidate only

Quarantine and regenerate; do not synthesize a manifest.

### ACC-REC-012 — Manifest only

Quarantine and regenerate.

### ACC-REC-013 — Raw success audit only

Repeat provider call; never promote the audit body.

### ACC-REC-014 — Valid candidate, Run state behind

Reconcile to Review without another generation call.

### ACC-REC-015 — Unreferenced Review

Do not promote; repeat Review.

### ACC-REC-016 — Valid referenced Review

Derive route without another Review call.

### ACC-REC-017 — Partial next version

Quarantine and use the following version number; do not reuse the partial number.

### ACC-REC-018 — Missing Context

Rebuild only if identical hash is reproduced; otherwise generate a new candidate version.

---

## 32. Transaction recovery

### ACC-REC-019 — Genesis matrix

Test staging-only, pre-HEAD final Generation, and post-HEAD Run-state-behind cases.

### ACC-REC-020 — Planning matrix

Test staging-before-move, final-plan-before-Run-state, and conflicting-final-plan cases.

### ACC-REC-021 — Scene matrix

Test every row of the Scene Generation transaction crash matrix.

### ACC-REC-022 — Handoff matrix

Test pre-HEAD orphan and post-HEAD reconciliation.

### ACC-REC-023 — Publication matrix

Test:

```text
partial OUT-01
finalized staging
passing Gate
renamed final root before CURRENT
both roots conflict
CURRENT changed before Run state
```

### ACC-REC-024 — Quarantine reachability

No path is quarantined before HEAD/CURRENT/Candidate/Checkpoint/transaction reachability is checked.

### ACC-REC-025 — Quarantine nonpromotion

Ordinary startup never promotes quarantine content.

### ACC-REC-026 — Idempotent startup

Two consecutive reconciliations with no intervening mutation produce no new ID, call, residual line, pointer change, or duplicate quarantine.

---

## 33. Stop and resume

### ACC-REC-027 — User stop safe boundary

A requested stop waits until the current atomic boundary completes and resumes from that durable boundary.

### ACC-REC-028 — Budget exhaustion

Stop occurs before the next forbidden LLM call.

Increasing a resume-increase-only budget permits resume without resetting usage.

### ACC-REC-029 — Paused

Paused state validates but does not continue without explicit resume.

### ACC-REC-030 — Recoverable failed

Explicit resume is permitted only after the registered cause is fixed and the exact next stage is known.

### ACC-REC-031 — Manual intervention

Invalid pointer graph, conflicting roots, counter regression, or Completion incomplete does not automatically resume.

### ACC-REC-032 — Completed

A completed run validates and remains completed; normal story generation cannot resume.

---

# Part VIII: Security and privacy acceptance

## 34. Secret handling

### ACC-SEC-001 — Credential absent everywhere

Run a full fake-credential success scenario and byte-search the entire workspace.

The credential value must not occur in any managed file.

### ACC-SEC-002 — Header redaction

Provider headers including Authorization, cookies, and secret vendor headers are absent/redacted in audits and exceptions.

### ACC-SEC-003 — Error sanitization

Simulated provider errors containing the credential and an external absolute path must be sanitized before storage/logging.

### ACC-SEC-004 — Private/public boundary

Byte-search publication payload for selected private truth strings present in:

```text
Initial design
Thread author truth
Knowledge author truth
Completion private audit
private Handoff
```

They must be absent unless the same text appears in adopted prose and is intentionally reader-facing.

### ACC-SEC-005 — Writer request boundary

Capture every prose-generation/revision request and assert private non-POV and author-only fields are absent.

### ACC-SEC-006 — Audit retention references

Retention must not delete an audit referenced by a retained Candidate manifest, Completion record, or Publication Gate.

### ACC-SEC-007 — External symlink

Attempt to place a secret file outside the workspace and reference it via symlink. Storycraft must reject the managed path without copying or logging the secret.

---

# Part IX: CLI and packaging acceptance

## 35. CLI behavior

### ACC-CLI-001 — Help without configuration

`storycraft --help` and subcommand help work without API credentials or workspace creation.

### ACC-CLI-002 — Exactly one input mode

`run` rejects:

```text
neither Brief nor Keywords
both Brief and Keywords
```

### ACC-CLI-003 — Workspace lock error

A second CLI writer reports a concise nonsecret error and nonzero exit.

### ACC-CLI-004 — Resume target

`resume --out <workspace>` derives the next stage from durable state and does not require resupplying Brief/Keywords.

### ACC-CLI-005 — Step

One `step` invocation completes at most one normative stage boundary and reports:

```text
completed stage
next stage
target
run status
```

It does not expose private Context or raw prompts.

### ACC-CLI-006 — Stop exit classes

Documented exit codes distinguish at least:

```text
success/completed step
user/budget/manual stop
usage/config error
mechanical failure
lock conflict
```

Exact numeric registry must be tested once defined.

### ACC-CLI-007 — No traceback for expected errors

Expected validation, budget, lock, and manual-intervention errors produce no Python traceback unless an explicit debug mode is enabled.

---

## 36. Packaging

### ACC-PKG-001 — Wheel build

The wheel builds from a clean checkout with declared build requirements.

### ACC-PKG-002 — Isolated install

Install the wheel into an empty virtual environment and run all CLI help smoke checks.

### ACC-PKG-003 — Packaged prompts and Schemas

Every prompt/system/user/Schema asset referenced by the stage registry is present in the installed wheel.

### ACC-PKG-004 — No source-tree dependency

Change the working directory outside the repository and verify the installed CLI still loads its packaged assets.

### ACC-PKG-005 — Version and compatibility

The installed package reports the expected version and rejects an unsupported workspace/Schema version before mutation.

### ACC-PKG-006 — Minimum Python

Run the core suite and wheel smoke under Python 3.11.

Additional supported Python versions declared by CI must run the same acceptance suite.

---

# Part X: Canonical integration fixtures

## 37. Fixture layout

Required fixture root:

```text
tests/fixtures/acceptance/
```

Recommended groups:

```text
schemas/
  valid/
  invalid/

contexts/
  writer-safe/
  private-review/
  completion/
  overflow/

workspaces/
  genesis/
  mid-scene-checkpoint/
  final-scene-pre-handoff/
  final-handoff/
  completed-publication/

provider-scripts/
  full-success.json
  structural-retry.json
  semantic-revision.json
  transport-failure.json
  completion-incomplete.json

expected/
  hashes.json
  stage-traces.json
  file-inventories.json
```

Fixtures may be generated by a deterministic builder, but committed expected hashes must be reviewed and versioned.

---

## 38. Fixture manifest

Every fixture workspace must include an external test-only fixture manifest, outside the simulated user workspace when possible.

It records:

```text
fixture ID
purpose
design-contract version
workspace version
builder version
expected HEAD
expected CURRENT
expected counters
expected file inventory hashes
private sentinel strings
created by deterministic fixture-builder version
```

The fixture manifest is not a production Storycraft record.

---

## 39. Canonical four-Volume success baseline

The mandatory full-success fixture is a four-Volume Japanese story.

### ACC-FIX-001 — Final Scene identity

The final adopted Scene is:

```text
v04-c003-s002
```

The final Story-clock time label is:

```text
最終日の夜
```

### ACC-FIX-002 — Scene count/order

The story contains exactly:

```text
47 adopted Scene commits
HEAD story_clock.current_order = 47
successful_scene_commits = 47
```

### ACC-FIX-003 — Final Scene Generation

Because three earlier Volume Handoff commits occur before the final Volume's last Scene:

```text
final Scene Commit/Generation ID = 00000050
```

Its Scene ID is `v04-c003-s002`.

### ACC-FIX-004 — Final Handoff Generation

After the final Scene, VH-ID creates the fourth Handoff commit:

```text
final HEAD Generation ID = 00000051
parent Generation ID = 00000050
commit_type = volume_handoff
current_order = 47
last_scene_id = v04-c003-s002
time_label = 最終日の夜
```

This replaces the obsolete assumption that Generation ID and Scene order are always equal.

### ACC-FIX-005 — Completion baseline

COMP-PRE and COMP-AUDIT use Generation `00000051`.

Every required Major Thread is:

```text
status = resolved
progress = 4
volume_disposition = resolve
```

Every required Ending criterion has supporting Evidence.

### ACC-FIX-006 — Publication

The success fixture produces one adopted Publication whose:

```text
output/CURRENT matches Publication ID
Manifest and Validation hashes verify
payload_set_sha256 verifies
content_set_sha256 verifies
Publication Gate passes
run_status = completed
last_completed_stage = OUT-03
```

### ACC-FIX-007 — File inventory

The expected fixture inventory includes exact hashes for:

```text
input artifacts
HEAD Generation roots/manifests
all adopted plans
final Scene artifact
all four Handoffs
Completion precondition/audit
Publication Gate
Publication Manifest/Validation
CURRENT
```

Tests need not hard-code the hash of every one of 47 prose files in each test; the fixture inventory must verify them collectively.

---

## 40. Residual-Issue integration fixture

### ACC-FIX-008 — Semantic exhaustion

At least one candidate family reaches semantic revision exhaustion with a mechanically valid candidate.

Assert:

```text
exact residual JSONL line
no duplicate on restart
safe residual constraint in relevant later Context
raw private Issue absent from Writer/publication
run may still complete when Completion permits it
```

---

## 41. Incomplete-Completion integration fixture

### ACC-FIX-009 — Incomplete result

The Completion fake returns one structurally valid `incomplete` result.

Assert:

```text
one saved valid attempt
no second Completion attempt
accepted private audit
OUT-01 payload build
OUT-02 passing mechanical Validation when payload is sound
COMP-PUBLISH Gate fail with COMPLETION_INCOMPLETE
no publications/<id> adoption
no output/CURRENT change
run stopped/manual_intervention
```

---

## 42. Structural-retry fixture

### ACC-FIX-010 — Retry separation

Script a logical stage with:

```text
transport failure
successful transport with invalid JSON
successful structurally valid candidate
semantic Review issue
complete revision
```

Assert independent exact counters and unique audit filenames.

---

## 43. Crash fixture matrix

### ACC-FIX-011 — Failpoint enumeration

For each atomic transaction, the suite must parameterize failpoints rather than implement one hand-written crash test.

Transactions:

```text
Genesis
Series plan adoption
Volume plan adoption
Chapter plan adoption
SC checkpoint
Prose checkpoint
Delta checkpoint
Scene commit
Volume-handoff commit
Publication adoption
```

For every failpoint, the expected post-restart action must be recorded as:

```text
reconcile
resume
regenerate
quarantine
explicit_recovery
manual_intervention
```

---

# Part XI: Prompt and Schema acceptance

## 44. Stage registry coverage

### ACC-PROMPT-001 — Every LLM stage registered

Every LLM stage has:

```text
processor/role
operation key
system prompt
user prompt
response format
Schema when structured
Context builder
Review/revision relationship
```

### ACC-PROMPT-002 — No orphan active asset

Every packaged active prompt/Schema is referenced by the stage registry.

Legacy inactive assets must be outside the active package path or explicitly marked inactive and excluded from runtime discovery.

### ACC-PROMPT-003 — Prompt/Schema version hashes

Changing an active prompt or Schema changes the corresponding bundle hash and invalidates incompatible candidate resume.

### ACC-PROMPT-004 — Structured-output exactness

The provider adapter sends the exact registered response Schema for structured stages.

Prose uses no JSON Schema response root.

### ACC-PROMPT-005 — Whole replacement

Every Revision prompt explicitly requires a complete replacement and the runtime rejects partial outputs regardless of prompt wording.

### ACC-PROMPT-006 — Evidence quote instruction

Continuity prompts require literal unique prose substrings, not paraphrases or summaries.

### ACC-PROMPT-007 — Author-truth boundary

Writer and Continuity prompt rendering cannot access private Context fields even if a template references a missing variable.

Undefined/private template access must fail closed.

### ACC-PROMPT-008 — Audit role filename

Rendered operation/role/round information produces the exact unique LLM-audit filename contract.

---

# Part XII: Performance and resource acceptance

## 45. Bounded behavior

### ACC-PERF-001 — Retry bounds

No loop can exceed configured bounds for:

```text
transport retries
response-structure retries
semantic revisions
Completion attempts
```

### ACC-PERF-002 — No Review-until-pass loop

A reviewer returning issues repeatedly reaches residual exhaustion; the runtime never calls it indefinitely until issues are empty.

### ACC-PERF-003 — No Completion-until-complete loop

A valid semantic `incomplete` result ends Completion attempts.

### ACC-PERF-004 — Context memory bound

Context Builder handles optional-record exclusion without duplicating complete manuscript text in memory beyond the documented implementation bound.

At minimum, a stress test must build a large valid Context without quadratic concatenation behavior.

### ACC-PERF-005 — Streaming/audit bound

Provider streaming and audit capture respect configured maximum body/audit size.

Truncation must follow the audit contract and never truncate candidate content silently.

### ACC-PERF-006 — Startup scaling

Startup validates pointer-selected authoritative graphs before broad orphan scans.

A workspace with many historical candidate/audit files must not change authority selection or exhaust memory through unbounded full-content loading.

---

# Part XIII: Release gates

## 46. Contract gate

A release candidate fails when any is true:

```text
a managed relative Markdown link is broken
a Stage ID is missing or duplicated
a canonical enum value is undocumented or inconsistent
an example JSON block intended as exact data does not parse
a deprecated artifact class appears in active contracts/code
an active path differs between layout, Runtime, and Pipeline contracts
an active prompt operation lacks a Context/Schema mapping
```

A documentation-lint script is strongly recommended.

---

## 47. Automated gate

Required:

```text
compileall passes
full unittest suite passes
wheel smoke passes
acceptance ID trace has no missing mandatory ID
no mandatory test uses real network
no skipped mandatory acceptance test
```

A test marked expected-failure or skipped does not satisfy its ID.

---

## 48. Fixture gate

Required fixture checks:

```text
all fixture JSON parses
all fixture roots reject unknown fields when mutated
all persistent references resolve
all stored hashes verify
all pointer graphs verify
all Evidence quotes/offsets/hashes verify
all candidate before values equal source State
all file inventories match
no credential/private sentinel leaks into publication
```

---

## 49. Reproducibility gate

Run the deterministic full-success integration twice in separate temporary roots with:

```text
same fake clock
same provider script
same configuration
same input
same fixture-builder version
```

Required equalities:

```text
all semantic/canonical artifact bytes
all hashes
all IDs
all stage traces
all provider request bodies
all counters
all final publication bytes
```

Paths containing the temporary workspace root must never appear in compared artifacts.

Timestamps are equal because the fake clock is equal.

---

## 50. Mutation gate

Before release, the suite must demonstrate that representative one-byte/one-field mutations are detected.

Required mutation targets:

```text
Brief
Candidate
Review
Context snapshot
Checkpoint prose
candidate delta before value
Evidence quote
Canon root
Story-state root
Commit manifest
Generation manifest
Scene manifest
Handoff
Completion audit
Publication Validation
Publication manifest
Publication Gate
HEAD
CURRENT
```

Each mutation must fail at the expected validation layer.

---

## 51. Crash gate

The parameterized failpoint suite must pass for every atomic transaction.

Required proof:

```text
no pointer references partial content
pre-pointer final-looking content is unadopted
post-pointer Run-state-behind is reconciled
no provider call repeats after a durable candidate/checkpoint boundary
no ID is reused
no counter is refunded
no quarantine item is auto-promoted
startup is idempotent
```

---

## 52. Security gate

Required:

```text
workspace byte-search finds no fake credential
publication byte-search finds no private sentinel
path traversal suite passes
symlink escape suite passes
expected errors contain no secret
audit redaction suite passes
Writer/Continuity request-boundary suite passes
```

---

## 53. Packaging gate

Required:

```text
isolated wheel build/install
CLI help smoke
packaged prompt/Schema registry completeness
run outside repository root
minimum Python 3.11 execution
no undeclared source-tree file dependency
```

---

## 54. Release evidence

The release record must contain:

```text
source revision
package version
design-contract revision/hash
Python versions
operating systems/filesystems tested
acceptance command outputs
acceptance-ID trace report
fixture-builder version
canonical success-fixture expected hashes
wheel filename/hash
known nonmandatory limitations
```

It must not contain credentials or private story data from a real user workspace.

---

# Part XIV: Implementation status rules

## 55. Status terminology

A component may be labeled:

### `not_started`

No production implementation.

### `partial`

Some code/tests exist, but one or more mandatory acceptance IDs are missing or failing.

### `contract_complete`

Field validators and local unit tests pass, but full pipeline/recovery/release gates are incomplete.

### `integration_complete`

Full deterministic lifecycle passes, but one or more packaging/security/crash/reproducibility release gates remain.

### `release_candidate`

All mandatory acceptance IDs and gates pass for the declared platform matrix.

### `released`

A release candidate has been packaged, archived with release evidence, and distributed through the project's chosen release process.

---

## 56. Prohibited status claims

The project must not claim:

```text
implementation complete
production ready
fully resumable
atomic
deterministic
secure
end-to-end complete
```

when the corresponding mandatory acceptance IDs are absent, skipped, or failing.

A successful happy-path demo alone is `partial`.

---

## 57. Current implementation comparison

The current repository's legacy tests and code may remain temporarily while implementation is replaced.

They do not satisfy this document merely because they test earlier concepts such as:

```text
critique passes
flat mutable state
raw Markdown LLM logs
legacy stage names
unversioned candidates
generic continuity payload
```

A test satisfies an acceptance ID only when it asserts the current normative contracts and paths.

Legacy tests that conflict with the current contracts must be:

- rewritten;
- moved to an explicitly legacy/nonrelease suite;
- or removed.

They must not make the release suite pass through obsolete behavior.

---

# Part XV: Acceptance matrices

## 58. Mandatory area matrix

| area | mandatory IDs |
|---|---|
| Core serialization | `ACC-CORE-001..005` |
| Path security | `ACC-PATH-001..007` |
| Configuration | `ACC-CFG-001..012` |
| Canon | `ACC-CANON-001..008` |
| Story state | `ACC-STATE-001..007` |
| Evidence/delta | `ACC-EVID-001..010` |
| Brief/Initial data | `ACC-INIT-DATA-001..009` |
| Planning data | `ACC-PLAN-DATA-001..005` |
| Scene data | `ACC-SCENE-DATA-001..007` |
| Review/audit | `ACC-REV-001..012` |
| Context | `ACC-CTX-001..016` |
| Runtime/layout | `ACC-RUN-001..019` |
| Input/Initial pipeline | `ACC-PIPE-INIT-001..007` |
| Planning pipeline | `ACC-PIPE-PLAN-001..007` |
| Scene pipeline | `ACC-PIPE-SCENE-001..012` |
| Scene commit | `ACC-COMMIT-001..014` |
| Volume Handoff | `ACC-VH-001..008` |
| Completion/output | `ACC-OUT-001..016` |
| Runtime recovery | `ACC-REC-001..032` |
| Security | `ACC-SEC-001..007` |
| CLI | `ACC-CLI-001..007` |
| Packaging | `ACC-PKG-001..006` |
| Fixtures | `ACC-FIX-001..011` |
| Prompts | `ACC-PROMPT-001..008` |
| Performance | `ACC-PERF-001..006` |

No area is optional for version-1 release.

---

## 59. Stage-to-acceptance matrix

| stage family | minimum acceptance groups |
|---|---|
| INPUT/INIT | Core, Config, Brief/Initial, Context, Runtime, `ACC-PIPE-INIT-*`, Recovery |
| SERIES/VOL/CH | Planning data, Context, Runtime, `ACC-PIPE-PLAN-*`, Recovery |
| SC | Scene data, Context, Review, `ACC-PIPE-SCENE-001..003`, Recovery |
| PROSE | Scene data, Writer Context, Review, `ACC-PIPE-SCENE-004..006`, Security |
| DELTA | Evidence, Continuity Context, Review, `ACC-PIPE-SCENE-007..010` |
| COMMIT | Ledger, Runtime manifests, `ACC-COMMIT-*`, Transaction recovery |
| VH | Story state, Handoff data, `ACC-VH-*`, Handoff recovery |
| COMP | Completion Review, Context, `ACC-OUT-001..004`, Completion recovery |
| OUT/Gate | Publication records, `ACC-OUT-005..016`, Publication recovery, Security |
| startup/resume | Runtime/layout, all `ACC-REC-*`, Path security |

---

## 60. Final release decision

Release is permitted only when all are true:

```text
every mandatory acceptance ID has a passing automated test
all canonical commands pass
all required fixtures validate
full-success lifecycle completes deterministically
residual-issue lifecycle completes where permitted
incomplete-Completion lifecycle stops correctly
all failpoint matrices pass
no secret/private sentinel leaks
wheel smoke passes outside the repository
release evidence is archived
implementation status is release_candidate or released
```

Any missing condition is a release blocker.

There is no manual waiver for:

```text
invalid adopted hash graph
pointer-last atomicity
ID non-reuse
credential leakage
Writer author-truth leakage
unknown-field acceptance
Completion-until-complete retry
Publication Gate/adoption separation
CURRENT or HEAD inference
```

---

## 61. Mechanical acceptance of this document

This acceptance document itself is valid only when:

```text
all ACC IDs are unique
all ACC ranges in the area matrix resolve to defined IDs
all relative document links resolve
all named Stage IDs exist in the canonical stage registry
all named paths match workspace_layout.md
all artifact classes match runtime_records.md
all fixture Generation/order assumptions match volume_handoff Commit behavior
no obsolete critique-pass or flat-candidate requirement is normative
```

A documentation-validation test must enforce these conditions.
