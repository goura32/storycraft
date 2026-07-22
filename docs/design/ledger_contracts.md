# Ledger contracts index and integration rules

This document is the normative integration contract for Storycraft's story, evidence, and execution ledgers.

It defines:

- the authority and boundary of each ledger;
- the relationship between immutable Canon generations and mutable execution state;
- how candidate proposals become adopted records, State changes, and Evidence;
- how Commit and Generation manifests bind the ledgers into one atomic snapshot;
- the special rules for Genesis, Scene commits, and Volume-handoff commits;
- which pipeline stages may read or write each ledger;
- identifier, hash, ordering, and resume invariants shared across ledger documents;
- forbidden cross-ledger shortcuts.

The field-level authorities are:

- [`contracts/ledger/canon_records.md`](contracts/ledger/canon_records.md)
- [`contracts/ledger/story_state.md`](contracts/ledger/story_state.md)
- [`contracts/ledger/evidence_and_updates.md`](contracts/ledger/evidence_and_updates.md)
- [`contracts/ledger/runtime_records.md`](contracts/ledger/runtime_records.md)

This index does not replace those exact Schemas. When a field-level rule appears more specific, the field-level document is authoritative.

Related integration authorities are:

- [`configuration_contracts.md`](configuration_contracts.md)
- [`context_contracts.md`](context_contracts.md)
- [`workspace_layout.md`](workspace_layout.md)
- [`runtime_and_recovery.md`](runtime_and_recovery.md)
- [`pipeline_contracts.md`](pipeline_contracts.md)
- [`contracts/data/brief_and_initial.md`](contracts/data/brief_and_initial.md)
- [`contracts/data/planning_artifacts.md`](contracts/data/planning_artifacts.md)
- [`contracts/data/scene_artifacts.md`](contracts/data/scene_artifacts.md)
- [`contracts/data/review_and_audit.md`](contracts/data/review_and_audit.md)
- [`implementation_acceptance.md`](implementation_acceptance.md)

---

## 1. Ledger model

Storycraft uses four logically separate ledger families.

| ledger family | primary responsibility |
|---|---|
| Canon ledger | fixed story identity, immutable facts, narrative structures, and knowledge-item definitions |
| Story-state ledger | current mutable values at one adopted Generation |
| Evidence/update ledger | prose-grounded proposed and committed changes, Evidence records, and change correspondence |
| Runtime ledger | execution identity, candidates, checkpoints, counters, manifests, pointers, publication records, and resume state |

The first three are story-domain ledgers.

The Runtime ledger is an execution ledger. It does not itself define story truth, but it determines which story-domain snapshot is adopted.

---

## 2. Adopted story snapshot

One adopted story snapshot is selected by:

```text
canon/HEAD
```

`canon/HEAD` names one immutable Generation directory:

```text
canon/generations/<generation-id>/
```

That directory contains exactly:

```text
current-canon.json
knowledge-items.json
story-state.json
evidence-index.json
commit-manifest.json
generation-manifest.json
```

The four root files together are the story snapshot:

| root | content |
|---|---|
| `current-canon.json` | fixed Canon records other than Knowledge items |
| `knowledge-items.json` | fixed Knowledge-item definitions |
| `story-state.json` | mutable Character, Relationship, Thread, Knowledge-audience, and Story-clock values |
| `evidence-index.json` | adopted prose Evidence records |

The two manifests prove:

- which Commit created the snapshot;
- which parent Generation preceded it;
- which Scene or Volume Handoff caused it;
- the exact hash of every root;
- the exact adopted artifact graph.

---

## 3. Pointer authority

### 3.1 Story pointer

```text
canon/HEAD
```

is the story-adoption point.

A Generation directory is not adopted merely because it exists.

### 3.2 Publication pointer

```text
output/CURRENT
```

is the publication-adoption point.

A Publication directory is not adopted merely because it exists.

### 3.3 Runtime state

```text
runtime/run-state.json
```

is the execution-position authority after valid adopted pointers are established.

A valid adopted pointer overrides a Run state that is behind.

A Run state may never override an invalid or absent pointer by inference.

---

## 4. Single-source-of-truth matrix

| concern | source of truth |
|---|---|
| Canon record identity and fixed fields | `current-canon.json` |
| Knowledge-item identity and fixed fact | `knowledge-items.json` |
| Character current values | `story-state.json.character_states` |
| Relationship current values | `story-state.json.relationship_states` |
| Thread status/progress/disposition | `story-state.json.thread_states` |
| Character/Reader knowledge status | `story-state.json.knowledge_states` plus sparse defaults |
| current time and Scene position | `story-state.json.story_clock` |
| adopted prose support | `evidence-index.json` |
| exact change applied by a Scene | adopted committed continuity delta |
| adopted Scene file identity | `scene-manifest.json` |
| Commit identity and root hashes | `commit-manifest.json` |
| Generation identity and parent/source graph | `generation-manifest.json` |
| current Generation | `canon/HEAD` |
| current execution stage | `runtime/run-state.json` |
| ID allocation | `runtime/counters.json` |
| active candidate | Run-state-selected `candidate-manifest.json` |
| active Scene checkpoint | Run-state-selected `checkpoint-manifest.json` |
| current publication | `output/CURRENT` |
| publication file graph | `publication-manifest.json` |
| publication eligibility | external Publication Gate |

No lower-level artifact may replace its designated authority.

---

# Part I: Canon ledger

## 5. Canon ledger roots

Canonical paths within a Generation:

```text
canon/generations/<generation-id>/current-canon.json
canon/generations/<generation-id>/knowledge-items.json
```

Exact roots:

```text
current-canon.json:
  {"records":[...]}

knowledge-items.json:
  {"items":[...]}
```

`current-canon.json` must not contain Knowledge-item records.

`knowledge-items.json` must not contain any other Canon record type.

---

## 6. Canon record families

`current-canon.json` contains:

```text
Character
Relationship
World entity
Temporal rule
Thread
Ending criterion
```

`knowledge-items.json` contains:

```text
Knowledge item
```

The exact fields, enums, lifecycle rules, and cross-reference rules are defined only by `canon_records.md`.

---

## 7. Fixed versus mutable information

Canon stores stable identity and invariant narrative meaning.

Story state stores current mutable values.

Examples:

| concept | Canon | Story state |
|---|---|---|
| Character name | yes | no |
| Character speech anchor | yes | no |
| Character current location | no | yes |
| Character current goal | no | yes |
| Relationship participants/type/origin | yes | no |
| current trust/perception/intention | no | yes |
| Thread description/author truth/resolution condition | yes | no |
| Thread status/progress/disposition | no | yes |
| Knowledge canonical fact | yes | no |
| who knows the fact | no | yes |
| Temporal fixed rule | yes | no |
| current story time | no | yes |

The same logical value must not be duplicated across Canon and State.

---

## 8. `canon/initial-design.json`

Canonical path:

```text
canon/initial-design.json
```

This is an immutable adopted design snapshot.

It may contain:

```text
accepted Initial-design content
private author truth
protagonist and Relationship arcs
accepted Major Thread/Ending design
Brief and bundle hashes
adopted ID inventories
Genesis Commit identity
```

It is not:

```text
the current Canon root
a mutable State file
a Generation
a substitute for current-canon.json
```

Later stages read safe or private projections from it through Context builders.

---

## 9. Canon enum ownership

Domain enums such as:

```text
record_origin
record_lifecycle
thread_type
thread_status
thread_action
knowledge status
scope
volume_disposition
```

are owned by `canon_records.md`.

Downstream documents must reference that registry and must not introduce:

```text
alternate spelling
composite values
legacy aliases
semantically overlapping enums under a new name
```

Runtime-only enums are owned by `runtime_records.md`.

Stage IDs are owned by the Pipeline contracts.

---

## 10. Persistent ID namespaces

Persistent story IDs are code-owned.

Examples:

```text
char-000001
rel-000001
loc-000001
item-000001
rule-000001
thread-000001
ending-000001
fact-000001
ev-000001
```

Properties:

- fixed prefix by type;
- fixed-width numeric suffix where specified;
- globally unique within its namespace;
- never reused;
- allocated only by code;
- persisted before use.

An LLM may use a candidate-local `local_key`.

An LLM must not allocate a persistent ID.

---

## 11. Record origin

Adopted Canon and Knowledge records use:

```text
record_origin = initial_design
or
record_origin = prose
```

### 11.1 Initial-design origin

Requires:

```text
created_scene_id = null
```

Creation is grounded in the accepted Initial-design bundle and Genesis transaction.

### 11.2 Prose origin

Requires:

```text
created_scene_id = adopted Scene ID
adopted prose Evidence
Scene-authorized creation proposal
code allocation and commit
```

`record_origin` does not describe Relationship history.

A Relationship uses its dedicated:

```text
relationship_origin
```

---

## 12. Creation restrictions

Normal Scene generation may create only the candidate types permitted by the Scene-card new-item policy and `evidence_and_updates.md`.

Normal Scene generation cannot create:

```text
Temporal rule
Major Thread
Ending criterion
required Thread
```

A Knowledge item uses the dedicated Knowledge-item proposal branch.

A new supporting Thread is the only Scene-created Thread category.

---

## 13. Record lifecycle

General Canon lifecycle:

```text
active
inactive
retired
```

It is distinct from Thread status:

```text
open
in_progress
resolved
retired
```

It is also distinct from Volume disposition:

```text
resolve
carry_over
retire
```

A generic record must not use `resolved`.

A Thread record's fixed lifecycle and its mutable Thread status are separate fields in separate ledgers.

---

## 14. Canon generation immutability

After a Generation is adopted:

- no Canon root is edited in place;
- no Knowledge root is edited in place;
- no record is appended to an adopted file;
- no lifecycle or scope field is patched in place;
- no hash is repaired in place.

A change produces a new Generation through an allowed Commit.

---

# Part II: Story-state ledger

## 15. Story-state root

Canonical path:

```text
canon/generations/<generation-id>/story-state.json
```

Exact root fields:

```text
character_states
relationship_states
thread_states
knowledge_states
story_clock
```

Forbidden root:

```text
world_states
```

World identity and fixed rules belong to Canon.

World changes that matter persist through allowed Canon records, Character locations, Knowledge, Thread, or other explicit State fields.

---

## 16. State-row identity

Each State row is identified by the Canon object it describes.

| State row | identity |
|---|---|
| Character State | `character_id` |
| Relationship State | `relationship_id` |
| Thread State | `thread_id` |
| Character Knowledge State | `(fact_id, character, audience_id)` |
| Reader Knowledge State | `(fact_id, reader, null)` |

A State row may not exist without its referenced adopted Canon/Knowledge record.

---

## 17. State-row completeness

### 17.1 Character

One State row exists for every active Character.

### 17.2 Relationship

One State row exists for every active Relationship.

### 17.3 Major Thread

One Thread State row exists for every Major Thread.

