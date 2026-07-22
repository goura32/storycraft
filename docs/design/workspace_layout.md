# Workspace layout

This document is the normative workspace-path contract for Storycraft.

It defines:

- the complete workspace directory tree;
- path grammar and fixed-width identifiers;
- the responsibility and authority of every top-level directory;
- exact candidate, checkpoint, generation, handoff, audit, staging, publication, and quarantine paths;
- which paths may be mutable, immutable, temporary, or pointer files;
- which paths are valid resume sources;
- rename-stable relative-path rules;
- startup scanning, cleanup, and retention boundaries.

Runtime field contracts are defined by [`contracts/ledger/runtime_records.md`](contracts/ledger/runtime_records.md). Pipeline ownership and stage transitions are defined by [`pipeline_contracts.md`](pipeline_contracts.md) and the documents under [`contracts/pipeline/`](contracts/pipeline/). Canon, Story state, Evidence, and data payloads are defined by the documents under [`contracts/ledger/`](contracts/ledger/) and [`contracts/data/`](contracts/data/).

All paths in this document are relative to the workspace root unless explicitly stated otherwise.

---

## 1. Workspace principles

### 1.1 One workspace, one story

A workspace contains exactly one Storycraft story and its complete execution history.

A valid workspace must not mix:

```text
multiple Briefs
multiple independent Canon roots
multiple unrelated canon/HEAD chains
multiple stories sharing one runtime directory
```

Creating a second story requires a different workspace root.

### 1.2 Path roles

Every path belongs to one of these roles:

| role | meaning |
|---|---|
| adopted authority | immutable story or publication artifact reachable from an adopted pointer |
| mutable runtime authority | current execution state used for resume |
| immutable candidate history | structurally valid generated/revised candidate versions |
| checkpoint authority | frozen pre-commit Scene transaction input |
| audit history | immutable evidence of calls, Reviews, validation, and decisions |
| transaction staging | unadopted files being prepared for one atomic transaction |
| quarantine | content proven or suspected to be unreferenced and not authoritative |
| human-readable log | redacted operational log; never a resume source |

### 1.3 Pointer authority

The two adopted pointer files are:

```text
canon/HEAD
output/CURRENT
```

Meaning:

| pointer | authority |
|---|---|
| `canon/HEAD` | current adopted Canon/State/Evidence generation |
| `output/CURRENT` | current adopted publication |

A directory is not adopted merely because it exists under:

```text
canon/generations/
artifacts/
publications/
```

It must be reachable from the applicable valid pointer and manifest graph.

### 1.4 No path inference

Code must not choose an artifact by:

```text
filesystem modification time
directory creation time
lexicographically highest filename
highest numeric ID alone
first parseable file
most semantically plausible file
```

Selection uses only:

```text
Run state
Candidate manifest
Checkpoint manifest
canon/HEAD
output/CURRENT
Commit/Generation/Scene/Handoff/Publication manifests
explicit transaction manifests
```

---

## 2. Canonical workspace tree

```text
workspace/
├── input/
│   ├── keywords.json
│   └── brief.json
│
├── runtime/
│   ├── run-manifest.json
│   ├── run-state.json
│   ├── counters.json
│   ├── effective-config.json
│   │
│   ├── candidates/
│   │   ├── input/
│   │   │   └── brief/
│   │   │       └── v0001/
│   │   │           ├── brief.json
│   │   │           └── candidate-manifest.json
│   │   │
│   │   ├── initial-design/
│   │   │   ├── concept/
│   │   │   │   └── v0001/
│   │   │   │       ├── concept.json
│   │   │   │       └── candidate-manifest.json
│   │   │   ├── people/
│   │   │   │   └── v0001/
│   │   │   │       ├── people.json
│   │   │   │       └── candidate-manifest.json
│   │   │   ├── world/
│   │   │   │   └── v0001/
│   │   │   │       ├── world.json
│   │   │   │       └── candidate-manifest.json
│   │   │   ├── arcs/
│   │   │   │   └── v0001/
│   │   │   │       ├── arcs.json
│   │   │   │       └── candidate-manifest.json
│   │   │   └── bundle/
│   │   │       ├── v0001/
│   │   │       │   ├── bundle.json
│   │   │       │   ├── review.json
│   │   │       │   └── candidate-manifest.json
│   │   │       └── v0002/
│   │   │           ├── bundle.json
│   │   │           ├── review.json
│   │   │           └── candidate-manifest.json
│   │   │
│   │   ├── planning/
│   │   │   ├── series-map/
│   │   │   │   └── v0001/
│   │   │   │       ├── series-map.json
│   │   │   │       ├── review.json
│   │   │   │       └── candidate-manifest.json
│   │   │   └── volumes/
│   │   │       └── v01/
│   │   │           ├── v0001/
│   │   │           │   ├── volume-design.json
│   │   │           │   ├── review.json
│   │   │           │   └── candidate-manifest.json
│   │   │           └── chapters/
│   │   │               └── c001/
│   │   │                   └── v0001/
│   │   │                       ├── chapter-design.json
│   │   │                       ├── review.json
│   │   │                       └── candidate-manifest.json
│   │   │
│   │   ├── scenes/
│   │   │   └── v01/
│   │   │       └── c001/
│   │   │           └── s001/
│   │   │               ├── scene-card/
│   │   │               │   └── v0001/
│   │   │               │       ├── scene-card.json
│   │   │               │       ├── review.json
│   │   │               │       └── candidate-manifest.json
│   │   │               ├── prose/
│   │   │               │   └── v0001/
│   │   │               │       ├── prose.md
│   │   │               │       ├── review.json
│   │   │               │       └── candidate-manifest.json
│   │   │               └── continuity/
│   │   │                   └── v0001/
│   │   │                       ├── continuity-delta.json
│   │   │                       ├── review.json
│   │   │                       └── candidate-manifest.json
│   │   │
│   │   ├── handoffs/
│   │   │   └── v01/
│   │   │       └── v0001/
│   │   │           ├── volume-handoff.json
│   │   │           ├── review.json
│   │   │           └── candidate-manifest.json
│   │   │
│   │   └── completion/
│   │       ├── candidate-manifest.json
│   │       ├── attempt-01.json
│   │       └── attempt-02.json
│   │
│   ├── checkpoints/
│   │   └── scenes/
│   │       └── v01/
│   │           └── c001/
│   │               └── s001/
│   │                   ├── scene-card.json
│   │                   ├── prose.md
│   │                   ├── continuity-delta.json
│   │                   ├── commit-plan.json
│   │                   └── checkpoint-manifest.json
│   │
│   ├── context-snapshots/
│   │   └── <operation-id-lower>/
│   │       └── <target-id-path-safe>/
│   │           └── <context-sha256>.json
│   │
│   └── orphans/
│       └── <timestamp-basic>/
│           ├── orphan-manifest.json
│           └── <quarantined-content>
│
├── canon/
│   ├── HEAD
│   ├── initial-design.json
│   └── generations/
│       ├── 00000000/
│       │   ├── current-canon.json
│       │   ├── knowledge-items.json
│       │   ├── story-state.json
│       │   ├── evidence-index.json
│       │   ├── commit-manifest.json
│       │   └── generation-manifest.json
│       └── 00000001/
│           ├── current-canon.json
│           ├── knowledge-items.json
│           ├── story-state.json
│           ├── evidence-index.json
│           ├── commit-manifest.json
│           └── generation-manifest.json
│
├── plans/
│   ├── series-map.json
│   └── volumes/
│       └── v01/
│           ├── volume-design.json
│           └── chapters/
│               └── c001/
│                   └── chapter-design.json
│
├── artifacts/
│   ├── scenes/
│   │   └── v01/
│   │       └── c001/
│   │           └── s001/
│   │               ├── scene-card.json
│   │               ├── prose.md
│   │               ├── continuity-delta.json
│   │               └── scene-manifest.json
│   └── handoffs/
│       └── v01.json
│
├── audit/
│   ├── llm-calls/
│   │   └── <sequence>__<operation>__<target>__<role>__attempt-NN[__round-NN].json.gz
│   ├── operations/
│   │   └── <timestamp-basic>__<operation>__<target>__<event>.json
│   ├── completion/
│   │   └── <generation-id>/
│   │       ├── completion-precondition.json
│   │       └── completion-audit.json
│   ├── publication-gates/
│   │   └── <publication-id>.json
│   └── residual-issues.jsonl
│
├── logs/
│   └── storycraft.log
│
├── publications/
│   └── pub-000001/
│       ├── manuscript/
│       │   ├── series.md
│       │   └── v01.md
│       ├── metadata/
│       │   ├── series.json
│       │   └── volumes/
│       │       └── v01.json
│       ├── reports/
│       │   └── completion-audit.json
│       ├── publication-validation.json
│       └── publication-manifest.json
│
├── output/
│   └── CURRENT
│
├── .staging/
│   ├── genesis/
│   │   └── <run-id>/
│   │       ├── initial-design.json
│   │       ├── generation/
│   │       │   └── 00000000/
│   │       └── genesis-validation.json
│   ├── planning/
│   │   ├── series-map/
│   │   │   └── <run-id>/
│   │   ├── volumes/
│   │   │   └── v01/
│   │   │       └── <run-id>/
│   │   └── chapters/
│   │       └── v01/
│   │           └── c001/
│   │               └── <run-id>/
│   ├── scene-commits/
│   │   └── v01-c001-s001/
│   │       ├── transaction-manifest.json
│   │       ├── merge-plan.json
│   │       ├── transaction-validation.json
│   │       ├── generation/
│   │       │   └── <generation-id>/
│   │       └── scene/
│   ├── handoffs/
│   │   └── v01/
│   │       └── <run-id>/
│   │           ├── handoff.json
│   │           ├── handoff-validation.json
│   │           └── generation/
│   │               └── <generation-id>/
│   └── publication/
│       └── <publication-id>/
│           ├── manuscript/
│           ├── metadata/
│           ├── reports/
│           ├── publication-build-manifest.json
│           ├── publication-validation.json
│           └── publication-manifest.json
│
└── .storycraft.lock
```

The tree shows possible files. A valid workspace contains only the files applicable to its current lifecycle state.

For example:

- `input/keywords.json` is absent in Brief mode;
- intermediate candidate directories may lack `review.json`;
- a Scene checkpoint contains only files valid for its current phase;
- `publication-build-manifest.json` must be absent from a finalized staged or adopted publication.

---

## 3. Path grammar

### 3.1 Volume component

```text
vNN
```

Rules:

- lowercase `v`;
- exactly two decimal digits;
- minimum numeric value `1`;
- examples: `v01`, `v09`, `v10`;
- values above `99` are unsupported by version 1.

### 3.2 Chapter component

```text
cNNN
```

Rules:

- lowercase `c`;
- exactly three decimal digits;
- minimum numeric value `1`;
- examples: `c001`, `c012`, `c100`.

### 3.3 Scene component

```text
sNNN
```

Rules:

- lowercase `s`;
- exactly three decimal digits;
- minimum numeric value `1`;
- examples: `s001`, `s020`, `s999`.

### 3.4 Scene ID

```text
vNN-cNNN-sNNN
```

Example:

```text
v04-c003-s002
```

The components must equal every corresponding path and numeric field.

### 3.5 Planning target IDs

```text
series
vNN
vNN-cNNN
```

### 3.6 Candidate version

```text
vNNNN
```

Rules:

- exactly four decimal digits;
- one-based within one logical candidate;
- contiguous for successful structurally valid versions;
- examples: `v0001`, `v0002`;
- never reused.

Candidate version and Volume component both begin with `v`, but their position and fixed width distinguish them.

### 3.7 Generation ID

```text
NNNNNNNN
```

Rules:

- exactly eight decimal digits;
- Genesis is `00000000`;
- later values match the numeric suffix of the adopting Commit ID;
- directory name only, with no `gen-` prefix.

### 3.8 Commit ID

```text
commit-NNNNNNNN
```

### 3.9 Publication ID

```text
pub-NNNNNN
```

At least six decimal digits are used. The counter may grow beyond six digits without truncation.

### 3.10 Call ID

```text
call-NNNNNN
```

The audit filename uses the zero-padded numeric suffix, not the literal `call-` prefix.

### 3.11 Evidence and story-record IDs

Persistent record and Evidence ID formats are defined by the Ledger contracts.

A path component derived from one of those IDs must use the exact canonical lowercase ID and must not introduce aliases.

### 3.12 Timestamp-basic

Used for quarantine and operation-audit filenames:

```text
YYYYMMDDTHHMMSSffffffZ
```

Example:

```text
20260722T091530123456Z
```

It is UTC, filesystem-safe, and lexicographically chronological.

### 3.13 Path-safe target

For Context and audit filenames:

- lowercase;
- `/`, `\`, colon, whitespace, and control characters forbidden;
- only `[a-z0-9._-]`;
- repeated separators normalized deterministically;
- no leading dot;
- no `..` segment.

---

## 4. General path rules

### 4.1 Relative-path storage

Persisted workspace references use workspace-relative POSIX-style paths.

Required:

```text
plans/volumes/v01/volume-design.json
artifacts/scenes/v01/c001/s001/prose.md
```

Forbidden:

```text
C:\story\plans\volumes\v01\volume-design.json
/home/user/story/plans/volumes/v01/volume-design.json
./plans/volumes/v01/volume-design.json
plans//volumes/v01/volume-design.json
```

### 4.2 Separator

Persisted paths use:

```text
/
```

even on operating systems whose native separator differs.

### 4.3 Normalization

Before validation or storage, code:

1. decodes the path as Unicode;
2. normalizes to NFC;
3. rejects NUL and control characters;
4. converts supported user-facing separators only at the CLI boundary;
5. rejects absolute paths;
6. rejects empty segments;
7. rejects `.` and `..` segments;
8. rejects path traversal after normalization;
9. verifies the resolved path remains under the workspace root.

### 4.4 Case sensitivity

Canonical paths are case-sensitive.

Required:

```text
canon/HEAD
output/CURRENT
```

Forbidden alternatives:

```text
canon/head
Canon/HEAD
output/current
```

On case-insensitive filesystems, startup must still detect canonical-name collisions.

### 4.5 Symlinks and reparse points

Storycraft must not follow a symlink, junction, reparse point, or mount escape that causes a managed path to resolve outside the workspace.

For managed authoritative directories:

```text
input
runtime
canon
plans
artifacts
audit
publications
output
.staging
```

symlinked files or directory components are rejected by default.

### 4.6 Reserved temporary filenames

Atomic writes use same-directory temporary files whose names are not authoritative.

Recommended pattern:

```text
.<final-filename>.tmp.<run-id>.<random-suffix>
```

Temporary files:

- are never referenced by a manifest;
- are ignored as story authority;
- are removed or quarantined at startup;
- must not use a final artifact filename until atomic replacement.

---

# Part I: Input and runtime

## 5. `input/`

The `input/` directory contains immutable adopted user-input artifacts.

### 5.1 Keyword source

```text
input/keywords.json
```

Present only in Keywords mode.

Authority:

- adopted normalized Keyword source;
- source for INPUT-02;
- referenced by Run manifest and adopted Brief metadata.

It is never modified after INPUT-01.

### 5.2 Brief

```text
input/brief.json
```

Present after INPUT-01 in Brief mode or INPUT-03 in Keywords mode.

Authority:

- one adopted Brief;
- immutable for the workspace;
- source for Initial design and all later planning.

A changed Brief requires a new workspace.

### 5.3 Forbidden files

The following do not belong under `input/`:

```text
raw provider response
candidate Brief
Review
runtime config
credentials
temporary prompt
```

---

## 6. Runtime root files

### 6.1 Run manifest

```text
runtime/run-manifest.json
```

Immutable for one run.

Contains:

```text
run identity
input mode and source hash
initial Effective-config identity
prompt/Schema bundle identity
workspace identity
```

It is a resume-validation source.

### 6.2 Run state

```text
runtime/run-state.json
```

Mutable single-writer execution authority.

Contains:

```text
run status
last completed stage
next stage
target coordinates
current HEAD identity
current publication identity
active Candidate-manifest path
active Checkpoint-manifest path
scene phase
budget/stop state
```

It is updated only by atomic replacement.

### 6.3 Counters

```text
runtime/counters.json
```

Mutable allocation authority.

Contains counters for:

```text
persistent story-record IDs
Knowledge IDs
Evidence IDs
Commit/Generation IDs
Call IDs
Publication IDs
```

Counter increments are persisted before the allocated value is used.

Counter gaps are valid and never repaired.

### 6.4 Effective config

```text
runtime/effective-config.json
```

Immutable materialized semantic/run configuration for the run.

It contains the credential environment-variable name, never the credential value.

### 6.5 Root-file restrictions

No runtime root file is copied into:

```text
Canon generation
Scene artifact
Handoff artifact
publication payload
```

Hashes and selected IDs may be referenced where a contract explicitly permits them.

---

## 7. `runtime/candidates/`

This directory contains immutable candidate-version history and mutable active Candidate manifests.

### 7.1 General version layout

```text
runtime/candidates/<logical-root>/vNNNN/
  <candidate-file>
  review.json
  candidate-manifest.json
```

Rules:

- `review.json` is absent until that exact version is reviewed;
- candidate filename is operation-specific;
- Candidate manifest filename is always `candidate-manifest.json`;
- Review filename is always `review.json`;
- one logical candidate has one contiguous version sequence;
- a revised version is a new directory;
- an earlier version is never overwritten.

### 7.2 Active version

The active version is selected only by:

```text
runtime/run-state.json:
  active_candidate_manifest_path
