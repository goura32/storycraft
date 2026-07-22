# Data contracts: Planning artifacts

This document is the normative contract for:

- the Series map generated after Genesis;
- one Volume design for each planned volume;
- one Chapter design for each planned chapter;
- their candidate, review, revision, adoption, hashing, and cross-plan consistency rules.

The adopted Brief and Initial design are defined by [`brief_and_initial.md`](brief_and_initial.md). Stable Canon records and IDs are defined by [`../ledger/canon_records.md`](../ledger/canon_records.md). Mutable current values are defined by [`../ledger/story_state.md`](../ledger/story_state.md). Runtime candidate and manifest behavior is defined by [`../ledger/runtime_records.md`](../ledger/runtime_records.md). Effective profile and length settings are defined by [`../../configuration_contracts.md`](../../configuration_contracts.md).

Every saved object and structured LLM response defined here uses `additionalProperties: false`.

---

## 1. Planning authority and scope

Planning artifacts describe intended dramatic structure. They are not current Canon or current Story state.

| artifact | authority |
|---|---|
| `plans/series-map.json` | intended series-wide progression by volume |
| `plans/volumes/vNN/volume-design.json` | intended progression inside one volume |
| `plans/volumes/vNN/chapters/cNNN/chapter-design.json` | intended progression inside one chapter |
| current Canon generation | adopted fixed records and current lifecycle |
| current Story state | actual mutable values reached by adopted prose |
| Volume handoff | actual end-of-volume state and carry-over constraints |

When actual adopted prose diverges from a plan:

- Canon and Story state remain authoritative;
- the plan is not silently rewritten;
- later Volume or Chapter planning uses the current adopted generation and latest Volume handoff;
- residual differences are visible to review and Completion audit.

Planning artifacts must not contain raw prompts, raw model responses, runtime counters, provider settings, Evidence offsets, or publication file paths.

---

## 2. Candidate and adopted artifacts

### 2.1 Candidate paths

```text
runtime/candidates/planning/series-map/
  series-map.json
  review.json
  candidate-manifest.json

runtime/candidates/planning/volumes/v01/
  volume-design.json
  review.json
  candidate-manifest.json

runtime/candidates/planning/volumes/v01/chapters/c001/
  chapter-design.json
  review.json
  candidate-manifest.json
```

Only `candidate-manifest.json` is a resume authority.

### 2.2 Adopted paths

```text
plans/series-map.json
plans/volumes/v01/volume-design.json
plans/volumes/v01/chapters/c001/chapter-design.json
```

Adopted planning artifacts are immutable. Regeneration creates a new run or an explicitly versioned migration outside the normal pipeline.

### 2.3 Candidate and adopted root distinction

LLM candidate roots contain only planning content.

Code adds these fields during adoption:

```text
schema_version
source_generation_id
source_generation_manifest_sha256
brief_sha256
initial_design_sha256
parent_plan_sha256 when applicable
accepted_candidate_sha256
created_at
```

The LLM never generates those fields.

---

## 3. Shared planning scalar contracts

### 3.1 Volume number

| property | contract |
|---|---|
| type | integer |
| minimum | `1` |
| maximum | adopted Brief `volumes` |
| sequence | Series-map volume entries are contiguous from `1` through Brief `volumes` |
| path form | `vNN`, zero-padded to two digits |

### 3.2 Chapter number

| property | contract |
|---|---|
| type | integer |
| minimum | `1` |
| sequence | Chapter designs for one Volume are contiguous from `1` through `target_chapter_count` |
| path form | `cNNN`, zero-padded to three digits |

### 3.3 Planned state summary

A planned state summary is a string that:

- is NFC nonempty;
- is `1..1500` code points;
- describes the intended observable or writer-relevant state;
- does not replace the actual Story-state object;
- does not contain an unresolved local key;
- may reference adopted persistent IDs through surrounding fields.

### 3.4 Planned thread status/progress

Planned Thread values use the exact `thread_status`, `thread_action`, and status/progress matrices from `story_state.md`.

A plan may forecast a future status, but it may not use an impossible pair.

### 3.5 Ordering

Candidate arrays are normalized before hashing:

- volume entries by `volume_number`;
- relationship targets by `relationship_id`;
- Thread targets/actions by `thread_id`;
- Ending-criterion targets by `criterion_id`;
- chapter entries by `chapter_number`;
- ID sets lexicographically by persistent ID.

