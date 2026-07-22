# Context contracts

This document is the normative contract for deterministic Context Builder snapshots, information-access boundaries, safe projections, token-limit handling, operation-specific planner/writer/reviewer/continuity/handoff/completion views, and context hashing.

The adopted Brief and Initial design are defined by [`contracts/data/brief_and_initial.md`](contracts/data/brief_and_initial.md). Planning artifacts are defined by [`contracts/data/planning_artifacts.md`](contracts/data/planning_artifacts.md). Scene artifacts are defined by [`contracts/data/scene_artifacts.md`](contracts/data/scene_artifacts.md). Review and Completion records are defined by [`contracts/data/review_and_audit.md`](contracts/data/review_and_audit.md). Canon, Story state, Evidence, and Runtime records are defined by the documents under [`contracts/ledger/`](contracts/ledger/). Effective token and model settings are defined by [`configuration_contracts.md`](configuration_contracts.md).

Every saved JSON object and every structured context payload defined here uses `additionalProperties: false`.

---

## 1. Context principles

### 1.1 Pure deterministic projection

A Context Builder:

- is code-only;
- reads adopted or frozen authoritative artifacts only;
- never calls an LLM;
- never reads a raw provider response as story authority;
- never includes an unadopted candidate except when that candidate is the explicit subject of Review or Revision;
- never mutates its sources;
- produces identical canonical bytes for identical source bytes, builder version, operation, target, and semantic configuration;
- removes optional records only by the deterministic rules in this document;
- never truncates a JSON token stream or cuts a string to make it fit.

### 1.2 Least-authority views

Storycraft uses distinct views.

| view | intended consumer | author-only truth |
|---|---|---|
| Brief-generation view | INPUT-02 | no |
| Initial-design view | INIT stages | Brief ending and design instructions only |
| Planner Author view | SERIES/VOL/CH/SC planning | yes, limited to the planning scope |
| Writer view | PROSE generation/revision | no |
| Private Review view | semantic reviewers | yes only when required to detect contradiction or disclosure |
| Continuity view | DELTA extraction/revision | no hidden author truth |
| Volume-handoff view | VH generation/revision | private current state, but no unrelated future plan |
| Completion view | COMP-AUDIT | yes, complete for required criteria and Major Threads |
| Publication-safe projection | publication construction | no |

A view intended for one consumer must not be reused for a more privileged consumer by adding fields ad hoc. A separate builder or explicit union branch is required.

### 1.3 Source precedence

When two sources disagree:

```text
frozen/adopted prose:
  exact narrative wording

current Canon generation:
  fixed adopted records and lifecycle

current Story state:
  mutable adopted values

current Evidence index:
  adopted prose support/contradiction

frozen Scene card:
  intended work and update authorization for the active scene

latest adopted handoff:
  safe narrative carry-over summary

planning artifacts:
  intended future structure

initial design:
  author-facing concept and arcs

Brief:
  user intent

review/residual issues:
  private quality constraints, never story facts
```

Planning or handoff text never overrides an adopted Canon or Story-state value.

---

## 2. Context-snapshot path and hash

Every LLM logical input uses one immutable Context snapshot.

Canonical path:

```text
runtime/context-snapshots/
  <operation-id-lower>/
    <target-id-path-safe>/
      <context-sha256>.json
```

Examples:

```text
runtime/context-snapshots/sc-01/v01-c001-s001/0123....abcd.json
runtime/context-snapshots/prose-01/v01-c001-s001/4567....ef01.json
runtime/context-snapshots/comp-audit/completion/89ab....2345.json
```

`context-sha256` is the SHA-256 of the complete canonical Context-snapshot bytes.

The hash is not stored inside the snapshot, avoiding a self-hash cycle.

The following fields equal this file hash:

```text
candidate-manifest.input_snapshot_sha256
review artifact input_snapshot_sha256
LLM call audit input_snapshot_sha256
Completion precondition context_snapshot_sha256
```

A Context snapshot contains no creation timestamp. Filesystem timestamps are not authoritative.

---

## 3. Common context enums

### 3.1 Context view type

```text
brief_generation
initial_design
planner
writer
review
revision
continuity
volume_handoff
completion
```

### 3.2 Builder ID

```text
input_brief_builder
init_concept_builder
init_people_builder
init_world_builder
init_arcs_builder
init_integrator_builder
series_planner_builder
volume_planner_builder
chapter_planner_builder
scene_planner_builder
prose_writer_builder
continuity_builder
volume_handoff_builder
completion_builder
review_builder
revision_builder
```

### 3.3 Token-count method

```text
provider_tokenizer
provider_preflight
fallback_estimate
```

### 3.4 Context source role

```text
keyword_source
brief
effective_config
initial_design
series_map
volume_design
chapter_design
scene_card
prose
continuity_delta
current_canon
knowledge_items
story_state
evidence_index
generation_manifest
commit_manifest
scene_manifest
volume_handoff
chapter_handoff
scene_handoff
review
residual_issues
completion_precondition
completion_audit
publication_validation
```

### 3.5 Exclusion reason

```text
retired_record
out_of_scope
nonparticipant
non_target
distant_supporting_record
duplicate_summary
sensory_detail
resolved_supporting_thread
old_evidence
optional_handoff_detail
token_budget
```

### 3.6 Projection sensitivity

```text
public
writer_safe
private_author
private_audit
```

---

## 4. Context artifact reference

Every source artifact used to build a snapshot is recorded.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `role` | enum `context_source_role` | yes | no | none | code | immutable | compatible with path |
| `path` | workspace-relative path | yes | no | none | code | immutable | adopted, frozen, or explicit reviewed-candidate path |
| `sha256` | SHA-256 | yes | no | none | code | immutable | matches canonical source bytes |
| `generation_id` | Generation ID | yes | yes | `null` | code | immutable | non-null for generation-owned sources |
| `required` | boolean | yes | no | `true` | code | immutable | true when omission would invalidate the builder |

References are unique by `(role,path)` and sorted by role registry order then path.

A snapshot never records an absolute path.

---

## 5. Context exclusion record

Code records every whole record or detail removed by deterministic overflow handling.

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `source_role` | enum `context_source_role` | yes | no | none | code | immutable | source containing the removed item |
| `record_type` | string | yes | no | none | code | immutable | registered source record/projection type |
| `record_id` | string | yes | yes | `null` | code | immutable | persistent ID or stable projection key when one exists |
| `field_path` | JSON Pointer string | yes | yes | `null` | code | immutable | null when a whole record was excluded |
| `reason` | enum `context_exclusion_reason` | yes | no | none | code | immutable | deterministic rule |
| `priority_rank` | integer | yes | no | none | code | immutable | one-based rank in the applicable exclusion order |

Records are sorted by priority rank, source role, record type, record ID, and field path.

An exclusion record contains no removed secret value.

---

## 6. Context token-budget record

| field | type | required | nullable | default | creator | mutability | validation |
|---|---|---:|---:|---|---|---|---|
| `operation_key` | operation key from `configuration_contracts.md` | yes | no | none | code | immutable | stage-compatible |
| `model_context_window_tokens` | integer | yes | no | none | code | immutable | Effective config |
| `reserved_output_tokens` | integer | yes | no | none | code | immutable | operation-map value |
| `protocol_overhead_tokens` | integer | yes | no | none | code | immutable | Effective config |
| `max_operation_input_tokens` | integer | yes | no | none | code | immutable | operation-map value |
| `hard_input_limit` | integer | yes | no | none | code | immutable | configuration formula |
| `static_prompt_tokens` | integer | yes | no | none | code | immutable | canonical rendered prompt without snapshot payload; `>=0` |
| `context_payload_limit` | integer | yes | no | none | code | immutable | `hard_input_limit - static_prompt_tokens`; must be positive |
| `token_count_method` | enum `context_token_count_method` | yes | no | none | code | immutable | selected counting method |
| `tokenizer_id` | string | yes | yes | `null` | code | immutable | required for provider tokenizer/preflight when available |
| `payload_tokens` | integer | yes | no | none | code | immutable | token count of the canonical payload supplied to prompt renderer |
| `final_input_tokens` | integer | yes | no | none | code | immutable | exact or estimated complete rendered call input |
| `overflowed` | boolean | yes | no | `false` | code | immutable | true iff one or more optional exclusions occurred |