Supporting Thread rules are defined by `story_state.md`.

### 17.4 Knowledge

Knowledge State is sparse.

Rows equal to the defined defaults are omitted.

---

## 18. Sparse Knowledge semantics

Missing Knowledge rows mean:

```text
Character audience:
  unknown

Reader audience:
  withheld
```

An explicit row equal to its default is invalid.

This means that absence is a defined semantic value, not missing data.

Code must apply sparse defaults consistently during:

```text
Context construction
candidate before-value injection
continuity validation
commit merge
Completion assessment
fixture validation
```

---

## 19. Character and Relationship state

Character State owns:

```text
location
physical condition
emotional state
current goal
current pressure
```

Relationship State owns:

```text
public relation
A-to-B trust/perception/emotional stance/intention
B-to-A trust/perception/emotional stance/intention
shared state
```

Directional fields must not be collapsed into one symmetric relationship value.

---

## 20. Thread state

Thread State owns:

```text
thread_status
progress
volume_disposition
```

### 20.1 Scene-owned fields

A Scene continuity delta may change:

```text
thread_status
progress
```

through an authorized Thread action.

### 20.2 Handoff-owned field

Only a Volume-handoff commit may change:

```text
volume_disposition
```

A Scene delta targeting `volume_disposition` is invalid.

---

## 21. Thread transition model

Thread operations:

```text
introduce
advance
resolve
retire
```

The exact before/after matrix is defined by `story_state.md`.

Required Major Threads:

- cannot be retired;
- must reach `resolved` and progress `4` by final Completion;
- use final Volume disposition `resolve`.

---

## 22. Story clock

Story clock owns:

```text
current_order
time_label
parallel_group_id
last_scene_id
current_volume_number
current_chapter_number
current_scene_number
```

### 22.1 Genesis

Genesis requires:

```text
current_order = 0
last_scene_id = null
position fields = null
```

### 22.2 Scene commit

A Scene commit:

```text
increments current_order exactly once
sets last_scene_id
sets current position
applies the validated time relation
```

### 22.3 Handoff commit

A Volume-handoff commit preserves the complete Story clock byte/logical value.

It does not increment Scene order.

---

## 23. Generation ID versus Story order

Generation ID is not Scene order.

Generation IDs advance for every adopted Commit:

```text
initial_design
scene
volume_handoff
```

Story-clock `current_order` advances only for Scene commits.

Therefore, after the first Handoff:

```text
Generation numeric suffix
>
current_order
```

Canonical success-fixture result:

```text
47 Scene commits
4 Handoff commits
final Generation = 00000051
final current_order = 47
```

Any implementation assuming equality is invalid.

---

## 24. Before-value authority

A candidate update's `before` value is code-injected from the source HEAD snapshot.

It must not be trusted from the LLM.

At checkpoint and commit:

```text
candidate before
=
source HEAD value
```

A mismatch means stale or mechanically invalid candidate content.

The runtime does not rebase the candidate.

---

## 25. State update ownership

| operation | may update Story state? |
|---|---|
| Planning generation/review | no |
| Scene-card generation | no |
| prose generation/review | no |
| continuity candidate/review | no adopted mutation |
| Scene Commit | yes, authorized committed changes |
| Volume Handoff Commit | yes, `volume_disposition` only |
| Completion audit | no |
| Publication build/gate | no |
| recovery reconciliation | no semantic mutation |

Recovery may reconcile Run state but does not invent story-state changes.

---

# Part III: Evidence and update ledger

## 26. Candidate continuity artifact

The validated pre-commit candidate continuity delta is stored in the Scene checkpoint.

It represents proposed changes.

It is not adopted story truth.

The candidate contains:

```text
existing-item updates
new-item proposals
Knowledge-item proposals
Knowledge-audience updates
Thread updates
Ending Evidence proposals
time update
handoff summary
```

The exact branches are defined by `evidence_and_updates.md`.

---

## 27. Code-owned candidate fields

The LLM must not generate:

```text
persistent story ID for a new item
Evidence ID
Commit ID
Generation ID
offset
quote hash
prose hash
timestamp
source-generation identity
```

Code provides or derives those values.

The provider response and normalized candidate are separate artifacts.

---

## 28. Candidate-local keys

A candidate may use:

```text
local_key
```

to connect newly proposed objects before persistent IDs exist.

Rules:

- unique within the candidate's complete proposal namespace;
- typed;
- deterministic allocation order;
- all references resolve during Commit;
- no unresolved local key survives in committed artifacts.

A local key is never written into adopted Canon, State, Evidence, or manifests.

---

## 29. Scene-card authorization

The frozen Scene card contains:

```text
allowed_update_targets
new_item_policy
```

The continuity candidate may update only those targets.

Authorization includes:

```text
target kind/type
target ID
field path
allowed operation
starting value/status/progress
permitted after value/status/progress
time relation
new-item type/scope/count limits
```

Review cannot waive an authorization failure.

---

## 30. Evidence quote contract

An Evidence proposal uses a literal prose quote.

The quote must:

- be NFC;
- be an exact substring of canonical frozen prose;
- occur exactly once;
- not be a paraphrase;
- not include generated publication headings;
- support the proposed change.

Code calculates:

```text
start_offset
end_offset
quote_sha256
prose_sha256
```

Offsets are Unicode code-point indices.

`end_offset` is exclusive.

---

## 31. Evidence allocation

Evidence IDs are allocated during Commit preparation after COMMIT-01 dry validation.

Properties:

- allocated by code;
- persisted before use;
- ordered deterministically from normalized proposal locations;
- never reused;
- gaps remain after failed transactions.

No Evidence ID is allocated in:

```text
DELTA-01
DELTA-02
DELTA-REV
DELTA-CHK
COMMIT-01
```

---

## 32. Evidence index

Canonical path:

```text
canon/generations/<generation-id>/evidence-index.json
```

Exact root:

```text
{"records":[...]}
```

Evidence records are sorted by Evidence ID.

The file is JSON, not JSON Lines.

Each record binds:

```text
Evidence ID
Evidence type
target identity/field
audience when relevant
Scene ID
Commit ID
literal quote
relation
offsets
quote hash
prose hash
created timestamp
```

---

## 33. Committed continuity delta

Canonical adopted path:

```text
artifacts/scenes/vNN/cNNN/sNNN/continuity-delta.json
```

The committed delta contains:

```text
resolved persistent IDs
resolved Evidence IDs
code-owned before/after values
no unresolved local key
no quote proposal object
no allocation request
```

It is the change description adopted with the Scene.

---

## 34. Candidate-to-commit transformation

Transformation order:

1. validate frozen Scene card, prose, and candidate delta;
2. validate source HEAD equality;
3. validate every authorized target;
4. validate every before value;
5. validate every quote occurrence;
6. create deterministic allocation requests;
7. persist Commit/record/Evidence counter increments;
8. resolve local keys;
9. calculate offsets and hashes;
10. create Evidence records;
11. create committed delta;
12. build after roots;
13. prove bidirectional change correspondence;
14. build Scene/Commit/Generation manifests;
15. adopt pointer-last.

The LLM does not perform this transformation.

---

## 35. Bidirectional change correspondence

For a Scene commit:

```text
every committed-delta change
→ appears in the after roots

every parent-to-after root change
→ is represented by the committed delta
```

Unchanged data must remain equal according to the owning root's canonical rules.

This prevents:

```text
hidden State mutation
unrecorded Canon addition
Evidence record without proposal
committed delta that was not applied
```

---

## 36. Ending Evidence

Ending Evidence proposals support or contradict an Ending criterion.

They do not directly change the Ending criterion record.

By Completion:

- every required criterion is assessed;
- support/contradiction Evidence IDs resolve;
- the audit determines whether the criterion is satisfied.

A Scene cannot rewrite the required Ending text to match its prose.

---

## 37. Handoff summary

Every continuity delta includes a safe handoff summary.

It is:

```text
a compact account of reader/Writer-safe changes
a source for later Context construction
not a substitute for Story state
not a Volume Handoff artifact
not a new Canon record
```

The final Scene handoff summary helps construct the Volume Handoff candidate.

---

# Part IV: Runtime ledger

## 38. Runtime root records

Canonical mutable/immutable runtime roots include:

```text
runtime/run-manifest.json
runtime/run-state.json
runtime/counters.json
runtime/effective-config.json
```

Responsibilities:

| file | responsibility |
|---|---|
| Run manifest | immutable run identity |
| Run state | current resumable execution position |
| counters | monotonic ID and usage allocation |
| Effective config | complete redacted materialized config |

Exact fields are defined by `runtime_records.md` and `configuration_contracts.md`.

---

## 39. Runtime candidate records

Versioned candidates use:

```text
runtime/candidates/.../vNNNN/
```

Each version may contain:

```text
candidate artifact
review.json
candidate-manifest.json
```

Properties:

- candidate bytes are immutable;
- revision creates a new version;
- Review is version-local;
- active selection comes only from Run state;
- directory scanning does not choose the active candidate;
- candidate logical owner remains the original generator/extractor stage.

Completion audit attempts are the registered exception and use:

```text
runtime/candidates/completion/attempt-NN.json
```

with one fixed Completion Candidate manifest.

---

## 40. Scene checkpoint

Canonical path:

```text
runtime/checkpoints/scenes/vNN/cNNN/sNNN/
```

Checkpoint phases:

```text
CARD_ACCEPTED
PROSE_FROZEN
DELTA_ACCEPTED
COMMIT_PREPARED
```

The Checkpoint manifest is the phase authority.

File presence alone is not authority.

A frozen Scene card or prose is immutable after its phase.

---

## 41. Runtime counters

Counters own:

```text
persistent story IDs
Knowledge IDs
Evidence IDs
Commit/Generation IDs
Call IDs
Publication IDs
usage totals
retry/revision totals
Scene-commit count
```

Rules:

- monotonic;
- atomic replacement;
- persist-before-use;
- no decrement;
- no reuse;
- gaps valid;
- discarded work does not refund usage or IDs.

---

## 42. Commit and Generation identity

Commit ID:

```text
commit-NNNNNNNN
```

Generation ID:

```text
NNNNNNNN
```

The numeric suffixes match.

Examples:

```text
commit-00000001
Generation 00000001
```

Genesis uses:

```text
commit-00000000
Generation 00000000
```

The suffix identifies Commit sequence, not Scene order.

---

## 43. Commit branches

Allowed Commit types:

```text
initial_design
scene
volume_handoff
```

### 43.1 Initial design

Creates Genesis:

```text
parent Generation = null
current_order = 0
Scene source = null
Handoff source = null
```

### 43.2 Scene

Requires:

```text
source Scene
Scene manifest
committed continuity delta
parent current_order + 1
Handoff source fields = null
```

### 43.3 Volume handoff

Requires:

```text
source Volume Handoff
no Scene source
same current_order as parent
only Story-state volume_disposition changes
```

