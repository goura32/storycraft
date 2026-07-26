# Storycraft V1 Review Findings

## F-001: Stage test workspaceの再構築コスト

状態: 対応中

Stage testのworkspace helperが前段Stageを毎回実行しており、
後段Stageほどfixture構築時間が累積する。

確認値:

- integrated build: 約1.5秒
- series plan build: 約2.0秒
- chapter plan build: 約2.8秒
- scene commit build: 約5.7秒
- workspace copy: 約0.002〜0.01秒

対応方針:

- 完成済みbaselineをprocess内で一度だけ構築
- 各テストには独立copyを渡す
- baselineをテストから直接変更させない

途中結果:

- 対象29テスト: 33.271秒から27.211秒へ短縮
- Initial Integrate 5テスト: 5.951秒から3.971秒へ短縮
- Volume Plan 7テスト: 8.742秒から4.484秒へ短縮
- baseline構築回数はprocess内で各1回
- PlanningからScene Commitまでの77テストは63.381秒から44.801秒へ短縮
- workspace全体検証は288回から214回へ減少
- workspace全体検証時間は58.234秒から40.152秒へ短縮
- Stage wrapperで検証済みの場合、共通runnerの開始時検証を省略

## F-002: Publication test fixtureの契約不整合

状態: 未調査

`create_publication_workspace()`で作成したworkspaceに対して
`validate_workspace_layout()`を実行すると、次のエラーになる。

```text
Completion Resultには全Volume Handoffが必要です
```

Publication testが無効なworkspaceを前提にしている可能性がある。

調査対象:

- Completion Resultが要求するVolume Handoff数
- fixtureのSeries Planに定義された`volume_count`
- `prepare_volume_handoff_workspace()`が作成するHandoff
- Publication Stage testでworkspace全体検証が回避されていないか
- Production経路でも同じ不整合が発生しないか

## 2026-07-26 全体テスト測定

- `python -m unittest discover`で526テストが成功
- 実行時間は157.720秒
- 初期測定の約821秒から約80.8%短縮
- Workflow経由ではPublication以外の全V1 Stageで開始時の重複workspace検証を省略
- Initial ConceptからScene Commitまでの103テストは49.029秒で成功
- Completionまで含む122テストは64.950秒で成功
- 既知のPublication fixture契約エラーF-002は今回の全体テストでは再現しなかった

## F-003: 外部LLM接続疑い

- 状態: 解消（誤検知）
- `LLM接続確認`はFake Clientを使う設定試験のログだった
- 後続の通信エラーログは別のエラー処理試験によるものだった
- 両ログの約41秒差は、その間に多数の通常試験が実行された時間だった
- socket接続を禁止した状態でも526テストが161.239秒で成功
- IPv4／IPv6のconnectおよびconnect_ex呼び出しは検出されなかった

## F-004: 通常テスト実行でnetwork禁止が強制されない

- 状態: 未対応
- 現在のテストが実networkを使用していないことは確認済み
- ただし通常の`unittest discover`では予期しないnetwork接続を自動的に失敗させない
- ACC-LLM-009に従い、network禁止付きの標準テストrunnerを追加する

## 2026-07-26 Acceptance最適化後

- Acceptance 2テストを71.723秒から6.683秒へ短縮
- Acceptance中間工程では重複するworkspace全体検証を延期
- 終端では本物のworkspace全体検証を3回実行
- 全528テストが100.558秒で成功
- テスト収集は528件、重複0件
- 初期測定の約821秒から約87.8%短縮

## 2026-07-26 Schema cache

- Prompt SchemaをPromptTemplateインスタンス内でPath単位にキャッシュ
- Scene Commit直前workspaceの全体検証20回を11.408秒から2.258秒へ短縮
- 1回平均は0.5704秒から0.1129秒へ短縮
- Schema cache entryは15件
- Schema関連43テストが成功

