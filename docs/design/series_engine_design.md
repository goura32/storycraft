# Series engine design

This document is the normative implementation architecture for the Storycraft series-generation engine.

It defines:

- the executable boundary between CLI, engine, stage registry, storage, prompts, provider calls, ledgers, and publication;
- the proposed Python package structure and dependency direction;
- the lifecycle of `run`, `resume`, and `step`;
- how the 50 canonical Stages are dispatched without a monolithic conditional workflow;
- how complete files, immutable candidates, checkpoints, transactions, pointers, counters, and audits are stored;
- how LLM calls, retries, budgets, Context snapshots, and response validation are coordinated;
- how Genesis, plans, Scene commits, Volume Handoffs, Completion, and Publication are implemented;
- how startup recovery uses the same validators and authority rules as normal execution;
- how the current legacy modules are replaced without preserving obsolete behavior;
- implementation order, test seams, error taxonomy, observability, and release acceptance.

The canonical stage and transition registry is [`pipeline_contracts.md`](pipeline_contracts.md).

Ledger ownership is defined by [`ledger_contracts.md`](ledger_contracts.md).

Prompt and Schema assets are defined by [`prompt_template_design.md`](prompt_template_design.md).

Runtime authority and crash recovery are defined by [`runtime_and_recovery.md`](runtime_and_recovery.md).

Exact data and field contracts are defined by:

- [`configuration_contracts.md`](configuration_contracts.md)
- [`context_contracts.md`](context_contracts.md)
- [`workspace_layout.md`](workspace_layout.md)
- [`contracts/data/brief_and_initial.md`](contracts/data/brief_and_initial.md)
- [`contracts/data/planning_artifacts.md`](contracts/data/planning_artifacts.md)
- [`contracts/data/scene_artifacts.md`](contracts/data/scene_artifacts.md)
- [`contracts/data/review_and_audit.md`](contracts/data/review_and_audit.md)
- [`contracts/ledger/canon_records.md`](contracts/ledger/canon_records.md)
- [`contracts/ledger/story_state.md`](contracts/ledger/story_state.md)
- [`contracts/ledger/evidence_and_updates.md`](contracts/ledger/evidence_and_updates.md)
- [`contracts/ledger/runtime_records.md`](contracts/ledger/runtime_records.md)
- [`contracts/pipeline/input_and_initial.md`](contracts/pipeline/input_and_initial.md)
- [`contracts/pipeline/planning.md`](contracts/pipeline/planning.md)
- [`contracts/pipeline/scene_generation.md`](contracts/pipeline/scene_generation.md)
- [`contracts/pipeline/commit_and_output.md`](contracts/pipeline/commit_and_output.md)

The product-facing scope remains in [`../product/SPECIFICATION.md`](../product/SPECIFICATION.md).

The visual flow is summarized by [`series_engine_flow.md`](series_engine_flow.md), but this document is authoritative for implementation structure.

---

## 1. Engine goals

The engine must be:

```text
deterministic where code owns behavior
strict at every structured boundary
resumable from explicit durable authority
atomic at every adoption point
private by construction
testable without network or wall-clock waiting
inspectable through immutable audit records
packaged without source-tree dependency
```

A plausible generated story is not sufficient.

The implementation must also prove the complete path, hash, state, counter, and recovery contracts.

---

## 2. Non-goals

Version 1 does not implement:

```text
distributed workers
multiple concurrent writers for one workspace
remote database authority
cloud object-store transactions
automatic human approval workflow
automatic publication to a retailer
automatic rollback of HEAD or CURRENT
automatic migration of incompatible candidates
semantic repair during recovery
```

The architecture may leave explicit future extension points, but no version-1 behavior may depend on them.

---

## 3. Core architectural principle

The engine is a deterministic coordinator around immutable semantic candidates.

The LLM may propose:

```text
Brief content
Initial-design components
plans
Scene-card content
prose
continuity proposals
Volume Handoff content
Completion assessment
Review issues
complete replacement revisions
```

Code owns:

```text
Stage dispatch
Context selection
Schema selection
persistent IDs
hashes
offsets
before values
paths
timestamps
counters
retry accounting
artifact classes
manifest construction
adoption
resume and recovery
```

The model never controls execution state.

---

## 4. Authority hierarchy

The engine resolves authority in this order:

```text
valid canon/HEAD and output/CURRENT
→ valid Run state
→ selected Checkpoint manifest
→ selected Candidate manifest
→ referenced transaction manifest
→ referenced artifact file
→ immutable audit
→ normal log
```

A lower layer may provide evidence.

It may not replace an invalid higher authority.

---

## 5. Public process surface

The supported public commands are:

```text
storycraft run
storycraft resume
storycraft step
```

Their engine-level equivalents are:

```text
SeriesService.run(...)
SeriesService.resume(...)
SeriesService.step(...)
```

The service API remains thin.

All three commands enter the same:

```text
workspace lock
→ package/config validation
→ startup/recovery
→ Stage execution
```

path.

---

## 6. `run` semantics

`run`:

1. resolves and validates Effective config;
2. acquires the workspace lock;
3. proves that no existing initialized workspace is present;
4. creates the workspace roots and immutable Run manifest;
5. adopts exactly one normalized input source;
6. creates the initial Run state;
7. repeatedly executes canonical Stage boundaries;
8. stops only on:
   ```text
   completed
   safe user stop
   budget stop
   failed
   manual intervention
   ```
9. returns a structured result.

`run` does not overwrite or reuse an existing run.

---

## 7. `resume` semantics

`resume`:

1. acquires the workspace lock;
2. validates package/config compatibility;
3. validates authoritative pointers and Runtime roots;
4. performs deterministic startup recovery;
5. derives the exact next Stage;
6. continues until a terminal/safe stop.

The caller does not resupply Brief or Keywords.

A changed credential value may be read from the configured environment variable without changing Effective-config bytes.

---

## 8. `step` semantics

`step` completes at most one canonical Stage boundary.

It may perform internal substeps required to make that Stage durable, including:

```text
one or more transport attempts
response-structure retries
candidate and manifest writes
one pointer-last transaction owned by that Stage
```

It does not execute the next canonical Stage.

The result reports:

```text
completed_stage
next_stage
target
run_status
current HEAD/CURRENT
```

---

## 9. Single-writer process model

One workspace permits one mutating engine process.

Required lock behavior:

```text
exclusive OS-level ownership
diagnostic metadata in the lock file
no time-only stale-lock stealing
explicit failure when locking semantics are unsupported
```

Read-only external inspection may occur, but it must tolerate atomic replacement and immutable-directory rename.

---

