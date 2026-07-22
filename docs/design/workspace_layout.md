# Workspace layout

> workspace・ファイル名・原子的保存の正本。工程は[pipeline contracts](pipeline_contracts.md)、情報正本は[ledger contracts](ledger_contracts.md)を参照する。

## 構成

```text
workspace/
├── run-manifest.json
├── runtime/
│   ├── run-state.json
│   ├── counters.json
│   └── checkpoints/scenes/
├── canon/
│   ├── initial-design.json
│   ├── current-canon.json
│   ├── story-state.json
│   ├── knowledge-items.json
│   └── evidence-index.jsonl
├── plans/
│   ├── series-map.json
│   └── volumes/v01/
│       ├── volume-design.json
│       ├── chapters.json
│       └── scenes/
├── artifacts/
│   ├── scenes/v01/c001/s001/
│   │   ├── scene-card.json
│   │   ├── prose.md
│   │   ├── continuity-delta.json
│   │   └── scene-manifest.json
│   └── volumes/v01/volume-handoff.json
├── audit/
│   ├── llm-calls/
│   ├── reviews/
│   ├── residual-issues.jsonl
│   └── completion/
├── logs/storycraft.log
├── output/
│   ├── manuscript/volume-01.md
│   ├── manuscript/series.md
│   ├── reports/completion-audit.json
│   ├── reports/quality-review-summary.json
│   └── metadata/publication.json
├── .staging/
└── .storycraft.lock
```

## 責務

| path | 内容 | 正本/可変性 | 禁止事項 |
|---|---|---|---|
| `run-manifest.json` | run_id,state/prompt/schema bundle version,editorial/publishing profile,model,config fingerprint,created_at | run開始時に固定 | 秘密値、絶対path |
| `runtime/run-state.json` | 現在工程、次の対象、停止理由、completed、inflight scene、最後の正常checkpoint、再開位置 | runtime_state正本 | Canon/current値 |
| `runtime/counters.json` | next_call_id、transport/structure/revision/audit counter | runtime_state正本、単調増加 | ファイル数からの採番 |
| `runtime/checkpoints/` | 未採用内部候補 | 一時。採用後は削除又はarchive | 採用済み正本として参照 |
| `canon/initial-design.json` | 採用済みinitial design bundle | 不変スナップショット | 現在state |
| `canon/current-canon.json` | fixed、scope、lifecycle、参照、局所Canon | canon正本 | 感情・進捗・reader知識 |
| `canon/story-state.json` | 現在値、knowledge state、clock | state正本 | fixed/author truth |
| `canon/knowledge-items.json` | knowledge target | canon正本 | writer viewへのauthor truth漏出 |
| `canon/evidence-index.jsonl` | append-only引用索引 | index正本 | 本文外引用 |
| `plans/` | 採用済み・未来の設計 | 過去計画は不変、未来は明示replanのみ可 | 本文artifact混在 |
| `artifacts/` | 採用済みcard/prose/delta/handoff | artifact正本 | raw LLM response |
| `audit/llm-calls/` | 全LLM入出力とmetadata | audit | outputへの混入 |
| `audit/reviews/` | reviewとrevision対応 | audit | 正本の置換 |
| `audit/residual-issues.jsonl` | 上限後に残るissue | append-only audit | 旧`quality-acceptances.json`を新規作成 |
| `audit/completion/` | completion audit attempt | audit | 正常でない`final`作成 |
| `output/` | 利用者へ配布する完成物 | 公開物 | prompt/raw/checkpoint |
| `.staging/` | 公開前の一時出力 | 使い捨て | 成功前のoutput更新 |

未執筆未来計画は明示的replan工程だけが変更できる。採用済み過去計画と採用artifactは不変である。

## 命名規則

ASCII小文字・kebab-case・固定幅番号・安定IDを使い、日本語題名を正本ファイル名に入れない。

| 対象 | 規則 / 例 |
|---|---|
| volume/chapter/scene | `v01` / `c001` / `s001`、scene ID=`v01-c001-s001` |
| 公開原稿 | `volume-01.md`、`series.md` |
| LLM call | `000123__prose-01__v01-c003-s002__generate__attempt-02.json` |
| review | `000124__prose-02__v01-c003-s002__review.json` |
| revision | `000125__prose-rev__v01-c003-s002__round-01.json` |
| completion | `completion-audit-attempt-01.json`、`completion-audit-final.json` |

call log名は`call_id__operation_id__target_id__call_role__attempt`。`call_id`は`runtime/counters.json`の単調増加値であり、ファイル数や時刻から算出しない。`completion-audit-final.json`は構造正常な最後の結果だけに作成する。

## manifestとhash

state/manifestに記録するpathはworkspace rootからの相対pathだけである。SHA-256は最低限、prose artifact、initial-design、current-canon、story-state、completion audit final、公開原稿に保存する。

`scene-manifest.json`は`scene_id,volume_number,chapter_number,scene_number,prose_sha256,character_count,adopted_at,input_plan_refs,evidence_count`を必須とする。

## 原子的保存

単一ファイルは一時ファイルへ書込み→flush→fsync→同一filesystemのreplace→親directory fsyncで保存する。場面採用はstaging directoryへcard/prose/delta/manifestを完成させ、全hash・delta merge・state/indexを検証してから採用pointerを最後に更新する。失敗時はpointerを更新せず、`.staging/`の当該runディレクトリを削除するか失敗理由付きで隔離する。`output/`への公開も同じ方式でstagingから原子的に置換する。
