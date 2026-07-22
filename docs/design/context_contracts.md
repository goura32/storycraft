# Context contracts

> Context Builderの唯一の正本。field台帳は[ledger contracts](ledger_contracts.md)、operation入力は[pipeline contracts](pipeline_contracts.md)、token設定は[configuration contracts](configuration_contracts.md)を参照する。

## 共通規則

Builderは純粋関数である。同一input snapshot・effective config・operationから同一NFC JSONと`context_hash`を返す。keyはUnicode codepoint昇順、recordはtype→volume→chapter→scene→persistent ID順で並べる。JSON途中切断、Builder内LLM要約、未採用候補の混入は禁止する。

hard token limitは`min(max_context_tokens_by_operation, model_context_window_tokens - reserved_output_tokens_by_operation - protocol_overhead_tokens)`である。provider tokenizerがなければUnicode code point数から`ceil(code_points / 1.5)`を推定tokenとし、provider usageがあれば実測を優先する。必須入力が収まらなければ機械停止する。

## Builder table

| builder | operation | source of truth | required projected fields | forbidden | deterministic overflow exclusion order |
|---|---|---|---|---|---|
| initial design | INIT-01..04 | adopted brief | brief all fields | runtime/audit | 1. none; brief exceeds hard limit = stop |
| series map | SERIES-01 | initial design | concept, records, arcs, threads, ending criteria | runtime/raw responses | 1. retired supporting records 2. sensory anchors 3. non-primary fixed detail |
| volume design | VOL-01 | initial design, series map, HEAD, prior handoff | target map record, current state, prior handoff, unresolved major threads | future volume plan detail, raw prose | 1. retired supporting 2. distant volume supporting 3. sensory anchors 4. non-central dynamic detail |
| chapter design | CH-01 | adopted volume design, HEAD | target volume, current state, assigned thread targets | future chapter/scene artifacts | 1. retired supporting 2. non-target scope 3. sensory anchors 4. non-central detail |
| scene card | SC-01 | adopted chapter, HEAD | target assignment, directly referenced records, state, time floor | author truth unavailable to design? none in author context; raw prose | 1. retired supporting 2. unassigned supporting 3. sensory anchors 4. nonparticipant dynamic detail |
| writer | PROSE-01 | adopted card, HEAD, knowledge state, prior scene handoff | writer view below | author truth, resolution condition, other private knowledge, future detail, unadopted data | 1. sensory anchors 2. nonparticipant visible record 3. nonmajor current detail 4. distant handoff |
| continuity | DELTA-01 | frozen prose, pre-scene HEAD, policy, ID index | full prose, baseline state, allowed targets | author truth, permanent ID allocation | 1. no optional removal; mandatory content overflow = stop |
| volume handoff | VH-01 | scene handoffs, chapter-end state, start/end generation delta, major states, clock, volume evidence | listed input only | full volume prose, unadopted artifacts | 1. retired supporting records 2. resolved supporting thread detail 3. sensory anchors 4. noncentral detail |
| completion audit | COMP-AUDIT | adopted manuscript artifacts, volume handoffs, current canon, story state, evidence index, initial design, series map | criteria, major threads, supports/contradicts evidence, handoffs | publication terminology, raw calls, unadopted content | 1. scene-level supporting detail 2. sensory anchors 3. retired supporting records 4. duplicate summaries |

## Writer knowledge projection

Writer output is an `additionalProperties:false` object. All listed fields are required, non-null, default none, created by code projection, immutable within the call, and source of truth is the Context snapshot.

| field | type | allowed operation | validation |
|---|---|---|---|
| `scene_card` | object | project | adopted card only |
| `pov_character` | object | project | card POV only |
| `visible_characters` | array<object> | project | participant/visible IDs only |
| `visible_relationship_state` | object | project | nested ledger state only |
| `visible_world` | array<object> | project | card-visible records only |
| `known_facts` | array<object> | project | POV status projection matrix |
| `previous_handoff` | object/null | project | immediately prior adopted handoff |
| `style_profile` | object | project | adopted profile |
| `forbidden_disclosures` | array<string> | project | generated from withheld constraints |

For every knowledge item about the POV: `unknown` is omitted; `suspects` emits `{writer_visible_label,status:"suspects"}`; `misunderstands` emits `{writer_visible_label,status:"misunderstands"}` explicitly as misunderstanding; `partially_knows` emits disclosed label and status; `knows` emits label and status. `author_truth` is never emitted. Other character knowledge is never emitted unless the scene card makes its expression directly observable.

## Context audit

Each call audit stores `context_hash,input_snapshot_hash,operation,hard_token_limit,estimated_tokens,provider_input_tokens,excluded_record_ids,overflowed`. `provider_input_tokens` is nullable and is filled only from provider usage. Exclusion order may not be retried or reordered.
