# Ledger contracts: evidence and updates

All update operations are code-validated. Free JSON Patch is forbidden. Evidence quote must be a literal substring of adopted NFC prose; offsets are Unicode code point positions and `quote_sha256` hashes UTF-8 quote bytes.

## Evidence index

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| evidence_id | evidence ID | yes | no | none | code | immutable | unique prefix | evidence_index |
| evidence_type | enum `update|knowledge|ending` | yes | no | none | code | immutable | exact enum | evidence_index |
| target_id | record ID | yes | no | none | code | immutable | known target | evidence_index |
| scene_id | scene ID | yes | no | none | code | immutable | adopted scene | evidence_index |
| quote | string | yes | no | none | code | immutable | literal prose substring | evidence_index |
| relation | enum `supports|contradicts` | yes | no | supports | code | immutable | exact enum | evidence_index |
| start_offset | integer | yes | no | none | code | immutable | Unicode code point offset | evidence_index |
| end_offset | integer | yes | no | none | code | immutable | quote boundary | evidence_index |
| quote_sha256 | SHA-256 string | yes | no | none | code | immutable | UTF-8 quote hash | evidence_index |

## Continuity update

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| operation | enum `set|append|remove|transition` | yes | no | none | LLM→code | candidate | allowed target field | evidence required | target matrix | delta |
| target_id | record ID | yes | no | none | code | candidate | known adopted record | evidence required | target matrix | delta |
| field | string | yes | no | none | LLM→code | candidate | allowed direct field | evidence required | target matrix | delta |
| before | typed value | yes | yes | null | code | candidate | equals current snapshot | evidence required | target matrix | delta |
| after | typed value | yes | yes | null | LLM→code | candidate | field Schema | evidence required | target matrix | delta |
| evidence | string | yes | no | none | LLM→code | candidate | literal prose quote | required | delta |

## New item proposal

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| record_type | record type enum | yes | no | none | LLM→code | candidate | allowed scene policy | candidate only | delta |
| local_key | string | yes | no | none | LLM | candidate | unique in commit | candidate only | delta |
| scope | scope enum | yes | no | none | LLM→code | candidate | policy allows scope | candidate only | delta |
| payload | typed record fields | yes | no | none | LLM→code | candidate | record Schema | candidate only | delta |