## 10. Proposed package layering

Canonical implementation layers:

```text
CLI / public service
        ↓
Engine orchestration
        ↓
Stage registry and Stage executors
        ↓
Domain services
        ↓
Workspace repositories and atomic storage
        ↓
filesystem

Engine orchestration
        ↓
Context / Prompt / Provider adapters

Stage executors
        ↓
contract validators and canonical serializers
```

Dependencies flow downward.

Storage, validators, and provider adapters do not import the CLI.

---

# Part I: Package structure

## 11. Canonical source layout

Recommended package layout:

```text
src/storycraft/
  __init__.py
  cli.py
  public_api.py

  engine/
    __init__.py
    service.py
    engine.py
    registry.py
    stage_spec.py
    execution.py
    routing.py
    results.py
    errors.py
    stops.py

  stages/
    __init__.py
    input.py
    initial.py
    planning.py
    scene_card.py
    prose.py
    continuity.py
    scene_commit.py
    volume_handoff.py
    completion.py
    publication.py

  contracts/
    __init__.py
    canonical_json.py
    canonical_text.py
    identifiers.py
    paths.py
    enums.py
    schemas.py
    cross_artifact.py
    transitions.py
    publication.py

  domain/
    __init__.py
    canon.py
    story_state.py
    evidence.py
    planning.py
    scene.py
    review.py
    completion.py
    publication.py

  context/
    __init__.py
    registry.py
    builders.py
    snapshots.py
    projections.py
    token_budget.py

  prompts/
    __init__.py
    bundle.py
    renderer.py
    registry.py
    package_loader.py

  provider/
    __init__.py
    protocol.py
    adapter.py
    retries.py
    usage.py
    errors.py
    fakes.py

  runtime/
    __init__.py
    startup.py
    recovery.py
    reconciliation.py
    counters.py
    budget.py
    clock.py
    operation_audit.py

  storage/
    __init__.py
    workspace.py
    atomic.py
    lock.py
    pointers.py
    candidates.py
    checkpoints.py
    transactions.py
    ledgers.py
    plans.py
    audit.py
    quarantine.py

  templates/
    prompts/
      ...
```

Exact module names may be refined during implementation, but the responsibilities and dependency boundaries are normative.

---

## 12. Public API module

`public_api.py` exposes stable user-facing types:

```text
SeriesService
RunRequest
ResumeRequest
StepRequest
EngineResult
RunStatus
```

It does not expose:

```text
filesystem transaction objects
provider response objects
mutable Run-state dictionaries
raw Candidate manifests
private Context payloads
```

The public API accepts typed paths/config/input references and returns a redacted result.

---

## 13. Engine service

`engine/service.py` owns:

```text
workspace-path resolution
lock scope
new-run versus existing-run decision
Engine construction
public result mapping
expected exception translation
```

It must not contain 50-Stage business logic.

---

## 14. Engine coordinator

`engine/engine.py` owns the canonical execution cycle.

Conceptual interface:

```python
class Engine:
    def initialize(self, request: RunRequest) -> EngineResult: ...
    def recover(self) -> RecoveryResult: ...
    def execute_next_stage(self) -> StageExecutionResult: ...
    def run_until_stop(self) -> EngineResult: ...
```

The coordinator:

- reads current authority;
- obtains a `StageSpec`;
- invokes exactly one executor;
- validates the executor result;
- commits the Run-state transition;
- repeats when requested.

---

## 15. Stage registry

`engine/registry.py` contains the one canonical executable registry for all 50 Stage IDs.

Each entry defines at least:

```text
stage_id
family
processor_type
operation_key
target_kind
executor_key
normal transition resolver
resume authority resolver
artifact classes
Context builder when LLM
response format and Schema identity when LLM
```

The Prompt registry is cross-validated against this registry.

A second independent transition table is forbidden.

---

## 16. Stage specification type

Conceptual immutable type:

```python
@dataclass(frozen=True)
class StageSpec:
    stage_id: StageId
    family: StageFamily
    processor_type: ProcessorType
    operation_key: OperationKey | None
    target_kind: TargetKind
    executor_key: str
    context_builder_id: str | None
    prompt_stage_id: StageId | None
    artifact_classes: frozenset[ArtifactClass]
    transition_resolver: str
    resume_resolver: str
```

A `StageSpec` does not contain mutable workspace data.

---

## 17. Stage executor interface

Every executor implements a common interface:

```python
class StageExecutor(Protocol):
    def execute(
        self,
        request: StageExecutionRequest,
        services: EngineServices,
    ) -> StageExecutionResult:
        ...
```

`StageExecutionRequest` includes:

```text
Stage spec
validated Run state
target identity
validated authority snapshot
safe-stop token
```

Executors do not discover their own target by scanning directories.

---

## 18. Executor result

A successful `StageExecutionResult` contains:

```text
completed_stage
target
next_stage
next_target
run_status
durable_output_refs
pointer_changes
usage_delta already persisted
operation_audit_ref
```

It does not contain an instruction to bypass Run-state transition validation.

The coordinator independently validates the result against the Stage registry.

---

## 19. Engine services container

Executors receive explicit services:

```text
WorkspaceStore
ContractRegistry
ContextRegistry
PromptBundle
ProviderAdapter
CounterService
BudgetService
Clock
OperationAuditWriter
StopController
```

No executor imports a global singleton for mutable runtime behavior.

---

## 20. Dependency injection

Production builds `EngineServices` from package resources and the real filesystem/provider.

Tests inject:

```text
temporary WorkspaceStore
fake clock
scripted provider
deterministic tokenizer
fault-injecting atomic store
fake lock
fake capacity monitor
```

The same executor code runs under both.

---

# Part II: Workspace and storage architecture

## 21. Workspace store

`storage/workspace.py` is the root repository facade.

It exposes typed repositories rather than arbitrary path concatenation:

```text
runtime
input
canon
plans
artifacts
audit
publication
pointers
staging
quarantine
```

All relative paths are validated before filesystem access.

---

## 22. No generic mutable JSON store

A generic interface such as:

```python
store.save(state_dict)
```

is forbidden for the version-1 workspace.

Every durable object uses:

- an exact root Schema;
- an owning repository;
- canonical serialization;
- the correct atomicity rule;
- an explicit path constructor.

---

## 23. Canonical JSON service

`contracts/canonical_json.py` owns:

```text
NFC normalization
strict number validation
object-key ordering
contract-normalized array validation
compact UTF-8 serialization
final-LF policy
SHA-256
```

All JSON-writing repositories call this service.

No module uses an independent `json.dumps(..., indent=2)` for persisted canonical artifacts.

