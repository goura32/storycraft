# Ledger contracts: Canon records and enum registry

`current_canon` stores adopted fixed records; `knowledge_items` stores adopted knowledge items; `story_state` stores mutable values. Every persisted object has `additionalProperties: false`; unlisted fields are rejected. Code alone allocates persistent IDs at adoption.

## Enum registry

| enum | permitted values |
|---|---|
| `record_type` | `character, relationship, world_entity, temporal_rule, thread, ending_criterion, knowledge_item` |
| `character_role` | `protagonist, love_interest, antagonist, ally, family, mentor, rival, supporting` |
| `relationship_type` | `central, romantic, family, friendship, alliance, rivalry, authority, conflict` |
| `structural_role` | `primary, secondary, supporting` |
| `trust` | `none, low, medium, high, absolute` |
| `world_entity_kind` | `location, organization, item, system, culture, history` |
| `temporal_rule_kind` | `deadline, travel_duration, recovery_rule, cycle, progression_rule, age_rule` |
| `thread_type` | `major, supporting` |
| `thread_status` | `open, in_progress, resolved, retired` |
| `thread_action` | `introduce, advance, resolve, retire` |
| `character_knowledge_status` | `unknown, suspects, misunderstands, partially_knows, knows` |
| `reader_knowledge_status` | `withheld, hinted, partially_revealed, revealed` |
| `time_relation` | `same_time, later, next_day, after_interval, parallel` |
| `chapter_completion_role` | `opening, development, turn, climax, resolution` |
| `scope` | `scene, chapter, volume, series` |
| `record_lifecycle` | `active, inactive, retired` |
| `volume_disposition` | `resolve, carry_over, retire` |
| `knowledge_origin` | `genesis, prose` |

## Character record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `id` | character ID | yes | no | none | code | immutable | registered ID | current canon |
| `record_type` | enum `character` | yes | no | none | code | immutable | enum registry | current canon |
| `name` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `aliases` | array<string> | yes | no | `[]` | LLM→code | transition / evidence update | unique values | current canon |
| `role` | enum `character_role` | yes | no | none | LLM→code | immutable | enum registry | current canon |
| `core_trait` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `values` | array<string> | yes | no | `[]` | LLM→code | immutable | unique values | current canon |
| `background` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `immutable_facts` | array<string> | yes | no | `[]` | LLM→code | transition / evidence update | unique values | current canon |
| `appearance_anchor` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `speech_anchor` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `scope` | enum `scope` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `created_scene_id` | scene ID | yes | yes | `null` | code | immutable | registered ID | current canon |

## Relationship record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `id` | relationship ID | yes | no | none | code | immutable | registered ID | current canon |
| `record_type` | enum `relationship` | yes | no | none | code | immutable | enum registry | current canon |
| `participant_a_id` | character ID | yes | no | none | LLM→code | immutable | adopted character; differs from `participant_b_id` | current canon |
| `participant_b_id` | character ID | yes | no | none | LLM→code | immutable | adopted character; differs from `participant_a_id` | current canon |
| `relationship_type` | enum `relationship_type` | yes | no | none | LLM→code | immutable | enum registry | current canon |
| `origin` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `structural_role` | enum `structural_role` | yes | no | none | LLM→code | immutable | enum registry | current canon |
| `scope` | enum `scope` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `created_scene_id` | scene ID | yes | yes | `null` | code | immutable | registered ID | current canon |

## World entity record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `id` | world entity ID | yes | no | none | code | immutable | registered ID | current canon |
| `record_type` | enum `world_entity` | yes | no | none | code | immutable | enum registry | current canon |
| `kind` | enum `world_entity_kind` | yes | no | none | LLM→code | immutable | enum registry | current canon |
| `name` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `description` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `immutable_rules` | array<string> | yes | no | `[]` | LLM→code | immutable | unique values | current canon |
| `sensory_anchors` | array<string> | yes | no | `[]` | LLM→code | transition / evidence update | unique values | current canon |
| `scope` | enum `scope` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `created_scene_id` | scene ID | yes | yes | `null` | code | immutable | registered ID | current canon |

## Temporal rule record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `id` | temporal rule ID | yes | no | none | code | immutable | registered ID | current canon |
| `record_type` | enum `temporal_rule` | yes | no | none | code | immutable | enum registry | current canon |
| `kind` | enum `temporal_rule_kind` | yes | no | none | LLM→code | immutable | enum registry | current canon |
| `description` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `fixed_rule` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `related_ids` | array<record ID> | yes | no | `[]` | LLM→code | transition / evidence update | unique values | current canon |
| `scope` | enum `scope` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `created_scene_id` | scene ID | yes | yes | `null` | code | immutable | registered ID | current canon |

## Thread record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `id` | thread ID | yes | no | none | code | immutable | registered ID | current canon |
| `record_type` | enum `thread` | yes | no | none | code | immutable | enum registry | current canon |
| `thread_type` | enum `thread_type` | yes | no | none | LLM→code | immutable | enum registry | current canon |
| `description` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `author_truth` | string | yes | yes | `null` | LLM→code | immutable | `null` iff `origin=prose`; otherwise NFC nonempty; never Writer View | current canon |
| `resolution_condition` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `presentation_rule` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `required` | boolean | yes | no | none | LLM→code | immutable | registered ID | current canon |
| `scope` | enum `scope` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `created_scene_id` | scene ID | yes | yes | `null` | code | immutable | registered ID | current canon |

## Ending criterion record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `id` | ending criterion ID | yes | no | none | code | immutable | registered ID | current canon |
| `record_type` | enum `ending_criterion` | yes | no | none | code | immutable | enum registry | current canon |
| `description` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `required` | boolean | yes | no | none | LLM→code | immutable | registered ID | current canon |
| `source_ending_text` | string | yes | no | none | LLM→code | immutable | NFC nonempty | current canon |
| `scope` | enum `scope` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | none | code | transition / evidence update | enum registry | current canon |
| `created_scene_id` | scene ID | yes | yes | `null` | code | immutable | registered ID | current canon |

## Knowledge item record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `id` | knowledge ID | yes | no | none | code | immutable | registered ID | knowledge items |
| `record_type` | enum `knowledge_item` | yes | no | none | code | immutable | enum registry | knowledge items |
| `origin` | enum `knowledge_origin` | yes | no | none | LLM→code | immutable | enum registry | knowledge items |
| `subject_type` | enum `record_type` excluding `knowledge_item` | yes | no | none | code | immutable | enum registry | knowledge items |
| `subject_id` | record ID | yes | no | none | code | immutable | registered ID | knowledge items |
| `canonical_fact` | string | yes | no | none | LLM→code | immutable | NFC nonempty | knowledge items |
| `writer_visible_label` | string | yes | no | none | LLM→code | immutable | NFC nonempty | knowledge items |
| `author_truth` | string | yes | yes | `null` | LLM→code | immutable | `null` iff `origin=prose`; otherwise NFC nonempty; never Writer View | knowledge items |
| `scope` | enum `scope` | yes | no | none | code | transition / evidence update | enum registry | knowledge items |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | none | code | transition / evidence update | enum registry | knowledge items |
| `created_scene_id` | scene ID | yes | yes | `null` | code | immutable | registered ID | knowledge items |

No generic `payload` field is permitted. Typed creation and every mutable update are governed by [evidence and updates](evidence_and_updates.md).
