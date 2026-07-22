# Pipeline contracts: commit and output

`COMP-PUBLISH` is a code gate after `OUT-02`; it writes only a gate audit and permits `OUT-03`, not a staged or adopted artifact.

## COMMIT-01 — scene commit検証

| contract | value |
|---|---|
| processor type | code |
| execution precondition | SC-CHK PROSE-CHK DELTA-CHK exist |
| input artifact names | three checkpoints and HEAD snapshots |
| input source paths | `runtime/checkpoints/scenes/v01/c001/s001; canon/HEAD generation` |
| output artifact name | validated commit plan |
| output Schema name | `commit-plan.schema.json` |
| artifact class | checkpoint |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | all checkpoint hashes, updates, IDs, evidence |
| adoption condition | SC-CHK PROSE-CHK DELTA-CHK exist |
| candidate path | `none` |
| adopted path | `runtime/checkpoints/scenes/v01/c001/s001/commit-plan.json` |
| audit path | `audit/operations/commit-01.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | COMMIT-02 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## COMMIT-02 — next generation作成

| contract | value |
|---|---|
| processor type | code |
| execution precondition | COMMIT-01 plan valid |
| input artifact names | validated commit plan and HEAD generation |
| input source paths | `runtime/checkpoints/scenes/v01/c001/s001/commit-plan.json; canon/HEAD generation` |
| output artifact name | staged generation |
| output Schema name | `generation.schema.json` |
| artifact class | staged_internal |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | copy-on-write schema/hash/evidence index |
| adoption condition | COMMIT-01 plan valid |
| candidate path | `none` |
| adopted path | `.staging/scene-commits/v01-c001-s001/generation` |
| audit path | `audit/operations/commit-02.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | COMMIT-03 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## COMMIT-03 — scene artifact作成

| contract | value |
|---|---|
| processor type | code |
| execution precondition | COMMIT-02 staged generation valid |
| input artifact names | validated plan and checkpoints |
| input source paths | `runtime/checkpoints/scenes/v01/c001/s001` |
| output artifact name | staged scene artifact |
| output Schema name | `scene-manifest.schema.json` |
| artifact class | staged_internal |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | artifact paths/NFC prose/fixed hashes |
| adoption condition | COMMIT-02 staged generation valid |
| candidate path | `none` |
| adopted path | `.staging/scene-commits/v01-c001-s001/artifact` |
| audit path | `audit/operations/commit-03.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | COMMIT-04 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## COMMIT-04 — HEAD更新・場面採用

| contract | value |
|---|---|
| processor type | code |
| execution precondition | COMMIT-02 and COMMIT-03 valid |
| input artifact names | staged generation and artifact |
| input source paths | ` .staging/scene-commits/v01-c001-s001/{generation,artifact}` |
| output artifact name | adopted generation and scene artifact |
| output Schema name | `commit-manifest.schema.json` |
| artifact class | adopted |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | atomic renames then HEAD last |
| adoption condition | COMMIT-02 and COMMIT-03 valid |
| candidate path | `none` |
| adopted path | `canon/generations/<new-generation>; artifacts/scenes/v01/c001/s001; canon/HEAD` |
| audit path | `audit/operations/commit-04.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | SC-01 or VH-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## VH-01 — volume handoff生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | last scene of volume committed |
| input artifact names | adopted volume scenes and HEAD snapshots |
| input source paths | `artifacts/scenes/v01/**; canon/HEAD generation` |
| output artifact name | handoff candidate |
| output Schema name | `volume-handoff.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | adopted-only facts/Schema |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/handoffs/v01/candidate.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/vh-01.json.gz` |
| resume source | `runtime/candidates/handoffs/v01/candidate-manifest.json` (manifest-selected payload only) |
| next stage | VH-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## VH-02 — volume handoff review

