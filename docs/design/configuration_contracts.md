# Configuration contracts

This document is the normative contract for Storycraft configuration materialization, model invocation parameters, timeout and retry classification, context-token limits, run budgets, audit retention, editorial and publishing profiles, resume-time configuration compatibility, and the redacted file stored at:

```text
runtime/effective-config.json
```

Runtime counters and manifests are defined by [`contracts/ledger/runtime_records.md`](contracts/ledger/runtime_records.md). Pipeline stage IDs and operation families are defined by [`pipeline_contracts.md`](pipeline_contracts.md).

Every saved object defined here uses `additionalProperties: false`.

---

## 1. Configuration principles

### 1.1 User configuration and effective configuration

User-provided configuration may omit fields that have defaults. Before any run artifact is created, code materializes one complete Effective config by:

1. loading built-in defaults;
2. applying an optional user configuration object;
3. applying explicit CLI overrides;
4. resolving editorial and publishing profiles;
5. resolving code, prompt, Schema, workspace, state, and pricing versions;
6. validating all field and cross-field rules;
7. calculating the immutable-config fingerprint;
8. writing a redacted `runtime/effective-config.json`.

All fields marked `required=yes` are required in the materialized Effective config, not necessarily in the user's partial input.

Unknown user-config fields are rejected.

### 1.2 Secret handling

The actual provider credential is never stored in:

```text
runtime/effective-config.json
runtime/run-manifest.json
runtime/run-state.json
audit files
logs
candidate manifests
checkpoint manifests
publication artifacts
```

The Effective config may store only the environment-variable name used to obtain the credential.

The credential value:

- is read at process start and before a resumed provider call;
- may be rotated without changing run compatibility;
- is never included in a hash or fingerprint;
- is never printed;
- is never placed in an exception message;
- is never sent anywhere except the configured provider authentication mechanism.

### 1.3 Mutability classes

| mutability | behavior |
|---|---|
| `run-fixed` | A changed value rejects resume |
| `resume-increase-only` | Resume permits the same or a larger value; a smaller value rejects resume |
| `resume-mutable` | Resume permits any valid value after an audit record is written |
| `code-generated` | User cannot set the value; code materializes it |

A permitted resume change updates `runtime/effective-config.json` and Run-state `effective_config_sha256`. It does not alter the immutable Run manifest or its immutable-config fingerprint.

---

## 2. Effective-config root

`runtime/effective-config.json` contains exactly the fields below.

### 2.1 Version and fingerprint fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `config_version` | string | yes | no | none | code | code-generated | supported Effective-config Schema version | Effective config |
| `state_version` | string | yes | no | none | code | run-fixed | supported Storycraft state-contract version | Effective config |
| `workspace_version` | string | yes | no | none | code | run-fixed | supported workspace-layout version | Effective config |
| `code_version` | string | yes | no | none | code | run-fixed | exact application build/version identifier | Effective config |
| `prompt_bundle_version` | string | yes | no | none | code | run-fixed | exact prompt bundle identifier | Effective config |
| `schema_bundle_version` | string | yes | no | none | code | run-fixed | exact structured-output Schema bundle identifier | Effective config |
| `materialized_at` | RFC 3339 UTC timestamp | yes | no | none | code | code-generated | valid timestamp | Effective config |
| `immutable_config_fingerprint` | SHA-256 | yes | no | none | code | code-generated | calculated by Section 18 | Effective config |

`runtime/effective-config.json` does not contain its own complete-file SHA-256. The complete-file hash is stored in Run state and applicable Candidate/Checkpoint manifests.

### 2.2 Model and provider fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `provider` | string | yes | no | none | user/default | run-fixed | NFC nonempty; registered provider adapter | Effective config |
| `base_url` | string | yes | no | none | user/default | run-fixed | absolute HTTP(S) URL; no userinfo, query, fragment, or credential | Effective config |
| `credential_env_var` | string | yes | yes | `null` | user/default | run-fixed | null for credential-free provider; otherwise pattern `[A-Z_][A-Z0-9_]*` | Effective config |
| `model` | string | yes | no | none | user/default | run-fixed | NFC nonempty | Effective config |
| `thinking` | boolean | yes | no | `false` | user/default | run-fixed | boolean | Effective config |
| `stream` | boolean | yes | no | `true` | user/default | run-fixed | boolean | Effective config |
| `temperature` | number | yes | no | `0.7` | user/default | run-fixed | finite `0..2` and provider-supported | Effective config |
| `top_p` | number | yes | no | `1.0` | user/default | run-fixed | finite `0..1` and provider-supported | Effective config |
| `seed` | integer | yes | yes | `null` | user/default | run-fixed | null or provider-supported signed integer | Effective config |
| `structured_output_mode` | constant string `json_schema` | yes | no | `json_schema` | code/default | run-fixed | exact constant | Effective config |

