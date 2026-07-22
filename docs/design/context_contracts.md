# Context contracts

> Context Builder・秘密投影・overflowの唯一の正本。fieldは[ledger contracts](ledger_contracts.md)、limitは[configuration contracts](configuration_contracts.md)を参照する。

## Determinism and tokens

Builder is a pure projection: identical adopted snapshot, effective config, and operation produce identical NFC JSON and `context_hash`. Keys sort by Unicode code point; records sort type → volume → chapter → scene → persistent ID. No builder calls an LLM, includes unadopted candidate, or cuts a JSON token stream.

A precise provider/tokenizer count is mandatory when available. Otherwise `estimated_tokens = ceil(code_points * fallback_tokens_per_code_point)`, default multiplier 2.0. The hard limit is defined in configuration. If mandatory data does not fit after the stated deterministic exclusions, the operation stops.

## Builder permissions

| builder | operation | adopted source | required projection | forbidden projection | deterministic exclusion order |
|---|---|---|---|---|---|
| initial design | INIT-01..04 | adopted brief | all brief fields | runtime/audit | brief overflow stops |
| series map | SERIES-01 | initial design | concept, records, arcs, threads, criteria | raw calls | retired supporting → sensory anchors → nonprimary fixed detail |
| volume design | VOL-01 | initial design, map, HEAD, prior handoff | target map row, current state, handoff, unresolved major threads | future volume details, raw prose | retired supporting → distant supporting → sensory anchors → noncentral state |
| chapter design | CH-01 | adopted volume, HEAD | target volume, current state, assigned thread targets | future chapters/scenes | retired supporting → non-target scope → sensory anchors → noncentral detail |
| scene card planner | SC-01 | adopted chapter, HEAD, series map | target assignment, records/state/time floor, **author truth**, **resolution condition**, ending author information, future plan only through target scene | raw prose, unadopted candidates | retired supporting → unassigned supporting → sensory anchors → nonparticipant state |
| writer | PROSE-01 | adopted card, HEAD, prior handoff | writer view below | author truth, resolution condition, private other-character knowledge, future scene/volume detail, secret ending content, unadopted candidate | sensory anchors → nonparticipant visible record → nonmajor state → distant handoff |
| continuity | DELTA-01 | frozen prose, pre-scene HEAD, policy | prose, baseline, allowed targets | author truth, permanent ID allocation | no optional removal; mandatory overflow stops |
| volume handoff | VH-01 | adopted scene handoffs, states, generation delta, major state, clock, evidence | enumerated source only | full volume prose, unadopted artifact | retired supporting → resolved supporting thread detail → sensory anchors → noncentral detail |
| completion audit | COMP-AUDIT | adopted manuscripts, handoffs, canon, state, evidence, initial design, map | criteria, major threads, supports/contradicts, handoffs | raw calls, unadopted content | scene supporting detail → sensory anchors → retired supporting → duplicate summaries |

Planner author access exists only to decide what to depict and what not yet to disclose. It must put actual withheld secret text nowhere in the scene card; card uses abstract constraints.

## Writer view

Writer view is `additionalProperties:false`, code-created, immutable for the call, and uses this field table.

All nested projection objects also have `additionalProperties:false`. `scene_card` exposes only `scene_id`, `pov_character_id`, `participant_ids`, `location_id`, `time_relation`, `time_label`, `scene_purpose`, `required_beats`, `thread_actions`, `reader_disclosures`, `withheld_constraints`, `length_guidance`, and `chapter_completion_role`. `pov_character` and `visible_characters[]` expose `id`, `name`, `aliases`, `role`, `appearance_anchor`, and `speech_anchor`. `visible_relationship_state` is an array of `{relationship_id,relationship_type,public_relation}`. `visible_world[]` exposes `{id,kind,name,description,sensory_anchors}`. `known_facts[]` exposes `{fact_id,writer_visible_label,status}` and never `canonical_fact` or `author_truth`. `reader_known_facts[]` exposes `{fact_id,status}` only. `previous_handoff` is the secret-free adopted handoff projection. `style_profile` exposes `{editorial_profile_id,allowed_style_rules}` only. `context_snapshot_metadata` exposes `{generation_id,scene_id,effective_config_hash,context_hash}`. Source artifacts are the adopted card, `canon/HEAD` generation, adopted handoff, effective config, and code-created context snapshot; no field is self-sourced.

| field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `scene_card` | object | yes | no | none | code | immutable | project | adopted card only | context snapshot |
| `pov_character` | object | yes | no | none | code | immutable | project | card POV only | context snapshot |
| `visible_characters` | array of object | yes | no | `[]` | code | immutable | project | participants/visible IDs | context snapshot |
| `visible_relationship_state` | object | yes | no | `{}` | code | immutable | project | nested ledger state only | context snapshot |
| `visible_world` | array of object | yes | no | `[]` | code | immutable | project | card-visible records | context snapshot |
| `known_facts` | array of object | yes | no | `[]` | code | immutable | project | POV knowledge projection | context snapshot |
| `reader_known_facts` | array of object | yes | no | `[]` | code | immutable | project | reader audience rows only | context snapshot |
| `previous_handoff` | object | yes | yes | null | code | immutable | project | immediately prior adopted handoff | context snapshot |
| `style_profile` | object | yes | no | none | code | immutable | project | adopted profile | context snapshot |
| `forbidden_disclosures` | array<string> | yes | no | `[]` | code | immutable | project | abstract labels only | context snapshot |

For the POV: unknown is omitted; suspects emits visible label and status; misunderstands emits visible label and status; partially_knows emits disclosed label and status; knows emits visible label and status. `author_truth` is never projected. Other-character knowledge is absent unless directly observable in the scene card. `reader_known_facts` uses reader audience facts to prevent repeated disclosure. `forbidden_disclosures` only contains abstract labels such as `secret-thread-not-yet-revealable`, `other-character-private-knowledge`, and `future-resolution-detail`, never secret text.

## Context audit

Each call audit stores `context_hash,input_snapshot_hash,operation,hard_token_limit,estimated_tokens,provider_input_tokens,excluded_record_ids,overflowed`. Provider count is nullable and set only from provider usage. Exclusion order cannot be retried or reordered.
