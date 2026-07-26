# Storycraft V1 Review Findings

## F-001: Stage test workspaceの再構築コスト

- 種別: 試験性能
- 重要度: 高
- 状態: 解消済み


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

- 種別: 試験fixture整合性
- 重要度: 高
- 状態: 解消済み


`create_publication_workspace()`で作成したworkspaceに対して
`validate_workspace_layout()`を実行すると、次のエラーになる。

```text
Completion Resultには全Volume Handoffが必要です
```

Publication testは当初、無効なworkspaceを前提にしていた。

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

- 種別: 調査誤検知
- 重要度: 低
- 状態: 撤回

- `LLM接続確認`はFake Clientを使う設定試験のログだった
- 後続の通信エラーログは別のエラー処理試験によるものだった
- 両ログの約41秒差は、その間に多数の通常試験が実行された時間だった
- socket接続を禁止した状態でも526テストが161.239秒で成功
- IPv4／IPv6のconnectおよびconnect_ex呼び出しは検出されなかった

## F-004: 通常テスト実行でnetwork禁止が強制されない

- 種別: 試験隔離
- 重要度: 高
- 状態: 未対応

- 現在のテストが実networkを使用していないことは確認済み
- ただし通常の`unittest discover`では予期しないnetwork接続を自動的に失敗させない
- ACC-TEST-001およびACCEPTANCE 95「Network禁止」に従い、network禁止付きの標準テストrunnerを追加する
- REQUIREMENTS確認: REQ-NFR-006は実networkを必要としないことだけを要求し、予期しない接続を試験失敗にする契約はAcceptance 95だけに存在する
- ACCEPTANCE 89・95はUnit、integration、acceptanceの必須suiteで予期しないnetwork接続を試験失敗とするが、標準実行経路での強制が未実装
- 全82 Python test file、pytest設定、conftestを静的確認したが、socket遮断、pytest-socket、no-network fixture等の実装兆候が0件

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

## F-005: 自動試験件数の記載が古い

- 種別: 文書整合性
- 重要度: 低
- 状態: 未対応

- READMEおよびIMPLEMENTATION_STATUSは527件成功と記載している
- 現在の必須suiteは532件で、全件成功している
- 仕様レビュー完了後、実装状況文書とREADMEを変更順序に従って更新する

## F-006: Briefの開始可能条件が未定義

- 種別: 製品仕様の曖昧さ
- 重要度: 中
- 状態: 未対応
- SPECIFICATION 10は「安全に開始できる最低限の情報」を定義していない
- 内部field一覧ではなく、意味的な最低開始条件を製品仕様で定義する必要がある
- DATA_MODEL確認: Brief不変条件としてpremise、4〜10のvolume_count、language=jaが定義されているが、利用者向け仕様へ反映されていない
- PIPELINE 25もBriefの最低開始条件としてpremise、4〜10の巻数、日本語前提、入力条件の非矛盾を要求する

## F-007: 巻数決定と検証の時点が曖昧

- 種別: 製品仕様の曖昧さ
- 重要度: 中
- 状態: 未対応
- 利用者が巻数を指定しない場合、作品設計から巻数を決定するとされている
- 一方で範囲外の場合は「処理を開始しない」とされ、どの工程を開始しないのか不明
- 利用者指定時と自動決定時の検証時点を分けて定義する必要がある
- DATA_MODEL確認: volume_countはBrief確定時点の必須不変条件であり、作品設計後に決定する余地がない
- PIPELINE 22〜25はBrief採用前にvolume_countを確定・検証するため、Initial Designから巻数を決定する上位仕様と一致しない

## F-008: stepの外部境界が製品仕様で未定義

- 種別: 製品仕様の曖昧さ
- 重要度: 高
- 状態: 未対応
- 「意味のある一つの処理段階」が生成、Review、Revision、採用、外部Stageのどれか不明
- 公開CLIの利用者向け契約なので、PIPELINEだけでなくSPECIFICATIONにも境界が必要
- Recoveryだけで正常化した場合のstep結果も明記する必要がある
- ARCHITECTURE確認: Review／RevisionはStage内operation、Schema確認・ID割当・rename・状態反映は内部処理であり、独立stepではない
- WORKSPACE_AND_RECOVERY 105はstepが一つの意味的Stageと内部確定処理を完了すると定義するが、Recoveryだけで前Stageが完了した場合に終了するか次Stageへ進むかは未定義
- PIPELINE 19はStage出力の採用・確定と次Stageへのrun-state更新までをStage完了条件とする
- PIPELINE 111〜113は通常stepの完了単位を明確にするが、Recoveryで前Stageが完了した場合にそれを一stepと数えるか、さらに次Stageを実行するかは未定義
- PIPELINE 138はRecovery後に正しいStageへ戻ることだけを要求し、step起動時にRecoveryで前Stageが完了した場合の外部停止境界を試験対象にしていない
- ACCEPTANCE 9は新規workspaceでstepを実行するが、Workspace／Pipelineはstepがworkspace初期化を担当するか定義していない
- test_pending_commit_recovery_returns_without_running_next_stageにより、実装はstep／workflow起動時にRecoveryで前Stageを完了した場合、次Stageを追加実行せず返る動作を採用している
- CLI実装試験はcreate_workspace後にcmd_stepを呼び、runを新規作成、stepを既存workspace操作としている。ACC-E2E-003の新規workspaceでstep実行とは一致しない
- 入力・CLI 27件の実行でも、cmd_stepは初期化済みworkspaceを対象とする実装であることを確認した

## F-009: 停止要求と停止完了の契約が曖昧

- 種別: 製品仕様の曖昧さ
- 重要度: 中
- 状態: 未対応
- 停止要求受付と安全な停止完了が区別されていない
- 停止完了時に残す永続状態と、利用者へ示す状態を定義する必要がある
- WORKSPACE_AND_RECOVERY 106は安全境界後にCandidateを保存しstoppedへ更新する処理を定義するが、停止要求受付時のstopping遷移とそのCrash Recoveryは未定義
- LLM_INTEGRATION 133〜135はcancel可能時の取消と、cancel不可時に応答またはtimeoutまで待って未採用とする動作を定義するが、stopping遷移とCrash Recoveryは未定義

## F-010: 最終巻HandoffとCompletion開始条件が曖昧

- 種別: 製品仕様の欠落
- 重要度: 高
- 状態: 未対応
- 各巻に最終巻を含むか、Completionに全巻Handoffが必要かが明記されていない
- F-002のCompletion契約不整合と直接関係する
- 最終巻Handoffの目的とCompletion開始条件を定義する必要がある
- REQUIREMENTS確認: REQ-FR-028は最終巻を含む各巻Handoffを次巻計画または完結判定へ渡すと定める
- ARCHITECTURE確認: Completion前確認にも全Volume Handoffの存在条件が含まれていない
- DATA_MODEL 77は最終巻を含むHandoffを次巻またはCompletionへ渡すと明記している
- DATA_MODEL 85と97は最終HandoffだけをCompletion入力として示しており、全Volume Handoffを要求する既存Completion契約と一致しない

## F-011: Design Revision／Plan Revisionが製品機能として未定義

- 種別: 製品仕様の欠落
- 重要度: 高
- 状態: 未対応
- Continuityで扱えない変更やincomplete後の修正方法として参照されるが、公開操作と遷移がない
- V1で提供するか、人間修正または新規実行とするかを決める必要がある
- REQUIREMENTS確認: REQ-FR-014およびREQ-FR-021もPlan Revision／Design Revisionを必須処理として参照する
- ARCHITECTURE確認: 確定成果物の修正は新しいIDまたはversionとする原則があるが、Revisionを開始・遷移する公開workflowは定義されていない
- WORKSPACE_AND_RECOVERY 104はmanual時に理由を表示して終了するだけで、Completion incomplete後にPlanまたは執筆を修正して再開する正式workflowを持たない
- PIPELINE 116は内部Plan Revision遷移を定義するが、公開操作、incomplete後の戻り先、確定Recovery、採用版Authorityは未定義
- ACCEPTANCE 24は採用済みVolume Plan Revisionを必須試験とし、34も明示的Revisionを要求するため、Revision workflowはV1 Release機能として扱われている
- Initial Design各StageにはRevision新version試験がある一方、Series／Volume／Chapter／Scene PlanにはRevision試験がなく、異なる既存Planは上書き拒否となる。採用済みPlan Revisionは実装されていない可能性が高い
- Series／Volume Planはversion=1、parent_plan_id=null、v0001 pathへ初回採用し、再実行で異なる内容を返すと新versionを作らずContractErrorとなる。Plan Revision未実装が試験本文からほぼ確定した
- ソース上、全Plan Stageがversion=1、parent_plan_id=nullを固定しており、Plan v0002を生成する処理がない。採用済みPlan Revision未実装が確定した

## F-012: Review Issueと採用可否の境界が不明

- 種別: 製品仕様の曖昧さ
- 重要度: 中
- 状態: 未対応
- どのIssueが採用を妨げるか、severityやnon-blocking Issueを許すかが不明
- Revision上限時に残ってよいIssueも定義されていない
- DATA_MODEL 82はerror、warning、noteを定義するが、未解決warningの採用主体とReview decisionとの関係は未定義
- PIPELINE 12はaccept／revise／rejectだけを扱い、未解決warningの採用判断規則を定義していない
- LLM_INTEGRATION 87はwarningのみの場合をoperation policyへ委ねるが、policyの内容・既定値・保存場所を定義していない

## F-013: complete_with_issuesとincompleteの境界が不明

- 種別: 製品仕様の曖昧さ
- 重要度: 高
- 状態: 上位文書への反映待ち
- Publication可否を分ける「軽微な未解決事項」の基準がない
- Required Thread、Ending必須条件、主要Arcなどの必須判定を定義する必要がある
- DATA_MODEL 90はcomplete_with_issuesで許される軽微な問題と、incompleteにすべき必須未達を具体的に定義する

## F-014: Handoffと作品状態のAuthority優先順位が不明

- 種別: 製品仕様の曖昧さ
- 重要度: 中
- 状態: 上位文書への反映待ち
- 次巻計画は作品状態とHandoffの両方を参照するが、矛盾時の扱いがない
- Generationの作品状態をAuthority、Handoffを導出要約として定義する必要がある
- ARCHITECTURE確認: Generationを現在Story StateのAuthority、Handoffを確定状態の導出要約と定義しており、Architecture上の優先順位は明確
- DATA_MODEL 78もGenerationを詳細Authority、Handoffを要約と定義している

## F-015: PublicationがPlanから利用できる情報の範囲が曖昧

- 種別: Publication入力成果物と用語の不一致
- 重要度: 中
- 状態: 未対応
- 実装には独立したPublication Plan成果物、Schema、Stageが存在しない
- PublicationはSeries／Volume／Chapter Planの順序とタイトル、確定Scene本文、Completion Resultをcode-onlyで収集する
- 文書でPublication Planを独立成果物として扱う場合は実装と一致しない
- V1では「採用済みPlan階層と確定SceneがPublication入力」であることへ用語を統一する必要がある
- Publicationの巻数はSeries Plan、巻タイトルとChapter順はVolume Plan、章タイトルとScene順はChapter Plan、本文は確定Scene proseを権威として使用する。Scene PlanはPublication構築時には直接参照しない

## F-016: Publication再作成とimmutable成果物の関係が不明

- 種別: Publication不変性と再実行規則
- 重要度: 高
- 状態: 解消済み
- Publicationはimmutable directoryとして確定される
- 既存finalの異なる内容による上書きを拒否する
- Publication、目次、metadata、hashの改変をValidatorが検出する
- 正当なstagingまたはfinalからは冪等Recoveryし、不正または競合状態はmanual扱いにする
- RecoveryでProvider／Modelを生成しない
- Completion後のScene本文改変問題はF-094として分離した。本Findingの解消は確定済みPublication directory自体のimmutable契約に限定する

## F-017: Scene本文の禁止事項が例外を許す表現になっている

- 種別: 製品仕様の曖昧さ
- 重要度: 中
- 状態: 未対応
- 内部識別子、Review結果、metadata等が「原則として」禁止されている
- 絶対禁止事項と、作品表現上の例外を許す事項を分離する必要がある
- REQUIREMENTS確認: REQ-FR-017では内部情報を本文へ含めることを絶対禁止しており、上位仕様だけが曖昧

## F-018: 停止後の再開保証とmanual状態が矛盾する

- 種別: 製品仕様の矛盾
- 重要度: 高
- 状態: 未対応
- Version 1の保証は「停止後に再開可能な状態を保持する」としている
- 一方でCrash後に人間確認が必要で自動再開できない状態を認めている
- 制御された停止と予期しないCrashを分けて保証する必要がある
- REQUIREMENTS確認: REQ-OPS-010は利用者停止時に再開可能な状態を残すと明記している

## F-019: incompleteがRecovery上のmanual状態と混同されている

- 種別: 製品仕様の状態分類不整合
- 重要度: 高
- 状態: 設計文書への反映待ち
- incompleteは正常な意味的Completion結果である
- workspace破損やAuthority不明によるmanual recovery requiredとは分離する必要がある
- 利用者へ示す停止理由も別にする必要がある
- REQUIREMENTS確認: REC要件にはincompleteがなく、Recovery状態との混同はSPECIFICATION 52側の問題
- WORKSPACE_AND_RECOVERYはcompletion_incompleteをstop_reasonとして持つが、stopped／blocked／failedのどれへ対応するかを定義していない
- WORKSPACE_AND_RECOVERY 71はincompleteを正常なblocked状態とする一方、89はRecovery manual条件に含めており、意味的停止とworkspace不整合を直接混同している
- ACCEPTANCE 45はincompleteを正式保存し、blockedとして停止し、Publicationせず再判定しない正常な意味結果と明確に定義する
- 実装ではincomplete Completion Resultをimmutable保存した後、status=blocked、stop_reason=completion_incompleteとして正常停止する。manual Recovery扱いではないため実装側は解消

## F-020: 外部資料入力が入力仕様に存在しない

- 種別: 製品仕様の不整合
- 重要度: 中
- 状態: 未対応
- 外部事実をBriefまたは資料として与えると記載されている
- V1の入力方式にはBriefとKeywordsしか存在しない
- V1ではBriefへ含めると明記するか、資料入力を正式に定義する必要がある

## F-021: 利用量上限の集計範囲が不明

- 種別: 製品仕様の曖昧さ
- 重要度: 中
- 状態: 未対応
- Call、token、費用、経過時間の上限がprocess単位かworkspace累積か不明
- resume後の引継ぎ、retryの数え方、usage欠落時の扱いも未定義
- LLM_INTEGRATION 114〜120はCall・token等をrun単位で累積する意図を示すが、max_elapsed_timeへ停止中の時間を含めるかは未定義

## F-022: POV制約の例外条件が曖昧

- 種別: 製品仕様の矛盾
- 重要度: 高
- 状態: 未対応
- 指定POVから知覚または推測できる情報だけを本文へ出すとしている
- 一方でScene Cardが許可すれば非POV人物の内面を断定できるように読める
- 単一POV厳守か、全知・複数視点を許すかを決める必要がある

## F-023: 作者用秘密情報の保証範囲が強すぎる

- 種別: 製品保証の過大表現
- 重要度: 高
- 状態: 未対応
- LLM出力から秘密情報の意味的漏洩を絶対保証することはできない
- Contextへ無条件に含めないことと、禁止開示候補を採用しないことを保証範囲とすべき
- ARCHITECTURE確認: Context BuilderがWriter秘密境界を適用するため、保証範囲は秘密情報をContextへ無条件に含めないこととして定義できる

## F-024: 手動編集の正式な取込方法がV1に存在しない

- 種別: 製品仕様の不整合
- 重要度: 中
- 状態: 未対応
- 手動編集は新Candidateまたは新versionとして取り込む必要があるとされる
- しかし正式な手動編集取込は将来拡張とされている
- V1では直接編集と再取込を正式に支援しないことを明記する必要がある

## F-025: V1完成条件が製品範囲より弱い

- 種別: Release／Publication E2E試験
- 重要度: 高
- 状態: 解消済み
- 4巻Acceptance E2Eで全Scene、全Handoff、Completion、Publicationを実行する
- Publication専用32件でBuilder、Manuscript契約、Stage、Workspace検証、Crash Recoveryを確認する
- Builder出力とStage確定ファイルの一致、metadata hash、決定的目次、改変拒否を試験する
- 上位仕様のCompletion Criteria表現が弱い問題は文書側の別論点とする

## F-026: Evidence要件の必須項目が不一致

