# Workspace layout

> Path・filename・正本分離の索引。runtime fieldは[ledger runtime records](contracts/ledger/runtime_records.md)、stage保存先は[pipeline index](pipeline_contracts.md)を正本とする。

```text
workspace/
├── input/
│   ├── brief.json
│   └── keywords.json
├── runtime/
│   ├── run-state.json
│   ├── counters.json
│   ├── effective-config.json
│   ├── candidates/
│   │   ├── input/
│   │   ├── initial-design/
│   │   ├── series-map/
│   │   ├── volumes/v01/
│   │   ├── chapters/v01/c001/
│   │   ├── scenes/v01/c001/s001/
│   │   ├── handoffs/v01/
│   │   └── completion/
│   ├── checkpoints/scenes/v01/c001/s001/
│   └── orphans/<timestamp>/
├── canon/
│   ├── initial-design.json
│   ├── HEAD
│   └── generations/<generation-id>/
│       ├── current-canon.json
│       ├── knowledge-items.json
│       ├── story-state.json
│       ├── evidence-index.jsonl
│       └── generation-manifest.json
├── plans/
│   ├── series-map.json
│   ├── volumes/v01.json
│   └── chapters/v01/c001.json
├── artifacts/
│   ├── scenes/v01/c001/s001/
│   └── handoffs/v01.json
├── audit/
├── logs/
├── publications/
├── output/CURRENT
├── .staging/
│   ├── scene-commits/v01-c001-s001/
│   └── publication/
└── .storycraft.lock
```

## 固定幅

```text
volume:  v01
chapter: c001
scene:   s001
scene ID: v01-c001-s001
```

## 正本

| object | path | 責務 |
|---|---|---|
| initial design | `canon/initial-design.json` | 初期来歴、author truth、長期方針 |
| current canon | `canon/generations/<id>/current-canon.json` | 採用済み固定Canon record |
| knowledge items | `canon/generations/<id>/knowledge-items.json` | knowledge itemのみ |
| story state | `canon/generations/<id>/story-state.json` | mutable stateのみ |
| runtime state | `runtime/run-state.json` | 実行位置、candidate/checkpoint参照 |

`canon/HEAD`が唯一の実行中generationを指します。candidateはresume正本、auditは監査だけです。scene commitはstaging検証、generation/artifact rename、HEAD最後のatomic replaceで行います。