Rules:

```text
payload_tokens <= context_payload_limit
final_input_tokens <= hard_input_limit
```

If mandatory payload alone exceeds `context_payload_limit`, the builder stops mechanically and writes no usable Context snapshot.

The Context builder and provider-call preflight use the same canonical prompt template version and token-count implementation.

---

## 7. Common Context-snapshot root

A Context snapshot uses a discriminated union: `view_type` selects the exact `payload` contract defined later in this document.

| field | type | required | nullable | default | creator | mutability | validation | source of truth |
|---|---|---:|---:|---|---|---|---|---|
| `schema_version` | constant string `1.0` | yes | no | `1.0` | code | immutable | exact constant | Context snapshot |
| `builder_version` | string | yes | no | none | code | immutable | exact Context-builder bundle version | Context snapshot |
| `builder_id` | enum `context_builder_id` | yes | no | none | code | immutable | operation-compatible | Context snapshot |
| `view_type` | enum `context_view_type` | yes | no | none | code | immutable | selects one payload branch | Context snapshot |
| `operation_id` | Stage ID | yes | no | none | code | immutable | exact LLM stage |
| `target_id` | string | yes | no | none | code | immutable | stage-compatible and path-safe after encoding |
| `source_generation_id` | Generation ID | yes | yes | `null` | code | immutable | null before Genesis; otherwise exact generation snapshot |
| `source_generation_manifest_sha256` | SHA-256 | yes | yes | `null` | code | immutable | null iff source generation null |
| `effective_config_sha256` | SHA-256 | yes | no | none | code | immutable | config bytes used for the call |
| `prompt_version` | string | yes | no | none | code | immutable | exact stage prompt |
| `response_schema_version` | string | yes | yes | `null` | code | immutable | null for prose-text output; otherwise exact Schema |
| `sensitivity` | enum `projection_sensitivity` | yes | no | none | code | immutable | branch-compatible |
| `source_refs` | array<Context artifact reference> | yes | no | none | code | immutable | nonempty and canonical |
| `token_budget` | Context token-budget record | yes | no | none | code | immutable | Section 6 |
| `exclusions` | array<Context exclusion record> | yes | no | `[]` | code | immutable | canonical order |
| `payload` | Context payload union | yes | no | none | code | immutable | exact branch selected by `view_type` |

The `payload` is the only branch rendered as task data to the LLM. Root metadata is available to the prompt renderer but is not necessarily repeated in natural-language instructions.

---

## 8. Canonical snapshot serialization

Context snapshots use the Runtime canonical JSON rules.

Additional ordering:

- all persistent-ID arrays are sorted unless a child contract explicitly preserves dramatic order;
- source references and exclusions use Sections 4 and 5 ordering;
- selected Canon records use Canon root ordering;
- selected State rows use Story-state ordering;
- Evidence records use Evidence-ID ordering;
- Review issues use normalized Issue ordering;
- plan arrays preserve their normative planning order.

No map with arbitrary dynamic keys is permitted in a payload. Registry-keyed configuration maps may appear only through explicit fixed-key projections.

---

# Part I: Safe and private projection records

## 9. Author Character projection

Used only in private planner, private reviewer, handoff, or Completion views.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact Character record from `canon_records.md` | yes | no | none | code | complete adopted record |
| `state` | exact Character state from `story_state.md` | yes | no | none | code | matching Character ID |
| `selection_reasons` | array<string> | yes | no | none | code | nonempty fixed builder reason labels; unique, sorted |

This branch may contain private current goal, pressure, and emotional state.

---

## 10. Author Relationship projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact Relationship record | yes | no | none | code | complete adopted record |
| `state` | exact Relationship state | yes | no | none | code | matching Relationship ID |
| `selection_reasons` | array<string> | yes | no | none | code | nonempty, unique, sorted |

---

## 11. Author World projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact World entity record | yes | no | none | code | complete adopted record |
| `selection_reasons` | array<string> | yes | no | none | code | nonempty, unique, sorted |

World entities have no separate mutable State row.

---

## 12. Author Temporal-rule projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact Temporal rule record | yes | no | none | code | complete adopted record |
| `selection_reasons` | array<string> | yes | no | none | code | nonempty, unique, sorted |

---

## 13. Author Thread projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact Thread record | yes | no | none | code | may include private `author_truth` and `resolution_condition` |
| `state` | exact Thread state | yes | no | none | code | matching Thread ID |
| `relevant_evidence_ids` | array<Evidence ID> | yes | no | `[]` | code | unique, sorted |
| `selection_reasons` | array<string> | yes | no | none | code | nonempty, unique, sorted |

---

## 14. Author Ending-criterion projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact Ending criterion record | yes | no | none | code | complete adopted record |
| `relevant_evidence_ids` | array<Evidence ID> | yes | no | `[]` | code | unique, sorted |
| `selection_reasons` | array<string> | yes | no | none | code | nonempty, unique, sorted |

---

## 15. Author Knowledge projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact Knowledge item record | yes | no | none | code | private `author_truth` permitted |
| `states` | array<exact Knowledge state> | yes | no | `[]` | code | all selected explicit rows for this fact; canonical order |
| `selection_reasons` | array<string> | yes | no | none | code | nonempty, unique, sorted |

Implicit default Knowledge states are not materialized unless the selected task needs one exact audience baseline. In that case, the applicable safe/target projection below carries the derived status.

---

## 16. Writer Character projection

### 16.1 POV Character projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `character_id` | Character ID | yes | no | none | code | Scene-card POV |
| `name` | string | yes | no | none | code | Character record |
| `aliases` | array<string> | yes | no | `[]` | code | Character record |
| `role` | enum `character_role` | yes | no | none | code | Character record |
| `core_trait` | string | yes | no | none | code | Character record |
| `values` | array<string> | yes | no | none | code | Character record |
| `background` | string | yes | no | none | code | Character record; secret-free for writer use |
| `immutable_facts` | array<string> | yes | no | `[]` | code | Character record |
| `appearance_anchor` | string | yes | no | none | code | Character record |
| `speech_anchor` | string | yes | no | none | code | Character record |
| `location_id` | Location ID | yes | yes | `null` | code | current Character state |
| `physical_condition` | string | yes | yes | `null` | code | current Character state |
| `emotional_state` | string | yes | yes | `null` | code | current POV-internal state |
| `current_goal` | string | yes | yes | `null` | code | current POV-internal state |
| `current_pressure` | string | yes | yes | `null` | code | current POV-internal state |

### 16.2 Visible non-POV Character projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `character_id` | Character ID | yes | no | none | code | Scene-card participant other than POV |
| `name` | string | yes | no | none | code | Character record |
| `aliases` | array<string> | yes | no | `[]` | code | Character record |
| `role` | enum `character_role` | yes | no | none | code | Character record |
| `appearance_anchor` | string | yes | no | none | code | Character record |
| `speech_anchor` | string | yes | no | none | code | Character record |
| `immutable_facts` | array<string> | yes | no | `[]` | code | only writer-safe fixed facts relevant to the scene |
| `location_id` | Location ID | yes | yes | `null` | code | current State when visible/relevant |
| `observable_physical_condition` | string | yes | yes | `null` | code | current physical condition only when observable or plan-required |
| `scene_intention_label` | string | yes | yes | `null` | code | safe plan-derived behavior direction; never private current goal verbatim |
| `relationship_role_labels` | array<string> | yes | no | `[]` | code | safe labels derived from selected Relationship targets |

