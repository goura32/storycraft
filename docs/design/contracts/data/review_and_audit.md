# Data contracts: Review and audit

This document is the normative contract for:

- semantic Review content returned by all `*-02` review stages;
- normalized saved Review artifacts;
- actionable Issue records;
- residual issues preserved after revision exhaustion;
- Completion precondition reports and Completion-audit attempts;
- the accepted private Completion audit and its publication-safe projection;
- LLM-call audit records;
- code-operation audit records;
- publication mechanical validation and the final publication Gate result.

Candidate resume and audit filenames are defined by [`../ledger/runtime_records.md`](../ledger/runtime_records.md). Canon identity and enums are defined by [`../ledger/canon_records.md`](../ledger/canon_records.md). Story-state transitions are defined by [`../ledger/story_state.md`](../ledger/story_state.md). Scene Evidence is defined by [`../ledger/evidence_and_updates.md`](../ledger/evidence_and_updates.md). Effective retry, usage, pricing, redaction, and retention settings are defined by [`../../configuration_contracts.md`](../../configuration_contracts.md).

Every saved JSON object and every structured LLM response defined here uses `additionalProperties: false`.

---

## 1. Separation of concerns

Storycraft uses four different kinds of evaluation record.

| record | producer | purpose | resume authority | may contain author-only truth |
|---|---|---|---|---|
| Review content candidate | LLM reviewer | Identify semantic defects in one candidate | no | yes, when the reviewer context permits it |
| Saved Review artifact | code from structurally valid Review content | Immutable reviewed-candidate result | indirectly through Candidate manifest | yes |
| Residual issue record | code | Preserve unresolved Review issues after revision exhaustion | no | yes; never sent directly to prose generation |
| Audit record | code | Reconstruct execution, provider calls, validation, and adoption decisions | no | may contain redacted private context |

Review artifacts and audit records never become Canon, Story state, prose, planning, or publication content.

A Review issue does not directly edit a candidate. Revision stages always return complete replacement candidates.

---

## 2. Shared Review enums

### 2.1 Issue severity

```text
error
warning
```

Meaning:

| severity | meaning |
|---|---|
| `error` | The reviewer found a material contract, consistency, continuity, disclosure, or narrative-function defect |
| `warning` | The artifact is structurally valid but has a material quality or risk issue that should be revised when budget permits |

`info` is forbidden. Non-actionable observations belong in the Review summary, not `issues`.

Severity does not create an unbounded loop. Revision budget is controlled only by configuration and Candidate manifest counters.

### 2.2 Issue category

```text
brief_consistency
initial_design
planning
schema_semantics
canon
story_state
continuity
evidence
pov
characterization
relationship
thread
knowledge
time
ending
disclosure
prose_quality
completion
publication
other
```

### 2.3 Reviewed artifact role

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

### 2.4 Review result status

```text
issues_empty
issues_found
```

Code derives the status solely from the normalized issue count.

### 2.5 Issue location type

```text
json_pointer
text_quote
artifact
cross_artifact
```

---

## 3. LLM Review content candidate

Every LLM review stage returns exactly:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `summary` | string | yes | no | none | LLM | candidate-only | NFC `1..3000` code points; concise overall assessment; no provider/runtime commentary |
| `issues` | array<Issue content candidate> | yes | no | `[]` | LLM | candidate-only | `0..200`; no duplicates after normalization |

The LLM does not output:

```text
review status
issue IDs
operation ID
target ID
candidate path
candidate hash
prompt or Schema version
timestamps
revision count
retry count
next stage
adoption decision
```

Code derives or adds those values.

---

## 4. Issue content candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `code` | string | yes | no | none | LLM | candidate-only | pattern `[A-Z][A-Z0-9_]{2,63}`; concise stable rule-like code |
| `severity` | enum `issue_severity` | yes | no | none | LLM | candidate-only | `error` or `warning` |
| `category` | enum `issue_category` | yes | no | none | LLM | candidate-only | registry value |
| `rule_id` | string | yes | yes | `null` | LLM | candidate-only | null or NFC `1..200`; points to a named contract/acceptance rule without a filesystem absolute path |
| `artifact_role` | enum `reviewed_artifact_role` | yes | no | none | LLM | candidate-only | artifact containing the defect or primary side of a cross-artifact defect |
| `location` | Issue location | yes | no | none | LLM | candidate-only | complete Section 5 object |
| `description` | string | yes | no | none | LLM | candidate-only | NFC `1..2000`; states the concrete defect and expected condition |
| `suggested_change` | string | yes | no | none | LLM | candidate-only | NFC `1..2000`; actionable correction, not a partial JSON patch |
| `related_ids` | array<persistent ID or Scene ID> | yes | no | `[]` | LLM | candidate-only | unique, sorted; every ID available in reviewer context |
| `evidence_ids` | array<Evidence ID> | yes | no | `[]` | LLM | candidate-only | unique, sorted; only adopted Evidence IDs from reviewer context |

### 4.1 Duplicate issue rule

Two issues are duplicates when all normalized values below match:

```text
code
artifact_role
location
related_ids
```

Code keeps the first issue and rejects conflicting duplicates whose descriptions or severities differ.

### 4.2 Secret-content rule

A private Review issue may refer to author-only truth when necessary, but:

- the `description` must not reproduce more hidden detail than needed;
- raw prompt text is forbidden;
- credentials and provider headers are forbidden;
- publication-safe projections remove or generalize secret detail;
- Writer View never receives raw Issue records.

