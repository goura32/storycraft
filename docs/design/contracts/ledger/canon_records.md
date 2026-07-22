# Ledger contracts: canon records

`canon/initial-design.json` keeps initial generation history, author long-range plan, author truth, ending criteria, series arcs, and the initial bundle snapshot. `canon/generations/<id>/current-canon.json` keeps adopted fixed Canon records only. It never contains knowledge items or mutable story state. Every saved object rejects unknown fields.

## Common Canon record

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| id | string | yes | no | none | code | immutable | registered prefix | current_canon |
| record_type | enum | yes | no | none | code | immutable | known type | current_canon |
| scope | enum `scene|chapter|volume|series` | yes | no | series | code | transition | scope graph | current_canon |
| record_lifecycle | enum `active|inactive|retired` | yes | no | active | code | transition | valid transition | current_canon |
| created_scene_id | scene ID | yes | yes | null | code | immutable | null at genesis | current_canon |
| references | array<string> | yes | no | [] | code | mutable | known unique IDs | current_canon |

## Character fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| name | string | yes | no | none | LLM→code | initial-only | NFC unique | current_canon |
| aliases | array<string> | yes | no | [] | LLM→code | initial-only | unique strings | current_canon |
| role | role enum | yes | no | none | LLM→code | initial-only | exact enum | current_canon |
| core_trait | string | yes | no | none | LLM→code | initial-only | nonempty | current_canon |
| values | array<string> | yes | no | [] | LLM→code | initial-only | unique strings | current_canon |
| background | string | yes | no | none | LLM→code | initial-only | nonempty | current_canon |
| immutable_facts | array<string> | yes | no | [] | LLM→code | initial-only | unique strings | current_canon |
| appearance_anchor | string | yes | yes | null | LLM→code | initial-only | NFC if set | current_canon |
| speech_anchor | string | yes | yes | null | LLM→code | initial-only | NFC if set | current_canon |

## Relationship fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| participant_a_id | character ID | yes | no | none | code | immutable | known character | current_canon |
| participant_b_id | character ID | yes | no | none | code | immutable | known distinct character | current_canon |
| relationship_type | relationship type enum | yes | no | none | LLM→code | initial-only | exact enum | current_canon |
| origin | string | yes | no | none | LLM→code | initial-only | nonempty | current_canon |
| structural_role | enum `primary|secondary|supporting` | yes | no | supporting | LLM→code | initial-only | exact enum | current_canon |

## World entity fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| name | string | yes | no | none | LLM→code | initial-only | NFC unique by kind | current_canon |
| kind | enum `location|organization|item|system|culture|history` | yes | no | none | code | immutable | prefix matches kind | current_canon |
| description | string | yes | no | none | LLM→code | initial-only | nonempty | current_canon |
| immutable_rules | array<string> | yes | no | [] | LLM→code | initial-only | unique strings | current_canon |
| sensory_anchors | array<string> | yes | no | [] | LLM→code | initial-only | unique strings | current_canon |

## Thread fixed fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| description | string | yes | no | none | LLM→code | initial-only | nonempty | current_canon |
| author_truth | string | yes | no | none | LLM→code | initial-only | nonempty | current_canon |
| resolution_condition | string | yes | no | none | LLM→code | initial-only | nonempty | current_canon |
| importance | enum `major|supporting` | yes | no | major | LLM→code | initial-only | exact enum | current_canon |

## Ending criterion fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| description | string | yes | no | none | LLM→code | initial-only | nonempty | current_canon |
| required | boolean | yes | no | true | LLM→code | initial-only | at least one true | current_canon |

## Knowledge item fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| origin | enum `initial_design|prose` | yes | no | none | code | immutable | exact enum | knowledge_items |
| subject_type | record type enum | yes | no | none | code | immutable | known type | knowledge_items |
| subject_id | record ID | yes | no | none | code | immutable | known record | knowledge_items |
| canonical_fact | string | yes | no | none | LLM→code | immutable | nonempty | knowledge_items |
| writer_visible_label | string | yes | no | none | LLM→code | mutable | set with evidence | knowledge_items |
| scope | scope enum | yes | no | series | code | immutable | valid scope | knowledge_items |
| created_scene_id | scene ID | yes | yes | null | code | immutable | prose requires scene | knowledge_items |
| record_lifecycle | general lifecycle enum | yes | no | active | code | transition | no resolved | knowledge_items |
| author_truth | string | yes | yes | null | code | immutable | non-null iff initial_design | knowledge_items |