Conditional branch fields are exact.

Fields from different branches must not coexist.

---

## 44. Generation manifest

The Generation manifest binds:

```text
Generation ID
Commit ID
parent Generation
current order
four root paths/hashes
Commit-manifest path/hash
conditional Scene path/hash
conditional Handoff path/hash
creation timestamp
```

It does not hash itself.

The Generation directory is immutable after HEAD adoption.

---

## 45. Scene manifest

The adopted Scene manifest binds:

```text
Scene ID and coordinates
Commit ID
source/adopted Generation
Scene-card final path/hash
prose final path/hash
committed-delta final path/hash
character count
Evidence IDs
plan references
adoption timestamp
```

It must use adopted paths:

```text
artifacts/scenes/...
plans/...
```

It must not reference:

```text
runtime/candidates
runtime/checkpoints
.staging
runtime/orphans
```

---

## 46. Volume Handoff artifact

Canonical path:

```text
artifacts/handoffs/vNN.json
```

An adopted Handoff is authoritative only when referenced by a HEAD-reachable `volume_handoff` Commit/Generation.

It is not adopted because the file exists.

It is immutable after adoption.

---

## 47. Artifact classes

The only canonical artifact classes are:

```text
candidate
checkpoint
staged_internal
staged_internal_validation
adopted
audit
```

Forbidden composite/legacy examples:

```text
review candidate
adopted/audit
candidate/checkpoint
```

A Review is an `audit` artifact.

A Candidate manifest is a `candidate` artifact.

A Publication Validation before adoption is `staged_internal_validation`.

---

## 48. LLM-call audit versus candidate authority

LLM-call audit proves what occurred at the provider boundary.

Candidate authority requires:

```text
candidate file
candidate-manifest reference
matching Context hash
matching source hashes
valid structure
Run-state active selection
```

A raw successful response in an audit file is never promoted to a candidate during recovery.

This intentionally permits duplicate provider work after an interrupted candidate write.

---

## 49. Resume compatibility

Resume compares:

```text
Run manifest
Effective config
immutable config fingerprint
prompt bundle
Schema bundle
code/workspace/state versions
active source hashes
HEAD/CURRENT pointers
```

A compatible resume may continue from:

```text
valid active Candidate manifest
valid active Checkpoint manifest
valid referenced transaction manifest
valid adopted pointer graph
```

It may not resume from:

```text
normal log
raw audit response
newest file
unreferenced staging
quarantine
```

---

# Part V: Atomic Generation transactions

## 50. Generation construction model

Story roots use copy-on-write.

For a new Generation:

1. read the parent Generation selected by HEAD;
2. create complete after roots in staging;
3. write complete manifests;
4. validate the complete graph;
5. rename the Generation and conditional Scene/Handoff artifact;
6. revalidate final paths;
7. replace `canon/HEAD` last;
8. update Run state;
9. clean checkpoint/staging residue.

No adopted root is edited in place.

---

## 51. Genesis transaction

INIT-ID:

1. validates the accepted integrated Initial-design bundle;
2. deterministically allocates persistent IDs;
3. creates:
   ```text
   current Canon
   Knowledge items
   complete Story state
   empty Evidence index
   ```
4. creates Genesis Commit and Generation;
5. creates `canon/initial-design.json`;
6. validates all hashes/references;
7. moves final artifacts;
8. writes `canon/HEAD=00000000` last.

Genesis does not create prose Evidence.

---

## 52. Scene transaction

A Scene transaction begins from:

```text
DELTA_ACCEPTED checkpoint
current canon/HEAD
```

COMMIT-01 performs dry validation and creates the Commit plan without allocation.

COMMIT-02 persists allocation counters and creates the merge plan.

COMMIT-03 creates:

```text
after roots
Evidence records
committed delta
Scene manifest
Commit manifest
Generation manifest
transaction validation
COMMIT_PREPARED checkpoint
```

COMMIT-04 adopts pointer-last.

---

## 53. Volume-handoff transaction

VH-ID creates a distinct Commit/Generation.

Permitted story-root effects:

```text
current-canon.json:
  byte-identical to parent

knowledge-items.json:
  byte-identical to parent

evidence-index.json:
  byte-identical to parent

story-state.json:
  only thread_states[].volume_disposition may change

story_clock:
  byte-identical to parent
```

The Handoff Commit consumes a Commit/Generation ID.

It does not consume a Scene order.

---

## 54. HEAD-last invariant

Before HEAD is replaced:

```text
final-looking Generation = unadopted
final-looking Scene = unadopted
final-looking Handoff = unadopted
```

After HEAD is replaced and the graph validates:

```text
Commit/Generation is adopted
Run state may be reconciled forward
```

Ordinary startup never completes HEAD from final-looking files by inference.

---

## 55. Crash boundary

### 55.1 Before HEAD

Unreferenced final-looking content is quarantined or resumed only through an exact referenced transaction where the Pipeline contract permits it.

### 55.2 After HEAD, before Run-state update

The Commit is adopted.

Startup validates the HEAD graph and reconciles Run state.

No provider call or ID allocation repeats.

### 55.3 Invalid graph after HEAD

Automatic rollback is forbidden.

Manual intervention is required.

---

# Part VI: Stage-to-ledger access

## 56. Input and Initial design

| stage family | reads | writes |
|---|---|---|
| INPUT | user input/config | adopted Brief and Runtime candidate records |
| INIT-01..05 | Brief and earlier candidates | versioned Initial-design candidates |
| INIT-06/REV | integrated candidate/private Context | Review/revised candidate |
| INIT-ID | accepted bundle and counters | Genesis roots, manifests, initial-design snapshot, HEAD |

