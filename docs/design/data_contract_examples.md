# Data contract examples and fixture index

This document is the normative index and authoring contract for Storycraft data examples and acceptance fixtures.

It defines:

- which examples are exact persisted artifacts;
- which examples are explanatory fragments only;
- canonical JSON and text hashing rules used by fixtures;
- the fixture chain and baseline identities;
- exact small hash anchors;
- required complete fixture documents and file inventories;
- stable positive-example and negative-mutation IDs;
- cross-fixture Generation, Scene-order, Handoff, Evidence, and Publication invariants;
- rules that prevent examples from drifting away from the active contracts.

Field authority remains in:

- [`contracts/data/brief_and_initial.md`](contracts/data/brief_and_initial.md)
- [`contracts/data/planning_artifacts.md`](contracts/data/planning_artifacts.md)
- [`contracts/data/scene_artifacts.md`](contracts/data/scene_artifacts.md)
- [`contracts/data/review_and_audit.md`](contracts/data/review_and_audit.md)
- [`contracts/ledger/canon_records.md`](contracts/ledger/canon_records.md)
- [`contracts/ledger/story_state.md`](contracts/ledger/story_state.md)
- [`contracts/ledger/evidence_and_updates.md`](contracts/ledger/evidence_and_updates.md)
- [`contracts/ledger/runtime_records.md`](contracts/ledger/runtime_records.md)
- [`context_contracts.md`](context_contracts.md)
- [`workspace_layout.md`](workspace_layout.md)
- [`implementation_acceptance.md`](implementation_acceptance.md)

When an example conflicts with a field contract, the field contract is authoritative and the example must be corrected before release.

---

## 1. Example classes

Every example is classified as exactly one of these classes.

### 1.1 Exact persisted artifact

An exact persisted artifact:

- represents the complete JSON or text bytes stored at one canonical workspace path;
- includes every required field;
- includes explicit nullable fields when the Schema requires them;
- contains no unknown field;
- satisfies every local conditional rule;
- has a canonical SHA-256 when the fixture records one;
- can be copied into a test workspace without adding story-semantic fields.

Exact persisted artifacts are marked:

```text
EXACT ARTIFACT
```

### 1.2 Exact provider response

An exact provider response:

- is the complete accepted LLM response before code-owned metadata is added;
- follows the exact response Schema or prose response contract;
- contains no code-owned IDs, hashes, timestamps, paths, counters, or routing fields;
- can be passed directly to the production structural validator.

Exact provider responses are marked:

```text
EXACT RESPONSE
```

### 1.3 Exact canonical value

An exact canonical value is a complete child object or root value used as a serialization/hash anchor.

It may not by itself be a complete story workspace artifact.

Example:

```text
the empty current-canon root {"records":[]}
```

is an exact root value but is not a valid populated Genesis for the lighthouse story.

These are marked:

```text
EXACT VALUE
```

### 1.4 Explanatory fragment

An explanatory fragment illustrates a subset of fields or a branch relationship.

It must be marked:

```text
FRAGMENT — NOT A PERSISTED ARTIFACT
```

A fragment:

- has no fixture SHA-256;
- is not placed in a `json` fenced block;
- is not accepted by fixture-generation tools as a complete artifact;
- cannot be used to satisfy an acceptance test.

### 1.5 Invalid mutation

An invalid mutation begins from one named valid example and applies one defined change.

It is marked with a stable ID:

```text
EX-NEG-...
```

Invalid mutations are shown as text/diff instructions, not as `json` blocks that documentation tooling could mistake for valid fixtures.

---

## 2. Canonical JSON bytes

All exact JSON hash anchors use the Runtime canonical JSON rules.

For the examples in this document, the byte algorithm is:

1. recursively normalize every string to Unicode NFC;
2. reject nonfinite numbers;
3. sort object keys by Unicode code-point order;
4. preserve contract-normalized array order;
5. encode JSON with:
   ```text
   ensure_ascii = false
   separators = (",", ":")
   ```
6. encode as UTF-8 without BOM;
7. append exactly one LF byte;
8. calculate SHA-256 over the complete bytes including that LF.

Conceptual reference:

```python
canonical_bytes = (
    json.dumps(
        nfc_normalized_value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    + "\n"
).encode("utf-8")
```

This snippet explains fixture construction. Production tests must call the production canonical serializer rather than maintaining a separate permissive implementation.

### 2.1 Arrays

`sort_keys=true` does not sort arrays.

Every array must first be normalized by its owning contract.

Examples:

| array | required order |
|---|---|
| Canon records | Canon record-type registry, then persistent ID |
| Story-state rows | owning persistent ID and audience tuple rules |
| Evidence records | Evidence ID |
| normalized Review issues | severity, category, role, location, code |
| Candidate update arrays | contract-specific target/local-key order |
| planning targets | dramatic/numeric plan order |
| Publication file references | `relative_path` |
| Context source references | source-role registry, then path |

### 2.2 Hashes inside objects

A fixture generator must construct objects in dependency order.

It must not use:

```text
64 zeroes
64 ones
"TODO"
"placeholder"
"hash-of-this-object" inside the same object
```

unless a contract explicitly defines a zero-like constant, which these artifact hashes do not.

### 2.3 Self-hash prohibition

The following do not contain their own file hash:

```text
Context snapshot
Generation manifest
Publication manifest
Publication Validation
Publication Gate
```

External manifests or filenames carry the applicable hashes.

---

## 3. Canonical text bytes

### 3.1 Prose

Canonical frozen/adopted prose:

- is UTF-8;
- is NFC;
- uses LF line endings;
- has exactly one final LF;
- contains no BOM;
- follows the prose-only Markdown restrictions;
- is hashed byte-for-byte.

### 3.2 Pointer files

Valid pointer bytes:

```text
canon/HEAD:
  <generation-id>\n

output/CURRENT:
  <publication-id>\n
```

No JSON quoting is used.

### 3.3 JSON Lines

`audit/residual-issues.jsonl` uses:

- one canonical JSON object per line;
- exactly one LF after each object;
- append-only ordering;
- no array wrapper.

---

## 4. Fixture chain

The canonical lighthouse acceptance story is divided into complete fixture baselines.

```text
lighthouse-input-and-genesis-v3
  ↓
lighthouse-planning-v3
  ↓
lighthouse-scene-commit-v3
  ↓
lighthouse-final-scene-v3
  ↓
lighthouse-final-handoff-v3
  ↓
lighthouse-completion-publication-v3
```

