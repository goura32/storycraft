# Ledger contracts

> 台帳・state・lifecycle・updateの唯一の正本。工程は[pipeline contracts](pipeline_contracts.md)、checkpointは[runtime and recovery](runtime_and_recovery.md)を参照する。

## Global rules and ID allocation

All persisted objects are `additionalProperties:false`. Unless a row says otherwise, fields are non-null, no default, created by `LLM candidate → code validation`, and the selected HEAD generation is source of truth. Code alone allocates six-digit IDs; gaps are allowed and reuse is forbidden.

| world kind | prefix | counter |
|---|---|---|
| location | `loc-000001` | `next_location_id` |
| organization | `org-000001` | `next_organization_id` |
| item | `item-000001` | `next_item_id` |
| system | `sys-000001` | `next_system_id` |
| culture | `culture-000001` | `next_culture_id` |
| history | `history-000001` | `next_history_id` |

Other prefixes are `char-`, `rel-`, `rule-`, `thread-`, `ending-`, `fact-`, and `ev-`. LLM never creates persistent IDs.

## Enum and lifecycle

| name | values |
|---|---|
| general record lifecycle | `active|inactive|retired` |
| thread status | `open|in_progress|resolved|retired` |
| volume disposition | `resolve|carry_over|retire` |
| world kind | `location|organization|item|system|culture|history` |
| knowledge origin | `initial_design|prose` |
| knowledge status | `unknown|suspects|misunderstands|partially_knows|knows` |
| trust | `none|low|medium|high|absolute` |

General records never use `resolved`. Thread consistency is `open=0`, `in_progress=1..3`, `resolved=4`, `retired=0..3`; progress labels are 0 未導入, 1 導入済み, 2 進展前半, 3 進展後半, 4 回収済み. `resolve` requires thread status resolved; `carry_over` requires in-progress and scope series; `retire` requires thread status retired.

## Common record fields

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `id` | string | yes | no | none | code | immutable | none | registered prefix | current canon |
| `record_type` | enum | yes | no | none | code | immutable | none | known record type | current canon |
| `scope` | enum `scene|chapter|volume|series` | yes | no | `series` | code | transition | transition | scope graph | current canon |
| `record_lifecycle` | general lifecycle enum | yes | no | `active` | code | transition | transition | active→inactive→retired | current canon |
| `created_scene_id` | scene ID | yes | yes | null | code | immutable | none | null for genesis | current canon |
| `references` | array<string> | yes | no | `[]` | code | mutable | append/remove | unique known IDs | current canon |

## Character fields

### Fixed profile

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `name` | string | yes | no | none | LLM | initial-only | none | nonempty unique display name | initial design |
| `aliases` | array<string> | yes | no | `[]` | LLM | initial-only | none | unique nonempty strings | initial design |
| `role` | enum `protagonist|love_interest|antagonist|ally|family|mentor|rival|supporting` | yes | no | none | LLM | initial-only | none | exact enum | initial design |
| `core_trait` | string | yes | no | none | LLM | initial-only | none | nonempty | initial design |
| `values` | array<string> | yes | no | `[]` | LLM | initial-only | none | unique nonempty | initial design |
| `background` | string | yes | no | none | LLM | initial-only | none | nonempty | initial design |
| `immutable_facts` | array<string> | yes | no | `[]` | LLM | initial-only | none | unique nonempty | initial design |
| `appearance_anchor` | string | yes | yes | null | LLM | initial-only | none | nonempty if set | initial design |
| `speech_anchor` | string | yes | yes | null | LLM | initial-only | none | nonempty if set | initial design |

### Character story state

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `location_id` | location ID | yes | yes | null | code | mutable | set | known active location | story state |
| `physical_condition` | string | yes | yes | null | LLM→code | mutable | set | nonempty if set; evidence | story state |
| `emotional_state` | string | yes | yes | null | LLM→code | mutable | set | nonempty if set; evidence | story state |
| `current_goal` | string | yes | yes | null | LLM→code | mutable | set | nonempty if set; evidence | story state |
| `current_pressure` | string | yes | yes | null | LLM→code | mutable | set | nonempty if set; evidence | story state |

## Relationship fields

### Fixed profile

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `participant_a_id` | character ID | yes | no | none | code | immutable | none | known character | current canon |
| `participant_b_id` | character ID | yes | no | none | code | immutable | none | known distinct character | current canon |
| `relationship_type` | enum `central|romantic|family|friendship|alliance|rivalry|authority|conflict` | yes | no | none | LLM | initial-only | none | exact enum | initial design |
| `origin` | string | yes | no | none | LLM | initial-only | none | nonempty | initial design |
| `structural_role` | enum `primary|secondary|supporting` | yes | no | `supporting` | LLM | initial-only | none | exact enum | initial design |

