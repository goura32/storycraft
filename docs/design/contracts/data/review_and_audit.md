# Data contracts: review and audit

Audit is never a resume authority. Public completion reports exclude author truth, resolution conditions, secret prose, raw prompts/responses, and internal paths. Every saved record rejects unknown fields.

## Review result

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `review_id` | string | yes | no | none | code | immutable | unique | review result |
| `target_operation_id` | operation ID | yes | no | none | code | immutable | candidate operation | review result |
| `target_id` | target ID | yes | no | none | code | immutable | target match | review result |
| `issues` | array of issue record | yes | no | `[]` | LLM then code | immutable | fully valid issue records | review result |

## Completion audit

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `audit_attempt` | integer | yes | no | none | code | immutable | positive and manifest match | completion audit |
| `criteria_assessments` | array of criterion assessment | yes | no | `[]` | LLM then code | immutable | each criterion once | completion audit |
| `thread_assessments` | array of thread assessment | yes | no | `[]` | LLM then code | immutable | required threads represented | completion audit |
| `contradictions` | array of contradiction | yes | no | `[]` | LLM then code | immutable | all evidence IDs resolve | completion audit |
| `residual_issues` | array of issue record | yes | no | `[]` | LLM then code | immutable | valid issues | completion audit |
| `overall_assessment` | `complete|complete_with_residual_issues|incomplete` | yes | no | none | LLM then code | immutable | exact enum | completion audit |

## Completion-audit child records

All child objects have `additionalProperties: false`.

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `criteria_assessments[].criterion_id` | ending criterion ID | yes | no | none | LLM then code | immutable | adopted criterion; unique per audit | completion audit |
| `criteria_assessments[].supports_evidence_ids` | array<evidence ID> | yes | no | `[]` | LLM then code | immutable | each ID resolves | completion audit |
| `criteria_assessments[].contradicts_evidence_ids` | array<evidence ID> | yes | no | `[]` | LLM then code | immutable | each ID resolves | completion audit |
| `criteria_assessments[].assessment` | enum | yes | no | none | LLM then code | immutable | `satisfied|partially_satisfied|not_satisfied|contradicted` | completion audit |
| `criteria_assessments[].explanation` | string | yes | no | none | LLM then code | immutable | NFC; public-safe; no author truth | completion audit |
| `thread_assessments[].thread_id` | thread ID | yes | no | none | LLM then code | immutable | adopted thread; unique per audit | completion audit |
| `thread_assessments[].thread_status` | enum `thread_status` | yes | no | none | LLM then code | immutable | enum registry | completion audit |
| `thread_assessments[].progress` | integer | yes | no | none | LLM then code | immutable | `0..4` | completion audit |
| `thread_assessments[].required` | boolean | yes | no | none | code | immutable | canonical thread match | completion audit |
| `thread_assessments[].assessment` | enum | yes | no | none | LLM then code | immutable | `satisfied|partially_satisfied|not_satisfied|contradicted` | completion audit |
| `thread_assessments[].explanation` | string | yes | no | none | LLM then code | immutable | NFC; public-safe | completion audit |
| `contradictions[].code` | string | yes | no | none | LLM then code | immutable | stable nonempty code | completion audit |
| `contradictions[].description` | string | yes | no | none | LLM then code | immutable | public-safe; no secret text | completion audit |
| `contradictions[].evidence_ids` | array<evidence ID> | yes | no | none | LLM then code | immutable | all IDs resolve | completion audit |
| `contradictions[].severity` | enum | yes | no | none | LLM then code | immutable | `info|warning|error` | completion audit |

Completion audit is information for the code gate; its LLM assessment cannot by itself permit publication.

## Publication validation

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `valid` | boolean | yes | no | none | code | immutable | all output checks | publication validation |
| `errors` | array of string | yes | no | `[]` | code | immutable | sanitized | publication validation |
