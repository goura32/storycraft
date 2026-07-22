# Ledger contracts

> 台帳・state・field契約の唯一の正本。工程は[pipeline contracts](pipeline_contracts.md)、Contextは[context contracts](context_contracts.md)、保存pathは[workspace layout](workspace_layout.md)を参照する。

## 共通SchemaとID

全保存objectは`additionalProperties: false`である。全fieldは明記しない限り`nullable: false`、defaultなし、作成者は「LLM候補→コード検証」、正本は`canon/HEAD`が指すgenerationである。IDはコードだけがtype別counterで採番し、6桁・欠番許容・再利用禁止である。

| type | ID | creator | mutability | allowed operation | validation |
|---|---|---|---|---|---|
| character | `char-000001` | code | immutable | none | type counter |
| relationship | `rel-000001` | code | immutable | none | type counter |
| location / organization / item / system | `loc/org/item/sys-000001` | code | immutable | none | type counter |
| temporal rule / thread / ending / fact / evidence | `rule/thread/ending/fact/ev-000001` | code | immutable | none | type counter |

## enum

| name | values |
|---|---|
| character role | `protagonist|love_interest|antagonist|ally|family|mentor|rival|supporting` |
| relationship type | `central|romantic|family|friendship|alliance|rivalry|authority|conflict` |
| structural role | `primary|secondary|supporting` |
| world entity kind | `location|organization|item|system|culture|history` |
| temporal rule kind | `deadline|travel_duration|recovery_rule|cycle|progression_rule|age_rule` |
| knowledge subject type | `character|relationship|world_entity|thread|ending_criterion|event` |
| evidence type | `state_update|knowledge_update|thread_update|ending_criterion|new_canon_item|time_update` |
| chapter completion role | `opening|development|turn|climax|resolution` |
| trust | `none|low|medium|high|absolute` |
| record lifecycle | `active|inactive|retired` |
| thread status | `open|in_progress|resolved|retired` |
| knowledge status | `unknown|suspects|misunderstands|partially_knows|knows` |

## 正本層

| layer | content | source of truth | mutable | prohibited duplicate |
|---|---|---|---|---|
| initial design | fixed initial design and author truth | `canon/initial-design.json` | no after INIT-ID | current state |
| series map | adopted volume-level plan | `plans/series-map.json` | no in v1 | chapter/scene detail |
| current canon | records, fixed facts, lifecycle, references | `canon/HEAD` generation | typed delta only | current emotion/progress |
| story state | dynamic character/relationship/thread/knowledge/clock | `canon/HEAD` generation | typed delta only | author truth |
| runtime | checkpoints/counters/run state | `runtime/` | runtime only | canon/state |

## Canon records

### Common record fields

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `id` | string | yes | no | none | code | immutable | none | registered ID | current canon |
| `record_type` | enum | yes | no | none | code | immutable | none | known type | current canon |
| `scope` | enum `scene|chapter|volume|series` | yes | no | `series` | code | transition | transition | scope graph | current canon |
| `record_lifecycle` | enum | yes | no | `active` | code | transition | transition | active→inactive→retired | current canon |
| `created_scene_id` | string | yes | yes | null | code | immutable | none | null only genesis | current canon |
| `references` | array<string> | yes | no | `[]` | code | mutable | append/remove | each known ID, unique | current canon |

### Character and relationship canon fields

| record / field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| character `name` | string | yes | no | none | LLM | initial-only | none | non-empty, unique display name | initial design |
| character `role` | character role enum | yes | no | none | LLM | initial-only | none | enum | initial design |
| character `fixed` | object | yes | no | none | LLM | initial-only | none | required fixed profile | initial design |
| relationship `participant_a_id` | character ID | yes | no | none | code | immutable | none | known character | current canon |
| relationship `participant_b_id` | character ID | yes | no | none | code | immutable | none | different known character | current canon |
| relationship `relationship_type` | relationship type enum | yes | no | none | LLM | initial-only | none | enum | initial design |
| relationship `structural_role` | structural role enum | yes | no | `supporting` | LLM | initial-only | none | enum | initial design |
| relationship `origin` | string | yes | no | none | LLM | initial-only | none | non-empty | initial design |

### World, rule, thread, ending, knowledge canon fields

| record / field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| world `kind` | world entity kind enum | yes | no | none | LLM | immutable | none | enum | current canon |
| world `name` | string | yes | no | none | LLM | initial-only | none | non-empty | initial design |
| world `fixed` | object | yes | no | none | LLM | initial-only | none | kind-specific schema | initial design |
| temporal `kind` | temporal rule kind enum | yes | no | none | LLM | immutable | none | enum | current canon |
| temporal `fixed_rule` | string | yes | no | none | LLM | initial-only | none | non-empty | initial design |
| thread `description` | string | yes | no | none | LLM | initial-only | none | non-empty | initial design |
| thread `author_truth` | string | yes | no | none | LLM | initial-only | none | never writer-visible | initial design |
| thread `resolution_condition` | string | yes | no | none | LLM | initial-only | none | non-empty | initial design |
| ending `description` | string | yes | no | none | LLM | immutable | none | non-empty | initial design |
| ending `required` | boolean | yes | no | true | LLM | immutable | none | boolean | initial design |
| knowledge `subject_type` | knowledge subject type enum | yes | no | none | code | immutable | none | enum | current canon |
| knowledge `subject_id` | ID | yes | no | none | code | immutable | none | known ID | current canon |
| knowledge `canonical_fact` | string | yes | no | none | LLM | immutable | none | non-empty | current canon |
| knowledge `writer_visible_label` | string | yes | no | none | LLM | immutable | none | non-empty | current canon |
| knowledge `author_truth` | string | yes | no | none | LLM | immutable | none | never writer-visible | current canon |
| knowledge `scope` | scope enum | yes | no | `scene` | code | immutable | none | enum | current canon |
| knowledge `created_scene_id` | scene ID | yes | yes | null | code | immutable | none | adopted scene or null | current canon |
| knowledge `record_lifecycle` | lifecycle enum | yes | no | `active` | code | transition | transition | lifecycle graph | current canon |