---

## 5. Issue location

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `location_type` | enum `issue_location_type` | yes | no | none | LLM | candidate-only | registry value |
| `json_pointer` | string | yes | yes | `null` | LLM | candidate-only | required iff type is `json_pointer`; valid RFC 6901 pointer or empty root pointer |
| `text_quote` | string | yes | yes | `null` | LLM | candidate-only | required iff type is `text_quote`; exact NFC substring of reviewed canonical text; `1..1000` code points |
| `related_artifact_roles` | array<enum `reviewed_artifact_role`> | yes | no | `[]` | LLM | candidate-only | nonempty iff type is `cross_artifact`; unique and sorted |
| `note` | string | yes | yes | `null` | LLM | candidate-only | null or NFC `1..750`; short locator explanation |

Conditional rules:

| location type | required non-null field |
|---|---|
| `json_pointer` | `json_pointer` |
| `text_quote` | `text_quote` |
| `artifact` | `note` |
| `cross_artifact` | `related_artifact_roles` and `note` |

Fields not required by the selected type are null or empty as defined above.

Code validates JSON pointers against the reviewed JSON artifact and text quotes against canonical reviewed text.

---

## 6. Normalized saved Review artifact

Saved path:

```text
<the active candidate directory>/review.json
```

Some legacy operation-specific review filenames are forbidden. Every candidate directory uses the fixed filename `review.json`.

### 6.1 Normalized Issue record

Code converts every valid Issue content candidate into:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|---|
| `issue_id` | string | yes | no | none | code | immutable | pattern `issue-[0-9]{4}`; contiguous from `0001` after canonical sorting |
| all Issue content fields | exact Section 4 types | yes | as defined | as defined | code from LLM | immutable | candidate contract plus target validation |

Canonical issue ordering:

1. severity, `error` before `warning`;
2. category registry order;
3. artifact role registry order;
4. normalized location;
5. code.

Issue IDs are assigned after sorting and are local to one Review artifact.

### 6.2 Issue-count object

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `error` | integer | yes | no | `0` | code | exact count, `>=0` |
| `warning` | integer | yes | no | `0` | code | exact count, `>=0` |
| `total` | integer | yes | no | `0` | code | equals error + warning |

### 6.3 Review artifact root

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | immutable | exact constant | saved Review artifact |
| `operation_id` | Stage ID | yes | no | none | code | immutable | exact review stage |
| `reviewed_artifact_role` | enum `reviewed_artifact_role` | yes | no | none | code | immutable | stage-compatible |
| `target_id` | string | yes | no | none | code | immutable | Candidate-manifest target |
| `candidate_path` | workspace-relative path | yes | no | none | code | immutable | exact reviewed candidate |
| `candidate_sha256` | SHA-256 | yes | no | none | code | immutable | matches canonical candidate bytes |
| `input_snapshot_sha256` | SHA-256 | yes | no | none | code | immutable | equals Candidate manifest |
| `review_prompt_version` | string | yes | no | none | code | immutable | exact prompt version |
| `review_schema_version` | string | yes | no | none | code | immutable | exact structured response Schema |
| `review_round` | integer | yes | no | `1` | code | immutable | one-based count for this candidate version |
| `candidate_version` | integer | yes | no | none | code | immutable | equals Candidate manifest candidate version |
| `summary` | string | yes | no | none | code from LLM | immutable | Section 3 |
| `issues` | array<Normalized Issue record> | yes | no | `[]` | code | immutable | canonical order and local IDs |
| `issue_counts` | Issue-count object | yes | no | zero object | code | immutable | exact |
| `review_status` | enum `review_result_status` | yes | no | none | code | immutable | `issues_empty` iff total is zero |
| `call_id` | Call ID | yes | no | none | code | immutable | LLM call that produced the accepted structurally valid Review response |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | accepted Review-response time |

The Review artifact contains no adoption decision. Candidate manifest and the Pipeline determine whether to revise, adopt, or stop.

---

## 7. Review-stage behavioral rules

### 7.1 Structural failure

The following are response-structure failures:

```text
invalid JSON
Review Schema failure
unknown field
invalid enum
invalid Issue location
Issue JSON pointer that does not resolve
Issue text quote that is not found
duplicate conflicting Issue records
```

They consume response-structure retries, not revision rounds.

### 7.2 Semantic issues

A structurally valid Review with one or more issues:

- sets `review_status=issues_found`;
- consumes no response retry;
- sends the whole candidate to revision when a revision round remains;
- may proceed with residual issues after revision exhaustion.

### 7.3 Empty issues

A structurally valid Review with `issues=[]`:

- sets `review_status=issues_empty`;
- moves the candidate toward code validation/adoption;
- does not guarantee later mechanical validation will succeed.

### 7.4 Review cannot mutate

A Review stage must not:

```text
rewrite candidate fields
return a corrected candidate
allocate IDs
change source generation
change the frozen Scene card or prose
change retry/revision counters
mark publication complete
```

---

## 8. Residual issue audit

Canonical path:

```text
audit/residual-issues.jsonl
```

Each line is one canonical compact JSON object followed by LF. The file is append-only while the workspace lock is held.

