# Pipeline contracts: scene generation

> この文書はpipeline stageの正本。共通用語は[pipeline index](../../pipeline_contracts.md)を参照する。

## SC-01 — scene card生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | CH-ID plan and target scene number exist |
| input artifact names | adopted chapter, HEAD canon, knowledge, story state |
| input source paths | `plans/chapters/v01/c001.json; canon/HEAD generation` |
| output artifact name | scene card candidate |
| output Schema name | `scene-card.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | fixed code scene identity/full scene card Schema |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/scene-card.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/sc-01.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/scene-card.json`; otherwise named adopted input |
| next stage | SC-02 |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | なし |

## SC-02 — scene card review

| contract | value |
|---|---|
| processor type | LLM review |
| execution precondition | SC-01 candidate exists |
| input artifact names | scene card candidate |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/scene-card.json` |
| output artifact name | review_result |
| output Schema name | `review-result.schema.json` |
| artifact class | review candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | review Schema/card constraints |
| adoption condition | not adopted; review only |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/scene-card-review.json` |
| adopted path | `none` |
| audit path | `audit/reviews/sc-02.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/scene-card-review.json`; otherwise named adopted input |
| next stage | SC-REV or SC-CHK |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | `review_result` only |

## SC-REV — scene card revise

| contract | value |
|---|---|
| processor type | LLM revise |
| execution precondition | SC-02 issues and revision budget remain |
| input artifact names | last valid card, review, chapter constraints |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/{scene-card,scene-card-review}.json` |
| output artifact name | revised scene card |
| output Schema name | `scene-card.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | Yes |
| mechanical validation | whole scene card/full code identity unchanged |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/scene-card.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/sc-rev.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/scene-card.json`; otherwise named adopted input |
| next stage | SC-02 |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | なし |

## SC-CHK — scene card checkpoint

| contract | value |
|---|---|
| processor type | code |
| execution precondition | SC-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| input artifact names | latest structurally valid scene card |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/{scene-card,scene-card-review}.json` |
| output artifact name | scene card checkpoint |
| output Schema name | `scene-card.schema.json` |
| artifact class | checkpoint |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | candidate hash/schema/review zero issues |
| adoption condition | SC-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| candidate path | `none` |
| adopted path | `runtime/checkpoints/scenes/v01/c001/s001/scene-card.json` |
| audit path | `audit/operations/sc-chk.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | PROSE-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## PROSE-01 — prose生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | SC-CHK checkpoint exists |
| input artifact names | scene card checkpoint, writer view |
| input source paths | `runtime/checkpoints/scenes/v01/c001/s001/scene-card.json; Context Builder snapshot` |
| output artifact name | prose candidate |
| output Schema name | `prose.schema.txt` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | decode failure, empty response, or whitespace-only response is a response structure error |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/prose.md` |
| adopted path | `none` |
| audit path | `audit/llm-calls/prose-01.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/prose.md`; otherwise named adopted input |
| next stage | PROSE-02 |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | なし |

## PROSE-02 — prose review

| contract | value |
|---|---|
| processor type | LLM review |
| execution precondition | PROSE-01 candidate exists |
| input artifact names | prose candidate, scene card |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/prose.md; runtime/checkpoints/scenes/v01/c001/s001/scene-card.json` |
| output artifact name | review_result |
| output Schema name | `review-result.schema.json` |
| artifact class | review candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | review Schema/prose evidence anchors |
| adoption condition | not adopted; review only |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/prose-review.json` |
| adopted path | `none` |
| audit path | `audit/reviews/prose-02.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/prose-review.json`; otherwise named adopted input |
| next stage | PROSE-REV or PROSE-CHK |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | `review_result` only |

## PROSE-REV — prose revise

