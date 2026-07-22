# Ledger contracts: Evidence and continuity updates

This document is the normative contract for:

- scene-derived continuity-update candidates;
- the normalized committed continuity delta;
- adopted prose evidence records;
- new-record proposal validation;
- the mapping from accepted prose evidence to Canon and Story-state changes.

Stable records and domain enums are defined by [`canon_records.md`](canon_records.md). Mutable adopted values and transition matrices are defined by [`story_state.md`](story_state.md). Runtime manifests and commit transactions are defined by [`runtime_records.md`](runtime_records.md).

Every saved object defined here uses `additionalProperties: false`.

An LLM proposes narrative changes. Code owns persistent IDs, exact target resolution, canonical offsets, hashes, merge validation, serialization, and adoption.

---

## 1. Artifact boundaries

Three related artifacts have different responsibilities.

| artifact | canonical path | producer | purpose | persistent IDs permitted |
|---|---|---|---|---|
| Raw continuity response | LLM call audit only | LLM | Untrusted structured proposal before code normalization | Existing IDs supplied in context only; no new persistent IDs |
| Validated continuity candidate | `runtime/checkpoints/scenes/vNN/cNNN/sNNN/continuity-delta.json` | code from accepted DELTA candidate | Resume-safe, structurally valid proposal with code-injected scene and HEAD `before` values | Existing IDs only; new records use `local_key` |
| Committed continuity delta | `artifacts/scenes/vNN/cNNN/sNNN/continuity-delta.json` | code during COMMIT-03 | Immutable historical description of the changes adopted by the scene commit | Persistent IDs and Evidence IDs only |

The validated candidate and committed delta intentionally use different schemas even though the filename is the same. The path determines the applicable schema.

The Evidence index is stored at:

```text
canon/generations/<generation-id>/evidence-index.json
```

---

## 2. Shared candidate rules

- The LLM never creates a persistent record ID, Evidence ID, Commit ID, generation ID, or hash.
- Code supplies `scene_id` from the accepted Scene card.
- A new-record `local_key` is candidate-local and never survives as a Canon identity.
- Candidate references may use an adopted persistent ID or an in-candidate `local_key` only where explicitly permitted.
- Every prose-derived creation or change has at least one Evidence proposal unless this document explicitly permits none.
- Evidence quotes must be literal substrings of the frozen accepted prose.
- A proposed `before` value is never trusted. Code injects or verifies it against HEAD before DELTA-CHK.
- No-op updates are forbidden.
- Candidate arrays use deterministic ordering after code normalization.
- A candidate may contain empty arrays.
- `time_update` is nullable.
- An accepted continuity candidate cannot modify the frozen prose or Scene card.

---

## 3. Common candidate types

### 3.1 Candidate local key

| property | contract |
|---|---|
| type | string |
| required | yes where specified |
| nullable | no |
| creator | LLM |
| validation | pattern `[a-z][a-z0-9_-]{0,63}`; unique within the candidate across all proposal arrays; must not match any persistent-ID pattern |
| source of truth | validated continuity candidate only |

### 3.2 Candidate record reference

A Candidate record reference is a string containing either:

- an adopted persistent ID of the required type; or
- a `local_key` defined by a compatible proposal in the same candidate.

Code resolves every local reference before commit. Unresolved, ambiguous, circular, or type-incompatible references reject the candidate.

### 3.3 JSON update value

`before` and `after` in an existing-item update may be exactly one of:

```text
string
integer
boolean
null
array<string>
```

Objects and mixed-type arrays are forbidden. `array<string>` is used only for fields whose Canon contract defines a set-like string or ID array.

### 3.4 Evidence proposal

An Evidence proposal is embedded in a candidate change. It is not an adopted Evidence record.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `quote` | string | yes | no | none | LLM | candidate-only | NFC nonempty; `1..1000` code points; must occur exactly once in canonical frozen prose |
| `relation` | enum `evidence_relation` | yes | no | `supports` | LLM | candidate-only | `supports` or `contradicts`; non-ending changes require `supports` |

