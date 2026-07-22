# Data contracts: review and audit

Audit is never a resume source. Public completion reports exclude author truth, resolution conditions, secret prose, raw prompts/responses, and internal workspace paths.

## Review result, completion audit, publication validation

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `review_id` | string | yes | no | none | code | immutable | unique operation review | review result |
| `target_operation_id` | string | yes | no | none | code | immutable | existing candidate operation | review result |
| `target_id` | string | yes | no | none | code | immutable | matches target | review result |
| `issues` | array of issue | yes | no | [] | LLM→code | immutable | all issue fields | review result |
| `issues[].code` | string | yes | no | none | LLM→code | immutable | NFC nonempty | review result |
| `issues[].severity` | enum `info|minor|major|critical` | yes | no | none | LLM→code | immutable | exact enum | review result |
| `issues[].path` | string | yes | no | none | LLM→code | immutable | valid candidate path | review result |
| `issues[].description` | string | yes | no | none | LLM→code | immutable | nonempty | review result |
| `issues[].evidence` | string | yes | yes | null | LLM→code | immutable | quoted if prose | review result |
| `issues[].suggested_change` | string | yes | yes | null | LLM→code | immutable | no new author fact | review result |
| `completion_audit.status` | enum `pass|issues` | yes | no | none | LLM→code | immutable | exact enum | audit |
| `completion_audit.findings` | array of finding | yes | no | [] | LLM→code | immutable | sanitized projection | audit |
| `publication_validation.valid` | boolean | yes | no | none | code | immutable | all output checks | publication validation |
| `publication_validation.errors` | array<string> | yes | no | [] | code | immutable | sanitized strings | publication validation |
