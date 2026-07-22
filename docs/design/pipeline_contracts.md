# Pipeline contracts

> 工程入出力の正本。状態・台帳は[ledger contracts](ledger_contracts.md)、保存先は[workspace layout](workspace_layout.md)、順番は[生成フロー](series_engine_flow.md)を正本とする。Schemaファイルは今回作成しない。

## 共通実行契約

各工程は下表のフィールド契約を持つ。件数・文字数はLLM出力の現実的な上限で、文芸品質の絶対評価ではない。

| 区分 | 必須記載 |
|---|---|
| 実行条件 | 前工程が採用済み、又は明示されたretry条件 |
| 入力 | `name: type / 必須性 / 正本 / 件数・文字数` |
| 出力 | `name: type / 必須性 / LLM生成又はコード付与 / 出力状態` |
| 可視性 | 参照可能情報、writer等の参照禁止情報 |
| 更新 | 更新可能データ、更新禁止データ |
| 検証 | ID、型、参照、evidence、hash、件数、順序 |
| retry | transport / response structure / revision roundの適用可否 |
| 採用・保存 | 採用条件、保存先、失敗時、次工程 |

transport retryは通信失敗だけ、response structure retryはparse/Schema/必須項目だけ、revision roundは**構造正常なレビューがissueを返した場合**だけを数える。正常レビュー後のrevisionは候補全体と全issueを一回で修正する。回数枯渇時、最後の構造正常候補を残存issueとともに採用する。構造不正・参照不正・evidence不一致は採用しない。

## 工程カタログ

| ID | 工程名・種類・目的 | 実行条件 / 入力（型・正本） | 出力（型・作成者・状態） | 参照/禁止・更新 | 検証 / retry / 採用 / 保存 / 次工程 |
|---|---|---|---|---|---|
| INPUT-01 | brief生成/入力 | run開始。keywords:`array<string>`又はbrief:`object` | brief:`object`、LLM又は入力複写、正本候補 | keywordsのみ。Canon更新不可 | 必須値、response retry。`plans/series-map.json`。INIT-01 |
| INIT-01 | コンセプト生成 | brief:`object` | concept:`object`、LLM、内部成果物 | briefのみ。更新不可 | 構造だけ検証、reviewなし。checkpoint。INIT-02 |
| INIT-02 | 人物・関係生成 | brief/concept | characters/relationships:`array<object>`、LLM、内部成果物 | local_key参照可、永続ID禁止 | local_key一意、構造だけ。INIT-03 |
| INIT-03 | 世界・時間規則生成 | 01/02 | entities/rules:`array<object>`、LLM、内部成果物 | 既知local_keyのみ | 構造だけ。INIT-04 |
| INIT-04 | 長期arc・thread・criteria生成 | 01-03 | arcs/threads/criteria:`array<object>`、LLM、内部成果物 | 作者真実は許可、writer viewへ渡さない | local_key参照、構造だけ。INIT-05 |
| INIT-05 | bundle統合/コード | 01-04内部成果物 | bundle candidate:`object`、コード、正本候補 | 全候補参照。意味更新禁止 | local_key完全性。`runtime/checkpoints/`。INIT-06 |
| INIT-06 | bundleレビュー/LLM | bundle candidate | review:`object`、LLM、監査記録 | bundle全体。個別成果物再レビュー禁止 | review型。issueあり→INIT-REV、clean/上限→INIT-ID。`audit/reviews/` |
| INIT-REV | bundle一括修正/LLM | candidate+全issues | bundle candidate:`object`、LLM、正本候補 | issue引用fieldのみ。新事実禁止 | 構造、revision round。INIT-06 |
| INIT-ID | 採番・参照変換・採用/コード | 構造正常bundle | initial bundle/canon/state:`object`、コード、採用済み正本 | local_keyのみ変換。採番後の意味修正禁止 | 永続ID、参照、hash。`canon/`。VOL-01 |
| VOL-01 | 巻設計生成/LLM | bundle,current canon,story state,handoff,target volume | volume design:`object`、LLM、正本候補 | 現在Canon/State可。作者真実は必要最小限 | volume番号、thread ID。VOL-02 |
| VOL-02 | 巻設計レビュー/LLM | volume candidate+同入力 | review:`object`、LLM、監査記録 | future未執筆計画可 | 型。issue→VOL-REV、clean/上限→採用。`audit/reviews/` |
| VOL-REV | 巻設計一括修正/LLM | volume candidate+全issues | volume candidate、LLM、正本候補 | 引用fieldのみ | 構造/revision。VOL-02 |
| CH-01 | 章設計生成/LLM | 採用巻設計,current canon/state | chapters:`array<object>`、LLM、正本候補 | 既知thread/volume参照 | 連番、場面数。CH-02 |
| CH-02 | 章設計レビュー/LLM | chapters+巻設計 | review、LLM、監査記録 | - | 型。issue→CH-REV、clean/上限→採用 |
| CH-REV | 章設計一括修正/LLM | candidate+全issues | chapters、LLM、正本候補 | 引用fieldのみ | 構造/revision。CH-02 |
| SC-01 | 場面カード生成/LLM | 採用章、current canon/state、writer projection | scene card:`object`、LLM、checkpoint | writerにauthor_truth/他者内面禁止 | `new_item_policy.max_items:int>=0`、既知ID。SC-02 |
| SC-02 | 場面カードレビュー/LLM | card+同入力 | review、LLM、監査記録 | - | 型。issue→SC-REV、clean/上限→PROSE-01 |
| SC-REV | 場面カード一括修正/LLM | card+全issues | card、LLM、checkpoint | 引用fieldのみ | 構造/revision。SC-02 |
| PROSE-01 | 本文生成/LLM | 採用card+writer view | prose:`string`、LLM、凍結checkpoint | author_truth/未来確定情報禁止 | 非空、文字数500〜5000目安、hash。PROSE-02 |
| PROSE-02 | 本文レビュー/LLM | prose+card | review、LLM、監査記録 | - | 型。issue→PROSE-REV、clean/上限→DELTA-01 |
| PROSE-REV | 本文全体修正/LLM | prose+全issues | prose、LLM、凍結checkpoint | 指摘範囲だけ、card契約維持 | 構造/revision。PROSE-02 |
| DELTA-01 | 継続性差分抽出/LLM | 凍結prose+card+投影state | continuity delta:`object`、LLM、checkpoint | frozen proseのみ根拠 | 全配列必須、evidence完全一致。DELTA-02 |
| DELTA-02 | 差分レビュー/LLM | delta+同入力 | review、LLM、監査記録 | fixed/author truth更新禁止 | 型。issue→DELTA-REV、clean/上限→MERGE |
| DELTA-REV | 差分全体修正/LLM | delta+全issues | delta、LLM、checkpoint | 引用fieldのみ | before/evidence/型。DELTA-02 |
| DELTA-MERGE | 更新・場面採用/コード | card/prose/delta checkpoint | canon/state/index/artifact、採用済み正本 | 更新許可fieldのみ | transaction、before/after、ID、clock+1、hash。`artifacts/`。次場面/VH-01 |
| VH-01 | 巻handoff生成/LLM | 採用済み巻、current canon/state | handoff:`object`、LLM、正本候補 | 採用本文由来のみ | 50〜300字。VH-02 |
| VH-02 | handoffレビュー/LLM | handoff+巻 | review、LLM、監査記録 | - | issue→VH-REV、clean/上限→採用 |
| VH-REV | handoff一括修正/LLM | handoff+全issues | handoff、LLM、正本候補 | 引用fieldのみ | 構造/revision。VH-02 |
| COMP-PRE | 監査前Gate/コード | 全採用成果物、canon/state/index | preflight:`object`、コード、監査記録 | 変更禁止 | 全巻/章/場面、非空prose、artifact/hash、required thread、required criterion supports、ID、canon/state/index。失敗→停止、成功→COMP-AUDIT |
| COMP-AUDIT | 意味監査/LLM | COMP-PRE成功、全体要約/evidence | audit:`object`、LLM、監査候補 | 本文/Canon更新禁止 | 正常JSON→保存候補。構造不正＋attempt残→再監査、枯渇→停止。意味issueは続行可 |
| COMP-PUBLISH | 公開前Gate/コード | COMP-PRE成功、正常audit>=1、staging | publish gate:`object`、コード、監査記録 | outputのみ更新可 | staging検証。失敗→停止、成功→OUT-01 |
| OUT-01 | staging出力/コード | 採用artifact | manuscript/report:`files`、コード、staging | raw/checkpoint禁止 | 欠落/空/hash。OUT-02 |
| OUT-02 | staging検証/コード | staging files | verification:`object`、コード | - | link/hash/manifest。OUT-03 |
| OUT-03 | 原子的公開/コード | publish gate+staging | output files、コード、公開原稿 | outputへ内部情報禁止 | replace+dir fsync。完了 |

## 入出力フィールド定義

| object.field | 型 | 必須 | 作成者 | 状態 | 正本 / 目安 |
|---|---|---:|---|---|---|
| `volume_design.volume_number` | integer | はい | コード | candidate/adopted | 1始まり |
| `.volume_promise` | string | はい | LLM | candidate | 40〜200字 |
| `.thread_actions` | array<object> | はい | LLM | candidate | 0〜20、既知thread ID |
| `chapter_design.chapter_number,scene_count` | integer | はい | コード/LLM | candidate | 1始まり/1〜20 |
| `scene_card.scene_id` | string | はい | コード | checkpoint | `v01-c001-s001` |
| `.new_item_policy.allowed_types,max_items` | array/ integer | はい | LLM | checkpoint | max_items 0〜profile上限 |
| `prose.content` | string | はい | LLM | checkpoint | 500〜5000字目安 |
| `review.issues` | array<object> | はい | LLM | audit | 0〜100 |
| `completion_audit.issues` | array<object> | はい | LLM | audit | 意味issueは非停止 |

## continuity deltaとcompletion gate

`continuity_delta`は`existing_item_updates,new_item_proposals,knowledge_item_proposals,knowledge_updates,thread_updates,ending_evidence_proposals,story_clock_update,handoff_summary`を全て必須キーとして持つ。詳細fieldは[ledger contracts](ledger_contracts.md)を正本とする。

COMP-PREは監査結果を要求しない。COMP-AUDITは正常JSONを1件以上作れなければ停止する。COMP-PUBLISHはCOMP-PRE成功、正常audit 1件以上、staging検証成功を要求する。required ending criterionは検証済み`supports` evidence 1件以上を要求し、`contradicts`だけでは満たさない。両relationは監査入力に含め、意味issueは保存するが停止条件ではない。
