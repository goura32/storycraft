# Ledger contracts: Story state

This document is the normative contract for mutable adopted story values stored at:

```text
canon/generations/<generation-id>/story-state.json
```

Stable identity, classification, immutable characterization, immutable world facts, thread definitions, ending criteria, and knowledge-item definitions belong to [`canon_records.md`](canon_records.md). Evidence and candidate update records belong to [`evidence_and_updates.md`](evidence_and_updates.md).

Every saved object defined here uses `additionalProperties: false`.

---

## 1. Root file contract

`story-state.json` contains exactly five fields.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `character_states` | array<Character state> | yes | no | `[]` | code | generation replacement only | atomic replacement during commit | state changes proposed from prose require adopted evidence | exactly one row for every adopted Character record; sorted by `character_id` | `story-state.json` |
| `relationship_states` | array<Relationship state> | yes | no | `[]` | code | generation replacement only | atomic replacement during commit | state changes proposed from prose require adopted evidence | exactly one row for every adopted Relationship record; sorted by `relationship_id` | `story-state.json` |
| `thread_states` | array<Thread state> | yes | no | `[]` | code | generation replacement only | atomic replacement during commit or volume handoff | thread changes proposed from prose require adopted evidence | exactly one row for every adopted Thread record; sorted by `thread_id` | `story-state.json` |
| `knowledge_states` | array<Knowledge state> | yes | no | `[]` | code | generation replacement only | atomic replacement during commit | every non-default prose-derived transition requires adopted evidence | sparse canonical rows; unique `(fact_id, audience_type, audience_id)`; sorted by that tuple | `story-state.json` |
| `story_clock` | Story clock object | yes | no | none | code | generation replacement only | atomic replacement during scene commit | time changes proposed from prose require adopted evidence when the time value changes | complete Story clock contract | `story-state.json` |

A saved Story state must never contain fixed Canon records, Knowledge item definitions, evidence records, candidate local keys, review issues, runtime retry counters, or publication state.

---

## 2. Canonical ordering and reference rules

For deterministic serialization and hashing:

- `character_states` is sorted by `character_id`.
- `relationship_states` is sorted by `relationship_id`.
- `thread_states` is sorted by `thread_id`.
- `knowledge_states` is sorted by:
  1. `fact_id`;
  2. `audience_type`, with `character` before `reader`;
  3. `audience_id`, with non-null IDs before `null`.
- State arrays contain no duplicate key.
- All strings are valid UTF-8 and normalized to NFC.
- Every persistent reference resolves in the same adopted generation.
- `last_scene_id` resolves to an adopted Scene manifest.
- A retired Canon record retains its State row for historical continuity, but normal generation cannot mutate that row after retirement.
- World entities, Temporal rules, Ending criteria, and Knowledge item definitions do not have separate mutable State rows.

---

## 3. State-row existence rules

### 3.1 Explicit rows

The following rows are always explicit:

```text
one Character state per adopted Character
one Relationship state per adopted Relationship
one Thread state per adopted Thread
```

This includes records whose Canon lifecycle is `inactive` or `retired`.

### 3.2 Sparse Knowledge state

Knowledge state is sparse.

The implicit status of a missing row is:

```text
audience_type = character:
  unknown

audience_type = reader:
  withheld
```

Canonical saved form rules:

- A row whose status equals its implicit default is omitted.
- A transition from an implicit default creates a row.
- A transition back to the implicit default removes the row only when that transition is permitted by the status matrix.
- `before` validation treats an absent row as the appropriate implicit default.
- This sparse rule avoids a full `knowledge items × characters` Cartesian product while preserving deterministic `before` validation.

---

## 4. Character state

A Character state stores only current mutable values. Stable character identity and anchors remain in the Character record.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `character_id` | Character ID | yes | no | none | code | immutable | none | none | pattern `char-[0-9]{6}`; resolves to one adopted Character record | `story-state.json` |
| `location_id` | Location World entity ID | yes | yes | `null` | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene; not required for Genesis initialization | null or pattern `loc-[0-9]{6}` resolving to an adopted active or inactive Location record | `story-state.json` |
| `physical_condition` | string | yes | yes | `null` | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | null or NFC nonempty string | `story-state.json` |
| `emotional_state` | string | yes | yes | `null` | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | null or NFC nonempty string | `story-state.json` |
| `current_goal` | string | yes | yes | `null` | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | null or NFC nonempty string | `story-state.json` |
| `current_pressure` | string | yes | yes | `null` | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | null or NFC nonempty string | `story-state.json` |