---

## 24. Canonical text service

`contracts/canonical_text.py` owns:

```text
prose normalization
LF conversion
BOM/control rejection
one final LF
prose-format checks
character count
pointer bytes
JSONL line bytes
```

Evidence offsets operate on canonical prose returned by this service.

---

## 25. Managed path service

`contracts/paths.py` validates:

```text
workspace-relative POSIX syntax
fixed-width coordinates
exact case
no traversal
no absolute path
no symlink/junction escape
root containment
publication-relative path rules
```

Repositories construct canonical paths through typed methods.

An LLM-provided path string is never passed directly to the filesystem.

---

## 26. Atomic file replacement

`storage/atomic.py` provides:

```text
write temporary sibling
flush file
fsync file
atomic replace
fsync containing directory
```

It returns a durable completion result only after the final required directory sync.

Expected platforms/filesystems are tested explicitly.

Unsupported semantics stop startup.

---

## 27. Immutable directory transaction

For Generation, Scene, Handoff, plan, and Publication moves:

```text
build complete staging directory
validate complete staging graph
fsync contents/directories as required
rename staging directory to final path
fsync parent
revalidate final graph
write adoption pointer or Run state
```

An existing conflicting final directory is not overwritten.

---

## 28. Pointer repository

`storage/pointers.py` owns:

```text
read/write canon/HEAD
read/write output/CURRENT
exact pointer syntax
pointer target validation hooks
atomic replacement
```

Only owning adoption executors can call the mutation methods.

General storage helpers expose read-only pointer access.

---

## 29. Runtime repository

The Runtime repository owns complete-file reads/writes for:

```text
run-manifest.json
run-state.json
counters.json
effective-config.json
```

Run state and counters are replaced atomically as whole validated objects.

No partial JSON field update is permitted.

---

## 30. Candidate repository

The Candidate repository:

- allocates the next version path without reusing a partial version;
- writes candidate bytes;
- writes version-local Review;
- writes complete Candidate manifest;
- validates same-directory containment;
- never selects the active version by scanning.

Selection comes from Run state.

---

## 31. Checkpoint repository

The Checkpoint repository owns the one active Scene checkpoint.

It writes:

```text
scene-card.json
prose.md
continuity-delta.json
commit-plan.json
checkpoint-manifest.json
```

The manifest phase is authoritative.

Writing an artifact and advancing the phase are separate durable boundaries.

---

## 32. Transaction repository

The transaction repository owns:

```text
Genesis staging
plan-adoption staging
Scene-commit staging
Handoff staging
Publication staging
```

Each transaction has a type-specific manifest and Validation.

The repository does not infer adoption from completed staging.

---

## 33. Ledger repository

The Ledger repository reads and validates:

```text
HEAD Generation
parent Generation
Commit manifests
Scene/Handoff source manifests
Canon/Knowledge/State/Evidence roots
```

It exposes an immutable `GenerationSnapshot`.

It never returns a partially validated group of roots.

---

## 34. Plan repository

The Plan repository reads immutable:

```text
Series map
Volume design
Chapter design
```

It validates the complete parent/source hash chain.

Adoption methods reject an existing different final file.

---

## 35. Audit repository

The Audit repository writes immutable unique records:

```text
LLM call
operation
Review
Completion
Publication Gate
error
recovery/quarantine
```

Normal logs are not stored through this repository.

Audit filename creation uses code-owned Call/operation identities.

---

## 36. Quarantine repository

Quarantine operations are atomic directory/file moves with an operation audit.

The repository requires a proved classification:

```text
unreferenced candidate
unreferenced checkpoint artifact
unreferenced Generation
unreferenced Scene
unreferenced Handoff
unreferenced Publication staging/final root
```

It exposes no method to promote quarantine during normal startup.

---

# Part III: Configuration, package, and startup

## 37. Configuration resolver

The configuration layer:

1. loads supported config sources in precedence order;
2. resolves defaults;
3. validates all fields and operation maps;
4. reads only the credential environment-variable name into Effective config;
5. materializes complete redacted bytes;
6. computes immutable fingerprint;
7. validates resume mutability.

Executors receive the validated Effective-config object, not raw YAML dictionaries.

---

## 38. Package validation

Before workspace mutation, startup validates:

```text
Python/package version
Stage registry
Prompt bundle
Schema bundle
all package asset hashes
template compilation
Context registry
contract registry
workspace/state compatibility declarations
```

A missing or conflicting package asset is a mechanical startup failure.

---

## 39. Startup modes

Canonical startup modes:

```text
new_run
resume
step_new
step_existing
inspect_read_only
```

Only the first four enter mutation.

`inspect_read_only` may be added as a separate CLI surface later; it is not a substitute for resume validation.

---

## 40. New workspace initialization

Initialization order:

1. validate requested output path and parent security;
2. acquire lock;
3. prove no initialized workspace;
4. create required top-level directories;
5. write Effective config;
6. write immutable Run manifest;
7. initialize counters;
8. normalize/adopt input source through INPUT-01;
9. write initial Run state;
10. fsync required roots;
11. return the first next Stage.

A partially initialized workspace is recovered or quarantined by explicit initialization transaction rules.

---

## 41. Existing workspace startup

Existing startup follows `runtime_and_recovery.md` exactly:

```text
security
foundational Runtime records
HEAD graph
CURRENT graph
Run-state comparison
active Checkpoint
active Candidate
referenced staging
orphan scan
```

No executor runs before startup returns a validated `ExecutionPosition`.

---

## 42. Execution position

Conceptual immutable result:

```python
@dataclass(frozen=True)
class ExecutionPosition:
    run_state: RunState
    next_stage: StageId | None
    target: TargetIdentity | None
    head: GenerationSnapshot | None
    current_publication: PublicationSnapshot | None
    active_candidate: CandidateSnapshot | None
    active_checkpoint: CheckpointSnapshot | None
    referenced_transaction: TransactionSnapshot | None
```

It contains validated snapshots, not raw paths alone.

---

## 43. Config compatibility on resume

Resume compares:

```text
immutable config fingerprint
workspace/state versions
code version policy
prompt bundle
Schema bundle
active candidate prompt/Schema versions
```

Permitted mutable or increase-only config changes are materialized through the config contract.

An incompatible change stops before any Stage mutation.

---

# Part IV: Canonical engine loop

## 44. Engine loop

Conceptual loop:

```python
while True:
    position = startup_or_reconcile()
    if position.run_state.is_terminal:
        return result(position)

    enforce_safe_stop_before_stage(position)
    spec = stage_registry[position.next_stage]
    executor = executors[spec.executor_key]

    result = executor.execute(
        StageExecutionRequest.from_position(position, spec),
        services,
    )

    validate_stage_result(spec, position, result)
    commit_run_state_transition(result)

    if step_mode:
        return result
```