The LLM does not provide offsets or hashes. Code computes those only after exact quote validation.


## 4. Validated continuity-candidate root

The checkpoint file at `runtime/checkpoints/.../continuity-delta.json` contains:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `schema_version` | string | yes | no | none | code | immutable | supported continuity-candidate Schema version |
| `delta_status` | constant `candidate` | yes | no | `candidate` | code | immutable | exact constant |
| `scene_id` | Scene ID | yes | no | none | code | immutable | matches checkpoint path and accepted Scene card |
| `existing_item_updates` | array<Existing item update candidate> | yes | no | `[]` | LLM, normalized by code | candidate-only | unique target and field combination unless operations are explicitly sequential |
| `new_item_proposals` | array<New item proposal union> | yes | no | `[]` | LLM, normalized by code | candidate-only | local keys unique; accepted Scene-card policy permits every type and total count |
| `knowledge_item_proposals` | array<Knowledge item proposal> | yes | no | `[]` | LLM, normalized by code | candidate-only | local keys unique; facts non-duplicate |
| `knowledge_updates` | array<Knowledge update candidate> | yes | no | `[]` | LLM, normalized by code | candidate-only | unique target tuple; valid transition |
| `thread_updates` | array<Thread update candidate> | yes | no | `[]` | LLM, normalized by code | candidate-only | unique thread reference; valid operation matrix |
| `ending_evidence_proposals` | array<Ending evidence proposal> | yes | no | `[]` | LLM, normalized by code | candidate-only | adopted Ending criterion references only |
| `time_update` | Time update candidate | yes | yes | `null` | LLM, normalized by code | candidate-only | null when no stored time value changes |
| `handoff_summary` | string | yes | no | none | LLM | candidate-only | NFC nonempty; describes only facts established by the frozen prose; no future plan or author truth |

Candidate canonical ordering:

1. `existing_item_updates`: `(target_type, target_id, field_path)`;
2. `new_item_proposals`: `local_key`;
3. `knowledge_item_proposals`: `local_key`;
4. `knowledge_updates`: `(fact_ref, audience_type, audience_id)`;
5. `thread_updates`: `thread_ref`;
6. `ending_evidence_proposals`: `(criterion_id, relation, first evidence quote)`.


## 5. Existing item update candidate

This record handles mutable Character state, Relationship state, mutable Canon metadata, and mutable Knowledge-item metadata.

Thread state, Knowledge state, and Story clock use dedicated records.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `operation` | enum `existing_update_operation` | yes | no | none | LLM | candidate-only | `set`, `transition`, `append`, or `remove`; permitted by field matrix |
| `target_type` | enum `existing_update_target_type` | yes | no | none | LLM | candidate-only | `character_state`, `relationship_state`, `canon_record`, or `knowledge_item_record` |
| `target_id` | persistent ID | yes | no | none | LLM | candidate-only | adopted, non-retired target compatible with `target_type` |
| `field_path` | JSON Pointer string | yes | no | none | LLM | candidate-only | exact permitted path from the matrix below |
| `before` | JSON update value | yes | yes | none | code-injected from HEAD | candidate-only | exact canonical HEAD value |
| `after` | JSON update value | yes | yes | none | LLM | candidate-only | valid target-field type; differs from `before` |
| `evidence` | array<Evidence proposal> | yes | no | none | LLM | candidate-only | `1..3` unique evidence proposals |

### 5.1 Existing-item field matrix