### 4.1 Fixture document ownership

| fixture scope | required document |
|---|---|
| input, Initial design, Genesis, Series/Volume/Chapter planning | [`examples/initial_and_planning_fixture.md`](examples/initial_and_planning_fixture.md) |
| one complete representative Scene checkpoint and Scene commit | [`examples/scene_commit_fixture.md`](examples/scene_commit_fixture.md) |
| final Scene, final Handoff generation, Completion, Publication | [`examples/completion_publication_fixture.md`](examples/completion_publication_fixture.md) |

Those documents must be replaced together with this index when fixture version changes.

### 4.2 Baseline reference

A fixture document may refer to an earlier baseline by:

```text
baseline_fixture_id
baseline_inventory_sha256
```

It must not duplicate a large baseline root and then allow the copies to drift.

A test fixture builder resolves the baseline reference and applies the exact documented new transaction.

### 4.3 Fixture version

The suffix:

```text
-v3
```

means the fixture follows the contracts that include:

```text
versioned candidate directories
Context snapshots
checkpoint phases
committed continuity delta
volume_handoff Commit/Generation
payload_set_sha256
rename-stable Publication Gate
```

Legacy `-v1` and `-v2` fixture IDs are not active.

---

## 5. Lighthouse story seed

The canonical fixture story is:

```text
title:
  岬の灯

genre:
  海洋幻想譚

Volumes:
  4

protagonist:
  澪

key person:
  凪

central durable question:
  灯台停止の原因と、町が灯を共同で守る仕組み

required ending:
  町が灯を守る意思を持ち、澪と凪が再点灯を見届ける
```

The story is intentionally small in cast and Canon breadth while still exercising:

```text
Character and Relationship State
Location and temporal rule
required Major Thread
Ending criterion
Knowledge item and audience State
Evidence quote/offset/hash
Scene checkpoint and Commit
four Volume Handoff commits
Completion criterion/Thread assessment
Publication Validation/Manifest/Gate
```

---

# Part I: Exact small anchors

## 6. Keyword source anchor

Classification:

```text
EXACT ARTIFACT
path = input/keywords.json
example_id = EX-POS-INPUT-001
```

```json
{"avoid":["主人公だけが全責任を負う結末","説明だけで謎を解決する場面"],"ending_hint":"町が灯を守る意思を持つ","genre_hint":"海洋幻想譚","keywords":["灯台","海","失われた鍵","町の共同責任"],"notes":"四巻構成。各巻で局所的な解決を置き、最終巻で灯台の再点灯と町の意思決定を完結させる。","title_hint":"岬の灯","volumes_hint":4}
```

Canonical SHA-256:

```text
cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f
```

Required mutation tests:

```text
EX-NEG-INPUT-001:
  append duplicate keyword "灯台"
  expected: Keyword-source uniqueness failure

EX-NEG-INPUT-002:
  set volumes_hint = 3
  expected: 4..10 range failure

EX-NEG-INPUT-003:
  add field "profile_id"
  expected: unknown-field failure
```

---

## 7. Brief content response anchor

Classification:

```text
EXACT RESPONSE
operation = INPUT-02
example_id = EX-POS-INPUT-002
```

```json
{"avoid":["主人公だけが全責任を負う結末","説明だけで謎を解決する場面"],"ending":"町が灯を守る意思を持ち、澪と凪が再点灯を見届ける","genre":"海洋幻想譚","key_people":[{"initial_relation_to_protagonist":"疎遠になった幼なじみ","name":"凪","present_position":"港の修理工"}],"protagonist":{"core_trait":"粘り強い","current_pressure":"日没までに停止原因を特定する必要がある","initial_wish":"家業としてではなく自分の意思で灯を守りたい","name":"澪","present_position":"岬の灯台守見習い"},"target_reader":"成人読者","title":"岬の灯","volumes":4,"want":"停止した灯台の原因を追い、町全体が灯を守る仕組みを作る"}
```

Canonical response SHA-256:

```text
db953c0f83fa420abfc618368f8531059c57af71112e70f3aeb21506dbfbe24e
```

The provider response must not include:

```text
brief_version
editorial_profile_id
publishing_profile_id
source_type
source_hash
created_at
```

Required mutation tests:

```text
EX-NEG-INPUT-004:
  add editorial_profile_id
  expected: unknown-field failure

EX-NEG-INPUT-005:
  remove one Keyword-source avoid item
  expected: INPUT-02 conditional validation failure

EX-NEG-INPUT-006:
  set volumes = 5
  expected: non-null volumes_hint equality failure
```

---

## 8. Adopted Brief anchor

Classification:

```text
EXACT ARTIFACT
path = input/brief.json
example_id = EX-POS-INPUT-003
```

```json
{"avoid":["主人公だけが全責任を負う結末","説明だけで謎を解決する場面"],"brief_version":"1.0","created_at":"2026-07-22T00:00:00Z","editorial_profile_id":"default-ja","ending":"町が灯を守る意思を持ち、澪と凪が再点灯を見届ける","genre":"海洋幻想譚","key_people":[{"initial_relation_to_protagonist":"疎遠になった幼なじみ","name":"凪","present_position":"港の修理工"}],"protagonist":{"core_trait":"粘り強い","current_pressure":"日没までに停止原因を特定する必要がある","initial_wish":"家業としてではなく自分の意思で灯を守りたい","name":"澪","present_position":"岬の灯台守見習い"},"publishing_profile_id":"kdp-ja-v1","source_hash":"cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f","source_type":"keywords","target_reader":"成人読者","title":"岬の灯","volumes":4,"want":"停止した灯台の原因を追い、町全体が灯を守る仕組みを作る"}
```

Canonical SHA-256:

```text
75551dbb434d9a71ac64590282dd697d5c2bd79471a9e0c7c52c5ff17d335fc7
```

Cross-hash invariant:

```text
adopted_brief.source_hash
=
SHA-256(input/keywords.json canonical bytes)
=
cce770d65d44faf242ecb2eafbf082ddfcf50d5ab813ed6cc6d35d765384728f
```

---

## 9. Empty root serialization anchors

These are exact root values used to test canonical file names and serialization.

They are not a complete lighthouse Genesis.

### 9.1 Empty current Canon

Classification:

```text
EXACT VALUE
example_id = EX-POS-HASH-001
```

```json
{"records":[]}
```

