# Storycraft V1 実装状況

最終確認日: 2026-07-26
確認対象branch: `audit/v1-only-contracts`

この文書は実装状況と検証結果を記録する。新しい仕様や契約は定義しない。

## 判定

V1 production経路は、BriefまたはKeywords入力からMarkdown Publicationまで実装済みである。

Release前の残作業は、外部Providerを使用した最小実LLM smokeと、main統合後の最終確認である。

## Pipeline

以下の全StageをV1 Workflowから実行できる。

- input
- initial_concept
- initial_characters
- initial_relationships
- initial_world
- initial_knowledge
- initial_threads
- initial_ending
- initial_integrate
- initial_accept
- series_plan
- volume_plan
- chapter_plan
- scene_plan
- scene_card
- scene_prose
- scene_continuity
- scene_commit
- volume_handoff
- completion
- publication

正常系Acceptanceでは、Brief入力から全Stageを通過してimmutableなPublicationを生成する。

## CLI

以下を実装済みである。

- `run`: 新規workspaceを作成して終端まで実行
- `resume`: 既存workspaceをRecovery優先で再開
- `step`: StageまたはRecoveryを一工程実行
- `status`: Recovery状態を含むrun-stateをJSON表示
- `validate`: workspace全体を変更せず検証

ProviderはModelが必要なStageでのみ遅延生成する。Brief採用、Recovery、`status`、`validate`ではProviderを必要としない。

## Recovery

以下を実装済みである。

- Candidate Adoption Recovery
- Scene Commit Recovery
- Publication Recovery
- Recovery優先Workflow dispatch
- forward-onlyな確定処理
- Recovery中のProvider非生成
- workspace lock
- atomic file保存
- immutable directory finalize

中断復旧Acceptanceでは、SceneとGenerationの確定後、run-state遷移前にCrashを発生させる。新しい`V1WorkflowService`で再開し、LLM呼び出しを重複させずPublicationまで完了することを確認している。

## Publication

以下を決定的に構築・検証する。

- `metadata.json`
- `completion.json`
- `series.md`
- `vNN.md`
- Series全体の目次
- 各巻の目次
- 巻・章・Sceneの正規順序
- 文字数
- SHA-256
- Completionとの整合性
- basis Generationとの整合性
- Crash Recovery

## PromptとSchema

productionで使用するV1 Prompt assetだけを保持する。

`critique.json`はlegacy資産ではなく、全V1 Review／Revision工程が共有する正規Schemaである。

wheelへPromptとSchemaを同梱し、隔離環境へのinstall後に読み込めることをsmoke testで確認している。

## 検証結果

自動試験:

- `Ran 512 tests`
- `OK`

主要な検証対象:

- 全V1 Schema／Stage
- run-state／Stage transition
- Workspace／Lock
- 各Recovery経路
- 正常系Workflow Acceptance
- 中断・再起動Workflow Acceptance
- Publication目次と改変拒否
- CLI全5コマンド
- Prompt／Model contract

wheel smokeでは以下を確認済みである。

- wheel build
- 隔離venvへのinstall
- インストール済みCLIの起動
- `run / resume / step / status / validate`の登録
- package内Prompt／Schemaの読み込み

## 最終静的監査

以下を確認済みである。

- `git diff --check`成功
- `src/storycraft`全moduleのimport成功
- 削除済みlegacy moduleへの実行時参照なし
- 削除済み旧Prompt Stageへの実行時参照なし
- tracked生成物なし
- conflict markerなし
- TODO／FIXME残存なし

`characters`、`continuity`、`world`などの一般名はV1 Data Modelでも使用するため、単純な文字列一致はlegacy残存を意味しない。

## Release前の残作業

1. 外部Providerを使用した最小実LLM smoke
2. 実LLM workspaceに対する`status`／`validate`
3. 最終差分監査
4. mainへの統合
5. 統合後の全テストとwheel smoke