### 4.1 Character-state invariants

- `character_id` is never changed.
- A scene update is rejected when `before` does not exactly match the HEAD State value.
- `location_id` may not point to a retired Location record.
- A retired Character retains its final Character state, but no normal scene update may target it.
- A prose-created Character must receive a complete Character state row in the same commit that adopts the Character record.
- Nullable does not permit an empty string. Use `null` when the value is genuinely unspecified.

---

## 5. Relationship state

A Relationship state is keyed by the adopted Relationship record. Direction names are determined by the fixed participant order in that record:

```text
a_to_b:
  participant_a_id's state toward participant_b_id

b_to_a:
  participant_b_id's state toward participant_a_id
```

### 5.1 Relationship state object

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `relationship_id` | Relationship ID | yes | no | none | code | immutable | none | none | pattern `rel-[0-9]{6}`; resolves to one adopted Relationship record | `story-state.json` |
| `public_relation` | string | yes | no | none | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | NFC nonempty string | `story-state.json` |
| `a_to_b` | Directional relationship state | yes | no | none | initial design / continuity candidate, adopted by code | mutable | field-specific operations | required for each changed child field | complete Directional relationship state | `story-state.json` |
| `b_to_a` | Directional relationship state | yes | no | none | initial design / continuity candidate, adopted by code | mutable | field-specific operations | required for each changed child field | complete Directional relationship state | `story-state.json` |
| `shared_state` | string | yes | no | none | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | NFC nonempty string | `story-state.json` |

### 5.2 Directional relationship state

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `trust` | enum `trust` from `canon_records.md` | yes | no | none | initial design / continuity candidate, adopted by code | mutable | `transition` | required when changed by a scene | exact enum; `before != after` | `story-state.json` |
| `perception` | string | yes | no | none | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | NFC nonempty string | `story-state.json` |
| `emotional_stance` | string | yes | no | none | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | NFC nonempty string | `story-state.json` |
| `current_intention` | string | yes | no | none | initial design / continuity candidate, adopted by code | mutable | `set` | required when changed by a scene | NFC nonempty string | `story-state.json` |

### 5.3 Relationship-state invariants

- The Relationship record's participants are fixed; State never repeats or changes those participant IDs.
- A prose-created Relationship must receive one complete Relationship state in the same commit.
- Trust may transition between any two distinct valid `trust` values when supported by evidence. A no-op transition is forbidden.
- A change to one direction does not imply a change to the opposite direction.
- A retired Relationship retains its final State row but cannot receive normal scene updates.

---

## 6. Thread state

Thread definition, truth, resolution condition, requirement, scope, and lifecycle remain in the Thread record. Thread state stores only current narrative progression and the most recently adopted volume disposition.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `thread_id` | Thread ID | yes | no | none | code | immutable | none | none | pattern `thread-[0-9]{6}`; resolves to one adopted Thread record | `story-state.json` |
| `thread_status` | enum `thread_status` from `canon_records.md` | yes | no | `open` | code from adopted candidate | mutable | thread-operation matrix | required for scene-derived change | exact enum and status/progress matrix | `story-state.json` |
| `progress` | integer | yes | no | `0` | code from adopted candidate | mutable | thread-operation matrix | required for scene-derived change | integer `0..4` and status/progress matrix | `story-state.json` |
| `volume_disposition` | enum `volume_disposition` from `canon_records.md` | yes | yes | `null` | code at `VH-ID` | mutable | `set` at volume handoff only | handoff review, not prose evidence | null before the first applicable handoff; otherwise exact enum and disposition matrix | `story-state.json` |

### 6.1 Status/progress matrix

| `thread_status` | permitted `progress` | meaning |
|---|---:|---|
| `open` | `0` | Defined but not yet introduced in adopted prose |
| `in_progress` | `1`, `2`, or `3` | Introduced and advancing |
| `resolved` | `4` | Resolution is established in adopted prose |
| `retired` | `0`, `1`, `2`, or `3` | Deliberately abandoned without resolution |

### 6.2 Thread-operation matrix

| operation | permitted before | required after | notes |
|---|---|---|---|
| `introduce` | `open / 0` | `in_progress / 1` | First adopted prose introduction |
| `advance` | `in_progress / 1` or `2` | `in_progress / before_progress + 1` | Cannot skip progress levels |
| `resolve` | `in_progress / 1`, `2`, or `3` | `resolved / 4` | Evidence must establish the resolution, not merely mention the thread |
| `retire` | `open / 0` or `in_progress / 1..3` | `retired / same progress` | Forbidden for a required Major thread |

Additional rules:

- `resolved` and `retired` are terminal during normal generation.
- A no-op status or progress update is forbidden.
- A prose-created Supporting thread is adopted with `open / 0` unless the same prose contains a separately evidenced `introduce` operation.
- `thread_status=retired` requires the corresponding Thread record's `record_lifecycle=retired` in the same committed generation.
- `thread_status=resolved` does not change generic `record_lifecycle`.

### 6.3 Volume-disposition matrix

| `volume_disposition` | required Thread state after `VH-ID` | additional condition |
|---|---|---|
| `resolve` | `resolved / 4` | Resolution must already be supported by adopted evidence |
| `carry_over` | `in_progress / 1..3` | Thread record `scope` must be `series` |
| `retire` | `retired / 0..3` | Thread record lifecycle must be `retired`; forbidden for a required Major thread |

`volume_disposition` records the most recent adopted volume-handoff decision. It remains unchanged until a later `VH-ID` replaces it.

---

## 7. Knowledge state

Knowledge state stores one audience's current status for one adopted Knowledge item.

### 7.1 Knowledge state row

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `fact_id` | Knowledge item ID | yes | no | none | code | immutable | none | none | pattern `fact-[0-9]{6}`; resolves to an adopted non-retired Knowledge item | `story-state.json` |
| `audience_type` | enum `knowledge_audience_type` from `canon_records.md` | yes | no | none | code from adopted candidate | immutable | none | none | `character` or `reader` | `story-state.json` |
| `audience_id` | Character ID | yes | yes | none | code from adopted candidate | immutable | none | none | non-null adopted Character ID iff `audience_type=character`; null iff `audience_type=reader` | `story-state.json` |
| `status` | audience-specific knowledge status | yes | no | implicit by audience type | continuity candidate, adopted by code | mutable | `transition` | required for prose-derived transition | Character or Reader transition matrix; explicit default rows forbidden | `story-state.json` |

### 7.2 Character knowledge transition matrix

Permitted statuses:

```text
unknown
suspects
misunderstands
partially_knows
knows
```

Permitted transitions:

| before | permitted after |
|---|---|
| `unknown` | `suspects`, `misunderstands`, `partially_knows`, `knows` |
| `suspects` | `misunderstands`, `partially_knows`, `knows` |
| `misunderstands` | `suspects`, `partially_knows`, `knows` |
| `partially_knows` | `misunderstands`, `knows` |
| `knows` | none |

### 7.3 Reader knowledge transition matrix

Permitted statuses:

```text
withheld
hinted
partially_revealed
revealed
```

Permitted transitions:

| before | permitted after |
|---|---|
| `withheld` | `hinted`, `partially_revealed`, `revealed` |
| `hinted` | `partially_revealed`, `revealed` |
| `partially_revealed` | `revealed` |
| `revealed` | none |

### 7.4 Knowledge-state invariants

- A no-op transition is forbidden.
- Reader knowledge cannot move backward.
- Character `knows` is terminal during normal generation.
- Character and Reader status enums are not interchangeable.
- Updating one character's status does not update any other character or the reader.
- A Knowledge item with `record_lifecycle=retired` retains existing State rows but cannot receive new normal-generation transitions.
- The Writer View receives only the audience-specific projected status and `writer_visible_label`; it never receives `author_truth`.

---

## 8. Story clock and current position

`story_clock` tracks narrative adoption order, the current story-time label, optional parallel grouping, and the most recently adopted scene position.

### 8.1 Story clock object

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `current_order` | integer | yes | no | `0` | code | mutable | increment by scene commit | none for the increment itself | integer `>=0`; Genesis is `0`; every adopted scene increments by exactly `1` | `story-state.json` |
| `time_label` | string | yes | yes | `null` | initial design / time-update candidate, adopted by code | mutable | `set` through time update | required when a scene changes the stored label | null or NFC nonempty string | `story-state.json` |
| `parallel_group_id` | string | yes | yes | `null` | initial design / time-update candidate, adopted by code | mutable | `set` through time update | required when changed by a scene | null or NFC nonempty string | `story-state.json` |
| `last_scene_id` | Scene ID | yes | yes | `null` | code | mutable | replace at scene commit | none | null at Genesis; otherwise the most recently adopted scene | `story-state.json` |
| `current_volume_number` | integer | yes | yes | `null` | code | mutable | replace at scene commit | none | null at Genesis; otherwise integer `>=1` matching `last_scene_id` | `story-state.json` |
| `current_chapter_number` | integer | yes | yes | `null` | code | mutable | replace at scene commit | none | null at Genesis; otherwise integer `>=1` matching `last_scene_id` | `story-state.json` |
| `current_scene_number` | integer | yes | yes | `null` | code | mutable | replace at scene commit | none | null at Genesis; otherwise integer `>=1` matching `last_scene_id` | `story-state.json` |

### 8.2 Genesis clock

At Genesis:

```json
{
  "current_order": 0,
  "time_label": null,
  "parallel_group_id": null,
  "last_scene_id": null,
  "current_volume_number": null,
  "current_chapter_number": null,
  "current_scene_number": null
}
```

`time_label` and `parallel_group_id` may be initialized to non-null values when the accepted initial temporal design provides them. Position fields remain null until the first scene commit.

### 8.3 Scene-commit position update

For an adopted scene such as `v04-c003-s002`, code sets:

```text
current_order:
  previous current_order + 1

last_scene_id:
  v04-c003-s002

current_volume_number:
  4

current_chapter_number:
  3

current_scene_number:
  2
```

A scene commit is rejected when the numeric fields do not match the adopted `scene_id`.

### 8.4 Time-relation rules

| `time_relation` | required behavior |
|---|---|
| `same_time` | `time_label` and `parallel_group_id` remain unchanged; a time update should be omitted unless it carries a mechanically meaningful clarification |
| `later` | `time_label` must be a non-null adopted value representing a later point; `parallel_group_id=null` |
| `next_day` | `time_label` must identify the following day; `parallel_group_id=null` |
| `after_interval` | `time_label` must be non-null and `elapsed_hint` must be non-null in the accepted time update; `parallel_group_id=null` |
| `parallel` | `parallel_group_id` must be non-null; `time_label` must identify the parallel time context |

`current_order` is adoption order, not chronological time. Parallel scenes still increment `current_order`.

---

## 9. Genesis initialization

At `INIT-ID`, code builds the first complete Story state in the same atomic Genesis adoption that writes Canon records and Knowledge items.

### 9.1 Required initialization

Code must create:

```text
one Character state for every adopted Character
one Relationship state for every adopted Relationship
one Thread state for every adopted Thread
zero or more non-default Knowledge state rows
one complete Story clock object
```

### 9.2 Genesis validation

Genesis adoption fails when:

- a Character lacks a complete Character state;
- a Relationship lacks a complete Relationship state;
- a Thread lacks a Thread state;
- a State row references a local key or persistent ID that was not adopted;
- a Knowledge state refers to an unknown Knowledge item or Character;
- an explicit Knowledge state stores its implicit default;
- a Thread status/progress pair violates the matrix;
- the Story clock is incomplete;
- any State row is duplicated.

Initial-design values do not require prose evidence, but they must originate from the structurally valid accepted initial-design bundle and its local-key mapping.

---

## 10. Scene-derived creation initialization

When one scene commit adopts a new Canon record, it must initialize the corresponding State atomically.

