# Ledger contracts: runtime records

`runtime_state` is execution state; it is distinct from `current_canon`, `knowledge_items`, and `story_state`. Every saved record has `additionalProperties: false`, canonical UTF-8/NFC/LF serialization, sorted keys, compact separators, and one trailing LF.

## Candidate layout and resume

```text
runtime/candidates/<target>/
  candidate.json
  review.json
  candidate-manifest.json
runtime/candidates/scenes/v01/c001/s001/
  candidate.md
  review.json
  candidate-manifest.json
runtime/candidates/completion/
  attempt-01.json
  attempt-02.json
  candidate-manifest.json
```

Every candidate, review, and revision stage resumes **only** from its directory's `candidate-manifest.json`. Candidate content, review content, scene cards, prose, and continuity deltas are never resume authorities.

## Common field-table columns

Every table uses `field | type | required | nullable | default | creator | mutability | validation | source of truth`. Saved fields not listed are rejected.

## run-manifest.json

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `run_id` | string | yes | no | none | code | immutable | unique run ID | run manifest |
| `started_at` | RFC3339 timestamp | yes | no | none | code | immutable | UTC | run manifest |
| `brief_hash` | SHA-256 | yes | no | none | code | immutable | canonical brief bytes | run manifest |
| `effective_config_hash` | SHA-256 | yes | no | none | code | immutable | redacted config bytes | run manifest |
| `workspace_version` | string | yes | no | none | code | immutable | supported version | run manifest |
| `created_by` | string | yes | no | `storycraft` | code | immutable | nonempty | run manifest |

## run-state.json

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `run_id` | string | yes | no | none | code | immutable | run manifest match | run state |
| `current_stage` | stage ID | yes | no | none | code | mutable | known stage | run state |
| `current_target_id` | string | yes | yes | null | code | mutable | stage target | run state |
| `current_volume_number` | integer | yes | yes | null | code | mutable | positive when set | run state |
| `current_chapter_number` | integer | yes | yes | null | code | mutable | positive when set | run state |
| `current_scene_number` | integer | yes | yes | null | code | mutable | positive when set | run state |
| `scene_phase` | scene phase | yes | yes | null | code | mutable | stage-compatible | run state |
| `last_valid_candidate_ref` | relative path | yes | yes | null | code | mutable | manifest-named file | run state |
| `last_valid_review_ref` | relative path | yes | yes | null | code | mutable | manifest-named file | run state |
| `last_checkpoint_ref` | relative path | yes | yes | null | code | mutable | checkpoint exists | run state |
| `next_stage` | stage ID | yes | no | none | code | mutable | known stage | run state |
| `stop_reason` | string | yes | yes | null | code | mutable | sanitized | run state |
| `completed` | boolean | yes | no | false | code | mutable | true only after OUT-03 | run state |
| `current_head_generation` | generation ID | yes | yes | null | code | mutable | HEAD match | run state |
| `current_publication_id` | publication ID | yes | yes | null | code | mutable | adopted publication | run state |
| `updated_at` | RFC3339 timestamp | yes | no | none | code | mutable | UTC | run state |

## counters.json

All fields are required, non-null integers created and mutated by code, default `0`, validated `>=0`, and sourced from `counters.json`: `next_call_id`, `next_commit_id`, `next_publication_id`, `next_character_id`, `next_relationship_id`, `next_location_id`, `next_organization_id`, `next_item_id`, `next_system_id`, `next_culture_id`, `next_history_id`, `next_rule_id`, `next_thread_id`, `next_ending_id`, `next_fact_id`, `next_evidence_id`, `transport_retries_used`, `response_structure_retries_used`, `revision_rounds_used`, `completion_audit_attempts_used`, `input_tokens_used`, `output_tokens_used`, `estimated_cost_used`, `active_elapsed_seconds`.

## candidate-manifest.json

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `operation_id` | stage operation ID | yes | no | none | code | immutable | known operation | candidate manifest |
| `target_id` | target ID | yes | no | none | code | immutable | operation target | candidate manifest |
| `candidate_path` | relative path | yes | no | none | code | mutable | candidate file exists | candidate manifest |
| `candidate_sha256` | SHA-256 | yes | no | none | code | mutable | candidate bytes | candidate manifest |
| `review_path` | relative path | yes | yes | null | code | mutable | review exists when set | candidate manifest |
| `review_sha256` | SHA-256 | yes | yes | null | code | mutable | review bytes when set | candidate manifest |
| `revision_rounds_used` | integer | yes | no | 0 | code | mutable | `0..max_revision_rounds` | candidate manifest |
| `transport_retries_used` | integer | yes | no | 0 | code | mutable | configured bound | candidate manifest |
| `response_structure_retries_used` | integer | yes | no | 0 | code | mutable | configured bound | candidate manifest |
| `completion_audit_attempt` | integer | yes | yes | null | code | mutable | null outside completion; positive in completion | candidate manifest |
| `last_structurally_valid` | boolean | yes | no | false | code | mutable | candidate validation result | candidate manifest |
| `next_stage` | stage ID | yes | no | none | code | mutable | transition table | candidate manifest |
| `created_at` | RFC3339 timestamp | yes | no | none | code | immutable | UTC | candidate manifest |
| `updated_at` | RFC3339 timestamp | yes | no | none | code | mutable | UTC | candidate manifest |

## checkpoint, scene, commit, generation, and publication manifests

Each field below is required unless marked nullable; creator is code; fixed identifiers and hashes are immutable; timestamps and paths validate as RFC3339 and workspace-relative paths.

| manifest | exact fields |
|---|---|
| `checkpoint-manifest.json` | `scene_id`, `phase`, `scene_card_path`, `scene_card_sha256`, `prose_path`, `prose_sha256`, `continuity_delta_path`, `continuity_delta_sha256`, `revision_rounds_used`, `transport_retries_used`, `response_structure_retries_used`, `created_at`, `updated_at` |
| `scene-manifest.json` | `scene_id`, `commit_id`, `volume_number`, `chapter_number`, `scene_number`, `scene_card_path`, `scene_card_sha256`, `prose_path`, `prose_sha256`, `continuity_delta_path`, `continuity_delta_sha256`, `character_count`, `evidence_ids`, `input_plan_refs`, `adopted_at` |
| `commit-manifest.json` | `commit_id`, `commit_type`, `parent_commit_id`, `scene_id`, `before_generation`, `after_generation`, `current_canon_sha256`, `story_state_sha256`, `knowledge_items_sha256`, `evidence_index_sha256`, `scene_card_sha256`, `prose_sha256`, `continuity_delta_sha256`, `local_key_mappings`, `created_at`, `committed_at` |
| `generation-manifest.json` | `generation_id`, `commit_id`, `parent_generation_id`, `current_canon_sha256`, `story_state_sha256`, `knowledge_items_sha256`, `evidence_index_sha256`, `scene_card_sha256`, `prose_sha256`, `continuity_delta_sha256` |
| `publication-manifest.json` | `publication_id`, `source_generation`, `publication_staging_path`, `validation_path`, `completion_audit_path`, `adopted_at`, `current_pointer_before`, `current_pointer_after` |

## Completion audit loop

COMP-AUDIT saves each response at `runtime/candidates/completion/attempt-NN.json`. Structure failure consumes `response_structure_retries_used` inside the same attempt. When that retry budget is exhausted and an audit attempt remains, code increments `completion_audit_attempts_used`, creates the next `attempt-NN.json`, and reruns with the unchanged COMP-PRE input. A structurally valid attempt advances to COMP-SAVE. Exhaustion without any valid attempt is a mechanical stop. Completion audit neither revises content nor authorizes publication by itself.
