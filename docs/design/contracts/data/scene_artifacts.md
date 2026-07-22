# Data contracts: scene artifacts

All saved objects reject unknown fields. Scene identity is code input; LLM never generates it.

## Scene card

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `scene_id` | scene ID | yes | no | none | code | immutable | v01-c001-s001 pattern | scene card |
| `volume_number` | integer | yes | no | none | code | immutable | target run state | scene card |
| `chapter_number` | integer | yes | no | none | code | immutable | target run state | scene card |
| `scene_number` | integer | yes | no | none | code | immutable | target run state | scene card |
| `pov_character_id` | character ID | yes | no | none | LLM→code | candidate | known active character | scene card |
| `participant_ids` | array<string> | yes | no | [] | LLM→code | candidate | known character IDs | scene card |
| `location_id` | location ID | yes | yes | null | LLM→code | candidate | known location | scene card |
| `time_relation` | enum `same_time|later|earlier_parallel` | yes | no | none | LLM→code | candidate | exact enum | scene card |
| `time_label` | string | yes | yes | null | LLM→code | candidate | NFC if set | scene card |
| `scene_purpose` | string | yes | no | none | LLM→code | candidate | nonempty | scene card |
| `required_beats` | array<string> | yes | no | [] | LLM→code | candidate | NFC strings | scene card |
| `emotional_change_target` | string | yes | yes | null | LLM→code | candidate | NFC if set | scene card |
| `relationship_change_target` | relationship ID | yes | yes | null | LLM→code | candidate | known relation | scene card |
| `thread_actions` | array of thread action | yes | no | [] | LLM→code | candidate | known thread IDs | scene card |
| `reader_disclosures` | array<string> | yes | no | [] | LLM→code | candidate | no author truth | scene card |
| `withheld_constraints` | array<string> | yes | no | [] | code | candidate | abstract labels | scene card |
| `allowed_update_targets` | array<string> | yes | no | [] | code | candidate | known IDs | scene card |
| `new_item_policy` | enum `forbid|allow_scene_only|allow_declared_scope` | yes | no | none | LLM→code | candidate | exact enum | scene card |
| `length_guidance` | integer | yes | no | none | LLM→code | candidate | >=1 | scene card |
| `chapter_completion_role` | enum `open|advance|close` | yes | no | none | LLM→code | candidate | exact enum | scene card |

## Writer view

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `scene_card` | scene card | yes | no | none | code | immutable | adopted checkpoint only | Context Builder |
| `pov_character` | character projection | yes | no | none | code | immutable | card POV only | Context Builder |
| `visible_characters` | array of character projection | yes | no | [] | code | immutable | visible IDs only | Context Builder |
| `visible_relationship_state` | relationship state projection | yes | no | none | code | immutable | participants only | Context Builder |
| `visible_world` | array of world projection | yes | no | [] | code | immutable | scene visible only | Context Builder |
| `known_facts` | array of knowledge projection | yes | no | [] | code | immutable | POV audience only | Context Builder |
| `reader_known_facts` | array of knowledge projection | yes | no | [] | code | immutable | reader audience only | Context Builder |
| `previous_handoff` | volume handoff | yes | yes | null | code | immutable | adopted only | Context Builder |
| `style_profile` | style profile | yes | no | none | code | immutable | known profile | Context Builder |
| `forbidden_disclosures` | array<string> | yes | no | [] | code | immutable | abstract labels only | Context Builder |

## Continuity delta

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `existing_item_updates` | array of update | yes | no | [] | LLM→code | candidate | matrix/evidence | delta |
| `new_item_proposals` | array of proposal | yes | no | [] | LLM→code | candidate | scope/local key | delta |
| `knowledge_item_proposals` | array of knowledge proposal | yes | no | [] | LLM→code | candidate | prose origin has null truth | delta |
| `knowledge_updates` | array of knowledge update | yes | no | [] | LLM→code | candidate | state row/evidence | delta |
| `thread_updates` | array of thread update | yes | no | [] | LLM→code | candidate | status/progress/evidence | delta |
| `ending_evidence_proposals` | array of ending evidence | yes | no | [] | LLM→code | candidate | quote in prose | delta |
| `time_update` | time update | yes | yes | null | LLM→code | candidate | time enum/evidence | delta |
| `handoff_summary` | string | yes | no | none | LLM→code | candidate | adopted facts only | delta |

## Volume handoff

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `volume_number` | integer | yes | no | none | code | immutable | adopted volume | handoff |
| `narrative_handoff` | string | yes | no | none | LLM→code | immutable | adopted facts | handoff |
| `open_pressures` | array of pressure | yes | no | [] | LLM→code | immutable | known IDs | handoff |
| `character_states` | array of state | yes | no | [] | code | immutable | end state | handoff |
| `relationship_states` | array of state | yes | no | [] | code | immutable | end state | handoff |
| `carried_threads` | array of thread state | yes | no | [] | code | immutable | matrix valid | handoff |
| `story_clock` | story clock | yes | no | none | code | immutable | end clock | handoff |
| `next_volume_constraints` | array of constraint | yes | no | [] | LLM→code | immutable | adopted facts | handoff |
