# Configuration contracts

> Config・retry・timeout・budget・audit retentionの唯一の正本。runtime保存は[runtime and recovery](runtime_and_recovery.md)を参照する。

すべてのfieldは`runtime/effective-config.json`へ秘密を除外して保存する。各fieldはrun-fixedであり、creatorは利用者設定、source of truthはeffective configである。`provider` credential、Authorization header、API key、OS environment、secret configurationは保存禁止である。

## Model fields

| field | type | required | nullable | default | mutability | validation |
|---|---|---:|---:|---|---|---|
| `provider` | string | yes | no | none | run-fixed | non-empty |
| `base_url` | string | yes | no | none | run-fixed | absolute HTTPS/HTTP URL, credentialなし |
| `model` | string | yes | no | none | run-fixed | non-empty |
| `thinking` | boolean | yes | no | false | run-fixed | boolean |
| `stream` | boolean | yes | no | true | run-fixed | boolean |
| `temperature` | number | yes | no | 0.7 | run-fixed | 0..2 |
| `top_p` | number | yes | no | 1.0 | run-fixed | 0..1 |
| `seed` | integer | yes | yes | null | run-fixed | provider-supported integer |
| `structured_output_mode` | enum `json_schema` | yes | no | `json_schema` | run-fixed | exact enum |

## Timeout and retry fields

| field | type | required | nullable | default | mutability | validation |
|---|---|---:|---:|---|---|---|
| `connect_timeout_seconds` | integer | yes | no | 30 | extension-only on resume | >0 |
| `first_event_timeout_seconds` | integer | yes | no | 120 | extension-only on resume | >0 |
| `idle_timeout_seconds` | integer | yes | no | 120 | extension-only on resume | >0 |
| `total_call_timeout_seconds` | integer | yes | no | 900 | extension-only on resume | >0 |
| `max_transport_retries` | integer | yes | no | 2 | run-fixed | 0..10 |
| `max_response_structure_retries` | integer | yes | no | 2 | run-fixed | 0..10 |
| `max_revision_rounds` | integer | yes | no | 1 | run-fixed | 0..10 |
| `max_completion_audit_attempts` | integer | yes | no | 2 | run-fixed | 1..10 |

`transport retry`はconnection failure、HTTP failure、stream interruption、timeoutだけである。timeoutはstream closeとworker termination後にtransport failureへ分類する。`response structure retry`はJSON parse failure、Schema failure、required field missing、enum violationだけである。JSON不正はtransport retryに含めない。review構造retryとrevision結果構造retryの双方は`max_response_structure_retries`を使う。

## Context token fields

| field | type | required | nullable | default | mutability | validation |
|---|---|---:|---:|---|---|---|
| `model_context_window_tokens` | integer | yes | no | none | run-fixed | >0 |
| `protocol_overhead_tokens` | integer | yes | no | 0 | run-fixed | >=0 |
| `fallback_tokens_per_code_point` | number | yes | no | 2.0 | run-fixed | >=1.0 |
| `reserved_output_tokens_by_operation.init` | integer | yes | no | none | run-fixed | >=0 |
| `reserved_output_tokens_by_operation.series_map` | integer | yes | no | none | run-fixed | >=0 |
| `reserved_output_tokens_by_operation.volume` | integer | yes | no | none | run-fixed | >=0 |
| `reserved_output_tokens_by_operation.chapter` | integer | yes | no | none | run-fixed | >=0 |
| `reserved_output_tokens_by_operation.scene_card` | integer | yes | no | none | run-fixed | >=0 |
| `reserved_output_tokens_by_operation.prose` | integer | yes | no | none | run-fixed | >=0 |
| `reserved_output_tokens_by_operation.continuity` | integer | yes | no | none | run-fixed | >=0 |
| `reserved_output_tokens_by_operation.volume_handoff` | integer | yes | no | none | run-fixed | >=0 |
| `reserved_output_tokens_by_operation.completion_audit` | integer | yes | no | none | run-fixed | >=0 |
| `max_context_tokens_by_operation.init` | integer | yes | no | none | run-fixed | >0 |
| `max_context_tokens_by_operation.series_map` | integer | yes | no | none | run-fixed | >0 |
| `max_context_tokens_by_operation.volume` | integer | yes | no | none | run-fixed | >0 |
| `max_context_tokens_by_operation.chapter` | integer | yes | no | none | run-fixed | >0 |
| `max_context_tokens_by_operation.scene_card` | integer | yes | no | none | run-fixed | >0 |
| `max_context_tokens_by_operation.prose` | integer | yes | no | none | run-fixed | >0 |
| `max_context_tokens_by_operation.continuity` | integer | yes | no | none | run-fixed | >0 |
| `max_context_tokens_by_operation.volume_handoff` | integer | yes | no | none | run-fixed | >0 |
| `max_context_tokens_by_operation.completion_audit` | integer | yes | no | none | run-fixed | >0 |

A precise provider/tokenizer count is mandatory when available. Only when neither is available, `estimated_tokens = ceil(code_points * fallback_tokens_per_code_point)` is used. Hard limit is `min(max_context_tokens_by_operation[operation], model_context_window_tokens - reserved_output_tokens_by_operation[operation] - protocol_overhead_tokens)`; non-positive value rejects startup.

## Budget and audit retention

| field | type | required | nullable | default | mutability | validation |
|---|---|---:|---:|---|---|---|
| `max_llm_calls` | integer | yes | yes | null | run-fixed | null or >=0 |
| `max_total_input_tokens` | integer | yes | yes | null | run-fixed | null or >=0 |
| `max_total_output_tokens` | integer | yes | yes | null | run-fixed | null or >=0 |
| `max_elapsed_seconds` | integer | yes | yes | null | run-fixed | null or >=0 |
| `max_estimated_cost` | number | yes | yes | null | run-fixed | null or >=0 |
| `pricing_table_version` | string | yes | no | none | run-fixed | non-empty |
| `audit_retention_days` | integer | yes | no | 30 | retention-only on resume | >=1 |
| `audit_max_total_bytes` | integer | yes | no | 1073741824 | retention-only on resume | >0 |
| `audit_warning_threshold_bytes` | integer | yes | no | 805306368 | retention-only on resume | 0..<audit_max_total_bytes |

Every attempt, including transport retry and invalid response, consumes call/token/cost budget before validation. Provider usage is authoritative; fallback is used only without it. Non-null `max_estimated_cost` with unknown model pricing rejects startup. `active_elapsed_seconds` accumulates active execution across resume and excludes paused time. Retention cleanup may remove only expired audit gzip files; when total bytes reaches warning threshold it emits an audit warning, and when max is exceeded it stops before another raw payload is saved.

## Resume and profiles

Resume rejects changes to `state_version,code_version,prompt_bundle_version,schema_bundle_version,config_fingerprint,pricing_table_version,provider,base_url,model,thinking,stream,temperature,top_p,seed,structured_output_mode,editorial_profile_id,publishing_profile_id`. It permits only log level, timeout extension, and retention fields; every permitted alteration is audit logged.

`scene_target_chars=3000`、`scene_guide_min_chars=500`、`scene_guide_max_chars=5000`、`chapter_target_chars=12000`、`volume_target_chars=60000` are soft targets. Empty prose is hard failure. KDP default has 4..10 volumes, first volume free entry, later volumes paid, local resolution required, non-final reader question required, and `auto_publish=false`.