| target type | field path | operation | value type | additional rule |
|---|---|---|---|---|
| `character_state` | `/location_id` | `set` | string or null | non-null value is adopted active/inactive Location ID |
| `character_state` | `/physical_condition` | `set` | string or null | empty string forbidden |
| `character_state` | `/emotional_state` | `set` | string or null | empty string forbidden |
| `character_state` | `/current_goal` | `set` | string or null | empty string forbidden |
| `character_state` | `/current_pressure` | `set` | string or null | empty string forbidden |
| `relationship_state` | `/public_relation` | `set` | string | NFC nonempty |
| `relationship_state` | `/a_to_b/trust` | `transition` | enum `trust` | distinct valid enum values |
| `relationship_state` | `/a_to_b/perception` | `set` | string | NFC nonempty |
| `relationship_state` | `/a_to_b/emotional_stance` | `set` | string | NFC nonempty |
| `relationship_state` | `/a_to_b/current_intention` | `set` | string | NFC nonempty |
| `relationship_state` | `/b_to_a/trust` | `transition` | enum `trust` | distinct valid enum values |
| `relationship_state` | `/b_to_a/perception` | `set` | string | NFC nonempty |
| `relationship_state` | `/b_to_a/emotional_stance` | `set` | string | NFC nonempty |
| `relationship_state` | `/b_to_a/current_intention` | `set` | string | NFC nonempty |
| `relationship_state` | `/shared_state` | `set` | string | NFC nonempty |
| `canon_record` | `/scope` | `transition` | enum `scope` | widening only |
| `canon_record` | `/record_lifecycle` | `transition` | enum `record_lifecycle` | lifecycle matrix; retirement may require related State change |
| `canon_record` | `/related_ids` | `append` or `remove` | array<string> | target must be a Temporal rule; `after` is the complete canonical set |
| `knowledge_item_record` | `/scope` | `transition` | enum `scope` | widening only |
| `knowledge_item_record` | `/record_lifecycle` | `transition` | enum `record_lifecycle` | lifecycle matrix |

Any unlisted target/path/operation combination is forbidden.

### 5.2 Multiple updates to one target

A candidate normally contains at most one update per `(target_type, target_id, field_path)`.

Multiple sequential updates to the same field in one scene are forbidden. The candidate must express the final prose-supported transition as one `before → after` update.


## 6. New item proposal union

A scene may propose only types permitted by the accepted Scene card's `new_item_policy` and `configuration.max_new_items_per_scene`.

Every proposal contains the common fields below and exactly one discriminator-specific payload.

### 6.1 Common fields

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Candidate local key | yes | no | none | LLM | candidate-only | globally unique within candidate |
| `proposal_type` | enum `new_item_proposal_type` from `canon_records.md` | yes | no | none | LLM | candidate-only | accepted Scene-card policy permits the value |
| `scope` | enum `scope` | yes | no | none | LLM | candidate-only | cannot exceed Scene-card declared scope permission |
| `evidence` | array<Evidence proposal> | yes | no | none | LLM | candidate-only | `1..3`; all `supports` |

### 6.2 Character proposal

Required when `proposal_type=character`.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `name` | string | yes | no | none | LLM | NFC nonempty |
| `aliases` | array<string> | yes | no | `[]` | LLM | unique canonical set |
| `role` | enum `character_role` | yes | no | `supporting` | LLM | prose-created protagonist forbidden |
| `core_trait` | string | yes | no | none | LLM | NFC nonempty and evidenced |
| `values` | array<string> | yes | no | `[]` | LLM | unique canonical set; every claimed value must be prose-supported |
| `background` | string | yes | no | none | LLM | limited to facts established by prose; no invented hidden history |
| `immutable_facts` | array<string> | yes | no | `[]` | LLM | unique canonical set; prose-supported |
| `appearance_anchor` | string | yes | no | none | LLM | prose-supported |
| `speech_anchor` | string | yes | no | none | LLM | prose-supported; no unsupported long-term style claim |
| `initial_state` | New Character state | yes | no | none | LLM | complete Character-state initialization |

New Character state:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `location_ref` | Location ID or candidate local key | yes | yes | `null` | LLM | null or adopted/new Location reference |
| `physical_condition` | string | yes | yes | `null` | LLM | null or NFC nonempty |
| `emotional_state` | string | yes | yes | `null` | LLM | null or NFC nonempty |
| `current_goal` | string | yes | yes | `null` | LLM | null or NFC nonempty |
| `current_pressure` | string | yes | yes | `null` | LLM | null or NFC nonempty |