Priority-ordered narrative arrays retain LLM order only where this document says so.

---

## 4. Shared planning enums

### 4.1 Volume structural role

```text
opening
development
midpoint
escalation
pre_final
final
```

Rules:

- Volume `1` uses `opening`.
- The last Volume uses `final`.
- `midpoint` is optional and may appear at most once.
- `pre_final` may appear at most once and only immediately before the final Volume.
- Other nonfinal Volumes use `development` or `escalation`.

### 4.2 Chapter end function

```text
hook
escalation
reversal
revelation
decision
climax
resolution
bridge
```

### 4.3 Ending-criterion plan action

```text
withhold
prepare
support
satisfy
contradict_risk
```

`contradict_risk` identifies a risk to avoid. It is not adopted contradiction evidence.

### 4.4 Planned change target type

```text
character
relationship
```

---

## 5. Shared relationship-change target

This object is used by Series and Volume planning.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `relationship_id` | Relationship ID | yes | no | none | LLM | candidate-only | adopted active or inactive Relationship |
| `start_state_summary` | planned state summary | yes | no | none | LLM | candidate-only | compatible with relevant starting Story state or prior plan target |
| `target_state_summary` | planned state summary | yes | no | none | LLM | candidate-only | meaningfully differs from start |
| `required_change` | string | yes | no | none | LLM | candidate-only | `1..1000`; observable change needed by the plan boundary |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1000`; dramatic function |

A Relationship target does not repeat participant IDs or fixed Relationship fields.

---

## 6. Shared Thread plan target

This object is used in the Series map.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `thread_id` | Thread ID | yes | no | none | LLM | candidate-only | adopted Major Thread; Supporting Threads are not available during initial Series planning |
| `start_status` | enum `thread_status` | yes | no | none | LLM | candidate-only | valid with `start_progress` |
| `start_progress` | integer | yes | no | none | LLM | candidate-only | `0..4`; valid status pair |
| `required_action` | enum `thread_action` | yes | no | none | LLM | candidate-only | valid transition from start to target |
| `target_status` | enum `thread_status` | yes | no | none | LLM | candidate-only | valid with `target_progress` |
| `target_progress` | integer | yes | no | none | LLM | candidate-only | `0..4`; exact result of required action |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1000`; dramatic function in the plan boundary |

For a single Volume boundary:

- `introduce` means `open/0 → in_progress/1`;
- `advance` increases progress by exactly one;
- `resolve` means `in_progress/1..3 → resolved/4`;
- `retire` is forbidden for a required Major Thread.

A Volume may omit a Major Thread from its target array only when no planned state change occurs in that Volume.

---

## 7. Shared Volume Thread action

This object is used by Volume and Chapter designs.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `thread_id` | Thread ID | yes | no | none | LLM | candidate-only | adopted Thread visible to the planner |
| `start_status` | enum `thread_status` | yes | no | none | LLM | candidate-only | valid pair |
| `start_progress` | integer | yes | no | none | LLM | candidate-only | valid pair |
| `required_action` | enum `thread_action` | yes | no | none | LLM | candidate-only | operation-matrix compatible |
| `target_status` | enum `thread_status` | yes | no | none | LLM | candidate-only | exact action result |
| `target_progress` | integer | yes | no | none | LLM | candidate-only | exact action result |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `required` | boolean | yes | no | `true` | LLM | candidate-only | true means later plan/review must preserve this action |

A Chapter action cannot represent multiple sequential Thread operations. Use at most one action per Thread per Chapter.

---

## 8. Shared Ending-criterion target

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `criterion_id` | Ending criterion ID | yes | no | none | LLM | candidate-only | adopted active or inactive Ending criterion |
| `plan_action` | enum `ending_criterion_plan_action` | yes | no | none | LLM | candidate-only | Section 4.3 value |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `required` | boolean | yes | no | none | LLM | candidate-only | must equal adopted Ending criterion `required` |
| `prohibited_disclosure` | string | yes | yes | `null` | LLM | candidate-only | null or `1..1000`; writer-safe instruction without author-truth quotation |

Final-Volume rules:

- every required Ending criterion appears;
- every required criterion uses `satisfy`;
- optional criteria may use `satisfy`, `support`, or `withhold`;
- `contradict_risk` may accompany another target only through a separate review issue, not a duplicate target.