The Writer View does not expose a non-POV Character's private emotional state, current goal, current pressure, or Knowledge states unless the frozen Scene card explicitly requires an observable disclosure. Such disclosure is represented as a safe scene target, not by copying private State fields.

---

## 17. Writer Relationship projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `relationship_id` | Relationship ID | yes | no | none | code | selected Relationship |
| `participant_a_id` | Character ID | yes | no | none | code | Relationship record |
| `participant_b_id` | Character ID | yes | no | none | code | Relationship record |
| `relationship_type` | enum `relationship_type` | yes | no | none | code | Relationship record |
| `public_relation` | string | yes | no | none | code | current Relationship state |
| `pov_to_other` | Writer directional Relationship projection | yes | no | none | code | direction from POV when POV is endpoint; otherwise safe observer projection |
| `other_to_pov` | Writer directional Relationship projection | yes | no | none | code | opposite direction when POV is endpoint; private fields generalized |
| `shared_state` | string | yes | no | none | code | current Relationship shared state when writer-safe |
| `scene_target` | string | yes | yes | `null` | code | safe required-change summary from frozen Scene card |

Writer directional Relationship projection:

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `trust` | enum `trust` | yes | yes | `null` | code | full value for POV's own direction; null when private other-character trust is not safely knowable |
| `perception` | string | yes | yes | `null` | code | full POV perception or generalized observable label |
| `emotional_stance` | string | yes | yes | `null` | code | full POV stance or generalized observable label |
| `current_intention` | string | yes | yes | `null` | code | full POV intention; null/generalized for non-POV private intention |

---

## 18. Writer World projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `world_entity_id` | World entity ID | yes | no | none | code | selected entity |
| `kind` | enum `world_entity_kind` | yes | no | none | code | World record |
| `name` | string | yes | no | none | code | World record |
| `description` | string | yes | no | none | code | writer-safe fixed description |
| `immutable_rules` | array<string> | yes | no | `[]` | code | relevant fixed rules |
| `sensory_anchors` | array<string> | yes | no | `[]` | code | relevant anchors; first optional overflow detail removed |

---

## 19. Writer Temporal-rule projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `temporal_rule_id` | Temporal rule ID | yes | no | none | code | selected rule |
| `kind` | enum `temporal_rule_kind` | yes | no | none | code | rule record |
| `description` | string | yes | no | none | code | writer-safe description |
| `fixed_rule` | string | yes | no | none | code | exact applicable fixed rule |

`related_ids` is not projected unless needed to understand the rule in this scene.

---

## 20. Writer Knowledge projection

### 20.1 POV-known fact

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `fact_id` | Knowledge item ID | yes | no | none | code | selected fact |
| `writer_visible_label` | string | yes | no | none | code | safe Knowledge label |
| `status` | enum `character_knowledge_status` | yes | no | none | code | exact POV explicit or implicit status |
| `scene_target_status` | enum `character_knowledge_status` | yes | yes | `null` | code | frozen Scene target or null |
| `scene_purpose` | string | yes | yes | `null` | code | safe target purpose |

Rules:

- implicit `unknown` rows are omitted unless the frozen Scene card targets that fact;
- `author_truth` is never projected;
- `canonical_fact` is never projected directly;
- `writer_visible_label` must be sufficient for safe writing; an insufficient label is a design defect, not permission to expose author truth.

### 20.2 Reader-known fact

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `fact_id` | Knowledge item ID | yes | no | none | code | selected fact |
| `writer_visible_label` | string | yes | no | none | code | safe Knowledge label |
| `status` | enum `reader_knowledge_status` | yes | no | none | code | exact explicit or implicit reader status |
| `scene_target_status` | enum `reader_knowledge_status` | yes | yes | `null` | code | frozen Scene target or null |
| `scene_purpose` | string | yes | yes | `null` | code | safe target purpose |

Reader facts with implicit `withheld` are omitted unless targeted or needed for a forbidden-disclosure constraint.

---

## 21. Writer Thread projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `thread_id` | Thread ID | yes | no | none | code | selected Thread |
| `thread_type` | enum `thread_type` | yes | no | none | code | Thread record |
| `description` | string | yes | no | none | code | writer-safe public dramatic question |
| `status` | enum `thread_status` | yes | no | none | code | current Thread state |
| `progress` | integer | yes | no | none | code | current Thread state |
| `scene_operation` | enum `thread_action` | yes | yes | `null` | code | frozen Scene action or null |
| `target_status` | enum `thread_status` | yes | yes | `null` | code | frozen Scene target or null |
| `target_progress` | integer | yes | yes | `null` | code | frozen Scene target or null |
| `purpose` | string | yes | yes | `null` | code | safe Scene-card purpose |
| `presentation_constraint` | string | yes | yes | `null` | code | safe abstraction derived from presentation rule; no author truth or resolution condition |

---

## 22. Writer forbidden-disclosure projection

This is the exact frozen Scene-card Forbidden-disclosure record from `scene_artifacts.md`.

The Writer View may include:

```text
constraint_id
source_type
source_id
label
reason
release_hint
```

It never includes the hidden source value that caused the constraint.

---

## 23. Safe previous-handoff projection

This projection is used by prose generation and later planners. The full private Volume-handoff artifact may contain more detail.

### 23.1 Safe Character carry-over

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `character_id` | Character ID | yes | no | none | code | selected active Character |
| `public_state_summary` | string | yes | no | none | code | secret-free current summary |
| `location_id` | Location ID | yes | yes | `null` | code | current location |
| `physical_condition` | string | yes | yes | `null` | code | writer-safe |
| `pov_private_summary` | string | yes | yes | `null` | code | non-null only for the next scene's POV Character |

### 23.2 Safe Relationship carry-over

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `relationship_id` | Relationship ID | yes | no | none | code | selected Relationship |
| `public_relation` | string | yes | no | none | code | current public relation |
| `shared_state_summary` | string | yes | no | none | code | secret-free |
| `pov_direction_summary` | string | yes | yes | `null` | code | next POV's own direction only |

### 23.3 Safe Thread carry-over

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `thread_id` | Thread ID | yes | no | none | code | selected non-retired Thread |
| `description` | string | yes | no | none | code | writer-safe |
| `status` | enum `thread_status` | yes | no | none | code | current |
| `progress` | integer | yes | no | none | code | current |
| `next_pressure` | string | yes | yes | `null` | code | safe adopted handoff instruction |

### 23.4 Safe handoff root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `source_scope` | enum | yes | no | none | code | `scene`, `chapter`, or `volume` |
| `source_id` | string | yes | no | none | code | adopted source |
| `narrative_handoff` | string | yes | no | none | code | secret-free summary |
| `open_pressures` | array<string> | yes | no | `[]` | code | unique, ordered by urgency |
| `character_states` | array<Safe Character carry-over> | yes | no | `[]` | code | sorted |
| `relationship_states` | array<Safe Relationship carry-over> | yes | no | `[]` | code | sorted |
| `carried_threads` | array<Safe Thread carry-over> | yes | no | `[]` | code | sorted |
| `story_clock` | exact Story-clock object | yes | no | none | code | adopted State |
| `next_constraints` | array<string> | yes | no | `[]` | code | safe constraints only |
| `source_artifact_sha256` | SHA-256 | yes | no | none | code | full adopted handoff hash |

---

## 24. Private disclosure-check record

Used only by private prose Review.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `constraint_id` | string | yes | no | none | code | matches frozen Scene-card constraint |
| `source_type` | enum from Forbidden-disclosure record | yes | no | none | code | exact |
| `source_id` | persistent ID | yes | yes | `null` | code | exact |
| `hidden_content` | string | yes | no | none | code | minimum private phrase/fact needed to detect disclosure |
| `allowed_abstraction` | string | yes | no | none | code | safe level permitted in prose |
| `detection_notes` | string | yes | no | none | code | private reviewer instruction |

This record is never included in Writer, Continuity, handoff-safe, publication, or normal logs.

---

# Part II: Core view roots

## 25. Brief-generation view

Used only by INPUT-02.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `keyword_source` | exact Keyword-source root | yes | no | none | code | adopted normalized source |
| `editorial_profile` | exact Editorial profile | yes | no | none | code | Effective config |
| `publishing_profile` | exact Publishing profile | yes | no | none | code | Effective config |
| `brief_contract_summary` | array<Context rule> | yes | no | none | code | fixed INPUT-02 rules |

No Canon, plan, runtime usage, prior run, raw audit, or credential data is included.

---

## 26. Initial-design view

The exact root depends on the INIT stage.

### 26.1 INIT-01 Concept view

```text
brief
editorial_profile
publishing_profile
concept_contract_rules
```

### 26.2 INIT-02 People view

```text
brief
accepted_concept_candidate
editorial_profile
people_contract_rules
```

### 26.3 INIT-03 World view

```text
brief
accepted_concept_candidate
accepted_people_candidate
editorial_profile
world_contract_rules
```

The People candidate is included to resolve proposed starting locations and world needs. It remains unadopted but is an explicit earlier structurally valid stage input.

### 26.4 INIT-04 Arcs view

```text
brief
accepted_concept_candidate
accepted_people_candidate
accepted_world_candidate
editorial_profile
publishing_profile
arcs_contract_rules
```

### 26.5 INIT-05 Integration view

```text
brief
concept_candidate
people_candidate
world_candidate
arcs_candidate
editorial_profile
publishing_profile
integration_rules
```

Every listed candidate path/hash is recorded in `source_refs`. No unrelated candidate is permitted.

### 26.6 Initial-design view root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `stage` | enum | yes | no | none | code | `concept`, `people`, `world`, `arcs`, or `integrate` |
| `brief` | exact adopted Brief | yes | no | none | code | complete |
| `concept_candidate` | exact INIT-01 candidate | yes | yes | `null` | code | required from People stage onward |
| `people_candidate` | exact INIT-02 candidate | yes | yes | `null` | code | required from World stage onward |
| `world_candidate` | exact INIT-03 candidate | yes | yes | `null` | code | required from Arcs stage onward |
| `arcs_candidate` | exact INIT-04 candidate | yes | yes | `null` | code | required only for Integrate |
| `editorial_profile` | exact Editorial profile | yes | no | none | code | Effective config |
| `publishing_profile` | exact Publishing profile | yes | no | none | code | Effective config |
| `rules` | array<Context rule> | yes | no | none | code | stage-specific nonempty rules |

Conditional nullability follows Sections 26.1–26.5 exactly.

---

## 27. Planner Author view

Used by SERIES-01, VOL-01, CH-01, and SC-01.

### 27.1 Planner target descriptor

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `planning_level` | enum | yes | no | none | code | `series`, `volume`, `chapter`, or `scene` |
| `volume_number` | integer | yes | yes | `null` | code | required for Volume/Chapter/Scene |
| `chapter_number` | integer | yes | yes | `null` | code | required for Chapter/Scene |
| `scene_number` | integer | yes | yes | `null` | code | required for Scene |
| `target_plan_entry` | typed planning entry | yes | yes | `null` | code | null for Series; exact target entry otherwise |

### 27.2 Planner Author-view root

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `target` | Planner target descriptor | yes | no | none | code | complete |
| `brief` | exact adopted Brief | yes | no | none | code | complete |
| `initial_design` | exact adopted Initial-design root | yes | no | none | code | complete |
| `series_map` | exact adopted Series map | yes | yes | `null` | code | null for Series planning; required otherwise |
| `volume_design` | exact adopted Volume design | yes | yes | `null` | code | required for Chapter/Scene |
| `chapter_design` | exact adopted Chapter design | yes | yes | `null` | code | required for Scene |
| `characters` | array<Author Character projection> | yes | no | none | code | selected by Section 36 |
| `relationships` | array<Author Relationship projection> | yes | no | `[]` | code | selected |
| `world_entities` | array<Author World projection> | yes | no | `[]` | code | selected |
| `temporal_rules` | array<Author Temporal-rule projection> | yes | no | `[]` | code | selected |
| `threads` | array<Author Thread projection> | yes | no | none | code | all required Major Threads plus selected others |
| `ending_criteria` | array<Author Ending-criterion projection> | yes | no | none | code | all required criteria plus selected optional targets |
| `knowledge_items` | array<Author Knowledge projection> | yes | no | `[]` | code | selected |
| `story_clock` | exact Story-clock object | yes | no | none | code | source generation |
| `previous_handoff` | full private adopted handoff or safe projection | yes | yes | `null` | code | level-appropriate immediately preceding handoff |
| `residual_constraints` | array<Safe residual constraint> | yes | no | `[]` | code | selected private issues transformed to task constraints |
| `editorial_profile` | exact Editorial profile | yes | no | none | code | Effective config |
| `publishing_profile` | exact Publishing profile | yes | no | none | code | Effective config |

Planner Author views may contain Thread author truth and Ending source text because planners decide what to depict and what to withhold. Those private fields must not be copied into Scene cards, Writer Views, or publication-safe text.

---

## 28. Writer Scene-card projection

The Writer View does not receive source hashes, allowed-update mechanics, or private Canon metadata.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `scene_id` | Scene ID | yes | no | none | code | frozen Scene card |
| `volume_number` | integer | yes | no | none | code | frozen Scene card |
| `chapter_number` | integer | yes | no | none | code | frozen Scene card |
| `scene_number` | integer | yes | no | none | code | frozen Scene card |
| `pov_character_id` | Character ID | yes | no | none | code | frozen Scene card |
| `participant_ids` | array<Character ID> | yes | no | none | code | frozen Scene card |
| `location_id` | Location ID | yes | yes | `null` | code | frozen Scene card |
| `time_relation` | enum `time_relation` | yes | no | none | code | frozen Scene card |
| `time_label` | string | yes | yes | `null` | code | frozen Scene card |
| `parallel_group_id` | string | yes | yes | `null` | code | frozen Scene card |
| `scene_purpose` | string | yes | no | none | code | frozen Scene card |
| `required_beats` | array<string> | yes | no | none | code | dramatic order retained |
| `emotional_change_target` | string | yes | no | none | code | frozen Scene card |
| `relationship_change_targets` | array<Scene Relationship target> | yes | no | `[]` | code | frozen Scene card |
| `thread_actions` | array<Frozen Scene Thread action> | yes | no | `[]` | code | frozen Scene card |
| `character_knowledge_targets` | array<Frozen Character Knowledge target> | yes | no | `[]` | code | frozen Scene card |
| `reader_disclosures` | array<Frozen Reader disclosure> | yes | no | `[]` | code | frozen Scene card |
| `ending_criterion_targets` | array<Writer-safe Ending target> | yes | no | `[]` | code | safe projection below |
| `canon_change_targets` | array<Writer-safe Canon change target> | yes | no | `[]` | code | safe projection below |
| `new_item_policy` | exact New-item policy | yes | no | none | code | frozen Scene card |
| `length_guidance` | exact Length-guidance object | yes | no | none | code | frozen Scene card |
| `chapter_completion_role` | enum `chapter_completion_role` | yes | no | none | code | frozen Scene card |
| `forbidden_disclosures` | array<Forbidden-disclosure record> | yes | no | `[]` | code | exact safe records |

