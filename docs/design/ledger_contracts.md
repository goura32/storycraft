# Ledger contracts index

## 目的

current_canon、knowledge_items、story_state、runtime_stateを分離し、保存artifactのfield契約へ案内します。

## 対象範囲

- current_canon、knowledge_items、story_state、runtime_state
- mutable story state
- evidenceとtyped continuity update
- run/candidate/checkpoint/commit/publication runtime record

## 正本関係

| 内容 | 詳細正本 |
|---|---|
| Canon record / knowledge item | [canon records](contracts/ledger/canon_records.md) |
| mutable state | [story state](contracts/ledger/story_state.md) |
| evidence / update / ID mapping | [evidence and updates](contracts/ledger/evidence_and_updates.md) |
| run-state / candidate / manifest / counters | [runtime records](contracts/ledger/runtime_records.md) |

## 用語

- `canon/initial-design.json`: 初期生成来歴、author truth、series arcs、ending criteria。
- `canon/generations/<id>/current-canon.json`: 採用済み固定Canon record。
- `canon/generations/<id>/knowledge-items.json`: knowledge itemだけ。
- `canon/generations/<id>/story-state.json`: mutable stateだけ。
- `runtime/run-state.json`: 実行位置とresume状態。

全保存recordは`additionalProperties:false`です。一般record lifecycleは`active|inactive|retired`だけで、thread statusは別に`open|in_progress|resolved|retired`です。`current_canon`はadopted fixed records、`knowledge_items`はaccepted knowledge subjects、`story_state`はmutable story values、`runtime_state`はprogram execution valuesです。

## 読み順

1. [canon records](contracts/ledger/canon_records.md)
2. [story state](contracts/ledger/story_state.md)
3. [evidence and updates](contracts/ledger/evidence_and_updates.md)
4. [runtime records](contracts/ledger/runtime_records.md)
