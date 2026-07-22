# Ledger contracts: Canon records and enum registry

`current_canon` contains adopted fixed records, their scope, lifecycle, and references. `knowledge_items` contains accepted knowledge subjects. `story_state` contains mutable current story values. `runtime_state` contains execution state. Every saved record has `additionalProperties: false`.

## Enum registry

| enum | permitted values |
|---|---|
| `record_type` | `character`, `relationship`, `location`, `organization`, `item`, `system`, `culture`, `history`, `supporting_thread` |
| `character_role` | `protagonist`, `love_interest`, `antagonist`, `ally`, `family`, `mentor`, `rival`, `supporting` |
| `relationship_type` | `central`, `romantic`, `family`, `friendship`, `alliance`, `rivalry`, `authority`, `conflict` |
| `structural_role` | `primary`, `secondary`, `supporting` |
| `trust` | `none`, `low`, `medium`, `high`, `absolute` |
| `world_entity_kind` | `location`, `organization`, `item`, `system`, `culture`, `history` |
| `temporal_rule_kind` | `deadline`, `travel_duration`, `recovery_rule`, `cycle`, `progression_rule`, `age_rule` |
| `thread_status` | `open`, `in_progress`, `resolved`, `retired` |
| `thread_action` | `introduce`, `advance`, `resolve`, `retire` |
| `character_knowledge_status` | `unknown`, `suspects`, `misunderstands`, `partially_knows`, `knows` |
| `reader_knowledge_status` | `withheld`, `hinted`, `partially_revealed`, `revealed` |
| `time_relation` | `same_time`, `later`, `next_day`, `after_interval`, `parallel` |
| `chapter_completion_role` | `opening`, `development`, `turn`, `climax`, `resolution` |
| `scope` | `scene`, `chapter`, `volume`, `series` |
| `record_lifecycle` | `active`, `inactive`, `retired` |
| `volume_disposition` | `resolve`, `carry_over`, `retire` |

## Common record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `id` | record ID | yes | no | none | code | immutable | registered prefix and uniqueness | current canon |
| `record_type` | record type enum | yes | no | none | code | immutable | registry | current canon |
| `scope` | scope enum | yes | no | `series` | code | transition | registry | current canon |
| `record_lifecycle` | record lifecycle enum | yes | no | `active` | code | transition | registry | current canon |
| `created_scene_id` | scene ID | yes | yes | null | code | immutable | null at genesis | current canon |
| `references` | array of record ID | yes | no | `[]` | code | mutable | unique adopted IDs | current canon |

The detailed immutable field tables for characters, relationships, world entities, threads, ending criteria, and knowledge items remain in the adopted generation selected by `canon/HEAD`; typed changes are exclusively governed by [evidence and updates](evidence_and_updates.md).
