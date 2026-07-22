# Data contracts: Scene artifacts

This document is the normative contract for:

- the Scene-card content candidate produced by SC-01;
- the frozen checkpoint and adopted Scene card;
- prose candidates, frozen prose, and adopted prose;
- Scene-card authorization of continuity changes;
- the immutable Scene artifact set adopted by one scene commit.

Planning inputs are defined by [`planning_artifacts.md`](planning_artifacts.md). Canon identity and enums are defined by [`../ledger/canon_records.md`](../ledger/canon_records.md). Mutable current values are defined by [`../ledger/story_state.md`](../ledger/story_state.md). Continuity candidates, committed deltas, and Evidence records are defined only by [`../ledger/evidence_and_updates.md`](../ledger/evidence_and_updates.md). Candidate, checkpoint, Scene-manifest, and commit behavior is defined by [`../ledger/runtime_records.md`](../ledger/runtime_records.md). Context projections are defined by [`../../context_contracts.md`](../../context_contracts.md). Effective length and profile settings are defined by [`../../configuration_contracts.md`](../../configuration_contracts.md).

Every saved JSON object and every structured LLM response defined here uses `additionalProperties: false`.

---

## 1. Scene lifecycle and authority

One scene passes through these artifact states:

```text
Scene-card content candidate
→ frozen checkpoint Scene card
→ prose candidate
→ frozen checkpoint prose
→ validated candidate continuity delta
→ committed continuity delta
→ adopted Scene artifact set
```

Authority by phase:

| concern | authority |
|---|---|
| Intended narrative work | frozen Scene card |
| Exact narrative text | frozen prose |
| Candidate continuity interpretation | checkpoint continuity delta |
| Actually adopted continuity changes | committed continuity delta plus resulting Canon/State generation |
| Adopted Scene paths and hashes | Scene manifest |
| Resume position | Candidate manifest, Checkpoint manifest, and Run state |

A review artifact may identify defects but never becomes a Scene artifact or continuity authority.

---

## 2. Canonical paths

### 2.1 Candidate paths

```text
runtime/candidates/scenes/v01/c001/s001/scene-card/
  scene-card.json
  review.json
  candidate-manifest.json

runtime/candidates/scenes/v01/c001/s001/prose/
  prose.md
  review.json
  candidate-manifest.json

runtime/candidates/scenes/v01/c001/s001/continuity/
  continuity-delta.json
  review.json
  candidate-manifest.json
```

Only each directory's `candidate-manifest.json` is a candidate resume authority.

### 2.2 Checkpoint paths

```text
runtime/checkpoints/scenes/v01/c001/s001/
  scene-card.json
  prose.md
  continuity-delta.json
  checkpoint-manifest.json
```

At the checkpoint path:

- `scene-card.json` is the frozen Scene card defined by this document;
- `prose.md` is the frozen canonical prose defined by this document;
- `continuity-delta.json` is the validated candidate delta defined by `evidence_and_updates.md`.

### 2.3 Adopted paths

```text
artifacts/scenes/v01/c001/s001/
  scene-card.json
  prose.md
  continuity-delta.json
  scene-manifest.json
```

At the adopted path:

- Scene-card bytes are identical to the frozen checkpoint Scene-card bytes;
- prose bytes are identical to the frozen checkpoint prose bytes;
- continuity-delta bytes use the committed-delta Schema and normally differ from checkpoint candidate-delta bytes;
- `scene-manifest.json` uses the Runtime contract.

---

## 3. Scene identity

### 3.1 Scene ID

| property | contract |
|---|---|
| format | `vNN-cNNN-sNNN` |
| example | `v04-c003-s002` |
| creator | code |
| volume digits | exactly two |
| chapter digits | exactly three |
| scene digits | exactly three |
| numeric minimum | every component is at least `1` |
| consistency | numeric fields, plan entry, checkpoint directory, adopted directory, Story clock, and Scene manifest all agree |

The LLM never emits `scene_id`, `volume_number`, `chapter_number`, or `scene_number`.

### 3.2 Source-generation rule

The frozen Scene card is based on one exact adopted generation.

Before COMMIT-01, code verifies:

```text
frozen Scene-card source_generation_id
  ==
current canon/HEAD
```

If HEAD changed after SC-CHK, the checkpoint is stale. Code does not rebase the Scene card or delta automatically. It returns to the stage required by the Pipeline contract and rebuilds from the new HEAD.

---

# Part I: Scene-card content candidate

## 4. SC-01 output root

SC-01 returns exactly these fields:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `pov_character_id` | Character ID | yes | no | none | LLM | candidate-only | adopted non-retired Character; compatible with Chapter Scene-function target |
| `participant_ids` | array<Character ID> | yes | no | none | LLM | candidate-only | `1..30`; unique; sorted by ID after normalization; contains POV; every Character non-retired |
| `location_id` | Location ID | yes | yes | `null` | LLM | candidate-only | null or adopted non-retired Location |
| `required_world_entity_ids` | array<World entity ID> | yes | no | `[]` | LLM | candidate-only | `0..50`; unique and sorted; every record non-retired; contains non-null `location_id` |
| `required_temporal_rule_ids` | array<Temporal rule ID> | yes | no | `[]` | LLM | candidate-only | `0..30`; unique and sorted; every record non-retired |
| `time_relation` | enum `time_relation` | yes | no | none | LLM | candidate-only | Section 5 |
| `time_label` | string | yes | yes | `null` | LLM | candidate-only | Section 5 |
| `parallel_group_id` | string | yes | yes | `null` | LLM | candidate-only | Section 5 |
| `scene_purpose` | string | yes | no | none | LLM | candidate-only | NFC `1..1500` code points; one clear dramatic purpose |
| `required_beats` | array<string> | yes | no | none | LLM | candidate-only | `1..12`; order is narratively significant; each NFC `1..500`; no duplicate |
| `emotional_change_target` | string | yes | no | none | LLM | candidate-only | NFC `1..750`; observable emotional movement |
| `relationship_change_targets` | array<Scene Relationship target> | yes | no | `[]` | LLM | candidate-only | `0..10`; unique Relationship IDs; sorted |
| `thread_actions` | array<Scene Thread-action candidate> | yes | no | `[]` | LLM | candidate-only | unique Thread IDs; sorted |
| `character_knowledge_targets` | array<Character Knowledge target candidate> | yes | no | `[]` | LLM | candidate-only | unique `(fact_id,character_id)`; sorted |
| `reader_disclosures` | array<Reader-disclosure candidate> | yes | no | `[]` | LLM | candidate-only | unique fact IDs; sorted |
| `ending_criterion_targets` | array<Scene Ending target> | yes | no | `[]` | LLM | candidate-only | unique criterion IDs; sorted |
| `canon_metadata_change_targets` | array<Canon-metadata change target> | yes | no | `[]` | LLM | candidate-only | unique `(target_type,target_id,field_path)`; sorted |
| `new_item_policy` | New-item policy | yes | no | none | LLM | candidate-only | Section 12 |

SC-01 must not emit:

```text
source generation metadata
chapter-plan path or hash
accepted candidate hash
forbidden disclosures
allowed update targets
length guidance
chapter completion role
timestamps
persistent IDs for new records
Evidence proposals
```

---

## 5. Scene time plan

The candidate time fields describe the intended resulting Story-clock label and parallel group for this scene.

### 5.1 Relation rules

| `time_relation` | `time_label` | `parallel_group_id` | required relationship to HEAD |
|---|---|---|---|
| `same_time` | equals current Story-clock `time_label` | equals current `parallel_group_id` | no stored time-value change |
| `later` | non-null | null | identifies a later point than current label |
| `next_day` | non-null | null | identifies the following narrative day |
| `after_interval` | non-null | null | identifies the later point; prose must make the interval supportable |
| `parallel` | non-null | non-null | identifies the parallel context and group |

Additional rules:

- `same_time` with a different label or group is invalid.
- `later`, `next_day`, or `after_interval` with an unchanged label is invalid.
- A non-null time-changing plan authorizes, but does not fabricate, a Time update.
- If frozen prose does not establish the planned time change, the Delta must omit it and the prose review must report the unmet Scene-card target.
- Story-clock `current_order` and scene-position fields are never Scene-card or LLM outputs.

---

## 6. Scene Relationship target

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `relationship_id` | Relationship ID | yes | no | none | LLM | candidate-only | adopted non-retired Relationship; at least one endpoint appears in `participant_ids` |
| `start_state_summary` | string | yes | no | none | LLM | candidate-only | NFC `1..1000`; compatible with projected current Relationship state |
| `target_state_summary` | string | yes | no | none | LLM | candidate-only | NFC `1..1000`; meaningfully differs from start |
| `required_change` | string | yes | no | none | LLM | candidate-only | NFC `1..750`; observable change |
| `purpose` | string | yes | no | none | LLM | candidate-only | NFC `1..750`; dramatic function |
| `required` | boolean | yes | no | `true` | LLM | candidate-only | semantic review requirement |

`required=true` is a semantic prose target. It does not permit code to create a Relationship-state update without literal prose evidence.

---

## 7. Scene Thread-action candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `thread_id` | Thread ID | yes | no | none | LLM | candidate-only | adopted non-retired Thread; compatible with Chapter plan |
| `operation` | enum `thread_action` | yes | no | none | LLM | candidate-only | operation is possible from current Thread state |
| `target_status` | enum `thread_status` | yes | no | none | LLM | candidate-only | exact operation result |
| `target_progress` | integer | yes | no | none | LLM | candidate-only | exact operation result; `0..4` |
| `purpose` | string | yes | no | none | LLM | candidate-only | NFC `1..750` |
| `required` | boolean | yes | no | `true` | LLM | candidate-only | semantic review requirement |

Code obtains `start_status` and `start_progress` from HEAD and does not trust an LLM copy.

A scene may contain at most one operation for one adopted Thread.

A newly proposed Supporting Thread is initialized inside its proposal under the Continuity contract and is not named here before prose exists.

---

## 8. Character Knowledge target candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `fact_id` | Knowledge item ID | yes | no | none | LLM | candidate-only | adopted non-retired Knowledge item |
| `character_id` | Character ID | yes | no | none | LLM | candidate-only | appears in `participant_ids` |
| `target_status` | enum `character_knowledge_status` | yes | no | none | LLM | candidate-only | valid non-no-op transition from current implicit or explicit status |
| `purpose` | string | yes | no | none | LLM | candidate-only | NFC `1..750` |
| `required` | boolean | yes | no | `true` | LLM | candidate-only | semantic review requirement |

Code injects the exact `start_status` from Story state, using implicit `unknown` when the row is absent.

---

## 9. Reader-disclosure candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `fact_id` | Knowledge item ID | yes | no | none | LLM | candidate-only | adopted non-retired Knowledge item |
| `target_status` | enum `reader_knowledge_status` | yes | no | none | LLM | candidate-only | valid forward non-no-op transition |
| `purpose` | string | yes | no | none | LLM | candidate-only | NFC `1..750` |
| `required` | boolean | yes | no | `true` | LLM | candidate-only | semantic review requirement |

Code injects exact `start_status`, using implicit `withheld` when the reader row is absent.

A Writer-facing disclosure exposes the Knowledge item's safe label and allowed target status, never its hidden `author_truth`.

---

## 10. Scene Ending target

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `criterion_id` | Ending criterion ID | yes | no | none | LLM | candidate-only | adopted non-retired Ending criterion; present in Chapter or Volume planning context |
| `intended_relation` | enum `evidence_relation` | yes | no | `supports` | LLM | candidate-only | `supports` or `contradicts` |
| `purpose` | string | yes | no | none | LLM | candidate-only | NFC `1..750`; safe dramatic purpose without quoting hidden truth |
| `required` | boolean | yes | no | `false` | LLM | candidate-only | semantic review requirement |

`intended_relation=contradicts` is permitted only when the plan explicitly calls for a setback or contradiction risk. It does not itself create contradiction Evidence.

---

## 11. Canon-metadata change target

This object explicitly authorizes a potential mutable metadata change. It does not authorize Character, Relationship, Thread, Knowledge-state, or Story-clock changes, which have dedicated Scene-card fields.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `target_type` | enum | yes | no | none | LLM | candidate-only | `canon_record` or `knowledge_item_record` |
| `target_id` | persistent record ID | yes | no | none | LLM | candidate-only | adopted non-retired record compatible with target type |
| `field_path` | JSON Pointer string | yes | no | none | LLM | candidate-only | one of `/scope`, `/record_lifecycle`, or `/related_ids` where permitted by the target record |
| `operation` | enum `existing_update_operation` | yes | no | none | LLM | candidate-only | exact operation permitted by Continuity field matrix |
| `purpose` | string | yes | no | none | LLM | candidate-only | NFC `1..750` |
| `required` | boolean | yes | no | `false` | LLM | candidate-only | semantic review requirement |

Rules:

- `/related_ids` is allowed only for a Temporal-rule record.
- Lifecycle retirement must be narratively established and must satisfy Canon/State cross-rules.
- An inactive Character used as the POV or participant must include an explicit `/record_lifecycle` transition intent to `active`.
- The Scene card never contains the proposed `after` value. The Continuity candidate proposes it and code validates it.

---

## 12. New-item policy

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `allowed_types` | array<enum `new_item_proposal_type`> | yes | no | `[]` | LLM | candidate-only | unique; canonical registry order |
| `allow_knowledge_items` | boolean | yes | no | `false` | LLM | candidate-only | boolean |
| `max_items` | integer | yes | no | `0` | LLM | candidate-only | `0..configuration.max_new_items_per_scene`; total across `new_item_proposals` and `knowledge_item_proposals` |
| `max_scope` | enum `scope` | yes | yes | `null` | LLM | candidate-only | null iff `max_items=0`; otherwise maximum permitted proposal scope |
| `purpose` | string | yes | no | none | LLM | candidate-only | NFC `1..750`; explains why spontaneous persistent creation is or is not allowed |

Conditional rules:

```text
max_items = 0:
  allowed_types = []
  allow_knowledge_items = false
  max_scope = null

max_items > 0:
  allowed_types is nonempty
  OR allow_knowledge_items = true
  max_scope is non-null
```

`max_items` is a hard limit. Length guidance and dramatic targets remain soft or semantic.

A new item is permitted, not required. The Delta must never invent a proposal merely to consume the allowance.

---

## 13. SC-01 validation against Chapter planning

SC-01 receives:

```text
adopted Chapter design
the target Scene-function entry
current adopted generation
previous adopted Scene handoff when present
Scene-card planning context
Effective config profiles
```

Code validates:

- target POV equals the Chapter Scene-function target;
- every Chapter-required Character appears in `participant_ids`;
- the planned Location is preserved when non-null;
- every Chapter-required beat appears in `required_beats`;
- each planned Thread target is represented with the exact operation and target pair;
- each planned Ending criterion is represented;
- `emotional_change_target` is compatible with the Chapter Scene-function target;
- no retired record is referenced;
- no unknown or new persistent ID is present;
- the new-item allowance does not exceed configuration;
- the candidate contains no secret author truth.

SC-01 may add optional participants, beats, knowledge targets, and safe context references when they remain compatible with the Chapter plan and current generation.

---

## 14. SC-02 and SC-REV

SC-02 returns the generic Review-result Schema defined by `review_and_audit.md`.

At minimum, it assesses:

```text
Chapter Scene-function preservation
POV feasibility
cast and Location feasibility
time-plan consistency
beat completeness
emotional-change clarity
Relationship-change feasibility
Thread operation validity
Knowledge-disclosure validity
Ending-target safety
Canon-metadata target validity
new-item policy necessity and bounds
forbidden disclosure risk
```

SC-REV receives the latest structurally valid Scene-card content candidate and all current issues. It returns one complete replacement candidate using the exact SC-01 Schema.

Partial patches are forbidden.

---

# Part II: Frozen Scene card

## 15. SC-CHK behavior

SC-CHK is code-only.

It:

1. validates the accepted SC candidate against current HEAD and Chapter design;
2. copies exact current Thread and Knowledge starting statuses;
3. derives safe forbidden-disclosure records;
4. derives exact allowed-update targets;
5. copies effective length guidance;
6. copies `chapter_completion_role` from the Chapter Scene-function entry;
7. adds source metadata and Scene coordinates;
8. writes canonical checkpoint `scene-card.json`;
9. updates the Checkpoint manifest to `CARD_ACCEPTED`.

Once written, the frozen Scene card is immutable.

---

## 16. Frozen Scene-card root

The frozen Scene card contains exactly these fields:

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | immutable | exact constant | frozen/adopted Scene card |
| `scene_id` | Scene ID | yes | no | none | code | immutable | Section 3 | frozen/adopted Scene card |
| `volume_number` | integer | yes | no | none | code | immutable | matches Scene ID and Chapter design | frozen/adopted Scene card |
| `chapter_number` | integer | yes | no | none | code | immutable | matches Scene ID and Chapter design | frozen/adopted Scene card |
| `scene_number` | integer | yes | no | none | code | immutable | matches Scene ID and Chapter Scene-function entry | frozen/adopted Scene card |
| `source_generation_id` | Generation ID | yes | no | none | code | immutable | HEAD used by SC-01/SC-CHK | frozen/adopted Scene card |
| `source_generation_manifest_sha256` | SHA-256 | yes | no | none | code | immutable | matches source Generation manifest | frozen/adopted Scene card |
| `chapter_design_path` | workspace-relative path | yes | no | none | code | immutable | exact adopted Chapter-design path | frozen/adopted Scene card |
| `chapter_design_sha256` | SHA-256 | yes | no | none | code | immutable | matches adopted Chapter design | frozen/adopted Scene card |
| `accepted_candidate_sha256` | SHA-256 | yes | no | none | code | immutable | accepted SC content candidate | frozen/adopted Scene card |
| `pov_character_id` | Character ID | yes | no | none | code from candidate | immutable | Section 4 | frozen/adopted Scene card |
| `participant_ids` | array<Character ID> | yes | no | none | code from candidate | immutable | Section 4 | frozen/adopted Scene card |
| `location_id` | Location ID | yes | yes | `null` | code from candidate | immutable | Section 4 | frozen/adopted Scene card |
| `required_world_entity_ids` | array<World entity ID> | yes | no | `[]` | code from candidate | immutable | Section 4 | frozen/adopted Scene card |
| `required_temporal_rule_ids` | array<Temporal rule ID> | yes | no | `[]` | code from candidate | immutable | Section 4 | frozen/adopted Scene card |
| `time_relation` | enum `time_relation` | yes | no | none | code from candidate | immutable | Section 5 | frozen/adopted Scene card |
| `time_label` | string | yes | yes | `null` | code from candidate | immutable | Section 5 | frozen/adopted Scene card |
| `parallel_group_id` | string | yes | yes | `null` | code from candidate | immutable | Section 5 | frozen/adopted Scene card |
| `scene_purpose` | string | yes | no | none | code from candidate | immutable | Section 4 | frozen/adopted Scene card |
| `required_beats` | array<string> | yes | no | none | code from candidate | immutable | Section 4 | frozen/adopted Scene card |
| `emotional_change_target` | string | yes | no | none | code from candidate | immutable | Section 4 | frozen/adopted Scene card |
| `relationship_change_targets` | array<Scene Relationship target> | yes | no | `[]` | code from candidate | immutable | Section 6 | frozen/adopted Scene card |
| `thread_actions` | array<Frozen Scene Thread action> | yes | no | `[]` | code | immutable | Section 17 | frozen/adopted Scene card |
| `character_knowledge_targets` | array<Frozen Character Knowledge target> | yes | no | `[]` | code | immutable | Section 18 | frozen/adopted Scene card |
| `reader_disclosures` | array<Frozen Reader disclosure> | yes | no | `[]` | code | immutable | Section 19 | frozen/adopted Scene card |
| `ending_criterion_targets` | array<Scene Ending target> | yes | no | `[]` | code from candidate | immutable | Section 10 | frozen/adopted Scene card |
| `canon_metadata_change_targets` | array<Canon-metadata change target> | yes | no | `[]` | code from candidate | immutable | Section 11 | frozen/adopted Scene card |
| `forbidden_disclosures` | array<Forbidden-disclosure record> | yes | no | `[]` | code | immutable | Section 20 | frozen/adopted Scene card |
| `allowed_update_targets` | array<Allowed-update-target union> | yes | no | `[]` | code | immutable | Sections 21–26 | frozen/adopted Scene card |
| `new_item_policy` | New-item policy | yes | no | none | code from candidate | immutable | Section 12 | frozen/adopted Scene card |
| `length_guidance` | Length-guidance object | yes | no | none | code | immutable | Section 27 | frozen/adopted Scene card |
| `chapter_completion_role` | enum `chapter_completion_role` | yes | no | none | code | immutable | exact Chapter Scene-function target | frozen/adopted Scene card |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | SC-CHK freeze time | frozen/adopted Scene card |

---

## 17. Frozen Scene Thread action

The frozen form adds code-owned current values.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `thread_id` | Thread ID | yes | no | none | code from candidate | adopted non-retired Thread |
| `operation` | enum `thread_action` | yes | no | none | code from candidate | operation matrix |
| `start_status` | enum `thread_status` | yes | no | none | code from HEAD | exact current status |
| `start_progress` | integer | yes | no | none | code from HEAD | exact current progress |
| `target_status` | enum `thread_status` | yes | no | none | code from candidate | exact operation result |
| `target_progress` | integer | yes | no | none | code from candidate | exact operation result |
| `purpose` | string | yes | no | none | code from candidate | candidate value |
| `required` | boolean | yes | no | `true` | code from candidate | candidate value |

---

## 18. Frozen Character Knowledge target

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `fact_id` | Knowledge item ID | yes | no | none | code from candidate | adopted non-retired Knowledge item |
| `character_id` | Character ID | yes | no | none | code from candidate | participant Character |
| `start_status` | enum `character_knowledge_status` | yes | no | none | code from HEAD | exact explicit or implicit status |
| `target_status` | enum `character_knowledge_status` | yes | no | none | code from candidate | valid transition |
| `purpose` | string | yes | no | none | code from candidate | candidate value |
| `required` | boolean | yes | no | `true` | code from candidate | candidate value |

---

## 19. Frozen Reader disclosure

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `fact_id` | Knowledge item ID | yes | no | none | code from candidate | adopted non-retired Knowledge item |
| `start_status` | enum `reader_knowledge_status` | yes | no | none | code from HEAD | exact explicit or implicit status |
| `target_status` | enum `reader_knowledge_status` | yes | no | none | code from candidate | valid forward transition |
| `purpose` | string | yes | no | none | code from candidate | candidate value |
| `required` | boolean | yes | no | `true` | code from candidate | candidate value |

---

## 20. Forbidden-disclosure record

This is a safe instruction. It never contains hidden truth.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `constraint_id` | string | yes | no | none | code | pattern `fd-[0-9]{4}`; unique within Scene card |
| `source_type` | enum | yes | no | none | code | `brief_avoid`, `knowledge_item`, `thread`, `ending_criterion`, or `editorial` |
| `source_id` | persistent ID | yes | yes | `null` | code | non-null for Knowledge item, Thread, or Ending criterion; null otherwise |
| `label` | string | yes | no | none | code from safe projection | NFC `1..500`; contains no author truth |
| `reason` | string | yes | no | none | code from safe projection | NFC `1..750`; operational writing constraint |
| `release_hint` | string | yes | yes | `null` | code from safe plan | null or NFC `1..500`; must not reveal the withheld content |

Examples of valid labels:

```text
主人公がまだ知らない事実
読者には今回まだ明かさない背景
この場面では解決しない主要スレッド
Briefで避けるよう指定された表現
```

Raw `author_truth`, Thread resolution conditions, hidden Ending wording, and secret prompt text are forbidden.

---

## 21. Allowed-update-target union

`allowed_update_targets` is a discriminated union using `target_kind`.

Permitted branches:

```text
existing_item
knowledge_state
thread_state
story_clock
```

Code derives every branch from the accepted Scene-card content and current HEAD. The LLM does not emit this array.

A Continuity candidate is rejected when it targets anything outside this union, except for same-candidate new-record initialization explicitly permitted by `new_item_policy`.

---

## 22. Existing-item allowed target

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `target_kind` | constant `existing_item` | yes | no | exact constant | code | exact |
| `target_type` | enum `existing_update_target_type` | yes | no | none | code | Continuity registry value |
| `target_id` | persistent ID | yes | no | none | code | adopted non-retired target |
| `field_rules` | array<Allowed field rule> | yes | no | none | code | `1..30`; unique field paths; sorted |

### 22.1 Allowed field rule

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `field_path` | JSON Pointer string | yes | no | none | code | exact path from Continuity field matrix |
| `allowed_operations` | array<enum `existing_update_operation`> | yes | no | none | code | nonempty; unique; canonical operation order |

### 22.2 Derivation

Code creates:

- one Character-state target for every `participant_id`, with the Character-state mutable paths;
- one Relationship-state target for every `relationship_change_target`, with Relationship-state mutable paths;
- one exact Canon/Knowledge metadata target for every `canon_metadata_change_target`.

An inactive participant's lifecycle reactivation target must be present before that participant can be used.

No other existing-item target is authorized.

---

## 23. Knowledge-state allowed target

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `target_kind` | constant `knowledge_state` | yes | no | exact constant | code | exact |
| `fact_id` | Knowledge item ID | yes | no | none | code | adopted non-retired fact |
| `audience_type` | enum `knowledge_audience_type` | yes | no | none | code | `character` or `reader` |
| `audience_id` | Character ID | yes | yes | none | code | Character ID iff character audience; null iff reader |
| `start_status` | audience-specific status | yes | no | none | code | exact HEAD explicit or implicit status |
| `allowed_after_statuses` | array<audience-specific status> | yes | no | none | code | exactly the Scene-card target status; one-element array |

Code creates one branch per Character Knowledge target and Reader disclosure.

A same-candidate Knowledge item may receive an initial Knowledge update only when:

```text
new_item_policy.allow_knowledge_items = true
total new-item count remains within max_items
the update begins at the implicit default
literal prose evidence supports the transition
```

---

## 24. Thread-state allowed target

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `target_kind` | constant `thread_state` | yes | no | exact constant | code | exact |
| `thread_id` | Thread ID | yes | no | none | code | adopted non-retired Thread |
| `start_status` | enum `thread_status` | yes | no | none | code | exact HEAD value |
| `start_progress` | integer | yes | no | none | code | exact HEAD value |
| `allowed_operations` | array<enum `thread_action`> | yes | no | none | code | one-element array equal to Scene-card operation |
| `target_status` | enum `thread_status` | yes | no | none | code | Scene-card target |
| `target_progress` | integer | yes | no | none | code | Scene-card target |

Code creates one branch per frozen Scene Thread action.

A new Supporting Thread is authorized through `new_item_policy` and its proposal initialization, not this branch.

---

## 25. Story-clock allowed target

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `target_kind` | constant `story_clock` | yes | no | exact constant | code | exact |
| `allowed_time_relations` | array<enum `time_relation`> | yes | no | none | code | one-element array equal to Scene-card relation |
| `target_time_label` | string | yes | yes | `null` | code | equals Scene-card `time_label` |
| `target_parallel_group_id` | string | yes | yes | `null` | code | equals Scene-card `parallel_group_id` |

Derivation:

- no Story-clock branch is emitted for `same_time`;
- exactly one branch is emitted for `later`, `next_day`, `after_interval`, or `parallel`.

A Continuity Time update must equal the branch target values.

---

## 26. Allowed-target canonical ordering

The union array is sorted by:

1. `target_kind` in this order:
   - `existing_item`;
   - `knowledge_state`;
   - `thread_state`;
   - `story_clock`;
2. branch-specific persistent target ID;
3. audience type and audience ID where applicable.

This ordering is part of canonical Scene-card serialization.

---

## 27. Length guidance

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `target_chars` | integer | yes | no | none | code from Effective config | equals `scene_target_chars` |
| `guide_min_chars` | integer | yes | no | none | code from Effective config | equals `scene_guide_min_chars` |
| `guide_max_chars` | integer | yes | no | none | code from Effective config | equals `scene_guide_max_chars` |
| `counting_rule` | constant `unicode_code_points_excluding_final_lf` | yes | no | exact constant | code | exact |
| `hard_limit` | constant boolean `false` | yes | no | `false` | code | exact false |

Length guidance is editorial. Prose outside the guide range is not structurally invalid solely because of length.

Whitespace-only prose remains a response-structure failure.

---

## 28. Frozen Scene-card safety properties

The frozen Scene card must not contain:

```text
Knowledge-item author_truth
Thread author_truth
Thread resolution_condition
Ending source_ending_text
raw Brief ending text unless safe and necessary
raw prompts
raw LLM responses
review issues
Evidence quotes
runtime counters
provider credentials
new persistent IDs
```

It may contain persistent IDs, safe labels, current statuses, planned target statuses, and code-derived update permissions.

The frozen Scene card is safe to provide to prose generation as part of the Writer View.

---

# Part III: Prose

## 29. Prose candidate

PROSE-01 returns narrative Markdown text, not JSON.

Canonical candidate path:

```text
runtime/candidates/scenes/v01/c001/s001/prose/prose.md
```

The candidate contains only the scene's narrative body.

### 29.1 Permitted Markdown

Permitted:

```text
ordinary prose paragraphs
Japanese dialogue punctuation
blank lines between paragraphs
a section-break line containing exactly ***
```

Forbidden:

```text
YAML front matter
Markdown headings
bullet or numbered lists
tables
block quotes
code fences
inline code
HTML
links
images
footnotes
scene metadata
character or record IDs
analysis, explanation, or review comments
```

A literal `***` section break must be on its own line and may not appear at the start or end of the scene.

### 29.2 Canonical prose bytes

Before hashing or evidence matching, code:

1. decodes UTF-8;
2. normalizes strings to NFC;
3. converts CRLF and CR to LF;
4. removes trailing horizontal whitespace on every line;
5. removes leading and trailing blank lines;
6. collapses runs of more than two blank lines to two blank lines;
7. appends exactly one final LF.

The canonical prose must contain at least one non-whitespace code point before the final LF.

The checkpoint and adopted prose files contain these canonical bytes.

### 29.3 Character count

```text
character_count =
  Unicode code-point count of canonical prose
  excluding the single final LF
```

Blank lines, punctuation, and section-break characters count. Bytes and grapheme clusters are not used.

---

## 30. Prose semantic contract

Prose generation receives only:

```text
frozen Scene card
Writer View
effective editorial profile
safe previous handoff
```

It does not receive Author View or hidden author truth.

The prose must:

- maintain the Scene-card POV;
- use only non-retired projected Characters and records;
- attempt every required beat;
- attempt required emotional, Relationship, Thread, Knowledge, and Ending targets;
- respect forbidden disclosures;
- respect the editorial profile;
- avoid unsupported immutable facts;
- avoid using persistent IDs in narrative text;
- remain compatible with the Scene-card time and Location;
- avoid creating persistent-worthy records outside `new_item_policy`;
- avoid treating a permitted new item as required.

A target marked `required=true` is assessed semantically. It does not permit unsupported continuity adoption.

### 30.1 Canonical-persistence rule

Narrative prose may contain:

- ephemeral sensory details;
- unnamed incidental people;
- non-reusable background texture.

A new identity, relationship, named place, named organization, durable item, system, culture, historical fact, Supporting Thread, or reusable canonical fact must be represented by an accepted Continuity proposal when it is to persist beyond this scene.

Prose itself remains immutable narrative evidence, but later Context Builders must not treat an unadopted incidental detail as a persistent Canon record or Story-state value.

---

## 31. PROSE-02 review focus

PROSE-02 uses the generic Review-result Schema.

At minimum, it assesses:

```text
POV consistency
Scene purpose
required beats
emotional change
Relationship targets
Thread targets
Character Knowledge targets
Reader disclosures
Ending targets
Location and time consistency
forbidden disclosures
immutable-fact consistency
speech anchors
new-item policy
editorial profile
prose-only output format
```

A semantic failure is a review issue, not a response-structure retry.

---

## 32. PROSE-REV

PROSE-REV receives:

```text
latest structurally valid prose
frozen Scene card
Writer View
all current review issues
```

It returns one complete replacement prose body.

Partial patches, edit instructions, diff syntax, explanations, and unchanged-prefix/suffix references are forbidden.

The revised prose is canonicalized and re-reviewed according to the Pipeline contract.

---

## 33. PROSE-CHK and frozen prose

PROSE-CHK is code-only.

It:

1. validates that a structurally valid prose candidate exists;
2. applies canonical prose normalization;
3. calculates the prose SHA-256 and character count;
4. writes checkpoint `prose.md`;
5. updates Checkpoint manifest to `PROSE_FROZEN`.

Once frozen:

- prose bytes never change during DELTA, COMMIT, resume, or publication;
- Evidence matching uses these exact canonical bytes;
- adopted prose is a byte-for-byte copy;
- a prose change requires returning to prose generation and invalidating the later checkpoint delta.

---

# Part IV: Continuity and adoption

## 34. Continuity-delta source of truth

This document intentionally does not repeat Continuity-delta child fields.

The sole normative contracts are:

- validated checkpoint candidate delta:
  [`evidence_and_updates.md`](../ledger/evidence_and_updates.md#4-validated-continuity-candidate-root)
- committed adopted delta:
  [`evidence_and_updates.md`](../ledger/evidence_and_updates.md#14-committed-continuity-delta-root)

Any summary elsewhere has no normative force.

---

## 35. Scene-card authorization of Continuity

A validated Continuity candidate must satisfy all of the following:

### 35.1 Existing-item updates

Every existing update matches one frozen `existing_item` allowed target:

```text
target_type
target_id
field_path
operation
```

The candidate `before` equals HEAD and `after` satisfies the Continuity field matrix.

### 35.2 Knowledge updates

Every update of an adopted fact matches one frozen `knowledge_state` target and one allowed after status.

A same-candidate new Knowledge-item update follows the special rule in Section 23.

### 35.3 Thread updates

Every adopted Thread update matches one frozen `thread_state` target, operation, and target pair.

The Delta never creates an update merely because the Scene card marked it required. Literal prose evidence is mandatory.

### 35.4 Time update

A non-null Time update requires one frozen `story_clock` target and exact target values.

A `same_time` Scene card normally produces `time_update=null`.

### 35.5 Ending evidence

Every Ending-evidence proposal:

- targets one frozen Scene Ending target;
- uses the same relation;
- contains literal prose evidence.

### 35.6 New records and Knowledge items

Across:

```text
new_item_proposals
knowledge_item_proposals
```

the total count does not exceed `new_item_policy.max_items`.

Every new Canon proposal type appears in `allowed_types`.

Knowledge-item proposals require `allow_knowledge_items=true`.

Every proposal scope is less than or equal to `max_scope`.

### 35.7 Unmet semantic target

When prose fails to support a required Scene-card target:

- Continuity must omit the unsupported update or Evidence;
- review/residual issues record the unmet target;
- code never fabricates the missing change;
- adoption may proceed only under the generic revision-exhaustion policy.

---

## 36. DELTA checkpoint behavior

After DELTA-CHK:

```text
scene-card.json:
  frozen immutable Scene card

prose.md:
  frozen immutable prose

continuity-delta.json:
  structurally valid candidate delta
```

Checkpoint manifest phase becomes:

```text
DELTA_ACCEPTED
```

The candidate delta references the exact frozen prose through Evidence quotes but contains no code-owned Evidence IDs, offsets, or hashes.

---

## 37. COMMIT-03 Scene artifact construction

COMMIT-03 writes staged:

```text
scene-card.json
prose.md
committed continuity-delta.json
scene-manifest.json
```

Rules:

- staged Scene-card bytes equal checkpoint Scene-card bytes;
- staged prose bytes equal checkpoint prose bytes;
- committed delta is generated by code from the validated candidate;
- all candidate local keys are resolved;
- all Evidence proposals become Evidence IDs;
- Scene manifest points only to final adopted `artifacts/scenes/...` paths;
- Scene manifest hashes staged final bytes;
- no staged or checkpoint path appears in an adopted manifest.

---

## 38. COMMIT-04 adoption

COMMIT-04 uses the transaction defined in `runtime_records.md`.

After successful adoption:

```text
artifacts/scenes/vNN/cNNN/sNNN/scene-card.json
artifacts/scenes/vNN/cNNN/sNNN/prose.md
artifacts/scenes/vNN/cNNN/sNNN/continuity-delta.json
artifacts/scenes/vNN/cNNN/sNNN/scene-manifest.json
```

exist and are reachable from the adopted Generation and Commit manifests.

The new Story clock contains:

```text
last_scene_id = adopted scene_id
current_volume_number = Scene-card volume_number
current_chapter_number = Scene-card chapter_number
current_scene_number = Scene-card scene_number
current_order = prior current_order + 1
```

---

## 39. Cross-artifact invariants

A valid adopted scene satisfies:

```text
Scene ID matches all paths and numeric fields
Scene-card source generation equals Commit before generation
Scene manifest source generation equals Scene-card source generation
Scene manifest adopted generation equals Commit after generation
checkpoint and adopted Scene-card SHA-256 are equal
checkpoint and adopted prose SHA-256 are equal
committed delta Scene ID equals Scene-card Scene ID
all committed Evidence quotes resolve in adopted prose
all committed delta targets were authorized by frozen Scene card
all committed delta changes appear in resulting Canon/State
all resulting Canon/State changes described by committed delta are exact
Scene-manifest Evidence IDs equal Evidence records created by the commit
Story-clock position matches Scene ID
adopted Scene manifest contains no checkpoint/staging path
```

---

## 40. Forbidden fields and deprecated forms

Forbidden in Scene-card content candidates:

```text
scene_id
volume_number
chapter_number
scene_number
source_generation_id
hash
timestamp
forbidden_disclosures
allowed_update_targets
length_guidance
chapter_completion_role
new persistent ID
Evidence quote
author truth
```

Forbidden in frozen/adopted Scene cards:

```text
raw author truth
raw Thread resolution condition
raw Ending source text
raw prompt
raw response
review issues
runtime retry counters
Evidence offsets or hashes
unresolved local key
```

Forbidden in prose:

```text
record IDs
front matter
headings
lists
tables
code
HTML
links
analysis
review comments
```

Deprecated Scene-card forms:

```text
relationship_change_target as one Relationship ID
thread action as free-form string
reader_disclosures as array<string>
allowed_update_targets as array<string>
new_item_policy as string
length_guidance as integer
chapter_completion_role = advance
```

Use the exact child objects and enums in this document.

---

## 41. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
SC-01 exact root Schema
LLM cannot emit code-owned Scene fields
Scene ID and path consistency
source-generation stale-check rejection
Chapter Scene-function preservation
POV and participant validation
Location and world-reference validation
time-relation matrix
Relationship target validation
Thread start-value code injection
Knowledge implicit-start code injection
Ending-target validation
Canon-metadata target validation
new-item policy conditional rules
max_new_items_per_scene enforcement
forbidden-disclosure safe projection
allowed-update-target deterministic derivation
allowed-target canonical ordering
frozen Scene-card exact root
prose-only Markdown restrictions
prose canonicalization
character-count calculation
whole-prose revision replacement
frozen-prose immutability
checkpoint/adopted Scene-card byte equality
checkpoint/adopted prose byte equality
candidate/committed delta Schema separation
unauthorized Continuity-target rejection
required target never fabricates unsupported update
new-item total count and scope enforcement
Ending-evidence Scene-card matching
time-update Scene-card matching
Scene-manifest adopted-path enforcement
Story-clock position update
cross-artifact hash and Evidence validation
unknown-field rejection
```