Pointer-owning executors include their Run-state postcondition after pointer durability.

---

## 45. No giant `_run_one`

The engine must not implement the pipeline as:

```python
if state["brief"] is None:
    ...
elif state["characters"] is None:
    ...
elif ...
```

Reasons:

```text
implicit Stage identity
directory/content inference
untyped state dictionary
unscoped retries
no exact durable boundary
difficult failpoint coverage
recovery logic divergent from normal logic
```

Dispatch is exclusively by validated `next_stage`.

---

## 46. Stage precondition

Before invoking an executor, the coordinator validates:

```text
Run status permits execution
Run-state next_stage equals Stage ID
target matches Stage target kind
required authority snapshots exist
active Candidate/Checkpoint fields are permitted
budget/audit capacity allows the Stage
user stop is not pending before a new LLM call
```

Executor-specific validation then proves detailed sources.

---

## 47. Run-state transition

A Run-state transition is derived from:

```text
previous validated Run state
StageSpec
StageExecutionResult
current pointer graph
```

Required checks include:

```text
completed_stage is the invoked Stage
next edge exists
target is valid for next Stage
active Candidate/Checkpoint paths match durable outputs
status/stop fields are consistent
state_revision increments exactly once
```

---

## 48. Operation audit

Every code Stage writes an operation audit containing:

```text
operation identity
Stage/target
source authority refs/hashes
input Run-state revision
durable outputs
pointer changes
result classification
timing
error when applicable
```

The audit does not become an execution authority.

---

## 49. Safe stop controller

The process signal handler only requests a stop.

It must not directly:

```text
write Run state
delete staging
close in the middle of a pointer transaction
raise asynchronously inside atomic storage
```

The engine observes the request at registered safe boundaries and writes a deterministic stopped state.

---

## 50. Error translation

Internal exceptions are categorized before reaching CLI:

```text
UsageError
ConfigurationError
LockConflictError
MechanicalContractError
ProviderExhaustedError
BudgetStop
UserStop
ManualInterventionRequired
CompletedRunError
UnexpectedEngineError
```

Expected errors do not print a traceback unless debug mode is explicitly enabled.

---

# Part V: LLM execution service

## 51. Context builder registry

`context/registry.py` maps each LLM Stage to one exact builder.

A builder receives validated domain snapshots and returns a complete Context root.

It does not:

```text
render prompts
call provider
write candidate
allocate Call ID
```

---

## 52. Context snapshot creation

Context creation order:

1. obtain exact authority inputs;
2. project the permitted view;
3. apply deterministic selection/exclusion;
4. calculate payload and final token estimates;
5. build the timestamp-free Context root;
6. canonicalize and hash;
7. write to the hash-named path;
8. re-read and validate.

An identical Context is reused only when exact bytes/hash match.

---

## 53. Prompt render service

The render service:

- reads the Prompt Stage spec;
- validates Context identity;
- serializes `payload_json`;
- renders one system and one user message;
- attaches the exact Schema for structured Stages;
- performs complete request token preflight;
- returns immutable rendered request bytes.

It never receives credentials.

---

## 54. Provider adapter protocol

Conceptual protocol:

```python
class ProviderAdapter(Protocol):
    def call(
        self,
        request: ProviderRequest,
        *,
        timeouts: TimeoutPolicy,
    ) -> ProviderAttemptResult:
        ...
```

The adapter returns transport facts and raw response bytes.

It does not validate Storycraft response Schemas or choose retries.

---

## 55. Provider request identity

Every HTTP attempt binds:

```text
Call ID
Stage
target
audit role
logical candidate/attempt identity
transport attempt
prompt version
Schema version
Context hash
Effective-config hash
provider/model
timeout policy
```

The credential is added only at the transport-header layer.

---

## 56. Retry coordinator

The retry coordinator separates:

```text
transport retry
response-structure retry
semantic revision
Completion attempt
```

It uses configuration-specific limits and counters.

It cannot convert one category into another to keep trying.

---

## 57. Transport attempt

For every attempt:

1. preflight budget/audit capacity;
2. allocate and persist a Call ID;
3. create audit identity;
4. send request;
5. capture timings/usage/error;
6. write immutable call audit;
7. classify transport result.

An ambiguous crash after send consumes the Call ID and conservative usage on recovery.

---

## 58. Response validation

Structured response path:

```text
UTF-8 decode
JSON parse
strict response Schema
stage-specific normalization
stage-specific cross-field validation
candidate bytes
```

Prose response path:

```text
UTF-8 decode
canonical text normalization
prose structural validation
candidate bytes
```

Only structurally valid output proceeds to candidate storage or semantic Review.

---

## 59. Candidate durability

For a successful generation/extraction/revision:

1. determine immutable candidate version/path;
2. write canonical candidate;
3. write/replace complete Candidate manifest;
4. write operation audit;
5. update Run state to Review/checkpoint next Stage.

The provider call is not repeated after this complete durable boundary.

---

## 60. Review execution

A Review executor:

- reads the exact candidate version selected by Run state;
- builds private Review Context;
- invokes the generic Review Schema;
- normalizes issue IDs/order/counts;
- writes version-local `review.json`;
- updates the Candidate manifest status;
- routes to Revision or adoption/checkpoint.

It never edits the candidate.

---

## 61. Revision execution

A Revision executor:

- reads the selected current candidate and Review;
- builds a sensitivity-correct Revision Context;
- invokes the generator owner's response contract;
- writes the next immutable version;
- updates active Candidate selection;
- routes back to Review.

It does not patch the previous version.

---

## 62. Residual-issue exhaustion

When revision budget is exhausted:

1. prove the candidate is mechanically valid;
2. normalize current Review issues;
3. append duplicate-safe residual records;
4. mark the candidate exhausted/ready according to Runtime contract;
5. route to checkpoint/adoption.

Mechanical errors never enter residual issue storage.

---

## 63. Usage accounting

Usage service persists:

```text
LLM calls
transport retries
structure retries
revision rounds
Completion attempts
input/output/cached/reasoning tokens
estimated cost
active elapsed seconds
```

Accounting occurs at the exact contract-defined boundary.

Discarding a candidate does not refund usage.

---

## 64. Budget enforcement

Before a new provider attempt, the engine checks:

```text
Call count
estimated request/output tokens
cost
active elapsed time
audit capacity
```

A prohibited next call is not sent.

