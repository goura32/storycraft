# Data contracts: brief and initial

All persisted records reject unknown fields. A raw source is serialized as canonical UTF-8, NFC, LF JSON with sorted keys, compact separators, and one trailing LF; `source_hash` is that byte sequence's SHA-256.

## Brief

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `title` | string | yes | no | none | user or LLM, validated by code | immutable | NFC length 1..100 | `input/brief.json` |
| `genre` | string | yes | no | none | user or LLM, validated by code | immutable | NFC length 1..100 | `input/brief.json` |
| `target_reader` | string | yes | no | none | user or LLM, validated by code | immutable | NFC length 1..200 | `input/brief.json` |
| `protagonist.name` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `protagonist.present_position` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `protagonist.core_trait` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `protagonist.current_pressure` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `protagonist.initial_wish` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `key_people` | array of key-person record | yes | no | none | user or LLM, validated by code | immutable | count 1..12; names unique | `input/brief.json` |
| `key_people[].name` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `key_people[].present_position` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `key_people[].initial_relation_to_protagonist` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `want` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `avoid` | array of string | yes | no | none | user or LLM, validated by code | immutable | count 0..20; every string NFC nonempty | `input/brief.json` |
| `ending` | string | yes | no | none | user or LLM, validated by code | immutable | NFC nonempty | `input/brief.json` |
| `volumes` | integer | yes | no | none | user or LLM, validated by code | immutable | 4..10 | `input/brief.json` |
| `editorial_profile_id` | string | yes | no | none | user or LLM, validated by code | immutable | configured profile exists | `input/brief.json` |
| `publishing_profile_id` | string | yes | no | none | user or LLM, validated by code | immutable | configured profile exists | `input/brief.json` |
| `brief_version` | integer | yes | no | 1 | code | immutable | positive | `input/brief.json` |
| `created_at` | RFC3339 timestamp | yes | no | none | code | immutable | UTC | `input/brief.json` |
| `source_type` | enum `brief|keywords` | yes | no | none | code | immutable | exact enum | `input/brief.json` |
| `source_hash` | SHA-256 string | yes | no | none | code | immutable | raw source canonical bytes | `input/brief.json` |

## INIT-01 concept

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `core_concept` | string | yes | no | none | LLM, validated by code | candidate | nonempty | INIT-01 candidate |
| `genre_promise` | string | yes | no | none | LLM, validated by code | candidate | nonempty | INIT-01 candidate |
| `reader_experience` | string | yes | no | none | LLM, validated by code | candidate | nonempty | INIT-01 candidate |
| `themes` | array of string | yes | no | none | LLM, validated by code | candidate | nonempty unique strings | INIT-01 candidate |
| `central_conflict` | string | yes | no | none | LLM, validated by code | candidate | nonempty | INIT-01 candidate |
| `ending_direction` | string | yes | no | none | LLM, validated by code | candidate | compatible with brief ending | INIT-01 candidate |
| `tone_constraints` | array of string | yes | no | none | LLM, validated by code | candidate | unique NFC strings | INIT-01 candidate |

## INIT-02 through INIT-04

The following records are each persisted as named candidates before INIT-05; `local_key` is unique across the bundle and only INIT-ID maps it to a persistent ID.

| record | required fields | validation | source of truth |
|---|---|---|---|
| character candidate | `local_key`, `name`, `aliases`, `role`, `core_trait`, `values`, `background`, `immutable_facts`, `appearance_anchor`, `speech_anchor`, `starting_location_local_key`, `starting_physical_condition`, `starting_emotional_state`, `starting_goal`, `starting_pressure` | local key unique; role enum; location local key resolves | INIT-02 candidate |
| relationship candidate | `local_key`, `participant_a_local_key`, `participant_b_local_key`, `relationship_type`, `origin`, `structural_role`, `starting_public_relation`, `a_to_b.trust`, `a_to_b.perception`, `a_to_b.emotional_stance`, `a_to_b.current_intention`, `b_to_a.trust`, `b_to_a.perception`, `b_to_a.emotional_stance`, `b_to_a.current_intention`, `shared_state` | endpoints resolve and differ; relationship and trust enums | INIT-02 candidate |
| world entity candidate | `local_key`, `kind`, `name`, `description`, `immutable_rules`, `sensory_anchors`, `scope` | kind and scope enums; unique local key | INIT-03 candidate |
| temporal rule candidate | `local_key`, `kind`, `description`, `fixed_rule`, `related_local_keys`, `scope` | every related key resolves | INIT-03 candidate |
| protagonist arc | `start`, `turning_points`, `end` | all strings nonempty | INIT-04 candidate |
| relationship arc | `relationship_local_key`, `start_state`, `turning_points`, `end_state`, `change_function` | relationship key resolves | INIT-04 candidate |
| major thread | `local_key`, `description`, `author_truth`, `resolution_condition`, `presentation_rule`, `required` | local key unique; required boolean | INIT-04 candidate |
| ending criterion | `local_key`, `description`, `required`, `source_ending_text` | source ending text equals brief ending | INIT-04 candidate |

INIT-05 emits `initial_design_bundle` with separately named `concept`, `people`, `world`, and `arcs` records. Code verifies Schema, all local-key references, duplicate local keys, required records, and forbidden references before it becomes a reviewable candidate.
