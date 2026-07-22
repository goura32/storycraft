# Ledger contracts: Runtime records and manifests

This document is the normative contract for Storycraft execution state, allocation counters, versioned candidate resume records, scene checkpoints, adopted Scene, Volume-handoff, Commit, Generation, and Publication manifests, pointer files, and runtime recovery metadata.

- Domain identity and fixed Canon records are defined by [`canon_records.md`](canon_records.md).
- Mutable adopted story values are defined by [`story_state.md`](story_state.md).
- Continuity candidates, committed deltas, and Evidence records are defined by [`evidence_and_updates.md`](evidence_and_updates.md).
- Config fields and permitted resume-time config changes are defined by [`configuration_contracts.md`](../../configuration_contracts.md).
- Stage IDs and transitions are defined by [`pipeline_contracts.md`](../../pipeline_contracts.md).
- Canonical paths are summarized by [`workspace_layout.md`](../../workspace_layout.md).

Every JSON object defined here uses `additionalProperties: false`.

---

## 1. Runtime principles

### 1.1 Authority boundaries

| concern | authority |
|---|---|
| Stable story identity and fixed facts | adopted Canon generation |
| Mutable story values | adopted Story state |
| Candidate resume | `candidate-manifest.json` |
| Scene checkpoint resume | `checkpoint-manifest.json` |
| Global run resume | `runtime/run-state.json` |
| Numeric allocation | `runtime/counters.json` |
| Current adopted generation | `canon/HEAD` |
| Current adopted publication | `output/CURRENT` |
| Historical Scene adoption | adopted Scene manifest |
| Historical Volume-handoff adoption | adopted Volume-handoff artifact plus HEAD-reachable Handoff Commit/Generation manifests |
| Historical generation adoption | adopted Generation and Commit manifests |
| Raw LLM request/response | audit gzip files only |

Audit files are never resume authorities. Candidate content without its valid manifest is never a resume authority.

### 1.2 Single-writer rule

Version 1 supports one process writing one workspace.

- The process must hold the workspace lock at `.storycraft.lock` before mutating runtime, staging, Canon, artifact, publication, or pointer files.
- A second writer fails before changing any file.
- Network filesystems and distributed locks are outside version 1.
- Read-only inspection may occur without the lock only when the inspector tolerates atomic pointer changes.

### 1.3 Atomic JSON write

A mutable runtime JSON file is replaced by:

1. serialize canonical bytes;
2. write a temporary file in the same directory;
3. flush and `fsync` the temporary file;
4. atomically replace the destination;
5. `fsync` the containing directory where supported.

Partial in-place writes are forbidden.

---

## 2. Shared scalar contracts

### 2.1 Canonical JSON bytes

JSON artifact hashes use:

```text
UTF-8
Unicode NFC for every string
object keys sorted by Unicode code-point order
compact separators: "," and ":"
no insignificant whitespace
exactly one trailing LF
```

Numbers must be serialized in a deterministic JSON representation supported by the implementation. NaN and infinities are forbidden.

### 2.2 Canonical text bytes

Markdown and prose artifact hashes use:

```text
UTF-8
Unicode NFC
CRLF and CR normalized to LF
trailing horizontal whitespace removed from every line
exactly one trailing LF
```

### 2.3 SHA-256

A SHA-256 field is a lowercase 64-character hexadecimal string calculated from the applicable canonical bytes.

### 2.4 Workspace-relative path

A workspace-relative path:

- uses `/` as separator;
- is not empty;
- is not absolute;
- contains no `.` or `..` segment;
- contains no NUL;
- resolves inside the workspace after symlink-safe validation.

Runtime code must not follow a path through a symlink that escapes the workspace.

### 2.5 Timestamp

All saved timestamps use RFC 3339 UTC form with `Z`.

Example:

```text
2026-07-22T09:15:30.123456Z
```

### 2.6 Runtime IDs

| ID | pattern | example | allocation |
|---|---|---|---|
| Run ID | `run-[0-9a-f]{32}` | `run-550e8400e29b41d4a716446655440000` | UUIDv4 bytes, lowercase hex, code-only |
| Generation ID | `[0-9]{8}` | `00000001` | equal to adopted Commit numeric suffix |
| Commit ID | `commit-[0-9]{8}` | `commit-00000001` | `next_commit_id`; Genesis is reserved `commit-00000000` |
| Publication ID | `pub-[0-9]{6}` | `pub-000001` | `next_publication_id` |
| Call ID | `call-[0-9]{6,}` | `call-000123` | `next_call_id` |

Allocated numbers are never reused. Gaps are valid.

---

## 3. Runtime file layout governed by this contract

```text
runtime/
  run-manifest.json
  run-state.json
  counters.json
  effective-config.json
  candidates/
    input/brief/v0001/
      brief.json
      candidate-manifest.json
    initial-design/bundle/v0001/
      bundle.json
      review.json
      candidate-manifest.json
    planning/series-map/v0001/
      series-map.json
      review.json
      candidate-manifest.json
    scenes/v01/c001/s001/
      scene-card/v0001/
        scene-card.json
        review.json
        candidate-manifest.json
      prose/v0001/
        prose.md
        review.json
        candidate-manifest.json
      continuity/v0001/
        continuity-delta.json
        review.json
        candidate-manifest.json
    handoffs/v01/v0001/
      volume-handoff.json
      review.json
      candidate-manifest.json
    completion/
      attempt-01.json
      attempt-02.json
      candidate-manifest.json
  checkpoints/
    scenes/v01/c001/s001/
      scene-card.json
      prose.md
      continuity-delta.json
      commit-plan.json
      checkpoint-manifest.json
  context-snapshots/
    <operation-id-lower>/<target-id-path-safe>/<context-sha256>.json
  orphans/
    <timestamp>/
      orphan-manifest.json
      <quarantined files>

canon/
  HEAD
  initial-design.json
  generations/00000001/
    current-canon.json
    knowledge-items.json
    story-state.json
    evidence-index.json
    commit-manifest.json
    generation-manifest.json

artifacts/
  scenes/v01/c001/s001/
    scene-card.json
    prose.md
    continuity-delta.json
    scene-manifest.json
  handoffs/
    v01.json

publications/
  pub-000001/
    publication-manifest.json
    publication-validation.json
    manuscript/
    metadata/
    reports/

output/
  CURRENT
```

Every ordinary candidate family uses immutable `vNNNN` version directories. The Completion-audit family instead uses numbered `attempt-NN.json` files and one fixed Candidate manifest.

Candidate artifact filenames are operation-specific. Within one candidate version directory, only these filenames are fixed:

```text
candidate-manifest.json
review.json  # present only after that exact version is reviewed
```

---

## 4. Runtime enum registry

