# Pipeline contracts index

## 目的

Storycraftのstage順序、candidate/checkpoint/adopted/audit境界、および各stageの唯一の実値契約への案内です。LLMはcandidate、review result、audit assessmentだけを返し、コードがSchema、ID、hash、evidence、adoption、state merge、retry、保存を担当します。

## 対象範囲

- INPUT、INIT、SERIES
- VOL、CH
- SC、PROSE、DELTA
- COMMIT、VH、COMP、OUT

## 正本関係

| 範囲 | 詳細正本 |
|---|---|
| INPUT / INIT / SERIES | [input and initial](contracts/pipeline/input_and_initial.md) |
| VOL / CH | [planning](contracts/pipeline/planning.md) |
| SC / PROSE / DELTA | [scene generation](contracts/pipeline/scene_generation.md) |
| COMMIT / VH / COMP / OUT | [commit and output](contracts/pipeline/commit_and_output.md) |
| 保存field | [data contracts](contracts/data/brief_and_initial.md) と [ledger contracts](contracts/ledger/canon_records.md) |
| runtime/resume | [runtime records](contracts/ledger/runtime_records.md) |

詳細field表やstage表はこの索引へ再掲しません。

## 共通用語

- **candidate**: `runtime/candidates/`の再開可能な未採用候補。
- **checkpoint**: 後続scene処理専用の`runtime/checkpoints/`保存物。正式readerは読まない。
- **adopted artifact**: 採用後に`plans/`、`canon/`、`artifacts/`、`publications/`へある正本。
- **audit**: `audit/`の監査証跡。resume正本ではない。
- **transport retry**: connection、HTTP、stream interruption、timeoutだけ。
- **response structure retry**: JSON parse、Schema validation、required field missing、enum violationだけ。

## 読み順

1. [brief and initial](contracts/data/brief_and_initial.md)
2. [input and initial pipeline](contracts/pipeline/input_and_initial.md)
3. [planning artifacts](contracts/data/planning_artifacts.md)
4. [planning pipeline](contracts/pipeline/planning.md)
5. [scene artifacts](contracts/data/scene_artifacts.md)
6. [scene pipeline](contracts/pipeline/scene_generation.md)
7. [ledger indexes](ledger_contracts.md)
8. [commit/output pipeline](contracts/pipeline/commit_and_output.md)
9. [runtime records](contracts/ledger/runtime_records.md)