Before INIT-ID there is no adopted Canon Generation.

---

## 57. Planning

Series, Volume, and Chapter planning read:

```text
adopted Brief
initial-design snapshot
adopted plans
HEAD Generation roots
prior Volume Handoff when applicable
safe prior Scene handoff summaries
```

Planning writes:

```text
versioned plan candidates
Reviews
immutable adopted plan files
Run state
audits
```

Planning does not mutate:

```text
Canon roots
Story state
Evidence index
HEAD
```

---

## 58. Scene generation

Scene-card, prose, and continuity stages read the same fixed source Generation until the Scene commit completes.

They write:

```text
Context snapshots
versioned candidates
Reviews
Scene checkpoint files
candidate continuity delta
audits
Run state
```

They do not mutate adopted roots or HEAD.

---

## 59. Scene commit

Only COMMIT-02 through COMMIT-04 may allocate/apply the Scene changes.

The Commit pipeline writes:

```text
counters
merge and transaction plans
staged roots
Evidence records
committed delta
Scene/Commit/Generation manifests
HEAD
Run state
```

The adopted Scene card and prose are byte-identical to their checkpoint versions.

---

## 60. Volume Handoff

VH-01/02/REV write candidates and Reviews only.

VH-ID writes:

```text
Handoff artifact
Handoff Commit
Handoff Generation
Story state with disposition changes
HEAD
Run state
```

No Evidence is allocated solely for a Handoff decision.

---

## 61. Completion

Completion stages read:

```text
final Handoff HEAD
final Canon/Knowledge/State/Evidence
all adopted plans and Scenes
Handoffs
residual issues
```

They write:

```text
Completion precondition
Completion Context
Completion attempt
accepted private Completion audit
Runtime/audit records
```

They do not mutate story ledgers.

The noncyclic identity order is:

```text
Completion precondition
→ Completion Context including precondition
→ saved attempt referring to both hashes
→ accepted private audit
```

The precondition must not contain the Context snapshot hash.

---

## 62. Publication

Publication stages read adopted story ledgers and accepted Completion records.

They write:

```text
publication payload
Publication Validation
Publication manifest
Publication Gate
publication directory
output/CURRENT
Run state
```

They do not change:

```text
canon/HEAD
Generation roots
Scene artifacts
Handoffs
plans
Evidence
```

---

## 63. Recovery

Recovery may:

```text
validate
reconcile Run state
resume an exact transaction
quarantine unreferenced content
remove proven cleanup residue
```

Recovery may not:

```text
repair story meaning
invent a committed delta
add Evidence
change Canon/State to match prose
rewrite HEAD/CURRENT from newest files
```

---

# Part VII: Hash and serialization topology

## 64. Canonical bytes

All persisted JSON uses the canonical serializer required by Runtime and fixture contracts.

Core properties:

```text
UTF-8
Unicode NFC
deterministic object-key order
contract-normalized array order
no insignificant whitespace
no nonfinite number
exact final-LF policy
```

Prose and pointer files follow their own exact text-byte contracts.

---

## 65. Root hashes

A Commit and Generation store hashes of complete canonical root bytes.

A root hash does not identify its role alone.

For example, two empty roots may have identical bytes.

Role identity also requires:

```text
path
manifest field
Schema
artifact role
```

---

## 66. Noncyclic manifest graph

Scene transaction hash order:

```text
Scene card
prose
committed continuity delta
after roots
→ Scene manifest
→ Commit manifest
→ Generation manifest
```

The Generation manifest does not hash itself.

The Commit manifest does not hash the Generation manifest.

The Scene manifest does not hash the Commit manifest.

---

## 67. Handoff manifest graph

Handoff transaction order:

```text
adopted Handoff
after roots
→ Handoff Commit
→ Handoff Generation
```

The Generation references the Handoff path/hash and Commit path/hash.

---

## 68. Completion identity graph

Required noncyclic order:

```text
Completion precondition
→ Completion Context
→ saved Completion attempt
→ accepted private Completion audit
```

A precondition must not require a hash of a Context that includes the precondition.

---

## 69. Publication identity graph

Required noncyclic order:

```text
payload files
→ payload_set_sha256
→ Publication Validation
→ Validation file reference
→ final Manifest.files
→ content_set_sha256
→ Publication manifest
→ Publication Gate snapshot
```

The Manifest does not list or hash itself.

The Validation does not hash the Manifest.

---

## 70. Pointer bytes

Exact pointer form:

```text
canon/HEAD:
  <generation-id>\n

output/CURRENT:
  <publication-id>\n
```

No JSON, BOM, spaces, comments, or extra line.

Pointers are replaced atomically.

---

# Part VIII: Cross-ledger invariants

## 71. Reference integrity

Every persisted reference must resolve against the same adopted snapshot or an explicitly permitted external adopted artifact.

Examples:

```text
State character_id
→ Character in current Canon

Knowledge State fact_id
→ Knowledge item

Evidence scene_id
→ adopted Scene

Evidence commit_id
→ HEAD-history Commit

Scene plan reference
→ immutable adopted plan

Generation source_scene_manifest
→ adopted Scene manifest
```

Unknown or wrong-prefix references fail mechanically.

---

## 72. Canon/State completeness

For every active relevant Canon object:

```text
required State row exists
```

For every State row:

```text
referenced Canon object exists
```

Sparse Knowledge defaults are the explicit exception.

