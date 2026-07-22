# Ledger contracts

> 台帳・状態・更新の正本。[pipeline contracts](pipeline_contracts.md)が工程I/O、[製品仕様](../product/SPECIFICATION.md)が製品動作を定める。

## 正本優先関係

| 情報 | 正本 |
|---|---|
| 固定事実、作者真実、ending criteria、長期arc、初期主要record | `initial_design_bundle` |
| 局所Canonと現在有効参照 | `current_canon` |
| 時間・人物等の現在値 | 各台帳recordの`current`、集約は`current_state` |

`current_state`はrecord currentを複写しない。`story_clock`、実行位置、active scene context、有効ID索引だけを持つ。

## 共通record

```json
{"id":"char-0001","type":"character","scope":"series","status":"active","fixed":{},"current":{},"created_scene_id":null}
```

`id`はコード生成・永続・再利用禁止、`type`は定義済みenumで不変、scopeは`scene|chapter|volume|series`、共通statusは`active|inactive|resolved|retired`。fixedは本文差分更新不可、currentは許可fieldのみ更新可。初期recordの`created_scene_id`はnull、局所recordは作成場面ID。全台帳へ同一形を強制せず、clock/indexは例外。

## 台帳

| 台帳 | 最小項目・不変 | 更新可能current / 規則 |
|---|---|---|
| characters | id,name,aliases,role,scope,status; fixed=`core_trait,values,background,immutable_facts,appearance_anchor,speech_anchor` | `location_id,physical_condition,emotional_state,current_goal,current_pressure,active_relationship_summary`。name/fixed不変、locationは既知ID。anchorは一貫性のためfixed。 |
| relationships | id,異なる既知`participant_ids`,relationship_type; fixed=`origin,structural_role` | `a_to_b`,`b_to_a`ごとにtrust/perception/emotional_stance/current_intention、shared_state。trustは`none|low|guarded|moderate|high`。自由一文字列のみで全体管理しない。 |
| world_entities | id,kind=`location|organization|item|system|culture|history`,name; fixed=`description,immutable_rules,sensory_anchors` | location=`availability,controller_id,condition`; item=`owner_id,location_id,condition`; organization=`controller_id,status`。kind外field禁止。 |
| temporal_rules | id,kind=`deadline|travel_duration|recovery_rule|cycle|progression_rule|age_rule`,description,scope,fixed_rule,related_ids | ルール本体不変。残時間はclock/state。 |
| story_clock | `current_order`必須、current_label,current_datetime,calendar_system,last_scene_id | 採用時だけ`after_order>=before_order`。同時刻は同orderとscene順序。checkpointは更新不可。 |
| threads | id,thread_type=`major|supporting`,scope,required,description,author_truth,resolution_condition,presentation_rule | thread固有status=`open|in_progress|resolved|retired`、progress=`0|1|2|3|4`、reader_knowledge_status,active_pressure,volume_disposition。majorは初期設計/計画改訂のみ、supportingはevidence付き追加可。progress減少・resolved再open禁止。 |
| ending_criteria | id,description,required,evidence_scope,source_ending_text,status | 初期設計採用後にID採番、本文差分で追加/変更/削除不可。supports evidence 1件以上がrequired達成。 |
| knowledge_state | fact_id,audience_type,audience_id,status,source_scene_id,evidence | 人物=`unknown|suspects|misunderstands|partially_knows|knows`、reader=`withheld|hinted|partially_revealed|revealed`。author_truthは保持しない。 |
| local_canon | 共通record、type=`character|location|organization|item|supporting_thread|local_fact` | major thread/ending/theme/author truth/fixed world ruleは不可。 |

## lifecycleと巻境界

local/thread recordのstatusは`active|inactive|resolved|retired`（thread固有statusは上表）。`volume_disposition`は別enumの`resolve|carry_over|retire`。resolve→resolved、retire→retired、carry_over→active・scope=series・次巻handoffへ追加。**carry_overはstatusではない**。

## Evidence index

thread、ending criterion、knowledge、state updateを索引化する。必須は`evidence_type,target_id,scene_id,quote,relation`、任意だが推奨は`start_offset,end_offset,quote_sha256`。同一`target_id,scene_id,quote,relation`は重複排除。quoteは本文完全一致。relationは`supports|contradicts`で、required criterionはsupportsだけで達成する。

## 更新規則

自由JSON Patchは禁止。`set|append|remove|transition`だけを許し、target type/fieldごとの許可operation表をSchemaで固定する。existing updateは`before`が現在正本と一致しevidenceが凍結本文一致でなければ棄却。new itemは`new_item_policy.allowed_types`と`max_items`以内で、max_itemsは場面カードの0以上整数、profile上限以下、既定2。コードが重複検出・永続ID採番する。

## Schema作成一覧

| Schema | 種別 | LLM / コード | 正本 |
|---|---|---|---|
| initial_design_bundle | 保存 | 候補 / ID・参照変換 | bundle |
| continuity_delta | 出力 | updates/proposals / 検証・merge | 各台帳 |
| scene_card | 出力 | policy / scene ID | checkpoint |
| completion_audit | 保存 | issue / attempt | audit |