### 8.1 Residual issue record

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | immutable | exact |
| `run_id` | Run ID | yes | no | none | code | immutable | active run |
| `operation_id` | Stage ID | yes | no | none | code | immutable | adoption/check stage that accepted the candidate |
| `target_id` | string | yes | no | none | code | immutable | adopted target |
| `candidate_path` | workspace-relative path | yes | no | none | code | immutable | accepted candidate |
| `candidate_sha256` | SHA-256 | yes | no | none | code | immutable | accepted candidate hash |
| `review_path` | workspace-relative path | yes | no | none | code | immutable | Review artifact |
| `review_sha256` | SHA-256 | yes | no | none | code | immutable | Review artifact hash |
| `revision_rounds_used` | integer | yes | no | none | code | immutable | equals exhausted Candidate-manifest count |
| `issue` | Normalized Issue record | yes | no | none | code | immutable | exact unresolved Review issue |
| `adopted_artifact_path` | workspace-relative path | yes | yes | `null` | code | immutable | null when adoption path is not yet known; otherwise final adopted path |
| `adopted_commit_id` | Commit ID | yes | yes | `null` | code | immutable | non-null for scene/Genesis adoption |
| `adopted_generation_id` | Generation ID | yes | yes | `null` | code | immutable | non-null for scene/Genesis adoption |
| `recorded_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | adoption decision time |

One line is written per unresolved issue.

Residual issues are private audit input. Context Builder may produce a safe task-specific constraint from them, but never passes raw residual records to prose generation or publication.

---

# Part I: Completion audit

## 9. Completion precondition report

COMP-PRE is code-only and writes:

```text
audit/completion/<generation-id>/completion-precondition.json
```

### 9.1 Mechanical check result

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `check_id` | string | yes | no | none | code | pattern `[A-Z][A-Z0-9_]{2,63}`; unique |
| `status` | enum | yes | no | none | code | `pass` or `fail` |
| `artifact_path` | workspace-relative path | yes | yes | `null` | code | null or checked artifact |
| `artifact_sha256` | SHA-256 | yes | yes | `null` | code | null iff no artifact path |
| `message` | string | yes | no | none | code | sanitized NFC `1..1000` |

### 9.2 Precondition root

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | immutable | exact |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | current valid HEAD |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | source generation |
| `brief_path` | constant path `input/brief.json` | yes | no | exact | code | immutable | exists and hashes |
| `brief_sha256` | SHA-256 | yes | no | none | code | immutable | adopted Brief |
| `series_map_path` | constant path `plans/series-map.json` | yes | no | exact | code | immutable | exists and hashes |
| `series_map_sha256` | SHA-256 | yes | no | none | code | immutable | adopted Series map |
| `final_volume_number` | integer | yes | no | none | code | immutable | equals Brief volumes |
| `final_scene_id` | Scene ID | yes | no | none | code | immutable | equals Story-clock last scene |
| `current_order` | integer | yes | no | none | code | immutable | equals Story clock |
| `checks` | array<Mechanical check result> | yes | no | none | code | immutable | nonempty; sorted by check ID |
| `all_checks_pass` | boolean | yes | no | none | code | immutable | true iff every check passes |
| `context_snapshot_path` | workspace-relative path | yes | no | none | code | immutable | Completion-audit Context snapshot built from this exact generation |
| `context_snapshot_sha256` | SHA-256 | yes | no | none | code | immutable | matches snapshot |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | UTC |

Minimum checks:

```text
HEAD and Generation/Commit manifest validity
Brief Volume count
final Volume/Chapter/Scene position
all planned Volumes and Chapters present
all adopted Scene manifests and hashes
Story-state reference integrity
required Major Thread records and State rows
required Ending criteria
Evidence-index integrity
no unresolved staging/checkpoint transaction
no invalid current publication pointer
```

COMP-AUDIT is not invoked unless `all_checks_pass=true`.

---

## 10. Completion-audit content candidate

The Completion auditor receives one immutable Completion Context snapshot and returns exactly:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `criteria_assessments` | array<Criterion assessment candidate> | yes | no | none | LLM | candidate-only | exactly one per adopted Ending criterion; sorted by ID after normalization |
| `thread_assessments` | array<Thread assessment candidate> | yes | no | none | LLM | candidate-only | exactly one per adopted required Major Thread; sorted |
| `contradictions` | array<Completion contradiction candidate> | yes | no | `[]` | LLM | candidate-only | unique normalized records |
| `residual_issues` | array<Completion residual assessment candidate> | yes | no | `[]` | LLM | candidate-only | exactly one per relevant residual issue supplied by context |
| `overall_assessment` | enum `completion_overall_assessment` | yes | no | none | LLM | candidate-only | derived-consistency rules in Section 15 |
| `summary` | string | yes | no | none | LLM | candidate-only | NFC `1..4000`; concise rationale |

The LLM does not output:

```text
audit attempt number
source generation
hash
path
timestamp
call ID
publication decision
retry count
```

---

## 11. Completion enums

### 11.1 Criterion assessment

```text
satisfied
partially_supported
unsupported
contradicted
```

### 11.2 Thread assessment

```text
resolved
unresolved
retired_unacceptably
inconsistent
```

### 11.3 Contradiction severity

```text
material
minor
```

### 11.4 Residual issue disposition

```text
acceptable
publication_warning
blocks_completion
superseded
```

### 11.5 Overall assessment

```text
complete
complete_with_residual_issues
incomplete
```

---

## 12. Criterion assessment candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `criterion_id` | Ending criterion ID | yes | no | none | LLM | candidate-only | adopted criterion |
| `required` | boolean | yes | no | none | LLM | candidate-only | exactly matches adopted criterion |
| `supports_evidence_ids` | array<Evidence ID> | yes | no | `[]` | LLM | candidate-only | unique, sorted; each supports this criterion |
| `contradicts_evidence_ids` | array<Evidence ID> | yes | no | `[]` | LLM | candidate-only | unique, sorted; each contradicts this criterion |
| `assessment` | enum `criterion_assessment` | yes | no | none | LLM | candidate-only | evidence-consistent |
| `explanation` | string | yes | no | none | LLM | candidate-only | NFC `1..2000`; cites evidence IDs rather than reproducing long prose |

Assessment rules:

| condition | permitted assessment |
|---|---|
| strong supporting evidence and no material contradiction | `satisfied` |
| some support but criterion not fully established | `partially_supported` |
| no sufficient support and no contradiction | `unsupported` |
| material contradicting evidence | `contradicted` |

A required criterion assessed other than `satisfied` forces overall `incomplete`.

---

## 13. Thread assessment candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `thread_id` | Thread ID | yes | no | none | LLM | candidate-only | adopted required Major Thread |
| `required` | constant boolean `true` | yes | no | `true` | LLM | candidate-only | exact true |
| `thread_status` | enum `thread_status` | yes | no | none | LLM | candidate-only | equals final Story state |
| `progress` | integer | yes | no | none | LLM | candidate-only | equals final Story state |
| `evidence_ids` | array<Evidence ID> | yes | no | `[]` | LLM | candidate-only | unique, sorted; relevant Thread evidence |
| `assessment` | enum `thread_assessment` | yes | no | none | LLM | candidate-only | status/evidence-consistent |
| `explanation` | string | yes | no | none | LLM | candidate-only | NFC `1..2000` |

Rules:

```text
resolved:
  thread_status = resolved
  progress = 4
  evidence establishes resolution

unresolved:
  thread_status = open or in_progress

retired_unacceptably:
  thread_status = retired

inconsistent:
  stored status/progress or evidence conflicts
```

Any assessment other than `resolved` forces overall `incomplete`.

---

## 14. Completion contradiction and residual assessment

### 14.1 Completion contradiction candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `code` | string | yes | no | none | LLM | candidate-only | `[A-Z][A-Z0-9_]{2,63}` |
| `severity` | enum `completion_contradiction_severity` | yes | no | none | LLM | candidate-only | `material` or `minor` |
| `description` | string | yes | no | none | LLM | candidate-only | NFC `1..2000` |
| `related_ids` | array<persistent ID or Scene ID> | yes | no | `[]` | LLM | candidate-only | unique, sorted |
| `evidence_ids` | array<Evidence ID> | yes | no | `[]` | LLM | candidate-only | nonempty for prose-grounded contradiction |
| `explanation` | string | yes | no | none | LLM | candidate-only | NFC `1..2000` |

Any `material` contradiction forces overall `incomplete`.

### 14.2 Completion residual assessment candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `operation_id` | Stage ID | yes | no | none | LLM | candidate-only | exact residual-context record |
| `target_id` | string | yes | no | none | LLM | candidate-only | exact residual-context record |
| `candidate_sha256` | SHA-256 | yes | no | none | LLM | candidate-only | exact residual-context record |
| `issue_code` | string | yes | no | none | LLM | candidate-only | exact residual issue code |
| `disposition` | enum `residual_issue_disposition` | yes | no | none | LLM | candidate-only | context-consistent |
| `explanation` | string | yes | no | none | LLM | candidate-only | NFC `1..1500` |

A `blocks_completion` disposition forces overall `incomplete`.

At least one `publication_warning` with no blocking finding requires `complete_with_residual_issues`.

---

## 15. Completion overall-assessment consistency

### 15.1 `complete`

Permitted only when:

```text
every required Ending criterion = satisfied
every required Major Thread = resolved
no material contradiction
no residual issue = blocks_completion
no residual issue = publication_warning
```

### 15.2 `complete_with_residual_issues`

Permitted only when:

```text
every required Ending criterion = satisfied
every required Major Thread = resolved
no material contradiction
no residual issue = blocks_completion
at least one warning-level condition exists:
  publication_warning
  minor contradiction
  acceptable unresolved quality risk
```

### 15.3 `incomplete`

Required when any is true:

```text
required criterion not satisfied
required Major Thread not resolved
material contradiction
residual issue blocks completion
stored final State is inconsistent
```

Code mechanically verifies that the LLM's overall value follows these rules.

A semantically `incomplete` but structurally valid audit is not response-retried and does not consume another Completion-audit attempt. Attempt retries exist only to obtain a structurally valid audit result.

---

## 16. Saved Completion-audit attempt

Candidate attempt path:

```text
runtime/candidates/completion/attempt-01.json
runtime/candidates/completion/attempt-02.json
```

The saved attempt contains:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | immutable | exact |
| `audit_attempt` | integer | yes | no | none | code | immutable | one-based and matches filename |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | Completion precondition source |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | source generation |
| `precondition_path` | workspace-relative path | yes | no | none | code | immutable | exact Completion-precondition report |
| `precondition_sha256` | SHA-256 | yes | no | none | code | immutable | matches report |
| `context_snapshot_path` | workspace-relative path | yes | no | none | code | immutable | immutable Completion Context snapshot |
| `context_snapshot_sha256` | SHA-256 | yes | no | none | code | immutable | matches snapshot |
| `prompt_version` | string | yes | no | none | code | immutable | Completion-audit prompt |
| `response_schema_version` | string | yes | no | none | code | immutable | Completion-audit response Schema |
| all Completion-audit content fields | exact Sections 10–14 types | yes | as defined | as defined | code from LLM | immutable | content and consistency rules |
| `call_id` | Call ID | yes | no | none | code | immutable | accepted structurally valid call |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | UTC |

A structurally invalid attempt is preserved only in the LLM call audit, not as `attempt-NN.json`.

---

## 17. Accepted private Completion audit

COMP-SAVE copies the first structurally valid attempt to:

```text
audit/completion/<generation-id>/completion-audit.json
```

and adds:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `accepted_attempt_path` | workspace-relative path | yes | no | none | code | exact accepted attempt |
| `accepted_attempt_sha256` | SHA-256 | yes | no | none | code | matches attempt |
| `saved_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

