# Configuration contracts

> LLM、token、timeout、budget、profile、resume互換性の唯一の正本。秘密を除いたeffective configは`runtime/effective-config.json`へ保存する。

## Model and token fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `provider,base_url,model` | string | yes | no | none | input | run-fixed | non-empty | effective config |
| `model_context_window_tokens` | integer | yes | no | none | input | run-fixed | >0 | effective config |
| `reserved_output_tokens_by_operation` | object<string,integer> | yes | no | none | input | run-fixed | every operation >=0 | effective config |
| `max_context_tokens_by_operation` | object<string,integer> | yes | no | none | input | run-fixed | every operation >0 | effective config |
| `protocol_overhead_tokens` | integer | yes | no | 0 | input | run-fixed | >=0 | effective config |
| `token_estimator` | enum | yes | no | `unicode_code_points_div_1_5` | input | run-fixed | only named estimator | effective config |
| `temperature,top_p,seed` | number/number/integer|null | yes | yes for seed | `0.7,1.0,null` | input | run-fixed | provider bounds | effective config |
| `structured_output_mode` | enum | yes | no | `json_schema` | input | run-fixed | `json_schema` only | effective config |

Context hard limit is `min(max_context_tokens_by_operation[operation], model_context_window_tokens - reserved_output_tokens_by_operation[operation] - protocol_overhead_tokens)`. If it is not positive, startup fails. Text length is a reference metric only. Without provider tokenizer/usage, `estimated_tokens = ceil(Unicode code point count / 1.5)` for UTF-8 text; provider usage is authoritative when available.

## Retry and timeout

| field | type | required | nullable | default | validation |
|---|---|---:|---:|---|---|
| `max_transport_retries` | integer | yes | no | 2 | 0..10 |
| `max_response_structure_retries` | integer | yes | no | 2 | 0..10 |
| `max_revision_rounds` | integer | yes | no | 1 | 0..10 |
| `max_completion_audit_attempts` | integer | yes | no | 2 | 1..10 |
| `connect_timeout_seconds,first_event_timeout_seconds,idle_timeout_seconds,total_call_timeout_seconds` | integer | yes | no | `30,120,120,900` | >0 |

Timeout closes the stream and terminates the worker before it becomes a transport failure. Transport retries never include invalid JSON/Schema; those consume response-structure retries. Every call attempt, including retry and invalid structure response, is budget-accounted.

## Budget

| field | type | required | nullable | default | validation |
|---|---|---:|---:|---|---|
| `max_llm_calls,max_total_input_tokens,max_total_output_tokens,max_elapsed_seconds` | integer | yes | yes | null | null = unlimited; otherwise >=0 |
| `max_estimated_cost` | number | yes | yes | null | null = unlimited; otherwise >=0 |
| `pricing_table_version` | string | yes | no | none | non-empty |

A call attempt increments call/token/cost accounting before response validation. Provider usage is used when available; otherwise the configured estimator is used. If `max_estimated_cost` is non-null and the selected model has unknown price, startup fails. `active_elapsed_seconds` is cumulative active execution seconds from run creation across resume; stopped time is excluded.

## Profiles and resume

`scene_target_chars=3000`、`scene_guide_min_chars=500`、`scene_guide_max_chars=5000`、`chapter_target_chars=12000`、`volume_target_chars=60000` are soft targets. Only empty prose is a hard error. KDP default profile has volume count 4..10, first volume free entry, later volumes paid, local resolution required, reader question for non-final volume, and `auto_publish=false`.

Resume rejects changes to `state_version,code_version,prompt_bundle_version,schema_bundle_version,config_fingerprint,pricing_table_version,model,editorial_profile_id,publishing_profile_id`. It may change only log level, timeout extension, or audit retention; any permitted change is audit logged.