| enum | permitted values |
|---|---|
| `input_mode` | `brief`, `keywords` |
| `run_status` | `initialized`, `running`, `paused`, `stopped`, `failed`, `completed` |
| `scene_phase` | `SCENE_NOT_STARTED`, `CARD_ACCEPTED`, `PROSE_FROZEN`, `DELTA_ACCEPTED`, `COMMIT_PREPARED`, `SCENE_COMMITTED` |
| `candidate_status` | `initialized`, `candidate_valid`, `reviewed`, `revision_required`, `ready_for_adoption`, `exhausted`, `failed` |
| `processor_type` | `code`, `llm_generate`, `llm_review`, `llm_revise`, `llm_extract` |
| `candidate_artifact_format` | `json`, `markdown`, `text` |
| `checkpoint_phase` | `CARD_ACCEPTED`, `PROSE_FROZEN`, `DELTA_ACCEPTED`, `COMMIT_PREPARED` |
| `commit_type` | `initial_design`, `scene`, `volume_handoff` |
| `allocation_type` | `character`, `relationship`, `location`, `organization`, `item`, `system`, `culture`, `history`, `temporal_rule`, `thread`, `ending_criterion`, `knowledge_item` |
| `plan_ref_role` | `series_map`, `volume_design`, `chapter_design`, `volume_handoff` |
| `publication_file_role` | `manuscript`, `metadata`, `report`, `validation` |
| `audit_call_role` | `generate`, `review`, `revise`, `extract` |
| `stop_reason_code` | `user_stop`, `budget_exhausted`, `mechanical_error`, `manual_intervention`, `completed` |
| `orphan_reason` | `head_unreachable_generation`, `unreferenced_scene_artifact`, `unreferenced_volume_handoff`, `unadopted_publication`, `abandoned_staging`, `invalid_pointer_target` |

Stage IDs are the exact stage-ID enum defined by the Pipeline contracts. This document does not introduce aliases.

---

## 5. `runtime/run-manifest.json`

The Run manifest is created once before `INPUT-01` and is immutable.

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `manifest_version` | string | yes | no | none | code | immutable | supported Run-manifest Schema version | Run manifest |
| `run_id` | Run ID | yes | no | none | code | immutable | unique in workspace history | Run manifest |
| `created_at` | timestamp | yes | no | none | code | immutable | valid UTC timestamp | Run manifest |
| `created_by` | string | yes | no | `storycraft` | code | immutable | NFC nonempty | Run manifest |
| `input_mode` | enum `input_mode` | yes | no | none | code from CLI input | immutable | `brief` or `keywords` | Run manifest |
| `input_source_path` | workspace-relative path | yes | no | none | code | immutable | `input/brief.json` for brief mode or `input/keywords.json` for keywords mode | Run manifest |
| `input_source_sha256` | SHA-256 | yes | no | none | code | immutable | hash of raw canonical input source | Run manifest |
| `state_version` | string | yes | no | none | code | immutable | supported state contract version | Run manifest |
| `workspace_version` | string | yes | no | none | code | immutable | supported workspace-layout version | Run manifest |
| `code_version` | string | yes | no | none | code | immutable | exact application build/version identifier | Run manifest |
| `prompt_bundle_version` | string | yes | no | none | code | immutable | exact prompt bundle version | Run manifest |
| `schema_bundle_version` | string | yes | no | none | code | immutable | exact structured-output Schema bundle version | Run manifest |
| `pricing_table_version` | string | yes | no | none | code from effective config | immutable | exact cost table version | Run manifest |
| `provider` | string | yes | no | none | code from effective config | immutable | NFC nonempty | Run manifest |
| `base_url` | string | yes | no | none | code from effective config | immutable | credential-free absolute HTTP(S) URL | Run manifest |
| `model` | string | yes | no | none | code from effective config | immutable | NFC nonempty | Run manifest |
| `thinking` | boolean | yes | no | none | code from effective config | immutable | boolean | Run manifest |
| `stream` | boolean | yes | no | none | code from effective config | immutable | boolean | Run manifest |
| `temperature` | number | yes | no | none | code from effective config | immutable | configuration range | Run manifest |
| `top_p` | number | yes | no | none | code from effective config | immutable | configuration range | Run manifest |
| `seed` | integer | yes | yes | `null` | code from effective config | immutable | null or provider-supported integer | Run manifest |
| `structured_output_mode` | string | yes | no | none | code from effective config | immutable | exact configured mode | Run manifest |
| `editorial_profile_id` | string | yes | no | none | code from effective config/input | immutable | NFC nonempty | Run manifest |
| `publishing_profile_id` | string | yes | no | none | code from effective config/input | immutable | NFC nonempty | Run manifest |
| `initial_effective_config_sha256` | SHA-256 | yes | no | none | code | immutable | hash of redacted initial `runtime/effective-config.json` | Run manifest |
| `immutable_config_fingerprint` | SHA-256 | yes | no | none | code | immutable | hash of the resume-immutable config subset in field-name order | Run manifest |

The immutable fingerprint covers every resume-rejected config field defined by `configuration_contracts.md`.

---

## 6. `runtime/run-state.json`

Run state is the global resume authority. It is replaced atomically after each durable state transition.

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `state_version` | string | yes | no | none | code | immutable within run | equals Run manifest `state_version` | Run state |
| `state_revision` | integer | yes | no | `0` | code | monotonic | increments by exactly one per successful Run-state replacement | integer `>=0` | Run state |
| `run_id` | Run ID | yes | no | none | code | immutable | equals Run manifest | Run state |
| `run_status` | enum `run_status` | yes | no | `initialized` | code | mutable | transition matrix below | Run state |
| `last_completed_stage` | Stage ID | yes | yes | `null` | code | mutable | null before first completed stage; otherwise known stage | Run state |
| `next_stage` | Stage ID | yes | yes | none | code | mutable | known stage; null only when `run_status=completed` or terminal failed/stopped state has no automatic continuation | Run state |
| `current_target_id` | string | yes | yes | `null` | code | mutable | null or stage-compatible target identifier | Run state |
| `current_volume_number` | integer | yes | yes | `null` | code | mutable | null or integer `>=1` | Run state |
| `current_chapter_number` | integer | yes | yes | `null` | code | mutable | null or integer `>=1`; requires volume | Run state |
| `current_scene_number` | integer | yes | yes | `null` | code | mutable | null or integer `>=1`; requires chapter | Run state |
| `scene_phase` | enum `scene_phase` | yes | yes | `null` | code | mutable | null outside active scene lifecycle; otherwise stage-compatible | Run state |
| `active_candidate_manifest_path` | workspace-relative path | yes | yes | `null` | code | mutable | null or existing `candidate-manifest.json` | Run state |
| `active_checkpoint_manifest_path` | workspace-relative path | yes | yes | `null` | code | mutable | null or existing `checkpoint-manifest.json` | Run state |
| `adopted_brief_path` | workspace-relative path | yes | yes | `null` | code | set once | null before INPUT-03; otherwise `input/brief.json` | Run state |
| `adopted_brief_sha256` | SHA-256 | yes | yes | `null` | code | set once | null iff `adopted_brief_path` is null | Run state |
| `current_head_generation` | Generation ID | yes | yes | `null` | code | mutable | null before Genesis; otherwise exact contents of `canon/HEAD` | Run state |
| `last_commit_id` | Commit ID | yes | yes | `null` | code | mutable | null before Genesis; otherwise Commit manifest of HEAD | Run state |
| `current_publication_id` | Publication ID | yes | yes | `null` | code | mutable | null before first publication; otherwise exact contents of `output/CURRENT` | Run state |
| `effective_config_sha256` | SHA-256 | yes | no | none | code | mutable only for permitted resume changes | hash of current redacted effective config | Run state |
| `last_error_audit_path` | workspace-relative path | yes | yes | `null` | code | mutable | null or existing sanitized error audit record | Run state |
| `stop_reason_code` | enum `stop_reason_code` | yes | yes | `null` | code | mutable | required for `stopped`, `failed`, or `completed`; null while initialized/running/paused | Run state |
| `stop_reason_detail` | string | yes | yes | `null` | code | mutable | null or sanitized NFC text; no secret config or raw prompt | Run state |
| `updated_at` | timestamp | yes | no | none | code | mutable | valid UTC timestamp | Run state |

