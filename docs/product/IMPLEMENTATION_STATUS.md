# Storycraft 実装状況

最終更新日: 2026-07-23

この文書は、Storycraft Version 1について、文書、production code、自動試験、移行作業、Release判断の現在状況を記録する。

この文書は仕様や設計の正本ではない。

正本:

- 製品仕様: [`SPECIFICATION.md`](SPECIFICATION.md)
- 製品要件: [`REQUIREMENTS.md`](REQUIREMENTS.md)
- アーキテクチャ: [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)
- データモデル: [`../design/DATA_MODEL.md`](../design/DATA_MODEL.md)
- 保存と復旧: [`../design/WORKSPACE_AND_RECOVERY.md`](../design/WORKSPACE_AND_RECOVERY.md)
- Pipeline: [`../design/PIPELINE.md`](../design/PIPELINE.md)
- LLM連携: [`../design/LLM_INTEGRATION.md`](../design/LLM_INTEGRATION.md)
- 受入試験: [`../testing/ACCEPTANCE.md`](../testing/ACCEPTANCE.md)

この文書へ、新しい仕様、要件、Stage、path、JSON field、Recovery規則を追加してはならない。

---

# Part I: 状態の意味

## 1. 状態分類

| 状態 | 意味 |
|---|---|
| `完了` | 成果物を作成し、内容確認まで終えている |
| `配置確認待ち` | 完成版は作成済みだが、対象repositoryへの配置を未確認 |
| `実装確認待ち` | 設計は存在するが、production codeと自動試験を未確認 |
| `部分実装` | 一部のproduction codeと対応試験を確認済み |
| `実装済み` | production codeと必要な自動試験を確認済み |
| `未着手` | 作業未開始 |
| `廃止予定` | 新設計への統合後に削除する |
| `阻害` | 先に解消すべき問題がある |

---

## 2. `実装済み`の判定

次をすべて確認した場合だけ`実装済み`とする。

```text
production codeが存在
上位仕様と設計に一致
対応する自動試験が存在
正常系が成功
主要失敗系が成功
必要なCrash試験が成功
installed package環境で成功
```

次だけでは`実装済み`としない。

```text
設計書に記載
classや型だけ存在
関数名だけ存在
正常系を手動実行
legacy testだけ成功
fixtureだけ存在
```

---

## 3. 現時点の確認範囲

確認済み:

```text
簡素化した文書構成
主要文書の完成版
受入試験項目
test fixture一式
旧文書の統合先
```

未確認:

```text
対象repositoryへ全成果物が配置済みか
production codeが新設計へ追従しているか
59件の受入試験が実装済みか
71 fileのfixtureが配置済みか
legacy文書参照をすべて切り替えたか
package smokeが成功するか
```

Production codeについて、証拠なしに`実装済み`とは記録しない。

---

# Part II: 文書刷新

## 4. 完成版を作成した成果物

| 成果物 | 状態 | 内容 |
|---|---|---|
| `docs/architecture/ARCHITECTURE.md` | `配置確認待ち` | 原則、全体像、主要用語、文書責務 |
| `docs/product/SPECIFICATION.md` | `配置確認待ち` | 利用者から見える製品仕様 |
| `docs/product/REQUIREMENTS.md` | `配置確認待ち` | 76件の検証可能要件 |
| `docs/design/DATA_MODEL.md` | `配置確認待ち` | Storyデータの意味上の正本 |
| `docs/design/WORKSPACE_AND_RECOVERY.md` | `配置確認待ち` | 保存、排他、Crash Recovery |
| `docs/design/PIPELINE.md` | `配置確認待ち` | 21 StageとLoop |
| `docs/design/LLM_INTEGRATION.md` | `配置確認待ち` | Provider、Prompt、Context、Retry等 |
| `docs/testing/ACCEPTANCE.md` | `配置確認待ち` | 59件の受入試験 |
| `tests/fixtures/` | `配置確認待ち` | 71 fileのfixture set |
| `docs/product/IMPLEMENTATION_STATUS.md` | `完了` | この文書 |

Repository上で存在と内容を確認した後、`配置確認待ち`を`完了`へ変更する。