The private audit may contain author-only references supplied through the Completion Context. It is never placed directly into publication content.

---

## 18. Publication-safe Completion report

OUT-01 creates:

```text
.staging/publication/<publication-id>/reports/completion-audit.json
```

from the accepted private Completion audit.

### 18.1 Safe criterion summary

```text
criterion_id
required
assessment
support_count
contradiction_count
safe_explanation
```

### 18.2 Safe Thread summary

```text
thread_id
assessment
status
progress
evidence_count
safe_explanation
```

### 18.3 Safe residual summary

```text
issue_code
disposition
safe_explanation
```

### 18.4 Safe report root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | exact |
| `source_generation_id` | Generation ID | yes | no | none | code | accepted audit source |
| `overall_assessment` | enum `completion_overall_assessment` | yes | no | none | code | accepted audit value |
| `criteria` | array<Safe criterion summary> | yes | no | none | code | one per criterion; sorted |
| `threads` | array<Safe Thread summary> | yes | no | none | code | one per required Major Thread; sorted |
| `contradiction_count` | integer | yes | no | `0` | code | exact |
| `residual_issues` | array<Safe residual summary> | yes | no | `[]` | code | safe and sorted |
| `summary` | string | yes | no | none | code | sanitized NFC summary |
| `private_audit_sha256` | SHA-256 | yes | no | none | code | hash only; no private path |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

The safe report excludes:

```text
author truth
Thread resolution conditions
Ending source text
raw Evidence quotes
workspace paths
raw residual Issue descriptions
prompts
responses
provider metadata
credentials
```

---

# Part II: LLM call audit

## 19. LLM call audit path

Canonical unique path:

```text
audit/llm-calls/
  <sequence>__<operation-id>__<target-id>__<role>__attempt-<NN>[__round-<NN>].json.gz
```

The filename contract and Call-ID allocation are defined by `runtime_records.md`.

The gzip member contains exactly one canonical JSON object and no concatenated members.

---

## 20. LLM call outcome enums

### 20.1 Outcome

```text
success
transport_error
response_structure_error
cancelled
```

### 20.2 Transport error code

```text
dns_failure
connection_failure
tls_failure
connection_reset
stream_interruption
connect_timeout
first_event_timeout
idle_timeout
total_call_timeout
http_retryable
http_nonretryable
```

### 20.3 Structure error code

```text
utf8_decode
json_parse
schema
required_field
unknown_field
enum
conditional_rule
empty_prose
```

### 20.4 Usage source

```text
provider
tokenizer
fallback_estimate
zero_unbilled
```

---

## 21. Audit request/response body record

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `stored` | boolean | yes | no | none | code | matches Effective config and redaction outcome |
| `media_type` | string | yes | no | none | code | NFC MIME type |
| `sha256` | SHA-256 | yes | no | none | code | hash of complete redacted canonical body bytes |
| `size_bytes` | integer | yes | no | none | code | exact redacted-body byte size |
| `content` | string | yes | yes | `null` | code | non-null iff stored; redacted UTF-8 text |
| `redactions` | array<string> | yes | no | `[]` | code | unique redaction labels; no removed secret values |

When `stored=false`, code still hashes the redacted body before discarding content.

Binary provider bodies are base64-encoded only when the registered adapter requires it; the media type and encoding label must then be explicit in content. Version 1 normally audits JSON or text.

---

## 22. Usage record

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `source` | enum `usage_source` | yes | no | none | code | registry value |
| `input_tokens` | integer | yes | no | `0` | code | `>=0` |
| `cached_input_tokens` | integer | yes | no | `0` | code | `>=0` and `<=input_tokens` |
| `output_tokens` | integer | yes | no | `0` | code | `>=0` |
| `reasoning_tokens` | integer | yes | no | `0` | code | `>=0`; included in output cost according to provider adapter |
| `estimated_cost` | number | yes | no | `0` | code | finite `>=0` |
| `currency` | string | yes | no | none | code | equals Effective config pricing currency |
| `pricing_table_version` | string | yes | no | none | code | equals Effective config |

---

