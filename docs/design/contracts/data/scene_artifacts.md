# Data contracts: scene artifacts

All persisted records reject unknown fields. Code sets scene coordinates and `scene_id`; the LLM does not generate them.

## Scene card

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `scene_id` | scene ID | yes | no | none | code | immutable | `vNN-cNNN-sNNN` | scene card |
| `volume_number` | integer | yes | no | none | code | immutable | target run state | scene card |
| `chapter_number` | integer | yes | no | none | code | immutable | target run state | scene card |
| `scene_number` | integer | yes | no | none | code | immutable | target run state | scene card |
| `pov_character_id` | character ID | yes | no | none | LLM, validated by code | candidate | active character | scene card |
| `participant_ids` | array of character ID | yes | no | none | LLM, validated by code | candidate | all active and unique | scene card |
| `location_id` | location ID | yes | yes | null | LLM, validated by code | candidate | adopted location if set | scene card |
| `time_relation` | enum `same_time|later|next_day|after_interval|parallel` | yes | no | none | LLM, validated by code | candidate | exact enum | scene card |
| `time_label` | string | yes | yes | null | LLM, validated by code | candidate | NFC if set | scene card |
| `scene_purpose` | string | yes | no | none | LLM, validated by code | candidate | NFC nonempty | scene card |
| `required_beats` | array of string | yes | no | none | LLM, validated by code | candidate | unique NFC strings | scene card |
| `emotional_change_target` | string | yes | yes | null | LLM, validated by code | candidate | NFC if set | scene card |
| `relationship_change_target` | relationship ID | yes | yes | null | LLM, validated by code | candidate | adopted relationship if set | scene card |
| `thread_actions` | array of thread-action record | yes | no | none | LLM, validated by code | candidate | each thread resolves | scene card |
| `thread_actions[].thread_id` | thread ID | yes | no | none | LLM, validated by code | candidate | adopted thread | scene card |
| `thread_actions[].action` | string | yes | no | none | LLM, validated by code | candidate | nonempty | scene card |
| `thread_actions[].target_progress` | integer | yes | no | none | LLM, validated by code | candidate | 0..4 | scene card |
| `thread_actions[].purpose` | string | yes | no | none | LLM, validated by code | candidate | nonempty | scene card |
| `reader_disclosures` | array of reader-disclosure record | yes | no | none | LLM, validated by code | candidate | fact IDs resolve | scene card |
| `reader_disclosures[].fact_id` | knowledge ID | yes | no | none | LLM, validated by code | candidate | adopted knowledge item | scene card |
| `reader_disclosures[].target_reader_status` | enum `withheld|hinted|partially_revealed|revealed` | yes | no | none | LLM, validated by code | candidate | exact enum | scene card |
| `reader_disclosures[].purpose` | string | yes | no | none | LLM, validated by code | candidate | nonempty | scene card |
| `withheld_constraints` | array of string | yes | no | none | code | candidate | abstract labels only | scene card |
| `allowed_update_targets` | array of update-target record | yes | no | none | code | candidate | every target resolves | scene card |
| `allowed_update_targets[].target_type` | record type enum | yes | no | none | code | candidate | exact enum | scene card |
| `allowed_update_targets[].target_id` | record ID | yes | no | none | code | candidate | adopted target | scene card |
| `allowed_update_targets[].allowed_fields` | array of string | yes | no | none | code | candidate | update matrix fields only | scene card |
| `new_item_policy.allowed_types` | array of record type enum | yes | no | none | LLM, validated by code | candidate | no duplicate type | scene card |
| `new_item_policy.max_items` | integer | yes | no | none | LLM, validated by code | candidate | 0..configuration.max_new_items_per_scene | scene card |
| `new_item_policy.purpose` | string | yes | no | none | LLM, validated by code | candidate | NFC nonempty | scene card |
| `length_guidance.target_chars` | integer | yes | no | none | LLM, validated by code | candidate | positive | scene card |
| `length_guidance.guide_min_chars` | integer | yes | no | none | LLM, validated by code | candidate | positive and <= target | scene card |
| `length_guidance.guide_max_chars` | integer | yes | no | none | LLM, validated by code | candidate | >= target | scene card |
| `chapter_completion_role` | enum `opening|development|turn|climax|resolution` | yes | no | none | LLM, validated by code | candidate | exact enum | scene card |

A prohibited-new-item scene uses `allowed_types: []`, `max_items: 0`, and a nonempty purpose stating that no new item is allowed.

## Continuity delta

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `existing_item_updates` | array of existing-update record | yes | no | none | LLM, validated by code | candidate | set, append, remove, transition | literal prose quote | all child fields required | delta |
| `existing_item_updates[].operation` | enum `set|append|remove|transition` | yes | no | none | LLM | candidate | exact enum | literal prose quote | target matrix | delta |
| `existing_item_updates[].target_type` | record type enum | yes | no | none | LLM | candidate | none | literal prose quote | exact enum | delta |
| `existing_item_updates[].target_id` | record ID | yes | no | none | LLM | candidate | none | literal prose quote | allowed target | delta |
| `existing_item_updates[].field` | string | yes | no | none | LLM | candidate | matrix field | literal prose quote | allowed direct field | delta |
| `existing_item_updates[].before` | typed field value | yes | yes | null | code | candidate | none | literal prose quote | equals prior snapshot | delta |
| `existing_item_updates[].after` | typed field value | yes | yes | null | LLM | candidate | operation compatible | literal prose quote | target field Schema | delta |
| `existing_item_updates[].scene_id` | scene ID | yes | no | none | code | candidate | none | literal prose quote | current scene | delta |
| `existing_item_updates[].evidence` | string | yes | no | none | LLM | candidate | none | self | verbatim adopted prose | delta |
| `new_item_proposals` | array of discriminated record proposal | yes | no | none | LLM, validated by code | candidate | append | literal prose quote | no free payload field | delta |
| `knowledge_item_proposals` | array of knowledge proposal | yes | no | none | LLM, validated by code | candidate | append | literal prose quote | all listed fields | delta |
| `knowledge_updates` | array of knowledge-state update | yes | no | none | LLM, validated by code | candidate | transition | literal prose quote | all listed fields | delta |
| `thread_updates` | array of thread update | yes | no | none | LLM, validated by code | candidate | transition | literal prose quote | all listed fields | delta |
| `ending_evidence_proposals` | array of ending-evidence proposal | yes | no | none | LLM, validated by code | candidate | append | literal prose quote | relation enum | delta |
| `time_update` | time-update record | yes | yes | null | LLM, validated by code | candidate | transition | literal prose quote if changed | all listed fields | delta |

`new_item_proposals[]` has `local_key`, `record_type`, `scope`, `scene_id`, and `evidence`; its discriminated branch is one of character, relationship, location, organization, item, system, culture, history, or supporting_thread and exposes that record type's named fields. It has no generic payload field. `knowledge_item_proposals[]` has `local_key`, `subject_type`, `subject_id`, `canonical_fact`, `writer_visible_label`, `scope`, `scene_id`, and `evidence`. `knowledge_updates[]` has `fact_id`, `audience_type`, `audience_id`, `before`, `after`, `scene_id`, and `evidence`. `thread_updates[]` has `thread_id`, `operation`, `before_status`, `after_status`, `before_progress`, `after_progress`, `scene_id`, and `evidence`. `ending_evidence_proposals[]` has `criterion_id`, `scene_id`, `evidence`, and `relation` where relation is `supports` or `contradicts`. `time_update` has `time_relation`, `time_label`, `elapsed_hint`, `parallel_group_id`, and `evidence`; code adds `before_order`, `after_order`, and `last_scene_id`.
