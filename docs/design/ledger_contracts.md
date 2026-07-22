# Ledger contracts

> 台帳・状態・更新の正本。[pipeline contracts](pipeline_contracts.md)が工程I/O、[workspace layout](workspace_layout.md)が保存先を定める。`initial_design_bundle`、`current_canon`、`story_state`、`runtime_state`は別の正本である。

## 四層の正本

| 層 | 正本とする情報 | 保存先 | 禁止する重複 |
|---|---|---|---|
| initial_design_bundle | 固定事実、作者真実、ending criteria、長期arc、初期主要record | `canon/initial-design.json` | 現在感情・進捗 |
| current_canon | recordの固定部分、scope、record_lifecycle、参照関係、採用済み局所Canon | `canon/current-canon.json` | current値、reader知識 |
| story_state | 人物・関係・threadの現在値、knowledge、clock、所有・同行 | `canon/story-state.json` | fixed/作者真実 |
| runtime_state | 工程、対象、checkpoint、counter、停止理由、再開位置、call_id | `runtime/run-state.json`と`runtime/counters.json` | 物語Canon/State |

人物の感情・関係の現在状態・thread進捗は**story_stateだけ**が正本である。`current_canon`のrecordに`current`を持たせない。

## 共通フィールド

| field | 型 | 必須 | 作成者 | 可変性 / operation | evidence | 目安 | 正本 |
|---|---|---:|---|---|---|---|---|
| `id` | string | はい | コード | 不変 | 不要 | prefix+連番 | 各台帳 |
| `type` | enum | はい | LLM候補→コード検証 | 不変 | 不要 | 定義enum | current_canon |
| `scope` | enum | はい | LLM候補→コード | `transition`のみ | 局所変更は必須 | scene/chapter/volume/series | current_canon |
| `record_lifecycle` | enum | はい | コード | `transition`のみ | 局所変更は必須 | active/inactive/retired | current_canon |
| `created_scene_id` | string/null | はい | コード | 不変 | 局所recordは必須 | scene ID | current_canon |
| `fixed` | object | はい | LLM候補→採用 | 初期revisionのみ | 不要 | type別 | initial/current canon |
| `references` | array<string> | 任意 | LLM候補→コード検証 | `append/remove` | 変更時必須 | 0〜50 | current_canon |

`resolved`はrecord_lifecycleではない。threadの完了は`story_state.thread_states[].thread_status`で表す。巻境界の処理は`volume_disposition: resolve|carry_over|retire`であり、carry_overは状態値ではない。

## current_canonのrecord契約

### characters

| field | 型 | 必須 | 作成者 | 可変性 | evidence | 目安 | 正本 |
|---|---|---:|---|---|---|---|---|
| `id,name,aliases,role` | string/array | はい | LLM候補→コード | 不変 | 不要 | aliases 0〜10 | canon |
| `fixed.core_trait,values,background,immutable_facts,appearance_anchor,speech_anchor` | string/array | はい | LLM候補 | 初期revisionのみ | 不要 | 各1〜500字 | initial/canon |
| `scope,record_lifecycle,references` | 共通 | はい | コード | 共通規則 | 変更時必須 | - | canon |

### relationships

| field | 型 | 必須 | 作成者 | 可変性 | evidence | 正本 |
|---|---|---:|---|---|---|---|
| `id,relationship_type` | string/enum | はい | LLM候補→コード | 不変 | 不要 | canon |
| `participant_a_id,participant_b_id` | string | はい | LLM候補→コード | 不変 | 不要 | canon |
| `fixed.origin,structural_role` | string | はい | LLM候補 | 初期revisionのみ | 不要 | initial/canon |

方向値はstory_stateの`relationship_states[id].directions`に保存し、`a_to_b`は必ず`participant_a_id`から`participant_b_id`への状態、`b_to_a`は逆方向を指す。

### world entities / temporal rules

| 台帳 | field | 型 | 必須 | 作成者 | 可変性 | evidence |
|---|---|---|---:|---|---|---|
| world_entities | `kind,name,fixed.description,immutable_rules,sensory_anchors` | enum/string/object | はい | LLM候補→コード | fixedは初期revisionのみ | 不要 |
| temporal_rules | `kind,description,scope,fixed_rule,related_ids` | enum/string/array | はい | LLM候補→コード | rule本体不変 | 不要 |

world entityの可変値（所有者、場所、状態）はstory_stateの`entity_states`に置く。organizationの状態enumは`active|suspended|dissolved`でありrecord_lifecycleと混同しない。

### threads / ending criteria / knowledge items