### 28.1 Writer-safe Ending target

```text
criterion_id
intended_relation
purpose
required
```

The Writer projection includes no Ending source text.

### 28.2 Writer-safe Canon change target

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `target_type` | enum | yes | no | none | code | `canon_record` or `knowledge_item_record` |
| `target_id` | persistent ID | yes | no | none | code | frozen Scene target |
| `field_path` | JSON Pointer string | yes | no | none | code | frozen Scene target |
| `purpose` | string | yes | no | none | code | frozen Scene target |
| `required` | boolean | yes | no | `false` | code | frozen Scene target |

The update operation and exact target value are not writing instructions and are omitted.

---

## 29. Writer view root

Used by PROSE-01 and PROSE-REV.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `scene_card` | Writer Scene-card projection | yes | no | none | code | Section 28 |
| `pov_character` | POV Character projection | yes | no | none | code | Section 16.1 |
| `visible_characters` | array<Visible non-POV Character projection> | yes | no | `[]` | code | one per other participant; sorted |
| `visible_relationships` | array<Writer Relationship projection> | yes | no | `[]` | code | selected and sorted |
| `visible_world` | array<Writer World projection> | yes | no | `[]` | code | selected and sorted |
| `visible_temporal_rules` | array<Writer Temporal-rule projection> | yes | no | `[]` | code | selected and sorted |
| `visible_threads` | array<Writer Thread projection> | yes | no | `[]` | code | selected and sorted |
| `pov_known_facts` | array<POV-known fact> | yes | no | `[]` | code | sorted |
| `reader_known_facts` | array<Reader-known fact> | yes | no | `[]` | code | sorted |
| `previous_handoff` | Safe previous-handoff projection | yes | yes | `null` | code | immediately prior adopted safe projection |
| `style_profile` | Writer style projection | yes | no | none | code | Section 30 |
| `context_identity` | Writer context identity | yes | no | none | code | Section 31 |

The Writer View contains no full Canon root, full Story-state root, full Knowledge-item record, raw plan, private Issue record, Evidence quote, or future Scene detail.

---

## 30. Writer style projection

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `profile_id` | string | yes | no | none | code | Editorial profile |
| `language_tag` | string | yes | no | none | code | Editorial profile |
| `narrative_person` | enum | yes | no | none | code | Editorial profile |
| `tense` | enum | yes | no | none | code | Editorial profile |
| `pov_policy` | constant `single_pov_per_scene` | yes | no | exact | code | Editorial profile |
| `pov_distance` | enum | yes | no | none | code | Editorial profile |
| `dialogue_guidance` | string | yes | no | none | code | Editorial profile |
| `prose_constraints` | array<string> | yes | no | none | code | Editorial profile |
| `forbidden_content` | array<string> | yes | no | `[]` | code | Editorial profile |

Publishing profile is not included in prose generation.

---

## 31. Writer context identity

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `source_generation_id` | Generation ID | yes | no | none | code | frozen Scene-card generation |
| `scene_id` | Scene ID | yes | no | none | code | target scene |
| `scene_card_sha256` | SHA-256 | yes | no | none | code | frozen card |
| `previous_handoff_sha256` | SHA-256 | yes | yes | `null` | code | null iff no handoff |
| `editorial_profile_id` | string | yes | no | none | code | Effective config |

The snapshot hash is intentionally not placed inside this child object.

---

## 32. Continuity view root

Used by DELTA-01 and DELTA-REV.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `scene_card` | exact frozen Scene card | yes | no | none | code | complete, including allowed targets |
| `prose` | string | yes | no | none | code | exact canonical frozen prose without additional wrapping |
| `target_baselines` | array<Continuity target baseline union> | yes | no | `[]` | code | exact before values for allowed targets |
| `existing_record_catalog` | array<Continuity record projection union> | yes | no | `[]` | code | relevant safe records only |
| `knowledge_catalog` | array<Continuity Knowledge projection> | yes | no | `[]` | code | selected adopted facts |
| `thread_catalog` | array<Continuity Thread projection> | yes | no | `[]` | code | selected adopted Threads |
| `ending_criteria` | array<Continuity Ending projection> | yes | no | `[]` | code | selected Scene-card criteria |
| `new_item_policy` | exact New-item policy | yes | no | none | code | frozen Scene card |
| `delta_contract_rules` | array<Context rule> | yes | no | none | code | nonempty, fixed |
| `context_identity` | Continuity context identity | yes | no | none | code | source hashes |

The Continuity View excludes:

```text
Thread author_truth
Thread resolution_condition
Knowledge-item author_truth
Ending source_ending_text
private non-target Character knowledge
future plan details
persistent-ID counters
```

### 32.1 Continuity target baseline union

Branches:

```text
existing_item_baseline
knowledge_state_baseline
thread_state_baseline
story_clock_baseline
```

Existing-item baseline:

```text
target_kind = existing_item_baseline
target_type
target_id
field_path
current_value
allowed_operations
```

Knowledge-state baseline:

```text
target_kind = knowledge_state_baseline
fact_id
audience_type
audience_id
current_status
allowed_after_statuses
```

Thread-state baseline:

```text
target_kind = thread_state_baseline
thread_id
current_status
current_progress
allowed_operations
target_status
target_progress
```

Story-clock baseline:

```text
target_kind = story_clock_baseline
current_time_label
current_parallel_group_id
allowed_time_relations
target_time_label
target_parallel_group_id
```

Every branch has exact fields only; unknown branch fields are rejected.

### 32.2 Continuity record projections

Character:

```text
record_kind = character
id
name
aliases
role
appearance_anchor
speech_anchor
immutable_facts
```

Relationship:

```text
record_kind = relationship
id
participant_a_id
participant_b_id
relationship_type
public_relation
shared_state
```

World entity:

```text
record_kind = world_entity
id
kind
name
description
immutable_rules
sensory_anchors
```

Temporal rule:

```text
record_kind = temporal_rule
id
kind
description
fixed_rule
```

No private Character goal, pressure, or emotional State is included unless it is the POV Character and needed to interpret the frozen prose; such values are then included in a separate target baseline, not the fixed record projection.

### 32.3 Continuity Knowledge projection

```text
fact_id
subject_type
subject_id
writer_visible_label
selected_audience_states
```

Selected audience state:

```text
audience_type
audience_id
status
```

No `canonical_fact` or `author_truth` is included.

### 32.4 Continuity Thread projection

```text
thread_id
thread_type
description
status
progress
presentation_constraint
```

### 32.5 Continuity Ending projection

```text
criterion_id
description
required
intended_relation
```

### 32.6 Continuity context identity

```text
source_generation_id
scene_id
scene_card_sha256
prose_sha256
```

---

## 33. Private Review view root

Used by all `*-02` review stages.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `reviewed_artifact_role` | enum `reviewed_artifact_role` | yes | no | none | code | stage-compatible |
| `candidate` | Reviewed candidate union | yes | no | none | code | exact candidate bytes/value |
| `candidate_sha256` | SHA-256 | yes | no | none | code | matches candidate |
| `generator_context_ref` | Context snapshot reference | yes | no | none | code | exact generation Context snapshot |
| `generator_context_payload` | one core view payload | yes | no | none | code | same semantic data used to generate candidate |
| `private_author_extensions` | Review private extension | yes | yes | `null` | code | only when required |
| `review_rules` | array<Context rule> | yes | no | none | code | artifact-role-specific |
| `prior_review` | Prior Review projection | yes | yes | `null` | code | included only when reviewing a revised candidate |
| `context_identity` | Review context identity | yes | no | none | code | exact hashes |