### Relationship story state

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `public_relation` | string | yes | no | none | LLM→code | mutable | set | nonempty; evidence | story state |
| `a_to_b.trust` | trust enum | yes | no | `medium` | LLM→code | mutable | transition | exact enum; evidence | story state |
| `a_to_b.perception` | string | yes | no | none | LLM→code | mutable | set | nonempty; evidence | story state |
| `a_to_b.emotional_stance` | string | yes | no | none | LLM→code | mutable | set | nonempty; evidence | story state |
| `a_to_b.current_intention` | string | yes | no | none | LLM→code | mutable | set | nonempty; evidence | story state |
| `b_to_a.trust` | trust enum | yes | no | `medium` | LLM→code | mutable | transition | exact enum; evidence | story state |
| `b_to_a.perception` | string | yes | no | none | LLM→code | mutable | set | nonempty; evidence | story state |
| `b_to_a.emotional_stance` | string | yes | no | none | LLM→code | mutable | set | nonempty; evidence | story state |
| `b_to_a.current_intention` | string | yes | no | none | LLM→code | mutable | set | nonempty; evidence | story state |
| `shared_state` | string | yes | no | none | LLM→code | mutable | set | nonempty; evidence | story state |

## World fields

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `name` | string | yes | no | none | LLM | initial-only | none | nonempty | initial design |
| `kind` | world kind enum | yes | no | none | LLM | immutable | none | exact enum | current canon |
| `description` | string | yes | no | none | LLM | initial-only | none | nonempty | initial design |
| `immutable_rules` | array<string> | yes | no | `[]` | LLM | initial-only | none | unique nonempty | initial design |
| `sensory_anchors` | array<string> | yes | no | `[]` | LLM | initial-only | none | unique nonempty | initial design |
| `scope` | scope enum | yes | no | `series` | code | transition | transition | scope graph | current canon |

Kind-specific usable fields: location uses `description,immutable_rules,sensory_anchors`; organization additionally uses `references`; item additionally uses `references`; system uses `immutable_rules`; culture uses `description,immutable_rules,sensory_anchors`; history uses `description,references`. No kind has unnamed fields.

## Thread, ending, knowledge, and story clock

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `thread.description` | string | yes | no | none | LLM | initial-only | none | nonempty | initial design |
| `thread.author_truth` | string | yes | no | none | LLM | initial-only | none | planner-only | initial design |
| `thread.resolution_condition` | string | yes | no | none | LLM | initial-only | none | planner-only | initial design |
| `thread.thread_status` | thread status enum | yes | no | `open` | code | transition | transition | progress matrix | story state |
| `thread.progress` | integer | yes | no | 0 | code | mutable | set | 0..4, evidence | story state |
| `ending.description` | string | yes | no | none | LLM | immutable | none | nonempty | initial design |
| `ending.required` | boolean | yes | no | true | LLM | immutable | none | boolean | initial design |
| `story_clock.current_order` | integer | yes | no | 0 | code | increment | increment | +1 each commit | story state |
| `story_clock.time_label` | string | yes | yes | null | LLM→code | mutable | set | evidence when changed | story state |
| `story_clock.parallel_group_id` | string | yes | yes | null | LLM→code | mutable | set | evidence when changed | story state |
| `story_clock.last_scene_id` | scene ID | yes | yes | null | code | mutable | set | adopted scene | story state |

### Knowledge item by origin

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `id` | fact ID | yes | no | code allocated | code | immutable | none | registered ID | current canon |
| `origin` | enum `initial_design|prose` | yes | no | none | code | immutable | none | exact enum | current canon |
| `subject_type` | enum | yes | no | none | code | immutable | none | known subject type | current canon |
| `subject_id` | ID | yes | no | none | code | immutable | none | existing subject | current canon |
| `canonical_fact` | string | yes | no | none | LLM→code | immutable | none | nonempty | current canon |
| `writer_visible_label` | string | yes | no | none | LLM→code | immutable | none | nonempty | current canon |
| `scope` | scope enum | yes | no | `scene` | code | immutable | none | scope graph | current canon |
| `created_scene_id` | scene ID | yes | yes | null | code | immutable | none | null only initial design | current canon |
| `record_lifecycle` | general lifecycle enum | yes | no | `active` | code | transition | transition | general lifecycle | current canon |
| `author_truth` initial_design | string | yes | no | none | LLM | immutable | none | nonempty, planner-only | current canon |
| `author_truth` prose | string | yes | yes | null | code | immutable | none | must be null | current canon |

A prose `knowledge_item_proposal` has exactly `local_key,subject_type,subject_id,canonical_fact,writer_visible_label,scope,scene_id,evidence`; it never has `author_truth`.

### Knowledge state array

`story_state.knowledge_states` is an array, never a concatenated-key map.

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `fact_id` | fact ID | yes | no | none | code | immutable | none | existing fact | story state |
| `audience_type` | enum `reader|character` | yes | no | none | code | immutable | none | exact enum | story state |
| `audience_id` | character ID | yes | yes | null | code | immutable | none | null iff reader; known character iff character | story state |
| `status` | knowledge status enum | yes | no | `unknown` | code | mutable | transition | unique fact+audience type+audience ID | story state |