An already-started atomic filesystem transaction finishes before a safe stop.

---

# Part VI: Validation and domain services

## 65. Contract registry

`contracts/schemas.py` loads exact validators for:

```text
Effective config
Runtime roots
candidates
Reviews
checkpoints
Canon/Knowledge/State/Evidence
plans
Scene artifacts
Commit/Generation manifests
Completion records
Publication records
```

The registry is package-versioned and validated at startup.

---

## 66. Domain value types

Use immutable typed values for:

```text
StageId
GenerationId
CommitId
SceneId
VolumeId
ChapterId
PublicationId
CallId
PersistentStoryId
EvidenceId
RelativePath
Sha256
RFC3339Timestamp
```

Raw strings are parsed at repository or provider boundaries.

---

## 67. Exact unknown-field rejection

Structured data is validated twice when appropriate:

```text
provider response Schema
persisted artifact Schema
```

The normalized persisted artifact may contain code-owned fields absent from the provider response.

Each root and union branch rejects unknown fields.

---

## 68. Cross-artifact validator

`contracts/cross_artifact.py` validates relationships such as:

```text
Run state ↔ pointers
Candidate manifest ↔ candidate/Review/Context
Checkpoint ↔ phase-required files
plan ↔ parent/source hashes
State ↔ Canon
Evidence ↔ prose/Scene/Commit
committed delta ↔ root diff
Commit ↔ Generation ↔ Scene/Handoff
Validation ↔ Manifest ↔ Gate
```

Executors use the same validator as startup recovery.

---

## 69. Transition registry

`contracts/transitions.py` owns:

```text
Knowledge transitions
Thread transitions
record lifecycle
Volume disposition rules
Story-clock relation validation
Run status transitions
Candidate status transitions
Checkpoint phase transitions
```

No executor implements a local ad hoc enum matrix.

---

## 70. Scene authorization service

The Scene authorization service:

1. derives `allowed_update_targets` from frozen source State/plans;
2. injects starting values at SC-CHK;
3. validates normalized continuity candidate;
4. validates again at DELTA-CHK;
5. validates again before Commit.

Review cannot expand the authorization set.

---

## 71. Evidence service

The Evidence service:

```text
validates literal quote uniqueness
calculates code-point offsets
calculates quote/prose hashes
sorts allocation requests
creates Evidence records
validates index ordering
proves target/change relation
```

It never reads publication manuscript text as Scene evidence.

---

## 72. Merge service

The merge service accepts:

```text
parent Generation snapshot
frozen Scene artifacts
validated candidate delta
persisted ID allocations
```

It produces:

```text
resolved local-key map
Evidence mapping
committed delta
complete after roots
root-diff proof
route facts
```

It is a pure/deterministic domain service apart from code-owned timestamps supplied as input.

---

## 73. Generation builder

The Generation builder creates complete copy-on-write roots and manifests.

It supports exactly:

```text
initial_design
scene
volume_handoff
```

It cannot create a generic Commit branch.

---

## 74. Manifest builder

Manifest construction is dependency-ordered.

Scene:

```text
frozen Scene card/prose
→ committed delta
→ Scene manifest
→ Commit manifest
→ Generation manifest
```

Handoff:

```text
Handoff artifact
→ Commit manifest
→ Generation manifest
```

No builder accepts placeholder hashes.

---

# Part VII: Stage-family executors

## 75. Input executor

`stages/input.py` owns:

```text
INPUT-01
INPUT-02
INPUT-03
```

Responsibilities:

- normalize exactly one input mode;
- adopt human Brief directly when selected;
- generate content-only Brief from Keywords;
- add code-owned source/profile/timestamp metadata;
- establish the next Initial-design target.

---

## 76. Initial executor

`stages/initial.py` owns:

```text
INIT-01
INIT-02
INIT-03
INIT-04
INIT-05
INIT-06
INIT-REV
INIT-ID
```

INIT-ID uses a dedicated Genesis transaction.

Persistent IDs are allocated only after complete dry validation.

---

## 77. Planning executor

`stages/planning.py` owns all Series, Volume, and Chapter Stages.

It resolves:

```text
Genesis-fixed Series source
Volume-start HEAD
prior Volume Handoff
Chapter-start HEAD
prior Chapter final Scene handoff
immutable parent-plan hashes
```

Plan adoption does not change HEAD.

---

## 78. Scene-card executor

`stages/scene_card.py` owns:

```text
SC-01
SC-02
SC-REV
SC-CHK
```

SC-CHK freezes the complete code-owned Scene card and creates `CARD_ACCEPTED`.

It does not create prose.

---

## 79. Prose executor

`stages/prose.py` owns:

```text
PROSE-01
PROSE-02
PROSE-REV
PROSE-CHK
```

It uses Writer-safe Context only.

PROSE-CHK canonicalizes/finalizes prose and creates `PROSE_FROZEN`.

---

## 80. Continuity executor

`stages/continuity.py` owns:

```text
DELTA-01
DELTA-02
DELTA-REV
DELTA-CHK
```

It:

- extracts from exact frozen prose;
- injects code-owned before values;
- validates authorization and transition rules;
- freezes the candidate delta;
- creates `DELTA_ACCEPTED`.

It allocates no story or Evidence ID.

---

## 81. Scene-commit executor

`stages/scene_commit.py` owns:

```text
COMMIT-01
COMMIT-02
COMMIT-03
COMMIT-04
```

Its internal dependencies are:

```text
CommitPlanner
CounterService
EvidenceService
MergeService
GenerationBuilder
SceneManifestBuilder
TransactionRepository
PointerRepository
```

COMMIT-04 is the only Scene adoption Stage.

---

## 82. Volume-handoff executor

`stages/volume_handoff.py` owns:

```text
VH-01
VH-02
VH-REV
VH-ID
```

VH-ID proves that:

```text
Canon unchanged
Knowledge unchanged
Evidence unchanged
Story clock unchanged
only thread volume_disposition changed
```

It then adopts HEAD last.

---

## 83. Completion executor

`stages/completion.py` owns:

```text
COMP-PRE
COMP-AUDIT
COMP-SAVE
```

Noncyclic construction:

```text
precondition
→ Completion Context
→ saved attempt referring to both
→ accepted private audit
```

The first structurally valid assessment is selected.

Semantic `incomplete` is not retried.

---

## 84. Publication executor

`stages/publication.py` owns:

```text
OUT-01
OUT-02
COMP-PUBLISH
OUT-03
```

It implements:

```text
payload build
payload Validation
final Manifest
rename-stable Gate
directory rename
final-root revalidation
CURRENT replacement
completed Run state
```

It never changes story ledgers.

---

## 85. Route resolver

`engine/routing.py` derives routes from immutable plans and adopted manifests.

Examples:

```text
Scene commit:
  next Scene
  next Chapter
  VH-01

Handoff:
  next Volume
  COMP-PRE

Gate:
  OUT-03
  terminal manual stop
```

It does not scan for existing candidate or plan files to choose a route.

---

# Part VIII: Transactions and adoption

## 86. Genesis transaction

Genesis transaction state:

```text
accepted integrated bundle
dry validation
persisted story-ID allocations
complete roots/manifests
initial-design snapshot
passing transaction Validation
final directory moves
HEAD replacement
Run-state transition
```

A crash before HEAD leaves Genesis unadopted.

A crash after HEAD reconciles Run state.

---

## 87. Plan-adoption transaction

Plan adoption:

```text
ready candidate
source/parent hash recheck
code-owned metadata
staging write
Validation
final move
Run-state transition
```

There is no pointer file for plans.

Recovery uses the final expected path plus exact transaction/Run identity, never “newest plan.”

---

## 88. Scene transaction

Scene commit boundaries:

```text
COMMIT-01:
  no allocation

COMMIT-02:
  persist allocation
  merge plan
  staged roots

COMMIT-03:
  committed artifacts/manifests
  transaction Validation
  COMMIT_PREPARED

COMMIT-04:
  final moves
  revalidation
  HEAD last
  Run-state route
```

---

## 89. Handoff transaction

VH-ID:

1. validates ready Handoff;
2. validates final Scene HEAD;
3. allocates Commit/Generation;
4. constructs disposition-only child State;
5. builds Handoff/Commit/Generation;
6. validates complete graph;
7. moves final artifacts;
8. replaces HEAD;
9. updates Run state.

---

## 90. Publication transaction

Publication identity is allocated in OUT-01.

OUT-02 finalizes noncyclic Validation/Manifest hashes.

COMP-PUBLISH creates the external Gate.

OUT-03 selects exactly one root:

```text
normal:
  .staging/publication/<id>/

explicit post-rename recovery:
  publications/<id>/
```

It validates the same snapshot before CURRENT.

---

## 91. Pointer-last enforcement

Pointer mutation methods require an ownership token created by the active adoption executor.

Conceptually:

```text
HeadAdoptionToken:
  INIT-ID / COMMIT-04 / VH-ID only

CurrentAdoptionToken:
  OUT-03 only
```

This prevents an unrelated helper or recovery scan from rewriting pointers.

---

## 92. Post-pointer reconciliation

After a valid pointer changes, adoption is complete even if:

```text
Run state is behind
operation audit is missing
cleanup is incomplete
```

Startup:

- validates the pointer graph;
- reconstructs the route;
- updates Run state;
- records recovery;
- performs safe cleanup.

It does not repeat semantic/provider work.

---

# Part IX: Recovery architecture

## 93. Recovery coordinator

`runtime/recovery.py` uses typed classifiers:

```text
reconcile
resume
regenerate
quarantine
explicit_recovery
manual_intervention
```

It returns actions.

It does not directly perform hidden semantic mutation while classifying.

---

## 94. Candidate recovery

Cases:

```text
candidate + valid manifest:
  resume/reconcile

candidate only:
  quarantine and regenerate

manifest only:
  quarantine and regenerate

raw successful audit only:
  repeat provider call

unreferenced Review:
  do not promote; repeat Review

valid referenced Review:
  derive route without provider call
```

---

## 95. Checkpoint recovery

Recovery selects only the Run-state-expected Scene checkpoint.

It validates:

```text
source HEAD
phase
phase-required files
candidate-manifest links
hashes
target not already adopted
```

Unreferenced later-phase files are quarantined.

---

## 96. Transaction recovery

A referenced transaction may be resumed only under its detailed contract.

Examples:

```text
COMMIT_PREPARED:
  COMMIT-04

passing finalized Publication staging + Gate:
  OUT-03

post-rename Publication + original Gate:
  explicit OUT-03 recovery
```

Unreferenced completed staging is not automatically adopted.

---

## 97. Pointer reconciliation

HEAD reconciliation derives from Commit type:

```text
initial_design:
  SERIES-01

scene:
  next Scene / Chapter / Handoff

volume_handoff:
  next Volume / Completion
```

CURRENT reconciliation derives:

```text
run_status = completed
next_stage = null
current_publication_id = CURRENT
```

---

## 98. Idempotency

Running startup recovery twice without intervening mutation must not create:

```text
new Call ID
new persistent ID
new residual issue
new candidate version
new quarantine copy
new pointer value
new usage
```

Operation audits may record one recovery operation only when the first run made a durable change.

---

## 99. Manual-intervention boundary

The recovery coordinator returns manual intervention for:

```text
invalid HEAD/CURRENT graph
counter regression
conflicting final/staging roots
conflicting immutable plan
unsupported migration
ambiguous pointer ownership
valid Completion incomplete
```

It does not choose the “most likely” story truth.

---

# Part X: CLI, observability, and results

## 100. CLI architecture

`cli.py` performs only:

```text
argument parsing
request construction
service invocation
human-readable result/error rendering
process-level signal registration
exit-code mapping
```

It does not:

```text
open Canon files
select templates
perform retries
write Run state
construct provider logs
choose next Stage
```

---

## 101. CLI input

`run` supports exactly one:

```text
--brief <JSON/YAML path>
--keywords <value> repeated
```

`step` accepts input only when initializing a new workspace.

`resume` accepts no input source.

---

## 102. Exit-code registry

Define and test stable exit classes:

```text
0:
  completed or successful step boundary

2:
  CLI usage/configuration error

3:
  safe user/budget/manual stop

4:
  lock conflict

5:
  mechanical contract failure

6:
  provider exhaustion

1:
  unexpected internal failure
```

Exact numeric values may be adjusted once, but must then be canonical and tested.

---

## 103. Engine result

A redacted `EngineResult` includes:

```text
run_id
run_status
completed_stage
next_stage
target
workspace path supplied by caller
HEAD Generation
CURRENT Publication
safe stop/error code
reader-facing output paths when adopted
```

It excludes private audit/Context content.

---

## 104. Structured logging

Normal logs use structured fields conceptually equivalent to:

```text
event
run_id
Stage
target
status
state_revision
HEAD
CURRENT
Call ID when applicable
duration
error code
```

Logs do not become resume authority.

---

## 105. Secret redaction

The logging/error boundary redacts:

```text
credential values
Authorization/cookies
provider secret headers
external absolute paths when not operationally necessary
private request bodies unless audit policy explicitly retains redacted bytes
```