SHA-256:

```text
d019f9c5cf72905427dac4571bd71052a1c6ac1c52c8fd1fb163243cdaec7c89
```

### 9.2 Empty Knowledge items

Classification:

```text
EXACT VALUE
example_id = EX-POS-HASH-002
```

```json
{"items":[]}
```

SHA-256:

```text
e813d564bccbeefe1db875d1c9abb55d63c52b639acc61134a5f1d19cc489b67
```

### 9.3 Empty Evidence index

Classification:

```text
EXACT VALUE
example_id = EX-POS-HASH-003
```

```json
{"records":[]}
```

SHA-256:

```text
d019f9c5cf72905427dac4571bd71052a1c6ac1c52c8fd1fb163243cdaec7c89
```

Important:

```text
current-canon and Evidence-index empty roots have identical bytes and hash
because both exact roots are {"records":[]}
```

File role and path, not hash alone, identify which artifact the bytes represent.

Required mutation tests:

```text
EX-NEG-HASH-001:
  use {"items":[]} for current-canon
  expected: root-Schema failure

EX-NEG-HASH-002:
  save Evidence index as evidence-index.jsonl
  expected: workspace-layout/file-set failure

EX-NEG-HASH-003:
  pretty-print an otherwise equal root
  expected: canonical-byte hash mismatch
```

---

## 10. Genesis Story-clock anchor

Classification:

```text
EXACT VALUE
example_id = EX-POS-STATE-001
```

```json
{"current_chapter_number":null,"current_order":0,"current_scene_number":null,"current_volume_number":null,"last_scene_id":null,"parallel_group_id":null,"time_label":"初日の夕方"}
```

Canonical SHA-256:

```text
92a704f5a0aac6465ae1495610c722d1c576f5070a90dff3450656d5ee41ee73
```

Required conditions:

```text
current_order = 0
all position fields = null
last_scene_id = null
time_label may be non-null from accepted initial temporal design
```

Required mutation tests:

```text
EX-NEG-STATE-001:
  set current_scene_number = 1 while last_scene_id = null
  expected: Story-clock consistency failure

EX-NEG-STATE-002:
  set current_order = 1 at Genesis
  expected: Genesis clock failure

EX-NEG-STATE-003:
  add world_states to Story-state root
  expected: unknown root field
```

---

## 11. Empty Review response anchor

Classification:

```text
EXACT RESPONSE
operation = any *-02 Review stage
example_id = EX-POS-REVIEW-001
```

```json
{"issues":[],"summary":"契約・整合性・開示境界に重大な問題はありません。"}
```

Canonical response SHA-256:

```text
5eeef0b0accd57a9732458567a45963516ce390f9158fe5589e57652a278a9eb
```

Code derives:

```text
issue_counts.error = 0
issue_counts.warning = 0
issue_counts.total = 0
review_status = issues_empty
```

The LLM does not return those fields.

---

## 12. Review issue response anchor

Classification:

```text
EXACT RESPONSE
operation = PROSE-02
example_id = EX-POS-REVIEW-002
```

```json
{"issues":[{"artifact_role":"prose","category":"disclosure","code":"DISCLOSURE_HIDDEN_FACT","description":"凍結Scene cardで開示が許可されていない停止原因を本文が断定しています。","evidence_ids":[],"location":{"json_pointer":null,"location_type":"text_quote","note":null,"related_artifact_roles":[],"text_quote":"予備鍵が停止原因だった"},"related_ids":["thread-000001"],"rule_id":"CTX-WRITER-NO-AUTHOR-TRUTH","severity":"error","suggested_change":"原因を示唆する観察へ置き換え、確定情報としては書かないでください。"}],"summary":"本文は概ね成立していますが、読者へ未開示の事実を断定しています。"}
```

Canonical response SHA-256:

```text
d5795ae828a123928e61940dad1d3c0b3952562a0b5904660cdc9f3f66f1f344
```

After normalization, code adds:

```text
issue_id = issue-0001
Review operation/target/candidate identity
candidate_version
input_snapshot_sha256
issue_counts
review_status = issues_found
call_id
created_at
```

Required mutation tests:

```text
EX-NEG-REVIEW-001:
  severity = info
  expected: enum failure

EX-NEG-REVIEW-002:
  location_type = text_quote and text_quote = null
  expected: conditional-location failure

EX-NEG-REVIEW-003:
  add next_stage to LLM response
  expected: unknown-field/adoption-authority failure

EX-NEG-REVIEW-004:
  text_quote does not occur in canonical reviewed prose
  expected: target-location validation failure
```

---

## 13. Empty-change continuity candidate anchor

Classification:

```text
EXACT ARTIFACT
path shape = runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json
example_id = EX-POS-DELTA-001
```

This is valid only for a frozen Scene whose prose creates no persistent change and whose Scene card authorizes no required persistent update.

```json
{"delta_status":"candidate","ending_evidence_proposals":[],"existing_item_updates":[],"handoff_summary":"澪と凪は修理庫の扉を確認したが、永続化すべき状態変化は生じなかった。","knowledge_item_proposals":[],"knowledge_updates":[],"new_item_proposals":[],"scene_id":"v01-c001-s001","schema_version":"1.0","thread_updates":[],"time_update":null}
```

Canonical SHA-256:

```text
7cd5bc5729682364be6e9b743ebf134491aecd71eeefa482e5e63a4a05388be1
```

This artifact contains no:

```text
persistent new ID
Evidence ID
Commit ID
Generation ID
offset
quote hash
prose hash
timestamp
```

---

## 14. Empty-change committed delta anchor

Classification:

```text
EXACT ARTIFACT
path shape = artifacts/scenes/v01/c001/s001/continuity-delta.json
example_id = EX-POS-DELTA-002
```

```json
{"delta_status":"committed","ending_evidence":[],"existing_item_updates":[],"handoff_summary":"澪と凪は修理庫の扉を確認したが、永続化すべき状態変化は生じなかった。","knowledge_item_adoptions":[],"knowledge_updates":[],"new_item_adoptions":[],"scene_id":"v01-c001-s001","schema_version":"1.0","thread_updates":[],"time_update":null}
```

Canonical SHA-256:

```text
9f5022f3ae3b11a1b39d969a1ac6dd47df3a45b9b1a08f8d4d48fa7e3f907397
```

Candidate/committed distinction:

| candidate | committed |
|---|---|
| `new_item_proposals` | `new_item_adoptions` |
| `knowledge_item_proposals` | `knowledge_item_adoptions` |
| `ending_evidence_proposals` | `ending_evidence` |
| Evidence proposals | resolved Evidence IDs |
| unresolved local keys allowed under rules | no unresolved local key |
| `delta_status=candidate` | `delta_status=committed` |

---

## 15. Evidence offset anchor

Classification:

```text
EXACT VALUE
example_id = EX-POS-EVID-001
```

Canonical prose bytes:

```text
澪は錆びた鍵を掌に置いた。町の人々は灯を守ると決めた。\n
```

Canonical prose SHA-256:

```text
f23621f9b7f0064818a6b31ecc5d7a51c01ad18c74d783b0363e68f06d52620c
```

Evidence quote:

```text
町の人々は灯を守ると決めた
```

Code-point coordinates:

```text
start_offset = 13
end_offset = 26
character_count excluding final LF = 27
```

Quote SHA-256:

```text
b38e6db8a2324c7884cf5ed340b259345428ec9ceac085af8397cbd0274022eb
```

Required test:

```python
canonical_prose[start_offset:end_offset] == quote
```

The offsets are Unicode code-point indices, not UTF-8 byte offsets.

Required mutation tests:

```text
EX-NEG-EVID-001:
  use UTF-8 byte offset 39 instead of code-point offset 13
  expected: quote-slice failure

EX-NEG-EVID-002:
  duplicate the quote in the prose
  expected: unique-occurrence failure

EX-NEG-EVID-003:
  use a paraphrase as quote
  expected: zero-occurrence failure

EX-NEG-EVID-004:
  calculate prose hash without final LF
  expected: prose hash mismatch
```

---

# Part II: Complete fixture responsibilities

## 16. Initial and planning fixture

The complete fixture document must define:

```text
fixture_id = lighthouse-input-and-genesis-v3
planning_fixture_id = lighthouse-planning-v3
```

It owns complete exact artifacts for:

```text
input/keywords.json
input/brief.json

accepted INIT-01 Concept response
accepted INIT-02 People response
accepted INIT-03 World response
accepted INIT-04 Arcs response
accepted INIT-05 integrated bundle
accepted INIT-06 Review
Genesis local-key mapping

canon/initial-design.json
canon/generations/00000000/current-canon.json
canon/generations/00000000/knowledge-items.json
canon/generations/00000000/story-state.json
canon/generations/00000000/evidence-index.json
canon/generations/00000000/commit-manifest.json
canon/generations/00000000/generation-manifest.json
canon/HEAD

plans/series-map.json
plans/volumes/v01/volume-design.json
plans/volumes/v01/chapters/c001/chapter-design.json
```

It must also include:

```text
canonical SHA-256 for every exact artifact
all local-key-to-persistent-ID mappings
parent/source hashes
required Major Thread and Ending IDs
the initial Knowledge-item and sparse State
the expected initial Runtime counters after Genesis/planning calls
```

It must not include:

```text
flat plan paths
Relationship field named origin
empty or incomplete Character/Relationship State
evidence-index.jsonl
placeholder hashes
same generic INIT root repeated for INIT-01..04
```

---

## 17. Representative Scene-commit fixture

The complete fixture document must define:

```text
fixture_id = lighthouse-scene-commit-v3
baseline_fixture_id = lighthouse-planning-v3
scene_id = v01-c001-s001
```

It owns:

```text
SC-01 response
saved normalized Scene-card Review
frozen Scene card
Writer Context snapshot
PROSE response
prose Review
frozen prose
Continuity Context snapshot
DELTA response
normalized candidate delta
Delta Review
Commit plan
merge plan
allocated mappings
staged after roots
committed delta
Evidence records
Scene manifest
Scene Commit manifest
Scene Generation manifest
adopted Scene directory inventory
canon/HEAD after commit
Run-state postcondition
```

The representative Scene must exercise at least:

```text
one Relationship-State update
one Thread advance
one Knowledge transition
one Evidence quote
one Story-clock position update
no new persistent record
```

The fixture must prove:

```text
checkpoint Scene card/prose byte equality with adopted files
candidate before values equal baseline HEAD
all updates are Scene-card authorized
Evidence quote is unique
committed delta and after roots correspond in both directions
Scene manifest uses artifacts/scenes/... final paths
```

---

## 18. Final Scene and final Handoff fixture

The Completion fixture document must include a final Scene baseline with:

```text
scene_id = v04-c003-s002
final Scene current_order = 47
final Scene Commit/Generation = 00000050
parent Generation = 00000049
```

After VH-ID:

```text
final Handoff path = artifacts/handoffs/v04.json
final Handoff Commit/Generation = 00000051
parent Generation = 00000050
canon/HEAD = 00000051
story_clock.current_order = 47
story_clock.last_scene_id = v04-c003-s002
story_clock.time_label = 最終日の夜
```

The Handoff generation changes only:

```text
thread_states[].volume_disposition
```

For every required Major Thread:

```text
status = resolved
progress = 4
volume_disposition = resolve
```

---

## 19. Completion and Publication fixture

The complete fixture document owns:

```text
Completion precondition
Completion Context identity
Completion valid attempt
accepted private Completion audit
publication-safe Completion report
Publication payload file references
payload_set_sha256
Publication Validation
Publication Manifest
content_set_sha256
Publication Gate
publication_snapshot_sha256
publications/<id>/ inventory
output/CURRENT
completed Run state
```

A success fixture requires:

```text
Completion overall_assessment = complete
Publication validation_status = pass
Gate gate_status = pass
output/CURRENT = publication ID
Run last_completed_stage = OUT-03
Run run_status = completed
```

It must prove rename stability:

```text
Gate snapshot calculated under:
  .staging/publication/<id>/

equals Gate snapshot recalculated under:
  publications/<id>/
```

No Gate or final Manifest field stores either root prefix.

---

# Part III: Cross-fixture arithmetic

## 20. Scene distribution

The canonical success fixture contains 47 adopted Scene commits.

Distribution:

| Volume | Chapter Scene counts | Volume Scene total |
|---:|---|---:|
| 1 | `3 + 3 + 3 + 3` | 12 |
| 2 | `3 + 3 + 3 + 3` | 12 |
| 3 | `4 + 4 + 3` | 11 |
| 4 | `5 + 5 + 2` | 12 |
| total |  | 47 |

The final coordinate is therefore:

```text
v04-c003-s002
```

### 20.1 Story order

Each Scene commit increments:

```text
story_clock.current_order
successful_scene_commits
```

exactly once.

Therefore the final value is:

```text
47
```

### 20.2 Handoff commits

Each completed Volume creates one `volume_handoff` Commit/Generation.

Handoff commits:

- do not increment `current_order`;
- do not increment `successful_scene_commits`;
- do consume Commit/Generation IDs.

### 20.3 Generation arithmetic

Starting from Genesis `00000000`:

| event | Scene commits | Handoff commits | resulting Generation |
|---|---:|---:|---:|
| Genesis | 0 | 0 | `00000000` |
| end Volume 1 Scene | 12 | 0 | `00000012` |
| Volume 1 Handoff | 12 | 1 | `00000013` |
| end Volume 2 Scene | 24 | 1 | `00000025` |
| Volume 2 Handoff | 24 | 2 | `00000026` |
| end Volume 3 Scene | 35 | 2 | `00000037` |
| Volume 3 Handoff | 35 | 3 | `00000038` |
| final Scene | 47 | 3 | `00000050` |
| final Volume Handoff | 47 | 4 | `00000051` |

Formula after final Handoff:

```text
Generation numeric suffix
=
successful Scene commits
+
adopted Volume Handoff commits

51 = 47 + 4
```

This is why:

```text
Generation ID != Story-clock current_order
```

after the first Volume Handoff.

---

## 21. Required persistent IDs

The fixture documents use stable IDs at least for:

```text
char-000001:
  澪

char-000002:
  凪

rel-000001:
  澪と凪の主要Relationship

loc-000001:
  岬の灯台

item-000001:
  予備鍵

rule-000001:
  灯台の点灯時刻に関するTemporal rule

thread-000001:
  灯台停止の原因を解決するrequired Major Thread

ending-000001:
  町が灯を守る意思を持つEnding criterion

fact-000001:
  予備鍵と停止原因の関係に関するKnowledge item
```

The exact record and State fields live in the complete fixture documents.

Legacy fixture ID:

```text
time-000001
```

is forbidden. Temporal rules use:

```text
rule-000001
```

---

## 22. Evidence identity

The fixtures do not require one Evidence record per Scene.

Evidence IDs follow actual committed proposals and may not numerically equal Scene order.

Requirements:

```text
every Evidence ID is allocated by code
every Evidence record points to one adopted Scene
every quote/hash/offset validates
every committed-delta evidence_ids value exists
every Completion support/contradiction Evidence ID exists
```

A fixture must not derive Evidence ID from:

```text
Scene number
current_order
Generation ID
array index without counter allocation
```

---

## 23. Commit types

Fixture chains must exercise all Commit branches.

| branch | required example |
|---|---|
| `initial_design` | Genesis `commit-00000000` |
| `scene` | representative Scene and final Scene |
| `volume_handoff` | at least Volume 1 and final Volume 4 Handoff |

Conditional fields must match the Runtime commit-type matrix.

A fixture may not reuse a Scene Commit manifest and merely change `commit_type` to `volume_handoff`.

---

# Part IV: Positive example catalogue

## 24. Positive example IDs

The complete fixture set must provide at least these stable example IDs.

### Input and Initial

```text
EX-POS-INPUT-001  Keyword source
EX-POS-INPUT-002  Brief content response
EX-POS-INPUT-003  adopted Brief
EX-POS-INIT-001   INIT-01 Concept
EX-POS-INIT-002   INIT-02 People
EX-POS-INIT-003   INIT-03 World
EX-POS-INIT-004   INIT-04 Arcs/Threads/Ending/Knowledge
EX-POS-INIT-005   INIT-05 integrated bundle
EX-POS-INIT-006   saved empty-issue Initial Review
EX-POS-INIT-007   Genesis local-key mapping
EX-POS-INIT-008   Genesis Commit
EX-POS-INIT-009   Genesis Generation
EX-POS-INIT-010   adopted initial-design snapshot
```

### Canon and State

```text
EX-POS-CANON-001  Character record
EX-POS-CANON-002  Relationship record using relationship_origin
EX-POS-CANON-003  World Location record
EX-POS-CANON-004  Temporal-rule record using rule ID
EX-POS-CANON-005  required Major Thread
EX-POS-CANON-006  required Ending criterion
EX-POS-CANON-007  Knowledge item
EX-POS-STATE-001  Genesis Story clock
EX-POS-STATE-002  Character State
EX-POS-STATE-003  directional Relationship State
EX-POS-STATE-004  open Major Thread State
EX-POS-STATE-005  sparse nondefault Knowledge State
```

### Planning

```text
EX-POS-PLAN-001   Series map
EX-POS-PLAN-002   Series Volume target
EX-POS-PLAN-003   Volume design
EX-POS-PLAN-004   Chapter function
EX-POS-PLAN-005   Chapter design
EX-POS-PLAN-006   Scene function
```

### Scene and Commit

```text
EX-POS-SCENE-001  SC-01 response
EX-POS-SCENE-002  frozen Scene card
EX-POS-SCENE-003  Writer Context snapshot
EX-POS-SCENE-004  canonical prose
EX-POS-SCENE-005  Continuity Context snapshot
EX-POS-DELTA-001  empty-change candidate delta anchor
EX-POS-DELTA-002  empty-change committed delta anchor
EX-POS-DELTA-003  representative changing candidate delta
EX-POS-DELTA-004  representative committed delta
EX-POS-EVID-001   Evidence offset anchor
EX-POS-EVID-002   adopted Evidence record
EX-POS-COMMIT-001 Commit plan
EX-POS-COMMIT-002 merge plan
EX-POS-COMMIT-003 Scene Commit manifest
EX-POS-COMMIT-004 Scene Generation manifest
EX-POS-COMMIT-005 Scene manifest
```

### Review, Handoff, Completion, Publication

```text
EX-POS-REVIEW-001 empty Review response
EX-POS-REVIEW-002 issue Review response
EX-POS-REVIEW-003 normalized saved Review
EX-POS-VH-001     Volume Handoff response
EX-POS-VH-002     normalized Handoff candidate
EX-POS-VH-003     adopted Handoff
EX-POS-VH-004     Handoff Commit
EX-POS-VH-005     Handoff Generation
EX-POS-COMP-001   passing Completion precondition
EX-POS-COMP-002   Completion response
EX-POS-COMP-003   accepted private Completion audit
EX-POS-COMP-004   publication-safe report
EX-POS-PUB-001    payload file-reference set
EX-POS-PUB-002    passing Publication Validation
EX-POS-PUB-003    final Publication manifest
EX-POS-PUB-004    passing Gate
EX-POS-PUB-005    CURRENT pointer
```