### 33.1 Reviewed candidate union

Branches:

```text
json_candidate:
  media_type = application/json
  artifact_role
  value = exact candidate Schema value

text_candidate:
  media_type = text/markdown
  artifact_role = prose
  canonical_text
```

A Review View never contains a diff or partial candidate.

### 33.2 Context snapshot reference

```text
path
sha256
builder_id
operation_id
target_id
```

### 33.3 Review private extension

Branches:

```text
prose_disclosure_extension:
  disclosure_checks
  selected_author_threads
  selected_author_knowledge
  selected_ending_criteria

planning_author_extension:
  selected author projections omitted from generator context by overflow but mandatory for review

continuity_author_extension:
  selected private truth needed to detect contradiction or false persistence

completion_private_extension:
  exact Completion private records
```

A private extension is included only when the reviewer requires it. It is never reused by the generator.

### 33.4 Prior Review projection

```text
candidate_sha256
review_sha256
summary
issues
```

Issues use the exact normalized Issue record. The reviewer must independently reassess the full revised candidate; prior issues are hints, not the only checklist.

### 33.5 Review context identity

```text
candidate_sha256
generator_context_sha256
source_generation_id
prior_review_sha256
```

`prior_review_sha256` is nullable.

---

## 34. Revision view root

Used by INIT-REV, SERIES-REV, VOL-REV, CH-REV, SC-REV, PROSE-REV, DELTA-REV, and VH-REV.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `artifact_role` | enum `reviewed_artifact_role` | yes | no | none | code | stage-compatible |
| `current_candidate` | Reviewed candidate union | yes | no | none | code | latest structurally valid complete candidate |
| `current_candidate_sha256` | SHA-256 | yes | no | none | code | matches candidate |
| `review` | exact saved Review artifact | yes | no | none | code | reviews current candidate hash |
| `generator_context_ref` | Context snapshot reference | yes | no | none | code | original/current generation context |
| `generator_context_payload` | one core view payload | yes | no | none | code | complete task context |
| `revision_round` | integer | yes | no | none | code | one-based, within configuration |
| `replacement_contract_rules` | array<Context rule> | yes | no | none | code | explicitly require whole replacement |
| `context_identity` | Revision context identity | yes | no | none | code | hashes |

Revision context identity:

```text
current_candidate_sha256
review_sha256
generator_context_sha256
revision_round
```

A Revision response must use the exact original candidate Schema or prose-text contract. Patch, diff, instruction list, or omitted unchanged field is structurally invalid.

---

## 35. Volume-handoff view root

Used by VH-01 and VH-REV.

This view is private and reflects the actual end-of-volume adopted generation.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `volume_number` | integer | yes | no | none | code | completed Volume |
| `source_generation_id` | Generation ID | yes | no | none | code | final adopted generation of Volume |
| `volume_design` | exact adopted Volume design | yes | no | none | code | completed Volume |
| `series_current_entry` | exact Series Volume target | yes | no | none | code | completed Volume |
| `series_next_entry` | exact Series Volume target | yes | yes | `null` | code | null for final Volume |
| `characters` | array<Author Character projection> | yes | no | none | code | active/inactive characters relevant to completed/next Volume |
| `relationships` | array<Author Relationship projection> | yes | no | `[]` | code | relevant |
| `threads` | array<Author Thread projection> | yes | no | none | code | all Major plus relevant Supporting Threads |
| `knowledge_items` | array<Author Knowledge projection> | yes | no | `[]` | code | next-volume-relevant facts |
| `story_clock` | exact Story-clock object | yes | no | none | code | final generation |
| `scene_handoffs` | array<Safe previous-handoff projection> | yes | no | none | code | all Chapter-ending/final Scene handoffs selected deterministically |
| `volume_evidence_summary` | array<Private Evidence summary> | yes | no | `[]` | code | relevant adopted evidence |
| `residual_constraints` | array<Safe residual constraint> | yes | no | `[]` | code | relevant unresolved issues |
| `handoff_contract_rules` | array<Context rule> | yes | no | none | code | exact output requirements |

The view excludes:

```text
full Volume prose
raw LLM calls
unadopted candidates
future Volume scene details
unrelated retired supporting records
publication metadata
```

### 35.1 Private Evidence summary

```text
evidence_id
evidence_type
target_type
target_id
target_field
scene_id
relation
quote
```

The quote is private and included only when needed to summarize an actual end-of-volume change.

---

## 36. Completion view root

Used only by COMP-AUDIT.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `precondition` | exact passing Completion-precondition report | yes | no | none | code | all checks pass |
| `brief` | exact adopted Brief | yes | no | none | code | complete |
| `initial_design` | exact adopted Initial-design root | yes | no | none | code | complete |
| `series_map` | exact adopted Series map | yes | no | none | code | complete |
| `final_generation_id` | Generation ID | yes | no | none | code | current HEAD |
| `final_story_clock` | exact Story-clock object | yes | no | none | code | final generation |
| `required_criteria` | array<Completion criterion context> | yes | no | none | code | exactly every required Ending criterion |
| `optional_criteria` | array<Completion criterion context> | yes | no | `[]` | code | every selected optional criterion |
| `required_major_threads` | array<Completion Thread context> | yes | no | none | code | exactly every required Major Thread |
| `volume_handoffs` | array<full private Volume handoff> | yes | no | none | code | one per Volume, canonical order |
| `residual_issues` | array<Completion residual context> | yes | no | `[]` | code | all relevant residual issues |
| `generation_chain` | array<Completion generation summary> | yes | no | none | code | Genesis through final generation |
| `completion_rules` | array<Context rule> | yes | no | none | code | exact assessment rules |

### 36.1 Completion criterion context

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact Ending criterion record | yes | no | none | code | adopted criterion |
| `supporting_evidence` | array<exact Evidence record> | yes | no | `[]` | code | target criterion, relation supports |
| `contradicting_evidence` | array<exact Evidence record> | yes | no | `[]` | code | target criterion, relation contradicts |

### 36.2 Completion Thread context

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `record` | exact Thread record | yes | no | none | code | required Major Thread; private author truth permitted |
| `final_state` | exact Thread state | yes | no | none | code | final generation |
| `evidence` | array<exact Evidence record> | yes | no | `[]` | code | all adopted Thread-state Evidence in order |
| `handoff_mentions` | array<Completion handoff mention> | yes | no | `[]` | code | canonical order |

Completion handoff mention:

```text
volume_number
volume_disposition
safe_summary
handoff_sha256
```

### 36.3 Completion residual context

```text
operation_id
target_id
candidate_sha256
issue_code
severity
category
private_description
adopted_artifact_path
```

### 36.4 Completion generation summary

```text
generation_id
parent_generation_id
commit_id
source_scene_id
current_order
generation_manifest_sha256
scene_manifest_sha256
```

`scene_manifest_sha256` is null for Genesis.

The Completion view includes no raw full manuscript by default. Evidence quotes and Volume handoffs provide the auditable support. A specific adopted prose artifact may be added as a required source only when an Evidence-integrity check identifies a need; its complete canonical text is then included, never an arbitrary excerpt.

---

# Part III: Context rules and residual projections

## 37. Context rule

A Context rule is code-owned immutable instruction data.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `rule_id` | string | yes | no | none | code | `[A-Z][A-Z0-9_]{2,63}`; unique within rules array |
| `description` | string | yes | no | none | code | NFC `1..1000`; testable requirement |
| `severity` | enum `issue_severity` | yes | no | `error` | code | `error` or `warning` |
| `source_contract` | string | yes | no | none | code | repository-relative document and heading identifier |
| `applies_to` | array<string> | yes | no | none | code | nonempty fixed operation/artifact labels |