### 6.3 Relationship proposal

Required when `proposal_type=relationship`.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `participant_a_ref` | Character ID or candidate local key | yes | no | none | LLM | resolves to Character |
| `participant_b_ref` | Character ID or candidate local key | yes | no | none | LLM | resolves to different Character |
| `relationship_type` | enum `relationship_type` | yes | no | none | LLM | registry value |
| `relationship_origin` | string | yes | no | none | LLM | prose-supported description |
| `structural_role` | enum `structural_role` | yes | no | `supporting` | LLM | prose-created `primary` relationship requires explicit Scene-card permission |
| `initial_state` | New Relationship state | yes | no | none | LLM | complete Relationship-state initialization |

New Relationship state:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `public_relation` | string | yes | no | none | LLM | NFC nonempty |
| `a_to_b` | Directional relationship state | yes | no | none | LLM | complete child object |
| `b_to_a` | Directional relationship state | yes | no | none | LLM | complete child object |
| `shared_state` | string | yes | no | none | LLM | NFC nonempty |

Each directional child contains:

```text
trust
perception
emotional_stance
current_intention
```

with the exact types and validation defined by `story_state.md`.

### 6.4 World-entity proposal

Required when `proposal_type` is one of:

```text
location
organization
item
system
culture
history
```

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `name` | string | yes | no | none | LLM | NFC nonempty |
| `description` | string | yes | no | none | LLM | limited to prose-established facts |
| `immutable_rules` | array<string> | yes | no | `[]` | LLM | unique canonical set; each rule explicitly established by prose |
| `sensory_anchors` | array<string> | yes | no | `[]` | LLM | unique canonical set; prose-supported |

Code derives the persisted World entity `kind` and ID prefix from `proposal_type`.

### 6.5 Supporting-thread proposal

Required when `proposal_type=supporting_thread`.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `description` | string | yes | no | none | LLM | one trackable dramatic question established by prose |
| `resolution_condition` | string | yes | yes | `null` | LLM | null or non-secret observable condition; may not invent author truth |
| `presentation_rule` | string | yes | yes | `null` | LLM | null or prose-supported presentation constraint |
| `initial_status` | enum `thread_status` | yes | no | `open` | LLM | `open` or `in_progress` only |
| `initial_progress` | integer | yes | no | `0` | LLM | `open/0` or `in_progress/1` only |

Persisted fixed values are code-owned:

```text
record_type = thread
record_origin = prose
thread_type = supporting
author_truth = null
required = false
created_scene_id = root scene_id
record_lifecycle = active
```

If initialized as `in_progress/1`, the creation evidence must also establish the first introduction. A separate Thread update for the same new local key is then forbidden.


## 7. Knowledge item proposal

A Knowledge item proposal creates one prose-origin canonical fact. It is separate from `new_item_proposals`.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Candidate local key | yes | no | none | LLM | candidate-only | unique across candidate |
| `subject_type` | enum `knowledge_subject_type` | yes | no | none | LLM | candidate-only | compatible with resolved subject reference |
| `subject_ref` | adopted Canon ID or candidate local key | yes | no | none | LLM | candidate-only | resolves to compatible adopted/new Canon record |
| `canonical_fact` | string | yes | no | none | LLM | candidate-only | NFC nonempty; one independently trackable prose-established fact |
| `writer_visible_label` | string | yes | no | none | LLM | candidate-only | safe projection that does not reveal hidden author truth |
| `scope` | enum `scope` | yes | no | none | LLM | candidate-only | permitted by Scene-card policy |
| `evidence` | array<Evidence proposal> | yes | no | none | LLM | candidate-only | `1..3`; all `supports` |

Code persists:

```text
record_type = knowledge_item
record_origin = prose
author_truth = null
created_scene_id = root scene_id
record_lifecycle = active
```

The proposal is rejected when its normalized `(subject_type, resolved subject_id, canonical_fact)` duplicates an active or inactive Knowledge item.


## 8. Knowledge update candidate

A Knowledge update changes one audience's status for one adopted or same-candidate Knowledge item.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `fact_ref` | Knowledge item ID or candidate local key | yes | no | none | LLM | candidate-only | resolves to an adopted or proposed Knowledge item |
| `audience_type` | enum `knowledge_audience_type` | yes | no | none | LLM | candidate-only | `character` or `reader` |
| `audience_id` | Character ID | yes | yes | none | LLM | candidate-only | non-null adopted Character iff `character`; null iff `reader` |
| `before` | audience-specific status | yes | no | none | code-injected from HEAD or implicit default | candidate-only | exact current status |
| `after` | audience-specific status | yes | no | none | LLM | candidate-only | valid non-no-op transition from `story_state.md` |
| `evidence` | array<Evidence proposal> | yes | no | none | LLM | candidate-only | `1..3`; all `supports` |

A new Knowledge item may be created without a Knowledge update. In that case all audience states remain implicit defaults.

If `fact_ref` is a same-candidate local key, `before` is:

```text
character audience:
  unknown

reader audience:
  withheld
```


## 9. Thread update candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `thread_ref` | Thread ID or candidate local key | yes | no | none | LLM | candidate-only | resolves to adopted Thread or same-candidate Supporting thread |
| `operation` | enum `thread_action` | yes | no | none | LLM | candidate-only | permitted by `story_state.md` operation matrix |
| `before_status` | enum `thread_status` | yes | no | none | code-injected from HEAD or proposal initialization | candidate-only | exact current status |
| `after_status` | enum `thread_status` | yes | no | none | LLM | candidate-only | operation-matrix result |
| `before_progress` | integer | yes | no | none | code-injected from HEAD or proposal initialization | candidate-only | exact current progress |
| `after_progress` | integer | yes | no | none | LLM | candidate-only | operation-matrix result |
| `evidence` | array<Evidence proposal> | yes | no | none | LLM | candidate-only | `1..3`; evidence establishes the operation |

A same-candidate Supporting-thread proposal initialized as `in_progress/1` cannot also appear in `thread_updates`.

A required Major thread cannot use operation `retire`.


## 10. Ending evidence proposal

An Ending evidence proposal does not mutate the Ending criterion. It creates immutable Evidence-index records for Completion audit.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `criterion_id` | Ending criterion ID | yes | no | none | LLM | candidate-only | adopted active/inactive Ending criterion |
| `relation` | enum `evidence_relation` | yes | no | none | LLM | candidate-only | `supports` or `contradicts` |
| `evidence` | array<Evidence proposal> | yes | no | none | LLM | candidate-only | `1..3`; every nested relation equals parent `relation` |

Mentioning an ending concept is insufficient. The quote must materially support or contradict the criterion.


## 11. Time update candidate

`time_update` is null when the stored time label and parallel group do not change.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `time_relation` | enum `time_relation` | yes | no | none | LLM | candidate-only | must satisfy `story_state.md` relation rules |
| `before_time_label` | string | yes | yes | none | code-injected from HEAD | candidate-only | exact HEAD value |
| `after_time_label` | string | yes | yes | none | LLM | candidate-only | relation-compatible; differs from `before_time_label` or parallel group changes |
| `before_parallel_group_id` | string | yes | yes | none | code-injected from HEAD | candidate-only | exact HEAD value |
| `after_parallel_group_id` | string | yes | yes | none | LLM | candidate-only | relation-compatible |
| `elapsed_hint` | string | yes | yes | `null` | LLM | candidate-only | required and nonempty for `after_interval`; otherwise optional |
| `evidence` | array<Evidence proposal> | yes | no | none | LLM | candidate-only | `1..3`; quote establishes the time transition |

Rules:

- `same_time` is forbidden in a non-null Time update unless `parallel_group_id` changes through a separately valid parallel-time case.
- `later`, `next_day`, and `after_interval` require `after_parallel_group_id=null`.
- `parallel` requires non-null `after_parallel_group_id`.
- `current_order` and scene-position fields are never proposed; code updates them during commit.


## 12. Evidence-index contract

### 12.1 Root object

`evidence-index.json` contains:

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `records` | array<Evidence record> | yes | no | `[]` | code | generation replacement only | Evidence IDs unique; sorted by `evidence_id`; records immutable | `evidence-index.json` |

### 12.2 Evidence ID

| property | contract |
|---|---|
| pattern | `ev-[0-9]{6}` |
| allocator | code |
| counter | `next_evidence_id` |
| reuse | forbidden |
| allocation stage | COMMIT-02 after all mechanical validation succeeds |

### 12.3 Evidence enums

| enum | values |
|---|---|
| `evidence_relation` | `supports`, `contradicts` |
| `evidence_type` | `record_creation`, `canon_metadata_update`, `character_state_update`, `relationship_state_update`, `knowledge_item_creation`, `knowledge_state_update`, `thread_state_update`, `ending_criterion_assessment`, `time_update` |
| `evidence_target_type` | `character`, `relationship`, `world_entity`, `temporal_rule`, `thread`, `ending_criterion`, `knowledge_item`, `character_state`, `relationship_state`, `knowledge_state`, `thread_state`, `story_clock` |

### 12.4 Evidence record

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `evidence_id` | Evidence ID | yes | no | none | code | immutable | pattern and uniqueness |
| `evidence_type` | enum `evidence_type` | yes | no | none | code | immutable | compatible with originating candidate record |
| `target_type` | enum `evidence_target_type` | yes | no | none | code | immutable | compatible with target ID and field |
| `target_id` | persistent ID | yes | yes | none | code | immutable | null only when `target_type=story_clock`; otherwise adopted or same-commit persistent ID |
| `target_field` | JSON Pointer string | yes | yes | `null` | code | immutable | non-null for field-level updates; null for record creation and Ending assessment |
| `audience_type` | enum `knowledge_audience_type` | yes | yes | `null` | code | immutable | non-null only for Knowledge-state evidence |
| `audience_id` | Character ID | yes | yes | `null` | code | immutable | conditional on Knowledge audience |
| `scene_id` | Scene ID | yes | no | none | code | immutable | scene whose adopted prose contains the quote |
| `commit_id` | Commit ID | yes | no | none | code | immutable | adopting scene commit |
| `quote` | string | yes | no | none | code from validated proposal | immutable | exact substring of canonical prose |
| `relation` | enum `evidence_relation` | yes | no | `supports` | code from proposal | immutable | `contradicts` permitted only for Ending assessment |
| `start_offset` | integer | yes | no | none | code | immutable | zero-based Unicode code-point offset |
| `end_offset` | integer | yes | no | none | code | immutable | exclusive; greater than `start_offset` |
| `quote_sha256` | lowercase hexadecimal string | yes | no | none | code | immutable | SHA-256 of exact NFC quote UTF-8 bytes |
| `prose_sha256` | lowercase hexadecimal string | yes | no | none | code | immutable | matches adopted prose artifact hash |
| `created_at` | RFC 3339 timestamp | yes | no | none | code | immutable | UTC with `Z` |

Conditional rules:

- `target_type=knowledge_state` requires non-null `audience_type`; `audience_id` follows audience rules.
- Other target types require `audience_type=null` and `audience_id=null`.
- `target_type=story_clock` requires `target_id=null` and a non-null time-field `target_field`.
- Record creation uses `target_field=null`.
- `ending_criterion_assessment` uses `target_type=ending_criterion`, `target_field=null`, and permits either relation.
- All other evidence records require `relation=supports`.


