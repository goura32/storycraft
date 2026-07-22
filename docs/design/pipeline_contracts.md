# Pipeline contracts

> 工程契約の唯一の正本。台帳は[ledger contracts](ledger_contracts.md)、Contextは[context contracts](context_contracts.md)、runtimeは[runtime and recovery](runtime_and_recovery.md)、保存pathは[workspace layout](workspace_layout.md)を参照する。

## 共通実行契約

各LLM工程はcandidate→review→revision→structure checkの順で動く。transport retryは通信・timeoutだけ、response structure retryはJSON/Schemaだけ、revision roundはreview issueだけに使う。review severityは停止条件でない。revision枯渇時は最後の構造正常candidateをresidual issue付きで採用する。ID、Schema、参照、hash、evidence、budget、timeoutの失敗だけが機械停止である。

各工程auditは`operation_id,target_id,input_hash,output_hash,started_at,finished_at`を保存する。表の「LLM」はLLM生成field、「code」はコード付与fieldであり、書かれていないfieldは出力禁止である。

## 製品フロー

`INPUT → INIT → SERIES → VOL → CH → SC → PROSE → DELTA → COMMIT → VH → COMP → OUT`。

## Initial design and series map fields

全表のobjectは`additionalProperties: false`。ここでの`local_key`はINIT内参照専用であり、INIT-IDでコードが永続IDへ一括変換する。

| output / field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| INIT-01 `title` | string | yes | no | none | LLM | revision | replace | 1..100 chars | candidate |
| INIT-01 `core_concept` | string | yes | no | none | LLM | revision | replace | non-empty | candidate |
| INIT-01 `genre_promise` | string | yes | no | none | LLM | revision | replace | non-empty | candidate |
| INIT-01 `central_conflict` | string | yes | no | none | LLM | revision | replace | non-empty | candidate |
| INIT-01 `ending_direction` | string | yes | no | none | LLM | revision | replace | non-empty | candidate |
| INIT-02 character `local_key` | string | yes | no | none | LLM | revision | replace | unique local key | candidate |
| INIT-02 character `name` | string | yes | no | none | LLM | revision | replace | non-empty | candidate |
| INIT-02 character `role` | character role enum | yes | no | none | LLM | revision | replace | enum | candidate |
| INIT-02 character `fixed` | object | yes | no | none | LLM | revision | replace | character fixed schema | candidate |
| INIT-02 character `initial_state` | object | yes | no | none | LLM | revision | replace | state schema | candidate |
| INIT-02 relationship `local_key` | string | yes | no | none | LLM | revision | replace | unique | candidate |
| INIT-02 relationship `participant_a_local_key` | string | yes | no | none | LLM | revision | replace | known character key | candidate |
| INIT-02 relationship `participant_b_local_key` | string | yes | no | none | LLM | revision | replace | different known key | candidate |
| INIT-02 relationship `relationship_type` | enum | yes | no | none | LLM | revision | replace | relationship enum | candidate |
| INIT-02 relationship `structural_role` | enum | yes | no | `supporting` | LLM | revision | replace | structural enum | candidate |
| INIT-02 relationship `initial_state` | nested relationship state | yes | no | none | LLM | revision | replace | ledger relationship schema | candidate |
| INIT-03 entity `local_key` | string | yes | no | none | LLM | revision | replace | unique | candidate |
| INIT-03 entity `kind` | world entity kind enum | yes | no | none | LLM | revision | replace | enum | candidate |
| INIT-03 entity `name,fixed,scope` | string/object/enum | yes | no | none | LLM | revision | replace | entity schema | candidate |
| INIT-03 rule `local_key` | string | yes | no | none | LLM | revision | replace | unique | candidate |
| INIT-03 rule `kind` | temporal rule kind enum | yes | no | none | LLM | revision | replace | enum | candidate |
| INIT-03 rule `description,fixed_rule,related_local_keys,scope` | string/string/array/enum | yes | no | none | LLM | revision | replace | rule schema | candidate |
| INIT-04 protagonist arc `start,turn,end` | string/string/string | yes | no | none | LLM | revision | replace | non-empty | candidate |
| INIT-04 relationship arc `relationship_local_key,start,turn,end` | string/string/string/string | yes | no | none | LLM | revision | replace | known relation key | candidate |
| INIT-04 major thread `local_key,description,author_truth,resolution_condition,presentation_rule` | string | yes | no | none | LLM | revision | replace | non-empty | candidate |
| INIT-04 ending criterion `local_key,description,required,evidence_scope` | string/bool/enum | yes | no | none | LLM | revision | replace | required boolean | candidate |
| series map `volume_number` | integer | yes | no | none | LLM→code | immutable after adopt | none | 1..brief.volumes, continuous | series map |
| series map `volume_role` | enum | yes | no | none | LLM | immutable after adopt | none | `entry|development|escalation|turning_point|climax|resolution` | series map |
| series map `volume_promise` | string | yes | no | none | LLM | immutable after adopt | none | non-empty | series map |
| series map `protagonist_change_target` | string | yes | no | none | LLM | immutable after adopt | none | non-empty | series map |
| series map `relationship_change_targets` | array<object> | yes | no | `[]` | LLM | immutable after adopt | none | known relation local/persistent ID | series map |
| series map `major_thread_targets` | array<object> | yes | no | `[]` | LLM | immutable after adopt | none | major thread only | series map |
| series map `reader_question` | string | yes | no | none | LLM | immutable after adopt | none | non-empty | series map |
| series map `ending_position` | enum | yes | no | none | LLM | immutable after adopt | none | `opening|early|middle|late|final` | series map |