---

## 73. Scene-card/State authorization

Every continuity update must match one frozen Scene-card authorization entry.

No Review result may permit an unlisted target.

No commit may add an update because it “appears in prose” without prior authorization.

---

## 74. Prose/Evidence integrity

For every adopted Evidence record:

```text
Scene exists
prose path/hash matches Scene manifest
quote occurs at stored offsets
quote hash matches
prose hash matches
target/change relation is valid
```

A Publication-generated heading is never prose Evidence.

---

## 75. Delta/State integrity

For every existing-item update:

```text
before = parent State
after = child State
```

For every Knowledge update:

```text
sparse default or explicit parent status
→ valid child status
```

For every Thread update:

```text
parent status/progress
→ permitted operation
→ child status/progress
```

For every time update:

```text
parent Story clock
→ permitted relation
→ child Story clock
```

---

## 76. Commit/Generation integrity

Required equalities include:

```text
Generation.commit_id = Commit.commit_id
Generation ID suffix = Commit ID suffix
Commit.after_generation = Generation ID
Commit.before_generation = Generation.parent_generation_id
Commit root hashes = Generation root hashes
Generation.current_order = child Story clock current_order
```

Conditional Scene/Handoff fields match the Commit type.

---

## 77. Scene-order integrity

For a Scene Commit:

```text
child current_order = parent current_order + 1
successful_scene_commits increments by 1
```

For a Handoff Commit:

```text
child current_order = parent current_order
successful_scene_commits unchanged
```

Genesis:

```text
current_order = 0
successful_scene_commits = 0
```

---

## 78. Handoff integrity

A `volume_handoff` Generation must satisfy:

```text
current Canon equal parent
Knowledge items equal parent
Evidence index equal parent
Story clock equal parent
only thread volume_disposition changes
```

A required Major Thread cannot receive `retire`.

The final Volume requires `resolve`.

---

## 79. Run-state integrity

After reconciliation:

```text
Run-state current_head_generation = canon/HEAD
Run-state last_commit_id = HEAD Commit
Run-state current_publication_id = output/CURRENT when non-null
successful_scene_commits = HEAD story_clock.current_order
```

The stage/target/Scene phase must match the exact durable candidate/checkpoint/adopted boundary.

---

## 80. Counter integrity

Every counter:

```text
> every observed allocated value in its namespace
```

A counter below an observed value is corruption.

A counter above observed values is valid.

The runtime must not silently repair a low counter.

---

## 81. Candidate integrity

A resumable candidate requires:

```text
valid Candidate manifest
candidate file/hash
Context snapshot/hash
source refs/hashes
operation/target/version match
Run-state active selection
non-superseded status
```

A candidate file alone has no authority.

---

## 82. Checkpoint integrity

A resumable checkpoint requires:

```text
exact expected Scene path
valid Checkpoint manifest
source Generation = current HEAD
phase-required files
matching candidate manifests
no already-adopted target Scene
```

Extra later-phase files are not promoted.

---

## 83. Publication separation

A Publication may contain safe reader-facing derivatives of the ledgers.

It must not contain:

```text
private author truth
raw State ledgers
raw Evidence index
private Handoff
raw Context snapshot
candidate/review records
runtime counters
workspace-private paths
```

The Publication manifest and Gate prove file integrity, not story-ledger mutation.

---

# Part IX: Mutability matrix

## 84. Adopted immutable records

Immutable after adoption:

```text
input source
Brief
initial-design snapshot
Generation roots
Commit/Generation manifests
adopted plans
adopted Scene card/prose/delta/manifest
adopted Volume Handoff
Completion audits
Publication payload/Validation/Manifest
Publication Gate
```

A later correction creates a new permitted artifact/Generation/Publication.

---

## 85. Mutable runtime records

Mutable through atomic replacement:

```text
runtime/run-state.json
runtime/counters.json
active Candidate manifest
active Checkpoint manifest
permitted effective-config resume update
pointer files at their owning adoption stage
```

Append-only:

```text
audit/residual-issues.jsonl
normal operational log
```

Immutable audit records use unique filenames.

---

## 86. Mutation owners

| object | only normal owner |
|---|---|
| Canon/Knowledge roots | INIT-ID or Scene Commit |
| Story State | INIT-ID, Scene Commit, VH-ID |
| Evidence index | INIT-ID or Scene Commit |
| `canon/HEAD` | INIT-ID, COMMIT-04, VH-ID |
| adopted plan | corresponding `*-ID` planning stage |
| Scene checkpoint | SC-CHK, PROSE-CHK, DELTA-CHK, COMMIT-01/03 |
| counters | code allocator/usage accounting |
| `output/CURRENT` | OUT-03 |
| Publication Gate | COMP-PUBLISH |

No generic helper may mutate these outside the owning transaction.

---

# Part X: Common failure classifications

## 87. Structural failure

Examples:

```text
invalid JSON
missing required field
unknown field
wrong discriminator branch
wrong scalar type
invalid ID/path format
```

At an LLM boundary, this may consume a response-structure retry.

For persisted adopted/runtime artifacts, it is a mechanical failure.

---

## 88. Semantic Review issue

A structurally valid candidate may have semantic issues.

It routes to:

```text
revision
or
revision exhaustion with residual issues
```

It does not permit mechanical-contract violations.

---

## 89. Staleness

A candidate/checkpoint is stale when its source Generation or source artifact hash changed.

Action:

```text
do not rebase
invalidate/quarantine as required
regenerate from current authority
```