## 23. Timing record

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `started_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |
| `connected_at` | RFC 3339 UTC timestamp | yes | yes | `null` | code | null when no connection completed |
| `first_event_at` | RFC 3339 UTC timestamp | yes | yes | `null` | code | null when no response event |
| `completed_at` | RFC 3339 UTC timestamp | yes | no | none | code | not earlier than started |
| `duration_seconds` | number | yes | no | none | code | finite `>=0` |
| `retry_backoff_seconds_before_call` | number | yes | no | `0` | code | finite `>=0` |

---

## 24. LLM error record

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `transport_error_code` | enum `transport_error_code` | yes | yes | `null` | code | non-null iff outcome transport error |
| `structure_error_code` | enum `structure_error_code` | yes | yes | `null` | code | non-null iff outcome structure error |
| `http_status` | integer | yes | yes | `null` | code | null or `100..599` |
| `provider_error_code` | string | yes | yes | `null` | code | sanitized provider code |
| `message` | string | yes | no | none | code | sanitized NFC `1..2000`; no credential/body dump |
| `retryable` | boolean | yes | no | none | code | classification from configuration contract |

Exactly one of transport and structure error codes is non-null for their respective outcomes. Both are null for `success` and `cancelled`.

---

## 25. LLM call audit root

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | immutable | exact |
| `run_id` | Run ID | yes | no | none | code | immutable | active run |
| `call_id` | Call ID | yes | no | none | code | immutable | matches filename sequence |
| `operation_id` | Stage ID | yes | no | none | code | immutable | exact stage |
| `target_id` | string | yes | no | none | code | immutable | matches filename |
| `role` | enum `audit_call_role` | yes | no | none | code | immutable | matches stage and filename |
| `attempt` | integer | yes | no | none | code | immutable | one-based logical/transport attempt as defined by adapter audit policy |
| `revision_round` | integer | yes | yes | `null` | code | immutable | non-null only for revise role |
| `completion_audit_attempt` | integer | yes | yes | `null` | code | immutable | non-null only for COMP-AUDIT |
| `provider` | string | yes | no | none | code | immutable | Effective config |
| `base_url` | string | yes | no | none | code | immutable | normalized credential-free URL |
| `model` | string | yes | no | none | code | immutable | Effective config |
| `prompt_version` | string | yes | yes | `null` | code | immutable | non-null for LLM call |
| `response_schema_version` | string | yes | yes | `null` | code | immutable | null for prose text call; otherwise exact Schema |
| `input_snapshot_sha256` | SHA-256 | yes | no | none | code | immutable | exact logical call input |
| `effective_config_sha256` | SHA-256 | yes | no | none | code | immutable | config used |
| `request` | Audit body record | yes | no | none | code | immutable | redacted |
| `response` | Audit body record | yes | yes | `null` | code | immutable | null only when no response body was obtained |
| `outcome` | enum `llm_call_outcome` | yes | no | none | code | immutable | registry value |
| `finish_reason` | string | yes | yes | `null` | code | immutable | sanitized provider finish reason |
| `usage` | Usage record | yes | no | none | code | immutable | complete |
| `timing` | Timing record | yes | no | none | code | immutable | complete |
| `error` | LLM error record | yes | yes | `null` | code | immutable | null iff outcome success |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | audit-write time |

A transport retry creates a separate Call audit file only when it receives a separately allocated Call ID under the Runtime policy. The implementation must use one consistent policy and counters must equal the number of created call records. The recommended version-1 policy is one Call ID per provider HTTP attempt.

---

# Part III: Code-operation audit

## 26. Operation audit path

Code-only events use unique files:

```text
audit/operations/
  <timestamp-basic>__<operation-id>__<target-id>__<event>.json
```

Example:

```text
20260722T091530123456Z__commit-04__v01-c001-s001__adopted.json
```

Files are immutable and never overwritten.

### 26.1 Operation outcome

```text
success
failure
warning
```

### 26.2 Operation audit root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | exact |
| `run_id` | Run ID | yes | no | none | code | active run |
| `operation_id` | Stage ID or registered runtime operation | yes | no | none | code | known value |
| `target_id` | string | yes | no | none | code | sanitized target |
| `event` | string | yes | no | none | code | `[a-z][a-z0-9_-]{1,63}` |
| `outcome` | enum `operation_outcome` | yes | no | none | code | registry value |
| `input_refs` | array<Audit artifact reference> | yes | no | `[]` | code | unique, sorted |
| `output_refs` | array<Audit artifact reference> | yes | no | `[]` | code | unique, sorted |
| `message` | string | yes | no | none | code | sanitized NFC `1..2000` |
| `details` | object<string, scalar or array<string>> | yes | no | `{}` | code | registered event-specific keys only; secret-free |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

### 26.3 Audit artifact reference

```text
path
sha256
role
```

All paths are workspace-relative. The referenced artifact may later be quarantined, but the audit record remains immutable.

---

# Part IV: Publication validation and Gate

## 27. Publication validation

OUT-02 writes the validation file inside the current publication transaction root.
Before adoption that root is:

```text
.staging/publication/<publication-id>/
```

After OUT-03 rename, the same relative file is:

```text
publications/<publication-id>/publication-validation.json
```

No persisted Validation or Gate field stores the staging-root path.

### 27.1 Publication check result

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `check_id` | string | yes | no | none | code | `[A-Z][A-Z0-9_]{2,63}`; unique |
| `status` | enum | yes | no | none | code | `pass` or `fail` |
| `relative_path` | relative publication path | yes | yes | `null` | code | null or path inside the publication root; never starts with `.staging/` or `publications/` |
| `sha256` | SHA-256 | yes | yes | `null` | code | null iff no file path is being checked |
| `message` | string | yes | no | none | code | sanitized NFC `1..1000` |

### 27.2 Publication payload set

The Validation record hashes the publication payload set, not the final manifest file set.

The payload set contains every final publication file except:

```text
publication-validation.json
publication-manifest.json
publication-build-manifest.json
```

It therefore includes:

```text
manuscript files
metadata files
publication-safe reports
other profile-defined final payload files
```

`payload_set_sha256` is SHA-256 over canonical JSON containing the sorted records:

```text
relative_path
sha256
size_bytes
media_type
role
```

The records use the same field meanings and ordering as Publication-manifest file references.

This separation prevents a hash cycle:

```text
Validation
  hashes payload files only