| contract | value |
|---|---|
| processor type | LLM review |
| execution precondition | VH-01 candidate exists |
| input artifact names | handoff candidate |
| input source paths | `runtime/candidates/handoffs/v01/candidate.json` |
| output artifact name | review_result |
| output Schema name | `review-result.schema.json` |
| artifact class | review candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | review Schema/adopted facts only |
| adoption condition | not adopted; review only |
| candidate path | `runtime/candidates/handoffs/v01/review.json` |
| adopted path | `none` |
| audit path | `audit/reviews/vh-02.json.gz` |
| resume source | `runtime/candidates/handoffs/v01/candidate-manifest.json` (manifest-selected payload only) |
| next stage | VH-REV or VH-ID |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | `review_result` only |

## VH-REV — volume handoff revise

| contract | value |
|---|---|
| processor type | LLM revise |
| execution precondition | VH-02 issues and revision budget remain |
| input artifact names | last valid handoff, review, current state |
| input source paths | `runtime/candidates/handoffs/v01/{candidate,review}.json; canon/HEAD generation` |
| output artifact name | revised handoff |
| output Schema name | `volume-handoff.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | Yes |
| mechanical validation | whole handoff Schema/adopted facts |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/handoffs/v01/candidate.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/vh-rev.json.gz` |
| resume source | `runtime/candidates/handoffs/v01/candidate-manifest.json` (manifest-selected payload only) |
| next stage | VH-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## VH-ID — volume handoff採用

| contract | value |
|---|---|
| processor type | code |
| execution precondition | VH-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| input artifact names | latest structurally valid handoff |
| input source paths | `runtime/candidates/handoffs/v01/{candidate,review}.json` |
| output artifact name | adopted handoff |
| output Schema name | `volume-handoff.schema.json` |
| artifact class | adopted |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | Schema/volume/current HEAD; append residual issues when needed |
| adoption condition | VH-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| candidate path | `none` |
| adopted path | `artifacts/handoffs/v01.json` |
| audit path | `audit/operations/vh-id.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | VOL-01 or COMP-PRE |
| failure classification | storage error or mechanical stop |
| review output | なし |

## Volume handoff field contract

`volume-handoff.schema.json` objects and every child object use `additionalProperties:false`. The candidate has the following required fields: `volume_number`, `ending_state_summary`, `unresolved_threads`, `resolved_threads`, `character_state_summaries`, `relationship_state_summaries`, `world_state_summary`, `story_clock`, `evidence_refs`, `next_volume_constraints`, `residual_issues`. `unresolved_threads[]` and `resolved_threads[]` each expose `{thread_id,status,progress,disposition,evidence_ids}`; `disposition` is `resolve|carry_over|retire`, `status` is the registered `thread_status`, and every evidence ID resolves to adopted evidence. `character_state_summaries[]` exposes `{character_id,public_state,knowledge_fact_ids}`; `relationship_state_summaries[]` exposes `{relationship_id,public_relation}`; `story_clock` exposes `{time_label,current_order,last_scene_id}`. `next_volume_constraints[]` are abstract non-secret constraints only. The LLM may populate candidate values from the enumerated adopted projection; code validates all IDs, statuses, evidence, and schema, and only VH-ID persists `artifacts/handoffs/vNN.json`.

## COMP-PRE — completion前提検証

| contract | value |
|---|---|
| processor type | code |
| execution precondition | last volume handoff adopted |
| input artifact names | all adopted volumes, HEAD, evidence |
| input source paths | `plans/series-map.json; artifacts/handoffs; canon/HEAD generation` |
| output artifact name | completion precheck |
| output Schema name | `completion-precheck.schema.json` |
| artifact class | checkpoint |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | required ending supports evidence/complete map |
| adoption condition | last volume handoff adopted |
| candidate path | `none` |
| adopted path | `runtime/checkpoints/completion/precheck.json` |
| audit path | `audit/operations/comp-pre.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | COMP-AUDIT |
| failure classification | storage error or mechanical stop |
| review output | なし |

## COMP-AUDIT — completion audit

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | COMP-PRE precheck valid |
| input artifact names | precheck, adopted prose, Canon, state, evidence |
| input source paths | `runtime/checkpoints/completion/precheck.json; artifacts/scenes; canon/HEAD generation` |
| output artifact name | completion audit result |
| output Schema name | `completion-audit.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | audit Schema only; no revision |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/completion/attempt-NN.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/000123__comp-audit__completion__generate__attempt-NN.json.gz` |
| resume source | `runtime/candidates/completion/candidate-manifest.json` |
| next stage | COMP-SAVE when structurally valid; COMP-AUDIT next attempt or mechanical stop otherwise |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## COMP-SAVE — completion audit保存