## Story state

### Relationship state is nested only

Directional trust aliases flattened into field names are prohibited.

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `public_relation` | string | yes | no | none | LLM→code | mutable | set | non-empty | story state |
| `a_to_b.trust` | trust enum | yes | no | `medium` | LLM→code | mutable | transition | trust enum | story state |
| `a_to_b.perception` | string | yes | no | none | LLM→code | mutable | set | non-empty | story state |
| `a_to_b.emotional_stance` | string | yes | no | none | LLM→code | mutable | set | non-empty | story state |
| `a_to_b.current_intention` | string | yes | no | none | LLM→code | mutable | set | non-empty | story state |
| `b_to_a.*` | same as `a_to_b.*` | yes | no | none | LLM→code | mutable | set/transition | same schema | story state |
| `shared_state` | string | yes | no | none | LLM→code | mutable | set | non-empty | story state |

| state field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `character_states[id].location_id` | location ID | yes | yes | null | code | mutable | set | known location | story state |
| `character_states[id].physical_condition` | string | yes | yes | null | LLM→code | mutable | set | non-empty if set | story state |
| `character_states[id].emotional_state` | string | yes | yes | null | LLM→code | mutable | set | non-empty if set | story state |
| `character_states[id].current_goal` | string | yes | yes | null | LLM→code | mutable | set | non-empty if set | story state |
| `character_states[id].current_pressure` | string | yes | yes | null | LLM→code | mutable | set | non-empty if set | story state |
| `thread_states[id].thread_status` | enum | yes | no | `open` | code | mutable | transition | status/progress matrix | story state |
| `thread_states[id].progress` | integer | yes | no | 0 | code | mutable | set | 0..4, non-decreasing except retire | story state |
| `knowledge_state[fact-id:audience-id].status` | knowledge status enum | yes | no | `unknown` | code | mutable | transition | audience is known ID | story state |
| `story_clock.current_order` | integer | yes | no | 0 | code | mutable | set | increment only | story state |
| `story_clock.time_label` | string | yes | yes | null | LLM→code | mutable | set | evidence if changed | story state |
| `story_clock.parallel_group_id` | string | yes | yes | null | LLM→code | mutable | set | evidence if changed | story state |
| `story_clock.last_scene_id` | scene ID | yes | yes | null | code | mutable | set | adopted scene | story state |

Thread matrix: `open=0`; `in_progress=1..3`; `resolved=4`; `retired=0..3`。`current_order`は本文evidence不要で、毎scene commitに`after_order = before_order + 1`でコードが更新する。

## Continuity delta and update matrix

`time_update`は`time_relation,time_label,elapsed_hint,parallel_group_id,evidence`をLLMが返す。`before_order,after_order,last_scene_id`はコードが付与する。`time_relation`は`same_time|later|next_day|after_interval|parallel`。

本文由来knowledge proposalは`local_key,subject_type,subject_id,canonical_fact,writer_visible_label,scope,scene_id,evidence`だけを持つ。`author_truth`は禁止する。

自由JSON Patchは禁止。更新は以下のみである。

| target_type | field | operation | before必須 | evidence必須 | validation |
|---|---|---|---:|---:|---|
| character_state | location_id | set | Yes | Yes | known location ID |
| character_state | physical_condition | set | Yes | Yes | non-empty |
| character_state | emotional_state | set | Yes | Yes | non-empty |
| character_state | current_goal | set | Yes | Yes | non-empty |
| character_state | current_pressure | set | Yes | Yes | non-empty |
| relationship_state | public_relation | set | Yes | Yes | non-empty |
| relationship_state | a_to_b.trust | transition | Yes | Yes | trust enum |
| relationship_state | b_to_a.trust | transition | Yes | Yes | trust enum |
| relationship_state | a_to_b.perception | set | Yes | Yes | non-empty |
| relationship_state | b_to_a.perception | set | Yes | Yes | non-empty |
| thread_state | thread_status | transition | Yes | Yes | status/progress matrix |
| thread_state | progress | set | Yes | Yes | 0..4 |
| canon_record | record_lifecycle | transition | Yes | Yes | lifecycle graph |
| canon_record | references | append/remove | Yes | Yes | known ID |
| knowledge_state | status | transition | Yes | Yes | knowledge status enum |

## Evidence index

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `evidence_id` | evidence ID | yes | no | code allocated | code | immutable | none | `ev-000001` | evidence index |
| `evidence_type` | evidence type enum | yes | no | none | code | immutable | none | enum | evidence index |
| `target_id` | ID | yes | no | none | code | immutable | none | known target | evidence index |
| `scene_id` | scene ID | yes | no | none | code | immutable | none | adopted scene | evidence index |
| `quote` | string | yes | no | none | LLM→code | immutable | none | exact prose substring | evidence index |
| `relation` | enum `supports|contradicts` | yes | no | none | LLM→code | immutable | none | enum | evidence index |
| `start_offset,end_offset` | integer | yes | no | none | code | immutable | none | exact NFC offsets | evidence index |
| `quote_sha256` | hex string | yes | no | none | code | immutable | none | hash quote | evidence index |
