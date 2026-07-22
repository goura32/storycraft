# Ledger contracts: evidence and updates

This is the sole normative contract for continuity delta. `scene_artifacts.md` links here and does not redefine it. All saved records reject unknown fields. Evidence is a literal adopted-NFC-prose substring; offsets are Unicode code points and `quote_sha256` is SHA-256 of UTF-8 quote bytes.

## Evidence index

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `evidence_id` | evidence ID | yes | no | none | code | immutable | unique | evidence index |
| `evidence_type` | `update|knowledge|ending` | yes | no | none | code | immutable | exact value | evidence index |
| `target_id` | record ID | yes | no | none | code | immutable | adopted target | evidence index |
| `scene_id` | scene ID | yes | no | none | code | immutable | adopted scene | evidence index |
| `quote` | string | yes | no | none | code | immutable | literal prose substring | evidence index |
| `relation` | `supports|contradicts` | yes | no | `supports` | code | immutable | exact value | evidence index |
| `start_offset` | integer | yes | no | none | code | immutable | code-point offset | evidence index |
| `end_offset` | integer | yes | no | none | code | immutable | quote boundary | evidence index |
| `quote_sha256` | SHA-256 | yes | no | none | code | immutable | quote UTF-8 bytes | evidence index |

## Continuity delta

Every row below is candidate data from LLM and validated by code. `scene_id` is copied by code from the stage input. `before` is copied by code from the pre-scene adopted snapshot. Every mutation needs literal prose evidence.

| record | exact fields | allowed operation | evidence requirement |
|---|---|---|---|
| existing item update | `operation`, `target_type`, `target_id`, `field`, `before`, `after`, `scene_id`, `evidence` | `set|append|remove|transition` | literal adopted prose quote |
| new item proposal common | `local_key`, `record_type`, `scope`, `scene_id`, `evidence` | append | literal adopted prose quote |
| knowledge item proposal | `local_key`, `subject_type`, `subject_id`, `canonical_fact`, `writer_visible_label`, `scope`, `scene_id`, `evidence` | append | literal adopted prose quote |
| knowledge update | `fact_id`, `audience_type`, `audience_id`, `before`, `after`, `scene_id`, `evidence` | transition | literal adopted prose quote |
| thread update | `thread_id`, `operation`, `before_status`, `after_status`, `before_progress`, `after_progress`, `scene_id`, `evidence` | `introduce|advance|resolve|retire` | literal adopted prose quote |
| ending evidence proposal | `criterion_id`, `scene_id`, `evidence`, `relation` | append | literal adopted prose quote |
| time update | `time_relation`, `time_label`, `elapsed_hint`, `parallel_group_id`, `evidence` | transition | literal adopted prose quote when changed |

`new_item_proposals` is a discriminated union on `record_type`: `character`, `relationship`, `location`, `organization`, `item`, `system`, `culture`, `history`, or `supporting_thread`. Each branch contains its named record fields; a generic `payload` field is forbidden.

## Residual issue record

When a structurally valid candidate is adopted at the revision limit with remaining issues, code appends one canonical JSON line to `audit/residual-issues.jsonl`.

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `operation_id` | operation ID | yes | no | none | code | immutable | listed review stage | residual issue record |
| `target_id` | target ID | yes | no | none | code | immutable | candidate target | residual issue record |
| `candidate_sha256` | SHA-256 | yes | no | none | code | immutable | retained candidate bytes | residual issue record |
| `revision_rounds_used` | integer | yes | no | none | code | immutable | configured bound reached | residual issue record |
| `issues` | array of review issue record | yes | no | none | code | immutable | nonempty | residual issue record |
| `adopted_at` | RFC3339 timestamp | yes | no | none | code | immutable | UTC | residual issue record |