---

# Part V: Negative mutation catalogue

## 25. General mutation rule

Each invalid example:

1. names one exact positive base example;
2. applies one principal mutation;
3. states the expected validation layer;
4. states whether a provider retry, semantic revision, mechanical stop, or recovery action occurs;
5. does not silently include unrelated mutations.

A test may combine mutations only for a separate defense-in-depth scenario.

---

## 26. Schema mutations

```text
EX-NEG-SCHEMA-001
base:
  any exact structured artifact
mutation:
  add unknown_field = true
expected:
  exact-Schema rejection
  no candidate/adopted artifact written

EX-NEG-SCHEMA-002
base:
  numeric count field
mutation:
  replace integer 1 with boolean true
expected:
  strict numeric-type rejection

EX-NEG-SCHEMA-003
base:
  required nullable field
mutation:
  omit field instead of setting null
expected:
  missing-required-field rejection

EX-NEG-SCHEMA-004
base:
  discriminated-union branch
mutation:
  include a field from another branch
expected:
  branch unknown-field rejection
```

---

## 27. Canon and State mutations

```text
EX-NEG-CANON-001
base:
  Relationship record
mutation:
  use field origin instead of relationship_origin
expected:
  unknown-field rejection

EX-NEG-CANON-002
base:
  Temporal rule
mutation:
  ID = time-000001
expected:
  persistent-ID registry failure

EX-NEG-CANON-003
base:
  required Major Thread
mutation:
  scope = volume
expected:
  Major Thread invariant failure

EX-NEG-CANON-004
base:
  Scene new-item proposal
mutation:
  proposal_type = ending_criterion
expected:
  forbidden Scene creation type

EX-NEG-STATE-004
base:
  required Major Thread State
mutation:
  status = retired
expected:
  required-Major retirement failure

EX-NEG-STATE-005
base:
  Knowledge State
mutation:
  explicit Character status = unknown
expected:
  sparse-default-row rejection

EX-NEG-STATE-006
base:
  Scene continuity update
mutation:
  target thread_state.volume_disposition
expected:
  field ownership/authorization rejection
```

---

## 28. Candidate and Review mutations

```text
EX-NEG-CAND-001
base:
  v0001 candidate
mutation:
  overwrite candidate bytes after Review
expected:
  candidate hash mismatch; version invalidated

EX-NEG-CAND-002
base:
  valid revised content
mutation:
  save into v0001 instead of new v0002
expected:
  immutable-version/path failure

EX-NEG-CAND-003
base:
  candidate directory
mutation:
  delete candidate-manifest.json
expected:
  quarantine/regenerate; candidate file not promoted

EX-NEG-CAND-004
base:
  Candidate manifest
mutation:
  point candidate_path outside its version directory
expected:
  manifest path containment failure

EX-NEG-REVIEW-005
base:
  valid Review with issue
mutation:
  include corrected_candidate object
expected:
  unknown-field failure

EX-NEG-REVIEW-006
base:
  saved Review
mutation:
  candidate_sha256 belongs to prior version
expected:
  Review/candidate identity failure

EX-NEG-REVIEW-007
base:
  residual issue file
mutation:
  append identical residual record twice
expected:
  duplicate-safe reconciliation; no duplicate durable line
```

---

## 29. Context mutations

```text
EX-NEG-CTX-001
base:
  Writer Context
mutation:
  add Thread author_truth
expected:
  Writer-view Schema/security failure

EX-NEG-CTX-002
base:
  Continuity Context
mutation:
  add Knowledge author_truth
expected:
  Continuity-view Schema/security failure

EX-NEG-CTX-003
base:
  Context snapshot
mutation:
  add created_at
expected:
  exact root/semantic determinism failure

EX-NEG-CTX-004
base:
  hash-named Context file
mutation:
  alter one source hash without changing filename
expected:
  filename/content-hash mismatch

EX-NEG-CTX-005
base:
  mandatory-overflow scenario
mutation:
  truncate prose string to fit
expected:
  forbidden overflow behavior; mechanical stop
```

---

## 30. Scene and Evidence mutations

```text
EX-NEG-SCENE-001
base:
  frozen Scene card
mutation:
  participant ID not present in Chapter Scene function
expected:
  planning/Scene-card integration failure

EX-NEG-SCENE-002
base:
  frozen Scene card
mutation:
  include author truth inside forbidden-disclosure label
expected:
  safe-projection failure

EX-NEG-SCENE-003
base:
  prose
mutation:
  prepend "# Scene"
expected:
  prohibited heading

EX-NEG-SCENE-004
base:
  candidate delta
mutation:
  include evidence_id
expected:
  LLM/code-ownership failure

EX-NEG-SCENE-005
base:
  candidate delta existing update
mutation:
  target field absent from allowed_update_targets
expected:
  authorization failure

EX-NEG-SCENE-006
base:
  committed delta
mutation:
  retain unresolved local_key reference in target
expected:
  committed-delta resolution failure

EX-NEG-EVID-005
base:
  Evidence record
mutation:
  end_offset uses inclusive rather than exclusive convention
expected:
  quote-slice mismatch

EX-NEG-EVID-006
base:
  Evidence record
mutation:
  quote_sha256 hashes surrounding sentence
expected:
  quote-hash mismatch
```

---

## 31. Manifest and pointer mutations

```text
EX-NEG-MANIFEST-001
base:
  Scene manifest
mutation:
  prose_path = runtime/checkpoints/...
expected:
  adopted-path failure

EX-NEG-MANIFEST-002
base:
  Commit manifest
mutation:
  commit_type = volume_handoff but Scene fields non-null
expected:
  commit-type conditional failure

EX-NEG-MANIFEST-003
base:
  Handoff Generation
mutation:
  current_order = parent + 1
expected:
  Handoff order-preservation failure

EX-NEG-MANIFEST-004
base:
  Generation manifest
mutation:
  source Scene and source Handoff both non-null
expected:
  conditional branch failure

EX-NEG-POINTER-001
base:
  canon/HEAD
mutation:
  write "51\n" instead of "00000051\n"
expected:
  pointer format failure

EX-NEG-POINTER-002
base:
  output/CURRENT
mutation:
  point to highest existing unadopted Publication
expected:
  invalid CURRENT graph; no fallback selection
```

---

## 32. Publication mutations

```text
EX-NEG-PUB-001
base:
  Publication Validation payload set
mutation:
  include publication-validation.json itself
expected:
  payload-set definition failure

EX-NEG-PUB-002
base:
  Publication Manifest files
mutation:
  include publication-manifest.json itself
expected:
  self-reference/content-set failure

EX-NEG-PUB-003
base:
  finalized Publication
mutation:
  retain publication-build-manifest.json
expected:
  exact final-file-set failure

EX-NEG-PUB-004
base:
  Publication Manifest
mutation:
  relative_path = .staging/publication/pub-000001/manuscript/v01.md
expected:
  publication-relative-path failure

EX-NEG-PUB-005
base:
  Publication Gate
mutation:
  publication_manifest_relative_path = publications/pub-000001/publication-manifest.json
expected:
  rename-stability/path failure

EX-NEG-PUB-006
base:
  passing Gate snapshot
mutation:
  change payload_set_sha256 without changing Manifest
expected:
  Gate mechanical failure

EX-NEG-PUB-007
base:
  valid Completion audit with overall_assessment = incomplete
mutation:
  gate_status = pass
expected:
  Gate semantic consistency failure

EX-NEG-PUB-008
base:
  final Publication directory before CURRENT
mutation:
  mark Run completed
expected:
  adoption/status failure
```

---

# Part VI: Fixture file inventories

## 33. Fixture inventory format

Every complete fixture document includes an inventory table with:

```text
path
role
media type
canonical size
SHA-256
baseline/new
authority
```

Authority values:

```text
adopted
runtime_resume
checkpoint
candidate_history
audit
staging
pointer
```

An inventory path must match `workspace_layout.md`.

### 33.1 Directory inventory hash

For a directory fixture, `inventory_sha256` is calculated over canonical JSON of sorted records containing:

```text
relative_path
sha256
size_bytes
role
```

The directory inventory does not hash filesystem timestamps, permissions, inode numbers, or absolute roots.

### 33.2 Baseline inventory

A delta fixture records:

```text
baseline_fixture_id
baseline_inventory_sha256
new_or_changed_records
removed_records
result_inventory_sha256
```

A fixture may not silently inherit an unversioned baseline.

---

## 34. Minimum Genesis inventory

The Initial fixture inventory includes:

```text
input/keywords.json
input/brief.json

runtime/effective-config.json
runtime/run-manifest.json
runtime/run-state.json
runtime/counters.json

canon/HEAD
canon/initial-design.json
canon/generations/00000000/current-canon.json
canon/generations/00000000/knowledge-items.json
canon/generations/00000000/story-state.json
canon/generations/00000000/evidence-index.json
canon/generations/00000000/commit-manifest.json
canon/generations/00000000/generation-manifest.json

plans/series-map.json
plans/volumes/v01/volume-design.json
plans/volumes/v01/chapters/c001/chapter-design.json
```

Candidate/Review/Context history may be included in the full test workspace, but the fixture document must at least list every artifact needed to reconstruct their validated identity.

---

## 35. Minimum representative Scene inventory

```text
runtime/checkpoints/scenes/v01/c001/s001/scene-card.json
runtime/checkpoints/scenes/v01/c001/s001/prose.md
runtime/checkpoints/scenes/v01/c001/s001/continuity-delta.json
runtime/checkpoints/scenes/v01/c001/s001/commit-plan.json
runtime/checkpoints/scenes/v01/c001/s001/checkpoint-manifest.json

artifacts/scenes/v01/c001/s001/scene-card.json
artifacts/scenes/v01/c001/s001/prose.md
artifacts/scenes/v01/c001/s001/continuity-delta.json
artifacts/scenes/v01/c001/s001/scene-manifest.json

canon/generations/<scene-generation>/...
canon/HEAD
runtime/run-state.json
runtime/counters.json
```

The final post-commit fixture normally omits the checkpoint directory because COMMIT-04 removes it.

To prove checkpoint/adopted equality, the fixture document retains the exact pre-commit checkpoint hashes as expected values.

---

## 36. Minimum Completion/Publication inventory

```text
artifacts/handoffs/v04.json

canon/generations/00000050/...
canon/generations/00000051/...
canon/HEAD

audit/completion/00000051/completion-precondition.json
audit/completion/00000051/completion-audit.json
audit/publication-gates/<publication-id>.json

publications/<publication-id>/manuscript/series.md
publications/<publication-id>/manuscript/v01.md
publications/<publication-id>/manuscript/v02.md
publications/<publication-id>/manuscript/v03.md
publications/<publication-id>/manuscript/v04.md
publications/<publication-id>/metadata/series.json
publications/<publication-id>/metadata/volumes/v01.json
publications/<publication-id>/metadata/volumes/v02.json
publications/<publication-id>/metadata/volumes/v03.json
publications/<publication-id>/metadata/volumes/v04.json
publications/<publication-id>/reports/completion-audit.json
publications/<publication-id>/publication-validation.json
publications/<publication-id>/publication-manifest.json

output/CURRENT
runtime/run-state.json
```

`publication-build-manifest.json` must be absent.

---

# Part VII: Validation procedure

## 37. Fixture validation order

A fixture validator performs:

1. parse the fixture-document metadata;
2. resolve and validate the baseline fixture;
3. construct the complete expected workspace inventory;
4. validate path grammar and root containment;
5. parse every JSON artifact;
6. validate exact Schemas and unknown-field rejection;
7. canonicalize and verify each file hash;
8. validate pointer bytes;
9. validate HEAD Generation/Commit/Scene-or-Handoff graph;
10. validate adopted plan hierarchy;
11. validate Candidate/Review/Context references included in the fixture;
12. validate Checkpoint phase when present;
13. validate Canon/State/Evidence references;
14. validate Evidence quote/offset/hash;
15. validate delta-to-root bidirectional correspondence;
16. validate Run-state and counters;
17. validate Completion coverage;
18. validate Publication payload/Validation/Manifest hashes;
19. validate Gate snapshot;
20. validate CURRENT and completed Run state;
21. verify private sentinel exclusion from publication.

The validator must stop using a lower-level artifact as substitute authority when a pointer-selected graph is invalid.

---

## 38. Mutation validation

For each `EX-NEG-*` case:

1. clone the exact named positive base;
2. apply the one documented mutation;
3. run the production validator or pipeline entry point;
4. assert the exact failure class:
   ```text
   response_structure_retry
   semantic_revision
   mechanical_error
   quarantine
   manual_intervention
   ```
5. assert no forbidden durable side effect;
6. restore/throw away the isolated test workspace.

Negative mutations must not alter the committed canonical fixture files in place.

---

## 39. Hash regeneration

Fixture hashes may be regenerated only by the repository's deterministic fixture-builder command.

The builder must:

```text
use the production canonical serializer
use the fake clock
use deterministic scripted provider responses
write to a temporary workspace
validate the complete workspace
emit an inventory diff
require explicit maintainer acceptance before committed fixture replacement
```

A text editor must not be used to manually replace a single hash without rebuilding dependent manifests.

---

## 40. Fixture review checklist

Before accepting a fixture update:

```text
all changed story-semantic values are intentional
all derived hashes changed where expected
no unrelated canonical bytes changed
all persistent IDs remain deterministic
no allocated ID was reused
Generation arithmetic includes Handoff commits
current_order counts only Scene commits
Scene manifests use adopted paths
Handoff manifests use Handoff branch fields
Context snapshots contain no timestamp/self-hash
Writer/Continuity contexts contain no author truth
Publication Validation/Manifest hash sets are noncyclic
Gate paths remain rename-stable
publication-build-manifest is absent from final inventory
private sentinels remain absent from publication
```

---

# Part VIII: Deprecated examples

## 41. Deprecated fixture forms

The following old fixture patterns are forbidden.

### 41.1 One generic INIT object reused four times

Forbidden:

```text
init_01 = same combined object
init_02 = same combined object
init_03 = same combined object
init_04 = same combined object
```

Each INIT stage has a distinct exact root.

### 41.2 Incomplete State roots

Forbidden:

```text
story_state = {"story_clock": ...}
```

when Character, Relationship, Thread, and Knowledge rows are required.

### 41.3 Relationship `origin`

Forbidden:

```text
Relationship record field:
  origin
```

Use the current Relationship contract's `relationship_origin`.

### 41.4 Old temporal ID

Forbidden:

```text
time-000001
```

Use:

```text
rule-000001
```

### 41.5 Evidence array root

Forbidden:

```text
evidence-index.json = []
```

Required:

```text
{"records":[]}
```

or populated `records`.

### 41.6 Checkpoint paths in adopted Scene manifest

Forbidden:

```text
runtime/checkpoints/scenes/.../prose.md
```

Required adopted path:

```text
artifacts/scenes/vNN/cNNN/sNNN/prose.md
```

### 41.7 Generation equals Scene order

Forbidden assumption:

```text
generation numeric suffix
=
story_clock.current_order
```

This fails after a Volume Handoff commit.

### 41.8 Final Scene as final HEAD

Forbidden for the canonical success fixture:

```text
final HEAD = final Scene Generation
```

Required:

```text
final Scene Generation = 00000050
final Handoff/final HEAD Generation = 00000051
```

### 41.9 Publication staging paths

Forbidden final fields:

```text
publication_staging_path
validation_path = .staging/publication/...
```

Use root-relative Validation/Manifest references and external Gate identity.

### 41.10 `adopted_at` self-cycle in Publication manifest

A Publication manifest field that can only be known after adoption but changes manifest bytes/hashes is forbidden.

Adoption time belongs in external operation/Run-state records when needed.

---

# Part IX: Acceptance mapping

## 42. Example-to-acceptance mapping

| example group | primary acceptance IDs |
|---|---|
| Keyword/Brief anchors | `ACC-INIT-DATA-001..002`, `ACC-PIPE-INIT-001..002` |
| hash anchors | `ACC-CORE-001..005` |
| Genesis clock | `ACC-STATE-006`, `ACC-PIPE-INIT-006..007` |
| Review anchors | `ACC-REV-001..006` |
| continuity anchors | `ACC-EVID-001..010`, `ACC-PIPE-SCENE-007..010` |
| Evidence offset anchor | `ACC-EVID-003..005` |
| initial/planning fixture | `ACC-FIX-001` dependencies and `ACC-PIPE-INIT-*`, `ACC-PIPE-PLAN-*` |
| representative Scene fixture | `ACC-COMMIT-*`, `ACC-PIPE-SCENE-*` |
| final Handoff fixture | `ACC-VH-*`, `ACC-FIX-001..005` |
| Completion/Publication fixture | `ACC-OUT-*`, `ACC-FIX-006..009` |
| negative mutation catalogue | Mutation Gate in `implementation_acceptance.md` |

The fixture documents may define additional example IDs. They must not redefine IDs in this index with different meaning.

---

## 43. Required documentation checks

Documentation validation must assert:

```text
every json fenced block in this document parses
every exact anchor hash matches its canonical JSON/text
every relative link resolves
every EX-POS ID is unique
every EX-NEG ID is unique
fixture IDs use active v3 suffix
no active v1/v2 fixture is referenced as authority
no checkpoint path appears in an adopted Scene example
no staging-root publication path appears in final Manifest/Gate examples
final Generation/order arithmetic equals 51/47
```

---

## 44. Mechanical acceptance conditions

This examples index is acceptable only when tests demonstrate:

```text
example-class labels
canonical JSON byte algorithm
canonical prose and pointer byte rules
all exact small hashes
Keyword-to-Brief source hash
empty root file-role distinction
Genesis Story-clock exact value
Review candidate exact roots
continuity candidate/committed distinction
Evidence code-point offsets and hashes

fixture chain and baseline identities
three fixture-document links
complete required inventories
47-Scene distribution
four Handoff commits
final Scene Generation 00000050
final Handoff/HEAD Generation 00000051
final current_order 47
required stable persistent IDs
Commit-type example coverage

positive example-ID uniqueness
negative mutation-ID uniqueness
single-principal-mutation rule
expected validation/failure classification
fixture inventory hashing
deterministic hash regeneration
private sentinel publication check

deprecated INIT generic object rejection
Relationship origin terminology correction
Temporal-rule ID correction
Evidence root correction
adopted Scene path correction
Generation/order distinction
rename-stable Publication fields
Publication-manifest self-cycle avoidance

relative link resolution
JSON fenced-block parsing
hash-anchor verification
acceptance-ID mapping