| adopted record | required State action |
|---|---|
| Character | append one complete Character state |
| Relationship | append one complete Relationship state |
| World entity | no State row |
| Supporting Thread | append one Thread state, normally `open / 0` |
| Knowledge item | append no default rows; append only explicitly proposed non-default Knowledge states |
| Temporal rule | normal scene creation forbidden |
| Major Thread | normal scene creation forbidden |
| Ending criterion | normal scene creation forbidden |

If State initialization fails, neither the new Canon record nor the scene commit is adopted.

---

## 11. Scene-commit merge order

Code applies a structurally valid accepted continuity delta in this order:

1. load the complete HEAD `current-canon.json`, `knowledge-items.json`, and `story-state.json`;
2. validate every referenced target and every `before` value;
3. validate evidence against the frozen adopted prose candidate;
4. validate and allocate IDs for new Canon and Knowledge records;
5. initialize State rows for newly adopted Character, Relationship, and Thread records;
6. apply existing Character and Relationship state updates;
7. apply Knowledge state transitions;
8. apply Thread state transitions;
9. apply a non-null time update when present;
10. increment `story_clock.current_order` and set the adopted scene position;
11. enforce all cross-record, lifecycle, status, and ordering invariants;
12. serialize the new generation canonically and calculate hashes;
13. adopt the generation only through the commit transaction.

The merge is atomic. A failure at any step leaves HEAD and adopted scene artifacts unchanged.

---

## 12. `before` and `after` validation

For every mutable State update:

```text
candidate before
  must equal
HEAD Story state before the scene
```

For sparse Knowledge state:

```text
missing character row = unknown
missing reader row = withheld
```

The resulting `after` value must:

- differ from `before`;
- satisfy the applicable operation and transition matrix;
- be supported by the required literal prose evidence;
- appear in the committed `story-state.json`;
- be reflected by the new Story-state hash in the Commit manifest.

A delta that names an update but produces no corresponding after-State change is rejected.

---

## 13. Canon lifecycle interaction

| Canon lifecycle | State-row rule |
|---|---|
| `active` | State row is retained and may be updated when otherwise permitted |
| `inactive` | State row is retained; updates are permitted only when the scene explicitly reactivates or uses the record and the Canon lifecycle transition is valid |
| `retired` | State row is retained as final history; normal generation updates are forbidden |

Thread-specific rules:

- `thread_status=retired` requires the corresponding Thread record lifecycle to be `retired`.
- `thread_status=resolved` does not require retirement.
- Reactivating a retired Thread or changing a resolved Thread requires an explicit migration outside the normal story pipeline.

---

## 14. Forbidden duplication

The following fixed fields are forbidden in Story state:

```text
Character:
  name
  aliases
  role
  core_trait
  values
  background
  immutable_facts
  appearance_anchor
  speech_anchor

Relationship:
  participant_a_id
  participant_b_id
  relationship_type
  relationship_origin
  structural_role

World / Temporal:
  all fixed record fields

Thread:
  thread_type
  description
  author_truth
  resolution_condition
  presentation_rule
  required

Ending criterion:
  all record fields

Knowledge item:
  subject_type
  subject_id
  canonical_fact
  writer_visible_label
  author_truth

Shared Canon metadata:
  record_type
  record_origin
  scope
  record_lifecycle
  created_scene_id
```

The following mutable State fields are forbidden in Canon record files:

```text
Character state fields
Relationship state fields
Thread state fields
Knowledge state rows
Story clock and current-position fields
```

---

## 15. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
complete Genesis State initialization
one explicit State row per Character, Relationship, and Thread
sparse Knowledge-state defaults
duplicate State-key rejection
unknown-reference rejection
before-value mismatch rejection
no-op update rejection
Character-state evidence enforcement
directional Relationship updates
Thread status/progress operation matrix
required Major-thread retirement rejection
volume-disposition matrix
audience-specific Knowledge status validation
reader knowledge monotonicity
Story-clock increment by exactly one per scene
scene ID and position-number consistency
parallel-time behavior
retired-record update rejection
new-record and State initialization atomicity
delta-to-after-State correspondence
canonical array ordering
unknown-field rejection
```
