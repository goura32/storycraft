# Pipeline contracts

> 工程入出力の正本。台帳は[ledger contracts](ledger_contracts.md)、Contextは[context contracts](context_contracts.md)、runtimeは[runtime and recovery](runtime_and_recovery.md)、保存先は[workspace layout](workspace_layout.md)を正本とする。

## 共通契約

全工程は`operation_id,target_id,input_hash,output_hash,started_at,finished_at`をauditへ保存する。LLM工程はtransport retry、response structure retry、revision roundを分離する。LLM reviewの`critical|major|minor`は停止条件でない。revision上限後は最後の構造正常候補を残存issueと採用する。構造、Schema、ID、hash、evidence、budget、timeout失敗だけが停止条件である。

修正LLMは全issue解消に必要な最小範囲と依存fieldを変更できる。工程責務内でrecord追加・削除・統合を許可するが、無関係な全体再生成はしない。本文修正はscene cardの目的・必須beat・禁止事項を保つ。

各行の入力・出力は`field: 型 / 必須 / 正本 / 目安`、出力状態は`internal|candidate|checkpoint|adopted|audit`である。保存は相対pathで記す。

## 工程カタログ

| ID | 処理・目的 | 実行条件 / 入力 | 出力・状態 | 検証 / 保存 / 失敗時 / 次 |
|---|---|---|---|---|
| INPUT-01 | brief読込 | brief:`object` | brief candidate | [brief fields](#brief) / `input/brief.json` / 構造不正停止 / INPUT-03 |
| INPUT-02 | keywordsからbrief生成 | keywords:`array<string>` 1〜20 | brief candidate | response構造retry / `input/keywords.json` / 枯渇停止 / INPUT-03 |
| INPUT-03 | brief構造検証・採用 | brief candidate | brief adopted、コード付与metadata | 必須・文字数・profile / `input/brief.json` / 停止 / INIT-01 |
| INIT-01 | concept | brief | concept internal | 構造のみ、意味reviewなし / checkpoint / INIT-02 |
| INIT-02 | people・relations | brief,concept | people/relations internal | local_key一意、構造のみ / checkpoint / INIT-03 |
| INIT-03 | world・time | 01-02 | entities/rules internal | local_key参照、構造のみ / checkpoint / INIT-04 |
| INIT-04 | arc・threads・ending | 01-03 | arcs/threads/criteria internal | local_key参照、構造のみ / checkpoint / INIT-05 |
| INIT-05 | bundle統合 | 01-04 | initial bundle candidate、コード | 全local_key / checkpoint / INIT-06 |
| INIT-06 | bundle全体review | bundle candidate | review audit | review型 / `audit/reviews/` / issue→INIT-REV、clean/上限→INIT-ID |
| INIT-REV | bundle一括修正 | candidate,all issues | bundle candidate | Schema / checkpoint / INIT-06 |
| INIT-ID | ID採番・採用 | 構造正常bundle | initial bundle/current canon/story state adopted、コード | ID・参照・hash / `canon/initial-design.json` / 停止 / SERIES-01 |
| SERIES-01 | series map生成 | initial bundle | map candidate | volume fields、章/本文禁止 / `plans/series-map.json` / SERIES-02 |
| SERIES-02 | map review | map candidate | review audit | 型 / issue→SERIES-REV、clean/上限→SERIES-ID |
| SERIES-REV | map一括修正 | map,issues | map candidate | Schema / SERIES-02 |
| SERIES-ID | map採用 | 構造正常map | map adopted | volume番号連番 / `plans/series-map.json` / VOL-01 |
| VOL-01/02/REV/ID | 巻生成・review・修正・採用 | map,current canon,story state,handoff,target volume | volume candidate/review/adopted | 既知thread、番号 / `plans/volumes/vNN/volume-design.json` / CH-01 |
| CH-01/02/REV/ID | 章生成・review・修正・採用 | adopted volume,current canon/state | chapters candidate/review/adopted | chapter連番、`scene_count: integer 1〜20`。採用後不変 / `chapters.json` / SC-01 |
| SC-01/02/REV/CHK | card生成・review・修正・checkpoint | adopted chapter,scene assignment,canon/state | card checkpoint | known ID、new policy / `artifacts/scenes/.../scene-card.json` / PROSE-01 |
| PROSE-01/02/REV/CHK | 本文生成・review・修正・凍結 | adopted card,writer context | prose checkpoint | 非空、card制約、NFC hash / `prose.md` / DELTA-01 |
| DELTA-01/02/REV/CHK | 差分抽出・review・修正・checkpoint | frozen prose,start state,policy | delta checkpoint | before、完全一致evidence、known ID / `continuity-delta.json` / COMMIT-01 |
| COMMIT-01 | 差分機械検証 | card,prose,delta,HEAD generation | prepared commit | Schema、before/after、clock、ID、hash / staging / 停止 / COMMIT-02 |
| COMMIT-02 | ID割当・generation構築 | prepared commit | generation candidate、コード | idempotent mapping / staging / COMMIT-03 |
| COMMIT-03 | scene artifact構築 | generation candidate | artifact candidate | manifest/hash / staging / COMMIT-04 |
| COMMIT-04 | 原子的commit | validated staging | canon/state/index/artifact adopted | generation+HEAD手順 / runtime / 次scene又はVH-01 |
| VH-01/02/REV/ID | handoff生成・review・修正・採用 | adopted volume,current canon/state | handoff candidate/review/adopted | 採用本文由来 / `artifacts/volumes/` / 次VOL又はCOMP-PRE |
| COMP-PRE | 機械的監査前Gate | adopted artifacts,canon,state,index | preflight audit | 全巻/章/scene、prose/hash、required thread、supports、ID / failure停止 / COMP-AUDIT |
| COMP-AUDIT | completion audit | successful preflight | audit candidate | JSON構造不正はattempt再試行、正常1件なしで停止 / COMP-SAVE |
| COMP-SAVE | 正常audit保存 | normal audit | audit record | 最後の正常JSON / `audit/completion/` / COMP-PUBLISH |
| COMP-PUBLISH | 公開前Gate | preflight,normal audit,staging | publish audit | staging検証 / failure停止 / OUT-01 |
| OUT-01/02/03 | staging生成・検証・公開 | adopted artifacts,publish Gate | manuscript/report staging→output | output検証、atomic replace / `output/` / 完了 |

## 主要出力field

### brief

| field | 型 | 必須 | 作成者 |
|---|---|---:|---|
| `title,genre` | string 1〜100 | はい | LLM/input |
| `target_reader` | string 1〜200 | はい | LLM/input |
| `protagonist.name,present_position,core_trait,current_pressure,initial_wish` | string | はい | LLM/input |
| `key_people[]` | array 1〜12 of `{name,present_position,initial_relation_to_protagonist}` | はい | LLM/input |
| `want,ending,editorial_profile_id,publishing_profile_id` | string | はい | LLM/input |
| `avoid` | array<string> 0〜20 | はい | LLM/input |
| `volumes` | integer 4〜10 | はい | LLM/input |
| `brief_version,created_at,source_type,source_hash` | string | はい | コード |

INIT-01 outputは`core_concept,genre_promise,reader_experience,themes,central_conflict,ending_direction,tone_constraints`。INIT-02 peopleは`local_key,name,aliases,role,core_trait,values,background,immutable_facts,appearance_anchor,speech_anchor,starting_location_local_key,starting_physical_condition,starting_emotional_state,starting_goal,starting_pressure`、relationsは`local_key,participant_a_local_key,participant_b_local_key,relationship_type,origin,structural_role,starting_public_relation,a_to_b_trust,a_to_b_perception,a_to_b_emotional_stance,a_to_b_current_intention,b_to_a_trust,b_to_a_perception,b_to_a_emotional_stance,b_to_a_current_intention,shared_state`。INIT-03 entityは`local_key,kind,name,description,immutable_rules,sensory_anchors,scope`、ruleは`local_key,kind,description,fixed_rule,related_local_keys,scope`。INIT-04は`protagonist_arc,relationship_arcs,major_threads,ending_criteria,series_pacing,volume_count`。

series map volumeは`volume_number,volume_role,volume_promise,protagonist_change_target,relationship_change_targets,major_thread_targets,reader_question,ending_position`。volume designは`volume_number,title,volume_promise,starting_state_summary,protagonist_change,relationship_changes,thread_actions,major_conflict,reader_question,ending_function,target_chapter_count`。chapter designは`chapter_number,title,purpose,start_state,end_goal,protagonist_or_relationship_change,thread_actions,scene_count,chapter_end_function`。scene cardは`scene_id,volume_number,chapter_number,scene_number,pov_character_id,participant_ids,location_id,time_relation,time_label,scene_purpose,required_beats,emotional_change_target,relationship_change_target,thread_actions,reader_disclosures,withheld_constraints,allowed_update_targets,new_item_policy,length_guidance,chapter_completion_role`。

reviewは`review_id,target_operation_id,target_id,issues[]`、issueは`code,severity,path,description,evidence,suggested_change`。deltaは`existing_item_updates,new_item_proposals,knowledge_item_proposals,knowledge_updates,thread_updates,ending_evidence_proposals,time_update,handoff_summary`。handoffは`volume_number,narrative_handoff,open_pressures,character_states,relationship_states,carried_threads,story_clock,next_volume_constraints`。completion auditは`audit_attempt,criteria_assessments,thread_assessments,contradictions,residual_issues,overall_assessment`で、criterion assessmentは`criterion_id,supports_evidence_ids,contradicts_evidence_ids,assessment,explanation`。
