# シリーズ生成フロー設計

> 製品契約は[製品仕様](../product/SPECIFICATION.md)、採用・保存は[エンジン設計](series_engine_design.md)を正本とする。

```mermaid
flowchart TD
  B[brief] --> I1[INIT-01]
  I1 --> I2[INIT-02 local_key]
  I2 --> I3[INIT-03]
  I3 --> I4[INIT-04]
  I4 --> I5[INIT-05 bundle候補]
  I5 --> R[INIT-06 全体レビュー]
  R -->|issue・上限内| X[初期設計全体を一括修正]
  X --> R
  R -->|clean または上限| V[機械的検証]
  V --> ID[コードがID採番・参照変換]
  ID --> A[initial_design_bundle採用]
  A --> SM[SERIES-01..ID series map採用]
  SM --> VD[巻設計: series map・現在Canon・State]
  VD --> CD[章設計]
  CD --> SC[場面設計 checkpoint]
  SC --> P[本文 checkpoint]
  P --> D[差分 checkpoint・evidence候補]
  D --> SA[Canon/State/index更新を含む場面採用]
  SA --> MS{章内に未処理場面?}
  MS -->|Yes| SC
  MS -->|No| MC{巻内に未処理章?}
  MC -->|Yes| CD
  MC -->|No| VH[巻handoff]
  VH --> MV{未処理巻?}
  MV -->|Yes| VD
  MV -->|No| CP[COMP-PRE: 監査前Gate]
  CP --> CA[COMP-AUDIT: completion audit attempt]
  CA --> CJ{監査JSON正常?}
  CJ -->|正常| SAVE[最後の正常監査を保存]
  CJ -->|不正・attempt残あり| CA
  CJ -->|不正・attempt枯渇| STOP[機械的エラーとして停止]
  SAVE --> PG[COMP-PUBLISH: staging検証]
  PG --> OUT[原子的に公開]
```

## 呼び出し責務

- `series map`はINIT-ID後、VOL-01前に生成・review・採用する不変全巻計画である。
- `volume_design`の入力は採用済みbundle、現在Canon、現在State、前巻handoff、巻番号、残り巻数、編集プロファイル。
- `chapter_design`、`scene_card`、`scene`、`continuity_delta`、`volume_handoff`は共通revision loop対象。
- `continuity_delta`は型付きupdates、new item、knowledge/thread/clock、`ending_evidence_proposals`、handoffを出力する。
- 機械的更新はevidence indexを保存してから場面を原子的採用する。
- `completion_audit`はrevisionでなく同一入力からの独立attempt。issueを材料に監査JSONを直さない。

## 品質・停止

共通loopは「生成→構造検証→全体レビュー→全issue一括修正→再レビュー」。review issueは停止しない。transport retry、review構造retry、revision内の構造再生成、revision roundは別に数える。通信・構造回復の枯渇だけが停止条件である。