Rules are sorted by `rule_id`.

No task rule contains credentials, hidden story truth, or dynamic user prose.

---

## 38. Safe residual constraint

A safe residual constraint is derived by code from a private residual Issue.

| field | type | required | nullable | default | creator | validation |
|---|---|---:|---:|---|---|---|
| `source_operation_id` | Stage ID | yes | no | none | code | residual record |
| `source_target_id` | string | yes | no | none | code | residual record |
| `issue_code` | string | yes | no | none | code | residual Issue |
| `category` | enum `issue_category` | yes | no | none | code | residual Issue |
| `constraint` | string | yes | no | none | code | sanitized actionable task constraint |
| `related_ids` | array<persistent ID or Scene ID> | yes | no | `[]` | code | selected IDs only |
| `private_source_sha256` | SHA-256 | yes | no | none | code | residual JSON-line canonical object hash |

The safe constraint excludes author truth, raw Issue prose, review paths, and candidate paths.

---

# Part IV: Operation-specific builders

## 39. Builder permission matrix

| builder | operation/stage | required adopted/frozen sources | payload view | sensitivity |
|---|---|---|---|---|
| `input_brief_builder` | INPUT-02 | Keyword source, Effective profiles | Brief-generation view | `private_author` |
| `init_concept_builder` | INIT-01 | Brief, Effective profiles | Initial-design Concept view | `private_author` |
| `init_people_builder` | INIT-02 | Brief, accepted Concept candidate | Initial-design People view | `private_author` |
| `init_world_builder` | INIT-03 | Brief, accepted Concept/People candidates | Initial-design World view | `private_author` |
| `init_arcs_builder` | INIT-04 | Brief, accepted Concept/People/World candidates | Initial-design Arcs view | `private_author` |
| `init_integrator_builder` | INIT-05 | Brief, all accepted INIT candidates | Initial-design Integration view | `private_author` |
| `series_planner_builder` | SERIES-01 | Brief, Initial design, Genesis generation | Planner Author view | `private_author` |
| `volume_planner_builder` | VOL-01 | Series map, target entry, HEAD, prior handoff | Planner Author view | `private_author` |
| `chapter_planner_builder` | CH-01 | Volume design, target Chapter entry, HEAD, prior handoff | Planner Author view | `private_author` |
| `scene_planner_builder` | SC-01 | Chapter design, target Scene entry, HEAD, prior handoff | Planner Author view | `private_author` |
| `prose_writer_builder` | PROSE-01 | Frozen Scene card, HEAD, safe prior handoff, Editorial profile | Writer view | `writer_safe` |
| `continuity_builder` | DELTA-01 | Frozen Scene card/prose, pre-scene HEAD | Continuity view | `writer_safe` |
| `volume_handoff_builder` | VH-01 | completed Volume design, final HEAD, selected handoffs/Evidence | Volume-handoff view | `private_author` |
| `completion_builder` | COMP-AUDIT | passing precondition, final generation, plans, handoffs, Evidence | Completion view | `private_audit` |
| `review_builder` | every `*-02` | candidate plus generator Context | Private Review view | `private_audit` |
| `revision_builder` | every `*-REV` | candidate, Review, generator Context | Revision view | generator sensitivity or `private_audit` |

A review/revision builder records the generator Context snapshot as a source reference and includes its payload deterministically. It does not rebuild a semantically different source view unless HEAD staleness forces the Pipeline to restart the generation stage.

---

## 40. Planner record-selection rules

### 40.1 Series planning

Mandatory:

```text
all Characters from Initial design
all Relationships from Initial design
all World entities and Temporal rules
all Major Threads
all Ending criteria
all initial Knowledge items
all Genesis State rows
complete Initial-design arcs
```

Optional exclusion order:

```text
1. sensory anchors beyond the first two per World entity
2. inactive nonprimary Relationship private directional detail
3. inactive supporting Character background detail beyond fixed anchors
```

Retired records cannot exist at Genesis.

### 40.2 Volume planning

Mandatory:

```text
target Series entry
all required Major Threads
all required Ending criteria
protagonist and all target Relationships
current Story clock
prior Volume handoff when volume > 1
all records explicitly referenced by target entry/handoff
```

Optional selection includes:

```text
active supporting Characters with series/volume scope
relevant Supporting Threads
target-adjacent World/Temporal records
selected Knowledge items
```

Exclusion order:

```text
1. retired supporting records
2. sensory anchors beyond first two
3. active records outside current/next target scope
4. distant supporting Character private detail
5. resolved optional Supporting-thread detail
```

### 40.3 Chapter planning

Mandatory:

```text
parent Volume design
target Chapter-function entry
protagonist
all target Characters/Relationships/Threads
current Story clock
current State for every target
prior Chapter/Scene handoff
records required by target World/Location constraints
```

Exclusion order:

```text
1. retired records
2. non-target series-scope supporting records
3. sensory anchors beyond first one
4. noncentral Knowledge items
5. distant handoff detail
```

### 40.4 Scene planning

Mandatory:

```text
parent Chapter design
target Scene-function entry
POV and required cast
required Location/World/Temporal records
target Relationships and current State
target Threads including private author truth and resolution condition
target Ending criteria
target Knowledge items
current Story clock
immediately prior safe/private handoff
```

Optional exclusion order:

```text
1. retired records
2. unassigned supporting records
3. sensory anchors beyond first two for current Location and first one elsewhere
4. nonparticipant Character private State
5. non-target Knowledge items
6. distant handoff detail
```

The Scene planner may see author truth to decide what not to reveal. Its output contract forbids secret text in the Scene card.

---

## 41. Writer selection rules

Mandatory:

```text
complete Writer Scene-card projection
POV Character projection
all other participant projections
all Scene-card target Relationships
current Location
all required World and Temporal records
all Scene-card target Threads
all targeted POV/Reader Knowledge facts
all forbidden disclosures
Editorial style projection
immediately prior safe handoff when present
```

Optional additions:

```text
participant-associated visible Relationships
nearby World entities named by required beats
already revealed reader facts preventing repetition
safe active Supporting-thread context
```

Exclusion order:

```text
1. optional sensory anchors beyond first two for current Location and first one elsewhere
2. optional visible World entities not named by beats
3. optional participant-associated Relationships without a Scene target
4. optional already-revealed facts not referenced by the Scene
5. optional safe handoff detail
6. optional non-target Supporting-thread context
```

The builder must never exclude:

```text
POV
required beat
forbidden disclosure
target Thread
target Knowledge transition
required World/Temporal rule
current time/location
style constraints
```

If mandatory Writer data does not fit, generation stops mechanically.

---

## 42. Continuity selection rules

No optional removal is permitted from:

```text
frozen Scene card
frozen prose
every allowed-update target baseline
every record referenced by frozen prose through an authorized target
every targeted Knowledge/Thread/Ending record
new-item policy
delta contract rules
```

Optional catalog additions may be excluded in this order:

```text
1. nonparticipant visible records not mentioned in prose
2. unrelated active World entities
3. unrelated Knowledge labels
4. unrelated Supporting Threads
```

The builder must not summarize or truncate prose. If mandatory data does not fit, DELTA generation stops mechanically.

---

## 43. Review selection rules

Mandatory:

```text
complete reviewed candidate
complete generator Context payload
artifact-specific review rules
source-generation identity
```

For revised candidates:

```text
prior Review
```

is mandatory.

Private extensions are mandatory only for checks that cannot be performed from generator context:

```text
prose forbidden-disclosure detection
plan contradiction against hidden truth
delta contradiction against author truth
Completion private assessment
```

Optional exclusion order inside private extensions:

```text
1. old unrelated Evidence
2. non-target optional Knowledge truth
3. distant Supporting-thread private detail
4. duplicate handoff summaries
```

The complete candidate and generator Context can never be excluded.

---

## 44. Volume-handoff selection rules

Mandatory:

```text
completed Volume design
current and next Series entries
final Story clock
protagonist and target Relationship final States
all Major Thread records and States
all Thread operations performed in the Volume
all next-Volume-required Characters/World records
selected Chapter/final Scene handoffs
relevant residual constraints
```

Exclusion order:

```text
1. retired supporting records unrelated to next Volume
2. sensory anchors
3. resolved optional Supporting-thread detail
4. duplicate Scene-handoff summaries
5. noncentral Knowledge facts
```

Full prose is never included. Evidence summaries are used when exact adopted support matters.

---

## 45. Completion selection rules

Mandatory and never excluded:

```text
passing Completion precondition
Brief
Initial design
Series map
final Story clock
every required Ending criterion
all supports/contradicts Evidence for required criteria
every required Major Thread record and final State
all Evidence for required Major-thread operations
all Volume handoffs
all blocking/publication-warning residual issues
complete generation chain
Completion rules
```

Optional exclusion order:

```text
1. Evidence older than the latest decisive Evidence for optional criteria
2. optional Ending criteria with no Evidence and required=false
3. resolved Supporting-thread detail
4. acceptable nonpublication residual quality issues
5. duplicate handoff summaries
```

A required criterion, required Major Thread, decisive Evidence, or blocking residual issue can never be excluded.

If mandatory Completion context does not fit, COMP-AUDIT stops mechanically. It must not assess completion from a partial mandatory set.

---

# Part V: Overflow, call assembly, and audit

## 46. Overflow algorithm

For one builder:

1. construct the complete mandatory and optional payload;
2. canonicalize it;
3. count the complete rendered call input;
4. if within limit, save snapshot with no token-budget exclusions;
5. otherwise remove the next whole optional item according to the builder's exact exclusion order;
6. append one Context exclusion record;
7. rebuild, canonicalize, and recount;
8. repeat until within limit or no optional item remains;
9. when mandatory data still exceeds the limit, stop mechanically.

Forbidden overflow behavior:

```text
LLM summarization
random selection
reordering exclusion priorities
cutting strings
cutting arrays at an arbitrary byte boundary
dropping required records
silently increasing model limits
using a different tokenizer after failure
retrying with a semantically different view under the same Context hash
```

---

## 47. Complete call-input assembly

The provider input is assembled from:

```text
stage system/developer instructions
stage task prompt
canonical Context payload
structured response Schema instructions when applicable
```

The snapshot root metadata is not blindly copied into prose-facing natural language. The prompt renderer selects required identity fields.

The `input_snapshot_sha256` always identifies the Context snapshot file, not the rendered provider request. The complete redacted provider request has its own hash in the LLM call audit.

Prompt-template version and response-Schema version are stored in both the Context snapshot and applicable audit/manifests.

---

## 48. Context cache and reuse

A Context snapshot may be reused only when all are true:

```text
file hash matches filename
builder version matches
operation/target match
source references still exist and hash correctly
source generation is still the required generation
semantic configuration remains resume-compatible
prompt and response-Schema versions match
```

A stale source generation invalidates reuse.

A change only to resume-mutable logging or audit-retention settings does not change the semantic payload, but the original snapshot retains the Effective-config hash used when it was built. Resume compatibility validation decides whether it remains reusable.

Context snapshots are immutable. Rebuilding produces a new hash-named file.

---

## 49. Context audit fields

The LLM call audit already stores the Context snapshot hash through `input_snapshot_sha256`.

The request body or a code-operation audit must additionally make these values reconstructible:

```text
context_snapshot_path
builder_id
builder_version
view_type
sensitivity
token_count_method
tokenizer_id
hard_input_limit
static_prompt_tokens
payload_tokens
final_input_tokens
excluded item count
overflowed
```

Excluded record IDs and reasons are stored in the Context snapshot, not duplicated as free-form log text.

Normal logs may report only counts and hashes, not private payload values.

---

## 50. Security and secret boundaries

### 50.1 Never included in any Context

```text
credential value
Authorization header
cookie
complete environment dump
absolute path outside workspace
provider secret response metadata
unredacted residual path from outside workspace
```

### 50.2 Never included in Writer or Continuity views

```text
Thread author_truth
Thread resolution_condition
Knowledge-item author_truth
Ending source_ending_text
private non-POV Character goal/pressure/knowledge
future Scene prose
future detailed Volume plan outside current task
raw Review Issue
raw audit body
```

### 50.3 Permitted only in private Author/Review/Completion views

```text
Thread author_truth
Thread resolution_condition
Knowledge-item author_truth
Ending source text
private residual Issue description
private disclosure-check hidden content
Evidence quotes outside current frozen prose
```

### 50.4 Publication

No Context snapshot is copied into publication content.

Publication-safe reports are generated only through the Review/Audit publication projection contract.

---

## 51. Cross-context invariants

A valid Context system satisfies:

```text
snapshot filename hash equals canonical bytes
Candidate manifest input snapshot hash equals snapshot
Review generator-context hash equals reviewed candidate's generation context
Revision review hash targets the current candidate hash
Writer source generation equals frozen Scene-card source generation
Continuity Scene-card/prose hashes equal checkpoint artifacts
Planner persistent IDs resolve in source generation
Writer contains no author-only truth
Continuity contains no author-only truth
Completion contains every required criterion and Major Thread
excluded items follow the exact builder order
mandatory record is never excluded
payload token count is within payload limit
final call input is within hard limit
no snapshot contains an unreferenced unadopted candidate
all source refs hash correctly
same sources and semantic settings produce identical bytes
```

---

## 52. Forbidden deprecated forms

Forbidden:

```text
visible_relationship_state as an undocumented object
array of object with no child Schema
writer known facts containing author_truth
writer known facts containing raw canonical_fact
scene card copied wholesale into Writer View
allowed_update_targets sent as prose writing instructions
one generic context object for every stage
Context Builder calling an LLM
context_hash stored inside its own hashed file
created_at inside deterministic snapshot
cutting JSON to fit
raw candidate included outside Review/Revision/explicit INIT dependency
completion audit over partial required criteria
```

Use the exact view and projection contracts in this document.

---

## 53. Mechanical acceptance conditions

An implementation of this contract is acceptable only when tests demonstrate:

```text
Context-snapshot canonical hash and hash-named path
absence of timestamp self-instability
source-reference hash validation
exact view-type discriminated union
Brief-generation view
all five Initial-design stage views
Series/Volume/Chapter/Scene Planner Author views
Writer Scene-card safe projection
POV and visible non-POV Character separation
Writer Relationship private-field filtering
Writer Knowledge author-truth exclusion
safe forbidden-disclosure projection
safe previous-handoff projection
Continuity exact prose inclusion
Continuity allowed-target baselines
Continuity author-truth exclusion
private Review generator-context equality
private prose disclosure extension
whole-candidate Revision view
Volume-handoff private view
Completion required criterion coverage
Completion required Major-thread coverage
deterministic record selection
deterministic optional exclusion
mandatory-overflow stop
no string or JSON truncation
precise tokenizer priority
fallback-estimate behavior
final rendered-input hard-limit check
Context cache reuse and stale-generation rejection
resume-mutable config compatibility
secret and absolute-path rejection
Writer/publication private-truth rejection
unknown-field rejection
```
