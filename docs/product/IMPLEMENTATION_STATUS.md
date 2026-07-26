# Storycraft V1 実装状況

最終確認日: 2026-07-26
確認対象branch: `audit/v1-only-contracts`

この文書は実装状況と検証結果を記録する。新しい仕様や契約は定義しない。

## 判定

V1 production経路は、BriefまたはKeywords入力からMarkdown Publicationまで実装され、mainへ統合済みである。527件の自動試験と隔離wheel build／install smokeが成功している。Initial Conceptの実LLM smokeではStructured Outputs、批評・改稿ループ、変更範囲制約まで確認済みである。Stage別critique Schema追加後の最終実LLM再試験は意図的に省略した。

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

- `Ran 527 tests`
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

## LLM Structured Outputsと品質契約

以下を実装済みである。

- Generate／Critique／RevisionへStage別production JSON Schemaを送信
- OpenAI互換APIのstrict `json_schema` response formatを使用
- Scene Prose批評は互換性のため`json_object` modeを維持
- Stage専用critique Schemaが存在する場合は共通Schemaより優先
- Stage専用Schemaが存在しない場合は共通`critique.json`へfallback
- Initial Conceptのcritique `field`を8つのトップレベルfieldへ限定
- Briefの`tone`を完全一致で保持
- critiqueの指摘を候補内の実在する根拠へ限定
- revisionで批評対象外fieldを変更することを禁止
- `quality.max_critique_passes`をV1 Candidate runnerへ正しく反映

Initial Conceptの実LLM smokeでは、次を確認した。

- Stage JSON Schemaによる構造制約
- Brief toneの完全一致
- 批評から改稿へのfield限定
- `max_critique_passes: 2`による2回のRevision実行
- 不正なcritique fieldをValidatorが拒否すること

この実LLM確認を根拠にStage専用critique Schemaを追加した。
追加後の最終実LLM再試験は実施していない。

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

## Release確認結果

以下を完了した。

1. Initial Conceptを対象とした実LLM smoke
2. 実LLM workspaceに対する`status`／`validate`
3. 最終差分監査
4. PR #24によるmainへの統合
5. 統合前の全527件の自動試験
6. wheel build／隔離install／package asset smoke

Stage別critique Schema追加後の最終実LLM再試験は、
費用と実行時間を考慮して意図的に省略した。
この未実施項目は、自動試験またはwheel smokeの失敗を意味しない。