Series map has no chapter or scene detail; every volume number is unique and consecutive; count equals `brief.volumes`; v1 never replans an adopted map.

## Individual operation contract

All rows define: objective; condition/input/source; output/state; LLM/code fields; forbidden references; mechanical validation; review; retry/revision; adoption; storage; failure; next.

| ID | contract |
|---|---|
| VOL-01 | **目的**巻design candidate。**条件/入力/正本**adopted series map、HEAD canon/state、prior adopted handoff。**出力/state**volume candidate。**LLM**`volume_number,title,volume_promise,starting_state_summary,protagonist_change,relationship_changes,thread_actions,major_conflict,reader_question,ending_function,target_chapter_count`。**code**operation metadata。**禁止**future volume detailと未採用本文。**検証**target number、known IDs、series target適合。**review**約束・thread配分・状態開始。**retry/revision**structure/revision。**採用**VOL-IDのみ。**保存**`plans/volumes/vNN/candidate.json`。**失敗**枯渇停止。**次**VOL-02。 |
| VOL-02 | **目的**volume review。**条件/入力/正本**VOL-01 candidate。**出力/state**review audit。**LLM**review result。**code**review ID。**禁止**candidate外の新事実。**検証**review schema。**review**volume promise、map適合。**retry/revision**structure; issueならVOL-REV。**採用**なし。**保存**`audit/reviews/`。**失敗**structure枯渇停止。**次**VOL-REVまたはVOL-ID。 |
| VOL-REV | **目的**volume修正。**条件**structure正常candidateとissues。**出力**candidate。**LLM**VOL-01 fieldのみ。**code**round。**禁止**map変更。**検証**VOL-01。**review**再実行。**retry/revision**revision round消費。**採用**なし。**保存**candidate revision。**失敗**最後の構造正常候補へ。**次**VOL-02。 |
| VOL-ID | **目的**volume採用。**条件**structure正常candidate。**入力正本**candidate/map/HEAD。**出力**adopted design。**LLM**なし。**code**hash/adopted metadata。**禁止**内容変更。**検証**hash/IDs/map。**retry**なし。**採用**原子的。**保存**`plans/volumes/vNN/volume-design.json`。**失敗**停止。**次**CH-01。 |
| CH-01 | **目的**chapter candidate。**条件/正本**adopted volume+HEAD。**出力**chapter list candidate。**LLM**`chapter_number,title,purpose,start_state,end_goal,protagonist_or_relationship_change,thread_actions,scene_count,chapter_completion_role`。**code**metadata。**禁止**scene detail。**検証**1..target count、scene_count 1..20、known IDs。**review**volume配分。**retry/revision**structure/revision。**採用**CH-ID。**保存**`plans/volumes/vNN/chapters-candidate.json`。**失敗**停止。**次**CH-02。 |
| CH-02 | **目的**chapter review。**入力**CH-01。**出力**review。**LLM**review result。**code**review ID。**禁止**新章。**検証**review schema。**review**順序、thread、ending role。**retry/revision**structure/revision。**採用**なし。**保存**audit。**失敗**停止。**次**CH-REV/CH-ID。 |
| CH-REV | **目的**chapter修正。**入力**candidate/issues。**出力**candidate。**LLM**CH-01 field。**code**round。**禁止**adopted volume変更。**検証**CH-01。**review**CH-02。**retry/revision**round消費。**採用**なし。**保存**revision。**失敗**最後の構造正常候補。**次**CH-02。 |
| CH-ID | **目的**chapter採用。**入力**candidate。**出力**adopted chapters。**LLM**なし。**code**hash。**禁止**scene_count変更。**検証**chapter連番。**retry**なし。**採用**atomic。**保存**`plans/volumes/vNN/chapters.json`。**失敗**停止。**次**SC-01。 |
| SC-01 | **目的**scene card candidate。**入力正本**adopted chapter、HEAD、scene assignment。**出力**card candidate。**LLM**`scene_id,volume_number,chapter_number,scene_number,pov_character_id,participant_ids,location_id,time_relation,time_label,scene_purpose,required_beats,emotional_change_target,relationship_change_target,thread_actions,reader_disclosures,withheld_constraints,allowed_update_targets,new_item_policy,length_guidance,chapter_completion_role`。**code**scene ID。**禁止**author truth、未知knowledge。**検証**known IDs/policy/assignment。**review**POV・開示・thread。**retry/revision**structure/revision。**採用**SC-CHK。**保存**scene artifact candidate。**失敗**停止。**次**SC-02。 |
| SC-02 | **目的**card review。**入力**SC candidate。**出力**review。**LLM**review result。**禁止**本文。**検証**review schema。**review**card contract。**retry/revision**structure/revision。**採用**なし。**保存**audit。**失敗**停止。**次**SC-REV/SC-CHK。 |
| SC-REV | **目的**card修正。**入力**candidate/issues。**出力**candidate。**LLM**SC-01 fields。**code**round。**禁止**chapter/volume採用物変更。**検証**SC-01。**review**SC-02。**retry/revision**round消費。**採用**なし。**保存**revision。**失敗**last structure-valid。**次**SC-02。 |
| SC-CHK | **目的**card checkpoint。**入力**structure正常card。**出力/state**CARD_ACCEPTED。**LLM**なし。**code**NFC hash/checkpoint。**検証**schema/ID。**採用**checkpointのみ。**保存**`artifacts/scenes/vNN/cNN/sNN/scene-card.json`。**失敗**停止。**次**PROSE-01。 |
| PROSE-01 | **目的**本文candidate。**入力正本**adopted cardとwriter context。**出力**prose candidate。**LLM**`manuscript_text`。**code**metadata。**禁止**writer context外秘密。**検証**non-empty/NFC/card rules。**review**POV/自然文/beat。**retry/revision**structure/revision。**採用**PROSE-CHK。**保存**artifact。**失敗**停止。**次**PROSE-02。 |
| PROSE-02 | **目的**本文review。**入力**prose/card。**出力**review。**LLM**review result。**禁止**新canon。**検証**review schema。**review**card保全。**retry/revision**structure/revision。**採用**なし。**保存**audit。**失敗**停止。**次**PROSE-REV/CHK。 |
| PROSE-REV | **目的**本文修正。**入力**prose/issues/card。**出力**prose。**LLM**manuscript text。**禁止**card外変更。**検証**PROSE-01。**review**PROSE-02。**retry/revision**round消費。**採用**なし。**保存**revision。**失敗**last structure-valid。**次**PROSE-02。 |
| PROSE-CHK | **目的**本文凍結。**入力**structure正常prose。**出力/state**PROSE_FROZEN。**code**NFC SHA-256。**検証**hash/nonempty。**保存**`prose.md`。**失敗**停止。**次**DELTA-01。 |
| DELTA-01 | **目的**continuity candidate。**入力正本**frozen prose、開始HEAD snapshot、policy。**出力**delta candidate。**LLM**`existing_item_updates,new_item_proposals,knowledge_item_proposals,knowledge_updates,thread_updates,ending_evidence_proposals,time_update,handoff_summary`。**code**none。**禁止**永続ID/author truth/clock order。**検証**before/quote/known ID。**review**state整合。**retry/revision**structure/revision。**採用**DELTA-CHK。**保存**artifact。**失敗**停止。**次**DELTA-02。 |
| DELTA-02 | **目的**delta review。**入力**delta/prose。**出力**review。**LLM**review result。**禁止**本文修正。**検証**review schema。**review**evidence意味。**retry/revision**structure/revision。**採用**なし。**保存**audit。**失敗**停止。**次**DELTA-REV/CHK。 |
| DELTA-REV | **目的**delta修正。**入力**delta/issues/prose。**出力**delta。**LLM**DELTA-01 fields。**禁止**本文/author truth。**検証**DELTA-01。**review**DELTA-02。**retry/revision**round消費。**採用**なし。**保存**revision。**失敗**last structure-valid。**次**DELTA-02。 |
| DELTA-CHK | **目的**delta checkpoint。**入力**structure正常delta。**出力/state**DELTA_ACCEPTED。**code**hash。**検証**evidence exact/before。**保存**`continuity-delta.json`。**失敗**停止。**次**COMMIT-01。 |
| VH-01 | **目的**handoff candidate。**入力正本**当該巻scene handoff、章末state、巻開始/終了generation差分、主要人物/中心関係/thread actions/clock/evidence index。**出力**handoff candidate。**LLM**`volume_number,narrative_handoff,open_pressures,character_states,relationship_states,carried_threads,story_clock,next_volume_constraints`。**禁止**巻本文全文、未採用artifact。**検証**known IDs。**review**次巻に必要な状態。**retry/revision**structure/revision。**採用**VH-ID。**保存**volume artifacts。**失敗**停止。**次**VH-02。 |
| VH-02 | **目的**handoff review。**入力**VH candidate。**出力**review。**LLM**review result。**禁止**本文全文。**検証**review schema。**review**state/evidence。**retry/revision**structure/revision。**採用**なし。**保存**audit。**失敗**停止。**次**VH-REV/VH-ID。 |
| VH-REV | **目的**handoff修正。**入力**candidate/issues。**出力**candidate。**LLM**VH-01 fields。**code**round。**禁止**canon/state変更。**検証**VH-01。**review**VH-02。**retry/revision**round消費。**採用**なし。**保存**revision。**失敗**last structure-valid。**次**VH-02。 |
| VH-ID | **目的**handoff採用。**入力**candidate。**出力**adopted handoff。**code**hash。**検証**schema/IDs。**採用**atomic。**保存**`artifacts/volumes/vNN/handoff.json`。**失敗**停止。**次**next VOL-01 / COMP-PRE。 |
| OUT-01 | **目的**publication staging。**入力正本**adopted manuscript artifacts、handoffs、current canon、story state、evidence index、initial design、series map。**出力**staging Markdown/report/metadata。**LLM**なし。**code**renderer。**禁止**audit raw/prompt/author truth。**検証**order/nonempty/no secret。**保存**`.staging/publication`。**失敗**停止。**次**OUT-02。 |
| OUT-02 | **目的**output検証。**入力**staging。**出力**validation result。**code**hash/Markdown checks。**禁止**変更。**検証**all output rules。**retry**なし。**採用**なし。**保存**staging manifest。**失敗**停止、CURRENT不変。**次**OUT-03。 |
| OUT-03 | **目的**pointer公開。**入力**validated staging。**出力**publication adopted。**code**publication ID/CURRENT。**検証**rename then pointer atomic replace。**採用**publication pointer。**保存**`publications/<id>/`, `output/CURRENT`。**失敗**old pointer維持。**次**complete。 |

## Review and completion field contracts

| output / field | type | required | nullable | default | creator | mutability | allowed operation | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| review `review_id,target_operation_id,target_id` | string | yes | no | none | code | immutable | none | known operation/target | audit |
| review issue `code,severity,path,description,evidence,suggested_change` | string/enum | yes | no | none | LLM | immutable | none | severity `critical|major|minor` | audit |
| volume handoff `volume_number` | integer | yes | no | none | LLM→code | immutable | none | adopted volume | artifact |
| volume handoff `narrative_handoff` | string | yes | no | none | LLM | immutable | none | adopted facts only | artifact |
| volume handoff `open_pressures,character_states,relationship_states,carried_threads,story_clock,next_volume_constraints` | object/array | yes | no | none | LLM→code | immutable | none | state/ID matching | artifact |
| completion audit `audit_attempt` | integer | yes | no | none | code | immutable | none | 1..max | audit |
| completion audit `criteria_assessments,thread_assessments,contradictions,residual_issues` | array | yes | no | `[]` | LLM | immutable | none | audit schema | audit |
| completion audit `overall_assessment` | enum | yes | no | none | LLM | immutable | none | `pass|pass_with_issues|fail` | audit |
