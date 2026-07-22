# Pipeline contracts: input and initial

> この文書はpipeline stageの正本。共通用語は[pipeline index](../../pipeline_contracts.md)を参照する。

## INPUT-01 — brief読込

| contract | value |
|---|---|
| processor type | code |
| execution precondition | brief.json exists |
| input artifact names | brief.json |
| input source paths | `input/brief.json` |
| output artifact name | brief candidate |
| output Schema name | `brief.schema.json` |
| artifact class | candidate |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | brief field/schema/source hash |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/input/brief.json` |
| adopted path | `input/brief.json` |
| audit path | `audit/operations/input-01.json.gz` |
| resume source | candidate manifest at `runtime/candidates/input/brief.json`; otherwise named adopted input |
| next stage | INPUT-03 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## INPUT-02 — keywordsからbrief生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | keywords.json exists and brief.json absent |
| input artifact names | keywords.json |
| input source paths | `input/keywords.json` |
| output artifact name | brief candidate |
| output Schema name | `brief.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | brief Schema and NFC |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/input/brief.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/input-02.json.gz` |
| resume source | candidate manifest at `runtime/candidates/input/brief.json`; otherwise named adopted input |
| next stage | INPUT-03 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## INPUT-03 — brief検証・採用

| contract | value |
|---|---|
| processor type | code |
| execution precondition | structurally valid brief candidate exists |
| input artifact names | brief candidate |
| input source paths | `runtime/candidates/input/brief.json or input/brief.json` |
| output artifact name | adopted brief |
| output Schema name | `brief.schema.json` |
| artifact class | adopted/audit |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | Schema/source hash/editorial and publishing profile IDs |
| adoption condition | structurally valid brief candidate exists |
| candidate path | `none` |
| adopted path | `input/brief.json` |
| audit path | `audit/operations/input-03.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | INIT-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## INIT-01 — concept生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | INPUT-03 adopted brief exists |
| input artifact names | adopted brief |
| input source paths | `input/brief.json` |
| output artifact name | concept candidate |
| output Schema name | `concept.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | concept Schema and brief compatibility |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/initial-design/concept.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/init-01.json.gz` |
| resume source | candidate manifest at `runtime/candidates/initial-design/concept.json`; otherwise named adopted input |
| next stage | INIT-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## INIT-02 — 人物・関係候補生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | INIT-01 structurally valid concept exists |
| input artifact names | brief, concept |
| input source paths | `input/brief.json; runtime/candidates/initial-design/concept.json` |
| output artifact name | character/relationship candidates |
| output Schema name | `initial-people.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | local key uniqueness and relationship endpoint local keys |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/initial-design/people.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/init-02.json.gz` |
| resume source | candidate manifest at `runtime/candidates/initial-design/people.json`; otherwise named adopted input |
| next stage | INIT-03 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## INIT-03 — world・time rule候補生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | INIT-02 structurally valid people candidate exists |
| input artifact names | brief, concept, people |
| input source paths | `input/brief.json; runtime/candidates/initial-design/concept.json; runtime/candidates/initial-design/people.json` |
| output artifact name | world/time candidates |
| output Schema name | `initial-world.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | world kind/local key/time rule Schema |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/initial-design/world.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/init-03.json.gz` |
| resume source | candidate manifest at `runtime/candidates/initial-design/world.json`; otherwise named adopted input |
| next stage | INIT-04 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## INIT-04 — arc・thread・ending候補生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | INIT-01..03 candidates structurally valid |
| input artifact names | brief and INIT-01..03 candidates |
| input source paths | `input/brief.json; runtime/candidates/initial-design/*.json` |
| output artifact name | arc/thread/ending candidates |
| output Schema name | `initial-arcs.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | local key references/ending required rule |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/initial-design/arcs.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/init-04.json.gz` |
| resume source | candidate manifest at `runtime/candidates/initial-design/arcs.json`; otherwise named adopted input |
| next stage | INIT-05 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## INIT-05 — initial bundle統合

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | INIT-01 through INIT-04 candidates are structurally valid |
| input artifact names | INIT-01..04 candidates |
| input source paths | `runtime/candidates/initial-design/{concept,people,world,arcs}.json` |
| output artifact name | initial_design_bundle candidate |
| output Schema name | `initial-design-bundle.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | Schema, local_key references, duplicate detection, required records, and forbidden references |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/initial-design/bundle.json` |
| adopted path | `none` |
| audit path | `audit/operations/init-05.json.gz` |
| resume source | candidate manifest at `runtime/candidates/initial-design/bundle.json`; otherwise named adopted input |
| next stage | INIT-06 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## INIT-06 — initial bundle review

