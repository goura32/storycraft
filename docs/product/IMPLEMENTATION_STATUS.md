# Storycraft 実装状況

この文書は、Storycraft Version 1の現在のproduction code、自動試験、Release blockerを記録する。仕様や設計の正本ではない。

正本:

- 製品仕様: [`SPECIFICATION.md`](SPECIFICATION.md)
- 要件: [`REQUIREMENTS.md`](REQUIREMENTS.md)
- アーキテクチャ: [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)
- 詳細設計: [`../design/`](../design/)
- 受入試験: [`../testing/ACCEPTANCE.md`](../testing/ACCEPTANCE.md)

更新基準:

```text
確認日: 2026-07-24
確認したmain: 15be118
文書契約: docs/v1-contract-freeze branchの内容
```

この文書へ新しい仕様、field、path、Stage、Recovery規則を追加しない。

## 状態の意味

| 状態 | 意味 |
|---|---|
| `実装済み` | production codeが存在し、対応する自動試験も存在する |
| `部分実装` | production codeまたは自動試験の一部が存在するが、V1契約を完了していない |
| `未実装` | V1 production codeが存在しない |
| `未確認` | 存在は確認したが、現行契約に対する試験成功を確認していない |
| `文書完了` | 正本文書の責務、相互参照、要件追跡を確認済み |

`実装済み`はRelease可能を意味しない。Releaseには[`../testing/ACCEPTANCE.md`](../testing/ACCEPTANCE.md)の必須suite成功が必要である。

## 文書

| 文書 | 状態 |
|---|---|
| repository root `README.md` | `文書完了` |
| `docs/README.md` | `文書完了` |
| `product/SPECIFICATION.md` | `文書完了` |
| `product/REQUIREMENTS.md` | `文書完了` |
| `architecture/ARCHITECTURE.md` | `文書完了` |
| `design/DATA_MODEL.md` | `文書完了` |
| `design/WORKSPACE_AND_RECOVERY.md` | `文書完了` |
| `design/PIPELINE.md` | `文書完了` |
| `design/LLM_INTEGRATION.md` | `文書完了` |
| `testing/ACCEPTANCE.md` | `文書完了` |

文書完了時点で、次を確認する。

```text
要件ID 76件
受入試験ID 79件
全76要件が少なくとも一つの受入試験から参照される
Markdown内部link切れなし
節番号の連続性
廃止した契約記述の除去
文書以外のfile変更なし
```

## V1 Stage実装

### 実装済み