### 6.1 Run-status transitions

| before | permitted after |
|---|---|
| `initialized` | `running`, `stopped`, `failed` |
| `running` | `paused`, `stopped`, `failed`, `completed` |
| `paused` | `running`, `stopped`, `failed` |
| `stopped` | `running` only through explicit resume after compatibility validation |
| `failed` | `running` only when the recorded failure is recoverable and explicit resume succeeds |
| `completed` | none |

`run_status=completed` requires:

```text
last_completed_stage = OUT-03
next_stage = null
stop_reason_code = completed
current_publication_id != null
```

### 6.2 Scene-phase consistency

| phase | required durable artifacts |
|---|---|
| `SCENE_NOT_STARTED` | no active checkpoint required |
| `CARD_ACCEPTED` | Scene card and checkpoint manifest |
| `PROSE_FROZEN` | Scene card, prose, and checkpoint manifest |
| `DELTA_ACCEPTED` | Scene card, prose, candidate continuity delta, and checkpoint manifest |
| `COMMIT_PREPARED` | complete staging transaction plus checkpoint manifest |
| `SCENE_COMMITTED` | HEAD and adopted Scene manifest updated; active checkpoint path cleared |

---

## 7. `runtime/counters.json`

Counters are code-owned, monotonic, and replaced atomically while the workspace lock is held.

### 7.1 Allocation counters

Each field below is an integer, required, non-null, code-created, code-mutated, and validated `>=1`.

| field | default | allocates |
|---|---:|---|
| `next_call_id` | `1` | Call numeric suffix |
| `next_commit_id` | `1` | Commit/Generation suffix after reserved Genesis `0` |
| `next_publication_id` | `1` | Publication suffix |
| `next_character_id` | `1` | Character ID |
| `next_relationship_id` | `1` | Relationship ID |
| `next_location_id` | `1` | Location ID |
| `next_organization_id` | `1` | Organization ID |
| `next_item_id` | `1` | Item ID |
| `next_system_id` | `1` | System ID |
| `next_culture_id` | `1` | Culture ID |
| `next_history_id` | `1` | History ID |
| `next_rule_id` | `1` | Temporal-rule ID |
| `next_thread_id` | `1` | Thread ID |
| `next_ending_id` | `1` | Ending-criterion ID |
| `next_fact_id` | `1` | Knowledge-item ID |
| `next_evidence_id` | `1` | Evidence ID |

### 7.2 Usage counters

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---:|---|---|---|
| `llm_calls_used` | integer | yes | no | `0` | code | monotonic | `>=0` |
| `transport_retries_used` | integer | yes | no | `0` | code | monotonic | `>=0` |
| `response_structure_retries_used` | integer | yes | no | `0` | code | monotonic | `>=0` |
| `revision_rounds_used` | integer | yes | no | `0` | code | monotonic | `>=0` |
| `completion_audit_attempts_used` | integer | yes | no | `0` | code | monotonic | `>=0` |
| `input_tokens_used` | integer | yes | no | `0` | code | monotonic | `>=0` |
| `output_tokens_used` | integer | yes | no | `0` | code | monotonic | `>=0` |
| `estimated_cost_used` | number | yes | no | `0` | code | monotonic | finite and `>=0` |
| `active_elapsed_seconds` | number | yes | no | `0` | code | monotonic | finite and `>=0` |
| `successful_scene_commits` | integer | yes | no | `0` | code | monotonic | `>=0`; equals HEAD Story-clock order after Genesis |

### 7.3 Allocation transaction

For every allocated numeric value:

1. read the current `next_*` value under the workspace lock;
2. atomically persist the counter increment;
3. use the reserved previous value;
4. never decrement or reuse it, even if the later operation fails.

Startup validates that every `next_*` value is greater than all observed adopted, staged, checkpoint, and audit IDs of that type. A lower counter is a mechanical corruption requiring explicit repair; code must not silently reuse IDs.

---

## 8. Candidate directory and `candidate-manifest.json`

Candidate artifact filenames are operation-specific.

Examples:

```text
runtime/candidates/initial-design/concept/v0001/concept.json
runtime/candidates/planning/volumes/v01/v0001/volume-design.json
runtime/candidates/scenes/v01/c001/s001/scene-card/v0001/scene-card.json
runtime/candidates/scenes/v01/c001/s001/prose/v0002/prose.md
runtime/candidates/handoffs/v01/v0001/volume-handoff.json
```

Each ordinary candidate version directory uses the fixed resume filename:

```text
candidate-manifest.json
```

A version directory is immutable after it is superseded. `review.json` is fixed within that exact version directory and is never overwritten by a later candidate version.