- 種別: 要件間不整合
- 重要度: 高
- 状態: 撤回
- REQ-FR-022は本文引用の出現位置と変更理由を必須とする
- REQ-DATA-005は出現位置と変更理由を要求していない
- 同じEvidence契約を一元化する必要がある
- DATA_MODEL 67により、引用位置はEvidence、更新対象・変更前後・理由は関連するUpdate Operationで確認する非重複設計と判明した

## F-027: 実行設定を確定する単位が不明

- 種別: 要件の曖昧さ
- 重要度: 高
- 状態: 上位文書への反映待ち
- REQ-OPS-003の「実行開始時」がworkspace、process、Stage、operationのどれか不明
- resume時の設定変更可否とworkspace固定設定の範囲を定義する必要がある
- WORKSPACE_AND_RECOVERY 31〜33はrun開始時に設定をmaterializeし、resumeでは保存済み設定を優先し、途中変更を明示操作と定義している

## F-028: Provider call監査要件の上位根拠が不正確

- 種別: 要件追跡不整合
- 重要度: 低
- 状態: 未対応
- REQ-OPS-008はProvider call監査を要求する
- 対応仕様節53〜55には監査記録の製品契約がない
- ARCHITECTUREのAudit LoggerまたはLLM_INTEGRATIONのCall Recordを根拠にすべき
- LLM_INTEGRATION 13がProvider Call記録の直接的な設計根拠であり、REQ-OPS-008の参照先として使用できる

## F-029: Recoveryが利用者入力を再生成すると読める

- 種別: 要件の意味的不整合
- 重要度: 高
- 状態: 未対応
- REQ-REC-003は不完全な「入力資料」を再生成対象と読める形で列挙している
- BriefやKeywordsは利用者入力のAuthorityであり、Storycraftが再生成してはならない
- Provider call用の一時Contextなど、再生成可能な内部資料へ対象を限定する必要がある

## F-030: Path安全性要件の対象範囲と根拠が不明

- 種別: 要件の曖昧さ
- 重要度: 高
- 状態: 上位文書への反映待ち
- REQ-SEC-006はabsolute pathを一律拒否すると読める
- CLIで明示されたworkspace rootと、作品データから導出する内部pathを区別する必要がある
- 対応仕様節61〜63はPath安全性を定義していない
- WORKSPACE_AND_RECOVERY 7と12はCLI指定のworkspace rootと作品入力から導出する内部pathを区別している
- ACCEPTANCE 83はabsolute pathを広く拒否する記述であり、許可されるCLI workspace rootと内部利用者由来pathを区別していない

## F-031: Network禁止がAcceptanceだけで強化されている

- 種別: 文書階層違反
- 重要度: 高
- 状態: 未対応
- REQ-NFR-006は必須試験が実networkを必要としないことだけを要求する
- ACCEPTANCE 95は予期しないnetwork接続を試験失敗にする追加契約を持つ
- Acceptanceは新しい仕様を追加できないため、REQ-NFR-006へ禁止検出を追加する必要がある
- ARCHITECTURE 53はAcceptanceが新しい契約を追加することを禁止しており、Network禁止検出は上位要件へ追加する必要がある
- ACCEPTANCE 89・95のnetwork遮断契約はREQ-NFR-006の「network不要」より強く、要件への反映が必要

## F-032: 要件の上位文書参照に複数の誤りがある

- 種別: 要件追跡不整合
- 重要度: 中
- 状態: 未対応
- REQ-SEC-006、REQ-NFR-002、REQ-NFR-004、REQ-NFR-007の対応仕様節が要件内容を定義していない
- REQ-OPS-008もF-028で同種の問題を記録済み
- 製品仕様にない内部要件はARCHITECTUREまたは適切な上位原則を根拠にする必要がある
- ARCHITECTURE確認: Schema形式は23、Context最小化は22、package assetは21、Auditは27を上位根拠として参照できる

## F-033: 文書の優先順位が矛盾している

- 種別: 文書階層不整合
- 重要度: 高
- 状態: 未対応
- ARCHITECTUREは製品仕様を含む他文書より上位と読める
- docs/READMEおよびREQUIREMENTSはSPECIFICATIONを上位文書として扱う
- ARCHITECTUREは内部設計の最上位であり、利用者向け仕様を変更・狭小化できないことを明記する必要がある
- ARCHITECTURE 43は8文書すべてを正本とするが、正本間で矛盾した場合の優先順位を定義していない

## F-034: 実装容易性がデータ保全より上位に置かれている

- 種別: アーキテクチャ原則の不整合
- 重要度: 高
- 状態: 未対応
- 最優先事項で実装しやすさがデータ喪失防止より上位にある
- 製品仕様と要件が必須とする安全性を、実装容易性との比較対象にしてはならない
- 必須制約と、必須制約を満たす案の選択順位を分離する必要がある

## F-035: immutable成果物の対象範囲が要件より広い

- 種別: Architectureと要件の不整合
- 重要度: 高
- 状態: 未対応
- ARCHITECTURE 10は全ての確定済み成果物directoryをimmutableとする
- REQ-DATA-004はStory状態、Scene成果物、Publicationしか明示していない
- Plan、Initial Design、Handoff、Completionなどを含む一般契約へ要件を統一する必要がある
- DATA_MODEL 7はInitial Design、Plan、Handoff、Completionを含めているが「原則として」上書きしないという例外可能な表現になっている

## F-036: PlanとCompletionの採用版を選ぶAuthorityが不明

- 種別: Authority設計の欠落
- 重要度: 高
- 状態: 未対応
- Authority Registryは採用済みPlanと採用済みCompletion Resultを正本とする
- immutableな新versionを作れるため、複数の確定済み成果物が存在し得る
- どのPlan versionとCompletion Resultが現在採用されているかを一意に選ぶAuthorityが示されていない
- 対象ごとの採用版selectorまたは確定成果物を一件に制限する不変条件が必要
- DATA_MODEL 4はPlan Authorityを「最新の採用済みPlan」とするが、最新採用版を選択する規則は定義していない
- WORKSPACE_AND_RECOVERY 4と13にもcurrent Plan selectorとcurrent_completion_idが存在せず、保存Authorityの欠落が確定
- WORKSPACE_AND_RECOVERY 57はPlanをtargetと上位Plan参照から決定するとするが、複数accepted版から一つを選ぶselectorは存在しない
- ACCEPTANCE 24はPlan新versionと旧version保持だけを確認し、新versionが現在採用版になることを試験しない
- Plan Stage試験は異なる既存Planを拒否するだけで、新versionを現在採用版へ切り替えるselectorを試験しない
- Plan Stageには現在版selectorを切り替える処理がなく、v0001だけを保存して異なる再採用を拒否する
- 全Plan保存先がv0001固定で、現在採用版selectorを切り替える実装は存在しない
- Publicationもseries-plan-v0001、各Volume／Chapter Planのv0001固定pathを直接読むため、Plan Revision導入時には現在採用版selector対応が必要になる

## F-037: 古いScene Candidateの再利用方針が矛盾する

- 種別: 製品仕様とArchitectureの矛盾
- 重要度: 高
- 状態: 上位文書への反映待ち
- SPECIFICATION 25は関連入力が同じならbasis Generationが異なるCandidateの再検証利用を許す
- ARCHITECTURE 33はbasis Generation不一致時にCandidateを再利用せずScene Planからやり直す
- Candidate再利用を全面禁止するか、同値判定契約を正式に定義する必要がある
- PIPELINE 21はCandidate再利用時にbasis Generationと現在Generationの一致を必須とし、Scene Candidateは異なるGeneration間で再利用しない契約になっている
- State変更なしのScene Commitでも新Generationを作れるため、Generation ID不一致だけではPlanを古いと判定できない。code-equivalenceの比較対象を定義する必要がある

## F-038: Writer秘密境界が予定された開示まで禁止する

