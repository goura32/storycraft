# Ledger contracts: Canon records and enum registry

This document is the normative contract for adopted Canon identity records and adopted knowledge-item records.

- `canon/generations/<generation-id>/current-canon.json` stores fixed Canon records.
- `canon/generations/<generation-id>/knowledge-items.json` stores knowledge-item records.
- Mutable character, relationship, thread, knowledge-audience, time, and story-position values belong only to [`story_state.md`](story_state.md).
- Scene-derived creation and mutation proposals are governed only by [`evidence_and_updates.md`](evidence_and_updates.md).

Every saved object defined here uses `additionalProperties: false`. Persistent IDs are allocated by code only at adoption. An LLM may emit a `local_key` in a candidate artifact, but it must never emit a persistent ID for a new record.

---

## 1. Root file contracts

### 1.1 `current-canon.json`

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `records` | array of Character, Relationship, World entity, Temporal rule, Thread, or Ending criterion records | yes | no | `[]` | code | generation replacement only | replace during atomic generation commit | all scene-derived additions or mutable metadata changes require adopted evidence | IDs are globally unique; records are sorted by `id`; Knowledge item records are forbidden | `current-canon.json` |

### 1.2 `knowledge-items.json`

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `items` | array of Knowledge item records | yes | no | `[]` | code | generation replacement only | replace during atomic generation commit | prose-origin additions and mutable metadata changes require adopted evidence | IDs are unique and sorted by `id`; non-Knowledge records are forbidden | `knowledge-items.json` |

### 1.3 Canonical ordering

For deterministic serialization and hashing:

- `records` and `items` are sorted by persistent `id` in ascending Unicode code-point order.
- Set-like string arrays such as `aliases`, `values`, `immutable_facts`, `sensory_anchors`, and `related_ids` contain unique NFC strings and are sorted in ascending Unicode code-point order.
- JSON object keys are serialized by the canonical JSON rule defined by the runtime contract; array order is not changed unless this document explicitly declares the array set-like.

---

## 2. Persistent ID registry

All numeric suffixes are six decimal digits. IDs are never reused, including after retirement.

| record | pattern | example | allocator counter |
|---|---|---|---|
| Character | `char-[0-9]{6}` | `char-000001` | `next_character_id` |
| Relationship | `rel-[0-9]{6}` | `rel-000001` | `next_relationship_id` |
| Location world entity | `loc-[0-9]{6}` | `loc-000001` | `next_location_id` |
| Organization world entity | `org-[0-9]{6}` | `org-000001` | `next_organization_id` |
| Item world entity | `item-[0-9]{6}` | `item-000001` | `next_item_id` |
| System world entity | `sys-[0-9]{6}` | `sys-000001` | `next_system_id` |
| Culture world entity | `culture-[0-9]{6}` | `culture-000001` | `next_culture_id` |
| History world entity | `history-[0-9]{6}` | `history-000001` | `next_history_id` |
| Temporal rule | `rule-[0-9]{6}` | `rule-000001` | `next_rule_id` |
| Thread | `thread-[0-9]{6}` | `thread-000001` | `next_thread_id` |
| Ending criterion | `ending-[0-9]{6}` | `ending-000001` | `next_ending_id` |
| Knowledge item | `fact-[0-9]{6}` | `fact-000001` | `next_fact_id` |

A World entity record's `id` prefix must match its `kind` according to the table above.

---

## 3. Normative enum registry

This registry is the single source of truth for the listed domain enums. Downstream contracts must link here rather than redefine a different value set.

| enum | permitted values | notes |
|---|---|---|
| `canon_record_type` | `character`, `relationship`, `world_entity`, `temporal_rule`, `thread`, `ending_criterion` | Persisted in `current-canon.json` |
| `knowledge_record_type` | `knowledge_item` | Persisted in `knowledge-items.json` |
| `record_origin` | `initial_design`, `prose` | `initial_design` records have `created_scene_id=null`; `prose` records require an adopted `created_scene_id` |
| `new_item_proposal_type` | `character`, `relationship`, `location`, `organization`, `item`, `system`, `culture`, `history`, `supporting_thread` | Candidate-only discriminator; it is not the persisted `record_type` field |
| `knowledge_subject_type` | `character`, `relationship`, `world_entity`, `temporal_rule`, `thread`, `ending_criterion` | Determines the permitted prefix of `subject_id` |
| `character_role` | `protagonist`, `love_interest`, `antagonist`, `ally`, `family`, `mentor`, `rival`, `supporting` | A character has exactly one structural role |
| `relationship_type` | `central`, `romantic`, `family`, `friendship`, `alliance`, `rivalry`, `authority`, `conflict` | Fixed classification, not current relationship state |
| `structural_role` | `primary`, `secondary`, `supporting` | Narrative importance of a relationship |
| `trust` | `none`, `low`, `medium`, `high`, `absolute` | Used only by Relationship state |
| `world_entity_kind` | `location`, `organization`, `item`, `system`, `culture`, `history` | Determines World entity ID prefix |
| `temporal_rule_kind` | `deadline`, `travel_duration`, `recovery_rule`, `cycle`, `progression_rule`, `age_rule` | Fixed temporal constraint category |
| `thread_type` | `major`, `supporting` | Major threads are initial-design records and completion-gate candidates |
| `thread_status` | `open`, `in_progress`, `resolved`, `retired` | Stored only in Story state |
| `thread_action` | `introduce`, `advance`, `resolve`, `retire` | Continuity-delta operation for a thread |
| `character_knowledge_status` | `unknown`, `suspects`, `misunderstands`, `partially_knows`, `knows` | Used when `audience_type=character` |
| `reader_knowledge_status` | `withheld`, `hinted`, `partially_revealed`, `revealed` | Used when `audience_type=reader` |
| `knowledge_audience_type` | `character`, `reader` | Stored only in Story state |
| `time_relation` | `same_time`, `later`, `next_day`, `after_interval`, `parallel` | Scene and time-update contract |
| `chapter_completion_role` | `opening`, `development`, `turn`, `climax`, `resolution` | Scene-card contract |
| `scope` | `scene`, `chapter`, `volume`, `series` | Relevance/lifetime boundary, not storage location |
| `record_lifecycle` | `active`, `inactive`, `retired` | Generic record lifecycle; `resolved` is forbidden here |
| `volume_disposition` | `resolve`, `carry_over`, `retire` | Volume-handoff decision for a thread |

### 3.1 Proposal-to-persisted-record mapping

| `new_item_proposal_type` | adopted record | adopted fixed values |
|---|---|---|
| `character` | Character record | `record_type=character` |
| `relationship` | Relationship record | `record_type=relationship` |
| `location` | World entity record | `record_type=world_entity`, `kind=location` |
| `organization` | World entity record | `record_type=world_entity`, `kind=organization` |
| `item` | World entity record | `record_type=world_entity`, `kind=item` |
| `system` | World entity record | `record_type=world_entity`, `kind=system` |
| `culture` | World entity record | `record_type=world_entity`, `kind=culture` |
| `history` | World entity record | `record_type=world_entity`, `kind=history` |
| `supporting_thread` | Thread record | `record_type=thread`, `thread_type=supporting`, `required=false` |

Normal scene generation cannot create a Temporal rule, Major thread, Ending criterion, or Knowledge item through `new_item_proposals`. Knowledge items use the dedicated knowledge-item proposal contract.

---

## 4. Shared validation rules

- All strings are stored as valid UTF-8, normalized to NFC.
- A required non-null string must contain at least one non-whitespace code point after trimming leading and trailing whitespace.
- Persistent references resolve against the same adopted generation, except `created_scene_id`, which resolves to an adopted scene artifact.
- `record_origin=initial_design` requires `created_scene_id=null`.
- `record_origin=prose` requires a non-null adopted `created_scene_id` and adopted evidence for creation.
- Scope changes may only widen: `scene → chapter → volume → series`. Narrowing is forbidden.
- Lifecycle transitions are limited to `active → inactive`, `inactive → active`, `active → retired`, or `inactive → retired`. `retired` is terminal.
- An immutable field cannot be changed by normal generation, review, revision, continuity merge, resume, or publication processing. Correcting an immutable-field defect requires an explicit migration outside the normal story pipeline.
- Every prose-derived creation or mutable metadata change is proposed by the LLM, mechanically validated, supported by adopted prose evidence, and applied by code during commit.

---

## 5. Character record

A Character record stores stable identity and characterization anchors. Current location, condition, emotion, goal, and pressure belong to Story state.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `id` | Character ID | yes | no | none | code | immutable | none | none | pattern `char-[0-9]{6}`; globally unique | `current-canon.json` |
| `record_type` | constant `character` | yes | no | none | code | immutable | none | none | exact constant | `current-canon.json` |
| `record_origin` | enum `record_origin` | yes | no | none | code from adopted candidate | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `name` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty; unique name is not required | `current-canon.json` |
| `aliases` | array<string> | yes | no | `[]` | LLM candidate / code merge | mutable | `append`, `remove` | adopted evidence for scene-derived change | unique NFC strings; canonical set ordering | `current-canon.json` |
| `role` | enum `character_role` | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `core_trait` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty | `current-canon.json` |
| `values` | array<string> | yes | no | `[]` | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | unique NFC strings; canonical set ordering | `current-canon.json` |
| `background` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty | `current-canon.json` |
| `immutable_facts` | array<string> | yes | no | `[]` | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | unique NFC strings; canonical set ordering | `current-canon.json` |
| `appearance_anchor` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty | `current-canon.json` |
| `speech_anchor` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty | `current-canon.json` |
| `scope` | enum `scope` | yes | no | none | code from adopted candidate | mutable | `transition` | adopted evidence for scene-derived widening | enum registry; widening only | `current-canon.json` |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | `active` | code | mutable | `transition` | adopted evidence for scene-derived transition | lifecycle transition matrix | `current-canon.json` |
| `created_scene_id` | Scene ID | yes | yes | `null` | code | immutable | none | creation evidence when non-null | null iff `record_origin=initial_design`; otherwise pattern `v[0-9]{2}-c[0-9]{3}-s[0-9]{3}` and adopted scene | `current-canon.json` |

Forbidden Character-record fields include `location_id`, `physical_condition`, `emotional_state`, `current_goal`, and `current_pressure`; they belong to Character state.

---

## 6. Relationship record

A Relationship record stores stable participants and narrative classification. Current public relation, directional trust, perceptions, emotions, intentions, and shared state belong to Relationship state.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `id` | Relationship ID | yes | no | none | code | immutable | none | none | pattern `rel-[0-9]{6}`; globally unique | `current-canon.json` |
| `record_type` | constant `relationship` | yes | no | none | code | immutable | none | none | exact constant | `current-canon.json` |
| `record_origin` | enum `record_origin` | yes | no | none | code from adopted candidate | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `participant_a_id` | Character ID | yes | no | none | LLM candidate, resolved by code | immutable | none | creation evidence when `prose` | adopted active/inactive Character; differs from `participant_b_id` | `current-canon.json` |
| `participant_b_id` | Character ID | yes | no | none | LLM candidate, resolved by code | immutable | none | creation evidence when `prose` | adopted active/inactive Character; differs from `participant_a_id` | `current-canon.json` |
| `relationship_type` | enum `relationship_type` | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `relationship_origin` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty; describes the relationship's backstory, not record provenance | `current-canon.json` |
| `structural_role` | enum `structural_role` | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `scope` | enum `scope` | yes | no | none | code from adopted candidate | mutable | `transition` | adopted evidence for scene-derived widening | enum registry; widening only | `current-canon.json` |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | `active` | code | mutable | `transition` | adopted evidence for scene-derived transition | lifecycle transition matrix | `current-canon.json` |
| `created_scene_id` | Scene ID | yes | yes | `null` | code | immutable | none | creation evidence when non-null | null iff `record_origin=initial_design`; otherwise adopted scene ID | `current-canon.json` |

Forbidden Relationship-record fields include `public_relation`, `a_to_b`, `b_to_a`, and `shared_state`; they belong to Relationship state.

---

## 7. World entity record

A World entity record stores stable identity, description, and rules for a location, organization, item, system, culture, or historical element.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `id` | kind-specific World entity ID | yes | no | none | code | immutable | none | none | prefix matches `kind`; globally unique | `current-canon.json` |
| `record_type` | constant `world_entity` | yes | no | none | code | immutable | none | none | exact constant | `current-canon.json` |
| `record_origin` | enum `record_origin` | yes | no | none | code from adopted candidate | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `kind` | enum `world_entity_kind` | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | enum registry; matches ID prefix | `current-canon.json` |
| `name` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty | `current-canon.json` |
| `description` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty | `current-canon.json` |
| `immutable_rules` | array<string> | yes | no | `[]` | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | unique NFC strings; canonical set ordering | `current-canon.json` |
| `sensory_anchors` | array<string> | yes | no | `[]` | LLM candidate / code merge | mutable | `append`, `remove` | adopted evidence for scene-derived change | unique NFC strings; canonical set ordering | `current-canon.json` |
| `scope` | enum `scope` | yes | no | none | code from adopted candidate | mutable | `transition` | adopted evidence for scene-derived widening | enum registry; widening only | `current-canon.json` |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | `active` | code | mutable | `transition` | adopted evidence for scene-derived transition | lifecycle transition matrix | `current-canon.json` |
| `created_scene_id` | Scene ID | yes | yes | `null` | code | immutable | none | creation evidence when non-null | null iff `record_origin=initial_design`; otherwise adopted scene ID | `current-canon.json` |

Temporary occupancy, possession, damage, availability, or operational condition belongs to Story state or a Knowledge item, not to this record.

---

## 8. Temporal rule record

A Temporal rule record stores a stable timing constraint. The current clock and scene order belong to Story state.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `id` | Temporal rule ID | yes | no | none | code | immutable | none | none | pattern `rule-[0-9]{6}`; globally unique | `current-canon.json` |
| `record_type` | constant `temporal_rule` | yes | no | none | code | immutable | none | none | exact constant | `current-canon.json` |
| `record_origin` | enum `record_origin` | yes | no | none | code from adopted candidate | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `kind` | enum `temporal_rule_kind` | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `description` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty | `current-canon.json` |
| `fixed_rule` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty; declarative constraint | `current-canon.json` |
| `related_ids` | array of Canon record IDs | yes | no | `[]` | LLM candidate / code merge | mutable | `append`, `remove` | adopted evidence for scene-derived change | unique adopted non-Knowledge IDs; canonical set ordering | `current-canon.json` |
| `scope` | enum `scope` | yes | no | none | code from adopted candidate | mutable | `transition` | adopted evidence for scene-derived widening | enum registry; widening only | `current-canon.json` |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | `active` | code | mutable | `transition` | adopted evidence for scene-derived transition | lifecycle transition matrix | `current-canon.json` |
| `created_scene_id` | Scene ID | yes | yes | `null` | code | immutable | none | creation evidence when non-null | null iff `record_origin=initial_design`; otherwise adopted scene ID | `current-canon.json` |

---

## 9. Thread record

A Thread record stores the stable dramatic question and author-only resolution design. Current status, progress, and volume disposition belong to Thread state.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `id` | Thread ID | yes | no | none | code | immutable | none | none | pattern `thread-[0-9]{6}`; globally unique | `current-canon.json` |
| `record_type` | constant `thread` | yes | no | none | code | immutable | none | none | exact constant | `current-canon.json` |
| `record_origin` | enum `record_origin` | yes | no | none | code from adopted candidate | immutable | none | creation evidence when `prose` | enum registry | `current-canon.json` |
| `thread_type` | enum `thread_type` | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | `major` requires `record_origin=initial_design`; `supporting` permits either origin | `current-canon.json` |
| `description` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty | `current-canon.json` |
| `author_truth` | string | yes | yes | `null` | LLM candidate, adopted by code | immutable | none | never derived from prose | non-null NFC string iff `record_origin=initial_design`; null iff `record_origin=prose`; never projected to Writer View | `current-canon.json` |
| `resolution_condition` | string | yes | yes | `null` | LLM candidate, adopted by code | immutable | none | never derived from prose | non-null NFC string for `major`; nullable for `supporting` | `current-canon.json` |
| `presentation_rule` | string | yes | yes | `null` | LLM candidate, adopted by code | immutable | none | never derived from prose | non-null NFC string for `major`; nullable for `supporting` | `current-canon.json` |
| `required` | boolean | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | `true` iff `thread_type=major`; `false` iff `thread_type=supporting` | `current-canon.json` |
| `scope` | enum `scope` | yes | no | none | code from adopted candidate | mutable | `transition` | adopted evidence for scene-derived widening | `major` requires `series`; `supporting` may widen normally | `current-canon.json` |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | `active` | code | mutable | `transition` | adopted evidence for scene-derived transition | lifecycle transition matrix; independent of Thread state `resolved` | `current-canon.json` |
| `created_scene_id` | Scene ID | yes | yes | `null` | code | immutable | none | creation evidence when non-null | null iff `record_origin=initial_design`; otherwise adopted scene ID | `current-canon.json` |

A prose-created supporting thread must have `record_origin=prose`, `thread_type=supporting`, `required=false`, `author_truth=null`, and a non-null `created_scene_id`.

Forbidden Thread-record fields include `thread_status`, `progress`, and `volume_disposition`; they belong to Thread state.

---

## 10. Ending criterion record

An Ending criterion is an initial-design completion condition. Normal scene generation cannot create or rewrite it.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `id` | Ending criterion ID | yes | no | none | code | immutable | none | none | pattern `ending-[0-9]{6}`; globally unique | `current-canon.json` |
| `record_type` | constant `ending_criterion` | yes | no | none | code | immutable | none | none | exact constant | `current-canon.json` |
| `record_origin` | constant `initial_design` | yes | no | none | code | immutable | none | none | exact constant | `current-canon.json` |
| `description` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | none | NFC nonempty; mechanically assessable through evidence | `current-canon.json` |
| `required` | boolean | yes | no | `true` | LLM candidate, adopted by code | immutable | none | none | exact boolean | `current-canon.json` |
| `source_ending_text` | string | yes | no | none | code from accepted Brief / LLM bundle | immutable | none | none | NFC nonempty; traceable to accepted Brief ending | `current-canon.json` |
| `scope` | constant `series` | yes | no | `series` | code | immutable | none | none | exact constant | `current-canon.json` |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | `active` | code | mutable | `transition` | adopted evidence or explicit design migration | lifecycle transition matrix | `current-canon.json` |
| `created_scene_id` | null | yes | yes | `null` | code | immutable | none | none | must be null | `current-canon.json` |

Satisfaction or contradiction evidence is stored in the Evidence index and assessed by Completion audit. It is not stored as a mutable field on the Ending criterion.

---

## 11. Knowledge item record

A Knowledge item defines one canonical fact that may be known differently by characters and readers. Audience-specific knowledge status belongs to Knowledge state.

| field | type | required | nullable | default | creator | mutability | allowed operation | evidence requirement | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|---|---|
| `id` | Knowledge item ID | yes | no | none | code | immutable | none | none | pattern `fact-[0-9]{6}`; unique | `knowledge-items.json` |
| `record_type` | constant `knowledge_item` | yes | no | none | code | immutable | none | none | exact constant | `knowledge-items.json` |
| `record_origin` | enum `record_origin` | yes | no | none | code from adopted candidate | immutable | none | creation evidence when `prose` | enum registry | `knowledge-items.json` |
| `subject_type` | enum `knowledge_subject_type` | yes | no | none | LLM candidate, resolved by code | immutable | none | creation evidence when `prose` | enum registry; matches the adopted subject record's type | `knowledge-items.json` |
| `subject_id` | Canon record ID | yes | no | none | LLM candidate, resolved by code | immutable | none | creation evidence when `prose` | adopted record; prefix/type agrees with `subject_type` | `knowledge-items.json` |
| `canonical_fact` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty; one independently trackable fact | `knowledge-items.json` |
| `writer_visible_label` | string | yes | no | none | LLM candidate, adopted by code | immutable | none | creation evidence when `prose` | NFC nonempty; may be projected without revealing `author_truth` | `knowledge-items.json` |
| `author_truth` | string | yes | yes | `null` | LLM candidate, adopted by code | immutable | none | never invented from prose | non-null NFC string iff `record_origin=initial_design`; null iff `record_origin=prose`; never projected to Writer View | `knowledge-items.json` |
| `scope` | enum `scope` | yes | no | none | code from adopted candidate | mutable | `transition` | adopted evidence for scene-derived widening | enum registry; widening only | `knowledge-items.json` |
| `record_lifecycle` | enum `record_lifecycle` | yes | no | `active` | code | mutable | `transition` | adopted evidence for scene-derived transition | lifecycle transition matrix | `knowledge-items.json` |
| `created_scene_id` | Scene ID | yes | yes | `null` | code | immutable | none | creation evidence when non-null | null iff `record_origin=initial_design`; otherwise adopted scene ID | `knowledge-items.json` |

The tuple `(subject_type, subject_id, canonical_fact)` must not duplicate another active or inactive Knowledge item after NFC normalization. A retired duplicate does not permit ID reuse; a genuinely new formulation receives a new ID only when it represents a distinct fact.

---

## 12. Canon–State boundary

The following fields are explicitly forbidden from `current-canon.json` and `knowledge-items.json` because their source of truth is Story state.

| state area | fields stored only in Story state |
|---|---|
| Character | `location_id`, `physical_condition`, `emotional_state`, `current_goal`, `current_pressure` |
| Relationship | `public_relation`, `a_to_b.trust`, `a_to_b.perception`, `a_to_b.emotional_stance`, `a_to_b.current_intention`, `b_to_a.trust`, `b_to_a.perception`, `b_to_a.emotional_stance`, `b_to_a.current_intention`, `shared_state` |
| Thread | `thread_status`, `progress`, `volume_disposition` |
| Knowledge audience | `fact_id`, `audience_type`, `audience_id`, `status` rows |
| Story clock / position | `current_order`, `time_label`, `parallel_group_id`, `last_scene_id`, `current_volume_number`, `current_chapter_number`, `current_scene_number` |

No field may be duplicated across these sources of truth. A context snapshot may copy projected values, but it is never an adopted source of truth.

---

## 13. Adoption and mutation rules

### 13.1 Genesis adoption

At `INIT-ID`, code:

1. validates all initial-design candidate records and cross-references;
2. allocates persistent IDs and resolves every `local_key`;
3. writes Character, Relationship, World entity, Temporal rule, Thread, and Ending criterion records to `current-canon.json`;
4. writes initial-design Knowledge item records to `knowledge-items.json`;
5. initializes corresponding Character, Relationship, Thread, and Knowledge state rows in `story-state.json`;
6. rejects the entire Genesis adoption if any mapped local key lacks an adopted record or required initial State row.

### 13.2 Scene-derived creation

At scene commit, code may adopt only the proposal types permitted by the accepted Scene card's `new_item_policy` and the continuity-delta contract. It allocates IDs after mechanical validation and records the local-key mapping in the Commit manifest.

### 13.3 Mutable metadata update

Only fields marked mutable in this document may change. Code must verify:

```text
known target
allowed operation
before value equals HEAD snapshot
proposed after value satisfies this contract
literal evidence exists in adopted prose when required
Scene card allowed_update_targets permits the target and field
```

All other fields are immutable.

---

## 14. Cross-record integrity rules

- Every Relationship participant resolves to a non-retired Character; participants are distinct.
- Every World entity ID prefix matches `kind`.
- Every Temporal rule `related_id` resolves to a non-retired Canon record.
- Every Major thread is `record_origin=initial_design`, `required=true`, `scope=series`, and has non-null `author_truth`, `resolution_condition`, and `presentation_rule`.
- Every prose-created Thread is supporting and optional.
- Every Ending criterion is initial-design, series-scoped, and has `created_scene_id=null`.
- Every Knowledge item subject resolves to a non-retired Canon record of the declared `subject_type`.
- Retiring a referenced record is rejected while an active record or State row requires it, unless the same atomic commit retires or redirects every dependent reference.
- `current-canon.json` must not contain Knowledge item records.
- `knowledge-items.json` must not contain Canon records or audience status rows.

---

## 15. Downstream normative references

The following later contracts must use this document without redefining incompatible enums or record shapes:

- [`story_state.md`](story_state.md): mutable current values and status matrices.
- [`evidence_and_updates.md`](evidence_and_updates.md): creation proposal branches and mutable update operations.
- `../data/brief_and_initial.md`: candidate fields before persistent-ID allocation.
- `../data/scene_artifacts.md`: `new_item_policy`, allowed update targets, and continuity-delta references.
- `runtime_records.md`: ID counters and local-key mappings.

When a downstream document conflicts with this file, this file is authoritative for Canon record identity, fixed fields, ID prefixes, record provenance, and domain enum values.
