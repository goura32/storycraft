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

A criterion assessment has `criterion_id`, `supports_evidence_ids`, `contradicts_evidence_ids`, `assessment`, and `explanation`; assessment is `satisfied|partially_satisfied|not_satisfied|contradicted`. A thread assessment has `thread_id`, `thread_status`, `progress`, `required`, `assessment`, and `explanation`. A contradiction has `code`, `description`, `evidence_ids`, and `severity`.

Completion audit is information for the code gate; its LLM assessment cannot by itself permit publication.

## Publication validation

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `valid` | boolean | yes | no | none | code | immutable | all output checks | publication validation |
| `errors` | array of string | yes | no | `[]` | code | immutable | sanitized | publication validation |