### 8.1 Candidate manifest

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `manifest_version` | string | yes | no | none | code | immutable | supported Candidate-manifest Schema | Candidate manifest |
| `operation_id` | Stage ID | yes | no | none | code | immutable | exact Pipeline stage that owns the candidate | Candidate manifest |
| `processor_type` | enum `processor_type` | yes | no | none | code | immutable | matches Pipeline stage | Candidate manifest |
| `target_id` | string | yes | no | none | code | immutable | stage-compatible target | Candidate manifest |
| `input_snapshot_path` | workspace-relative path | yes | no | none | code | immutable | exact immutable Context-snapshot path; file hash must equal `input_snapshot_sha256` | Candidate manifest |
| `input_snapshot_sha256` | SHA-256 | yes | no | none | code | immutable | SHA-256 of the immutable Context-snapshot file used for this candidate call | Candidate manifest |
| `effective_config_sha256` | SHA-256 | yes | no | none | code | immutable for this candidate generation | equals config used for calls | Candidate manifest |
| `prompt_version` | string | yes | yes | `null` | code | immutable | null for code-only operation; non-null for LLM operation | Candidate manifest |
| `response_schema_version` | string | yes | yes | `null` | code | immutable | null when no structured response Schema applies | Candidate manifest |
| `candidate_status` | enum `candidate_status` | yes | no | `initialized` | code | mutable | stage-compatible transition | Candidate manifest |
| `candidate_artifact_format` | enum `candidate_artifact_format` | yes | no | none | code | immutable | matches candidate artifact | Candidate manifest |
| `candidate_path` | workspace-relative path | yes | yes | `null` | code | mutable | null before first structurally valid candidate; otherwise existing operation-specific file | Candidate manifest |
| `candidate_sha256` | SHA-256 | yes | yes | `null` | code | mutable | null iff candidate path is null | Candidate manifest |
| `review_path` | workspace-relative path | yes | yes | `null` | code | mutable | null before valid review; otherwise `review.json` in this exact candidate version directory | Candidate manifest |
| `review_sha256` | SHA-256 | yes | yes | `null` | code | mutable | null iff review path is null | Candidate manifest |
| `candidate_version` | integer | yes | no | `1` | code | immutable for one version directory | equals the numeric suffix of `vNNNN`; starts at 1 and increases by exactly one for each complete replacement version | Candidate manifest |
| `previous_candidate_manifest_path` | workspace-relative path | yes | yes | `null` | code | immutable | null for `v0001` and Completion attempts; otherwise exact prior version Candidate manifest | Candidate manifest |
| `previous_candidate_manifest_sha256` | SHA-256 | yes | yes | `null` | code | immutable | null iff predecessor path null; matches frozen predecessor manifest | Candidate manifest |
| `revision_rounds_used` | integer | yes | no | `0` | code | immutable for one completed version | `0..max_revision_rounds`; equals the cumulative semantic revision count that produced this version | Candidate manifest |
| `transport_retries_used` | integer | yes | no | `0` | code | monotonic | per-operation count within configured bounds | Candidate manifest |
| `response_structure_retries_used` | integer | yes | no | `0` | code | monotonic | per-operation count within configured bounds | Candidate manifest |
| `completion_audit_attempt` | integer | yes | yes | `null` | code | mutable | null outside COMP-AUDIT; otherwise `1..max_completion_audit_attempts` | Candidate manifest |
| `last_call_id` | Call ID | yes | yes | `null` | code | mutable | null before first LLM call; otherwise allocated Call ID | Candidate manifest |
| `last_structurally_valid` | boolean | yes | no | `false` | code | mutable | true iff candidate path/hash identify a structurally valid artifact | Candidate manifest |
| `residual_issues_path` | workspace-relative path | yes | yes | `null` | code | mutable | non-null when adopted with unresolved review issues | Candidate manifest |
| `next_stage` | Stage ID | yes | no | none | code | mutable | exact Pipeline transition from current status/budget | Candidate manifest |
| `created_at` | timestamp | yes | no | none | code | immutable | UTC | Candidate manifest |
| `updated_at` | timestamp | yes | no | none | code | mutable | UTC and not earlier than created_at | Candidate manifest |

### 8.2 Candidate-status transitions

Within one immutable `vNNNN` version directory:

```text
initialized
→ candidate_valid
→ reviewed
→ ready_for_adoption
```

When Review finds issues and revision budget remains:

```text
reviewed
→ revision_required
```

That version is then frozen. The revision stage creates a new directory:

```text
vNNNN revision_required
→ v(N+1) initialized
→ v(N+1) candidate_valid
```

When Review finds issues and revision budget is exhausted:

```text
reviewed
→ exhausted
→ ready_for_adoption
```

The final transition occurs only after residual Issue records are durable.

`failed` is terminal for that version. Regeneration or revision creates a new version directory; it never changes failed/superseded candidate bytes.

`ready_for_adoption` requires a structurally valid candidate and either no Review issues or exhausted semantic revision budget according to the owning Pipeline contract.

### 8.3 Resume validation

A candidate is reusable only when all are true:

```text
manifest parses and validates
input_snapshot_path exists, its hash equals input_snapshot_sha256, and all snapshot source references still validate
effective config and version compatibility pass
candidate_path exists
candidate_sha256 matches canonical candidate bytes
review path/hash conditions match status
last_structurally_valid = true
next_stage is valid for status and budget
```

Otherwise code regenerates from the exact preceding authority named by the owning Pipeline contract. That authority may be adopted/frozen input or an explicitly referenced immutable earlier candidate dependency. Raw audit content is not promoted into a candidate.

---

## 9. Scene checkpoint and `checkpoint-manifest.json`

Checkpoint directory:

```text
runtime/checkpoints/scenes/v01/c001/s001/
```

### 9.1 Checkpoint manifest

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `manifest_version` | string | yes | no | none | code | immutable | supported Checkpoint-manifest Schema | Checkpoint manifest |
| `scene_id` | Scene ID | yes | no | none | code | immutable | matches directory `vNN/cNNN/sNNN` | Checkpoint manifest |
| `phase` | enum `checkpoint_phase` | yes | no | none | code | mutable | monotonic phase progression | Checkpoint manifest |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | HEAD generation used to build the Scene card/context | Checkpoint manifest |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | adopted source Generation manifest hash | Checkpoint manifest |
| `effective_config_sha256` | SHA-256 | yes | no | none | code | immutable | config used for this scene checkpoint | Checkpoint manifest |
| `scene_card_candidate_manifest_path` | workspace-relative path | yes | no | none | code | immutable | valid SC candidate manifest | Checkpoint manifest |
| `prose_candidate_manifest_path` | workspace-relative path | yes | yes | `null` | code | mutable | required from `PROSE_FROZEN` onward | Checkpoint manifest |
| `continuity_candidate_manifest_path` | workspace-relative path | yes | yes | `null` | code | mutable | required from `DELTA_ACCEPTED` onward | Checkpoint manifest |
| `scene_card_path` | workspace-relative path | yes | no | none | code | immutable after CARD_ACCEPTED | exact checkpoint Scene-card path | Checkpoint manifest |
| `scene_card_sha256` | SHA-256 | yes | no | none | code | immutable after CARD_ACCEPTED | matches checkpoint Scene card | Checkpoint manifest |
| `prose_path` | workspace-relative path | yes | yes | `null` | code | immutable after PROSE_FROZEN | conditional phase rule | Checkpoint manifest |
| `prose_sha256` | SHA-256 | yes | yes | `null` | code | immutable after PROSE_FROZEN | null iff prose path null | Checkpoint manifest |
| `continuity_delta_path` | workspace-relative path | yes | yes | `null` | code | immutable after DELTA_ACCEPTED | candidate-delta checkpoint path | Checkpoint manifest |
| `continuity_delta_sha256` | SHA-256 | yes | yes | `null` | code | immutable after DELTA_ACCEPTED | null iff delta path null | Checkpoint manifest |
| `commit_plan_path` | workspace-relative path | yes | yes | `null` | code | immutable after COMMIT-01 | required after COMMIT-01 succeeds and at COMMIT_PREPARED; otherwise null | Checkpoint manifest |
| `commit_plan_sha256` | SHA-256 | yes | yes | `null` | code | immutable after COMMIT-01 | null iff commit-plan path null | Checkpoint manifest |
| `staging_transaction_path` | workspace-relative path | yes | yes | `null` | code | mutable | required only at COMMIT_PREPARED | Checkpoint manifest |
| `created_at` | timestamp | yes | no | none | code | immutable | UTC | Checkpoint manifest |
| `updated_at` | timestamp | yes | no | none | code | mutable | UTC | Checkpoint manifest |

### 9.2 Phase conditions

| phase | Scene card | prose | candidate delta | Commit plan | staging path |
|---|---|---|---|---|---|
| `CARD_ACCEPTED` | required | null | null | null | null |
| `PROSE_FROZEN` | required | required | null | null | null |
| `DELTA_ACCEPTED`, before COMMIT-01 | required | required | required | null | null |
| `DELTA_ACCEPTED`, after COMMIT-01 | required | required | required | required | null |
| `COMMIT_PREPARED` | required | required | required | required | required |

After successful COMMIT-04:

- Run state moves to `SCENE_COMMITTED`;
- `active_checkpoint_manifest_path` is cleared;
- the checkpoint directory is deleted;
- failure to delete it produces a cleanup warning but does not roll back the adopted commit;
- startup quarantines a leftover checkpoint whose scene is already adopted.

---

## 10. Adopted `scene-manifest.json`

Canonical path:

```text
artifacts/scenes/v01/c001/s001/scene-manifest.json
```

All artifact paths in an adopted Scene manifest point to `artifacts/scenes/...`, never `runtime/checkpoints/...` or `.staging/...`.

### 10.1 Input plan reference

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `role` | enum `plan_ref_role` | yes | no | none | code | compatible with path |
| `path` | workspace-relative path | yes | no | none | code | adopted plan/handoff path |
| `sha256` | SHA-256 | yes | no | none | code | matches referenced canonical bytes |

### 10.2 Scene manifest

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `manifest_version` | string | yes | no | none | code | immutable | supported Scene-manifest Schema |
| `scene_id` | Scene ID | yes | no | none | code | immutable | matches directory and numeric fields |
| `commit_id` | Commit ID | yes | no | none | code | immutable | adopting Commit manifest |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | generation before scene commit |
| `adopted_generation_id` | Generation ID | yes | no | none | code | immutable | generation after scene commit |
| `volume_number` | integer | yes | no | none | code | immutable | `>=1`; matches scene ID |
| `chapter_number` | integer | yes | no | none | code | immutable | `>=1`; matches scene ID |
| `scene_number` | integer | yes | no | none | code | immutable | `>=1`; matches scene ID |
| `scene_card_path` | workspace-relative path | yes | no | none | code | immutable | exact adopted Scene-card path |
| `scene_card_sha256` | SHA-256 | yes | no | none | code | immutable | matches adopted Scene card |
| `prose_path` | workspace-relative path | yes | no | none | code | immutable | exact adopted prose path |
| `prose_sha256` | SHA-256 | yes | no | none | code | immutable | matches adopted prose |
| `continuity_delta_path` | workspace-relative path | yes | no | none | code | immutable | exact adopted committed-delta path |
| `continuity_delta_sha256` | SHA-256 | yes | no | none | code | immutable | matches committed delta |
| `character_count` | integer | yes | no | none | code | immutable | Unicode code points after canonicalization, excluding the single final LF |
| `evidence_ids` | array<Evidence ID> | yes | no | `[]` | code | immutable | unique, sorted; all created by this scene commit |
| `input_plan_refs` | array<Input plan reference> | yes | no | `[]` | code | immutable | unique by `(role,path)`; sorted by role then path |
| `adopted_at` | timestamp | yes | no | none | code | immutable | equals Commit `committed_at` |

---

## 11. Adopted `commit-manifest.json`

Canonical path:

```text
canon/generations/<after-generation>/commit-manifest.json
```

### 11.1 Local-key mapping

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `allocation_type` | enum `allocation_type` | yes | no | none | code | compatible with persistent ID prefix |
| `local_key` | string | yes | no | none | code from accepted candidate | candidate-local key |
| `persistent_id` | persistent ID | yes | no | none | code | allocated and adopted in this commit |

Mappings are unique by `(allocation_type,local_key)` and sorted by that pair.

### 11.2 Commit manifest

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `manifest_version` | string | yes | no | none | code | immutable | supported Commit-manifest Schema |
| `commit_id` | Commit ID | yes | no | none | code | immutable | unique; suffix equals `after_generation` |
| `commit_type` | enum `commit_type` | yes | no | none | code | immutable | `initial_design`, `scene`, or `volume_handoff` |
| `parent_commit_id` | Commit ID | yes | yes | `null` | code | immutable | null iff `commit_type=initial_design`; otherwise parent generation's Commit ID |
| `scene_id` | Scene ID | yes | yes | `null` | code | immutable | non-null iff `commit_type=scene` |
| `volume_handoff_path` | workspace-relative path | yes | yes | `null` | code | immutable | non-null iff `commit_type=volume_handoff`; exact adopted `artifacts/handoffs/vNN.json` path |
| `volume_handoff_sha256` | SHA-256 | yes | yes | `null` | code | immutable | null iff handoff path null; matches adopted handoff bytes |
| `before_generation` | Generation ID | yes | yes | `null` | code | immutable | null iff Genesis; otherwise parent generation |
| `after_generation` | Generation ID | yes | no | none | code | immutable | `00000000` for Genesis; otherwise newly reserved Commit suffix |
| `current_order` | integer | yes | no | none | code | immutable | equals resulting Story-clock order |
| `current_canon_sha256` | SHA-256 | yes | no | none | code | immutable | resulting generation root artifact |
| `knowledge_items_sha256` | SHA-256 | yes | no | none | code | immutable | resulting generation root artifact |
| `story_state_sha256` | SHA-256 | yes | no | none | code | immutable | resulting generation root artifact |
| `evidence_index_sha256` | SHA-256 | yes | no | none | code | immutable | resulting generation root artifact |
| `scene_card_sha256` | SHA-256 | yes | yes | `null` | code | immutable | non-null iff `commit_type=scene` |
| `prose_sha256` | SHA-256 | yes | yes | `null` | code | immutable | non-null iff `commit_type=scene` |
| `continuity_delta_sha256` | SHA-256 | yes | yes | `null` | code | immutable | non-null iff `commit_type=scene` |
| `scene_manifest_sha256` | SHA-256 | yes | yes | `null` | code | immutable | non-null iff `commit_type=scene` |
| `local_key_mappings` | array<Local-key mapping> | yes | no | `[]` | code | immutable | complete mapping for records created by this commit; empty for `volume_handoff` |
| `evidence_ids` | array<Evidence ID> | yes | no | `[]` | code | immutable | unique and sorted; empty for Genesis and `volume_handoff` |
| `created_at` | timestamp | yes | no | none | code | immutable | staging creation time |
| `committed_at` | timestamp | yes | no | none | code | immutable | adoption time; not earlier than created_at |

### 11.3 Commit-type condition matrix

| condition | `initial_design` | `scene` | `volume_handoff` |
|---|---|---|---|
| `parent_commit_id` | null | required | required |
| `scene_id` | null | required | null |
| `volume_handoff_path/hash` | null | null | required |
| `before_generation` | null | required | required |
| Scene hashes | all null | all required | all null |
| local-key mappings | complete Genesis mappings | complete scene-created mappings | empty |
| Evidence IDs | empty | complete scene-created Evidence set | empty |
| `current_order` relation | `0` | parent + 1 | equals parent |

For `volume_handoff`:

```text
current_canon_sha256 = parent current_canon_sha256
knowledge_items_sha256 = parent knowledge_items_sha256
evidence_index_sha256 = parent evidence_index_sha256
story_state_sha256 may differ only because thread_states[].volume_disposition changed
```

### 11.4 Genesis constants

```text
commit_id = commit-00000000
commit_type = initial_design
parent_commit_id = null
scene_id = null
volume_handoff_path = null
volume_handoff_sha256 = null
before_generation = null
after_generation = 00000000
current_order = 0
scene_card_sha256 = null
prose_sha256 = null
continuity_delta_sha256 = null
scene_manifest_sha256 = null
evidence_ids = []
```

---

## 12. Adopted `generation-manifest.json`

Canonical path:

```text
canon/generations/<generation-id>/generation-manifest.json
```

### 12.1 Generation manifest

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `manifest_version` | string | yes | no | none | code | immutable | supported Generation-manifest Schema |
| `generation_id` | Generation ID | yes | no | none | code | immutable | matches directory |
| `commit_id` | Commit ID | yes | no | none | code | immutable | suffix equals generation ID |
| `parent_generation_id` | Generation ID | yes | yes | `null` | code | immutable | null iff Genesis |
| `current_order` | integer | yes | no | none | code | immutable | equals resulting Story clock |
| `created_at` | timestamp | yes | no | none | code | immutable | equals adopting Commit `committed_at` |
| `current_canon_path` | workspace-relative path | yes | no | none | code | immutable | own generation `current-canon.json` |
| `current_canon_sha256` | SHA-256 | yes | no | none | code | immutable | matches file |
| `knowledge_items_path` | workspace-relative path | yes | no | none | code | immutable | own generation `knowledge-items.json` |
| `knowledge_items_sha256` | SHA-256 | yes | no | none | code | immutable | matches file |
| `story_state_path` | workspace-relative path | yes | no | none | code | immutable | own generation `story-state.json` |
| `story_state_sha256` | SHA-256 | yes | no | none | code | immutable | matches file |
| `evidence_index_path` | workspace-relative path | yes | no | none | code | immutable | own generation `evidence-index.json` |
| `evidence_index_sha256` | SHA-256 | yes | no | none | code | immutable | matches file |
| `commit_manifest_path` | workspace-relative path | yes | no | none | code | immutable | own generation `commit-manifest.json` |
| `commit_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | matches file |
| `source_scene_id` | Scene ID | yes | yes | `null` | code | immutable | non-null iff adopting Commit type is `scene` |
| `source_scene_manifest_path` | workspace-relative path | yes | yes | `null` | code | immutable | non-null iff Scene source ID is non-null; adopted artifact path |
| `source_scene_manifest_sha256` | SHA-256 | yes | yes | `null` | code | immutable | null iff Scene-manifest path null; matches file |
| `source_volume_handoff_path` | workspace-relative path | yes | yes | `null` | code | immutable | non-null iff adopting Commit type is `volume_handoff`; adopted `artifacts/handoffs/vNN.json` path |
| `source_volume_handoff_sha256` | SHA-256 | yes | yes | `null` | code | immutable | null iff Handoff path null; matches file |

The Generation manifest does not hash itself.

### 12.2 Source condition matrix

| adopting Commit type | Scene source fields | Volume-handoff source fields |
|---|---|---|
| `initial_design` | all null | all null |
| `scene` | all required | all null |
| `volume_handoff` | all null | both required |

Exactly one source branch is active for a non-Genesis generation.

### 12.3 Manifest creation order

To avoid cyclic hashes:

#### Genesis

1. build Canon/Knowledge/State/Evidence files;
2. build Commit manifest;
3. build Generation manifest.

#### Scene commit

1. build Canon/Knowledge/State/Evidence files;
2. build adopted-form Scene files and Scene manifest;
3. build Commit manifest, including Scene-manifest hash;
4. build Generation manifest, including Commit-manifest and Scene-manifest hashes.

#### Volume-handoff commit

1. build the adopted-form Handoff artifact and resulting generation root files;
2. build Commit manifest, including Handoff path/hash;
3. build Generation manifest, including Commit-manifest and Handoff path/hash.

The Scene manifest identifies the Commit and generations but does not contain Commit- or Generation-manifest hashes. The Volume-handoff artifact identifies its Commit and adopted generation according to the Handoff data contract but does not contain manifest hashes that would create a cycle.

### 12.4 Adopted Volume-handoff identity

Canonical path:

```text
artifacts/handoffs/vNN.json
```

Runtime considers a Handoff adopted only when all are true:

```text
the Handoff artifact exists and validates
its commit_id and adopted_generation_id match a volume_handoff Commit/Generation
the Generation manifest source_volume_handoff_path/hash match it
the generation is reachable from valid canon/HEAD
```

A standalone Handoff file that is not referenced by a HEAD-reachable Handoff generation is an orphan and is not a planning authority.

---

## 13. `canon/HEAD`

`canon/HEAD` is a plain UTF-8 text pointer containing:

```text
<generation-id>\n
```

Rules:

- exactly one Generation ID and one LF;
- no spaces or additional lines;
- target directory and Generation manifest must exist and validate;
- Run state `current_head_generation` must match;
- updated only after all artifacts required by the adopting Commit type are durable at final paths:
  - Genesis: generation and `canon/initial-design.json`;
  - Scene commit: generation and adopted Scene directory;
  - Volume-handoff commit: generation and adopted Handoff artifact.

HEAD is the final atomic adoption step of Genesis, COMMIT-04, and VH-ID. A valid changed HEAD is authoritative even when a crash prevented the later Run-state update or cleanup.

---

## 14. Adopted `publication-manifest.json`

Canonical path:

```text
publications/<publication-id>/publication-manifest.json
```

The manifest stores paths relative to the adopted publication root. It never stores `.staging/...` paths, so its references remain valid after directory rename.

### 14.1 Publication file reference

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `role` | enum `publication_file_role` | yes | no | none | code | compatible with relative path |
| `relative_path` | relative path inside publication root | yes | no | none | code | no escape; not `publication-manifest.json` |
| `sha256` | SHA-256 | yes | no | none | code | matches adopted file |
| `size_bytes` | integer | yes | no | none | code | exact byte length; `>=0` |
| `media_type` | string | yes | no | none | code | NFC nonempty MIME type |

File references are unique and sorted by `relative_path`.

### 14.2 Publication manifest

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `manifest_version` | string | yes | no | none | code | immutable | supported Publication-manifest Schema |
| `publication_id` | Publication ID | yes | no | none | code | immutable | matches adopted directory |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | adopted source generation |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | source Generation-manifest hash |
| `files` | array<Publication file reference> | yes | no | `[]` | code | immutable | complete adopted file set except manifest itself |
| `content_set_sha256` | SHA-256 | yes | no | none | code | immutable | hash of canonical sorted `(relative_path,sha256,size_bytes,media_type,role)` records |
| `validation_relative_path` | relative publication path | yes | no | `publication-validation.json` | code | immutable | listed with role `validation` |
| `validation_sha256` | SHA-256 | yes | no | none | code | immutable | matches validation file |
| `completion_audit_relative_path` | relative publication path | yes | no | `reports/completion-audit.json` | code | immutable | sanitized report listed with role `report` |
| `completion_audit_sha256` | SHA-256 | yes | no | none | code | immutable | matches sanitized report |
| `current_pointer_before` | Publication ID | yes | yes | `null` | code | immutable | exact prior `output/CURRENT`, or null |
| `current_pointer_after` | Publication ID | yes | no | none | code | immutable | equals `publication_id` |
| `created_at` | timestamp | yes | no | none | code | immutable | OUT-02 final-manifest creation time before Gate evaluation |

The sanitized completion report must not contain author truth, resolution-condition secrets, raw prompts, raw responses, secret configuration, or internal workspace paths.

---

## 15. `output/CURRENT`

`output/CURRENT` is a plain UTF-8 text pointer containing:

```text
<publication-id>\n
```

Rules:

- exactly one Publication ID and one LF;
- target publication directory and manifest must exist and validate;
- Run state `current_publication_id` must match;
- updated by atomic replacement only after publication staging is validated, COMP-PUBLISH succeeds, and the publication directory is renamed into `publications/`.

---

## 16. Publication transaction

OUT-01 through OUT-03 use:

```text
.staging/publication/<publication-id>/
```

Transaction:

1. OUT-01 creates deterministic manuscript, metadata, safe reports, and `publication-build-manifest.json`.
2. OUT-02 validates every file and profile constraint, writes `publication-validation.json`, constructs the final relative-path `publication-manifest.json`, verifies `content_set_sha256`, and removes the provisional build manifest.
3. COMP-PUBLISH writes a Gate result outside publication content and performs no adoption or file mutation.
4. OUT-03 revalidates the passing Gate and unchanged staging, `fsync`s staging, atomically renames it to `publications/<publication-id>`, then atomically replaces `output/CURRENT`.
5. Run state records the adopted publication.
6. A failure after directory rename but before CURRENT replacement leaves an unadopted publication directory. Startup does not publish it by inference; it quarantines it unless explicit OUT-03 recovery revalidates the original passing Gate.

The adopted Publication manifest contains no staging path, candidate path, private Completion-audit path, or provisional build-manifest reference. Its creation timestamp is the OUT-02 finalization time; publication adoption time is recorded by the OUT-03 operation audit and Run-state `updated_at`.

---

## 17. Generation adoption transactions

### 17.1 Scene commit transaction

Staging root:

```text
.staging/scene-commits/<scene-id>/
  transaction-manifest.json
  merge-plan.json
  transaction-validation.json
  generation/<generation-id>/
  scene/
```

COMMIT-04 adoption order:

1. validate the complete staged generation and Scene artifact;
2. `fsync` staged files and directories;
3. atomically rename the generation directory to `canon/generations/<generation-id>`;
4. atomically rename the Scene directory to `artifacts/scenes/vNN/cNNN/sNNN`;
5. revalidate both adopted directories;
6. atomically replace `canon/HEAD`;
7. replace Run state with the derived next-Scene/Chapter/Handoff route and clear active candidate/checkpoint references;
8. increment `successful_scene_commits` exactly once;
9. remove the checkpoint and remaining staging.

A crash:

- before adopted rename leaves abandoned staging;
- after one or both adopted renames but before HEAD leaves HEAD-unreachable orphan content;
- after HEAD replacement means the commit is adopted even if Run-state or checkpoint cleanup is incomplete.

### 17.2 Volume-handoff commit transaction

Staging root:

```text
.staging/handoffs/vNN/<run-id>/
  handoff.json
  handoff-validation.json
  generation/<generation-id>/
```

VH-ID adoption order:

1. validate the ready Handoff candidate, Review/residual records, resulting generation, and Handoff Commit/Generation manifests;
2. verify that only `thread_states[].volume_disposition` differs in Story state and that Story-clock/current order are unchanged;
3. `fsync` staged files and directories;
4. atomically rename the generation directory to `canon/generations/<generation-id>`;
5. atomically place the Handoff artifact at `artifacts/handoffs/vNN.json`;
6. revalidate both adopted artifacts;
7. atomically replace `canon/HEAD`;
8. update Run state to the next Volume or COMP-PRE route;
9. leave `successful_scene_commits` unchanged;
10. remove staging and clear the active Handoff Candidate manifest path.

A crash:

- before HEAD leaves the generation and/or Handoff as unadopted orphan content;
- after HEAD means the Handoff commit is adopted and Run state must be reconciled;
- a standalone Handoff file is never promoted by inference.

For both transaction types, startup reconciles Run state only from a valid HEAD-reachable Commit/Generation chain and the exact conditional source artifact.

---

## 18. Orphan quarantine and `orphan-manifest.json`

Potential orphan content is moved under:

```text
runtime/orphans/<timestamp>/
```

### 18.1 Orphan item

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `reason` | enum `orphan_reason` | yes | no | none | code | exact reason |
| `original_path` | workspace-relative path | yes | no | none | code | discovered path |
| `quarantined_path` | workspace-relative path | yes | no | none | code | path under this orphan directory |
| `related_generation_id` | Generation ID | yes | yes | `null` | code | null or detected ID |
| `related_scene_id` | Scene ID | yes | yes | `null` | code | null or detected ID |
| `related_volume_number` | integer | yes | yes | `null` | code | null or detected Handoff Volume number `>=1` |
| `related_publication_id` | Publication ID | yes | yes | `null` | code | null or detected ID |
| `sha256` | SHA-256 | yes | yes | `null` | code | file hash for file; null for directory aggregate unless calculated |

### 18.2 Orphan manifest

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `manifest_version` | string | yes | no | none | code | supported Schema |
| `discovered_at` | timestamp | yes | no | none | code | UTC |
| `head_generation_at_discovery` | Generation ID | yes | yes | `null` | code | exact valid HEAD or null when HEAD invalid |
| `current_publication_at_discovery` | Publication ID | yes | yes | `null` | code | exact valid CURRENT or null |
| `items` | array<Orphan item> | yes | no | `[]` | code | unique original paths; sorted by original path |
| `cleanup_permitted` | boolean | yes | no | `false` | code | true only after all items are proven unreferenced by valid adopted pointers |

Valid HEAD-reachable generations and their referenced adopted Scene or Volume-handoff artifacts are never quarantined or deleted.

---

## 19. LLM audit call ID and filename

Before each provider call, code allocates one Call ID and persists all budget usage resulting from that call.

Canonical audit path:

```text
audit/llm-calls/
  <sequence>__<operation-id>__<target-id>__<role>__attempt-<NN>[__round-<NN>].json.gz