## Volume handoff fields

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `volume_number` | integer | yes | no | none | code | immutable | none | adopted volume | handoff artifact |
| `narrative_handoff` | string | yes | no | none | LLM→code | immutable | none | adopted facts only | handoff artifact |
| `open_pressures` | array of open pressure item | yes | no | `[]` | LLM→code | immutable | none | each item table below | handoff artifact |
| `character_states` | array of character state item | yes | no | `[]` | LLM→code | immutable | none | each item table below | handoff artifact |
| `relationship_states` | array of relationship state item | yes | no | `[]` | LLM→code | immutable | none | each item table below | handoff artifact |
| `carried_threads` | array of carried thread item | yes | no | `[]` | LLM→code | immutable | none | each item table below | handoff artifact |
| `story_clock` | story clock object | yes | no | none | code | immutable | none | adopted end-of-volume clock | handoff artifact |
| `next_volume_constraints` | array of constraint item | yes | no | `[]` | LLM→code | immutable | none | each item table below | handoff artifact |

| handoff item field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `open_pressures.pressure_id` | string | yes | no | none | code | immutable | none | unique within handoff | handoff artifact |
| `open_pressures.description` | string | yes | no | none | LLM→code | immutable | none | adopted fact only | handoff artifact |
| `open_pressures.related_ids` | array<string> | yes | no | `[]` | code | immutable | none | known IDs | handoff artifact |
| `open_pressures.urgency` | enum `low|medium|high|immediate` | yes | no | none | LLM→code | immutable | none | exact enum | handoff artifact |
| `character_states.character_id` | character ID | yes | no | none | code | immutable | none | known character | handoff artifact |
| `character_states.physical_condition` | string | yes | yes | null | code | immutable | none | end state | handoff artifact |
| `character_states.emotional_state` | string | yes | yes | null | code | immutable | none | end state | handoff artifact |
| `character_states.current_goal` | string | yes | yes | null | code | immutable | none | end state | handoff artifact |
| `character_states.current_pressure` | string | yes | yes | null | code | immutable | none | end state | handoff artifact |
| `relationship_states.relationship_id` | relationship ID | yes | no | none | code | immutable | none | known relationship | handoff artifact |
| `relationship_states.public_relation` | string | yes | no | none | code | immutable | none | end state | handoff artifact |
| `relationship_states.a_to_b` | relationship direction object | yes | no | none | code | immutable | none | full nested state | handoff artifact |
| `relationship_states.b_to_a` | relationship direction object | yes | no | none | code | immutable | none | full nested state | handoff artifact |
| `relationship_states.shared_state` | string | yes | no | none | code | immutable | none | end state | handoff artifact |
| `carried_threads.thread_id` | thread ID | yes | no | none | code | immutable | none | known thread | handoff artifact |
| `carried_threads.thread_status` | thread status enum | yes | no | none | code | immutable | none | status matrix | handoff artifact |
| `carried_threads.progress` | integer | yes | no | none | code | immutable | none | 0..4 | handoff artifact |
| `carried_threads.active_pressure` | string | yes | yes | null | LLM→code | immutable | none | adopted fact | handoff artifact |
| `carried_threads.volume_disposition` | disposition enum | yes | no | none | code | immutable | none | disposition/status matrix | handoff artifact |
| `next_volume_constraints.constraint_type` | enum `must_preserve|must_reveal|must_not_reveal|must_resolve` | yes | no | none | code | immutable | none | exact enum | handoff artifact |
| `next_volume_constraints.description` | string | yes | no | none | LLM→code | immutable | none | adopted fact | handoff artifact |
| `next_volume_constraints.related_ids` | array<string> | yes | no | `[]` | code | immutable | none | known IDs | handoff artifact |

## Series map targets, update matrix, evidence

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `relationship_target.relationship_id` | relationship ID | yes | no | none | code | immutable | none | existing relationship | series map |
| `relationship_target.start_state` | string | yes | no | none | LLM | immutable | none | nonempty | series map |
| `relationship_target.target_state` | string | yes | no | none | LLM | immutable | none | nonempty | series map |
| `relationship_target.change_function` | string | yes | no | none | LLM | immutable | none | nonempty | series map |
| `thread_target.thread_id` | thread ID | yes | no | none | code | immutable | none | existing major thread | series map |
| `thread_target.start_progress` | integer | yes | no | none | code | immutable | none | 0..4 | series map |
| `thread_target.target_progress` | integer | yes | no | none | code | immutable | none | 0..4 and >= start | series map |
| `thread_target.required_action` | enum `introduce|advance|resolve` | yes | no | none | LLM | immutable | none | target/status compatible | series map |

Only `set|append|remove|transition` operations are permitted; free JSON Patch is forbidden. Every allowed dynamic field needs exact prose evidence and matching before value. Evidence index rows have individually required `evidence_id,evidence_type,target_id,scene_id,quote,relation,start_offset,end_offset,quote_sha256`; code allocates evidence ID and computes offsets/hash, while quote is exact NFC prose substring. `relation` is `supports|contradicts`.
