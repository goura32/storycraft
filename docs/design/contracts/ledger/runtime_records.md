# Ledger contracts: runtime records

`runtime_state` is `runtime/run-state.json` plus candidate/checkpoint manifests and counters. It is distinct from current_canon, knowledge_items, and story_state. All saved records reject unknown fields.

## Run state

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| run_id | string | yes | no | none | code | immutable | unique run | run-state |
| current_stage | stage ID | yes | no | none | code | mutable | known stage | run-state |
| current_target_id | string | yes | yes | null | code | mutable | matches stage | run-state |
| current_volume_number | integer | yes | yes | null | code | mutable | positive if set | run-state |
| current_chapter_number | integer | yes | yes | null | code | mutable | positive if set | run-state |
| current_scene_number | integer | yes | yes | null | code | mutable | positive if set | run-state |
| scene_phase | scene phase enum | yes | yes | null | code | mutable | phase/stage compatible | run-state |
| last_valid_candidate_ref | path/hash reference | yes | yes | null | code | mutable | candidate manifest exists | run-state |
| last_valid_review_ref | path/hash reference | yes | yes | null | code | mutable | candidate manifest exists | run-state |
| last_checkpoint_ref | path/hash reference | yes | yes | null | code | mutable | checkpoint exists | run-state |
| next_stage | stage ID | yes | no | none | code | mutable | known stage | run-state |
| stop_reason | string | yes | yes | null | code | mutable | sanitized | run-state |
| completed | boolean | yes | no | false | code | mutable | true iff OUT-03 | run-state |
| current_head_generation | generation ID | yes | yes | null | code | mutable | HEAD equals value | run-state |
| current_publication_id | publication ID | yes | yes | null | code | mutable | published exists | run-state |
| updated_at | RFC3339 timestamp | yes | no | none | code | mutable | UTC | run-state |

## Candidate manifest

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| operation_id | string | yes | no | none | code | immutable | unique operation | candidate manifest |
| target_id | string | yes | no | none | code | immutable | stage target | candidate manifest |
| candidate_path | relative path | yes | no | none | code | mutable | under runtime/candidates | candidate manifest |
| candidate_sha256 | SHA-256 string | yes | yes | null | code | mutable | matches candidate iff present | candidate manifest |
| review_path | relative path | yes | yes | null | code | mutable | under runtime/candidates | candidate manifest |
| review_sha256 | SHA-256 string | yes | yes | null | code | mutable | matches review iff present | candidate manifest |
| revision_rounds_used | integer | yes | no | 0 | code | mutable | >=0 | candidate manifest |
| transport_retries_used | integer | yes | no | 0 | code | mutable | >=0 | candidate manifest |
| response_structure_retries_used | integer | yes | no | 0 | code | mutable | >=0 | candidate manifest |
| last_structurally_valid | boolean | yes | no | false | code | mutable | true iff hash/schema valid | candidate manifest |
| next_stage | stage ID | yes | no | none | code | mutable | known stage | candidate manifest |
| created_at | RFC3339 timestamp | yes | no | none | code | immutable | UTC | candidate manifest |
| updated_at | RFC3339 timestamp | yes | no | none | code | mutable | UTC | candidate manifest |

## Fixed artifact hashes

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| current_canon_sha256 | SHA-256 string | yes | yes | null | code | immutable | canonical bytes if present | manifest |
| story_state_sha256 | SHA-256 string | yes | yes | null | code | immutable | canonical bytes if present | manifest |
| knowledge_items_sha256 | SHA-256 string | yes | yes | null | code | immutable | canonical bytes if present | manifest |
| evidence_index_sha256 | SHA-256 string | yes | yes | null | code | immutable | canonical bytes if present | manifest |
| scene_card_sha256 | SHA-256 string | yes | yes | null | code | immutable | canonical bytes if present | manifest |
| prose_sha256 | SHA-256 string | yes | yes | null | code | immutable | NFC bytes if present | manifest |
| continuity_delta_sha256 | SHA-256 string | yes | yes | null | code | immutable | canonical bytes if present | manifest |

## Local key mapping row

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| record_type | record type enum | yes | no | none | code | immutable | known type | local key mapping |
| local_key | string | yes | no | none | code | immutable | unique type+key | local key mapping |
| persistent_id | record ID | yes | no | none | code | immutable | allocated known ID | local key mapping |


## Resume

For every stage, a candidate manifest with `last_structurally_valid=true` resumes from its `next_stage`; a review manifest obeys its `next_stage`. Corrupt candidates are discarded and regenerated from the named prior adopted artifact. Audit raw logs are never resume input.