## 13. Canonical prose, offsets, and hashes

Before evidence matching, code canonicalizes the frozen prose:

1. decode as UTF-8;
2. normalize Unicode to NFC;
3. replace CRLF and CR with LF;
4. remove trailing horizontal whitespace from each line;
5. ensure exactly one final LF for artifact hashing.

Evidence offsets are measured in Unicode code points over this canonical prose string, including the final LF.

For every Evidence record:

```text
quote == canonical_prose[start_offset:end_offset]
```

The Evidence proposal quote must occur exactly once. If it occurs zero times or more than once, DELTA validation fails and the candidate must be revised with a longer or corrected quote.

`quote_sha256` is calculated from the exact quote's UTF-8 bytes without adding a trailing LF.

`prose_sha256` is calculated from the complete canonical prose bytes, including the single final LF.

Byte offsets are not stored.


## 14. Committed continuity-delta root

The adopted artifact at `artifacts/scenes/.../continuity-delta.json` is generated by code. It contains no Evidence proposals and no unresolved local references.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `schema_version` | string | yes | no | none | code | supported committed-delta Schema |
| `delta_status` | constant `committed` | yes | no | `committed` | code | exact constant |
| `scene_id` | Scene ID | yes | no | none | code | matches artifact path |
| `existing_item_updates` | array<Committed existing update> | yes | no | `[]` | code | targets and before/after equal committed merge |
| `new_item_adoptions` | array<New item adoption> | yes | no | `[]` | code | every local key resolved to one persistent ID |
| `knowledge_item_adoptions` | array<Knowledge item adoption> | yes | no | `[]` | code | every local key resolved |
| `knowledge_updates` | array<Committed Knowledge update> | yes | no | `[]` | code | equals resulting Story-state transition |
| `thread_updates` | array<Committed Thread update> | yes | no | `[]` | code | equals resulting Story-state transition |
| `ending_evidence` | array<Committed Ending evidence> | yes | no | `[]` | code | all Evidence IDs exist |
| `time_update` | Committed Time update | yes | yes | `null` | code | equals resulting Story clock |
| `handoff_summary` | string | yes | no | none | code from accepted candidate | same accepted prose-grounded summary |

### 14.1 Committed existing update

```text
operation
target_type
target_id
field_path
before
after
evidence_ids
```

`evidence_ids` is a nonempty array of adopted Evidence IDs.

### 14.2 New item adoption

```text
local_key
proposal_type
persistent_id
canon_record_sha256
initial_state_sha256
evidence_ids
```

Rules:

- `initial_state_sha256` is non-null only for Character, Relationship, and Supporting-thread adoptions.
- `canon_record_sha256` hashes the canonical adopted individual record object.
- `evidence_ids` is nonempty.

### 14.3 Knowledge item adoption

```text
local_key
fact_id
knowledge_item_sha256
evidence_ids
```

### 14.4 Committed Knowledge update

```text
fact_id
audience_type
audience_id
before
after
evidence_ids
```

### 14.5 Committed Thread update

```text
thread_id
operation
before_status
after_status
before_progress
after_progress
evidence_ids
```

### 14.6 Committed Ending evidence

```text
criterion_id
relation
evidence_ids
```

### 14.7 Committed Time update

```text
time_relation
before_time_label
after_time_label
before_parallel_group_id
after_parallel_group_id
elapsed_hint
evidence_ids
```

Every committed array is canonically sorted by the corresponding resolved persistent target.


## 15. Candidate-to-commit transformation

### COMMIT-01: mechanical validation

Code validates:

```text
candidate Schema and unknown-field rejection
root scene_id and checkpoint path
Scene-card allowed_update_targets
Scene-card new_item_policy types and count
local-key uniqueness and reference resolution graph
existing target existence and lifecycle
field/operation matrix
HEAD before values
non-no-op after values
Character/Relationship/Thread/Knowledge transition matrices
new-record fixed-field completeness
new-record initial-State completeness
Knowledge-item duplicate rule
Evidence quote unique occurrence
Ending-evidence relation
Time-update relation
handoff summary contains no future plan or author truth
```