Staleness is not a semantic revision.

---

## 90. Mechanical ledger inconsistency

Examples:

```text
invalid HEAD graph
root hash mismatch
missing referenced record
counter regression
committed delta/root mismatch
Evidence offset mismatch
Handoff modifies forbidden root
Scene manifest points to checkpoint
```

Normal generation does not continue.

---

## 91. Orphan

An orphan is content not reachable from:

```text
valid HEAD
valid CURRENT
valid active Candidate
valid active Checkpoint
valid referenced transaction
```

It is quarantined only after reachability proof.

Quarantine is not an adoption queue.

---

# Part XI: Forbidden shortcuts

## 92. Canon and State shortcuts

Forbidden:

```text
store current emotion in Character Canon
store Relationship origin in record_origin
store world_states root
store Thread status in Thread Canon record
store who knows a fact inside Knowledge-item definition
write mutable roots directly under canon/
edit an adopted Generation
```

---

## 93. Evidence shortcuts

Forbidden:

```text
LLM allocates Evidence ID
LLM emits offsets/hashes
paraphrase used as Evidence quote
nonunique quote accepted
byte offsets stored as code-point offsets
create Evidence from publication heading
accept unrepresented State mutation
```

---

## 94. Runtime shortcuts

Forbidden:

```text
select newest candidate
select highest Generation and rewrite HEAD
select highest Publication and rewrite CURRENT
promote raw audit response to candidate
reuse an allocated ID gap
decrement usage counters
trust file presence instead of manifest phase
```

---

## 95. Commit shortcuts

Forbidden:

```text
allocate IDs during COMMIT-01
mutate parent roots in place
build committed delta separately from merge plan
write HEAD before final Generation/Scene/Handoff durability
adopt final-looking pre-HEAD directories by inference
use Scene Commit branch for Volume Handoff
```

---

## 96. Completion/publication shortcuts

Forbidden:

```text
retry valid incomplete Completion until complete
let Completion mutate story ledgers
copy private Completion audit directly into publication
let COMP-PUBLISH rename/adopt publication
store staging-root paths in final Manifest/Gate
include Manifest in its own files hash
```

---

# Part XII: Implementation dependency order

## 97. Recommended implementation order

Implement ledger foundations in this order:

1. canonical serialization and hash utilities;
2. managed path and identifier validators;
3. Canon record/enum validators;
4. Story-state validators and transition matrices;
5. Evidence/update candidate validators;
6. Runtime record and manifest validators;
7. counters and persist-before-use allocator;
8. Context builders and source-reference validation;
9. candidate/Review storage;
10. Scene checkpoint state machine;
11. Commit plan and merge plan;
12. root copy-on-write builder;
13. Scene/Handoff transaction adoption;
14. startup reconciliation/quarantine;
15. Completion and Publication readers/builders.

A downstream stage must not be implemented against placeholder ledger models.

---

## 98. Validator reuse

Production, tests, CLI inspection, and recovery must use the same:

```text
canonical serializer
ID validators
path validator
enum registries
State transition tables
candidate validators
Evidence offset checker
Commit/Generation graph validator
pointer reader
```

A permissive recovery-only validator is forbidden.

---

## 99. Test and fixture mapping

Normative examples are defined by:

- [`data_contract_examples.md`](data_contract_examples.md)
- [`examples/initial_and_planning_fixture.md`](examples/initial_and_planning_fixture.md)
- [`examples/scene_commit_fixture.md`](examples/scene_commit_fixture.md)
- [`examples/completion_publication_fixture.md`](examples/completion_publication_fixture.md)

Core acceptance groups include:

```text
ACC-CANON-*
ACC-STATE-*
ACC-EVID-*
ACC-RUN-*
ACC-COMMIT-*
ACC-VH-*
ACC-REC-*
ACC-FIX-*
```

The fixtures are evidence of contract consistency, not an alternate Schema source.

---

## 100. Mechanical acceptance conditions

This Ledger index is acceptable only when tests demonstrate:

```text
four ledger-family boundaries
single-source-of-truth matrix
Canon versus State field ownership
current-canon/Knowledge root separation
complete Story-state root
sparse Knowledge defaults
Thread status/progress/disposition ownership
Story-clock Scene/Handoff behavior

persistent-ID code ownership
persist-before-use and non-reuse
record-origin semantics
Scene creation restrictions
candidate local-key resolution
candidate code-owned-field exclusion

frozen Scene-card authorization
before-value equality
unique literal Evidence quote
Unicode code-point offsets
Evidence index exact root
candidate-to-committed transformation
bidirectional committed-delta/root correspondence

Run-manifest/Run-state/counter authority
versioned candidate authority
Checkpoint-manifest phase authority
Commit type conditional branches
Generation ID versus Scene-order distinction
Scene-manifest adopted paths
Handoff-only disposition changes
artifact-class registry

copy-on-write Generation construction
Genesis transaction
Scene Commit transaction
Handoff Commit transaction
HEAD-last adoption
post-HEAD Run-state reconciliation
pre-HEAD orphan handling

stage-to-ledger read/write ownership
Completion ledger read-only behavior
noncyclic Completion identity order
Publication ledger read-only behavior
noncyclic Publication hash order

cross-reference integrity
root/manifest hash graph
Scene/current-order invariants
Handoff current-order preservation
Run-state pointer reconciliation
counter lower-bound rejection
candidate/checkpoint resume validation
publication private/public separation

forbidden shortcut rejection
implementation dependency order
validator reuse
relative-link resolution
unknown-field rejection