`structured_output_mode` applies to structured LLM stages. Prose stages return canonical text rather than JSON.

### 2.3 Profile fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `editorial_profile_id` | string | yes | no | `ja-novel-default` | user/default | run-fixed | equals `editorial_profile.profile_id` | Effective config |
| `publishing_profile_id` | string | yes | no | `kdp-series-default` | user/default | run-fixed | equals `publishing_profile.profile_id` | Effective config |
| `editorial_profile` | Editorial profile | yes | no | built-in default | profile resolver | run-fixed | complete Section 13 contract | Effective config |
| `publishing_profile` | Publishing profile | yes | no | built-in default | profile resolver | run-fixed | complete Section 14 contract | Effective config |

The adopted Brief's profile IDs must equal these IDs.

### 2.4 Timeout, retry, and revision fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---:|---|---|---|---|
| `connect_timeout_seconds` | integer | yes | no | `30` | user/default | resume-increase-only | `1..3600` | Effective config |
| `first_event_timeout_seconds` | integer | yes | no | `120` | user/default | resume-increase-only | `1..3600` | Effective config |
| `idle_timeout_seconds` | integer | yes | no | `120` | user/default | resume-increase-only | `1..3600` | Effective config |
| `total_call_timeout_seconds` | integer | yes | no | `900` | user/default | resume-increase-only | `1..86400`; not less than any other timeout | Effective config |
| `max_transport_retries` | integer | yes | no | `2` | user/default | run-fixed | `0..10` | Effective config |
| `max_response_structure_retries` | integer | yes | no | `2` | user/default | run-fixed | `0..10` | Effective config |
| `max_revision_rounds` | integer | yes | no | `1` | user/default | run-fixed | `0..10` | Effective config |
| `max_completion_audit_attempts` | integer | yes | no | `2` | user/default | run-fixed | `1..10` | Effective config |
| `retry_initial_backoff_seconds` | number | yes | no | `1.0` | user/default | run-fixed | finite `0..300` | Effective config |
| `retry_max_backoff_seconds` | number | yes | no | `30.0` | user/default | run-fixed | finite; `>= retry_initial_backoff_seconds`; `<=3600` | Effective config |
| `retry_jitter_ratio` | number | yes | no | `0.2` | user/default | run-fixed | finite `0..1` | Effective config |

### 2.5 Context-token fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `model_context_window_tokens` | integer | yes | no | none | user/provider metadata | run-fixed | `>0`; exact usable model context window | Effective config |
| `protocol_overhead_tokens` | integer | yes | no | `1024` | user/default | run-fixed | `>=0`; less than model window | Effective config |
| `fallback_tokens_per_code_point` | number | yes | no | `2.0` | user/default | run-fixed | finite `1.0..8.0` | Effective config |
| `reserved_output_tokens_by_operation` | Operation-token map | yes | no | Section 9 defaults | user/default | run-fixed | complete exact-key map; every value `>=1` | Effective config |
| `max_context_tokens_by_operation` | Operation-token map | yes | no | model window for every key | user/default | run-fixed | complete exact-key map; every value `>0` | Effective config |

### 2.6 Budget and pricing fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `max_llm_calls` | integer | yes | yes | `null` | user/default | run-fixed | null or `>=0` | Effective config |
| `max_total_input_tokens` | integer | yes | yes | `null` | user/default | run-fixed | null or `>=0` | Effective config |
| `max_total_output_tokens` | integer | yes | yes | `null` | user/default | run-fixed | null or `>=0` | Effective config |
| `max_active_elapsed_seconds` | number | yes | yes | `null` | user/default | run-fixed | null or finite `>=0` | Effective config |
| `max_estimated_cost` | number | yes | yes | `null` | user/default | run-fixed | null or finite `>=0` in `pricing_currency` | Effective config |
| `pricing_table_version` | string | yes | no | none | user/default | run-fixed | NFC nonempty | Effective config |
| `pricing_currency` | string | yes | no | `USD` | user/default | run-fixed | three uppercase ASCII letters | Effective config |
| `input_cost_per_million_tokens` | number | yes | no | none | user/default | run-fixed | finite `>=0` | Effective config |
| `cached_input_cost_per_million_tokens` | number | yes | yes | `null` | user/default | run-fixed | null or finite `>=0` | Effective config |
| `output_cost_per_million_tokens` | number | yes | no | none | user/default | run-fixed | finite `>=0` | Effective config |