次のStage Service、Prompt／Schema、対応unit testが存在する。

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
```

主なproduction file:

```text
src/storycraft/input_stage.py
src/storycraft/initial_*_stage.py
src/storycraft/series_plan_stage.py
src/storycraft/volume_plan_stage.py
src/storycraft/chapter_plan_stage.py
src/storycraft/scene_plan_stage.py
src/storycraft/scene_card_stage.py
src/storycraft/scene_prose_stage.py
src/storycraft/scene_continuity_stage.py
```

### 未実装

```text
scene_commit
volume_handoff
completion
publication
```

`src/storycraft/stages.py`にStage名が存在するだけでは実装済みとみなさない。

## V1 WorkflowとCLI

| 項目 | 状態 | 根拠・不足 |
|---|---|---|
| V1 Stage Registry | `部分実装` | Stage enumと個別Serviceは存在するが、全Stage dispatchは未完成 |
| V1 Workflow Orchestrator | `未実装` | Recovery、遅延Provider生成、Stage dispatchを統合する実行境界がない |
| 公開`run` | `部分実装` | CLIは存在するが、現在は旧`SeriesService`経路を使用 |
| 公開`resume` | `部分実装` | CLIは存在するが、V1 Recoveryへ未接続 |
| 公開`step` | `部分実装` | CLIは存在するが、V1の一意味Stage境界へ未接続 |
| Workspace Lock | `未確認` | V1公開経路での取得・解放・競合動作を未確認 |
| code-only operationのProvider非依存 | `未実装` | CLI起動時に`OpenAIStoryModel`を生成する現行構造が残る |

現行CLIの存在を、V1 workflow全体の実装完了とはみなさない。

## Data・Workspace・Recovery

| 項目 | 状態 | 根拠・不足 |
|---|---|---|
| `run-state.json` contract | `部分実装` | validatorとtestは存在するが、全Stageの公開実行へ未統合 |
| Workspace layout validator | `部分実装` | V1 layout検証は存在するが、最新Data Modelへの追従が必要 |
| immutable Generation | `部分実装` | Initial Generation作成と検証は存在する |
| immutable Scene | `部分実装` | Scene staging成果物は存在するが、Scene Commit未実装 |
| `pending_commit` | `部分実装` | fieldとphase検証は存在するが、確定・Recovery処理未実装 |
| Scene Commit Crash Recovery | `未実装` | 前進型Recovery Serviceがない |
| Publication Crash Recovery | `未実装` | Publication自体が未実装 |
| Counter不整合検出 | `部分実装` | counter contractは存在するが全Recovery経路の受入試験未実装 |

今回確定した次のData Model変更は、production Schemaとvalidatorへまだ反映されていない。

```text
情報種別ごとのAuthority
Reader Knowledge State
Location State
World State
Inventory whereabouts_status
Continuity target_typeの10種類固定
通常SceneからCanonを変更しない契約
Evidenceから更新情報の重複保存を排除
```

## LLM連携

| 項目 | 状態 | 根拠・不足 |
|---|---|---|
| OpenAI互換client | `実装済み` | 現行model実装が存在する |
| Prompt asset package同梱 | `部分実装` | wheel設定は存在するが、現行文書契約でのsmoke成功を未確認 |
| Review／Revision runner | `実装済み` | structured candidateとprose用runnerが存在する |
| operation別Provider／model | `未実装` | 現行設定は主に単一modelを使用 |
| Provider遅延初期化 | `未実装` | CLI起動時にclientを生成する |
| Recovery前のProvider非生成 | `未実装` | V1 Recovery実行境界がない |
| 4種timeout | `部分実装` | 設定項目はあるが、blocking I/Oを外側から中断できる保証が不足 |
| internal error分類 | `部分実装` | 広い`Exception`捕捉を意味的失敗と分離する必要がある |
| Call前token確認 | `未確認` | 最終送信入力に対するpreflight test未実装 |
| Budget／Audit | `部分実装` | 既存機能はあるがV1 operation単位の受入試験未実装 |

## 自動試験

現在、次のV1 unit test群がrepositoryに存在する。

```text
入力Schema／Stage
Initial Design各Schema／Stage
Initial Generation
Series／Volume／Chapter／Scene Plan
Scene Card
Scene Prose
Scene Continuity
run-state
Stage transition
Workspace
Prompt／model contract
```

ただし、文書契約を更新したため、既存testが成功するだけでは新契約を満たしたことにならない。特に次の受入試験は未実装である。

```text
Scene Commitの全Crash境界
Generationの決定的再構築
V1 CLI縦断
Reader Knowledge更新
Location／World State更新
State Authorityの重複禁止
code-only operationのProvider factory call 0
Recovery中のProvider factory call 0
blocking stream timeout
internal_error分類
Path traversal／symlink拒否
全76要件の自動追跡
```

## Release判定

**Release不可。**

主なblocker:

1. V1公開WorkflowとCLIが未統合。
2. `scene_commit`以降の4 Stageが未実装。
3. V1 Crash Recoveryが未実装。
4. 今回確定したData Modelへproduction Schemaとvalidatorが未追従。
5. Provider遅延初期化とcode-only operationの非依存化が未実装。
6. 79件の受入試験が自動化されていない。
7. 必須suiteとwheel smokeの成功証拠がない。

## 次の実装順

文書完了後は次の順で進める。

```text
1. V1 Workflow実行境界
   Lock → run-state読込 → Recovery → Stage判定
   → 必要な場合だけProvider生成 → Stage実行

2. 最新Data ModelをSchema／validatorへ反映

3. scene_commit
   staging検証 → pending_commit → Scene finalize
   → Generation finalize → run-state一回更新

4. Scene Commit Crash Recovery

5. scene_planから次scene_planまでの一Scene縦断

6. volume_handoff

7. completion

8. publication

9. CLIをV1 Workflowへ切替

10. 受入試験79件とpackage smoke
```

実装開始前に、この文書の「文書」欄がすべて`文書完了`であることを確認する。

## 更新規則

状態を上げる場合は、production file、対応test、実行結果を確認する。名前だけ存在するStage、fixtureだけ存在する試験、legacy経路の成功を根拠にしない。

状態を下げる必要が判明した場合は、理由と不足をこの文書へ反映する。正本文書の契約は、実装状況へ合わせて弱めない。