- 種別: Architectureの意味的不整合
- 重要度: 高
- 状態: LLM設計内の整合修正待ち
- ARCHITECTURE 37は未公開の真相、Thread回答、Ending内部設計を本文Contextから一律除外する
- 真相やEnding情報を開示する予定Sceneでは、許可された情報を本文生成へ渡す必要がある
- 現在Sceneで開示が許可され、執筆に必要な範囲だけを渡せる契約へ修正する必要がある
- DATA_MODEL 103は未公開のprivate_truthだけをPOV本文Contextから除外しており、許可された開示Sceneでは必要な情報を渡せる契約になっている
- LLM_INTEGRATION 50は現在Sceneで開示を許可した事実をWriterへ渡せると明記し、下位設計上は解決している
- LLM_INTEGRATION 50はSceneで許可した事実をWriterへ渡せる一方、51は未公開真相等を一律除外しており、文書内で開示Sceneの扱いが矛盾する
- ACCEPTANCE 26はEnding真相や黒幕をWriter Contextから一律除外し、現在Sceneで許可された開示情報を渡せるLLM設計と衝突する
- ACCEPTANCE 98のWriter秘密情報漏洩は、未許可・不要なContext投入または未許可の本文開示に限定し、現在Sceneで許可された開示情報の利用と区別する必要がある

## F-039: 長期Arcが複数箇所で独立定義される

- 種別: データAuthorityの重複
- 重要度: 高
- 状態: 未対応
- Character.long_term_arc、Relationship.desired_arc、Long-term Arcが同じ将来変化を表現できる
- Long-term ArcはCharacterとRelationshipをtargetにできるため、内容が矛盾する可能性がある
- 長期変化のAuthorityを一箇所へ統一し、他はID参照にする必要がある

## F-040: Scene由来の永続的な過去事実のAuthorityがない

- 種別: データモデルの欠落
- 重要度: 高
- 状態: 未対応
- CanonはInitial DesignまたはDesign Revisionだけを作成元とする
- Stateは現在値、Timelineは時間関係、Evidenceは変更根拠であり、Sceneで成立した重要な過去事実の構造化Authorityが不明
- Scene由来Event／Historical Factを追加するか、Timelineの責務を拡張する必要がある
- DATA_MODEL 122はCanonを「確定事実」と要約する一方、37はScene由来の確定事実をCanonから除外しており、Scene由来Historical FactのAuthority欠落が残る

## F-041: 開示可能な作者用秘密がKnowledge IDへ結び付く保証がない

- 種別: 秘密情報・Knowledgeモデルの欠落
- 重要度: 高
- 状態: 未対応
- reader_knowledgeが追跡できる対象はKnowledge FactとThreadだけ
- Character.private_profile、Relationship.private_truth、World.private_truths等の秘密に対応するKnowledge IDが必須ではない
- 将来開示され得る秘密はKnowledge FactまたはThreadとしてIDを持つ不変条件が必要
- DATA_MODEL 60は開示対象をKnowledge IDまたはThread IDへ限定しており、開示可能な秘密のID対応が必須

## F-042: Relationship Stateが非対称・複数人物関係を表現できない

- 種別: データ表現の矛盾
- 重要度: 高
- 状態: 未対応
- Relationshipは二人以上を参加者にできる
- trust、affection、fear、hostilityは関係全体に一つだけで、参加者ごとの方向差を表せない
- 方向付き参加者状態を導入するか、方向付き二者Relationshipへ限定する必要がある

## F-043: Plan識別子が二重定義される

- 種別: データ項目の重複
- 重要度: 高
- 状態: 未対応
- Plan共通規則はplan_idを要求する
- 各Plan種別はseries_plan_id、volume_plan_id、chapter_plan_id、scene_plan_idも持つ
- 一つのPlan identityを二つのfieldへ保存しないよう統一する必要がある

## F-044: Series Planのbasis Generation規則が不一致

- 種別: データモデルの不整合
- 重要度: 中
- 状態: 設計文書への反映待ち
- Plan共通規則は全Planにbasis_generation_idを要求する
- Plan基準Generation節はVolume、Chapter、Sceneだけを対象とする
- Series PlanのbasisをInitial GenerationとするかInitial Designとするか定義が必要
- PIPELINEのseries_plan入力にはInitial Generationが含まれ、Series PlanのbasisはInitial Generationである意図が明確

## F-045: 上位Plan Revision時の下位Plan無効化規則がない

- 種別: Plan整合性契約の欠落
- 重要度: 高
- 状態: 未対応
- Series、Volume、Chapterの採用版変更時に既存下位Planをどう扱うか未定義
- basis_generation_idだけでは上位Plan version変更を検出できない
- 上位Plan IDとversion参照、および再評価・再生成条件が必要
- PIPELINE 55はGeneration差分だけを扱い、上位Plan version変更時の下位Plan再評価を定義していない
- PIPELINE 116は下位Planを順に再評価すると定めるが、再利用と新version作成の判定条件、および確定済みSceneとの整合規則はない
- PIPELINE 132〜138には上位Plan Revision後の下位Plan再評価を確認する試験観点がない

## F-046: Scene Cardのrequired_revelations契約が不完全

- 種別: データモデル内不整合
- 重要度: 高
- 状態: 未対応
- 開示制約節はrequired_revelationsを定義する
- Scene Card主要項目にはrequired_revelationsが存在しない
- required、allowed、forbidden間の包含・排他不変条件も必要
- PIPELINE 58のScene Card Reviewにもrequired_revelationsの生成・検証・採用条件が存在しない
- ACCEPTANCE 25は開示制約を一般表現で確認するだけで、required_revelationsの存在・達成を個別に試験しない

## F-047: Generation内EvidenceがScene Authorityと重複し得る

- 種別: Authority重複の曖昧さ
- 重要度: 高
- 状態: 未対応
- Generation論理構成にevidenceが含まれる
- 本文由来EvidenceのAuthorityは採用済みScene成果物と定義されている
- Generation側はEvidence ID参照だけを持ち、本体を複製しないことを明記する必要がある
- WORKSPACE_AND_RECOVERY 58はGeneration内にevidence.jsonを実際に保存するため、Scene側EvidenceとのAuthority境界を明記する必要がある

## F-048: manual_revision Generationの公開作成経路がない

- 種別: データモデルと製品範囲の不整合
- 重要度: 高
- 状態: 未対応
- Generation commit_typeにmanual_revisionが存在する
- V1では手動編集取込やDesign／Plan Revisionの公開workflowが未定義
- 正式経路を定義するかV1の列挙値から除外する必要がある

## F-049: Handoffの状態項目が非Authorityである保証が弱い

- 種別: Authority境界の曖昧さ
- 重要度: 中
- 状態: 未対応
- Handoffはcharacter_statesとrelationship_statesを持つ
- Generationが詳細Authorityであることは説明されるが、HandoffからStateを復元・上書きしない不変条件がない
- Handoff内項目を要約または参照に限定する必要がある

## F-050: Completion statusのcross-field規則が不十分

- 種別: Completionクロスフィールド規則
- 重要度: 高
- 状態: 解消済み
- completeは全Thread resolved、全Ending satisfied、全Arc satisfied、全issues空を要求する
- complete_with_issuesはblocking条件を許さず、部分Arcまたは具体的Issueを要求する
- incompleteは未達または部分達成条件とtop-level issuesの両方を要求する
- status、Check、Issueの矛盾はContractErrorとして拒否される

## F-051: Relationship Arc Checkのデータ契約がない

- 種別: Relationship Arc Completion Check
- 重要度: 高
- 状態: 解消済み
- relationship_arc_checksはCompletion必須fieldとして実装されている
- Ending Designの全Relationship End Stateを順序どおり一度ずつ評価する
- Relationshipの最終Generation存在、planned_end_state一致、Evidence Sceneを検証する
- not_satisfiedはblocking、partially_satisfiedとnot_applicableはcompleteを禁止する

## F-052: Completion Issueの型とblocking規則が不明

- 種別: Completion Issueとblocking規則
- 重要度: 高
- 状態: 解消済み
- top-level Issueはcategoryとdescriptionだけを持つ閉じたobjectとしてSchema定義される
- categoryは空でない最大120文字の拡張可能な文字列である
- blocking性はIssueではなくThread、Ending、Character／Relationship Arcのstatusから決定される
- Thread未解決、Ending未達、Arc not_satisfiedはblockingとなる
- Arc partially_satisfiedとnot_applicableは非blockingだがcompleteを許可しない
- complete、complete_with_issues、incompleteのクロスフィールド条件はValidatorで明示される

## F-053: Completion前確認が全巻Handoffの連続性を検証しない

- 種別: Completion事前検証
- 重要度: 高
- 状態: 解消済み
- CompletionはSeries Planのvolume_countに従い全Volumeを走査する
- 全Volume／Chapter／Scene Plan、確定Scene、Generation系列、全Handoffを検証する
- 実Scene集合とPlan由来Scene集合、実Handoff集合と期待Handoff集合の完全一致を要求する
- current Generationが最終計画Sceneのresult Generationであることも確認する
- 4巻E2Eでhandoff-v01〜v04とCompletion completeを実行確認した

## F-054: Completion Resultの代表例が不変条件に違反する

- 種別: 設計例とデータ契約の不整合
- 重要度: 高
- 状態: 未対応
- DATA_MODEL 112はcomplete_with_issuesの例でthread_checksとending_checksを空にしている
- Initial Designには必須ThreadとEnding Designが存在し、Completionでは全必須対象の評価が必要
- summaryだけで主要ThreadとEnding条件を満たしたことにしており、Completion不変条件に違反する
- 必須Checkを含む有効な完全例へ修正する必要がある

## F-055: Schema Migrationに必要なversion識別契約がない

- 種別: Schema管理契約の欠落
- 重要度: 中
- 状態: 未対応
- DATA_MODEL 120は旧schema_versionと新schema_versionによるMigrationを要求する
- 共通データ規則と主要成果物には現在のschema_versionを識別する契約がない
- 永続JSONまたは成果物共通metadataの一箇所でSchema版を一意に特定できる必要がある
- WORKSPACE_AND_RECOVERYではrun-stateとcountersだけにschema_versionが確認でき、他の永続成果物の版識別は未確認
- WORKSPACE_AND_RECOVERY 82はschema_versionを制御fileだけに要求し、物語成果物のSchema版は未定義
- Publicationはmetadata.json.schema_version=1と、schema_version付きcompletion.jsonによりdirectory契約をversion識別する。series.mdとvNN.mdはmetadata管理下の派生成果物であり、Publicationについては問題なし

## F-056: Initial Generation作成前の実行状態を表現できない

- 種別: Run State不変条件の矛盾
- 重要度: 高
- 状態: 未対応
- current_generation_idは存在するGenerationを必ず指すとされている
- 新規runの入力確認からInitial Design採用まではGenerationが存在しない
- Initial Generation確定前はnullを許可し、Stageまたはstatusとのcross-field制約を定義する必要がある
- WORKSPACE_AND_RECOVERY 62はInitial Generation確定後に初めてcurrent_generation_idを設定すると明記し、17・26の常時存在条件との矛盾が確定した
- WORKSPACE_AND_RECOVERY 87・89・110は正常なCurrent Generationを常時要求し、入力確認からInitial Design途中の正常workspaceをmanual扱いする
- ACCEPTANCE 61はcurrent Generation欠落を常にmanualとし、Initial Generation前の正常なnull状態を区別していない
- ACCEPTANCE 98のcurrent Generation欠落に関するRelease不可条件も、Initial Generation確定後に限定しないと正常な初期Stageのnull状態と衝突する
- Initial Accept実装はcurrent_generation_id未設定状態を正式に扱い、Initial Design採用後にInitial Generationを作成する。current Generation欠落が常に不正という文書上の不変条件とは一致しない

## F-057: pending_commitの対象がimmutable成果物全体を覆わない

- 種別: Recovery設計文書・受入網羅性の不足
- 重要度: 中
- 状態: 実装済み・文書未対応
- 実装では全Model Stageがcandidate_adoption Recovery対象である
- InputはInput固有candidate_adoption、Initial AcceptはFilesystem検証再利用方式を使う
- Scene CommitとPublicationは専用pending commit Recoveryを使う
- 共通Recoveryはaccepted Candidate再検証、成果物採用、Workspace検証、phase更新、Stage遷移をProviderなしで行う
- 競合時はmanual対応を要求し、自動上書きしない
- 設計文書にStage別Recovery分類がなく、AcceptanceのCrash注入は代表Stageに限定される
- 専用Recovery試験はInput、Prose、Scene Continuity、Completionに存在し、共通Runner代表としてSeries Plan試験もある。Scene CardとVolume HandoffにはStage固有の故障注入試験名がなく、共通Runner経路による間接保証に留まる
- Prose専用Recoveryはprepared／artifact_finalized、本文競合拒否、activeとpendingの同時保存を直接試験し成功した。Continuity専用Recoveryも予約Generation／Evidence／Update IDを再消費せず、競合を拒否することを直接試験し成功した
- Scene Card adopterは既存成果物と完全一致なら冪等成功、不一致ならContractErrorとし、一時file経由で保存する。専用Crash試験はないが共通Recoveryで安全に再実行可能
- Volume Handoff adopterも既存immutable directoryを再検証し、同一内容なら冪等成功、不一致なら上書きを拒否するため、共通Candidate Adoption Recoveryで安全に再実行可能

## F-058: Run statusとstop_reasonの対応規則がない

- 種別: 実行状態分類の欠落
- 重要度: 高
- 状態: 未対応
- stopped、blocked、failedと各stop_reasonの対応が未定義
- completion_incomplete、revision_limit、provider_unavailableなどの分類が判断できない
- Recovery、CLI表示、終了codeで共通するcross-field規則が必要
- WORKSPACE_AND_RECOVERY 71はcompletion_incompleteをblockedへ対応付けるが、他のstop_reasonは未定義
- WORKSPACE_AND_RECOVERY 71はcompletion_incompleteだけをblockedへ対応付けるが、他のExpected errorとRun statusの対応は依然として未定義
- ACCEPTANCE 41はRevision上限時にblockedと停止理由表示を要求するが、安定したstop_reason／error codeを指定しない
- Input Revision上限ではstatus=blocked、stop_reason=revision_limitを実装・試験している。Revision上限部分の安定値は確定済み
- Revision上限の実試験はstop_reason=revision_limitを確認し成功した

## F-059: Counter不整合条件が最大使用済みIDとの等値を許す

- 種別: ID再利用防止条件の誤り
- 重要度: 高
- 状態: 未対応
- 「next値が既存最大ID以上になっていない」ではnextと既存最大IDの等値を許す
- nextは既存最大IDより厳密に大きくなければならない
- next > existing_maxを不変条件として明記する必要がある
- ACCEPTANCE 81はCounterが既存最大番号より小さい場合だけを試し、等しい場合の使用済みID再利用を検出しない

## F-060: immutable Planのstatusをsupersededへ変更できない

- 種別: Plan状態と不変性の矛盾
- 重要度: 高
- 状態: 未対応
- 採用済みPlanはstatus acceptedを持つimmutable directoryである
- 新version採用後も旧Planをstatus supersededへ変更できない
- 複数Planがacceptedのまま残り、現在採用版を一意に決定できない
- supersedes参照と単一selectorによる導出状態へ変更する必要がある
- PIPELINE 55は旧Planをsupersededにすると明記するが、immutableな旧Planのstatusを変更する方法がない
- ACCEPTANCE 24は旧Plan保持を要求するが、immutable旧版のsuperseded導出と現在版selectorを確認しない
- Plan試験は採用済みfileの変更と異なる内容の上書きを拒否するが、旧versionの保持、superseded導出、現在版切替は試験しない
- Plan成果物にはversionとparent_plan_idが存在するが、実装試験では常にversion=1、parent_plan_id=nullであり、旧版保持と現在版切替は未実装
- Series／Volume／Chapter／Scene Planの実装はすべてversion=1、parent_plan_id=null固定。Schema上のversion系fieldはV1で履歴管理に使用されていない
- Publication Metadataはbasis GenerationとCompletion IDを持つが、各Plan ID／versionを記録しない。現状のv0001固定では再構築可能だが、Plan Revision導入時にはPublication provenance拡張が必要

## F-061: Workspace成果物layoutが一意に定義されていない

- 種別: 保存形式正本の曖昧さ
- 重要度: 高
- 状態: 未対応
- Initial Designは複数fileまたは単一fileの選択制になっている
- Scene versionもdirectory名へversionを含める方式と配下version方式の選択制になっている
- 必須file、Recovery、validator、fixtureの正規契約が一意に決まらない
- Version 1の正規layoutを一つへ固定する必要がある
- WORKSPACE_AND_RECOVERY 121はworkspace構成が一意であることを文書受入条件にしており、前半で複数layoutを許す記述と矛盾する

## F-062: Handoffのimmutable revision IDが定義されていない

- 種別: Handoff版管理の欠落
- 重要度: 中
- 状態: 未対応
- Handoff pathはhandoff-v01のように巻番号だけである
- Handoffはimmutableだが、再評価・修正時に新しい成果物を保存するversionまたはIDがない
- Handoff revisionの識別子と採用版選択規則を定義する必要がある

## F-063: 初期設計Candidateの採用版を選ぶAuthorityがない

- 種別: Pipeline入力Authorityの欠落
- 重要度: 高
- 状態: 未対応
- 初期設計StageはCandidateを出力し、後続Stageは採用候補Candidateを入力にする
- どのCandidate IDとversionが採用候補かを永続的に選択する規則がない
- 複数accepted Candidateが存在した場合やCrash後に後続入力を一意に決定できない
- componentごとの採用Candidate selectorまたはaccepted一件制約が必要

## F-064: input Stageの開始条件ではCrash後に再開できない

- 種別: Pipeline再開条件の矛盾
- 重要度: 高
- 状態: 未対応
- input開始条件は新規workspaceを要求するが、Stage途中Crash後は既存workspaceになる
- Keywords経路では元Keywordsと生成Briefが同時に存在し得る
- file存在数ではなくsource_typeと採用済みBriefの有無で再開条件を定義する必要がある

## F-065: 全Stage共通のBudget条件がcode-only確定を妨げる

- 種別: Pipeline開始条件の過剰制約
- 重要度: 高
- 状態: 未対応
- 全Stage開始条件に予算残存を要求している
- initial_accept、scene_commit、publication、RecoveryなどProvider不要処理まで停止する可能性がある
- Budgetは新しいProvider Call開始前だけ確認し、code-only確定と安全停止は許可する必要がある
- PIPELINE 104はBudget確認を新Provider Call前だけに限定する正しい契約を持つが、18の全Stage共通開始条件と矛盾する
- PIPELINEの失敗系にはBudget到達があるが、到達後もcode-only確定を完了して安全停止する試験がない
- LLM_INTEGRATION 7・18はOperation ServiceとBudget確認をLLM operationだけに限定し、code-only処理は経由しない

## F-066: Review reject後の遷移が決定的でない

- 種別: Pipeline遷移の曖昧さ
- 重要度: 高
- 状態: 未対応
- Review reject時の処理が「停止または再生成」とだけ定義されている
- PipelineはStage遷移の唯一の正本だが選択条件がない
- reject理由、再生成可能性、上限に基づく決定規則を定義する必要がある
- PIPELINE 101はreject理由を列挙するが、理由ごとの再生成／blocked／Plan再評価への遷移を定義していない

## F-067: Planのbasis規則が通常の複数Scene進行と衝突する

- 種別: PipelineとPlanモデルの矛盾
- 重要度: 高
- 状態: 未対応
- Chapter PlanとVolume Planは作成後に複数Sceneで継続利用する
- Scene確定ごとにCurrent Generationが変わるため、Planのbasis_generation_idは直ちに古くなる
- PIPELINE 55はbasisが異なるPlanをそのまま実行できないとするが、78はPlan再評価なしで次Scene Planへ進む
- 同じPlan版を再利用してもimmutableなbasis_generation_idは古いまま残る
- Plan階層ごとのbasisの意味と再評価条件を分けて定義する必要がある
- LLM_INTEGRATION 142は古いbasisのPlan Candidateを破棄して再生成するとする一方、PIPELINE 55は影響なしを証明できるPlan版の再利用を許す。未採用Candidate限定かを明記する必要がある
- later chapter／sceneおよび第2巻Planの試験により、実装は対象Plan生成時のcurrent Generationをbasisに使う。採用済み将来Planの再利用条件は未確認
- 実装は子Planを生成する時点のcurrent Generationをbasisとし、親Chapter Planがgen-000001、子Scene Planがgen-000002でも許容する。Plan階層間でbasis一致を要求しない方針を設計へ明記する必要がある

## F-068: Completion Revision回数と対象が決定的でない

- 種別: Completion Pipelineの曖昧さ
- 重要度: 中
- 状態: 未対応
- PIPELINE 89は意味的Review／Revisionを「原則一回まで許可してよい」とする
- 必須か任意か、設定上限との関係、Revision対象となる問題が不明
- 形式不正、checksとstatusの不整合、正当なincompleteを分離して処理規則を固定する必要がある
- PIPELINE 98はCompletion Revision上限を設定可能とし推奨既定1回を示すが、89の「原則一回まで」と表現が一致しない
- LLM_INTEGRATION 92も一度のRevisionを「許可してよい」とし、設定上限との統一が必要
- LLM_INTEGRATION 147はCompletionの再試行をformat errorだけと記載し、92で許可するsemantic consistency RevisionをOperation別方針へ明示していない

## F-069: Plan Revisionが確定済みSceneを破壊する変更を制限していない

- 種別: Plan Revision不変条件の欠落
- 重要度: 高
- 状態: 未対応
- PIPELINE 116はCurrent Generationを維持して過去のPlan Stageへ戻れる
- 新Planが確定済みSceneの削除、順序変更、番号変更、未発生扱いを行えるか未定義
- immutableなSceneとGenerationを既成事実として保持し、未確定の将来部分だけをRevision可能にする必要がある
- PIPELINEの試験観点にはPlan Revision時に確定済みSceneを保持し、未確定将来部分だけを変更する不変条件の試験がない
- Planのimmutable性は試験されるが、Revision時に完了済み過去Planを保持して将来部分だけを新version化する試験はない

## F-070: 古いbasis GenerationをReview Rejectへ混入している

- 種別: コード検証と意味的Reviewの責務混同
- 重要度: 高
- 状態: 未対応
- PIPELINE 101は基準Generationが古いことをReview reject理由に含める
- basis Generation一致と影響差分はコードで決定する契約であり、LLM Review Issueではない
- Stage開始前または採用前検証からPlan／Scene再評価へ直接遷移すべき

## F-071: Stage遷移表がStageとRun statusを混在させている

- 種別: Pipeline状態モデルの混同
- 重要度: 中
- 状態: 未対応
- Stage IDにblockedとcompletedは存在しない
- PIPELINE 114はcompletionからblocked、publicationからcompletedへ遷移すると記載する
- current_stage遷移とrun status遷移を別々に定義する必要がある

## F-072: Candidate再利用に必要な設定versionを検証できない

- 種別: LLM実行契約の識別不足
- 重要度: 高
- 状態: 未対応
- PIPELINEはCandidate再利用時に設定version一致を要求する
- materialized Operation Configに永続的なIDまたはversionがない
- 保存Contextのprompt_version、basis_generation_id、operation_id、target等も任意になっている
- Candidate、Call、Contextへ共通するoperation_config_idと必須識別情報が必要
- LLM_INTEGRATION 118はBudget変更をmaterialized configの新versionとするが、Call metadataにconfig versionがない
- ACCEPTANCE 78は再開時に設定識別情報との互換性確認を要求するが、Operation Configの必須ID／version契約がない

## F-073: Prompt versionと実際のasset内容の対応がimmutableでない

- 種別: Prompt版管理の欠落
- 重要度: 高
- 状態: 未対応
- Prompt versionを識別するとされるがasset pathはversion別になっていない
- 同じversion名のままPrompt fileを書き換えられる
- versionからimmutable package assetを一意に解決するRegistryまたはversion別pathが必要
- LLM_INTEGRATION 122はprompt_versionを記録するが、versionとimmutable assetの一意対応は未定義
- LLM_INTEGRATION 151のPrompt testはversionからimmutable assetを一意に解決できることや、同version内容変更の拒否を確認しない

## F-074: Call Recordで実際のrequest契約を追跡できない

- 種別: Audit・由来情報の不足
- 重要度: 中
- 状態: 一部解決
- Call RecordにPrompt version、Schema version、Operation Config、Candidate、Context参照がない
- Retryごとに新Call IDを作るが、同じ論理operation内のattempt関係を識別できない
- logical_operation_id、attempt_number、operation_config_id等を追加する必要がある
- LLM_INTEGRATION 97・122でoperation_instance_id、attempt、prompt_version、basis_generation_idは記録される。Operation Config、Schema、Candidate、Context参照が残る
- LLM_INTEGRATION 123・157はPrompt version、Context、Candidate IDを調査識別子として扱うが、Call metadataにCandidate versionやContext参照を必須化していない
- ACCEPTANCE 86はtoken preflight結果のAudit記録を要求するが、Call recordに見積token、予約output、上限、判定結果の必須fieldが定義されていない

## F-075: Provider tokenizerがない場合のtoken確認方法がない

- 種別: Token上限契約の欠落
- 重要度: 高
- 状態: 未対応
- Provider tokenizerが利用可能なら使用するとされる
- 利用不能時にCall可否を判断する保守的推定、余裕、拒否条件が未定義
- 安全に上限内と確認できない場合はCallを開始しない規則が必要
- LLM_INTEGRATION 138はAdapterへcount_tokensを要求するが、正確なtokenizerを提供できないAdapterのfallback契約はない
- ACCEPTANCE 86も最終payloadのtoken確認を要求するが、正確なProvider tokenizerがない場合の期待動作を定義しない

## F-076: Context要約の由来と再利用条件が未定義

- 種別: Context導出情報の契約不足
- 重要度: 高
- 状態: 一部解決
- token削減時に過去本文を要約へ置換できる
- 要約の生成方法、source Scene、無効化条件、Budget計上、Authority境界が定義されていない
- source参照を持つ導出情報とし、元Authority変更時に再構築する必要がある
- LLM_INTEGRATION 113は要約を補助情報とし、重要ID等の保持と別Call時のBudget計上を要求するが、source参照と無効化規則はない

## F-077: 出力契約がPromptとContextで二重定義される

- 種別: Prompt構成の重複
- 重要度: 中
- 状態: 未対応
- Prompt層に出力契約があり、Context分類とContext順序にもoutput_contractがある
- 二箇所の内容が競合する可能性がある
- Operation Registryを正本とし、最終Promptへ一度だけ組み込む必要がある

## F-078: 秘密情報Policyの列挙値がData Modelと一致しない

- 種別: 秘密情報モデルの不整合
- 重要度: 高
- 状態: 未対応
- DATA_MODELはreader_visible、character_visible、writer_private、system_privateを定義する
- LLM_INTEGRATIONはreader_visible、pov_visible、scene_allowed、writer_privateを例示する
- 永続visibilityとScene／operation固有の利用許可を分離し、共通契約を定義する必要がある

## F-079: old_value不一致時に有効な上位Scene成果物まで破棄し得る

- 種別: 再生成境界の過剰化
- 重要度: 中
- 状態: 未対応
- LLM_INTEGRATION 74はold_value不一致時にScene Planから全面再構築する
- basis Generationが同じでContinuity Candidateだけが誤った場合も本文等を破棄することになる
- basis変更、Continuity生成ミス、本文不整合を区別して戻り先を決定する必要がある

## F-080: Reviewとコード検証の境界が一部重複している

- 種別: Component責務の混同
- 重要度: 中
- 状態: 未対応
- LLM_INTEGRATION 71は許可外更新をSemantic Issue例に含める
- allowed_updates違反はコードで決定可能で、Review前に拒否する契約である
- Schema・参照・Evidence・old_value・許可fieldと意味的Reviewを明確に分離する必要がある
- LLM_INTEGRATION 145はEvidence、old_value、参照をコード検証と明記し、71のSemantic Issue例との整理が必要

## F-081: usage欠落CallのBudget算入規則がない

- 種別: Budget安全性契約の欠落
- 重要度: 高
- 状態: 未対応
- usage欠落でもCandidateを採用可能としている
- 次回Call前にCall数、token量、costへ何を算入するか未定義
- request見積、受信response推定、予約上限などの保守値を使う共通規則が必要
- LLM_INTEGRATION 150はusage欠落を試験対象にするが、Budgetへ算入する保守値と期待される停止条件を定義していない

## F-082: Recording policyの保存・redaction契約が定義されていない

- 種別: Audit・秘密情報保存Policyの欠落
- 重要度: 高
- 状態: 未対応
- metadata_only、redacted、full_localの名称だけが定義されている
- Call metadata、Context、raw response、structured payload等を各Policyで保存するか不明
- writer_private、system_private、Credential、Provider raw errorのredaction規則が不明
- Policyごとの保存表と、判断不能時に保存を中止するfail-closed規則が必要

## F-083: LLM設計内の試験一覧とAcceptance唯一正本宣言が矛盾する

- 種別: 文書Authority境界の矛盾
- 重要度: 中
- 状態: 未対応
- Part XXVIはUnit、Adapter、Prompt、Context等の具体的な試験一覧を持つ
- Part XXXは試験ケース一覧を重複管理せずACCEPTANCEを唯一の正本と宣言する
- Component設計上の検証観点とRelease受入ケースの境界を明示する必要がある

## F-084: Acceptanceが未定義の「不確定扱い」を追加している

- 種別: Acceptanceによる仕様追加
- 重要度: 高
- 状態: 未対応
- ACC-CONT-006は曖昧な変化を「Reviewまたは不確定扱い」とする
- Data ModelにContinuityまたはStateの不確定状態は定義されていない
- Review、本文Revision、Updateなし採用、blockedのどれかも決定されていない
- 設計側で動作を固定し、Acceptanceは一つの観測可能な結果を要求する必要がある

## F-085: AcceptanceのRequirement対応付けに誤りと不足がある

- 種別: 要件Traceabilityの不整合
- 重要度: 中
- 状態: 未対応
- ACC-E2E-001は停止・再開を行わないのにREQ-REC-002へ対応付けられている
- ACC-E2E-002はPublicationまで確認するがREQ-FR-031を対応要件に含めない
- Requirement IDと受入試験の対応を機械的に検証できる一覧が必要
- ACCEPTANCE 90は全76要件の参照有無を機械検査するが、試験内容が記載Requirementを実際に検証するかは判定しない
- 全84 Acceptance IDのうち実テストから明示参照されるIDは0件で、受入条件と試験実装の機械的な対応を検証できない

## F-086: Crash Recovery Acceptanceが保存・復旧設計と矛盾する

- 種別: AcceptanceとRecovery設計の不整合
- 重要度: 高
- 状態: 未対応
- ACC-CRASH-002はScene final後にGeneration stagingが不完全なら人間対応とする
- WORKSPACE_AND_RECOVERY 93は確定Sceneと親GenerationからGeneration stagingを決定的に再構築する
- manualは再構築後も契約を満たせない場合だけである
- ACC-CRASH-001もScene Commit staging再構築時にProvider Callを許すように読める
- Recovery中のProvider Callを0とし、code-only再構築とmanual条件を設計通りに固定する必要がある
- test_missing_generation_staging_is_rebuilt等により、実装はScene finalからGeneration stagingをcode-onlyで再構築し、Recovery中にmodelを生成しない保存・復旧設計側の契約に従う
- 正規unittestでE2E・Crash Recovery・workflow 11件が成功。Scene Commit途中Crashから同一Publicationへ復旧し、Recovery中のmodel生成なしを実行確認した
- Crash E2EはRecovery中のProvider factory呼出なし、baselineとの最終run-state完全一致、Publication全fileのbyte一致、両Workspaceの最終validationまで確認する
- Publication専用Recovery試験でもprepared、rename直後、publication_finalizedからの復旧が成功し、不正staging、不正final、staging／final競合はmanualとなる。RecoveryでModelを生成しないことも確認済み

## F-087: Acceptance IDと実テストの対応付けが存在しない

- 種別: 受入試験Traceabilityの欠落
- 重要度: 高
- 状態: 未対応
- ACCEPTANCE.mdには84個のACC IDが定義されている
- tests配下から参照されるACC IDは0件である
- test_v1_acceptance等が受入動作を実装していても、どのACCを満たすか機械的に判定できない
- 必須Acceptanceの未実装、重複実装、期待結果不足をRelease Gateで検出できない
- test marker、pytest parameter、docstring、または明示的なtrace tableでACC IDとtest node IDを対応付ける必要がある
- test_v1_acceptance等の受入相当11件は成功したが、ACC IDを参照しないため、84個のAcceptance項目との対応範囲は依然として機械判定できない
- 実テストは形式的ではなく、BriefからPublication、Scene Commit故障復旧、一Scene縦断、code-only StageのProvider非依存などを実Workflowで検証している。問題は試験不在ではなくACC IDとの明示対応不在に限定される
- 主要受入テストは成果物、Handoff、Completion、Publication、Counter、basis Generation、Crash後のbyte一致まで検証している。Findingは試験内容ではなくACC ID traceの欠落だけを指す
- Input／CLI試験もBrief、Keywords、Revision、candidate adoption Recovery等を具体的に検証するが、ACC-IN-*やACC-PKG-*への明示参照はない
- ACC-IN-003〜005相当の試験は存在し成功したが、ACC ID参照がないため自動traceには現れない
- Initial Design／Plan関連82件も実質的な契約を広く検証しているが、ACC-DESIGN-*／ACC-PLAN-*との明示的traceはない
- Scene／Handoff／Completion通常採用関連35件は成功。専用Recoveryファイルは別実行が必要だが、いずれもACC ID参照はない
- Prose／Continuity／Completion専用Recovery 7件も成功した。ただしCompletion試験は主要validationをmockしており、実Workspaceでの完全Recovery受入を表さない
- Publication関連32件はすべて成功したが、ACC-PUB-*等との明示的ID traceはない
- Publication title resolverと複数Artifact間のタイトル優先順位を直接確認する恒久試験は見つからない

## F-088: Keywords生成Briefが全入力条件を保持する保証がない

- 種別: 入力条件保持契約の不足
- 重要度: 高
- 状態: 未対応
- Keywords生成Briefのコード検証はsource、language、volume_count、avoidを対象とする
- 必須keywords、ending_preference、notesの保持を決定的に確認しない
- 正常系試験は事前作成した正しいBriefをModelから返すため、条件欠落を検出しない
- ACC-E2E-002の「元Keywords条件を保持する」を満たす保存形式または検証規則が必要
- _validate_generated_briefの実装を確認し、保持検証はsource、language、volume_count、avoidに限定され、keywords、ending_preference、notesは対象外と確定した

## F-089: Prompt injection受入Fixtureが試験で使用されていない

- 種別: Security受入試験の欠落
- 重要度: 高
- 状態: 未対応
- brief-prompt-injection.jsonはFixture Catalogへ登録されているがPython testから参照されない
- 作品内の命令風文字列がSystem instruction、response mode、秘密Context、外部取得を変更しないことを試験していない
- ACC-IN-007およびACC-SEC-003を実際のPrompt／Adapter境界で確認する必要がある

## F-090: 必須条件とavoidの入力時矛盾を検出しない

- 種別: 入力検証契約の未実装
- 重要度: 高
- 状態: 未対応
- ACC-IN-006は矛盾内容を表示し作品生成を開始しないことを要求する
- 現在のavoid検証は生成後Candidateに対する下流検証であり、入力時矛盾検出ではない
- Provider Call前に何を機械的矛盾と判定するかを仕様・設計で定義する必要がある

## F-091: Completion Recovery試験が実Workspace検証を迂回する

- 種別: Recovery試験網羅性の不足
- 重要度: 中
- 状態: 未対応
- 専用試験は予約completion_idの再利用、Provider非依存、Stage遷移を確認する
- 一方で_prepare_inputsとWorkflow、Completion、共通Runnerのvalidate_workspace_layoutをmockする
- 実Handoff、Generation、Sceneからの入力再構築と、Recovery後Workspace全体の妥当性を直接検証しない
- 競合するCompletion成果物を拒否するRecovery試験も確認できない
- validationをmockしない実Workspace Crash Recovery試験を追加する必要がある
- Completion実装自体はRecovery時にも_prepare_inputsを実行し、Initial Design、全Plan、全Scene、Handoff、current Generationを実workspaceから再構築・検証する。問題は専用試験がこの経路をmockしている点に限定される
- Completion実装は全Plan、全Scene、全Handoff、Generation系列、staging残存を実workspaceから検証し、既存Resultとの競合も拒否する。FindingはvalidationをmockしないCompletion Crash試験の不在だけを指す

## F-092: Completion statusクロスフィールド規則の否定試験が不足する

- 種別: Semantic Validator試験網羅性の不足
- 重要度: 中
- 状態: 未対応
- Validatorはcomplete、complete_with_issues、incompleteの詳細な矛盾規則を実装している
- 恒久試験は正常系と一部のThread未解決ケースに偏る
- completeとIssue、completeと部分Arc、complete_with_issuesとblocking条件、注意事項なしcomplete_with_issues、Issueなしincomplete等の否定試験がない
- Publication可否を決定する境界なので各分岐を専用Unit Testとして固定する必要がある
- 一時実行により、complete＋Issue、complete＋部分Arc、blocking条件付きcomplete_with_issues、注意事項なしcomplete_with_issues、未達条件なしincomplete、Issueなしincompleteがすべて拒否され、部分達成Relationship Arc付きcomplete_with_issuesだけが許可されることを確認した。実装不具合はなく恒久Regression Test化だけが残る

## F-093: Publicationシリーズ題名のfallback順序が文書化・試験されていない

- 種別: Publicationタイトル解決実装とV1 Schemaの不一致
- 重要度: 低
- 状態: 未対応
- 正式V1 Schemaでシリーズタイトルを持つ上流ArtifactはBrief.titleだけである
- Series Plan、Initial Concept、Integrated Initial DesignにはタイトルfieldがなくadditionalPropertiesも禁止される
- _resolve_series_titleが探索する9候補のうち、正常なV1 Workspaceで到達可能なのはBrief.titleだけである
- 現状の出力は決定的であり、タイトル権威の実害ある曖昧さはない
- 契約外fallbackは将来のSchema追加時に暗黙の優先順位を生むため、Brief.titleへ単純化するか将来用分岐であることを明記する
- 正式Schemaを通したPublicationタイトル試験を追加することが望ましい

## F-094: Completion確定後に改変したScene本文をPublicationできる

- 種別: Scene immutable契約とPublication provenanceの破断
- 重要度: 高
- 状態: 未対応
- 実Acceptance WorkflowをPublication直前まで実行したWorkspaceはvalidate_workspace_layoutに成功した
- Completion確定後に確定Sceneのprose.mdを変更してもvalidate_workspace_layoutが成功した
- そのままPublicationを実行すると変更後本文を含むseries.mdが正常確定した
- Completion Resultは変更前本文を評価しているため、Completion未評価本文を出版できる
- Publicationの文字数とSHA-256は変更後本文から生成されるため、Publication単体の整合性検証では検出できない
- 確定Scene directoryの事後不変性がWorkspace Validatorで保証されていない
- Publication Stage試験はvalidate_workspace_layoutと_prepare_inputsをmockするため、この境界を検証していない
- Scene Adoption Recordが確定後も保持される場合は、Workspace Validatorで確定SceneのCard／prose／Continuityを採用記録と完全一致比較し、CommitとGenerationも決定的に再構築して照合するのが第一候補。新しいDigest契約は、既存採用記録を利用できない場合だけ検討する
- 少なくともCompletion後のprose.md改変をPublication前に拒否するRegression Testが必要
- 既存のScene Adoption Recordはruntime/candidates/scene_continuity/adopted-<scene-id>-v0001にCard、prose、Continuityをimmutable directoryとして保持する。同一再公開は冪等、競合上書きは拒否され、staging消失時の復元元としても使用されるため、確定Scene再検証の第一アンカーにできる
- Scene Adoption Recordの確定directoryを削除する実装経路は見つからない。削除処理は作成失敗時の一時stagingに限定される。専用試験でもRecordがScene staging消失後に存続し、復元元として利用できることを確認しているため、恒久照合元として使用可能
- validate_workspace_layoutの全呼出しで全Sceneを深く再検証すると長編では各Stepが全Scene数に比例する。共通Scene完全性Validatorを作成し、Completion／Publication境界で必ず実行し、Workspace全体ではCompletion以降などに限定して実行する構成が望ましい
- Regression Unit Testはcreate_scene_commit_workspaceを利用する専用test_final_scene_integrity_v1.pyへ置き、prose、Card、Continuity、Commit、result Generation、Adoption Record欠落を個別に検証する
- F-094のPublication境界を固定するため、実WorkflowでCompletion後のprose改変をPublicationが拒否し、Publication directory、state、counterを変更しないことを確認する試験を1件追加する
- 推奨修正構成は下位独立module final_scene_integrity.pyへ確定Scene検証を抽出し、CompletionとPublicationから呼び出す方式とする
- 共通Generation読込み関数は存在しないため、同moduleで通常directory、file完全集合、JSON読込みを厳密に検証する
- Workspace ValidatorからSceneCommitStageServiceを逆importすると循環するため使用しない。Scene Adoption Recordとscene_generationの純粋関数だけを利用する
- Workspace全体での深いScene検証はcurrent_stageがcompletionまたはpublication、もしくはstatusがcompletedの場合に限定し、通常Scene生成中の累積性能劣化を避ける