```

When a downstream stage requires a fixed dependency candidate, its exact path and hash are recorded in the Context snapshot source references.

### 7.3 Initial-generation candidates without Review

These normally contain no `review.json`:

```text
input/brief
initial-design/concept
initial-design/people
initial-design/world
initial-design/arcs
```

Their Candidate manifest and candidate file are sufficient for the next INIT stage.

### 7.4 Reviewed candidate families

These use version-local `review.json`:

```text
initial-design/bundle
planning/series-map
planning/volumes/vNN
planning/volumes/vNN/chapters/cNNN
scenes/vNN/cNNN/sNNN/scene-card
scenes/vNN/cNNN/sNNN/prose
scenes/vNN/cNNN/sNNN/continuity
handoffs/vNN
```

### 7.5 Completion candidates

Completion audit is not a version-directory family.

Canonical layout:

```text
runtime/candidates/completion/
  candidate-manifest.json
  attempt-01.json
  attempt-02.json
  ...
```

Rules:

- one fixed Candidate manifest;
- attempt number is one-based;
- only structurally valid attempts are saved;
- raw invalid responses remain only in LLM-call audit;
- the first structurally valid attempt becomes the selected candidate;
- a valid semantic `incomplete` attempt does not cause another attempt.

### 7.6 Candidate immutability

After a candidate file is written:

- its bytes never change;
- revision creates a new version;
- staleness regeneration creates a new version;
- old candidate and Review remain history.

The active version's Candidate manifest may be atomically updated while active. Once superseded, it is immutable.

### 7.7 Candidate cleanup

Candidate files and manifests are not audit-retention cleanup targets.

Automatic deletion is forbidden.

Manual compaction requires an explicit archival feature that preserves all manifest and hash references. Version 1 does not provide such compaction.

---

## 8. `runtime/context-snapshots/`

Canonical path:

```text
runtime/context-snapshots/
  <operation-id-lower>/
    <target-id-path-safe>/
      <context-sha256>.json
```

Properties:

- immutable;
- deterministic;
- no creation timestamp inside the snapshot;
- filename equals SHA-256 of complete canonical bytes;
- one snapshot may be referenced by Candidate manifest, Review, Completion precondition, and LLM-call audit;
- same semantic sources produce identical bytes and path.

A hash/path mismatch invalidates the snapshot.

Context snapshots are resume sources only through an authoritative manifest reference.

They are not selected by scanning a target directory.

---

## 9. `runtime/checkpoints/`

Version 1 uses Scene checkpoints only.

Canonical path:

```text
runtime/checkpoints/scenes/vNN/cNNN/sNNN/
```

### 9.1 Phase-dependent files

| phase | required files |
|---|---|
| `CARD_ACCEPTED` | `scene-card.json`, `checkpoint-manifest.json` |
| `PROSE_FROZEN` | previous files plus `prose.md` |
| `DELTA_ACCEPTED` | previous files plus `continuity-delta.json` |
| `COMMIT_PREPARED` | previous files plus `commit-plan.json`, staged transaction reference in manifest |

An unreferenced later-phase file is not promoted by inference.

### 9.2 Frozen-file immutability

| file | immutable after |
|---|---|
| `scene-card.json` | `CARD_ACCEPTED` |
| `prose.md` | `PROSE_FROZEN` |
| `continuity-delta.json` | `DELTA_ACCEPTED` |
| `commit-plan.json` | successful COMMIT-01 |

Changing a frozen byte requires checkpoint invalidation.

### 9.3 Checkpoint authority

The Checkpoint manifest is the phase and hash authority.

A checkpoint directory is not interpreted from file presence alone.

### 9.4 Checkpoint cleanup

After a successful Scene commit:

- the checkpoint is no longer a resume source;
- code removes it after HEAD and Run state are durable;
- leftover valid checkpoint content is cleanup residue;
- startup first proves whether the Scene commit is already adopted.

---

## 10. `runtime/orphans/`

Canonical quarantine path:

```text
runtime/orphans/<timestamp-basic>/
```

Every quarantine batch contains:

```text
orphan-manifest.json
```

### 10.1 Purpose

Quarantine isolates content that is:

```text
unreferenced by valid HEAD
unreferenced by valid CURRENT
partial staging
partial candidate version
unreferenced checkpoint file
conflicting adopted-looking artifact
invalid pointer target
temporary file residue
```

### 10.2 Not an adoption queue

Quarantine content is never automatically promoted back into:

```text
canon/generations
artifacts
publications
runtime/checkpoints
```

Recovery requires an explicit validated recovery procedure.

### 10.3 Original structure

Quarantine should preserve enough original relative structure to diagnose the item.

Example:

```text
runtime/orphans/20260722T091530123456Z/
  orphan-manifest.json
  canon/generations/00000042/
  artifacts/scenes/v03/c004/s002/
