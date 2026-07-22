# Workspace layout

> workspace、generation path、artifact、audit、publication filenameの唯一の正本。

```text
workspace/
├── input/brief.json
├── plans/series-map.json
├── canon/
│   ├── initial-design.json
│   ├── generations/<generation-id>/{current-canon.json,story-state.json,knowledge-items.json,evidence-index.jsonl,commit-manifest.json}
│   └── HEAD
├── artifacts/scenes/vNN/cNN/sNN/{scene-card.json,prose.md,continuity-delta.json,scene-manifest.json}
├── artifacts/volumes/vNN/handoff.json
├── audit/{llm-calls, reviews, completion}/
├── runtime/{run-manifest.json,counters.json,run-state.json,effective-config.json,orphans}/
├── publications/<publication-id>/{manuscript,reports,metadata}/
├── output/CURRENT
└── .staging/
```

No root-level canon/state/knowledge JSON aliases are valid; every effective object resides beneath the HEAD-selected generation.

## Naming

| kind | filename |
|---|---|
| LLM call | `000123__prose-01__v01-c003-s002__generate__attempt-02.json.gz` |
| review | `000124__prose-02__v01-c003-s002__review.json.gz` |
| revision | `000125__prose-rev__v01-c003-s002__round-01.json.gz` |
| completion | `completion-audit-attempt-01.json`, `completion-audit-final.json` |
| manuscript | `volume-01.md`, `volume-02.md`, `series.md` |
| publication metadata | `publication.json` |

`completion-audit-final.json` points only to the last structurally valid audit result. A scene manifest has required `scene_id,commit_id,card_hash,prose_hash,delta_hash,generation_id,created_at`.

## Canonical JSON and hash

JSON is NFC-normalized, UTF-8, sorted keys, compact separators, and no NaN/Infinity. SHA-256 is over that byte sequence; prose SHA-256 is NFC UTF-8 prose bytes. JSONL evidence is one canonical object per line ordered by evidence ID.

## Publication pointer

`output/` is a logical reference, not a replaceable publication directory. Publish exactly:

1. construct `.staging/publication`;
2. validate all manuscript/report/metadata/hash rules;
3. rename it to `publications/<publication-id>/`;
4. atomically replace `output/CURRENT` with `<publication-id>`.

A crash before step 4 preserves the old pointer. A crash after step 4 exposes only a fully renamed, validated publication. `publication.json` records publication ID, source HEAD generation, completion audit hash, created timestamp, and output hashes.