Publication manifest
  hashes its complete files array,
  including publication-validation.json,
  but excluding publication-manifest.json itself
```

### 27.3 Publication-validation root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | exact |
| `publication_id` | Publication ID | yes | no | none | code | target publication transaction/adopted directory |
| `source_generation_id` | Generation ID | yes | no | none | code | source generation |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | matches source |
| `publishing_profile_id` | string | yes | no | none | code | Effective config |
| `checks` | array<Publication check result> | yes | no | none | code | nonempty; sorted by check ID |
| `validation_status` | enum | yes | no | none | code | `pass` iff every check passes; otherwise `fail` |
| `validated_payload_file_count` | integer | yes | no | none | code | exact number of payload-set records; `>=0` |
| `payload_set_sha256` | SHA-256 | yes | no | none | code | Section 27.2 payload-set hash |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

Minimum checks:

```text
all expected Volumes present
manuscript files parse as permitted publication format
no internal IDs in reader-facing manuscript
no forbidden internal path
metadata completeness
publication-safe Completion report
payload file hashes, byte sizes, roles, and media types
Publishing-profile constraints
no credential, prompt, raw response, or author-truth leakage
no provisional build manifest in the final payload set
```

The Validation file does not contain `content_set_sha256` or the final Publication-manifest hash.
Those values are known only after the Validation file itself has been finalized and referenced by the final Publication manifest.

---

## 28. Publication Gate result

COMP-PUBLISH writes outside publication content:

```text
audit/publication-gates/<publication-id>.json
```

The Gate is an immutable audit decision. It must remain valid after the publication directory moves from staging to its adopted path.

### 28.1 Gate source role

```text
completion_precondition
completion_audit
source_generation
publication_validation
publication_manifest
publication_content
output_current
```

### 28.2 Gate failure

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `code` | string | yes | no | none | code | `[A-Z][A-Z0-9_]{2,63}` |
| `source_role` | enum `gate_source_role` | yes | no | none | code | Section 28.1 value |
| `artifact_path` | workspace-relative path | yes | yes | `null` | code | stable external path; forbidden for publication-internal roles; never a `.staging/publication/...` path |
| `publication_relative_path` | relative publication path | yes | yes | `null` | code | publication-root-relative path for publication-internal roles |
| `sha256` | SHA-256 | yes | yes | `null` | code | actual or expected hash when applicable |
| `message` | string | yes | no | none | code | sanitized NFC `1..1000` |

Conditional rules:

```text
source_role = publication_validation | publication_manifest | publication_content:
  artifact_path = null
  publication_relative_path is non-null

source_role = completion_precondition | completion_audit | source_generation | output_current:
  artifact_path is non-null
  publication_relative_path = null
```

### 28.3 Publication snapshot hash

The Gate stores one rename-stable `publication_snapshot_sha256`.

It is SHA-256 over canonical JSON containing exactly:

```text
publication_id
source_generation_id
source_generation_manifest_sha256
publication_validation_relative_path
publication_validation_sha256
publication_manifest_relative_path
publication_manifest_sha256
payload_set_sha256
content_set_sha256
```

All paths in this object are publication-root-relative.

### 28.4 Gate root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | exact |
| `publication_id` | Publication ID | yes | no | none | code | target publication |
| `source_generation_id` | Generation ID | yes | no | none | code | publication source |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | matches source Generation manifest |
| `completion_precondition_path` | workspace-relative path | yes | no | none | code | valid passing precondition; stable external audit path |
| `completion_precondition_sha256` | SHA-256 | yes | no | none | code | matches |
| `completion_audit_path` | workspace-relative path | yes | no | none | code | accepted private Completion audit; stable external audit path |
| `completion_audit_sha256` | SHA-256 | yes | no | none | code | matches |
| `completion_overall_assessment` | enum `completion_overall_assessment` | yes | no | none | code | accepted audit value |
| `publication_validation_relative_path` | constant relative path `publication-validation.json` | yes | no | exact | code | listed by final Publication manifest with role `validation` |
| `publication_validation_sha256` | SHA-256 | yes | no | none | code | matches Validation file |
| `publication_manifest_relative_path` | constant relative path `publication-manifest.json` | yes | no | exact | code | exact constant |
| `publication_manifest_sha256` | SHA-256 | yes | no | none | code | matches final Publication manifest |
| `payload_set_sha256` | SHA-256 | yes | no | none | code | equals passing Validation value and recomputed payload set |
| `content_set_sha256` | SHA-256 | yes | no | none | code | equals final Publication-manifest value and recomputed complete file-reference set |
| `publication_snapshot_sha256` | SHA-256 | yes | no | none | code | Section 28.3 |
| `gate_status` | enum | yes | no | none | code | `pass` or `fail` |
| `failures` | array<Gate failure> | yes | no | `[]` | code | empty iff pass |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | UTC |

### 28.5 Gate pass conditions

Gate pass requires:

```text
Completion precondition all_checks_pass = true
accepted Completion audit is structurally valid
Completion overall assessment is:
  complete
  OR complete_with_residual_issues