```

### 10.4 Deletion

Automatic deletion is permitted only when:

```text
orphan-manifest.cleanup_permitted = true
retention policy permits deletion
no active manual hold exists
all items remain unreferenced
```

---

# Part II: Adopted story artifacts

## 11. `canon/`

The `canon/` directory contains adopted immutable generation history and the current-generation pointer.

### 11.1 `canon/HEAD`

Plain UTF-8 text:

```text
<generation-id>\n
```

Rules:

- exactly one Generation ID;
- exactly one final LF;
- no spaces or comments;
- written by atomic replacement;
- changed only after the target generation and its conditional Scene/Handoff artifact are durable.

### 11.2 `canon/initial-design.json`

Immutable adopted Initial-design snapshot.

It records:

```text
accepted integrated Initial-design content
Brief hash
persistent-ID mapping result
Genesis Commit identity
adopted record ID inventories
```

It is not the current mutable Canon root.

### 11.3 Generation directory

Canonical path:

```text
canon/generations/<generation-id>/
```

Exact files:

```text
current-canon.json
knowledge-items.json
story-state.json
evidence-index.json
commit-manifest.json
generation-manifest.json
```

No other file is permitted inside a finalized Generation directory.

### 11.4 Genesis

```text
canon/generations/00000000/
```

Genesis has:

```text
Commit type = initial_design
parent generation = null
current_order = 0
empty Evidence index
```

### 11.5 Scene generation

A Scene commit creates a new Generation whose:

```text
current_order = parent current_order + 1
source Scene fields are non-null
source Handoff fields are null
```

### 11.6 Handoff generation

A Volume-handoff commit creates a new Generation whose:

```text
current_order = parent current_order
source Scene fields are null
source Handoff fields are non-null
```

Only Thread `volume_disposition` may differ from its parent Story state.

### 11.7 Generation immutability

After the directory is adopted through HEAD:

- no file is modified;
- no file is added;
- no file is deleted;
- corrections require a new Commit/Generation.

### 11.8 Reachability

A valid current generation is selected by:

```text
canon/HEAD
→ generation-manifest.json
→ commit-manifest.json
→ conditional Scene or Handoff artifact
```

Earlier generations remain immutable history.

---

## 12. `plans/`

Planning artifacts are immutable adopted intent.

### 12.1 Series map

```text
plans/series-map.json
```

Adopted once after Genesis.

### 12.2 Volume design

```text
plans/volumes/vNN/volume-design.json
```

Adopted before the first Chapter of that Volume.

### 12.3 Chapter design

```text
plans/volumes/vNN/chapters/cNNN/chapter-design.json
```

Adopted before the first Scene of that Chapter.

### 12.4 Plan hierarchy

Required parent relationships:

```text
series-map.json
└── Volume target vNN
    └── volume-design.json
        └── Chapter target cNNN
            └── chapter-design.json
                └── Scene target sNNN
```

### 12.5 Immutability

An adopted plan is not rewritten to match later prose.

If later execution differs semantically, that difference is represented by:

```text
Review/residual issues
Scene prose
committed continuity delta
Volume handoff
Completion audit
```

not by modifying the plan.

### 12.6 Forbidden old paths

Forbidden:

```text
plans/volumes/v01.json
plans/chapters/v01/c001.json
plans/v01/c001.json
```

Required:

```text
plans/volumes/v01/volume-design.json
plans/volumes/v01/chapters/c001/chapter-design.json
```

---

## 13. `artifacts/scenes/`

Canonical adopted Scene root:

```text
artifacts/scenes/vNN/cNNN/sNNN/
```

Exact files:

```text
scene-card.json
prose.md
continuity-delta.json
scene-manifest.json
```

### 13.1 Scene manifest authority

`scene-manifest.json` identifies:

```text
Scene ID and coordinates
source and adopted generation
final artifact-relative paths
artifact hashes and sizes
Evidence IDs
character count
```

### 13.2 Adopted path rule

The Scene manifest may point only to final adopted Scene paths.

Forbidden:

```text
runtime/checkpoints/...
.staging/scene-commits/...
runtime/candidates/...
```

### 13.3 Byte equality

Adopted:

```text
scene-card.json
prose.md
```

must be byte-identical to the frozen checkpoint versions.

The committed delta normally differs from the candidate checkpoint delta because code resolves IDs and Evidence records.

### 13.4 Adoption

A Scene directory is adopted only when:

```text
it validates
its Scene manifest is referenced by the HEAD-reachable Scene Commit/Generation
```

A standalone Scene directory is an orphan, not an adopted scene.

---

## 14. `artifacts/handoffs/`

Canonical path:

```text
artifacts/handoffs/vNN.json
```

One file exists per completed Volume.

### 14.1 Authority

An adopted Handoff is valid only when:

```text
its hash is referenced by a HEAD-reachable volume_handoff Commit and Generation
```

### 14.2 Immutability

The Handoff file is immutable after Handoff Commit adoption.

### 14.3 Private content

Handoffs are private planning artifacts.

They are not copied directly into publication.

A safe projection may be included in later Context snapshots.

### 14.4 Forbidden old paths

Forbidden:

```text
artifacts/handoffs/v01/
artifacts/handoffs/v01/handoff.json
artifacts/volume-handoffs/v01.json
```

Required:

```text
artifacts/handoffs/v01.json
```

---

# Part III: Audit and logs

## 15. `audit/llm-calls/`

Canonical filename:

```text
<sequence>__<operation-id>__<target-id>__<role>__attempt-NN[__round-NN].json.gz
```

Example:

```text
000123__prose-01__v01-c003-s002__generate__attempt-02.json.gz
```

Rules:

- one immutable file per provider HTTP attempt under the selected audit policy;
- gzip contains exactly one canonical JSON object;
- no filename reuse;
- request/response bodies are redacted according to Effective config;
- hash and byte metadata remain even when body storage is disabled.

LLM-call audits are never candidate or resume authority.

---

## 16. `audit/operations/`

Canonical filename:

```text
<timestamp-basic>__<operation-id>__<target-id>__<event>.json
```

Example:

```text
20260722T091530123456Z__commit-04__v01-c001-s001__adopted.json
```

Contains immutable code-only operation events such as:

```text
candidate activated
Review routed
checkpoint frozen
transaction validated
HEAD changed
publication adopted
orphan quarantined
Run state reconciled
```

Code operations must not be stored in `audit/llm-calls/`.

---

## 17. `audit/residual-issues.jsonl`

Append-only canonical JSON Lines file.

Properties:

- one unresolved normalized Issue per line;
- lines are appended while the workspace lock is held;
- each line ends with LF;
- not a story fact source;
- not copied directly into Writer View or publication;
- safe residual constraints may be derived by Context Builder.

If no residual issue has ever been recorded, the file may be absent.

---

## 18. `audit/completion/`

Canonical root:

```text
audit/completion/<generation-id>/
```

Files:

```text
completion-precondition.json
completion-audit.json
```

The directory key is the final generation evaluated by Completion.

`completion-precondition.json` is code-only.

`completion-audit.json` is the accepted private audit and may contain private author-only references.

Neither file is copied directly into publication.

---

## 19. `audit/publication-gates/`

Canonical path:

```text
audit/publication-gates/<publication-id>.json
```

The Gate stores:

```text
Publication ID
root-relative Validation and Manifest paths
Validation and Manifest hashes
payload_set_sha256
content_set_sha256
rename-stable publication_snapshot_sha256
pass/fail result
```

It must not persist:

```text
.staging/publication/<id>/...
publications/<id>/...
```

for publication-internal paths.

The Gate is immutable and external to the publication directory.

---

## 20. Audit retention

Retention cleanup may delete only audit files that satisfy all configured conditions.

It never deletes:

```text
candidate files or manifests
Context snapshots referenced by active/history manifests
Scene checkpoints
adopted Generations
adopted plans
adopted Scene artifacts
adopted Handoffs
adopted publications
pointer files
```

A retained audit file referenced by a Gate, Completion record, Candidate manifest, or operation hold must not be deleted.

---

## 21. `logs/`

Canonical normal log:

```text
logs/storycraft.log
```

Properties:

- human-readable;
- controlled by Effective-config `log_level`;
- secret-redacted at every level;
- raw prompts and raw provider responses forbidden;
- not a resume source;
- not an adopted artifact;
- may be rotated only by an explicit logging policy.

A missing normal log must not prevent resume when authoritative manifests remain valid.

---

# Part IV: Transactions and publication

## 22. `.staging/genesis/`

Canonical path:

```text
.staging/genesis/<run-id>/
```

Contains:

```text
initial-design.json
generation/00000000/
genesis-validation.json
```

It exists only while INIT-ID prepares Genesis.

After successful adoption:

- Generation moves to `canon/generations/00000000`;
- Initial design moves to `canon/initial-design.json`;
- `canon/HEAD` is written last;
- staging is removed.

Content left before HEAD is unadopted.

---

## 23. `.staging/planning/`

Canonical paths:

```text
.staging/planning/series-map/<run-id>/
.staging/planning/volumes/vNN/<run-id>/
.staging/planning/chapters/vNN/cNNN/<run-id>/
```

Each transaction contains:

```text
one staged final plan
plan-validation.json
```

After successful adoption, the plan moves to its immutable `plans/` path.

A final plan path is never replaced by a different plan.

---

## 24. `.staging/scene-commits/`

Canonical path:

```text
.staging/scene-commits/<scene-id>/
```

Contents:

```text
transaction-manifest.json
merge-plan.json
transaction-validation.json
generation/<generation-id>/
scene/
```

The staged `scene/` directory contains the four final Scene files.

### 24.1 Transaction authority

Resume uses:

```text
Checkpoint manifest
transaction-manifest.json
merge-plan.json
transaction-validation.json
```

not directory presence alone.

### 24.2 Adoption order

```text
staged Generation rename
→ staged Scene rename
→ both revalidated
→ canon/HEAD atomic replacement
→ Run-state update
```

### 24.3 Cleanup

After HEAD is durable:

- remaining staging is cleanup residue;
- checkpoint is removed after reconciliation;
- failure before HEAD produces unadopted orphan content.

---

## 25. `.staging/handoffs/`

Canonical path:

```text
.staging/handoffs/vNN/<run-id>/
```

Contents:

```text
handoff.json
handoff-validation.json
generation/<generation-id>/
```

Adoption order:

```text
staged Generation rename
→ Handoff placed at artifacts/handoffs/vNN.json
→ both revalidated
→ canon/HEAD atomic replacement
→ Run-state update
```

A Handoff file without a HEAD-reachable Handoff Generation is not authoritative.

---

## 26. `.staging/publication/`

Canonical path:

```text
.staging/publication/<publication-id>/
```

### 26.1 OUT-01 state

Contains:

```text
payload files
publication-build-manifest.json
```

It does not yet contain a final Validation or Manifest.

### 26.2 OUT-02 finalized state

Contains exactly:

```text
publication-manifest.json
every file listed in publication-manifest.json.files
```

Normally including:

```text
publication-validation.json
manuscript/
metadata/
reports/
```

It must not contain:

```text
publication-build-manifest.json
```

### 26.3 Publication-relative paths

All internal paths are relative to the publication root.

The same references remain valid after:

```text
.staging/publication/<publication-id>
→
publications/<publication-id>
```

### 26.4 Gate

COMP-PUBLISH validates finalized staging and writes an external Gate.

It does not modify or rename staging.

### 26.5 Adoption

OUT-03:

```text
staging rename
→ final-root revalidation
→ output/CURRENT atomic replacement
→ Run-state completion
```

---

## 27. `publications/`

Canonical adopted publication path:

```text
publications/<publication-id>/
```

### 27.1 Final exact root

A valid default publication contains:

```text
publication-manifest.json
publication-validation.json
manuscript/
metadata/
reports/
```

No provisional build manifest is allowed.

### 27.2 Adoption status

A final publication directory is adopted only when:

```text
output/CURRENT
```

points to its Publication ID and the Manifest/file set validates.

### 27.3 Immutability

After adoption:

- payload files are immutable;
- Validation is immutable;
- Manifest is immutable;
- corrections create a new Publication ID.

### 27.4 Multiple publications

Multiple immutable publication directories may remain.

Only `output/CURRENT` selects the current one.

---

## 28. `output/CURRENT`

Plain UTF-8 text:

```text
<publication-id>\n
```

Rules:

- exactly one Publication ID;
- exactly one final LF;
- no spaces or comments;
- atomic replacement;
- changed only after the publication directory is durable and reproduces the passing Gate snapshot.

A publication directory with no matching CURRENT pointer is unadopted.

---

## 29. `.storycraft.lock`

Canonical lock path:

```text
.storycraft.lock
```

### 29.1 Purpose

The lock prevents concurrent writers from modifying:

```text
Run state
counters
candidates
checkpoints
staging
Canon pointers
publication pointers
audit append files
```

### 29.2 Scope

The lock covers the entire workspace.

Per-file or per-stage locks are not sufficient for version 1.

### 29.3 Lock content

The lock implementation may store diagnostic metadata such as:

```text
process ID
hostname
run ID
acquired timestamp
```

This metadata is not authoritative.

### 29.4 Stale lock

A stale-looking lock is not removed solely because its timestamp is old.

Code must use platform-appropriate ownership/liveness checks and explicit recovery policy.

---

# Part V: Authority and lifecycle

## 30. Authority matrix

| object | authoritative path |
|---|---|
| input source | `input/keywords.json` or adopted Brief source |
| adopted Brief | `input/brief.json` |
| current run position | `runtime/run-state.json` |
| counters | `runtime/counters.json` |
| semantic configuration | `runtime/effective-config.json` |
| active candidate | Candidate manifest referenced by Run state |
| candidate content | `candidate_path` in that Candidate manifest |
| candidate Review | `review_path` in that Candidate manifest |
| frozen Scene phase | active `checkpoint-manifest.json` |
| current generation | `canon/HEAD` |
| generation contents | HEAD-selected Generation manifest and roots |
| adopted Series plan | `plans/series-map.json` |
| adopted Volume plan | `plans/volumes/vNN/volume-design.json` |
| adopted Chapter plan | `plans/volumes/vNN/chapters/cNNN/chapter-design.json` |
| adopted Scene | HEAD-reachable Scene manifest |
| adopted Handoff | HEAD-reachable Handoff Commit/Generation |
| accepted Completion audit | `audit/completion/<generation-id>/completion-audit.json` |
| publication Gate | `audit/publication-gates/<publication-id>.json` |
| current publication | `output/CURRENT` |

Audit call bodies and normal logs are never authority for candidate content or story state.

---

## 31. Mutability matrix

| path family | mutable? | rule |
|---|---|---|
| `input/*.json` | no after adoption | immutable input |
| `runtime/run-state.json` | yes | atomic replacement |
| `runtime/counters.json` | yes | persist-before-use |
| `runtime/effective-config.json` | no | immutable materialization |
| candidate file | no | new version for change |
| active Candidate manifest | yes while active | atomic replacement |
| superseded Candidate manifest | no | immutable |
| Context snapshot | no | hash-named immutable |
| frozen checkpoint artifact | no after phase | invalidate checkpoint for change |
| Checkpoint manifest | yes during phase progression | atomic replacement |
| Generation file | no | new Generation for change |
| adopted plan | no | never rewritten |
| adopted Scene/Handoff | no | new Commit/artifact required |
| audit file | no | immutable; residual JSONL append-only |
| normal log | append/rotate | non-authoritative |
| staging | yes within transaction | unadopted |
| adopted publication | no | new Publication ID |
| pointer file | yes | atomic replacement |

---

## 32. Lifecycle matrix

| lifecycle state | location |
|---|---|
| generated candidate | `runtime/candidates/.../vNNNN/` |
| reviewed candidate | same version directory plus `review.json` |
| revised candidate | next version directory |
| frozen Scene input | `runtime/checkpoints/scenes/.../` |
| transaction build | `.staging/...` |
| adopted Canon generation | `canon/generations/<id>/` |
| adopted plan | `plans/...` |
| adopted Scene | `artifacts/scenes/...` |
| adopted Handoff | `artifacts/handoffs/vNN.json` |
| private audit | `audit/...` |
| finalized unadopted publication | `.staging/publication/<id>/` |
| adopted publication directory | `publications/<id>/` plus CURRENT |
| unreferenced/partial content | `runtime/orphans/<timestamp>/` |

Movement between lifecycle states is performed only by the owning pipeline stage.

---

## 33. Cross-path invariants

A valid workspace satisfies:

```text
Run-state current_head_generation equals canon/HEAD
Run-state current_publication_id equals output/CURRENT when non-null

every HEAD Generation directory contains exactly six required files
every Generation root hash matches Generation manifest
every Commit manifest conditional Scene/Handoff path resolves
every adopted Scene path matches Scene ID coordinates
every adopted Handoff path matches Volume number

every adopted plan path matches its numeric fields
every Candidate version path matches Candidate-manifest version
every Candidate-manifest candidate path stays in its own version directory
every version-local Review path stays in the same version directory

every Context filename equals its content hash
every Checkpoint-manifest artifact path stays in its Scene checkpoint directory
every frozen checkpoint hash matches

every Publication-manifest internal path is publication-root-relative
every Publication-manifest file is under its own publication root
every Gate internal publication path is root-relative
every CURRENT target Publication manifest validates

no authoritative manifest references runtime/orphans
no adopted manifest references .staging
no publication payload references workspace-private paths
```

---

## 34. Startup scan order

Startup validates in this order:

1. acquire `.storycraft.lock`;
2. validate workspace-root security and canonical directory names;
3. validate `runtime/run-manifest.json` when present;
4. validate `runtime/effective-config.json`;
5. validate `runtime/counters.json`;
6. validate `canon/HEAD` when present;
7. validate the full HEAD Generation/Commit/conditional artifact graph;
8. validate `output/CURRENT` when present;
9. validate the CURRENT Publication manifest/file set;
10. validate `runtime/run-state.json`;
11. compare Run-state HEAD/CURRENT identities to pointers;
12. inspect active Candidate manifest path;
13. inspect active Checkpoint manifest path;
14. scan `.staging/` for explicitly resumable transactions;
15. scan for HEAD-unreachable Generations, Scenes, and Handoffs;
16. scan for CURRENT-unreferenced partially adopted publication directories;
17. scan for partial candidate versions and temporary files;
18. quarantine only content proven or suspected to be non-authoritative;
19. reconcile Run state from valid adopted pointer graphs when required;
20. continue from the authoritative next stage.

Startup does not quarantine a path before checking whether a valid pointer/manifest references it.

---

## 35. Directory creation

Code creates directories lazily.

Rules:

- create parent directories before a same-directory atomic write;
- creating an empty directory has no lifecycle meaning;
- permissions are applied at creation;
- a directory existing early does not imply a stage completed;
- manifests and pointer files determine completion.

Empty unused candidate or staging directories may be removed.

---

## 36. Permissions and sensitive content

Recommended default permissions:

| path | recommendation |
|---|---|
| workspace root | owner-only write |
| `runtime/` | owner-only read/write |
| `audit/` | owner-only read/write |
| `.staging/` | owner-only read/write |
| `.storycraft.lock` | owner-only |
| `publications/` | owner write; read policy chosen by user |
| `logs/` | owner-only by default |

Private content may appear in:

```text
runtime/context-snapshots
runtime/candidates
audit
artifacts/handoffs
canon/initial-design.json
Canon records with author-only fields
```

Those paths must not be made public merely because `publications/` is shared.

Credential values are forbidden everywhere in the workspace.

---

## 37. Durability rules

For every authoritative atomic write:

1. write a temporary same-directory file;
2. flush file content;
3. `fsync` the file when supported;
4. atomically replace or rename to the final path;
5. `fsync` the parent directory when supported;
6. re-read and validate bytes when the pipeline contract requires it.

For directory adoption:

1. all files are durable;
2. all child directories are durable;
3. atomic directory rename occurs;
4. adopted directory is revalidated;
5. pointer file is atomically replaced last.

These rules apply to:

```text
Genesis
plan adoption
Scene commit
Volume-handoff commit
Publication adoption
```

---

## 38. Retention and cleanup boundaries

### 38.1 Never automatic retention cleanup

Automatic retention cleanup must not delete:

```text
input
Run manifest/state/counters/config
candidate files/manifests
Context snapshots referenced by any retained manifest
active or retained checkpoint
Canon Generations
plans
adopted Scenes
adopted Handoffs
publications
pointer files
passing Publication Gates for retained publications
```

### 38.2 Audit retention

Audit retention follows Effective config and `review_and_audit.md`.

Before deleting an audit file, code verifies it is not referenced by:

```text
Candidate manifest
Commit/Generation/Scene/Handoff manifest
Completion record
Publication Gate
manual hold
active run
```

### 38.3 Normal log rotation

Log rotation may operate independently of audit retention.

Normal logs remain non-authoritative.

### 38.4 Quarantine cleanup

Quarantine cleanup follows Section 10.4.

---

## 39. Forbidden layouts

The following are forbidden.

### 39.1 Old candidate layout

```text
runtime/candidates/scenes/v01/c001/s001/scene-card.json
runtime/candidates/series-map/
runtime/candidates/volumes/v01/
runtime/candidates/chapters/v01/c001/
```

Required versioned roots are under:

```text
runtime/candidates/planning/...
runtime/candidates/scenes/.../<family>/vNNNN/
```

### 39.2 Mutable adopted generation

```text
canon/current-canon.json
canon/story-state.json
canon/evidence-index.jsonl
```

Current roots belong under the HEAD Generation directory.

The Evidence file is:

```text
evidence-index.json
```

not JSON Lines.

### 39.3 Flat plan paths

```text
plans/volumes/v01.json
plans/chapters/v01/c001.json
```

### 39.4 Checkpoint as adopted Scene

```text
artifacts/scenes/... → symlink to runtime/checkpoints/...
```

### 39.5 Handoff directory form

```text
artifacts/handoffs/v01/handoff.json
```

### 39.6 Publication manifest with staging paths

```text
.staging/publication/pub-000001/manuscript/v01.md
```

inside a final Manifest or Gate.

### 39.7 Pointer alternatives

```text
canon/current
canon/latest
output/latest
publications/CURRENT
```

### 39.8 Mixed artifact classes in one field

```text
review candidate
adopted/audit
candidate/checkpoint
```

---

## 40. Mechanical acceptance conditions

An implementation of this layout is acceptable only when tests demonstrate:

```text
canonical top-level directory names
workspace-root containment
absolute-path rejection
dot-segment and traversal rejection
separator normalization
case-collision detection
symlink/reparse-point escape rejection

Volume/Chapter/Scene fixed-width path validation
Scene ID/path equality
candidate-version validation
Generation/Commit/Publication ID validation
timestamp-basic validation
path-safe target validation

Brief- and Keywords-mode input layouts
runtime root exact filenames
versioned Initial-design candidate paths
versioned planning candidate paths
versioned Scene candidate-family paths
versioned Handoff paths
Completion attempt layout
version-local Review filename
active Candidate selection only from Run state

Context hash-named paths
Checkpoint phase-dependent file set
Checkpoint-manifest authority
orphan quarantine manifest
quarantine non-promotion

Generation exact six-file set
evidence-index.json filename
Genesis/Scene/Handoff generation distinctions
HEAD pointer exact bytes
adopted plan hierarchy
adopted Scene exact four-file set
Handoff exact file path
HEAD reachability checks

LLM-call audit filename uniqueness
operation-audit filename uniqueness
residual JSONL path
Completion audit path
Publication Gate path
normal log path and non-authority

Genesis staging layout
planning staging layouts
Scene-commit staging layout
Handoff staging layout
Publication provisional/finalized staging distinction
provisional build-manifest removal

Publication payload-set and final file-set path rules
publication-root-relative internal references
Publication exact default root
CURRENT pointer exact bytes
publication-directory non-adoption without CURRENT

lock acquisition and stale-lock policy
atomic same-directory writes
directory rename then pointer-last durability
startup scan order
Run-state pointer reconciliation
cleanup/retention boundaries

forbidden old candidate paths
forbidden flat plan paths
forbidden mutable Canon roots
forbidden JSONL Evidence filename
forbidden staging path in adopted manifest/Gate
unknown managed path rejection
