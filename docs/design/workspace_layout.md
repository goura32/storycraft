# Workspace layout

> workspace・ファイル名・正規化・公開の正本。commitは[runtime and recovery](runtime_and_recovery.md)、工程は[pipeline contracts](pipeline_contracts.md)を参照する。

```text
workspace/
├── input/
│   ├── brief.json
│   └── keywords.json
├── run-manifest.json
├── runtime/
│   ├── run-state.json
│   ├── counters.json
│   ├── effective-config.json
│   └── checkpoints/scenes/
├── canon/
│   ├── initial-design.json
│   ├── generations/
│   └── HEAD
├── plans/
│   ├── series-map.json
│   └── volumes/
├── artifacts/
│   ├── scenes/
│   └── volumes/
├── audit/
│   ├── llm-calls/
│   ├── reviews/
│   ├── residual-issues.jsonl
│   └── completion/
├── logs/storycraft.log
├── output/
│   ├── manuscript/
│   ├── reports/
│   └── metadata/
├── .staging/
│   ├── scene-commits/
│   └── publication/
└── .storycraft.lock
```

## path契約

| path | 内容・正本 |
|---|---|
| `canon/generations/00000042/` | `current-canon.json,story-state.json,knowledge-items.json,evidence-index.jsonl,commit-manifest.json`。HEADだけが正本generationを指定。 |
| `plans/series-map.json` | 採用series map。不変。 |
| `plans/volumes/v01/volume-design.json` / `chapters.json` | 採用済み設計。不変。 |
| `artifacts/scenes/v01/c001/s001/` | `scene-card.json,prose.md,continuity-delta.json,scene-manifest.json`。 |
| `audit/llm-calls/v01/c001/` | 巻・章対象call。非対象callは`audit/llm-calls/global/`。JSON gzipで保存。 |
| `audit/completion/` | 内部正本。公開用は`output/reports/completion-audit.json`へ秘密を除いて複製。 |

scene manifestは`scene_id,commit_id,volume_number,chapter_number,scene_number,prose_sha256,character_count,adopted_at,input_plan_refs,evidence_ids`を必須とする。

## JSON・prose正規化

JSONはUTF-8、BOMなし、Unicode NFC、key sort、compact separator、末尾LF。proseはUTF-8、BOMなし、Unicode NFC、LF改行、末尾LF。hashは親manifestへ保存し、対象ファイルへ自己hashを書かない。

## audit log

call logは`call_id,operation_id,target_id,call_role,attempt,model,request_timestamp,response_timestamp,duration_ms,prompt_template_version,schema_version,message_hashes,request_body,response_body,finish_reason,input_tokens,output_tokens,estimated_cost,error,retry_classification`を持つ。API key、Authorization header、OS環境変数、secret configを保存しない。

## output Markdown

volume file:

```markdown
# 巻タイトル

## 第1章　章タイトル

本文
```

series fileは`# シリーズタイトル`の後に`# 第1巻　巻タイトル`を巻順で並べる。scene境界は出力しない。公開前検証はUTF-8、全巻・章見出し、本文非空、巻章順、重複本文なし、内部JSON/prompt/author truth/未採用本文なしを要求する。
