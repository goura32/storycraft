# Pipeline contracts

> 工程入出力の正本。製品動作は[製品仕様](../product/SPECIFICATION.md)、台帳・更新は[ledger contracts](ledger_contracts.md)、順番は[生成フロー](series_engine_flow.md)を正本とする。JSON Schemaは今回作成しない。

## 共通規則

LLMは候補、レビューissue、本文からの抽出候補を返す。コードはID、参照、構造、evidence完全一致、採用、保存、状態遷移を決定する。想定件数・文字数は暴走防止の目安であり文芸上の絶対制限ではない。

| 再試行 | 対象 | 設定値 | 実行カウンタ |
|---|---|---|---|
| transport retry | 接続・HTTP・timeout・stream中断 | `max_transport_retries` | `transport_retries_used` |
| response structure retry | JSON parse、Schema、必須項目 | `max_response_structure_retries` | `response_structure_retries_used` |
| revision round | 正常レビューにissueがある候補全体修正 | `max_revision_rounds` | `revision_rounds_used` |
| completion audit attempt | 同一完成候補への独立意味監査 | `max_completion_audit_attempts` | `completion_audit_attempts_used` |

## 工程一覧

各LLM生成・修正は「入力→生成→response structure retry→構造検証→レビュー→issueがあれば全件一括修正→再レビュー」。レビューissueだけでは停止しない。`固定事実/作者真実/ending criteria/長期arc`はinitial bundle、局所参照はcurrent canon、現在値はcurrent stateをContext Builderが投影し、LLMへ矛盾解消を委ねない。

| ID | 種類・目的 | 入力正本 → 出力/状態 | LLM / コード | 検証・採用・次工程 |
|---|---|---|---|---|
| INPUT-01 | LLM生成。brief読込・keywordsから生成 | 入力 → `brief`/正本候補 | LLM:題材等、コード:入力ID | 必須文字列。採用後INIT-01 |
| INIT-01 | LLM生成。作品コンセプト | brief → 内部成果物 | LLM:concept、コード:なし | 構造/review。INIT-02 |
| INIT-02 | LLM生成。人物・関係 | concept → 内部成果物 | LLM:`local_key`、コード:永続IDなし | local_key一意。INIT-03 |
| INIT-03 | LLM生成。世界・時間規則 | 01/02 → 内部成果物 | LLM:規則、コード:なし | 参照local_key。INIT-04 |
| INIT-04 | LLM生成。arc/伏線/ending | 01-03 → 内部成果物 | LLM:作者真実・criteria、コード:なし | future/knowledge境界。INIT-05 |
| INIT-05 | コード統合。bundle候補 | 01-04 → 正本候補 | LLM値を複写、コード:統合 | 永続IDなし。INIT-06 |
| INIT-06 | LLMレビュー。bundle全体 | bundle候補 → review記録 | LLM:issue、コード:round判定 | 正常issueならINIT-REV、clean/上限ならINIT-ID |
| INIT-REV | LLM修正。bundle全体一括修正 | bundle候補+issues → 正本候補 | LLM:引用field修正、コード:構造 | 全issue対象。INIT-06 |
| INIT-ID | コード処理。採番・参照変換・採用 | bundle候補 → 採用済み正本 | コード:永続ID/変換 | 採番後の意味修正禁止。VOL-01 |
| VOL-01/02/REV | 生成/レビュー/修正。巻設計 | initial bundle/current canon/current state/handoff → 巻正本候補 | LLM:promise/actions、コード:番号 | 既知ID/巻範囲。CH-01 |
| CH-01/02/REV | 生成/レビュー/修正。章設計 | 巻設計 → 章正本候補 | LLM:章・場面数、コード:連番 | 章数/場面数。SC-01 |
| SC-01/02/REV | 生成/レビュー/修正。場面カード | 章、投影Context → checkpoint | LLM:card/new_item_policy、コード:scene ID | `max_items`は0以上、設定上限以内。PROSE-01 |
| PROSE-01/02/REV | 生成/レビュー/修正。本文 | card/writer_view → 凍結本文checkpoint | LLM:本文、コード:hash | writer_viewへ作者真実禁止。DELTA-01 |
| DELTA-01/02/REV | 抽出/レビュー/修正。継続性差分 | 凍結本文+card → 差分checkpoint | LLM:候補、コード:evidence | 完全一致/typed field。DELTA-MERGE |
| DELTA-MERGE | コード処理。mergeと場面採用 | 3 checkpoint → 採用済み場面 | コードのみ | transaction失敗は部分採用なし。次場面/VH-01 |
| VH-01/02/REV | 生成/レビュー/修正。巻handoff | 採用済み巻 → handoff | LLM:要約、コード:境界適用 | 本文成立事実のみ。次巻/VOL-01 |
| COMP-01 | コード処理。完成前提 | 全採用成果物 → 検証記録 | コードのみ | 下記必須条件。COMP-02 |
| COMP-02 | LLM意味監査 | completion input → 監査候補 | LLM:issue、コード:attempt | 正常ならCOMP-03。不正かつ残あり再attempt、不正枯渇は停止 |
| COMP-03 | コード保存 | 正常監査候補 → 監査記録 | コードのみ | 最後の正常を保存。OUT-01 |
| OUT-01/02/03 | staging/検証/公開 | 採用済み正本 → Markdown | コードのみ | 欠落/hash/空本文検証後に原子的公開 |

## 共通項目

| 項目 | 型 | 必須 | 作成者 | 可変性 | 目安・検証 | 正本 |
|---|---|---:|---|---|---|---|
| `volume_number` | integer | はい | コード | 不変 | 1始まり、profile範囲 | 巻設計 |
| `volume_promise` | string | はい | LLM | revision可 | 40〜200字、空禁止 | 巻設計 |
| `thread_actions` | array | はい | LLM | revision可 | 0〜20、既知ID/enum | 巻・場面 |
| `local_key` | string | 初期候補 | LLM | revision可 | 候補内一意 | bundle候補 |
| `id` | string | 採用後 | コード | 不変 | type-prefix、一意 | 台帳 |
| `evidence` | string | 差分 | LLM | revision可 | 凍結本文完全一致 | evidence index |

## continuity_delta

```json
{"existing_item_updates":[],"new_item_proposals":[],"knowledge_updates":[],"thread_updates":[],"ending_evidence_proposals":[],"story_clock_update":{},"handoff_summary":""}
```

`existing_item_updates`は`operation,target_type,target_id,field,before,after,scene_id,evidence`。operationは`set|append|remove|transition`のみで、type/field別許可表、現在値との`before`一致、fixed領域禁止、本文完全一致をコードが検証する。`new_item_proposals`は`local_type,local_key,scope,fixed,current,scene_id,evidence`。LLMはIDを作らず、policyのallowed typeと`max_items`以内だけをコードが採番する。`knowledge_updates`は`fact_id,audience_type,audience_id,before,after,scene_id,evidence`（readerのaudience_idは`reader`固定）。`thread_updates`は`thread_id,operation,before_status,after_status,before_progress,after_progress,scene_id,evidence`、operationは`introduce|advance|resolve|retire`。`ending_evidence_proposals`は`criterion_id,scene_id,evidence,relation`でrelationは`supports|contradicts`。`story_clock_update`は`before_order,after_order,time_label,scene_id,evidence`（場面カードで明確ならevidence省略可）。handoffは本文成立事実のみ、50〜300字目安。

## completion前提

全巻、全章、必要採用場面、非空本文、artifact欠落・重複・hash不一致なし、required major thread完了、required ending criterionごとの検証済み`supports` evidence 1件以上、全ID参照、state/artifact/evidence index正常、**正常completion audit 1件以上**。`contradicts`だけは満たさず、両relationは監査へ渡す。文芸issueは前提に含めない。

## Schema作成一覧

| Schema | 対象工程 | 種別 | LLM項目 / コード項目 | 正本 |
|---|---|---|---|---|
| brief, initial_concept, initial_characters_relationships, initial_world_temporal_rules, initial_series_arcs | INPUT/INIT | 出力 | 候補 / IDなし | bundle候補 |
| initial_design_bundle, review_result | INIT-05/06 | 保存/出力 | bundle・issues / ID・round | bundle |
| volume_design, chapter_design, scene_card | VOL/CH/SC | 出力 | 設計 / 番号・ID | 設計正本 |
| continuity_delta, volume_handoff | DELTA/VH | 出力 | 候補 / merge・採用 | state/index |
| completion_audit | COMP | 出力/保存 | issue / attempt・保存 | audit record |
