# Workspace layout

> Workspace path・filename・canonical JSON・publication pointerの唯一の正本。checkpoint/manifest意味は[runtime and recovery](runtime_and_recovery.md)を参照する。

```text
workspace/
├── input/
│   └── brief.json
├── plans/
│   ├── series-map.json
│   └── volumes/v01/{volume-design.json,chapters.json}
├── canon/
│   ├── initial-design.json
│   ├── generations/00000000/{current-canon.json,story-state.json,knowledge-items.json,evidence-index.jsonl,commit-manifest.json}
│   └── HEAD
├── runtime/
│   ├── checkpoints/scenes/v01/c001/s001/{checkpoint-manifest.json,scene-card.json,prose.md,continuity-delta.json}
│   ├── orphans/
│   ├── run-manifest.json
│   ├── counters.json
│   ├── run-state.json
│   └── effective-config.json
├── artifacts/
│   ├── scenes/v01/c001/s001/{scene-card.json,prose.md,continuity-delta.json,scene-manifest.json}
│   └── volumes/v01/handoff.json
├── audit/
│   ├── llm-calls/
│   ├── reviews/
│   ├── completion/
│   └── residual-issues.jsonl
├── logs/storycraft.log
├── publications/<publication-id>/{manuscript,reports,metadata}
├── output/CURRENT
├── .staging/
└── .storycraft.lock
```

Directory widths are fixed: volume directory is `v01`, chapter directory is `c001`, scene directory is `s001`, and `scene_id` is `v01-c001-s001`. Effective canon/state/knowledge/evidence exists only under the generation selected by `canon/HEAD`; no root-level aliases are valid.

## Checkpoint/artifact boundary

`runtime/checkpoints/scenes/v01/c001/s001/` contains **only unadopted** checkpoint files. SC-CHK writes only `scene-card.json`, PROSE-CHK writes only `prose.md`, DELTA-CHK writes only `continuity-delta.json`; each updates `checkpoint-manifest.json`. No checkpoint stage writes `artifacts/`.

`artifacts/scenes/v01/c001/s001/` contains **only COMMIT-04 adopted** card, prose, delta, and scene manifest. COMMIT-04 copies validated checkpoint bytes into a staged artifact directory, finalizes it, then marks it adopted. Readers of formal scene artifacts must not read checkpoint files.

## Audit filename and payload location

| payload | path / filename |
|---|---|
| LLM call | `audit/llm-calls/000123__prose-01__v01-c001-s001__generate__attempt-02.json.gz` |
| review | `audit/reviews/000124__prose-02__v01-c001-s001__review__attempt-01.json.gz` |
| revision | `audit/llm-calls/000125__prose-rev__v01-c001-s001__revision__attempt-01.json.gz` |
| completion attempt | `audit/completion/completion-audit-attempt-01.json.gz` |
| final valid audit | `audit/completion/completion-audit-final.json` |
| residual issue | `audit/residual-issues.jsonl` |
| volume manuscript | `publications/<publication-id>/manuscript/volume-01.md` |
| series manuscript | `publications/<publication-id>/manuscript/series.md` |
| publication metadata | `publications/<publication-id>/metadata/publication.json` |

A call payload is JSON gzip and has `call_id,operation_id,target_id,call_role,attempt,model,request_timestamp,response_timestamp,duration_ms,prompt_template_version,schema_version,context_hash,request_body,response_body,finish_reason,input_tokens,output_tokens,estimated_cost,error,retry_classification`. It excludes API keys, Authorization headers, OS environment, and secret configuration.

## Canonical bytes and publication

JSON uses NFC-normalized UTF-8, sorted keys, compact separators, no NaN/Infinity. SHA-256 is over those bytes. Prose hash is over NFC UTF-8 prose. Evidence JSONL has one canonical record per line ordered by evidence ID.

Publication is exactly: build `.staging/publication`; validate manuscript/report/metadata/hash rules; rename to `publications/<publication-id>/`; atomically replace `output/CURRENT` with that ID. Crash before pointer replacement keeps prior publication; after replacement exposes only complete validated publication. `publication.json` records publication ID, source HEAD generation, completion audit hash, created timestamp, and output hashes.