source generation still equals current canon/HEAD
Publication validation status = pass
Validation payload_set_sha256 matches the recomputed payload set
Publication manifest lists the Validation file with the exact Validation hash
Publication manifest content_set_sha256 matches its complete sorted files array
all Publication-manifest file references resolve under the current publication root
publication_snapshot_sha256 recomputes exactly
the final adopted publication directory does not conflict with this publication ID
```

At normal COMP-PUBLISH time, the current publication root is:

```text
.staging/publication/<publication-id>/
```

The Gate stores only the Publication ID and relative paths, not that root.

### 28.6 OUT-03 and crash-recovery resolution

OUT-03 resolves the Gate's publication-relative references against:

```text
normal pre-adoption:
  .staging/publication/<publication-id>/

explicit recovery after directory rename but before CURRENT update:
  publications/<publication-id>/
```

Exactly one root may be selected for one OUT-03 execution.
The selected root must reproduce every Gate hash and `publication_snapshot_sha256`.

A Gate remains valid after rename because none of its publication-internal references contain the staging or adopted root prefix.

`incomplete` never triggers another Completion-audit attempt and never passes the Gate.

COMP-PUBLISH performs no rename, publication adoption, Publication-manifest mutation, or `output/CURRENT` update.
OUT-03 alone performs those actions after revalidating the passing Gate result.

---

## 29. Audit redaction and projection rules

### 29.1 Always forbidden

No Review or audit artifact may contain:

```text
credential value
Authorization header
cookie
complete environment dump
absolute path outside workspace
unredacted provider secret
private key
database password
```

### 29.2 Private but permitted

Private Review/Completion/audit storage may contain, when necessary:

```text
author truth
Thread resolution condition
Ending criterion source text
raw prompt
raw response
private Context snapshot references
```

subject to configured body-storage and strict redaction rules.

### 29.3 Never publication-safe without projection

The following are removed or generalized before publication:

```text
author truth
raw Ending source text
Thread resolution condition
raw Evidence quote
raw Issue description
internal workspace path
prompt/Schema/provider metadata
Call ID
candidate/review/runtime path
```

A publication-safe report may retain persistent story IDs for machine debugging only when the Publishing profile explicitly allows them. The default KDP profile retains criterion/thread IDs in the non-manuscript report but never inserts them into reader-facing manuscript text.

---

## 30. Cross-record invariants

A valid review/audit set satisfies:

```text
saved Review candidate hash equals Candidate manifest
Review issue IDs are local, contiguous, and sorted
Review status equals issue count
Candidate manifest review hash equals saved Review
residual issue lines reproduce unresolved normalized issues exactly
Completion precondition generation equals current HEAD at audit start
Completion attempt context hash equals precondition context hash
Completion criterion and Thread coverage is complete
Completion overall assessment follows finding rules
accepted private audit hash equals accepted attempt projection
safe Completion report hash is listed in Publication manifest
Publication validation payload-set hash matches its payload files
Publication manifest content-set hash matches its complete files array
Gate stores only rename-stable publication-relative references
Gate publication snapshot hash matches the selected current publication root
Gate input hashes match current files
Gate pass excludes incomplete Completion audit
no audit filename is reused
no adopted or publication-safe artifact contains forbidden secret content
```

---

## 31. Forbidden fields and deprecated forms

Forbidden in LLM Review content:

```text
issue_id
review_status
operation_id
target_id
candidate_sha256
revision_rounds_used
next_stage
adopt
reject
timestamp
```

Forbidden in Completion-audit content:

```text
audit_attempt
source_generation_id
hash
path
call_id
retry_count
publish
do_not_publish
```

Forbidden deprecated Review forms:

```text
issues: array<string>
severity without registered enum
free-form path with no location type
review candidate as artifact class
Review result directly editing candidate
```

Forbidden deprecated audit paths and Gate references:

```text
audit/llm-calls/prose-01.json.gz
audit/reviews/sc-02.json.gz
audit/operations/init-05.json.gz for an LLM call
publication_validation_path = .staging/publication/<id>/publication-validation.json
publication_manifest_path = .staging/publication/<id>/publication-manifest.json
Gate failure artifact_path pointing inside .staging/publication/
```

Use the unique Runtime filename and exact schemas in this document.

---

## 32. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
Review content exact Schema
Issue code, severity, category, and location validation
JSON-pointer existence
text-quote existence
duplicate Issue rejection
normalized Issue ordering and local IDs
Review count/status derivation
Review cannot make adoption decision
structure retry versus semantic revision classification
whole-candidate revision behavior
residual issue JSONL canonical append
raw residual issue exclusion from Writer/publication
Completion precondition exact root and minimum checks
Completion audit complete criterion coverage
Completion audit complete required-Thread coverage
Ending Evidence reference validation
Thread final-State equality
contradiction and residual disposition rules
overall Completion assessment derivation
structurally invalid attempt retry
semantically incomplete audit does not retry
accepted private Completion audit
publication-safe Completion projection
LLM call audit unique filename and exact root
request/response redaction and hashes
usage and cost accounting
timing and error classification
code-operation audit uniqueness
publication validation exact root
cycle-free payload_set_sha256 calculation
final Publication-manifest content_set_sha256 calculation
rename-stable Gate relative references
Gate publication_snapshot_sha256 calculation
Gate resolution against staging and explicit post-rename recovery roots
publication Gate pass/fail rules
COMP-PUBLISH performs no adoption
secret-content rejection
cross-record hash consistency
unknown-field rejection
```