```

Examples:

```text
000123__prose-01__v01-c003-s002__generate__attempt-02.json.gz
000124__prose-02__v01-c003-s002__review__attempt-01.json.gz
000125__prose-rev__v01-c003-s002__revise__attempt-01__round-01.json.gz
```

Rules:

- `<sequence>` is the zero-padded numeric suffix of the allocated Call ID, using at least six digits.
- `operation-id` is lowercased Stage ID.
- `target-id` is lowercased and path-safe.
- `role` is enum `audit_call_role`.
- `attempt` is one-based within the operation/round.
- `round` is present only for revise calls.
- Every filename is unique and never overwritten.
- Code-only operation logs are stored separately from `audit/llm-calls/`.
- The audit payload contract is defined by the Review/Audit data contract, not by this manifest contract.

---

## 20. Resume compatibility

Before resume, code validates:

```text
Run manifest Schema
Run-state Schema
workspace lock
input source hash
state_version
workspace_version
code_version
prompt_bundle_version
schema_bundle_version
pricing_table_version
provider
base_url
model
thinking
stream
temperature
top_p
seed
structured_output_mode
editorial_profile_id
publishing_profile_id
immutable_config_fingerprint
HEAD and CURRENT pointers
all referenced candidate/checkpoint manifests
counters greater than all observed IDs
```

Only config changes explicitly permitted by `configuration_contracts.md` may change `runtime/effective-config.json`. After a permitted change:

1. write an audit record;
2. atomically replace effective config;
3. update Run-state `effective_config_sha256`;
4. do not alter Run manifest or immutable fingerprint.

A version or immutable-config mismatch is a mechanical stop. Version migration is outside normal resume.

---

## 21. Startup reconciliation

Under the workspace lock, startup performs:

1. validate Run manifest, Run state, Effective config, and counters;
2. validate `canon/HEAD` when present;
3. validate the HEAD Generation and Commit manifests, root hashes, and commit-type condition matrix;
4. validate the exact HEAD source branch:
   - no source artifact for Genesis;
   - adopted Scene manifest for a Scene commit;
   - adopted Volume-handoff artifact for a Handoff commit;
5. validate `output/CURRENT` when present;
6. reconcile Run-state HEAD, last Commit, Scene count, target route, and publication fields when an adoption completed before a crash;
7. scan `.staging/`, generation directories, Scene artifacts, Handoff artifacts, publication directories, leftover checkpoints, and partial candidate version directories;
8. quarantine content not reachable from valid adopted pointers or valid resume manifests;
9. validate the exact Candidate/Checkpoint manifest selected for resume, including Context-snapshot and source hashes;
10. set `run_status=running` only after all compatibility checks pass.

Startup never promotes orphan content by modification time, directory order, parse success, or semantic plausibility.

---

## 22. Cross-manifest invariants

A valid workspace satisfies all common invariants:

```text
HEAD generation directory exists
HEAD Generation manifest validates
Generation commit_id suffix equals generation_id
Generation Commit manifest exists and hashes correctly
Commit after_generation equals generation_id
Commit root hashes equal Generation root hashes
Generation current_order equals Story-clock current_order
Run-state HEAD equals canon/HEAD
Run-state last_commit_id equals HEAD Commit ID
successful_scene_commits equals HEAD Story-clock current_order
no adopted manifest contains a staging or checkpoint path
all next_* counters exceed every observed allocated ID
```

Commit-type branch invariants:

### 22.1 Initial-design generation

```text
parent generation and parent Commit are null
Scene source fields are null
Volume-handoff source fields are null
current_order = 0
```

### 22.2 Scene generation

```text
parent generation and Commit exist
Generation source Scene manifest exists and hashes
Commit and Generation Scene source fields agree
Scene manifest adopted_generation_id equals Generation ID
Scene manifest source_generation_id equals Generation parent
Scene artifact paths are adopted artifact paths
Scene artifact hashes match files
Commit Scene hashes equal Scene manifest hashes
Commit evidence_ids exist in resulting Evidence index
Commit local-key mappings match adopted new records
current_order = parent current_order + 1
```

### 22.3 Volume-handoff generation

```text
parent generation and Commit exist
Generation source Handoff artifact exists and hashes
Commit and Generation Handoff path/hash agree
Handoff commit_id and adopted_generation_id match manifests
Scene source fields and Scene hashes are null
local-key mappings and Evidence IDs are empty
current_order = parent current_order
current Canon hash equals parent
Knowledge-items hash equals parent
Evidence-index hash equals parent
Story-state difference is limited to thread_states[].volume_disposition
successful_scene_commits remains equal to unchanged current_order
```

### 22.4 Publication invariants

```text
CURRENT publication directory and manifest exist when CURRENT is present
Publication source generation exists and validates
Run-state publication equals output/CURRENT
Publication manifest contains only publication-root-relative file paths
Publication content set excludes provisional build manifest
```

---

## 23. Forbidden runtime content

The following are forbidden in saved runtime manifests and pointers:

```text
API keys
Authorization headers
OS environment dumps
secret configuration
raw prompt or raw response
author truth outside approved Canon/Context artifacts
absolute paths
parent-directory traversal
symlink-escaped paths
unresolved candidate local keys in adopted manifests
placeholder hashes
multiple artifact classes in one field such as "adopted/audit"
checkpoint paths in adopted Scene manifests
staging paths in adopted Publication manifests
```

---

## 24. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
canonical JSON and text hash stability
atomic mutable-runtime replacement
single-writer lock enforcement
Run-manifest immutability
resume compatibility rejection
permitted resume config update
Run-status transition matrix
Run-state revision monotonicity
allocation counter persistence before use
ID gap acceptance and reuse rejection
counter corruption detection
versioned operation-specific candidate directories
fixed review.json per candidate version
candidate-manifest-only resume
Context-snapshot hash/source mismatch rejection
candidate artifact/hash mismatch rejection
candidate version-directory consistency
checkpoint phase conditions
Commit-plan checkpoint fields
checkpoint cleanup after Scene adoption
adopted Scene manifest contains artifact paths only
Scene character-count calculation
Commit/Generation hash graph without cycles
Genesis Commit constants
scene Commit conditional fields
volume_handoff Commit conditional fields
Handoff Generation source fields
Handoff-only volume_disposition mutation
Handoff current-order preservation
successful Scene count preservation across Handoff commit
HEAD atomic replacement last for Genesis, Scene, and Handoff adoption
crash before and after HEAD behavior for Scene and Handoff
Run-state reconciliation after adopted Scene/Handoff commit
orphan Handoff detection and quarantine
Publication manifest contains no staging/private/provisional path
publication validation and Gate order
Publication manifest finalization before Gate
CURRENT atomic replacement
unadopted publication quarantine
audit filename uniqueness
cross-manifest branch invariant validation
unknown-field rejection
secret and absolute-path rejection
placeholder-hash rejection
```