| contract | value |
|---|---|
| processor type | LLM revise |
| execution precondition | PROSE-02 issues and revision budget remain |
| input artifact names | last valid prose, review, writer view |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/{prose.md,prose-review.json}; Context Builder snapshot` |
| output artifact name | revised prose |
| output Schema name | `prose.schema.txt` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | Yes |
| mechanical validation | decode failure, empty response, or whitespace-only response is a response structure error |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/prose.md` |
| adopted path | `none` |
| audit path | `audit/llm-calls/prose-rev.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/prose.md`; otherwise named adopted input |
| next stage | PROSE-02 |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | なし |

## PROSE-CHK — prose checkpoint

| contract | value |
|---|---|
| processor type | code |
| execution precondition | PROSE-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| input artifact names | latest structurally valid prose |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/{prose.md,prose-review.json}` |
| output artifact name | prose checkpoint |
| output Schema name | `prose.schema.txt` |
| artifact class | checkpoint |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | NFC bytes/hash/review zero issues |
| adoption condition | PROSE-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| candidate path | `none` |
| adopted path | `runtime/checkpoints/scenes/v01/c001/s001/prose.md` |
| audit path | `audit/operations/prose-chk.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | DELTA-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## DELTA-01 — continuity delta抽出

| contract | value |
|---|---|
| processor type | LLM extract |
| execution precondition | PROSE-CHK checkpoint exists |
| input artifact names | prose checkpoint, scene card, HEAD snapshots |
| input source paths | `runtime/checkpoints/scenes/v01/c001/s001/{prose.md,scene-card.json}; canon/HEAD generation` |
| output artifact name | delta candidate |
| output Schema name | `continuity-delta.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | delta Schema/evidence quotes copied from prose |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/continuity-delta.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/delta-01.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/continuity-delta.json`; otherwise named adopted input |
| next stage | DELTA-02 |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | なし |

## DELTA-02 — continuity delta review

| contract | value |
|---|---|
| processor type | LLM review |
| execution precondition | DELTA-01 candidate exists |
| input artifact names | delta candidate, prose, prior state |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/continuity-delta.json; runtime/checkpoints/scenes/v01/c001/s001/prose.md; canon/HEAD generation` |
| output artifact name | review_result |
| output Schema name | `review-result.schema.json` |
| artifact class | review candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | review Schema/evidence/state transition validity |
| adoption condition | not adopted; review only |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/delta-review.json` |
| adopted path | `none` |
| audit path | `audit/reviews/delta-02.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/delta-review.json`; otherwise named adopted input |
| next stage | DELTA-REV or DELTA-CHK |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | `review_result` only |

## DELTA-REV — continuity delta revise

| contract | value |
|---|---|
| processor type | LLM revise |
| execution precondition | DELTA-02 issues and revision budget remain |
| input artifact names | last valid delta, review, prose, snapshots |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/{continuity-delta.json,delta-review.json}; runtime/checkpoints/scenes/v01/c001/s001/prose.md; canon/HEAD generation` |
| output artifact name | revised delta |
| output Schema name | `continuity-delta.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | Yes |
| mechanical validation | whole delta Schema/quote equality |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/scenes/v01/c001/s001/continuity-delta.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/delta-rev.json.gz` |
| resume source | candidate manifest at `runtime/candidates/scenes/v01/c001/s001/continuity-delta.json`; otherwise named adopted input |
| next stage | DELTA-02 |
| failure classification | transport is only connection, HTTP, stream, or timeout; JSON/Schema/required field/enum and prose decode, empty, or whitespace-only response consume response structure retry |
| review output | なし |

## DELTA-CHK — continuity delta checkpoint

| contract | value |
|---|---|
| processor type | code |
| execution precondition | DELTA-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| input artifact names | latest structurally valid delta |
| input source paths | `runtime/candidates/scenes/v01/c001/s001/{continuity-delta.json,delta-review.json}` |
| output artifact name | delta checkpoint |
| output Schema name | `continuity-delta.schema.json` |
| artifact class | checkpoint |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | Schema/evidence quote-offset-hash/review zero issues |
| adoption condition | DELTA-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| candidate path | `none` |
| adopted path | `runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json` |
| audit path | `audit/operations/delta-chk.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | COMMIT-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |
