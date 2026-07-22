# Data contracts: Brief and initial design

This document is the normative data contract for:

- keyword-source input;
- the normalized adopted Brief;
- INPUT-02 Brief generation;
- INIT-01 Concept generation;
- INIT-02 Character and Relationship design;
- INIT-03 World and Temporal design;
- INIT-04 Arc, Thread, Ending, and initial Knowledge design;
- INIT-05 integrated Initial-design bundle;
- INIT-REV revised Initial-design bundle;
- INIT-ID transformation into adopted Genesis artifacts.

Stable Canon records and enums are defined by [`../ledger/canon_records.md`](../ledger/canon_records.md). Mutable Genesis values are defined by [`../ledger/story_state.md`](../ledger/story_state.md). Runtime candidate and Genesis manifest contracts are defined by [`../ledger/runtime_records.md`](../ledger/runtime_records.md). Effective profile and volume constraints are defined by [`../../configuration_contracts.md`](../../configuration_contracts.md).

Every saved object and every structured LLM response defined here uses `additionalProperties: false`.

---

## 1. Authority and ownership

| concern | authority |
|---|---|
| User's story request | normalized adopted Brief |
| Provider/profile/runtime settings | Effective config |
| Pre-ID Initial-design candidate | `runtime/candidates/initial-design/...` |
| Adopted author-facing concept and arcs | `canon/initial-design.json` |
| Adopted fixed story records | Genesis `current-canon.json` |
| Adopted Knowledge-item definitions | Genesis `knowledge-items.json` |
| Adopted mutable initial values | Genesis `story-state.json` |
| Local-key to persistent-ID allocation | Genesis Commit manifest |
| Review issues | Review artifact and residual-issue audit |

The LLM does not create:

```text
persistent IDs
Commit IDs
Generation IDs
timestamps
hashes
profile IDs
record_origin
record_lifecycle
created_scene_id
Story-clock order or scene position
```

Code adds or derives those fields during normalization and INIT-ID.

---

## 2. Shared initial-design rules

### 2.1 Initial local key

Every initial-design candidate record that needs cross-reference uses one `local_key`.

| property | contract |
|---|---|
| type | string |
| pattern | `[a-z][a-z0-9_-]{0,63}` |
| creator | LLM |
| scope | one integrated Initial-design bundle |
| uniqueness | globally unique across Character, Relationship, World entity, Temporal rule, Thread, Ending criterion, and Knowledge-item candidates |
| persistence | candidate-only; converted to persistent ID at INIT-ID |
| forbidden | any persistent-ID pattern, whitespace, `/`, `.`, or uppercase character |

Recommended prefixes such as `char_`, `rel_`, `loc_`, `thread_`, and `fact_` improve readability but are not required.

### 2.2 Candidate reference

A candidate reference is an Initial local key of the required candidate type.

Code validates references only after all relevant INIT outputs are available. INIT-02 may therefore refer to a Location local key that is generated later by INIT-03.

### 2.3 String normalization

Unless a field defines a stricter limit:

- strings are valid UTF-8;
- normalized to NFC;
- leading and trailing whitespace is removed;
- empty strings are forbidden;
- embedded NUL is forbidden.

### 2.4 Ordered arrays

The following arrays preserve semantic priority order:

```text
key_people
themes
tone_constraints
turning_points
immutable_rules
sensory_anchors
```

Set-like arrays reject duplicates after NFC normalization.

Candidate record arrays are normalized by code to ascending `local_key` order before hashing.

### 2.5 No hidden invention

Initial design may define author-only truth because it is an authoring stage. It must still remain compatible with the adopted Brief.

The Initial-design stages must not:

- contradict an explicit Brief statement;
- change the configured number of volumes;
- replace configured profile IDs;
- introduce a different protagonist;
- turn an `avoid` item into a required story event;
- silently weaken the requested ending;
- include future prose or publication metadata.

---

## 3. Keyword-source input

When the user starts from keywords, code saves the normalized source at:

```text
input/keywords.json
```

### 3.1 Keyword-source root

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `keywords` | array<string> | yes | no | none | user | immutable | `1..50`; each `1..100` code points; unique after NFC and case-sensitive comparison | `input/keywords.json` |
| `notes` | string | yes | yes | `null` | user | immutable | null or `1..5000` code points | `input/keywords.json` |
| `title_hint` | string | yes | yes | `null` | user | immutable | null or `1..100` code points | `input/keywords.json` |
| `genre_hint` | string | yes | yes | `null` | user | immutable | null or `1..100` code points | `input/keywords.json` |
| `ending_hint` | string | yes | yes | `null` | user | immutable | null or `1..1000` code points | `input/keywords.json` |
| `avoid` | array<string> | yes | no | `[]` | user | immutable | `0..20`; each `1..300` code points; unique | `input/keywords.json` |
| `volumes_hint` | integer | yes | yes | `null` | user | immutable | null or `4..10`; must fit Publishing profile | `input/keywords.json` |

The Keyword-source SHA-256 is calculated from the complete canonical JSON bytes of this object.

---

## 4. Brief content candidate

A Brief content candidate is:

- directly supplied by the user in Brief mode; or
- generated by INPUT-02 from the Keyword source and Effective config.

It excludes code-owned metadata and profile IDs.

### 4.1 Protagonist brief

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `name` | string | yes | no | none | user or LLM | candidate-only | `1..100` code points |
| `present_position` | string | yes | no | none | user or LLM | candidate-only | `1..500` code points |
| `core_trait` | string | yes | no | none | user or LLM | candidate-only | `1..300` code points |
| `current_pressure` | string | yes | no | none | user or LLM | candidate-only | `1..500` code points |
| `initial_wish` | string | yes | no | none | user or LLM | candidate-only | `1..500` code points |

### 4.2 Key-person brief

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `name` | string | yes | no | none | user or LLM | candidate-only | `1..100` code points |
| `present_position` | string | yes | no | none | user or LLM | candidate-only | `1..500` code points |
| `initial_relation_to_protagonist` | string | yes | no | none | user or LLM | candidate-only | `1..500` code points |

### 4.3 Brief content candidate root

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `title` | string | yes | no | none | user or LLM | candidate-only | `1..100` code points |
| `genre` | string | yes | no | none | user or LLM | candidate-only | `1..100` code points |
| `target_reader` | string | yes | no | none | user or LLM | candidate-only | `1..200` code points |
| `protagonist` | Protagonist brief | yes | no | none | user or LLM | candidate-only | complete Protagonist brief |
| `key_people` | array<Key-person brief> | yes | no | none | user or LLM | candidate-only | `1..12`; normalized names unique; no name equals protagonist name |
| `want` | string | yes | no | none | user or LLM | candidate-only | `1..1000` code points |
| `avoid` | array<string> | yes | no | `[]` | user or LLM | candidate-only | `0..20`; each `1..300` code points; unique |
| `ending` | string | yes | no | none | user or LLM | candidate-only | `1..2000` code points |
| `volumes` | integer | yes | no | none | user or LLM | candidate-only | `4..10` and within Publishing-profile range |

### 4.4 INPUT-02 constraints

INPUT-02 receives:

```text
Keyword-source input
editorial_profile
publishing_profile
```

It returns exactly one Brief content candidate.

Code additionally validates:

- `volumes` equals `volumes_hint` when that hint is non-null;
- title and genre honor non-null hints;
- ending honors non-null ending hint;
- every Keyword-source `avoid` item appears in candidate `avoid`;
- generated profile IDs are not accepted because INPUT-02 does not output them;
- the candidate contains no metadata, hashes, timestamps, or persistent IDs.

---

## 5. Adopted `input/brief.json`

INPUT-03 writes the normalized adopted Brief.

### 5.1 Brief root

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `brief_version` | constant string `1.0` | yes | no | `1.0` | code | immutable | exact constant | `input/brief.json` |
| `title` | string | yes | no | none | code from accepted content | immutable | Brief content contract | `input/brief.json` |
| `genre` | string | yes | no | none | code from accepted content | immutable | Brief content contract | `input/brief.json` |
| `target_reader` | string | yes | no | none | code from accepted content | immutable | Brief content contract | `input/brief.json` |
| `protagonist` | Protagonist brief | yes | no | none | code from accepted content | immutable | Brief content contract | `input/brief.json` |
| `key_people` | array<Key-person brief> | yes | no | none | code from accepted content | immutable | Brief content contract | `input/brief.json` |
| `want` | string | yes | no | none | code from accepted content | immutable | Brief content contract | `input/brief.json` |
| `avoid` | array<string> | yes | no | `[]` | code from accepted content | immutable | Brief content contract | `input/brief.json` |
| `ending` | string | yes | no | none | code from accepted content | immutable | Brief content contract | `input/brief.json` |
| `volumes` | integer | yes | no | none | code from accepted content | immutable | `4..10`; profile-compatible | `input/brief.json` |
| `editorial_profile_id` | string | yes | no | none | code from Effective config | immutable | equals Effective config | `input/brief.json` |
| `publishing_profile_id` | string | yes | no | none | code from Effective config | immutable | equals Effective config | `input/brief.json` |
| `source_type` | enum `input_mode` | yes | no | none | code | immutable | `brief` or `keywords` | `input/brief.json` |
| `source_hash` | SHA-256 | yes | no | none | code | immutable | Section 5.2 | `input/brief.json` |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | valid UTC timestamp | `input/brief.json` |

### 5.2 Source-hash rule

When `source_type=keywords`:

```text
source_hash =
  SHA-256 of canonical input/keywords.json bytes
```

When `source_type=brief`:

```text
source_hash =
  SHA-256 of the canonical Brief content candidate
```

The Brief content projection contains exactly:

```text
title
genre
target_reader
protagonist
key_people
want
avoid
ending
volumes
```

It excludes all code-owned metadata and profile IDs. The projection is reproducible from the adopted Brief.

### 5.3 Adopted-Brief hash

References to the adopted Brief from Run state, candidate input snapshots, and `initial-design.json` use the SHA-256 of the complete canonical `input/brief.json`, not `source_hash`.

---

## 6. INIT-01 Concept candidate

INIT-01 returns exactly this root object.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `core_concept` | string | yes | no | none | LLM | candidate-only | `1..1000` code points; concise causal story premise |
| `genre_promise` | string | yes | no | none | LLM | candidate-only | `1..1000`; compatible with Brief genre |
| `reader_experience` | string | yes | no | none | LLM | candidate-only | `1..1000`; compatible with target reader and profiles |
| `themes` | array<string> | yes | no | none | LLM | candidate-only | `1..10`; each `1..200`; unique |
| `central_conflict` | string | yes | no | none | LLM | candidate-only | `1..1500`; identifies opposing forces and stakes |
| `ending_direction` | string | yes | no | none | LLM | candidate-only | `1..1500`; compatible with Brief ending |
| `tone_constraints` | array<string> | yes | no | `[]` | LLM | candidate-only | `0..20`; each `1..300`; unique |

Code rejects an INIT-01 candidate that:

- changes the protagonist;
- describes a different ending;
- violates a Brief `avoid` item;
- embeds character, relationship, world, or ID objects that belong to later stages;
- contains publication metadata.

---

## 7. INIT-02 People candidate

INIT-02 returns:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `characters` | array<Character candidate> | yes | no | none | LLM | candidate-only | `2..50`; local keys and normalized names unique; exactly one protagonist |
| `relationships` | array<Relationship candidate> | yes | no | none | LLM | candidate-only | `1..100`; local keys unique; endpoint pair and relationship type unique |

### 7.1 Character candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Initial local key | yes | no | none | LLM | candidate-only | globally unique |
| `name` | string | yes | no | none | LLM | candidate-only | `1..100`; normalized name unique |
| `aliases` | array<string> | yes | no | `[]` | LLM | candidate-only | `0..20`; unique; no alias equals another Character's name |
| `role` | enum `character_role` | yes | no | none | LLM | candidate-only | registry value |
| `core_trait` | string | yes | no | none | LLM | candidate-only | `1..500` |
| `values` | array<string> | yes | no | none | LLM | candidate-only | `1..20`; each `1..300`; unique |
| `background` | string | yes | no | none | LLM | candidate-only | `1..3000`; Brief-compatible |
| `immutable_facts` | array<string> | yes | no | `[]` | LLM | candidate-only | `0..30`; unique; genuinely identity-defining facts only |
| `appearance_anchor` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `speech_anchor` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `scope` | enum `scope` | yes | no | none | LLM | candidate-only | protagonist and all Brief key people require `series`; other initial Characters use `volume` or `series` |
| `starting_location_local_key` | Initial local key | yes | yes | `null` | LLM | candidate-only | null or World-entity candidate with `kind=location` |
| `starting_physical_condition` | string | yes | yes | `null` | LLM | candidate-only | null or `1..500` |
| `starting_emotional_state` | string | yes | yes | `null` | LLM | candidate-only | null or `1..500` |
| `starting_goal` | string | yes | yes | `null` | LLM | candidate-only | null or `1..500` |
| `starting_pressure` | string | yes | yes | `null` | LLM | candidate-only | null or `1..500` |

### 7.2 Character coverage rules

- Exactly one Character has `role=protagonist`.
- Its normalized `name` equals `brief.protagonist.name`.
- Its `core_trait`, starting pressure, and starting goal remain compatible with the Brief.
- Every Brief key person resolves to exactly one Character by normalized name.
- Additional supporting Characters are permitted.
- A normalized Character name cannot appear only as another Character's alias.

### 7.3 Relationship candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Initial local key | yes | no | none | LLM | candidate-only | globally unique |
| `participant_a_local_key` | Initial local key | yes | no | none | LLM | candidate-only | resolves to Character |
| `participant_b_local_key` | Initial local key | yes | no | none | LLM | candidate-only | resolves to a different Character |
| `relationship_type` | enum `relationship_type` | yes | no | none | LLM | candidate-only | registry value |
| `relationship_origin` | string | yes | no | none | LLM | candidate-only | `1..1500`; fixed historical origin |
| `structural_role` | enum `structural_role` | yes | no | none | LLM | candidate-only | registry value |
| `scope` | enum `scope` | yes | no | none | LLM | candidate-only | `volume` or `series`; primary relationships require `series` |
| `starting_public_relation` | string | yes | no | none | LLM | candidate-only | `1..500` |
| `a_to_b` | Directional relationship candidate | yes | no | none | LLM | candidate-only | complete child object |
| `b_to_a` | Directional relationship candidate | yes | no | none | LLM | candidate-only | complete child object |
| `shared_state` | string | yes | no | none | LLM | candidate-only | `1..1000` |

### 7.4 Directional relationship candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `trust` | enum `trust` | yes | no | none | LLM | candidate-only | registry value |
| `perception` | string | yes | no | none | LLM | candidate-only | `1..500` |
| `emotional_stance` | string | yes | no | none | LLM | candidate-only | `1..500` |
| `current_intention` | string | yes | no | none | LLM | candidate-only | `1..500` |

Relationship directions are determined by the candidate's explicit participant order and remain aligned after persistent-ID conversion.

---

## 8. INIT-03 World candidate

INIT-03 returns:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `world_entities` | array<World-entity candidate> | yes | no | none | LLM | candidate-only | `1..200`; local keys and normalized `(kind,name)` unique |
| `temporal_rules` | array<Temporal-rule candidate> | yes | no | `[]` | LLM | candidate-only | `0..100`; local keys unique |
| `initial_story_time` | Initial story-time candidate | yes | no | none | LLM | candidate-only | complete child object |

### 8.1 World-entity candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Initial local key | yes | no | none | LLM | candidate-only | globally unique |
| `kind` | enum `world_entity_kind` | yes | no | none | LLM | candidate-only | registry value |
| `name` | string | yes | no | none | LLM | candidate-only | `1..200` |
| `description` | string | yes | no | none | LLM | candidate-only | `1..3000` |
| `immutable_rules` | array<string> | yes | no | `[]` | LLM | candidate-only | `0..50`; each `1..500`; unique |
| `sensory_anchors` | array<string> | yes | no | `[]` | LLM | candidate-only | `0..30`; each `1..300`; unique |
| `scope` | enum `scope` | yes | no | none | LLM | candidate-only | `volume` or `series` for initial design |

At least one Location must exist when any Character has a non-null starting location.

### 8.2 Temporal-rule candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Initial local key | yes | no | none | LLM | candidate-only | globally unique |
| `kind` | enum `temporal_rule_kind` | yes | no | none | LLM | candidate-only | registry value |
| `description` | string | yes | no | none | LLM | candidate-only | `1..1500` |
| `fixed_rule` | string | yes | no | none | LLM | candidate-only | `1..1500`; mechanically interpretable narrative constraint |
| `related_local_keys` | array<Initial local key> | yes | no | `[]` | LLM | candidate-only | unique; each resolves to a Character, World entity, Thread, or Ending criterion after integration |
| `scope` | enum `scope` | yes | no | none | LLM | candidate-only | `volume` or `series` |

### 8.3 Initial story-time candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `time_label` | string | yes | yes | `null` | LLM | candidate-only | null or `1..300` |
| `parallel_group_id` | string | yes | yes | `null` | LLM | candidate-only | normally null; non-null only when the story intentionally opens inside an already defined parallel sequence |

INIT-ID creates Story-clock order and scene-position fields. INIT-03 never outputs them.

---

## 9. INIT-04 Arc, Thread, Ending, and Knowledge candidate

INIT-04 returns:

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `protagonist_arc` | Protagonist-arc candidate | yes | no | none | LLM | candidate-only | targets the sole protagonist |
| `relationship_arcs` | array<Relationship-arc candidate> | yes | no | `[]` | LLM | candidate-only | unique relationship reference |
| `major_threads` | array<Major-thread candidate> | yes | no | none | LLM | candidate-only | `1..30`; local keys unique |
| `ending_criteria` | array<Ending-criterion candidate> | yes | no | none | LLM | candidate-only | `1..20`; local keys unique; at least one required |
| `knowledge_items` | array<Initial Knowledge-item candidate> | yes | no | `[]` | LLM | candidate-only | local keys unique; normalized fact triples unique |
| `initial_knowledge_states` | array<Initial Knowledge-state candidate> | yes | no | `[]` | LLM | candidate-only | non-default states only; unique audience/fact tuple |

### 9.1 Arc turning point

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `sequence` | integer | yes | no | none | LLM | candidate-only | contiguous starting at `1` |
| `description` | string | yes | no | none | LLM | candidate-only | `1..1000` |
| `purpose` | string | yes | no | none | LLM | candidate-only | `1..500`; describes dramatic function, not future prose |

### 9.2 Protagonist-arc candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `protagonist_local_key` | Initial local key | yes | no | none | LLM | candidate-only | resolves to sole protagonist Character |
| `start_state` | string | yes | no | none | LLM | candidate-only | `1..1500`; compatible with Genesis Character state |
| `turning_points` | array<Arc turning point> | yes | no | none | LLM | candidate-only | `1..12`; contiguous sequence |
| `end_state` | string | yes | no | none | LLM | candidate-only | `1..1500`; compatible with Brief ending |
| `change_function` | string | yes | no | none | LLM | candidate-only | `1..1000` |

### 9.3 Relationship-arc candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `relationship_local_key` | Initial local key | yes | no | none | LLM | candidate-only | resolves to Relationship |
| `start_state` | string | yes | no | none | LLM | candidate-only | `1..1500`; compatible with starting Relationship state |
| `turning_points` | array<Arc turning point> | yes | no | none | LLM | candidate-only | `1..12`; contiguous sequence |
| `end_state` | string | yes | no | none | LLM | candidate-only | `1..1500` |
| `change_function` | string | yes | no | none | LLM | candidate-only | `1..1000` |

### 9.4 Major-thread candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Initial local key | yes | no | none | LLM | candidate-only | globally unique |
| `description` | string | yes | no | none | LLM | candidate-only | `1..1500`; one trackable dramatic question |
| `author_truth` | string | yes | no | none | LLM | candidate-only | `1..2000`; author-only actual truth |
| `resolution_condition` | string | yes | no | none | LLM | candidate-only | `1..1500`; observable condition sufficient for resolution |
| `presentation_rule` | string | yes | no | none | LLM | candidate-only | `1..1500`; controls withholding and revelation |
| `required` | constant boolean `true` | yes | no | `true` | LLM | candidate-only | exact true |
| `scope` | constant `series` | yes | no | `series` | LLM | candidate-only | exact constant |

### 9.5 Ending-criterion candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Initial local key | yes | no | none | LLM | candidate-only | globally unique |
| `description` | string | yes | no | none | LLM | candidate-only | `1..1500`; independently auditable condition |
| `required` | boolean | yes | no | none | LLM | candidate-only | boolean |
| `source_ending_text` | string | yes | no | none | LLM | candidate-only | exact nonempty substring of adopted Brief `ending` |
| `scope` | constant `series` | yes | no | `series` | LLM | candidate-only | exact constant |

### 9.6 Initial Knowledge-item candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `local_key` | Initial local key | yes | no | none | LLM | candidate-only | globally unique |
| `subject_type` | enum `knowledge_subject_type` | yes | no | none | LLM | candidate-only | compatible with subject reference |
| `subject_local_key` | Initial local key | yes | no | none | LLM | candidate-only | resolves to compatible Character, Relationship, World entity, Temporal rule, Thread, or Ending criterion |
| `canonical_fact` | string | yes | no | none | LLM | candidate-only | `1..1500`; one independently trackable fact |
| `writer_visible_label` | string | yes | no | none | LLM | candidate-only | `1..500`; safe non-secret label |
| `author_truth` | string | yes | no | none | LLM | candidate-only | `1..2000`; may equal canonical fact; never projected to Writer View |
| `scope` | enum `scope` | yes | no | none | LLM | candidate-only | registry value |

### 9.7 Initial Knowledge-state candidate

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `fact_local_key` | Initial local key | yes | no | none | LLM | candidate-only | resolves to Initial Knowledge-item candidate |
| `audience_type` | enum `knowledge_audience_type` | yes | no | none | LLM | candidate-only | `character` or `reader` |
| `audience_character_local_key` | Initial local key | yes | yes | none | LLM | candidate-only | Character local key iff audience is `character`; null iff `reader` |
| `status` | audience-specific Knowledge status | yes | no | none | LLM | candidate-only | non-default only: Character status not `unknown`; Reader status not `withheld` |

INIT-ID omits default rows according to the sparse Knowledge-state contract.

---

## 10. INIT-05 integrated Initial-design bundle

INIT-05 is an LLM generation stage. It receives structurally valid INIT-01 through INIT-04 artifacts and returns one integrated bundle.

### 10.1 People design

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `characters` | array<Character candidate> | yes | no | none | LLM | candidate-only | complete INIT-02 Character contract |
| `relationships` | array<Relationship candidate> | yes | no | none | LLM | candidate-only | complete INIT-02 Relationship contract |

### 10.2 World design

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `world_entities` | array<World-entity candidate> | yes | no | none | LLM | candidate-only | complete INIT-03 contract |
| `temporal_rules` | array<Temporal-rule candidate> | yes | no | `[]` | LLM | candidate-only | complete INIT-03 contract |
| `initial_story_time` | Initial story-time candidate | yes | no | none | LLM | candidate-only | complete INIT-03 contract |

### 10.3 Arc design

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `protagonist_arc` | Protagonist-arc candidate | yes | no | none | LLM | candidate-only | complete INIT-04 contract |
| `relationship_arcs` | array<Relationship-arc candidate> | yes | no | `[]` | LLM | candidate-only | complete INIT-04 contract |
| `major_threads` | array<Major-thread candidate> | yes | no | none | LLM | candidate-only | complete INIT-04 contract |
| `ending_criteria` | array<Ending-criterion candidate> | yes | no | none | LLM | candidate-only | complete INIT-04 contract |
| `knowledge_items` | array<Initial Knowledge-item candidate> | yes | no | `[]` | LLM | candidate-only | complete INIT-04 contract |
| `initial_knowledge_states` | array<Initial Knowledge-state candidate> | yes | no | `[]` | LLM | candidate-only | complete INIT-04 contract |

### 10.4 Bundle root

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `concept` | INIT-01 Concept candidate | yes | no | none | LLM | candidate-only | complete INIT-01 contract |
| `people` | People design | yes | no | none | LLM | candidate-only | complete child object |
| `world` | World design | yes | no | none | LLM | candidate-only | complete child object |
| `arcs` | Arc design | yes | no | none | LLM | candidate-only | complete child object |

### 10.5 Integration rules

INIT-05 may reconcile wording and details, but it must:

- retain every Brief protagonist and key person;
- use globally unique local keys;
- retain every valid record required for cross-references;
- resolve all local references;
- preserve one protagonist;
- preserve the configured volume count indirectly through Brief-compatible arcs;
- keep Major threads initial-design, required, series-scoped, and truth-bearing;
- keep Ending criteria series-scoped;
- keep initial Knowledge items truth-bearing;
- avoid adding fields from planning stages such as volume numbers or chapter counts.

INIT-05 does not merely wrap invalid earlier output. The integrated result must independently satisfy the complete bundle Schema.

---

## 11. INIT-06 and INIT-REV

INIT-06 produces the generic Review-result Schema defined by the Review/Audit contract.

INIT-REV receives:

```text
last structurally valid integrated bundle
all current review issues
adopted Brief
fixed profiles and constraints
```

It returns one complete replacement Initial-design bundle using the exact INIT-05 bundle Schema.

Partial patches are forbidden.

When revision budget is exhausted, the latest structurally valid bundle may proceed to INIT-ID with residual issues recorded according to the Pipeline and Runtime contracts.

---

## 12. INIT-ID persistent-ID allocation

INIT-ID is code-only.

### 12.1 Deterministic allocation order

Within each type, candidates are sorted by `local_key`.

Allocation order:

1. Characters;
2. Relationships;
3. World entities, grouped by `kind` in this order:
   - `location`;
   - `organization`;
   - `item`;
   - `system`;
   - `culture`;
   - `history`;
4. Temporal rules;
5. Major threads;
6. Ending criteria;
7. Knowledge items.

Each type uses its own counter from `runtime/counters.json`.

### 12.2 Candidate-to-Canon mapping

| candidate | adopted record |
|---|---|
| Character candidate | Character record with `record_origin=initial_design`, `record_lifecycle=active`, `created_scene_id=null` |
| Relationship candidate | Relationship record with `record_origin=initial_design`, `record_lifecycle=active`, `created_scene_id=null` |
| World-entity candidate | World entity record with `record_origin=initial_design`, `record_lifecycle=active`, `created_scene_id=null` |
| Temporal-rule candidate | Temporal rule record with `record_origin=initial_design`, `record_lifecycle=active`, `created_scene_id=null` |
| Major-thread candidate | Thread record with `record_origin=initial_design`, `thread_type=major`, `required=true`, `record_lifecycle=active`, `created_scene_id=null` |
| Ending-criterion candidate | Ending criterion record with fixed initial-design constants |
| Initial Knowledge-item candidate | Knowledge item with `record_origin=initial_design`, `record_lifecycle=active`, `created_scene_id=null` |

### 12.3 Genesis Story-state construction

INIT-ID creates:

```text
one Character state per Character candidate
one Relationship state per Relationship candidate
one Thread state per Major-thread candidate
zero or more non-default Knowledge-state rows
one complete Story clock
```

Character-state mapping:

```text
starting_location_local_key
  → location_id

starting_physical_condition
  → physical_condition

starting_emotional_state
  → emotional_state

starting_goal
  → current_goal

starting_pressure
  → current_pressure
```

Relationship-state mapping uses:

```text
starting_public_relation
a_to_b
b_to_a
shared_state
```

Every Major thread begins:

```text
thread_status = open
progress = 0
volume_disposition = null
```

Story clock begins:

```text
current_order = 0
time_label = world.initial_story_time.time_label
parallel_group_id = world.initial_story_time.parallel_group_id
last_scene_id = null
current_volume_number = null
current_chapter_number = null
current_scene_number = null
```

---

## 13. Adopted `canon/initial-design.json`

This immutable file stores author-facing concept and arc design without duplicating complete Canon records.

### 13.1 Adopted arc turning point

Same fields as the candidate turning point:

```text
sequence
description
purpose
```

### 13.2 Adopted protagonist arc

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `protagonist_id` | Character ID | yes | no | none | code | adopted protagonist |
| `start_state` | string | yes | no | none | code from bundle | candidate value |
| `turning_points` | array<Adopted arc turning point> | yes | no | none | code from bundle | candidate value |
| `end_state` | string | yes | no | none | code from bundle | candidate value |
| `change_function` | string | yes | no | none | code from bundle | candidate value |

### 13.3 Adopted relationship arc

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `relationship_id` | Relationship ID | yes | no | none | code | adopted Relationship |
| `start_state` | string | yes | no | none | code from bundle | candidate value |
| `turning_points` | array<Adopted arc turning point> | yes | no | none | code from bundle | candidate value |
| `end_state` | string | yes | no | none | code from bundle | candidate value |
| `change_function` | string | yes | no | none | code from bundle | candidate value |

### 13.4 Initial-design root

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | immutable | exact constant | `canon/initial-design.json` |
| `brief_path` | constant path `input/brief.json` | yes | no | exact path | code | immutable | exact constant | `canon/initial-design.json` |
| `brief_sha256` | SHA-256 | yes | no | none | code | immutable | adopted Brief hash | `canon/initial-design.json` |
| `accepted_bundle_sha256` | SHA-256 | yes | no | none | code | immutable | accepted integrated-bundle canonical bytes | `canon/initial-design.json` |
| `concept` | INIT-01 Concept candidate | yes | no | none | code from bundle | immutable | complete Concept contract | `canon/initial-design.json` |
| `protagonist_arc` | Adopted protagonist arc | yes | no | none | code | immutable | local key replaced by persistent ID | `canon/initial-design.json` |
| `relationship_arcs` | array<Adopted relationship arc> | yes | no | `[]` | code | immutable | unique Relationship IDs; sorted | `canon/initial-design.json` |
| `character_ids` | array<Character ID> | yes | no | none | code | immutable | complete adopted Character set; sorted | `canon/initial-design.json` |
| `relationship_ids` | array<Relationship ID> | yes | no | none | code | immutable | complete adopted Relationship set; sorted | `canon/initial-design.json` |
| `world_entity_ids` | array<World entity ID> | yes | no | none | code | immutable | complete adopted World-entity set; sorted by prefix then numeric suffix | `canon/initial-design.json` |
| `temporal_rule_ids` | array<Temporal rule ID> | yes | no | `[]` | code | immutable | complete adopted Temporal-rule set; sorted | `canon/initial-design.json` |
| `major_thread_ids` | array<Thread ID> | yes | no | none | code | immutable | complete adopted Major-thread set; sorted | `canon/initial-design.json` |
| `ending_criterion_ids` | array<Ending criterion ID> | yes | no | none | code | immutable | complete adopted Ending-criterion set; sorted | `canon/initial-design.json` |
| `knowledge_item_ids` | array<Knowledge item ID> | yes | no | `[]` | code | immutable | complete adopted initial Knowledge-item set; sorted | `canon/initial-design.json` |
| `genesis_commit_id` | constant `commit-00000000` | yes | no | exact constant | code | immutable | exact constant | `canon/initial-design.json` |
| `created_at` | RFC 3339 UTC timestamp | yes | no | none | code | immutable | equals Genesis Commit `committed_at` | `canon/initial-design.json` |

`initial-design.json` is an immutable author-design snapshot. During generation, fixed record details are read from the current Canon generation, not copied back from this file.

---

## 14. Genesis output set

INIT-ID atomically produces:

```text
canon/initial-design.json
canon/generations/00000000/current-canon.json
canon/generations/00000000/knowledge-items.json
canon/generations/00000000/story-state.json
canon/generations/00000000/evidence-index.json
canon/generations/00000000/commit-manifest.json
canon/generations/00000000/generation-manifest.json
canon/HEAD
```

Genesis Evidence index is:

```json
{"records":[]}
```

Initial-design assertions do not use prose Evidence records.

The Genesis Commit manifest's `local_key_mappings` contains every Character, Relationship, World entity, Temporal rule, Thread, Ending criterion, and Knowledge item candidate.

---

## 15. Cross-candidate integration rules

Before INIT-06, code verifies all of the following:

```text
every Brief person is represented
exactly one protagonist exists
every Relationship endpoint resolves and differs
every Character starting Location resolves
every Temporal-rule related reference resolves
every protagonist and Relationship arc target resolves
every Major thread is required and series-scoped
every Ending source text is a Brief-ending substring
every initial Knowledge subject resolves
every initial Knowledge-state fact and audience resolves
no duplicate local key
no duplicate active fact triple
no unknown enum
no unknown field
no persistent ID
no Scene ID
no impossible Story-state initialization
```

The integrated bundle is invalid if any rule fails.

---

## 16. Forbidden fields and deprecated names

Forbidden in Brief content candidate:

```text
editorial_profile_id
publishing_profile_id
brief_version
source_type
source_hash
created_at
```

Forbidden in INIT candidate artifacts:

```text
persistent IDs
record_type
record_origin
record_lifecycle
created_scene_id
Commit ID
Generation ID
hash
timestamp
volume_number
chapter_number
scene_number
future prose
publication metadata
```

Deprecated names:

```text
relationship.origin
knowledge_origin
genesis as record origin
time-000001
initial_state object without child Schema
people/world/arcs as undocumented free-form objects
```

Use:

```text
relationship_origin
record_origin = initial_design
rule-000001
the exact child contracts in this document
```

---

## 17. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
Keyword-source Schema and hash
direct Brief-content projection hash
INPUT-02 cannot output profile IDs or metadata
Brief profile IDs equal Effective config
Brief volume range and Publishing-profile compatibility
INIT-01 exact root
INIT-02 exact people root
INIT-03 exact world root
INIT-04 exact arcs root
one protagonist and complete Brief-person coverage
global local-key uniqueness
Relationship endpoint inequality
forward Location-reference resolution
Temporal-rule reference resolution
Major-thread fixed conditions
Ending source substring validation
initial Knowledge-item and State validation
INIT-05 exact integrated root
INIT-REV whole-bundle replacement
residual-issue adoption compatibility
deterministic ID allocation order
complete local-key mapping
complete Canon record creation
complete Character/Relationship/Thread State initialization
sparse Knowledge-state initialization
complete Story clock
immutable initial-design snapshot
Genesis manifests and HEAD
unknown-field rejection
persistent-ID injection rejection
canonical serialization stability
```