For a local or free provider, explicit zero prices are valid. Unknown pricing is not valid because Runtime always tracks `estimated_cost_used`.

### 2.7 Scene and manuscript planning fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---:|---|---|---|---|
| `max_new_items_per_scene` | integer | yes | no | `2` | user/default | run-fixed | `0..20` | Effective config |
| `scene_target_chars` | integer | yes | no | `3000` | user/default | run-fixed | `>=1` | Effective config |
| `scene_guide_min_chars` | integer | yes | no | `500` | user/default | run-fixed | `>=1`; `<=scene_target_chars` | Effective config |
| `scene_guide_max_chars` | integer | yes | no | `5000` | user/default | run-fixed | `>=scene_target_chars` | Effective config |
| `chapter_target_chars` | integer | yes | no | `12000` | user/default | run-fixed | `>=scene_target_chars` | Effective config |
| `volume_target_chars` | integer | yes | no | `60000` | user/default | run-fixed | `>=chapter_target_chars` | Effective config |

These are soft planning targets. They never reject otherwise valid prose solely because of length. Empty or whitespace-only prose is a response-format failure.

### 2.8 Audit and log fields

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---:|---|---|---|---|
| `log_level` | enum `log_level` | yes | no | `info` | user/default | resume-mutable | `debug`, `info`, `warning`, or `error` | Effective config |
| `audit_compression` | constant string `gzip` | yes | no | `gzip` | code/default | run-fixed | exact constant | Effective config |
| `audit_redaction_mode` | constant string `strict` | yes | no | `strict` | code/default | run-fixed | exact constant | Effective config |
| `audit_store_request_body` | boolean | yes | no | `true` | user/default | run-fixed | boolean | Effective config |
| `audit_store_response_body` | boolean | yes | no | `true` | user/default | run-fixed | boolean | Effective config |
| `audit_retention_days` | integer | yes | no | `30` | user/default | resume-mutable | `1..3650` | Effective config |
| `audit_max_total_bytes` | integer | yes | no | `1073741824` | user/default | resume-mutable | `>0` | Effective config |
| `audit_warning_threshold_bytes` | integer | yes | no | `805306368` | user/default | resume-mutable | `>=0` and `<audit_max_total_bytes` | Effective config |

---

## 3. Configuration source precedence

From lowest to highest priority:

```text
built-in defaults
optional user configuration
explicit CLI overrides
code-generated version/profile/pricing materialization
```

Secret credential values are resolved separately from the configured environment-variable name and never enter the precedence merge.

An explicit JSON `null` is accepted only for fields whose contract is nullable. Omission applies a default when one exists.

After materialization, the complete Effective config is validated as one object. Validation does not stop after the first field error; code reports all mechanically detectable errors together.

---

## 4. Provider and credential contract

### 4.1 Base URL

`base_url` must:

- use `http` or `https`;
- include a hostname;
- contain no username or password;
- contain no query string;
- contain no fragment;
- end without duplicate `/`;
- be stored in normalized URL form.

Plain HTTP is permitted only for a loopback or explicitly registered local provider adapter. Remote non-loopback HTTP is rejected.

### 4.2 Credential environment variable

When `credential_env_var` is non-null:

- the environment variable must exist and be nonempty before a provider call;
- the variable name may be logged;
- the value may not be logged or persisted;
- a missing value is a mechanical configuration error, not a transport retry.

When null, the selected provider adapter must declare that credentials are not required.

### 4.3 Provider capability validation

Startup rejects configuration when the selected adapter/model does not support required capabilities:

```text
configured context window
configured temperature/top_p/seed values
streaming mode when stream=true
structured JSON Schema output for structured stages
usage reporting or the documented fallback accounting path
worker cancellation after timeout
```

A provider may omit token usage only when fallback token estimation and configured pricing can produce budget accounting.

---

## 5. Timeout semantics

Timeouts apply to each individual provider-call attempt, including retry attempts.