| contract | value |
|---|---|
| processor type | LLM review |
| execution precondition | INIT-05 bundle candidate exists |
| input artifact names | initial_design_bundle candidate |
| input source paths | `runtime/candidates/initial-design/bundle.json` |
| output artifact name | review_result |
| output Schema name | `review-result.schema.json` |
| artifact class | review candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | review result Schema; issue paths target bundle |
| adoption condition | not adopted; review only |
| candidate path | `runtime/candidates/initial-design/review.json` |
| adopted path | `none` |
| audit path | `audit/reviews/init-06.json.gz` |
| resume source | candidate manifest at `runtime/candidates/initial-design/review.json`; otherwise named adopted input |
| next stage | INIT-REV or INIT-ID |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | `review_result` only |

## INIT-REV — initial bundle revise

| contract | value |
|---|---|
| processor type | LLM revise |
| execution precondition | INIT-06 review has issues and revision budget remains |
| input artifact names | last valid bundle, review_result, brief |
| input source paths | `runtime/candidates/initial-design/{bundle,review}.json; input/brief.json` |
| output artifact name | revised initial_design_bundle |
| output Schema name | `initial-design-bundle.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | Yes |
| mechanical validation | whole bundle Schema/local key consistency |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/initial-design/bundle.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/init-rev.json.gz` |
| resume source | candidate manifest at `runtime/candidates/initial-design/bundle.json`; otherwise named adopted input |
| next stage | INIT-06 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## INIT-ID — initial design採用・genesis

| contract | value |
|---|---|
| processor type | code |
| execution precondition | structurally valid bundle exists and review issues are empty or revision_rounds_used reached max_revision_rounds |
| input artifact names | latest structurally valid initial bundle and review result |
| input source paths | `runtime/candidates/initial-design/{bundle,review}.json` |
| output artifact name | initial_design and genesis generation |
| output Schema name | `initial-design.schema.json` |
| artifact class | adopted/audit |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | local key mapping, fixed manifest, initial projection |
| adoption condition | structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds); residual issues append to `audit/residual-issues.jsonl` |
| candidate path | `none` |
| adopted path | `canon/initial-design.json; canon/generations/00000000/; canon/HEAD` |
| audit path | `audit/operations/init-id.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | SERIES-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## SERIES-01 — series map生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | INIT-ID genesis and initial design exist |
| input artifact names | initial_design |
| input source paths | `canon/initial-design.json` |
| output artifact name | series map candidate |
| output Schema name | `series-map.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | no volume number from LLM/local key uniqueness |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/series-map/candidate.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/series-01.json.gz` |
| resume source | candidate manifest at `runtime/candidates/series-map/candidate.json`; otherwise named adopted input |
| next stage | SERIES-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## SERIES-02 — series map review

| contract | value |
|---|---|
| processor type | LLM review |
| execution precondition | SERIES-01 candidate exists |
| input artifact names | series map candidate and initial design |
| input source paths | `runtime/candidates/series-map/candidate.json; canon/initial-design.json` |
| output artifact name | review_result |
| output Schema name | `review-result.schema.json` |
| artifact class | review candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | review Schema/all volume target coverage |
| adoption condition | not adopted; review only |
| candidate path | `runtime/candidates/series-map/review.json` |
| adopted path | `none` |
| audit path | `audit/reviews/series-02.json.gz` |
| resume source | candidate manifest at `runtime/candidates/series-map/review.json`; otherwise named adopted input |
| next stage | SERIES-REV or SERIES-ID |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | `review_result` only |

## SERIES-REV — series map revise

| contract | value |
|---|---|
| processor type | LLM revise |
| execution precondition | SERIES-02 issues and revision budget remain |
| input artifact names | last valid map, all review issues, initial design |
| input source paths | `runtime/candidates/series-map/{candidate,review}.json; canon/initial-design.json` |
| output artifact name | revised series map |
| output Schema name | `series-map.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | Yes |
| mechanical validation | whole map Schema/local key continuity |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/series-map/candidate.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/series-rev.json.gz` |
| resume source | candidate manifest at `runtime/candidates/series-map/candidate.json`; otherwise named adopted input |
| next stage | SERIES-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## SERIES-ID — series map採用

| contract | value |
|---|---|
| processor type | code |
| execution precondition | structurally valid series map exists and review issues are empty or revision_rounds_used reached max_revision_rounds |
| input artifact names | latest structurally valid series map and review result |
| input source paths | `runtime/candidates/series-map/{candidate,review}.json` |
| output artifact name | adopted series map |
| output Schema name | `series-map.schema.json` |
| artifact class | adopted/audit |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | code assigns 1..brief.volumes/no duplicates |
| adoption condition | structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds); residual issues append to `audit/residual-issues.jsonl` |
| candidate path | `none` |
| adopted path | `plans/series-map.json` |
| audit path | `audit/operations/series-id.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | VOL-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |
