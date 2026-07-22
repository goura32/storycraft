# プロンプトテンプレートと出力契約

> 製品上の正本は[製品仕様](../product/SPECIFICATION.md)、LLM呼び出しの正本は[シリーズ生成フロー設計](series_engine_flow.md)とする。この文書は次期実装でtemplateと出力契約をどう構成するかを定める。現行template・JSON Schemaは今回変更しない。

## 1. 基本方針

- 一つの製品フェーズは複数のLLM呼び出しを含められる。templateのstage名と製品フェーズを同義にしない。
- 品質改善対象は、生成、対象全体レビュー、一括修正、対象全体再レビューを共通パターンとする。ただし入力、出力、所有範囲はstageごとに定義する。
- レビューは意味・品質上のissueを返す補助である。severity、passed/failed、継続可能性を工程停止の指示にしない。
- templateが返す候補の採否は、LLM自己申告ではなくコードの機械的検証が決める。
- 修正templateは、対象成果物全体、全issue、変更可能範囲、維持すべき内容を一回で受け取り、整合した成果物全体を返す。issueごと・fieldごとの修正templateは作らない。
- LLMは永続IDを決めない。コードが検証後に採番する。

## 2. 次期stage一覧

| stage | 役割 | 主な出力 |
|---|---|---|
| `initial_concept` | INIT-01の作品コンセプト | 作品の核、ジャンル、読者体験、テーマ、対立、終了方向 |
| `initial_characters_relationships` | INIT-02の人物・関係 | 人物、開始State、関係、認識差、長期変化 |
| `initial_world_temporal_rules` | INIT-03の舞台・時間規則 | 世界、場所、制度、重要物、`temporal_rules` |
| `initial_series_arcs` | INIT-04の全体変化 | 主要な問い・伏線・イベント、major thread、`ending_criteria` |
| `initial_canon_assembly` | INIT-05の構造化 | 初期Canon・初期State・知識状態候補 |
| `initial_design_review` | INIT-06の全体レビュー | 初期設計全体のissue一覧 |
| `initial_design_revision` | 初期設計の一括修正 | 初期設計全体の修正版 |
| `volume_design` | 巻設計 | 巻目的、人物・関係変化、thread、対立、問い |
| `chapter_design` | 章設計 | 順序付き章、目的、変化、thread action、場面数 |
| `scene_card` | 場面設計 | POV、開示制約、イベント、更新許可、文字数目安 |
| `scene` | 本文生成 | 小説本文だけ |
| `continuity_delta` | 本文後の差分抽出 | handoff、更新、新規項目、knowledge、thread、`story_clock`差分 |
| `volume_handoff` | 巻境界処理 | 次巻向けの事実handoff |
| `completion_audit` | 完結意味監査 | ending criteria・未解決へのissue |

現行の`brief`は入力確定時のkeywords→brief生成に残せる。既存の`characters`、`relationships`、`world`、`timeline`、`threads`、`volume_map`、`volume_chapters`、`continuity`、`volume_summary`、`closure`は、次期仕様のstageへ置換または責務移管する対象であり、互換名を残すことを要件にしない。

## 3. templateの入出力境界

### 初期設計

- INIT-01〜04は先行採用済み成果物だけを入力にする。人物・関係、世界・時間規則、全体変化を一回の巨大出力に混ぜない。
- `initial_canon_assembly`は前段の構造化・統合を主目的とする。前段にない主要創作を大量追加しない。不足補完が必要なら理由を返す。
- `initial_design_review`はbriefと初期設計全体を読み、候補を直接変更しない。
- `initial_design_revision`は全issueを同時に解決する初期設計全体を返す。修正後も全体をレビューする。

### 巻・章・場面

- `volume_design`は人物と中心関係の開始・終了目標を必須の設計対象とし、thread操作だけの配分にしない。
- `chapter_design`は物語上の意味からthread actionを章へ配置する。コードによる先頭・中央・末尾への固定配分を前提にしない。
- `scene_card`は作者真実ではなく、writerへ必要な開示制約を渡す。可視ID、更新可能ID・field、`story_clock`に沿う時間進行を明示する。
- `scene`は本文だけを返す。Canon更新、handoff、注釈を混在させない。作者真実、結末条件、他者の秘密、将来詳細を入力に含めない。

### 差分・監査

- `continuity_delta`は凍結本文だけから、`existing_item_updates`、`new_item_proposals`、`knowledge_updates`、`thread_updates`、`story_clock_update`、`handoff_summary`を返す。根拠は本文からそのままコピーする。
- `volume_handoff`は場面handoff、巻の差分、現在State、thread状態、`story_clock`を使う。対象巻の全本文を再入力しない。
- `completion_audit`は意味上の根拠不足・未解決をissueとして返す。結末を生成、修正、自己承認しない。

## 4. 機械的検証との責務分離

| 対象 | templateが守ること | コードが決定的に確認すること |
|---|---|---|
| 構造 | 指定したJSON構造を返す | JSON parse、Schema、必須項目、型 |
| ID | 既知IDを参照し、IDを発番しない | 既知ID、許可ID、重複、コードによる新規ID採番 |
| 更新 | 許可範囲だけを差分候補にする | field、`before`値、本文evidence完全一致、非重複、`story_clock`非逆行 |
| 品質 | 全体をレビューし、全issueを一括修正する | review issueを停止条件にせず、構造正常候補を採用 |
| 完結 | 意味上の裏付けと未解決を指摘する | 必要成果物、本文、major thread、ending criterion、artifact |

## 5. 監査と保存

各呼び出しの要求・応答、正本候補、レビュー、修正、検証結果、残存issue、採用理由を監査可能に保存する。場面では、カード採用、本文凍結、差分抽出を内部checkpointにできるが、本文、handoff、検証済み差分、Canon・現在State更新、新規項目、`story_clock`がそろうまで後続場面への正本を更新しない。

## 6. 実装移行時の確認

template・Schema・validator・workflowを変更する実装タスクでは、各stageの入力所有権、出力Schema、機械的検証、品質ループ、採用・保存単位を同時に整合させる。今回の文書改訂はその設計契約のみを定め、現行のtemplate、JSON Schema、ソースコード、テストを変更しない。