### 5.1 Connect timeout

Time from starting the network attempt until transport connection and TLS negotiation complete.

### 5.2 First-event timeout

When `stream=true`, time from completed connection/request transmission until the first response event.

When `stream=false`, time until the first response byte or complete response becomes available.

### 5.3 Idle timeout

When `stream=true`, maximum time between consecutive response events.

When `stream=false`, idle timeout is not applied after the first response byte; total timeout remains active.

### 5.4 Total-call timeout

Wall-clock time from starting one attempt until the response is complete, including connection and streaming.

On timeout, code must:

1. cancel the provider request;
2. close the stream;
3. terminate the call worker when required;
4. write an audit error record;
5. classify the attempt as transport failure;
6. apply transport retry policy when budget remains.

Merely returning control while a worker continues running is forbidden.

---

## 6. Retry classification

### 6.1 Transport retry

Transport retry is limited to:

```text
DNS or connection failure
TLS negotiation failure
connection reset
premature stream interruption
connect timeout
first-event timeout
idle timeout
total-call timeout
HTTP 408
HTTP 409 when the provider documents it as retryable
HTTP 425
HTTP 429
HTTP 500..599
```

Non-retryable examples:

```text
HTTP 400
HTTP 401
HTTP 403
HTTP 404
missing credential environment variable
invalid local configuration
unsupported provider capability
JSON parse failure
Schema failure
review issue
```

`max_transport_retries=N` permits at most:

```text
1 initial transport attempt + N transport retry attempts
```

for one logical response-generation attempt.

### 6.2 Response-structure retry

Response-structure retry applies after a transport-successful response when:

```text
UTF-8 decode fails
structured response is not valid JSON
structured response fails its exact Schema
required field is missing
unknown field is present
enum value is invalid
field type or conditional rule is invalid
prose response is empty or whitespace-only
```

It does not apply to semantic review issues.

`max_response_structure_retries=N` permits:

```text
1 initial logical response + N new logical response calls
```

Each logical response call receives its own transport retry allowance.

Review output and revision output use the same `max_response_structure_retries` setting.

### 6.3 Semantic revision

A semantic review issue consumes `max_revision_rounds`, not a response retry.

```text
issues empty:
  proceed to adoption/checkpoint

issues present and rounds remain:
  revise the entire candidate

issues present and rounds exhausted:
  adopt the latest structurally valid candidate
  write residual issues
```

Severity does not create an unbounded repair loop.

### 6.4 Completion-audit attempts

`max_completion_audit_attempts` is independent of response-structure retries.

Each Completion-audit attempt:

- starts from the same COMP-PRE input snapshot;
- has its own response-structure retry allowance;
- is saved as `attempt-NN.json`;
- does not revise a prior audit answer toward success.

The run stops mechanically only when all configured audit attempts fail to produce one structurally valid audit result.

### 6.5 Backoff

For transport retry index `r`, where the first retry is `r=0`:

```text
base_delay =
  min(
    retry_max_backoff_seconds,
    retry_initial_backoff_seconds * 2^r
  )

actual_delay =
  base_delay * U(1 - retry_jitter_ratio, 1 + retry_jitter_ratio)
```

When jitter is zero, delay is deterministic. The actual delay is recorded in the audit error record.

Response-structure retries and semantic revisions do not use transport backoff unless their individual provider call also encounters a transport failure.

---

## 7. Operation-key registry

The exact operation keys are:

```text
brief
initial_design
series_map
volume_design
chapter_design
scene_card
prose
continuity_delta
volume_handoff
completion_audit
```

No alias is permitted.

Stage-to-operation mapping:

| stages | operation key |
|---|---|
| `INPUT-02` | `brief` |
| `INIT-01` through `INIT-06`, `INIT-REV` | `initial_design` |
| `SERIES-01`, `SERIES-02`, `SERIES-REV` | `series_map` |
| `VOL-01`, `VOL-02`, `VOL-REV` | `volume_design` |
| `CH-01`, `CH-02`, `CH-REV` | `chapter_design` |
| `SC-01`, `SC-02`, `SC-REV` | `scene_card` |
| `PROSE-01`, `PROSE-02`, `PROSE-REV` | `prose` |
| `DELTA-01`, `DELTA-02`, `DELTA-REV` | `continuity_delta` |
| `VH-01`, `VH-02`, `VH-REV` | `volume_handoff` |
| `COMP-AUDIT` | `completion_audit` |

Code-only stages have no operation key because they do not invoke an LLM.

---

## 8. Operation-token map contract

An Operation-token map is an object with all ten operation keys, no unknown keys, and integer values.

```text
additionalProperties = false
all keys required
```

### 8.1 Reserved-output defaults

| key | default reserved output tokens |
|---|---:|
| `brief` | `2048` |
| `initial_design` | `8192` |
| `series_map` | `4096` |
| `volume_design` | `4096` |
| `chapter_design` | `4096` |
| `scene_card` | `4096` |
| `prose` | `8192` |
| `continuity_delta` | `6144` |
| `volume_handoff` | `4096` |
| `completion_audit` | `8192` |

Every value is an integer `>=1`.

### 8.2 Maximum-context defaults

By default, every `max_context_tokens_by_operation` value is materialized as `model_context_window_tokens`.

Every value is an integer `>0`.

---

## 9. Token counting and hard input limits

### 9.1 Token-count source

Priority:

```text
provider/model tokenizer
provider preflight token-count endpoint
configured fallback estimator
```

When a precise provider/model count is available, using the fallback is forbidden.

Fallback:

```text
estimated_tokens =
  ceil(
    Unicode_NFC_code_points
    * fallback_tokens_per_code_point
  )
```

The fallback count includes all serialized context, prompt-template output, structured instructions, and delimiters supplied to the provider.

### 9.2 Hard operation input limit

For operation `k`:

```text
available_model_input =
  model_context_window_tokens
  - reserved_output_tokens_by_operation[k]
  - protocol_overhead_tokens

hard_input_limit =
  min(
    max_context_tokens_by_operation[k],
    available_model_input
  )
```

Startup rejects configuration when `available_model_input <= 0` for any operation.

A provider call is rejected before transmission when its precise or estimated input count exceeds `hard_input_limit`.

The Context Builder must reduce optional context according to the Context contract. It must not truncate required records or bypass the hard limit.

### 9.3 Usage accounting

Provider-reported usage is authoritative.

When the provider omits usage:

- input tokens use the precise tokenizer count or fallback estimate;
- output tokens use the precise tokenizer count or fallback estimate over the actual response;
- the audit record marks usage as estimated.

All attempts count, including:

```text
transport attempts that reached the provider and incurred usage
invalid structured responses
review calls
revision calls
completion-audit attempts
```

A transport failure known to have sent no billable request records zero tokens and cost.

---

## 10. Budget semantics

### 10.1 Preflight

Before each provider call, code checks:

```text
llm_calls_used + 1
known input-token usage plus this input
reserved possible output usage
estimated cost using configured prices
active elapsed time
audit storage availability
```

If a non-null cap would be exceeded by the preflight values, the call is not sent and the run stops with `budget_exhausted`.

### 10.2 Post-call accounting

Immediately after every attempt, before response validation, code updates:

```text
llm_calls_used
input_tokens_used
output_tokens_used
estimated_cost_used
active_elapsed_seconds
transport or response retry counters
```

Actual provider usage may exceed a reservation. In that case:

- actual usage is still recorded;
- the current response may be validated and used;
- no later provider call is permitted once a cap is reached or exceeded;
- code-only adoption may finish when no additional LLM call is required.

### 10.3 Cost calculation

For each call:

```text
input_cost =
  uncached_input_tokens
  * input_cost_per_million_tokens
  / 1_000_000

cached_input_cost =
  cached_input_tokens
  * (
      cached_input_cost_per_million_tokens
      if non-null
      else input_cost_per_million_tokens
    )
  / 1_000_000

output_cost =
  billable_output_tokens
  * output_cost_per_million_tokens
  / 1_000_000
```

Provider adapters define how reported cached and reasoning tokens map to these categories. The mapping must be recorded in the adapter documentation and audit payload.

### 10.4 Active elapsed time

`active_elapsed_seconds` includes:

```text
provider call time
retry backoff
LLM response validation
review/revision processing
code-only pipeline processing
commit and publication processing
```

It excludes time while `run_status=paused` or while no Storycraft process owns the active run.

---

## 11. Editorial profile

An Editorial profile is fully materialized inside the Effective config.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `profile_id` | string | yes | no | `ja-novel-default` | profile resolver | run-fixed | equals root `editorial_profile_id` |
| `language_tag` | string | yes | no | `ja-JP` | profile resolver | run-fixed | valid BCP 47 language tag |
| `narrative_person` | enum | yes | no | `third_person` | profile resolver | run-fixed | `first_person` or `third_person` |
| `tense` | enum | yes | no | `past` | profile resolver | run-fixed | `past` or `present` |
| `pov_policy` | constant `single_pov_per_scene` | yes | no | exact constant | profile resolver | run-fixed | exact constant |
| `pov_distance` | enum | yes | no | `close` | profile resolver | run-fixed | `close`, `medium`, or `distant` |
| `dialogue_guidance` | string | yes | no | built-in Japanese-novel guidance | profile resolver | run-fixed | NFC nonempty |
| `prose_constraints` | array<string> | yes | no | built-in defaults | profile resolver | run-fixed | unique canonical set |
| `forbidden_content` | array<string> | yes | no | `[]` | profile resolver | run-fixed | unique canonical set |

`forbidden_content` contains editorial constraints, not secret safety configuration. It may be projected to the Writer View when relevant.

Default Japanese-novel prose constraints include:

```text
maintain one POV per scene
avoid unexplained POV leakage
preserve established speech anchors
do not reveal forbidden disclosures
do not add unsupported Canon facts
```

---

## 12. Publishing profile

A Publishing profile is fully materialized inside the Effective config.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|---|
| `profile_id` | string | yes | no | `kdp-series-default` | profile resolver | run-fixed | equals root `publishing_profile_id` |
| `platform` | constant `kdp` | yes | no | `kdp` | profile resolver | run-fixed | exact constant |
| `manuscript_format` | constant `markdown` | yes | no | `markdown` | profile resolver | run-fixed | exact constant |
| `min_volumes` | integer | yes | no | `4` | profile resolver | run-fixed | `4..10` |
| `max_volumes` | integer | yes | no | `10` | profile resolver | run-fixed | `min_volumes..10` |
| `first_volume_access` | constant `free` | yes | no | `free` | profile resolver | run-fixed | exact constant |
| `later_volume_access` | constant `paid` | yes | no | `paid` | profile resolver | run-fixed | exact constant |
| `require_volume_local_resolution` | boolean | yes | no | `true` | profile resolver | run-fixed | boolean |
| `require_nonfinal_reader_question` | boolean | yes | no | `true` | profile resolver | run-fixed | boolean |
| `auto_publish` | constant boolean `false` | yes | no | `false` | profile resolver | run-fixed | exact false in version 1 |

`auto_publish=false` concerns external marketplace publication. It does not disable local `publications/<id>` generation or `output/CURRENT`.

The adopted Brief's `volumes` must satisfy both the product hard range `4..10` and this profile's inclusive range.

---

## 13. Audit storage and retention

### 13.1 Audit contents

LLM-call audit filenames and IDs are defined by `runtime_records.md`.

With body storage enabled, each call audit may contain:

```text
redacted request body
raw provider response body
usage
finish reason
timing
retry classification
provider error details
prompt and Schema versions
context hash
```

Strict redaction always removes:

```text
credential values
Authorization headers
cookies
secret environment values
OS environment dumps
filesystem paths outside the workspace
```

`audit_store_request_body=false` or `audit_store_response_body=false` removes that body but preserves its SHA-256, byte length, media type, and redaction metadata.

### 13.2 Retention cleanup

Retention cleanup may delete only audit files that are:

- older than `audit_retention_days`;
- not part of the currently active run;
- not explicitly retained by a manual hold.

It never deletes:

```text
candidate artifacts
candidate manifests
checkpoints
adopted Canon generations
adopted Scene artifacts
publications
logs required by another retention policy
```

### 13.3 Size thresholds

When total audit gzip bytes reach `audit_warning_threshold_bytes`, code writes a warning and continues.

When total bytes are already at or above `audit_max_total_bytes` before a new provider call, the call is not sent.

If one completed call causes the total to cross the maximum:

- the complete current audit record is still saved;
- the run stops before the next provider call;
- the current structurally valid response may still be processed through code-only stages.

Changing retention limits on resume does not retroactively delete files until the next explicit cleanup pass.

---

## 14. Logging

`log_level` controls `logs/storycraft.log`.

| level | behavior |
|---|---|
| `debug` | detailed code-path and validation diagnostics, still secret-redacted |
| `info` | stage transitions, adoption, resume, and summary usage |
| `warning` | recoverable anomalies, residual issues, retention threshold, cleanup warnings |
| `error` | mechanical stop and unrecoverable operation failure |

Raw prompt and response bodies never appear in the normal log at any level.

Changing `log_level` on resume is audit logged and does not affect the immutable fingerprint.

---

## 15. Resume compatibility

### 15.1 Run-fixed comparison

Resume rejects a changed value for every `run-fixed` field, including nested profile fields and operation-token maps.

The actual credential value is excluded and may rotate.

### 15.2 Increase-only timeout comparison

Each timeout may remain the same or increase.

Any decrease rejects resume.

A timeout increase:

1. is validated against all cross-field rules;
2. is written to an audit operation record;
3. replaces the Effective config atomically;
4. updates Run-state `effective_config_sha256`.

### 15.3 Resume-mutable comparison

The following may change to any valid value:

```text
log_level
audit_retention_days
audit_max_total_bytes
audit_warning_threshold_bytes
```

All cross-field rules must still pass.

### 15.4 Fingerprint and detailed comparison

Resume validation performs both:

```text
immutable_config_fingerprint equality
field-by-field comparison against the previous Effective config
```

The fingerprint detects accidental changes. Field-by-field comparison enforces timeout increase-only and resume-mutable rules.

A mismatch is a mechanical stop. Storycraft never silently adopts a changed model, prompt, Schema, profile, budget, token limit, retry policy, or pricing table.

---

## 16. Immutable-config fingerprint

The fingerprint is SHA-256 over canonical JSON containing every root and nested `run-fixed` field, sorted according to canonical JSON rules.

It excludes:

```text
materialized_at
immutable_config_fingerprint
actual credential value
connect_timeout_seconds
first_event_timeout_seconds
idle_timeout_seconds
total_call_timeout_seconds
log_level
audit_retention_days
audit_max_total_bytes
audit_warning_threshold_bytes
```

The timeout fields are excluded because they have separate increase-only comparison. Resume-mutable fields are excluded because changes are permitted.

The environment-variable name `credential_env_var` is included.

---

## 17. Effective-config validation order

Code validates in this order:

1. root Schema and unknown fields;
2. scalar types, nullability, and ranges;
3. version support;
4. URL and credential-source rules;
5. provider/model capabilities;
6. timeout cross-field rules;
7. retry/backoff cross-field rules;
8. exact operation-map keys;
9. token-window calculations for all operations;
10. budget and pricing rules;
11. scene/manuscript planning rules;
12. editorial profile;
13. publishing profile;
14. audit threshold relationships;
15. immutable fingerprint calculation.

The Effective config is not written when any validation fails.

---

## 18. Complete redacted example

