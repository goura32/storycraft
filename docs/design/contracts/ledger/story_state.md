# Ledger contracts: story state

`canon/generations/<id>/story-state.json` has only character states, relationship states, thread states, knowledge states, story clock, and current volume/chapter/scene. It never embeds fixed Canon records or knowledge items. Every saved object rejects unknown fields.

## Character state

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| character_id | character ID | yes | no | none | code | immutable | known character | story_state |
| location_id | location ID | yes | yes | null | code | mutable | set|evidence | story_state |
| physical_condition | string | yes | yes | null | LLM→code | mutable | set|evidence | story_state |
| emotional_state | string | yes | yes | null | LLM→code | mutable | set|evidence | story_state |
| current_goal | string | yes | yes | null | LLM→code | mutable | set|evidence | story_state |
| current_pressure | string | yes | yes | null | LLM→code | mutable | set|evidence | story_state |

## Relationship state

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| relationship_id | relationship ID | yes | no | none | code | immutable | known relationship | story_state |
| public_relation | string | yes | no | none | LLM→code | mutable | set|evidence | story_state |
| a_to_b.trust | trust enum | yes | no | medium | LLM→code | mutable | transition|evidence | story_state |
| a_to_b.perception | string | yes | no | none | LLM→code | mutable | set|evidence | story_state |
| a_to_b.emotional_stance | string | yes | no | none | LLM→code | mutable | set|evidence | story_state |
| a_to_b.current_intention | string | yes | no | none | LLM→code | mutable | set|evidence | story_state |
| b_to_a.trust | trust enum | yes | no | medium | LLM→code | mutable | transition|evidence | story_state |
| b_to_a.perception | string | yes | no | none | LLM→code | mutable | set|evidence | story_state |
| b_to_a.emotional_stance | string | yes | no | none | LLM→code | mutable | set|evidence | story_state |
| b_to_a.current_intention | string | yes | no | none | LLM→code | mutable | set|evidence | story_state |
| shared_state | string | yes | no | none | LLM→code | mutable | set|evidence | story_state |

## Thread state

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| thread_id | thread ID | yes | no | none | code | immutable | known thread | story_state |
| thread_status | enum `open|in_progress|resolved|retired` | yes | no | open | code | mutable | status/progress matrix | story_state |
| progress | integer | yes | no | 0 | code | mutable | 0..4 and status matrix | story_state |
| volume_disposition | enum `resolve|carry_over|retire` | yes | yes | null | code | mutable | matrix and scope | story_state |

## Knowledge state

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| fact_id | knowledge ID | yes | no | none | code | immutable | known fact | story_state |
| audience_type | enum `character|reader` | yes | no | none | code | immutable | exact enum | story_state |
| audience_id | character ID | yes | yes | null | code | immutable | null iff reader | story_state |
| status | knowledge status enum | yes | no | unknown | code | mutable | unique fact/audience row | story_state |

## Story clock and position

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| current_order | integer | yes | no | 0 | code | mutable | monotonic | story_state |
| time_label | string | yes | yes | null | code | mutable | NFC if set | story_state |
| parallel_group_id | string | yes | yes | null | code | mutable | NFC if set | story_state |
| last_scene_id | scene ID | yes | yes | null | code | mutable | adopted scene | story_state |
| current_volume_number | integer | yes | yes | null | code | mutable | run target | story_state |
| current_chapter_number | integer | yes | yes | null | code | mutable | run target | story_state |
| current_scene_number | integer | yes | yes | null | code | mutable | run target | story_state |
