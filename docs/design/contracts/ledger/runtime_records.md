# Ledger contracts: runtime records

`runtime_state` is program execution data, distinct from `current_canon`, `knowledge_items`, and `story_state`. Every persisted record rejects unknown fields.

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

`candidate-manifest.json` is the only resume source for a candidate directory. It names the retained structurally valid candidate and its next stage.

## Run state

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `run_id` | string | yes | no | none | code | immutable | unique run | `runtime/run-state.json` |
| `current_stage` | stage ID | yes | no | none | code | mutable | known stage | `runtime/run-state.json` |
| `current_target_id` | string | yes | yes | null | code | mutable | stage target | `runtime/run-state.json` |
| `current_volume_number` | integer | yes | yes | null | code | mutable | positive if set | `runtime/run-state.json` |
| `current_chapter_number` | integer | yes | yes | null | code | mutable | positive if set | `runtime/run-state.json` |
| `current_scene_number` | integer | yes | yes | null | code | mutable | positive if set | `runtime/run-state.json` |
| `scene_phase` | scene-phase enum | yes | yes | null | code | mutable | compatible with stage | `runtime/run-state.json` |
| `last_valid_candidate_ref` | relative path | yes | yes | null | code | mutable | named manifest exists | `runtime/run-state.json` |
| `last_valid_review_ref` | relative path | yes | yes | null | code | mutable | named manifest exists | `runtime/run-state.json` |
| `last_checkpoint_ref` | relative path | yes | yes | null | code | mutable | checkpoint exists | `runtime/run-state.json` |
| `next_stage` | stage ID | yes | no | none | code | mutable | known stage | `runtime/run-state.json` |
| `stop_reason` | string | yes | yes | null | code | mutable | sanitized | `runtime/run-state.json` |
| `completed` | boolean | yes | no | false | code | mutable | true only after OUT-03 | `runtime/run-state.json` |
| `current_head_generation` | generation ID | yes | yes | null | code | mutable | equals HEAD | `runtime/run-state.json` |
| `current_publication_id` | publication ID | yes | yes | null | code | mutable | adopted publication if set | `runtime/run-state.json` |
| `updated_at` | RFC3339 timestamp | yes | no | none | code | mutable | UTC | `runtime/run-state.json` |

## Manifest field sets

Each named manifest stores all fields in its named field table below; no arbitrary map is permitted.

| manifest | fields |
|---|---|
| `run-manifest.json` | `run_id`, `started_at`, `brief_hash`, `effective_config_hash`, `workspace_version`, `created_by` |
| `counters.json` | `next_character_id`, `next_relationship_id`, `next_location_id`, `next_organization_id`, `next_item_id`, `next_system_id`, `next_culture_id`, `next_history_id`, `next_supporting_thread_id`, `next_knowledge_id`, `next_evidence_id`, `next_commit_id`, `next_generation_id`, `next_publication_id`, `next_audit_sequence` |
| `candidate-manifest.json` | `operation_id`, `target_id`, `candidate_path`, `candidate_sha256`, `review_path`, `review_sha256`, `revision_rounds_used`, `transport_retries_used`, `response_structure_retries_used`, `completion_audit_attempts_used`, `last_structurally_valid`, `next_stage`, `created_at`, `updated_at` |
| `checkpoint-manifest.json` | `scene_id`, `phase`, `scene_card_path`, `scene_card_sha256`, `prose_path`, `prose_sha256`, `continuity_delta_path`, `continuity_delta_sha256`, `revision_rounds_used`, `transport_retries_used`, `response_structure_retries_used`, `created_at`, `updated_at` |
| `scene-manifest.json` | `scene_id`, `commit_id`, `volume_number`, `chapter_number`, `scene_number`, `scene_card_path`, `scene_card_sha256`, `prose_path`, `prose_sha256`, `continuity_delta_path`, `continuity_delta_sha256`, `character_count`, `evidence_ids`, `input_plan_refs`, `adopted_at` |
| `commit-manifest.json` | `commit_id`, `commit_type`, `parent_commit_id`, `scene_id`, `before_generation`, `after_generation`, `current_canon_sha256`, `story_state_sha256`, `knowledge_items_sha256`, `evidence_index_sha256`, `scene_card_sha256`, `prose_sha256`, `continuity_delta_sha256`, `local_key_mappings`, `created_at`, `committed_at` |
| `generation-manifest.json` | `generation_id`, `commit_id`, `parent_generation_id`, `current_canon_sha256`, `story_state_sha256`, `knowledge_items_sha256`, `evidence_index_sha256`, `scene_card_sha256`, `prose_sha256`, `continuity_delta_sha256` |
| `publication-manifest.json` | `publication_id`, `source_generation`, `publication_staging_path`, `validation_path`, `completion_audit_path`, `adopted_at`, `current_pointer_before`, `current_pointer_after` |

`local_key_mappings` is an array of rows with `record_type`, `local_key`, and `persistent_id`. Fixed hash fields are SHA-256 over the canonical artifact bytes, or null only when the named artifact does not exist.

## Completion audit loop

COMP-AUDIT writes `attempt-01.json`, then later attempts with incremented two-digit suffixes. A structurally valid attempt advances directly to COMP-SAVE. A decode failure, empty string, whitespace-only response, JSON failure, Schema failure, missing required field, or enum failure consumes response-structure retry first; a separate exhausted completion attempt increments `completion_audit_attempts_used` and reruns COMP-AUDIT with the unchanged COMP-PRE input. If attempts are exhausted with no structurally valid result, code performs a mechanical stop. Completion audit never revises prose, Canon, knowledge, or story state.