| contract | value |
|---|---|
| processor type | code |
| execution precondition | latest structurally valid completion audit exists |
| input artifact names | structurally valid audit candidate |
| input source paths | `runtime/candidates/completion/attempt-NN.json` selected by manifest |
| output artifact name | saved completion audit |
| output Schema name | `completion-audit.schema.json` |
| artifact class | audit |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | Schema/hash/sanitize public projection |
| adoption condition | latest structurally valid completion audit exists |
| candidate path | `none` |
| adopted path | `audit/completion/audit.json.gz` |
| audit path | `audit/operations/comp-save.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | OUT-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## OUT-01 — publication staging

| contract | value |
|---|---|
| processor type | code |
| execution precondition | COMP-SAVE saved audit exists |
| input artifact names | saved audit and adopted manuscript |
| input source paths | `audit/completion/audit.json.gz; artifacts/scenes` |
| output artifact name | staged publication |
| output Schema name | `publication-manifest.schema.json` |
| artifact class | staged_internal |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | public report sanitized/Markdown complete |
| adoption condition | COMP-SAVE saved audit exists |
| candidate path | `none` |
| adopted path | `.staging/publication/<publication-id>` |
| audit path | `audit/operations/out-01.json.gz` |
| resume source | persisted staged artifact; no candidate manifest |
| next stage | OUT-02 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## OUT-02 — publication validation

| contract | value |
|---|---|
| processor type | code |
| execution precondition | OUT-01 staging exists |
| input artifact names | staged publication |
| input source paths | ` .staging/publication` |
| output artifact name | publication validation result |
| output Schema name | `publication-validation.schema.json` |
| artifact class | staged_internal_validation |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | files order/nonempty/no secret leakage |
| adoption condition | OUT-01 staging exists |
| candidate path | `none` |
| adopted path | `.staging/publication/<publication-id>/publication-validation.json` |
| audit path | `audit/operations/out-02.json.gz` |
| resume source | no candidate; named staged input |
| next stage | COMP-PUBLISH |
| failure classification | storage error or mechanical stop |
| review output | なし |

## COMP-PUBLISH — public precondition gate

| contract | value |
|---|---|
| processor type | code |
| execution precondition | COMP-PRE passed, structurally valid completion audit exists, and OUT-02 validation passed |
| input artifact names | completion precheck, audit, and validation |
| input source paths | `runtime/checkpoints/completion/precheck.json; audit/completion/audit.json.gz; .staging/publication/<id>/publication-validation.json` |
| output artifact name | gate-result |
| output Schema name | `gate-result.schema.json` |
| artifact class | audit |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | all three preconditions only; no publication adoption |
| adoption condition | gate succeeds |
| candidate path | `none` |
| adopted path | `none` |
| audit path | `audit/operations/comp-publish.json.gz` |
| resume source | no candidate; named audit/staged inputs |
| next stage | OUT-03 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## OUT-03 — CURRENT切替

| contract | value |
|---|---|
| processor type | code |
| execution precondition | COMP-PUBLISH gate result passed |
| input artifact names | validated staged publication and gate result |
| input source paths | `.staging/publication/<publication-id>; audit/operations/comp-publish.json.gz` |
| output artifact name | adopted publication and updated output pointer |
| output Schema name | `publication-manifest.schema.json` |
| artifact class | adopted |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | atomically rename `.staging/publication/<publication-id>` to `publications/<publication-id>`, then atomically replace `output/CURRENT` |
| adoption condition | COMP-PUBLISH gate result passed |
| candidate path | `none` |
| adopted path | `publications/<publication-id>; output/CURRENT` |
| audit path | `audit/operations/out-03.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | complete |
| failure classification | storage error or mechanical stop |
| review output | なし |