---

# Part I: Series map

## 9. Series-map candidate root

SERIES-01 returns exactly:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `series_question` | string | yes | no | none | LLM | candidate-only | `1..1500`; central reader-facing question |
| `protagonist_start_state` | planned state summary | yes | no | none | LLM | candidate-only | compatible with Genesis protagonist State |
| `protagonist_end_state` | planned state summary | yes | no | none | LLM | candidate-only | compatible with Initial-design protagonist arc and Brief ending |
| `volumes` | array<Series Volume target> | yes | no | none | LLM | candidate-only | length equals Brief `volumes`; contiguous numbers |
| `final_required_criterion_ids` | array<Ending criterion ID> | yes | no | none | LLM | candidate-only | exactly all adopted required Ending criteria; sorted |

The candidate contains no top-level title, genre, profile ID, hash, timestamp, or persistent-ID allocation.

## 10. Series Volume target

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `volume_number` | Volume number | yes | no | none | LLM | candidate-only | contiguous |
| `structural_role` | enum `volume_structural_role` | yes | no | none | LLM | candidate-only | Section 4.1 rules |
| `volume_function` | string | yes | no | none | LLM | candidate-only | `1..1500`; unique dramatic function |
| `protagonist_change_target` | Protagonist change target | yes | no | none | LLM | candidate-only | continuous with adjacent Volumes |
| `relationship_change_targets` | array<Relationship-change target> | yes | no | `[]` | LLM | candidate-only | unique Relationship IDs |
| `major_thread_targets` | array<Shared Thread plan target> | yes | no | `[]` | LLM | candidate-only | unique Thread IDs |
| `ending_criterion_targets` | array<Ending-criterion target> | yes | no | `[]` | LLM | candidate-only | unique criterion IDs |
| `local_resolution` | string | yes | no | none | LLM | candidate-only | `1..1500`; concrete Volume-level closure |
| `reader_question` | string | yes | yes | none | LLM | candidate-only | required non-null for nonfinal Volume when Publishing profile requires it; final Volume may be null |
| `ending_function` | string | yes | no | none | LLM | candidate-only | `1..1500`; describes the boundary effect and transition |
| `estimated_chapter_count` | integer | yes | no | none | LLM | candidate-only | `1..100`; soft initial estimate |

### 10.1 Protagonist change target

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `character_id` | Character ID | yes | no | none | LLM | candidate-only | sole adopted protagonist |
| `start_state_summary` | planned state summary | yes | no | none | LLM | candidate-only | Volume 1 matches Genesis; later Volumes match previous target |
| `target_state_summary` | planned state summary | yes | no | none | LLM | candidate-only | meaningfully differs from start |
| `required_change` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1000` |

### 10.2 Series continuity rules

For adjacent Volume targets `N` and `N+1`:

```text
protagonist target of N
  must be compatible with
protagonist start of N+1
```

For the same planned Relationship:

```text
target_state_summary in N
  must be compatible with
start_state_summary in N+1
```

For the same Major Thread:

```text
target status/progress in N
  must equal
start status/progress in the next Volume entry that changes that Thread
```

A Thread not mentioned in an intervening Volume retains the prior planned status/progress.

Final Volume rules:

```text
structural_role = final
reader_question may be null
all required Major Threads end resolved/4
all required Ending criteria use satisfy
local_resolution describes series-level closure
protagonist target matches protagonist_end_state
```

Nonfinal Volume rules:

```text
no required Major Thread may be retired
reader_question is non-null when profile requires it
local_resolution provides Volume-level payoff
ending_function preserves a reason to continue
```

---

## 11. Adopted `plans/series-map.json`

The adopted root contains:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | immutable | exact constant |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | Genesis generation |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | Genesis Generation manifest |
| `brief_sha256` | SHA-256 | yes | no | none | code | immutable | adopted Brief |
| `initial_design_sha256` | SHA-256 | yes | no | none | code | immutable | adopted `canon/initial-design.json` |
| `accepted_candidate_sha256` | SHA-256 | yes | no | none | code | immutable | accepted Series-map candidate bytes |
| `series_question` | string | yes | no | none | code from candidate | immutable | candidate contract |
| `protagonist_start_state` | planned state summary | yes | no | none | code from candidate | immutable | candidate contract |
| `protagonist_end_state` | planned state summary | yes | no | none | code from candidate | immutable | candidate contract |
| `volumes` | array<Series Volume target> | yes | no | none | code from candidate | immutable | candidate contract |
| `final_required_criterion_ids` | array<Ending criterion ID> | yes | no | none | code from candidate | immutable | candidate contract |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | adoption timestamp |

SERIES-02 reviews the complete candidate. SERIES-REV returns a complete replacement Series-map candidate; partial patches are forbidden.

---

# Part II: Volume design

## 12. Volume-design candidate root

VOL-01 returns exactly:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `volume_number` | Volume number | yes | no | none | LLM | candidate-only | target Volume |
| `title` | string | yes | no | none | LLM | candidate-only | `1..100` code points |
| `volume_promise` | string | yes | no | none | LLM | candidate-only | `1..1500`; reader-facing promise |
| `starting_state_summary` | string | yes | no | none | LLM | candidate-only | `1..3000`; derived from actual current generation/handoff |
| `protagonist_change` | Volume protagonist change | yes | no | none | LLM | candidate-only | conforms to Series-map target |
| `relationship_changes` | array<Volume relationship change> | yes | no | `[]` | LLM | candidate-only | unique Relationship IDs |
| `thread_actions` | array<Volume Thread action> | yes | no | `[]` | LLM | candidate-only | unique Thread IDs |
| `ending_criterion_targets` | array<Ending-criterion target> | yes | no | `[]` | LLM | candidate-only | conforms to Series map |
| `major_conflict` | Major conflict design | yes | no | none | LLM | candidate-only | complete child object |
| `reader_question` | string | yes | yes | none | LLM | candidate-only | matches Series-map requirement |
| `ending_function` | Volume ending function | yes | no | none | LLM | candidate-only | complete child object |
| `target_chapter_count` | integer | yes | no | none | LLM | candidate-only | `1..100`; generally compatible with Series estimate |
| `chapter_functions` | array<Chapter function target> | yes | no | none | LLM | candidate-only | length equals target count; contiguous chapter numbers |

### 12.1 Volume protagonist change

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `character_id` | Character ID | yes | no | none | LLM | candidate-only | protagonist |
| `start_state_summary` | planned state summary | yes | no | none | LLM | candidate-only | compatible with actual Volume start |
| `target_state_summary` | planned state summary | yes | no | none | LLM | candidate-only | Series-map-compatible |
| `required_turns` | array<Required turn> | yes | no | none | LLM | candidate-only | `1..12`; ordered and unique sequence |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1000` |

### 12.2 Required turn

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `sequence` | integer | yes | no | none | LLM | candidate-only | contiguous from `1` |
| `description` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..500` |

### 12.3 Volume relationship change

This contains the Shared relationship-change target plus:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `required_turns` | array<Required turn> | yes | no | none | LLM | candidate-only | `1..12`; ordered |

All Shared relationship fields remain required.

### 12.4 Major conflict design

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `conflict_statement` | string | yes | no | none | LLM | candidate-only | `1..1500` |
| `opposing_force_ids` | array<Character or Organization ID> | yes | no | `[]` | LLM | candidate-only | unique; every ID resolves |
| `stakes` | string | yes | no | none | LLM | candidate-only | `1..1500` |
| `escalation_rule` | string | yes | no | none | LLM | candidate-only | `1..1000`; describes how pressure must increase |
| `resolution_condition` | string | yes | no | none | LLM | candidate-only | `1..1500`; Volume-local observable condition |

The opposing-force array may be empty when the opposition is environmental, systemic, or internal.

### 12.5 Volume ending function

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_resolution` | string | yes | no | none | LLM | candidate-only | `1..1500`; concrete Volume payoff |
| `series_transition` | string | yes | yes | none | LLM | candidate-only | required non-null for nonfinal Volume; final Volume requires null |
| `final_image_or_decision` | string | yes | no | none | LLM | candidate-only | `1..1000`; planned dramatic boundary, not prose |
| `prohibited_outcomes` | array<string> | yes | no | `[]` | LLM | candidate-only | unique `0..20`; conflicts to avoid |

### 12.6 Chapter function target

This is a compact Volume-level outline, not the full Chapter design.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `chapter_number` | Chapter number | yes | no | none | LLM | candidate-only | contiguous |
| `function` | string | yes | no | none | LLM | candidate-only | `1..1000`; unique dramatic purpose |
| `primary_change_target_type` | enum `planned_change_target_type` | yes | no | none | LLM | candidate-only | `character` or `relationship` |
| `primary_change_target_id` | Character or Relationship ID | yes | no | none | LLM | candidate-only | compatible with type |
| `required_thread_ids` | array<Thread ID> | yes | no | `[]` | LLM | candidate-only | unique; subset of Volume action targets or deliberately unchanged visible Threads |
| `chapter_end_function` | enum `chapter_end_function` | yes | no | none | LLM | candidate-only | Section 4.2 |
| `target_scene_count` | integer | yes | no | `3` | LLM | candidate-only | `1..20`; soft planning value |

### 12.7 Volume-design consistency

VOL-01 receives:

```text
adopted Series map
target Series Volume entry
adopted current generation
latest preceding Volume handoff when volume_number > 1
Effective profiles and planning targets
```

It must satisfy:

- `volume_number` equals the requested target;
- Series-map protagonist, Relationship, Thread, criterion, reader-question, and ending targets are preserved;
- starting summaries use actual current state/handoff, not only the old Series forecast;
- `target_chapter_count` equals `chapter_functions` length;
- Chapter functions collectively cover every required turn and required Thread action;
- nonfinal/final ending rules match the Publishing profile.

---

## 13. Adopted Volume design

Path:

```text
plans/volumes/v01/volume-design.json
```

The adopted root contains:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | immutable | exact |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | generation used for Volume planning |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | matches source |
| `series_map_sha256` | SHA-256 | yes | no | none | code | immutable | adopted Series map |
| `preceding_volume_handoff_path` | workspace-relative path | yes | yes | `null` | code | immutable | null for Volume 1; otherwise adopted prior handoff |
| `preceding_volume_handoff_sha256` | SHA-256 | yes | yes | `null` | code | immutable | null iff path null |
| `accepted_candidate_sha256` | SHA-256 | yes | no | none | code | immutable | accepted Volume candidate |
| all Volume-design candidate fields | exact candidate types | yes | as defined | as defined | code from candidate | immutable | candidate contract |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | adoption timestamp |

VOL-02 reviews the whole candidate. VOL-REV returns one complete replacement Volume-design candidate.

---

# Part III: Chapter design

## 14. Chapter-design candidate root

CH-01 returns exactly:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `volume_number` | Volume number | yes | no | none | LLM | candidate-only | requested Volume |
| `chapter_number` | Chapter number | yes | no | none | LLM | candidate-only | requested Chapter |
| `title` | string | yes | no | none | LLM | candidate-only | `1..100` |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1500`; conforms to Chapter function target |
| `start_state` | Chapter state summary | yes | no | none | LLM | candidate-only | actual/planned Chapter start |
| `end_goal` | Chapter end goal | yes | no | none | LLM | candidate-only | complete child object |
| `protagonist_or_relationship_change` | Primary Chapter change | yes | no | none | LLM | candidate-only | one discriminated object |
| `thread_actions` | array<Volume Thread action> | yes | no | `[]` | LLM | candidate-only | unique Thread IDs |
| `ending_criterion_targets` | array<Ending-criterion target> | yes | no | `[]` | LLM | candidate-only | unique criterion IDs |
| `required_world_entity_ids` | array<World entity ID> | yes | no | `[]` | LLM | candidate-only | unique; adopted and non-retired |
| `chapter_end_function` | enum `chapter_end_function` | yes | no | none | LLM | candidate-only | matches Volume Chapter function target |
| `scene_plan` | array<Scene function target> | yes | no | none | LLM | candidate-only | contiguous scene numbers; `1..20` |
| `target_scene_count` | integer | yes | no | none | LLM | candidate-only | equals scene-plan length |

### 14.1 Chapter state summary

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `summary` | string | yes | no | none | LLM | candidate-only | `1..3000` |
| `active_character_ids` | array<Character ID> | yes | no | none | LLM | candidate-only | `1..30`; unique; adopted and non-retired |
| `active_relationship_ids` | array<Relationship ID> | yes | no | `[]` | LLM | candidate-only | unique; endpoints compatible with active cast |
| `active_thread_ids` | array<Thread ID> | yes | no | `[]` | LLM | candidate-only | unique; adopted and not retired |
| `time_label` | string | yes | yes | `null` | LLM | candidate-only | compatible with actual Story clock and planned chronology |
| `location_ids` | array<Location ID> | yes | no | `[]` | LLM | candidate-only | unique and non-retired |

### 14.2 Chapter end goal

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `state_summary` | string | yes | no | none | LLM | candidate-only | `1..2000` |
| `required_decision_or_event` | string | yes | no | none | LLM | candidate-only | `1..1500`; observable |
| `reader_effect` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `handoff_to_next_chapter` | string | yes | yes | none | LLM | candidate-only | required non-null except last Chapter of final Volume; `1..1000` |

### 14.3 Primary Chapter change

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `target_type` | enum `planned_change_target_type` | yes | no | none | LLM | candidate-only | `character` or `relationship` |
| `target_id` | Character or Relationship ID | yes | no | none | LLM | candidate-only | compatible with target type |
| `start_state_summary` | planned state summary | yes | no | none | LLM | candidate-only | Chapter-start compatible |
| `target_state_summary` | planned state summary | yes | no | none | LLM | candidate-only | meaningfully differs |
| `required_change` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1000` |

If `target_type=character`, the target is normally the protagonist. A supporting Character may be primary only when the Volume Chapter-function target explicitly names it.

### 14.4 Scene function target

This object guides later Scene-card generation. It is not a Scene card.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `scene_number` | integer | yes | no | none | LLM | candidate-only | contiguous from `1` |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `pov_character_id` | Character ID | yes | no | none | LLM | candidate-only | active, non-retired Character |
| `required_character_ids` | array<Character ID> | yes | no | none | LLM | candidate-only | includes POV; unique |
| `required_location_id` | Location ID | yes | yes | `null` | LLM | candidate-only | null or adopted non-retired Location |
| `required_beats` | array<string> | yes | no | none | LLM | candidate-only | `1..12`; ordered; each `1..500` |
| `thread_action_ids` | array<Thread ID> | yes | no | `[]` | LLM | candidate-only | each has a Chapter Thread action or an explicit unchanged purpose |
| `ending_criterion_ids` | array<Ending criterion ID> | yes | no | `[]` | LLM | candidate-only | subset of Chapter targets |
| `emotional_change_target` | string | yes | no | none | LLM | candidate-only | `1..500` |
| `completion_role` | enum `chapter_completion_role` | yes | no | none | LLM | candidate-only | sequence rules below |

Scene completion-role rules:

- first Scene is `opening`;
- last Scene is `resolution`;
- intermediate Scenes use `development`, `turn`, or `climax`;
- at most one `climax`;
- `climax`, when present, precedes the final `resolution`.

### 14.5 Chapter-design consistency

CH-01 receives:

```text
adopted Volume design
target Chapter-function entry
current adopted generation
prior adopted Chapter handoff or prior Scene handoff when available
Effective editorial and length settings
```

It must satisfy:

- requested Volume and Chapter numbers;
- exact Volume Chapter-function purpose and end function;
- actual current State compatibility;
- every required Volume turn/action assigned to one or more Chapters;
- every required Chapter change/action assigned to one or more Scene-function targets;
- no scene-level persistent creation requirement;
- `target_scene_count` equals Scene-plan length;
- final Chapter satisfies Volume ending function;
- nonfinal Chapter has non-null handoff.

---

## 15. Adopted Chapter design

Path:

```text
plans/volumes/v01/chapters/c001/chapter-design.json
```

The adopted root contains:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|---|
| `schema_version` | constant `1.0` | yes | no | `1.0` | code | immutable | exact |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | generation used for Chapter planning |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | matches source |
| `volume_design_sha256` | SHA-256 | yes | no | none | code | immutable | adopted parent Volume design |
| `prior_chapter_handoff_path` | workspace-relative path | yes | yes | `null` | code | immutable | null for first Chapter; otherwise adopted preceding Chapter handoff when defined |
| `prior_chapter_handoff_sha256` | SHA-256 | yes | yes | `null` | code | immutable | null iff path null |
| `accepted_candidate_sha256` | SHA-256 | yes | no | none | code | immutable | accepted Chapter candidate |
| all Chapter-design candidate fields | exact candidate types | yes | as defined | as defined | code from candidate | immutable | candidate contract |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | adoption timestamp |

CH-02 reviews the entire candidate. CH-REV returns one complete replacement Chapter-design candidate.

---

## 16. Review focus by planning level

The generic Review-result Schema is defined in `review_and_audit.md`.

### 16.1 Series review

At minimum, SERIES-02 assesses:

```text
Brief and Initial-design consistency
contiguous Volume numbering
protagonist progression continuity
Relationship progression continuity
Major-thread operation continuity
required Major-thread final resolution
Ending-criterion coverage
Volume-local resolutions
nonfinal reader questions
final ending compatibility
```

### 16.2 Volume review

At minimum, VOL-02 assesses:

```text
Series-map target preservation
actual starting State compatibility
Chapter-function coverage
required turn allocation
Thread-action validity
Volume-local resolution
nonfinal/final ending behavior
target chapter-count consistency
```

### 16.3 Chapter review

At minimum, CH-02 assesses:

```text
Volume Chapter-function preservation
actual starting State compatibility
primary change clarity
Thread-action validity
Scene-plan coverage
POV and cast feasibility
completion-role sequence
Chapter-end function
handoff requirement
```

A review issue never directly edits a plan.

---

## 17. Adoption rules

SERIES-ID, VOL-ID, and CH-ID are code-only adoption stages.

Adoption requires:

```text
one structurally valid candidate
valid Review result
issues empty
OR revision_rounds_used >= max_revision_rounds
```

When issues remain after revision exhaustion:

- the structurally valid plan is still adopted;
- a residual-issue record is appended;
- the adopted plan does not include the issue text;
- later planners receive the sanitized relevant residual constraints through the appropriate context contract.

Code calculates candidate and adopted artifact hashes. The LLM does not provide them.

---

## 18. Cross-artifact invariants

A valid planning set satisfies:

```text
Series-map Volume count equals adopted Brief volumes
Series-map volume numbers are contiguous
Volume design number exists in Series map
Volume design targets conform to its Series entry
Volume target_chapter_count equals Chapter-function count
Chapter design number exists in parent Volume design
Chapter purpose/end function match the Chapter-function target
Chapter target_scene_count equals Scene-plan length
all persistent IDs resolve in the source generation
no retired record is newly planned as active
Major-thread status/progress chains are valid
required Major Threads end resolved/4 in final Volume
required Ending criteria are satisfied in final Volume plan
nonfinal reader questions satisfy Publishing profile
final Volume has no series-transition text
all adopted artifact paths and parent hashes are valid
```

---

## 19. Forbidden fields and deprecated names

Forbidden in planning candidates:

```text
local_key
new persistent ID
record_origin
record_lifecycle mutation
author_truth copied from Canon
raw resolution_condition copied from Canon
hash
timestamp
Commit ID
Generation ID
Evidence ID
Evidence quote or offset
runtime counter
provider or model setting
publication path
full Canon or Story-state snapshot
future prose
```

Planning may refer to a Thread or Ending criterion by ID and describe a safe dramatic purpose. It must not copy secret author truth into general plan fields that may later enter Writer context.

Deprecated Series-map names:

```text
ending_position
major_thread_targets[].purpose without start/target/action
array<string> relationship targets
array<string> thread targets
```

Deprecated Volume names:

```text
objective
chapter_count
required_thread_ids
required_thread_actions
```

Deprecated Chapter names:

```text
objective
required_thread_actions
free-form scene list
```

Use the exact fields in this document.

---

## 20. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
candidate and adopted root separation
Series-map exact Schema
Volume-design exact Schema
Chapter-design exact Schema
Brief Volume-count equality
contiguous Volume and Chapter numbers
valid structural-role placement
protagonist continuity across Volumes
Relationship continuity across Volumes
Major-thread operation/status/progress continuity
required Major-thread final resolution
required Ending-criterion final coverage
nonfinal reader-question requirement
final Volume series-transition null
Volume Chapter-function count equality
Chapter Scene-plan count equality
actual source-generation reference validation
parent-plan hash validation
retired-reference rejection
whole-candidate revision replacement
residual-issue adoption behavior
unknown-field rejection
code-owned field injection rejection
secret author-truth duplication rejection
canonical ordering and hash stability
```