| 台帳 | field | 型 | 必須 | 作成者 | 可変性 | evidence | 正本 |
|---|---|---|---:|---|---|---|---|
| threads | `thread_type,required,description,author_truth,resolution_condition,presentation_rule` | enum/bool/string | はい | LLM候補→コード | 初期revisionまたは明示replan | 不要 | initial/canon |
| ending_criteria | `description,required,evidence_scope,source_ending_text` | string/bool | はい | LLM候補→コード | 不変 | 不要 | initial/canon |
| knowledge_items | `subject_type,subject_id,description,author_truth,scope,created_scene_id` | enum/string | はい | LLM候補→コード | 本文evidence付き局所追加可 | 追加時必須 | canon |

`knowledge_state.fact_id`は既知のknowledge item IDだけを参照する。`author_truth`はwriter viewへ渡さない。threadに`reader_knowledge_status`は置かない。ending criterion本体にstatusは置かず、supports/contradicts件数と監査assessmentは派生情報である。

## story_stateフィールド契約

| collection.field | 型 | 必須 | 作成者 | 可変性 / operation | evidence | 正本 |
|---|---|---:|---|---|---|---|
| `character_states[id].location_id` | string/null | はい | 初期bundle→コード | set | 必須 | story_state |
| `.physical_condition,.emotional_state,.current_goal,.current_pressure` | string/null | はい | 初期bundle→コード | set | 必須 | story_state |
| `relationship_states[id].directions.a_to_b/b_to_a` | object | はい | 初期bundle→コード | set | 必須 | story_state |
| `.trust,.perception,.emotional_stance,.current_intention` | enum/string | 任意 | LLM候補→コード | set | 必須 | story_state |
| `entity_states[id].owner_id,location_id,condition,organization_state` | string/enum | 任意 | LLM候補→コード | set | 必須 | story_state |
| `thread_states[id].thread_status` | enum | はい | 初期bundle→コード | transition | 必須 | story_state |
| `.progress,.active_pressure` | integer/string | はい/任意 | LLM候補→コード | set | 必須 | story_state |
| `knowledge_state[fact_id,audience].knowledge_status` | enum | はい | LLM候補→コード | transition | 必須 | story_state |
| `story_clock.current_order` | integer | はい | コード | set | 必須 | story_state |
| `.time_label,.parallel_group_id,last_scene_id` | string/null | 任意 | LLM候補/コード | set | clock update時必須 | story_state |

thread statusは`open|in_progress|resolved|retired`、進捗は0〜4で非減少。clockは毎場面採用で必ず`after_order = before_order + 1`。同時刻は`time_label`または`parallel_group_id`で表し、orderは一意に増える。

## continuity delta

| field | 型 | 必須 | 作成者 | 可変性 | evidence | 上限 | 正本 |
|---|---|---:|---|---|---|---:|---|
| `existing_item_updates` | array<object> | はい | LLM候補 | revision可 | 各要素必須 | 0〜50 | story_state |
| `new_item_proposals` | array<object> | はい | LLM候補 | revision可 | 各要素必須 | policy以下 | current_canon |
| `knowledge_item_proposals` | array<object> | はい | LLM候補 | revision可 | 各要素必須 | policy以下 | knowledge_items |
| `knowledge_updates` | array<object> | はい | LLM候補 | revision可 | 各要素必須 | 0〜50 | story_state |
| `thread_updates` | array<object> | はい | LLM候補 | revision可 | 各要素必須 | 0〜20 | story_state |
| `ending_evidence_proposals` | array<object> | はい | LLM候補 | revision可 | 各要素必須 | 0〜20 | evidence index |
| `story_clock_update` | object | はい | LLM候補→コード | revision可 | 必須 | 1 | story_state |
| `handoff_summary` | string | はい | LLM候補 | revision可 | 本文成立事実 | 50〜300字 | artifact |

updateは`operation,target_type,target_id,field,before,after,scene_id,evidence`。許可operationは`set|append|remove|transition`のみ。`before`は採用前stateと一致、`after`は採用後stateと一致、evidenceは凍結本文の完全一致でなければ棄却する。knowledge item proposalは`local_key,subject_type,subject_id,description,author_truth,scope,scene_id,evidence`を必須とし、LLMは永続IDを作らない。

## evidence index

`evidence_type,target_id,scene_id,quote,relation`を必須、`start_offset,end_offset,quote_sha256`を推奨とする。relationは`supports|contradicts`。同一`target_id,scene_id,quote,relation`はappendしない。required criterionは検証済み`supports`が1件以上必要であり、contradictsだけでは達成しない。両方あれば両方をcompletion auditへ渡す。
