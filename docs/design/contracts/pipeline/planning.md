# Pipeline contracts: planning

> この文書はpipeline stageの正本。共通用語は[pipeline index](../../pipeline_contracts.md)を参照する。

## VOL-01 — 巻設計生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | SERIES-ID exists and target volume incomplete |
| input artifact names | series map, current canon, knowledge, story state, prior handoff |
| input source paths | `plans/series-map.json; canon/HEAD generation; artifacts/handoffs prior` |
| output artifact name | volume design candidate |
| output Schema name | `volume-design.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | target volume equals run state/no secrets to writer-only fields |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/volumes/v01/candidate.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/vol-01.json.gz` |
| resume source | `runtime/candidates/volumes/v01/candidate-manifest.json` (manifest-selected payload only) |
| next stage | VOL-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## VOL-02 — 巻設計review

| contract | value |
|---|---|
| processor type | LLM review |
| execution precondition | VOL-01 candidate exists |
| input artifact names | volume design candidate |
| input source paths | `runtime/candidates/volumes/v01/candidate.json` |
| output artifact name | review_result |
| output Schema name | `review-result.schema.json` |
| artifact class | review candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | review paths/reference IDs |
| adoption condition | not adopted; review only |
| candidate path | `runtime/candidates/volumes/v01/review.json` |
| adopted path | `none` |
| audit path | `audit/reviews/vol-02.json.gz` |
| resume source | `runtime/candidates/volumes/v01/candidate-manifest.json` (manifest-selected payload only) |
| next stage | VOL-REV or VOL-ID |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | `review_result` only |

## VOL-REV — 巻設計revise

| contract | value |
|---|---|
| processor type | LLM revise |
| execution precondition | VOL-02 issues and revision budget remain |
| input artifact names | last valid volume design, review, constraints |
| input source paths | `runtime/candidates/volumes/v01/{candidate,review}.json` |
| output artifact name | revised volume design |
| output Schema name | `volume-design.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | Yes |
| mechanical validation | whole volume Schema/series map target |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/volumes/v01/candidate.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/vol-rev.json.gz` |
| resume source | `runtime/candidates/volumes/v01/candidate-manifest.json` (manifest-selected payload only) |
| next stage | VOL-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## VOL-ID — 巻設計採用

| contract | value |
|---|---|
| processor type | code |
| execution precondition | VOL-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| input artifact names | latest structurally valid volume design |
| input source paths | `runtime/candidates/volumes/v01/{candidate,review}.json` |
| output artifact name | adopted volume design |
| output Schema name | `volume-design.schema.json` |
| artifact class | adopted/audit |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | target volume/no existing plan overwrite |
| adoption condition | VOL-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| candidate path | `none` |
| adopted path | `plans/volumes/v01.json` |
| audit path | `audit/operations/vol-id.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | CH-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |

## CH-01 — 章設計生成

| contract | value |
|---|---|
| processor type | LLM generate |
| execution precondition | VOL-ID plan exists |
| input artifact names | adopted volume design, HEAD canon/state |
| input source paths | `plans/volumes/v01.json; canon/HEAD generation` |
| output artifact name | chapter design candidate |
| output Schema name | `chapter-design.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | chapter number/current volume plan |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/chapters/v01/c001/candidate.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/ch-01.json.gz` |
| resume source | `runtime/candidates/chapters/v01/c001/candidate-manifest.json` (manifest-selected payload only) |
| next stage | CH-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## CH-02 — 章設計review

| contract | value |
|---|---|
| processor type | LLM review |
| execution precondition | CH-01 candidate exists |
| input artifact names | chapter design candidate |
| input source paths | `runtime/candidates/chapters/v01/c001/candidate.json` |
| output artifact name | review_result |
| output Schema name | `review-result.schema.json` |
| artifact class | review candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | No |
| mechanical validation | review Schema/scene allocation |
| adoption condition | not adopted; review only |
| candidate path | `runtime/candidates/chapters/v01/c001/review.json` |
| adopted path | `none` |
| audit path | `audit/reviews/ch-02.json.gz` |
| resume source | `runtime/candidates/chapters/v01/c001/candidate-manifest.json` (manifest-selected payload only) |
| next stage | CH-REV or CH-ID |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | `review_result` only |

## CH-REV — 章設計revise

| contract | value |
|---|---|
| processor type | LLM revise |
| execution precondition | CH-02 issues and revision budget remain |
| input artifact names | last valid chapter design, review, volume constraints |
| input source paths | `runtime/candidates/chapters/v01/c001/{candidate,review}.json; plans/volumes/v01.json` |
| output artifact name | revised chapter design |
| output Schema name | `chapter-design.schema.json` |
| artifact class | candidate |
| LLM call | Yes |
| transport retry | Yes |
| response structure retry | Yes |
| revision round consumption | Yes |
| mechanical validation | whole chapter Schema/volume consistency |
| adoption condition | not adopted; candidate remains resumable |
| candidate path | `runtime/candidates/chapters/v01/c001/candidate.json` |
| adopted path | `none` |
| audit path | `audit/llm-calls/ch-rev.json.gz` |
| resume source | `runtime/candidates/chapters/v01/c001/candidate-manifest.json` (manifest-selected payload only) |
| next stage | CH-02 |
| failure classification | transport error, response structure error, or mechanical stop |
| review output | なし |

## CH-ID — 章設計採用

| contract | value |
|---|---|
| processor type | code |
| execution precondition | CH-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| input artifact names | latest structurally valid chapter design |
| input source paths | `runtime/candidates/chapters/v01/c001/{candidate,review}.json` |
| output artifact name | adopted chapter design |
| output Schema name | `chapter-design.schema.json` |
| artifact class | adopted/audit |
| LLM call | No |
| transport retry | No |
| response structure retry | No |
| revision round consumption | No |
| mechanical validation | chapter belongs adopted volume |
| adoption condition | CH-02 structurally valid candidate exists and (issues are empty or revision_rounds_used >= max_revision_rounds) |
| candidate path | `none` |
| adopted path | `plans/chapters/v01/c001.json` |
| audit path | `audit/operations/ch-id.json.gz` |
| resume source | candidate manifest at `none`; otherwise named adopted input |
| next stage | SC-01 |
| failure classification | storage error or mechanical stop |
| review output | なし |