```json
{
  "audit_compression": "gzip",
  "audit_max_total_bytes": 1073741824,
  "audit_redaction_mode": "strict",
  "audit_retention_days": 30,
  "audit_store_request_body": true,
  "audit_store_response_body": true,
  "audit_warning_threshold_bytes": 805306368,
  "base_url": "https://api.example.invalid/v1",
  "cached_input_cost_per_million_tokens": null,
  "chapter_target_chars": 12000,
  "code_version": "1.0.0",
  "config_version": "1.0",
  "connect_timeout_seconds": 30,
  "credential_env_var": "STORYCRAFT_API_KEY",
  "editorial_profile": {
    "dialogue_guidance": "人物ごとの既定の話し方を維持し、説明目的だけの不自然な会話を避ける。",
    "forbidden_content": [],
    "language_tag": "ja-JP",
    "narrative_person": "third_person",
    "pov_distance": "close",
    "pov_policy": "single_pov_per_scene",
    "profile_id": "ja-novel-default",
    "prose_constraints": [
      "maintain one POV per scene",
      "avoid unexplained POV leakage",
      "preserve established speech anchors",
      "do not reveal forbidden disclosures",
      "do not add unsupported Canon facts"
    ],
    "tense": "past"
  },
  "editorial_profile_id": "ja-novel-default",
  "fallback_tokens_per_code_point": 2.0,
  "first_event_timeout_seconds": 120,
  "idle_timeout_seconds": 120,
  "immutable_config_fingerprint": "0000000000000000000000000000000000000000000000000000000000000000",
  "input_cost_per_million_tokens": 1.0,
  "log_level": "info",
  "materialized_at": "2026-07-22T09:15:30.123456Z",
  "max_active_elapsed_seconds": null,
  "max_completion_audit_attempts": 2,
  "max_context_tokens_by_operation": {
    "brief": 131072,
    "chapter_design": 131072,
    "completion_audit": 131072,
    "continuity_delta": 131072,
    "initial_design": 131072,
    "prose": 131072,
    "scene_card": 131072,
    "series_map": 131072,
    "volume_design": 131072,
    "volume_handoff": 131072
  },
  "max_estimated_cost": null,
  "max_llm_calls": null,
  "max_new_items_per_scene": 2,
  "max_response_structure_retries": 2,
  "max_revision_rounds": 1,
  "max_total_input_tokens": null,
  "max_total_output_tokens": null,
  "max_transport_retries": 2,
  "model": "example-model",
  "model_context_window_tokens": 131072,
  "output_cost_per_million_tokens": 2.0,
  "pricing_currency": "USD",
  "pricing_table_version": "2026-07-01",
  "prompt_bundle_version": "1.0.0",
  "protocol_overhead_tokens": 1024,
  "provider": "openai-compatible",
  "publishing_profile": {
    "auto_publish": false,
    "first_volume_access": "free",
    "later_volume_access": "paid",
    "manuscript_format": "markdown",
    "max_volumes": 10,
    "min_volumes": 4,
    "platform": "kdp",
    "profile_id": "kdp-series-default",
    "require_nonfinal_reader_question": true,
    "require_volume_local_resolution": true
  },
  "publishing_profile_id": "kdp-series-default",
  "reserved_output_tokens_by_operation": {
    "brief": 2048,
    "chapter_design": 4096,
    "completion_audit": 8192,
    "continuity_delta": 6144,
    "initial_design": 8192,
    "prose": 8192,
    "scene_card": 4096,
    "series_map": 4096,
    "volume_design": 4096,
    "volume_handoff": 4096
  },
  "retry_initial_backoff_seconds": 1.0,
  "retry_jitter_ratio": 0.2,
  "retry_max_backoff_seconds": 30.0,
  "scene_guide_max_chars": 5000,
  "scene_guide_min_chars": 500,
  "scene_target_chars": 3000,
  "schema_bundle_version": "1.0.0",
  "seed": null,
  "state_version": "1.0.0",
  "stream": true,
  "structured_output_mode": "json_schema",
  "temperature": 0.7,
  "thinking": false,
  "top_p": 1.0,
  "total_call_timeout_seconds": 900,
  "volume_target_chars": 60000,
  "workspace_version": "1.0.0"
}
```

The all-zero fingerprint is a documentation placeholder only and is forbidden in a real Effective config.

The example intentionally contains no credential value. The field `completion_audit_attempts_used` shown in some older drafts is not an Effective-config field and must not appear in a real file; implementations and fixtures must omit it.

---

## 19. Forbidden fields and deprecated names

The following are forbidden in Effective config:

```text
api_key
authorization
headers containing credentials
credential_value
environment
config_fingerprint
max_elapsed_seconds
reserved_output_tokens_by_operation.init
max_context_tokens_by_operation.init
auto_publish at root
completion_audit_attempts_used
```

Use:

```text
immutable_config_fingerprint
max_active_elapsed_seconds
reserved_output_tokens_by_operation.initial_design
max_context_tokens_by_operation.initial_design
publishing_profile.auto_publish
runtime/counters.json for usage counters
```

---

## 20. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
default materialization
unknown-field rejection
redacted Effective-config persistence
credential value exclusion from every persisted artifact
base URL credential and remote-HTTP rejection
provider capability validation
complete exact operation-key maps
model-window hard-limit calculation
precise tokenizer priority
conservative Japanese fallback estimate
timeout worker cancellation
transport classification
non-retryable HTTP classification
JSON failure excluded from transport retry
response-structure retry counting
empty prose response retry
semantic revision counting
residual-issue adoption after round exhaustion
independent Completion-audit attempts
retry backoff bounds
preflight budget stop
post-call actual-usage accounting
cost calculation
active elapsed-time accounting
scene length remains soft
new-item hard cap
editorial profile materialization
publishing profile volume range and auto-publish false
audit body redaction
audit warning and maximum behavior
retention excludes current run and non-audit artifacts
immutable fingerprint stability
run-fixed resume rejection
timeout decrease rejection
timeout increase acceptance
resume-mutable audit/log changes
Effective-config atomic replacement
placeholder fingerprint rejection
deprecated-field rejection
```
