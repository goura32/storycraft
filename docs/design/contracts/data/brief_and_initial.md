# Data contracts: brief and initial

All saved objects reject unknown fields. INIT candidates use local keys only; INIT-ID alone assigns persistent IDs and writes `canon/initial-design.json`.

## Brief

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `title` | string | yes | no | none | user/LLM→code | immutable | NFC nonempty | input/brief.json |
| `genre` | string | yes | no | none | user/LLM→code | immutable | NFC nonempty | input/brief.json |
| `target_reader` | string | yes | no | none | user/LLM→code | immutable | NFC nonempty | input/brief.json |
| `protagonist.name` | string | yes | no | none | user/LLM→code | immutable | NFC nonempty | input/brief.json |
| `protagonist.present_position` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `protagonist.core_trait` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `protagonist.current_pressure` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `protagonist.initial_wish` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `key_people` | array of key person | yes | no | [] | user/LLM→code | immutable | unique names | input/brief.json |
| `key_people[].name` | string | yes | no | none | user/LLM→code | immutable | NFC nonempty | input/brief.json |
| `key_people[].present_position` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `key_people[].initial_relation_to_protagonist` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `want` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `avoid` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `ending` | string | yes | no | none | user/LLM→code | immutable | nonempty | input/brief.json |
| `volumes` | integer | yes | no | none | user/LLM→code | immutable | >=1 | input/brief.json |
| `editorial_profile_id` | string | yes | no | none | user/LLM→code | immutable | known config profile | input/brief.json |
| `publishing_profile_id` | string | yes | no | none | user/LLM→code | immutable | known config profile | input/brief.json |
| `brief_version` | integer | yes | no | 1 | code | immutable | >=1 | input/brief.json |
| `created_at` | RFC3339 timestamp | yes | no | none | code | immutable | UTC | input/brief.json |
| `source_type` | enum `brief|keywords` | yes | no | none | code | immutable | exact enum | input/brief.json |
| `source_hash` | SHA-256 string | yes | no | none | code | immutable | canonical input bytes | input/brief.json |

## INIT outputs and initial_design_bundle

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `concept.logline` | string | yes | no | none | LLM→code | candidate | brief compatibility | initial candidate |
| `concept.theme` | string | yes | no | none | LLM→code | candidate | nonempty | initial candidate |
| `character_candidates[].local_key` | string | yes | no | none | LLM | candidate | unique local key | initial candidate |
| `character_candidates[].name` | string | yes | no | none | LLM | candidate | NFC nonempty | initial candidate |
| `relationship_candidates[].local_key` | string | yes | no | none | LLM | candidate | unique local key | initial candidate |
| `relationship_candidates[].participant_a_local_key` | string | yes | no | none | LLM | candidate | known distinct character key | initial candidate |
| `relationship_candidates[].participant_b_local_key` | string | yes | no | none | LLM | candidate | known distinct character key | initial candidate |
| `world_entity_candidates[].local_key` | string | yes | no | none | LLM | candidate | unique local key | initial candidate |
| `world_entity_candidates[].kind` | world kind enum | yes | no | none | LLM | candidate | exact enum | initial candidate |
| `temporal_rule_candidates[].local_key` | string | yes | no | none | LLM | candidate | unique local key | initial candidate |
| `protagonist_arc.start` | string | yes | no | none | LLM | candidate | nonempty | initial candidate |
| `protagonist_arc.end` | string | yes | no | none | LLM | candidate | nonempty | initial candidate |
| `relationship_arcs[].relationship_local_key` | string | yes | no | none | LLM | candidate | known relationship key | initial candidate |
| `major_threads[].local_key` | string | yes | no | none | LLM | candidate | unique local key | initial candidate |
| `major_threads[].author_truth` | string | yes | no | none | LLM | candidate | nonempty | initial candidate |
| `major_threads[].resolution_condition` | string | yes | no | none | LLM | candidate | nonempty | initial candidate |
| `ending_criteria[].local_key` | string | yes | no | none | LLM | candidate | unique local key | initial candidate |
| `ending_criteria[].required` | boolean | yes | no | true | LLM | candidate | required ending exists | initial candidate |
| `initial_design_bundle.concept` | concept | yes | no | none | code | candidate | all INIT sections | runtime candidate |
| `initial_design_bundle.people` | initial people | yes | no | none | code | candidate | local refs resolve | runtime candidate |
| `initial_design_bundle.world` | initial world | yes | no | none | code | candidate | local refs resolve | runtime candidate |
| `initial_design_bundle.arcs` | initial arcs | yes | no | none | code | candidate | ending exists | runtime candidate |