---

## 5. 未作成の文書

| 文書 | 状態 | 目的 |
|---|---|---|
| `docs/README.md` | `未着手` | 文書一覧と推奨読書順 |
| `README.md` | `未着手` | 製品紹介、install、quick start |

---

## 6. 最終文書構成

```text
README.md

docs/
├── README.md
├── product/
│   ├── SPECIFICATION.md
│   ├── REQUIREMENTS.md
│   └── IMPLEMENTATION_STATUS.md
├── architecture/
│   └── ARCHITECTURE.md
├── design/
│   ├── DATA_MODEL.md
│   ├── WORKSPACE_AND_RECOVERY.md
│   ├── PIPELINE.md
│   └── LLM_INTEGRATION.md
└── testing/
    └── ACCEPTANCE.md

tests/
└── fixtures/
```

---

# Part III: 旧文書の移行

## 7. Architecture系

| 旧文書 | 状態 | 統合先 |
|---|---|---|
| `docs/architecture/ARCHITECTURE_PRINCIPLES.md` | `廃止予定` | `ARCHITECTURE.md` |
| `GLOSSARY.md` | `作成しない` | `ARCHITECTURE.md` |
| `DOCUMENT_STRUCTURE.md` | `作成しない` | `ARCHITECTURE.md`と`docs/README.md` |
| `SYSTEM_ARCHITECTURE.md` | `作成しない` | `ARCHITECTURE.md` |

---

## 8. Pipeline・Engine系

| 旧文書 | 状態 | 統合先 |
|---|---|---|
| `docs/design/series_engine_design.md` | `廃止予定` | `ARCHITECTURE.md`、`PIPELINE.md` |
| `docs/design/series_engine_flow.md` | `廃止予定` | `PIPELINE.md` |
| `docs/design/pipeline_contracts.md` | `廃止予定` | `PIPELINE.md` |
| `docs/design/contracts/pipeline/*` | `廃止予定` | `PIPELINE.md` |

---

## 9. Workspace・Recovery系

| 旧文書 | 状態 | 統合先 |
|---|---|---|
| `docs/design/workspace_layout.md` | `廃止予定` | `WORKSPACE_AND_RECOVERY.md` |
| `docs/design/runtime_and_recovery.md` | `廃止予定` | `WORKSPACE_AND_RECOVERY.md` |
| `docs/design/contracts/ledger/runtime_records.md` | `廃止予定` | `WORKSPACE_AND_RECOVERY.md` |
| `docs/design/ledger_contracts.md`の保存部分 | `廃止予定` | `WORKSPACE_AND_RECOVERY.md` |

---

## 10. Data系

| 旧文書 | 状態 | 統合先 |
|---|---|---|
| `docs/design/ledger_contracts.md`の意味部分 | `廃止予定` | `DATA_MODEL.md` |
| `docs/design/contracts/ledger/*` | `廃止予定` | `DATA_MODEL.md` |
| `docs/design/contracts/data/*` | `廃止予定` | `DATA_MODEL.md` |
| `docs/design/data_contract_examples.md` | `廃止予定` | `DATA_MODEL.md`、`tests/fixtures/` |
| `docs/design/examples/*.md` | `廃止予定` | `tests/fixtures/` |

---

## 11. LLM系

| 旧文書 | 状態 | 統合先 |
|---|---|---|
| `docs/design/context_contracts.md` | `廃止予定` | `LLM_INTEGRATION.md` |
| `docs/design/prompt_template_design.md` | `廃止予定` | `LLM_INTEGRATION.md` |
| `docs/design/configuration_contracts.md` | `廃止予定` | `LLM_INTEGRATION.md`と実装Schema |
| `docs/design/contracts/data/review_and_audit.md` | `廃止予定` | `DATA_MODEL.md`、`LLM_INTEGRATION.md` |

---

## 12. Acceptance系

| 旧文書 | 状態 | 統合先 |
|---|---|---|
| `docs/design/implementation_acceptance.md` | `廃止予定` | `docs/testing/ACCEPTANCE.md` |
| Markdown内の巨大fixture | `廃止予定` | `tests/fixtures/` |

---

## 13. 旧文書の削除開始条件

```text
新文書がrepositoryに存在
相互linkが有効
root READMEから新文書へ到達可能
docs/READMEから新文書へ到達可能
production codeが旧pathへ依存していない
testが旧fixtureへ依存していない
repository全体検索で旧参照を把握済み
```

---

# Part IV: 要件実装

## 14. 要件総数

| 分類 | 件数 | 状態 |
|---|---:|---|
| 機能要件 | 34 | `実装確認待ち` |
| データ・保存要件 | 8 | `実装確認待ち` |
| 運用要件 | 10 | `実装確認待ち` |
| 再開・復旧要件 | 8 | `実装確認待ち` |
| 安全性・秘密情報要件 | 8 | `実装確認待ち` |
| 非機能・Release要件 | 8 | `実装確認待ち` |
| **合計** | **76** | `実装確認待ち` |

未実装と断定しているのではなく、production codeと試験の照合が未完了である。

---

## 15. 機能領域

| 領域 | 設計 | Production code | 自動試験 | 状態 |
|---|---|---|---|---|
| Brief | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Keywords | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Initial Design | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Series Plan | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Volume Plan | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Chapter Plan | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Scene Plan | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Scene Card | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Scene本文 | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Continuity | 完成 | 未確認 | fixtureあり・test未確認 | `実装確認待ち` |
| Scene Commit | 完成 | 未確認 | Crash fixtureあり | `実装確認待ち` |
| Volume Handoff | 完成 | 未確認 | fixtureあり | `実装確認待ち` |
| Completion | 完成 | 未確認 | 3状態fixtureあり | `実装確認待ち` |
| Publication | 完成 | 未確認 | 4巻fixtureあり | `実装確認待ち` |

---

## 16. CLI

| 項目 | 状態 | 主な確認 |
|---|---|---|
| `run` | `実装確認待ち` | 既存workspaceを上書きしない |
| `resume` | `実装確認待ち` | Recovery後の正しいStage |
| `step` | `実装確認待ち` | 一つの意味的Stage |
| help | `実装確認待ち` | 三commandと利用方法 |
| error code | `実装確認待ち` | 安定したcode |
| progress表示 | `実装確認待ち` | Stage、巻、章、Scene、停止理由 |

---

# Part V: データ・保存

## 17. Schema

| 項目 | 状態 |
|---|---|
| Brief Schema | `実装確認待ち` |
| Initial Design Schema | `実装確認待ち` |
| Plan Schema | `実装確認待ち` |
| Scene Card Schema | `実装確認待ち` |
| Continuity Schema | `実装確認待ち` |
| Generation Schema | `実装確認待ち` |
| Handoff Schema | `実装確認待ち` |
| Completion Schema | `実装確認待ち` |
| Publication Metadata Schema | `実装確認待ち` |

厳密なSchema assetが一つのrootへ統合されているか確認する。

---

## 18. Workspace

| 項目 | 状態 |
|---|---|
| 単一writer lock | `実装確認待ち` |
| run-state唯一Authority | `実装確認待ち` |
| Counter予約 | `実装確認待ち` |
| atomic file replacement | `実装確認待ち` |
| stagingからfinalize | `実装確認待ち` |
| immutable final directory | `実装確認待ち` |
| orphan隔離 | `実装確認待ち` |
| path traversal防止 | `実装確認待ち` |

---

## 19. 旧保存機構

Production codeに次が残っていないか確認する。

```text
canon/HEADをAuthorityにする処理
output/CURRENTをAuthorityにする処理
Candidate Manifest
Checkpoint Manifest
Generation Manifest graph
Publication Gate
hash chain
Manifest reachability Recovery
```

---

# Part VI: Pipeline

## 20. 目標Stage

```text
input
initial_concept
initial_characters
initial_relationships
initial_world
initial_knowledge
initial_threads
initial_ending
initial_integrate
initial_accept
series_plan
volume_plan
chapter_plan
scene_plan
scene_card
scene_prose
scene_continuity
scene_commit
volume_handoff
completion
publication
```

合計21 Stage。

現在のproduction Stage Registryは未確認である。

---

## 21. 廃止対象Stage

```text
SC-CHK
PROSE-CHK
DELTA-CHK
COMMIT-01
COMMIT-02
COMMIT-03
COMMIT-04
COMP-PRE
COMP-SAVE
OUT-01
OUT-02
OUT-03
COMP-PUBLISH
```

必要な処理は内部operationへ統合する。

---

## 22. Review／Revision

| 項目 | 状態 |
|---|---|
| ReviewがCandidateを書き換えない | `実装確認待ち` |
| Revisionが完全置換 | `実装確認待ち` |
| Revision後に再Review | `実装確認待ち` |
| transport／format／revision分離 | `実装確認待ち` |
| 上限到達時にblocked | `実装確認待ち` |

---

# Part VII: LLM連携

## 23. Provider Adapter

| 項目 | 状態 |
|---|---|
| 共通Adapter interface | `実装確認待ち` |
| Provider error正規化 | `実装確認待ち` |
| Usage正規化 | `実装確認待ち` |
| structured response | `実装確認待ち` |
| prose response | `実装確認待ち` |
| streaming中断 | `実装確認待ち` |

---

## 24. Prompt asset

| 項目 | 状態 |
|---|---|
| 一つのPrompt asset root | `実装確認待ち` |
| installed packageへ同梱 | `実装確認待ち` |
| source tree fallbackなし | `実装確認待ち` |
| Prompt version | `実装確認待ち` |
| Operation Registry | `実装確認待ち` |

---

## 25. Context

| 項目 | 状態 |
|---|---|
| basis Generation明示 | `実装確認待ち` |
| operation別最小Context | `実装確認待ち` |
| Writer秘密情報filter | `実装確認待ち` |
| 非POV内面の除外 | `実装確認待ち` |
| token上限前確認 | `実装確認待ち` |
| hash名Context path廃止 | `実装確認待ち` |

---

## 26. Credential・Audit

| 項目 | 状態 |
|---|---|
| Credentialをworkspace外から取得 | `実装確認待ち` |
| request記録から秘密値を除外 | `実装確認待ち` |
| log redaction | `実装確認待ち` |
| Call IDとattempt | `実装確認待ち` |
| Stage・operation・usage | `実装確認待ち` |

---

# Part VIII: Recovery

## 27. 三分類

```text
resume
regenerate
manual
```

この分類がproduction codeへ実装されているか確認する。

---

## 28. Scene Commit Crash

| Crash位置 | 期待結果 | 状態 |
|---|---|---|
| pending設定前 | stagingを再生成 | `実装確認待ち` |
| Scene rename後 | Generation finalizeまたは人間対応 | `実装確認待ち` |
| Generation rename後 | run-state更新のみ | `実装確認待ち` |
| run-state更新後 | pending整理 | `実装確認待ち` |

---

## 29. Publication Crash

| Crash位置 | 期待結果 | 状態 |
|---|---|---|
| rename前 | stagingを再生成 | `実装確認待ち` |
| rename後 | current Publicationとcompletedを更新 | `実装確認待ち` |
| completed更新後 | pending整理 | `実装確認待ち` |

---

## 30. 自動修復禁止

次が自動実行されていないことを確認する。

```text
不正run-stateからの推測復元
過去Generationへの黙った巻戻し
Counterの自動再採番
競合final directoryの自動削除
古いtmp fileの自動採用
Completion incompleteの自動再試行
```

---

# Part IX: 試験

## 31. 受入試験

`docs/testing/ACCEPTANCE.md`には59件の受入試験を定義済み。

```text
試験仕様:
  完成版作成済み

試験コード:
  未確認

実行結果:
  未確認
```

---

## 32. Fixture

71 fileのfixture setを作成済み。

```text
brief
keywords
initial-design
plans
scene
generation
handoff
completion
publication
workspace
recovery
provider
security
invalid
```

```text
fixture内容:
  作成済み

repository配置:
  確認待ち

test codeからの利用:
  未確認
```

---

## 33. 必須suite

| Suite | 状態 |
|---|---|
| unit | `実装確認待ち` |
| schema | `実装確認待ち` |
| workspace | `実装確認待ち` |
| pipeline | `実装確認待ち` |
| provider contract | `実装確認待ち` |
| security | `実装確認待ち` |
| crash recovery | `実装確認待ち` |
| end-to-end | `実装確認待ち` |
| package smoke | `実装確認待ち` |

---

## 34. 最優先試験

```text
Lock競合
run-stateのatomic replacement
Scene rename後Crash
Generation rename後Crash
Publication rename後Crash
Recovery冪等性
Writer秘密情報除外
Evidence quote照合
allowed updates外の拒否
incomplete時のPublication禁止
Publication中のProvider call 0
installed packageからPrompt読込
```

---

# Part X: Release

## 35. 現在の判定

```text
Release不可
```

理由:

```text
production codeの設計適合性を未確認
59件の受入試験実装を未確認
必須suite結果を未確認
package smokeを未確認
legacy文書と旧設計参照の削除未完了
```

実装が必ず未完成だという断定ではない。

Release可能と判断する証拠がまだ揃っていない。

---

## 36. Release可能条件

```text
全正本文書をrepositoryへ配置
旧文書参照の切替完了
76要件の実装追跡完了
59受入試験の自動化
必須suite成功
必須試験skipなし
実network依存なし
実Credential依存なし
package smoke成功
秘密情報漏洩なし
Crash Recovery成功
```

---

# Part XI: 次の作業

## 37. 文書作業

```text
1. docs/README.mdを作成
2. root README.mdを全面改訂
3. Markdown linkを新構成へ切替
4. 旧文書参照を検索
5. 旧文書を削除
6. link checkを実行
```

---

## 38. 実装確認順

```text
1. package構成
2. CLI
3. Workspace API
4. Schema
5. Stage Registry
6. Transition Engine
7. Provider Adapter
8. Context Builder
9. Review／Revision
10. Completion
11. Publication Builder
12. Recovery
13. Test suite
```

---

## 39. Requirement trace

各要件について次を追跡する。

```text
Requirement ID
production code
test ID
test file
最新結果
未対応内容
```

機械生成できる場合は、test metadataからsummaryを生成する。

---

## 40. Repository検索

旧文書と旧実装を削除する前に検索する。

```text
ARCHITECTURE_PRINCIPLES
series_engine_design
series_engine_flow
workspace_layout
runtime_and_recovery
pipeline_contracts
ledger_contracts
context_contracts
prompt_template_design
implementation_acceptance
Publication Gate
Candidate Manifest
Checkpoint Manifest
payload_set_sha256
content_set_sha256
CURRENT
HEAD
```

---

# Part XII: 更新規則

## 41. 更新タイミング

```text
文書をrepositoryへ配置
production codeを確認
自動試験を追加
必須suiteを実行
阻害要因を発見
Release判定を変更
旧文書を削除
```

---

## 42. 状態変更の証拠

状態を`実装済み`へ変更する場合は、少なくとも次を記録する。

```text
対象commit
production code path
test path
test ID
実行command
実行結果
確認日
```

---

## 43. 状態の後退

以前`実装済み`だった機能が、仕様変更またはtest失敗で保証できなくなった場合は、`部分実装`または`阻害`へ戻す。

過去のStatusを守るために失敗を隠さない。

---

## 44. 肥大化防止

この文書へ次を追加しない。

```text
詳細な設計説明
全Schema
全Stage契約
全試験手順
長い障害調査log
全commit履歴
```

---

## 45. Release後

Release後は次を簡潔に示す。

```text
Release version
対応要件数
必須suite結果
既知の制限
次Versionの未着手項目
```

---

## 46. 現在の要約

2026-07-23時点:

```text
文書構成:
  簡素化設計へ再構成中

主要正本文書:
  完成版作成済み
  repository配置確認待ち

受入試験:
  59件を定義済み
  test code未確認

Fixture:
  71 fileを作成済み
  repository配置とtest利用は未確認

Production code:
  新設計への適合を未確認

旧文書:
  統合先を決定済み
  削除は参照切替後

Release:
  不可
```