COMMIT-01 performs no persistent-ID allocation and no adopted-file mutation.

### COMMIT-02: allocation and merge preparation

After COMMIT-01 succeeds, code:

1. allocates persistent IDs for new Canon and Knowledge records;
2. resolves every candidate local reference;
3. allocates Evidence IDs;
4. computes Evidence offsets and hashes;
5. constructs new Canon, Knowledge, Story-state, and Evidence-index values in staging;
6. records the local-key mapping in the Commit manifest;
7. computes individual and root artifact hashes.

ID gaps are allowed if a later staging step fails. Allocated IDs are never reused.

### COMMIT-03: scene-artifact construction

Code writes staged:

```text
scene-card.json
prose.md
committed continuity-delta.json
scene-manifest.json
```

The committed delta contains only persistent IDs and Evidence IDs.

### COMMIT-04: atomic adoption

Code atomically adopts the staged generation and scene artifact, then updates HEAD according to the runtime contract.

No Evidence record or continuity update is visible through HEAD before COMMIT-04 completes.


## 16. Merge and consistency invariants

A commit is rejected when any of the following is true:

```text
unknown or retired update target
target not permitted by Scene card
new proposal type not permitted by new_item_policy
new proposal count exceeds Scene card or configuration limit
duplicate local key
unresolved or type-incompatible local reference
immutable field update
invalid operation for field
candidate before differs from HEAD
before equals after
invalid State transition
required evidence missing
evidence quote absent or non-unique
evidence relation incompatible with update
new record lacks complete initial State
new Knowledge item duplicates existing active/inactive fact
new Supporting thread violates prose-origin constraints
Ending evidence targets unknown criterion
time update conflicts with Story-clock rules
delta change absent from staged after-State
staged after-State change absent from committed delta
Evidence ID missing from staged Evidence index
committed delta hash differs from scene manifest
```

A rejected commit leaves adopted Canon, Knowledge items, Story state, Evidence index, scene artifacts, and HEAD unchanged.


## 17. Forbidden candidate content

The following are forbidden in raw or validated continuity candidates:

```text
new persistent IDs
Evidence IDs
Commit IDs
generation IDs
hash values
offset values
author_truth for prose-created records
new Major thread
new Ending criterion
new Temporal rule
future scene or future volume detail
unobserved private knowledge
immutable-field rewrite
full before/after Canon snapshots
publication metadata
runtime retry counters
```

The following are forbidden in the committed delta:

```text
unresolved local references
Evidence proposal objects
secret prompt context
review comments
raw LLM response
candidate retry metadata
```


## 18. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
raw response cannot inject code-owned fields
candidate local-key uniqueness
persistent-ID and local-key reference resolution
new_item_policy type/count enforcement
existing-field matrix enforcement
immutable-field rejection
HEAD before-value equality
no-op rejection
Character-state update merge
directional Relationship-state update merge
scope widening and lifecycle transition validation
Temporal-rule related_ids append/remove validation
new Character adoption with complete State
new Relationship adoption with complete State
new World-entity adoption
new Supporting-thread adoption
new Knowledge-item adoption
same-candidate fact and thread references
Knowledge-state implicit-default handling
Knowledge-state transition matrix
Thread operation matrix
Ending evidence supports/contradicts handling
time-update relation validation
unique prose quote requirement
Unicode code-point offset calculation
quote and prose SHA-256 calculation
Evidence-ID allocation and non-reuse
Evidence-index canonical ordering
candidate-to-committed-delta normalization
local-key mapping completeness
delta-to-after-State correspondence
committed delta contains no local references
checkpoint uses candidate schema
adopted artifact uses committed schema
atomic rollback on any commit failure
unknown-field rejection
canonical serialization stability
```
