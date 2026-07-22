# Implementation acceptance

> deterministic fakeで実行する内容ベース受入条件。詳細fieldは分割contractを正本とする。

## Pipeline content

- 各stageのprocessor typeが分割pipeline契約と一致する。
- code-only stageはLLM call、transport retry、response structure retry、revision round、review outputを持たない。
- review stageだけが`review_result`を出力し、revise stageだけがrevision roundを消費する。
- candidate stageは`runtime/candidates/`、checkpoint stageは`runtime/checkpoints/`、adoption stageだけが`plans/`、`canon/`、`artifacts/`、`publications/`へ書く。
- SC/PROSE/DELTAに旧入力採用限定の誤記、またはinputとLLM auditを混同する保存先誤記がない。

## Data and ledger content

- briefとscene cardの全field、unknown field拒否、code identity fieldを検証する。
- relationship participantsが異なる。
- current canonにknowledge item、thread status/progress、story stateが混入しない。
- knowledge itemとknowledge state配列、general lifecycle/thread status matrixを検証する。
- candidate manifest、run-state、fixed hash fields、local key mapping rowを検証する。

## Fixture and output content

- 全fixture JSON parse、baseline chain、ID参照、before/after、evidence quote/offset/hash、manifest hashを検証する。
- NFC character countは本文実値と一致する。
- pre-completion baselineとfinal checkpoint/commit/scene manifest/HEAD更新を検証する。
- public auditからauthor truth、resolution condition、秘密全文、raw prompt/response、internal pathが除去される。
- minimum volume、multi-volume、candidate resume、checkpoint resume、corrupt candidate recovery、publication pointer crashを実行する。