Expected exceptions implement safe public messages separately from private diagnostics.

---

## 106. Progress reporting

Progress is derived from immutable plans and Run target coordinates.

It may report:

```text
Volume N/total
Chapter N/total
Scene N/total
current Stage
```

It must not infer completion from directory count.

---

# Part XI: Testability and performance

## 107. Deterministic clock

All code-owned timestamps and elapsed-time checks use injected interfaces:

```text
WallClock.now()
MonotonicClock.now()
Sleeper.sleep()
```

Mandatory tests use fakes and never wait in real time.

---

## 108. Scripted provider

The provider fake supports:

```text
success
transport error
HTTP error
timeouts
invalid UTF-8
invalid JSON
Schema failure
prose-format failure
semantic Review issues
Completion incomplete
usage/timing variants
```

It records exact rendered requests for golden/privacy tests.

---

## 109. Fault injection

Atomic storage exposes registered failpoints around:

```text
temporary write
file fsync
atomic replace
directory fsync
directory rename
pointer replace
Run-state replace
audit write
```

The production path has near-zero branching overhead when failpoints are disabled.

---

## 110. Pure domain tests

These services should be testable without a workspace:

```text
canonical serialization
ID parsing
transition validation
Context projection
Evidence offset calculation
delta normalization
merge-plan construction
root-diff proof
route derivation
manifest dependency ordering
Publication hash-set calculation
```

---

## 111. Integration test seam

A complete engine integration test injects:

```text
temporary directory
package test bundle
fake clock
scripted provider
deterministic tokenizer
fault injector
fake lock/capacity
```

It uses public service methods, not private mutation helpers.

---

## 112. No real network

Mandatory tests fail if an unmocked socket opens.

Provider integration tests requiring a real endpoint are optional and outside the release acceptance suite.

---

## 113. Memory behavior

The engine avoids one giant mutable in-memory series dictionary.

It loads:

```text
one validated Generation snapshot
one target plan chain
one active Context/candidate/checkpoint family
selected Evidence/prose needed by the Stage
```

Large manuscript publication uses deterministic streaming/iterative assembly where possible.

---

## 114. Context construction performance

Context builders:

- use indexed Canon/State lookups;
- avoid repeated full-root scans;
- remove optional records deterministically;
- avoid quadratic string concatenation;
- calculate final request tokens once per rendered candidate request.

---

## 115. Startup performance

Startup validates pointer-selected graphs before orphan history.

Historical candidates/audits are scanned by metadata/path and loaded lazily where possible.

Authority selection must not depend on a full-content newest-file scan.

---

# Part XII: Legacy replacement

## 116. Current legacy modules

The current source contains modules such as:

```text
series_engine.py
series_workflow.py
series_store.py
series_contracts.py
series_model.py
series_output.py
prompt_template.py
llm.py
```

They represent the previous prototype architecture and are not the normative module boundaries.

---

## 117. `SeriesWorkflow` replacement

The legacy inheritance-based `SeriesWorkflow`:

```text
stores the whole series in one mutable dict
derives next work from missing dictionary fields
combines generation, Review, retry, and persistence
uses one large conditional `_run_one`
```

It must be replaced by:

```text
Engine
StageRegistry
StageExecutor implementations
typed repositories
typed domain services
```

No compatibility wrapper may preserve the old internal state file as authority.

---

## 118. `StateStore` replacement

A store that serializes one complete legacy state dictionary is deprecated.

It is replaced by repositories for:

```text
Run roots
Candidates
Checkpoints
Generations
plans
Scene/Handoff artifacts
Completion
Publication
audits
```

There is no automatic conversion from legacy state version 5 to the version-1 contract workspace.

---

## 119. `ContractValidator` replacement

One broad class containing all validation methods is replaced by:

```text
exact root validators
domain transition services
cross-artifact graph validators
stage-specific precondition validators
```

Shared registries remain centralized; unrelated domains are not coupled through inheritance.

---

## 120. `StoryModel` replacement

A model abstraction that accepts arbitrary stage/category strings is replaced by:

```text
Prompt Stage registry
rendered ProviderRequest
ProviderAdapter protocol
RetryCoordinator
ResponseValidator
```

The provider does not select a Schema by filename inference.

---

## 121. Raw log replacement

Legacy sequential raw Markdown/JSON logs such as:

```text
raw/0001-...
```

do not satisfy the audit contract.

They are replaced by unique immutable LLM-call audit records whose filename and body bind:

```text
Call ID
Stage
target
role
attempt/revision identity
```

Human-readable diagnostics may be derived, but they are not authority.

---

## 122. Prompt loader replacement

Legacy behavior:

```text
one common JSON system prompt
category/stage filename inference
critique special case
source-tree fallback
generic kwargs
```

is replaced by the package-only immutable Prompt bundle defined in `prompt_template_design.md`.

---

## 123. Output writer replacement

A writer that directly writes final manuscript files during story generation is replaced by the Publication transaction:

```text
OUT-01 payload
OUT-02 Validation/Manifest
COMP-PUBLISH Gate
OUT-03 adoption
```

Reader-facing files are not considered adopted before CURRENT.

---

## 124. Legacy test handling

Legacy tests that assert:

```text
flat state dictionaries
legacy stage names
volume_map/timeline/closure
critique loops
raw logs
flat output paths
```

must be rewritten, moved to a clearly nonrelease historical suite, or removed.

They do not satisfy current acceptance IDs.

---

# Part XIII: Implementation order and release

## 125. Phase 1 — Foundations

Implement first:

```text
typed IDs/paths
canonical JSON/text
hash utilities
atomic replacement
lock
exact Runtime/config validators
package Prompt/Schema loader
```

No pipeline executor should be implemented on placeholder serialization.

---

## 126. Phase 2 — Runtime and registry

Implement:

```text
Stage registry
Run manifest/state/counters repositories
public service and Engine loop
startup validation
safe stop/error taxonomy
operation audit
```

Use code-only test Stages/fakes before LLM semantics.

---

## 127. Phase 3 — Candidate/LLM framework

Implement:

```text
Context snapshots
Prompt renderer
Provider adapter
retry coordinator
LLM-call audits
Candidate/Review/version repositories
generic Review/Revision orchestration
```

Prove raw-audit nonpromotion and candidate durability boundaries.

---

## 128. Phase 4 — Genesis and planning

Implement:

```text
INPUT
INIT
Genesis transaction
Series/Volume/Chapter planning
immutable plan adoption
```

Run the complete Initial/planning fixture.

---

## 129. Phase 5 — Scene pipeline

Implement:

```text
Scene card
Writer-safe prose
continuity extraction
Checkpoint phases
Evidence
merge service
Scene transaction
```

Run the representative Scene fixture and failpoint matrix.

---

## 130. Phase 6 — Handoff, Completion, Publication

Implement:

```text
Volume Handoff transaction
Completion precondition/Context/attempt/save
Publication payload/Validation/Manifest/Gate/adoption
CURRENT recovery
```

Run success, residual, and incomplete fixtures.

---

## 131. Phase 7 — Recovery and packaging

Complete:

```text
all startup classifiers
quarantine
counter/usage reconciliation
wheel package assets
CLI exit behavior
full reproducibility/security/crash gates
```

Do not claim implementation completion before this phase passes.

---

## 132. Acceptance mapping

Primary acceptance groups:

```text
ACC-CORE-*
ACC-PATH-*
ACC-CFG-*
ACC-CTX-*
ACC-RUN-*
ACC-PIPE-*
ACC-COMMIT-*
ACC-VH-*
ACC-OUT-*
ACC-REC-*
ACC-SEC-*
ACC-CLI-*
ACC-PKG-*
ACC-FIX-*
ACC-PROMPT-*
ACC-PERF-*
```

Every engine component must list the acceptance IDs covered by its tests.

---

## 133. Release status

Implementation status terminology follows `implementation_acceptance.md`.

A working happy-path CLI is at most:

```text
partial
```

until crash, privacy, packaging, and deterministic fixture gates pass.

---

# Part XIV: Security and extension boundaries

## 134. Filesystem trust boundary

The workspace is untrusted on startup.

The engine validates:

```text
path syntax
case
symlinks/junctions
pointer bytes
Schema
hash graphs
unexpected files at authoritative roots
```

It does not deserialize arbitrary Python objects or execute workspace content.

---

## 135. Model trust boundary

Provider output is untrusted bytes.

Even strict structured output remains subject to:

```text
UTF-8
JSON
Schema
stage normalization
cross-artifact validation
authorization
semantic Review where required
```

Prose is never parsed as an instruction to the engine.

---

## 136. Plugin boundary

Version 1 has no runtime third-party Stage plugin system.

Future plugins would require:

```text
signed/versioned registry extension
new artifact/path/Schema authority
sandbox/security review
compatibility rules
acceptance IDs
```

Arbitrary Python entry-point discovery is outside scope.

---

## 137. Multiple-provider boundary

The ProviderAdapter permits additional providers only when they implement:

```text
strict response Schema compatibility
timeout semantics
usage mapping
error classification
audit redaction
deterministic request identity
```

Provider-specific fallback behavior may not weaken Storycraft contracts.

---

## 138. Remote-storage boundary

Remote object storage is not supported by version 1.

A future implementation must provide equivalents for:

```text
exclusive writer
atomic complete-file replacement
conditional pointer update
directory transaction semantics
durable listing/reachability
```

It cannot emulate local atomicity through best-effort multiple writes.

---

## 139. Human intervention boundary

Manual intervention may inspect and repair a copied workspace through a documented future tool.

Normal engine code does not include hidden “force latest” options.

Any repair tool must create an explicit immutable repair audit and revalidate the complete graph.

---

# Part XV: Forbidden architecture shortcuts

## 140. Forbidden orchestration

Forbidden:

```text
one mutable series dict
one giant conditional workflow
derive Stage from missing fields
advance more than one Stage in step
let executor choose an unregistered next Stage
```

---

## 141. Forbidden storage

Forbidden:

```text
pretty JSON as canonical data
in-place file editing
overwrite candidate versions
overwrite adopted plans/Generations
select newest directory
write pointer before final graph
```

---

## 142. Forbidden LLM integration

Forbidden:

```text
arbitrary stage string
Schema filename inference
free-form JSON fallback
global mutable prompt singleton
credential in Context/template
provider response promoted from audit
```

---

## 143. Forbidden recovery

Forbidden:

```text
set HEAD to highest Generation
set CURRENT to highest Publication
synthesize Candidate manifest
promote unreferenced Review
rebase stale Scene checkpoint
refund counters/usage
auto-promote quarantine
```

---

## 144. Forbidden semantic repair

Recovery and code-only stages must not:

```text
invent prose
change author truth
change a plan to fit generated prose
add Evidence without an adopted quote
change Completion incomplete to complete
rewrite Handoff to make final State valid
```

---

# Part XVI: Mechanical acceptance

## 145. Architecture acceptance

The engine architecture is acceptable only when tests demonstrate:

```text
thin CLI/public service
one canonical 50-Stage registry
no giant conditional Stage inference
typed immutable Stage specs
one executor per responsibility/family
validated executor result transitions
dependency injection

complete-file canonical repositories
atomic file and directory operations
pointer ownership and pointer-last
candidate/checkpoint/transaction repositories
no newest-file authority
quarantine nonpromotion

package/config validation before mutation
single startup/recovery path
new/run/resume/step semantics
exclusive writer
Run-state state_revision behavior
safe stops and expected error translation

Context/Prompt/Provider separation
30 LLM Stage registry cross-validation
Call-ID persist-before-use
retry-category separation
candidate durability
Review/Revision immutability
residual exhaustion
usage/budget accounting

exact validators and transition registries
Scene authorization
Evidence code-point offsets
merge and root-diff proof
noncyclic manifests
three Commit branches
Generation/order distinction

Input/Initial/Planning executors
Scene-card/Prose/Continuity Checkpoints
four-stage Scene Commit
Handoff disposition-only behavior
Completion noncyclic identity
valid incomplete nonretry
Publication Gate/adoption separation

startup Candidate/Checkpoint/transaction recovery
pointer reconciliation
explicit Publication recovery
idempotency
manual-intervention boundaries

structured logging and redaction
deterministic fakes/failpoints
no real network in mandatory tests
memory/startup scaling
wheel package behavior

legacy state/workflow/store/prompt/output replacement
implementation phase order
acceptance-ID traceability
security and future-extension boundaries
forbidden shortcut rejection
relative-link resolution
```

---

## 146. Final implementation invariant

At every observable boundary, the engine must be able to answer from durable validated data:

```text
Which run is this?
Which exact Stage and target are active?
Which input/source Generation was used?
Which candidate/checkpoint/transaction is selected?
Which IDs and usage have been consumed?
Which story Generation and Publication are adopted?
What exact next Stage is legal?
What will recovery do after a crash here?
```

If any answer depends on:

```text
the newest file
an in-memory dictionary
a normal log line
an LLM claim
an unreferenced staging directory
```

the implementation is not contract-complete.
