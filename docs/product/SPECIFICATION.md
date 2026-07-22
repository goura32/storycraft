# Storycraft 製品仕様

> 次期正式リリースで利用者へ保証する振る舞いの正本。現行コードの到達状況は[実装状況](IMPLEMENTATION_STATUS.md)を参照する。この仕様を、現行実装へ合わせて後退させてはならない。

Storycraftは、一度与えられたBriefまたはKeywordsから、長編の日本語シリーズを計画・執筆・継続性管理・完結監査し、検証済みMarkdown publicationとしてローカルに採用するCLI製品である。

詳細な実装契約は次を正本とする。

- [Pipeline contracts](../design/pipeline_contracts.md)
- [Ledger contracts](../design/ledger_contracts.md)
- [Workspace layout](../design/workspace_layout.md)
- [Runtime and recovery](../design/runtime_and_recovery.md)
- [Configuration contracts](../design/configuration_contracts.md)
- [Context contracts](../design/context_contracts.md)
- [Prompt template design](../design/prompt_template_design.md)
- [Series engine design](../design/series_engine_design.md)
- [Implementation acceptance](../design/implementation_acceptance.md)

本書は製品の外部挙動を定める。内部JSON field、Schema、hash graph、transaction順序の詳細は上記設計文書へ委譲する。

---

## 1. 製品の目的

利用者は、物語の基本条件を一度入力し、通常実行中に巻・章・Sceneごとの判断を繰り返し求められることなく、次を得る。

```text
一貫したSeries map
巻ごとの局所的な解決
章・Scene単位の具体的計画
POVと開示境界を守る日本語本文
本文根拠付きの継続性更新
巻をまたぐHandoff
全Required ThreadとEnding criterionの完結監査
巻別・全巻Markdown
検証済みpublication metadataとCompletion report
Crash後に再開可能なworkspace
```

---

## 2. 製品が解決する問題

長編シリーズ生成では、単発の本文品質だけでなく次の問題が起きる。

```text
人物・関係・知識・時刻の矛盾
前巻の終了Stateを無視した次巻
未解決Threadの放置
Ending条件を満たさない完結
レビューによる候補の上書き
Crash後の重複生成・ID再利用
内部メモやauthor truthの公開物への漏洩
途中ファイルを完成品として誤採用
```

Storycraftは、LLMの生成を厳密な候補・Review・Checkpoint・Commit・Gateへ分離し、これらを製品レベルで防止する。

---

## 3. 対象利用者

主な対象は次である。

```text
長編日本語フィクションを一括生成したい個人
シリーズ構成と継続性を機械的に管理したい編集者・開発者
LLM出力を再現可能なartifactとして検証したいチーム
Crash・timeout・provider failureを含む長時間生成を安全に運用したい利用者
```

利用者が内部LedgerやStageを理解していなくても、`run`、`resume`、`step`を利用できることを要求する。

---

## 4. 製品範囲

Storycraft version 1は次を行う。

```text
4〜10巻の日本語シリーズ生成
BriefまたはKeywords入力
Series／Volume／Chapter／Scene計画
Scene本文生成
本文根拠付き継続性更新
Volume Handoff
Completion audit
ローカルKDP向けMarkdown publication生成
workspace、audit、resume、recovery
```

---

## 5. 非目標

version 1の範囲外:

```text
KDPその他の外部サービスへの自動アップロード
Web UI
対話型人間承認画面
RAGまたは外部資料検索
Web閲覧
複数モデルの自動選択・投票
複数writerによる同一workspace同時編集
旧state/workspaceの自動migration
既存作品の途中からの自動取り込み
生成後の自動販売価格設定
商業的成功や文学賞品質の保証
```

Publishing profileが販売区分を記述しても、Storycraft自身はストアへ公開しない。

---

# Part I: 利用者インターフェース

## 6. 公開コマンド

公開CLIは次の3コマンドを提供する。

```text
storycraft run
storycraft resume
storycraft step
```

内部Stageを直接指定する一般利用者向けコマンドは提供しない。

---

## 7. `run`

`run`は新しいworkspaceでシリーズ生成を開始し、terminalまたは安全な停止条件まで進める。

利用者は開始時に次を指定する。

```text
workspace
設定
BriefまたはKeywordsのどちらか一方
```

同じworkspaceに既存runがある場合、`run`は上書きせず失敗する。

---

## 8. `resume`

`resume`は既存workspaceの正本を検証し、最後の安全なdurable boundaryから続行する。

利用者はBriefやKeywordsを再指定しない。

`resume`は次をしない。

```text
最新ファイルを自動選択
最大GenerationをHEADへ設定
途中候補を推測して採用
使用済みID・usageを巻き戻す
```

---

## 9. `step`

`step`は最大1件のCanonical Stageを完了して返る。

用途:

```text
段階的なデバッグ
CIでのStage境界検証
長時間runの外部制御
障害注入試験
```

1 Stage内部で必要なtransport／response-structure retryまたはatomic transactionは完了してよいが、次Stageまでは実行しない。

---

## 10. 入力モード

開始時の入力モードは正確に一つである。

### Brief mode

利用者が完全なBriefを渡す。

### Keywords mode

利用者がKeywordsと任意のhintを渡し、StorycraftがBrief候補を生成・採用する。

両方指定または両方未指定はCLI usage errorである。

---

## 11. Briefが表すもの

Briefは少なくとも次の製品条件を定義する。

```text
作品タイトル
ジャンル
対象読者
主人公
主要人物
作品の目標
避ける内容
Ending方向
巻数
```

巻数は4〜10でなければならない。

---

## 12. Keywordsが表すもの

Keywords modeでは次を指定できる。

```text
複数Keyword
自由なnotes
title hint
genre hint
ending hint
avoid
volumes hint
```

Storycraftはhintを無視せず、構造正常なBrief contentへ変換する。

Profile ID、source hash、timestampなどの実行metadataはコードが追加する。

---

## 13. 通常実行中の利用者入力

正常な自動実行では、巻・章・Sceneごとに利用者へ質問しない。

次の場合だけ、runは停止して利用者または運用者の判断を要求できる。

```text
機械的正本不整合
互換性のない設定変更
Completionが意味的にincomplete
競合するstaging/final artifact
無効なHEADまたはCURRENT
予算上限
利用者による停止
```

---

## 14. 設定

利用者は設定により次を選択できる。

```text
providerとmodel
credentialを読む環境変数名
timeout
retry上限
revision上限
Completion attempt上限
Context/token制限
Call/token/cost/active-time予算
editorial profile
publishing profile
audit保存・retention
log level
```

設定の完全な意味は[Configuration contracts](../design/configuration_contracts.md)を正本とする。

---

## 15. Credential

Credential値はworkspace、Context、prompt、publication、通常logへ保存しない。

保存されるのは必要に応じて環境変数名だけである。

`resume`時にcredential値をrotationしてよいが、credential sourceの契約を黙って変更してはならない。

---

## 16. Single writer

一つのworkspaceは同時に一つのmutating processだけが扱う。

Lockを取得できない場合:

```text
既存runを破壊しない
待機を無期限に行わない
lock conflictとして終了する
```

---

## 17. Exit result

CLIは少なくとも次を区別できる終了結果を返す。

```text
成功または成功したstep
usage/config error
安全なuser/budget/manual stop
lock conflict
mechanical contract failure
provider exhaustion
unexpected internal failure
```

正確なexit code registryは[Series engine design](../design/series_engine_design.md)を正本とする。

---

# Part II: 生成される作品

## 18. シリーズ規模

シリーズは4〜10巻である。

各巻は:

```text
一つ以上のChapter
順序付きScene
巻内の局所的な解決
非最終巻では次巻へ残すreader question
```

を持つ。

最終巻は主要な完結条件を満たさなければならない。

---

## 19. 言語

作品本文、計画の物語内容、読者向けmetadataは日本語を基本とする。

次は契約上のtechnical scalarとして英数字を用いてよい。

```text
ID
enum
path
hash
language tag
provider/model名
Stage ID
```

---

## 20. Series map

Series mapは全巻を通した不変の長期計画である。

少なくとも次を定める。

```text
各巻の構造的役割
主人公変化
主要Relationship変化
Required Major Threadの進行
Ending criterionの準備・充足
巻内解決
非最終巻のreader question
最終巻の完結機能
```

採用後のSeries mapは後続本文に合わせて書き換えない。

---

## 21. Volume design

各巻開始時に、その時点の実際のHEADと前巻Handoffを利用してVolume designを作る。

Volume designは次を定める。

```text
巻タイトル
開始State
主人公・Relationshipの巻内変化
Thread action
Ending criterion target
主要対立
Chapter機能
巻内局所解決
次巻への移行
```

---

## 22. Chapter design

各Chapter開始時に、その時点のHEADと親Volume designを利用してChapter designを作る。

Chapter designは次を含む。

```text
Chapterタイトルと目的
開始State
終了目標
中心的な人物またはRelationship変化
Thread／Ending target
順序付きScene plan
Chapter末機能
```

---

## 23. Scene Card

Scene Cardは本文生成前の凍結計画である。

利用者向けに保証される内容:

```text
POV人物
登場人物
場所
時刻関係
Scene目的
必須beat
感情・Relationship変化
Thread action
Knowledge変化
Reader disclosure
Ending evidence target
禁止開示
許可されるState更新
新規項目上限
本文長guide
```

---

## 24. 本文

本文Stageは自然な日本語のScene本文だけを生成する。

本文応答には次を含めない。

```text
JSON
front matter
heading
箇条書き
表
code fence
metadata説明
continuity delta
Evidence offset
内部ID
```

Publicationの巻・章headingは後でコードが決定的に追加する。

---

## 25. POVと開示

一つのSceneは原則として一つのPOVを持つ。

Writerへ渡すContextは次を除外する。

```text
Thread author truth
Thread resolution condition
Knowledge author truth
Endingのprivate source text
非POV人物のprivate goal・pressure・emotion
未来の未開示事実
```

本文は提示されていない秘密を一般的な物語パターンから推測して断定してはならない。

---

## 26. 新規Canon項目

SceneはScene Cardが許可した場合だけ、局所的な新規項目を提案できる。

許可可能な代表例:

```text
Character
Location
Organization
Item
System
Culture
History
supporting Thread
Knowledge item
```

正確な種類はCanon契約を正本とする。

Sceneごとに次を固定する。

```text
allowed_types
Knowledge itemを許可するか
max_items
max_scope
purpose
```

---

## 27. Sceneで作れないもの

通常Sceneは次を新規作成できない。

```text
Temporal rule
Major Thread
Ending criterion
required Thread
シリーズの固定世界規則
```

上限外の提案や未許可の種類は機械的に拒否する。

---

## 28. Persistent ID

LLMは永続IDを生成しない。

候補内では`local_key`を使い、採用transaction中にコードが永続IDへ変換する。

IDは:

```text
persist-before-use
単調増加
再利用なし
失敗時のgapを保持
```

とする。

---

# Part III: ReviewとRevision

## 29. Review対象

通常のReview／Revision loopは次の候補に適用する。

```text
Initial-design integrated bundle
Series map
Volume design
Chapter design
Scene Card
本文
continuity delta
Volume Handoff
```

Completion auditは別の規則を使う。

---

## 30. Reviewの役割

Reviewは候補全体を監査し、次だけを返す。

```text
summary
issues
```

Reviewは次を返さない。

```text
修正版候補
pass/fail
next Stage
adoption指示
retry指示
```

---

## 31. Revision

Issueがありrevision budgetが残る場合、Revisionは候補全体の完全置換を返す。

Revisionは次を返さない。

```text
diff
patch
変更箇所だけ
修正手順
省略記号
```

以前の候補・Reviewはimmutable historyとして残る。

---

## 32. Revision上限

`max_revision_rounds`は構造正常な意味修正round数である。

次はrevision roundに含まれない。

```text
初回生成
Review
transport retry
response-structure retry
source stalenessによる再生成
```

---

## 33. 残存Issue

Revision上限後もissueが残る場合:

```text
候補が機械的に有効であること
残存issueをimmutable auditへ保存すること
```

を条件に、候補を採用可能とする。

機械的Schema違反や参照破損を残存issueとして採用してはならない。

---

## 34. Retry区分

Retryは次を分離する。

### Transport retry

```text
接続失敗
timeout
stream中断
登録されたretryable provider error
```

### Response-structure retry

```text
invalid UTF-8
invalid JSON
Schema failure
unknown field
本文format違反
```

### Semantic Revision

```text
構造正常候補へのReview issue
```

区分を混ぜて無制限に再試行してはならない。

---

## 35. Provider failure

Transportまたはresponse-structure retryを使い切った場合:

```text
失敗したCall IDとauditを保持
使用量を保持
構造不正候補を正本として保存しない
Runをfailedまたは契約された停止状態にする
```

---

# Part IV: Canon、State、Evidence

## 36. Canon

Canonは固定の物語identity・不変事実・長期構造を持つ。

代表例:

```text
Character identity
Relationship participants/type/origin
World entity
Temporal rule
Thread定義
Ending criterion
Knowledge itemのcanonical fact
```

---

## 37. Story State

Story Stateは現在変化する値を持つ。

```text
Character location・condition・emotion・goal・pressure
Relationshipの方向別trust・perception・stance・intention
Thread status・progress・volume disposition
Character／Reader Knowledge status
Story clock
```

CanonとStateに同じ意味の値を重複保存しない。

---

## 38. Knowledge

Knowledge itemは固定のfact定義である。

誰が知っているか、Readerへどこまで開示されたかはStory Stateで管理する。

Default:

```text
Character: unknown
Reader: withheld
```

Defaultと同じ行は保存しない。

---

## 39. Thread

Major Threadはシリーズ全体で追跡する。

状態は少なくとも次を区別する。

```text
open
in_progress
resolved
retired
```

Scene action:

```text
introduce
advance
resolve
retire
```

Required Major Threadはretireできず、最終Completionまでにresolvedでなければならない。

---

## 40. Story clock

Story clockは:

```text
採用Scene順
物語上の時刻label
parallel group
最後のScene
現在のVolume／Chapter／Scene
```

を持つ。

Scene Commitだけが`current_order`を1増やす。

Volume Handoff CommitはStory clockを変えない。

---

## 41. GenerationとScene順

Generationはすべての採用Commitで進む。

```text
initial_design
Scene
Volume Handoff
```

Scene順はScene Commitだけで進む。

したがって:

```text
Generation ID = Scene順
```

とは限らない。

Canonical fixtureでは:

```text
47 Scene commits
4 Volume Handoff commits
final Generation = 00000051
final current_order = 47
```

---

## 42. continuity delta

本文から抽出される候補deltaは、Scene Cardで許可された永続的変化だけを含む。

代表的なbranch:

```text
既存項目更新
新規項目提案
Knowledge item提案
Character／Reader Knowledge更新
Thread更新
Ending Evidence提案
時間更新
safe handoff summary
```

LLMは`before`値、永続ID、Evidence ID、offset、hashを生成しない。

---

## 43. Evidence

永続的な更新は、凍結本文に一度だけ現れる完全一致quoteで裏付ける。

コードは次を計算する。

```text
Unicode code-point start/end offset
quote SHA-256
prose SHA-256
Evidence ID
```

ParaphraseやPublicationで追加したheadingはEvidenceにならない。

---

## 44. Scene Commit

Scene Card、本文、candidate deltaはCheckpointであり、まだ採用済みではない。

Scene Commitは次を一つのtransactionとして行う。

```text
更新許可とbefore値検証
ID採番
Evidence作成
committed delta作成
Canon／Knowledge／State／Evidence root作成
Scene artifact作成
Commit／Generation manifest作成
全hash・差分検証
最終pathへのmove
canon/HEAD更新
```

---

## 45. 双方向差分保証

Scene Commitは次を両方向に証明する。

```text
committed deltaの全変更がafter rootsに存在する
parentからafter rootsへの全変更がcommitted deltaに存在する
```

隠れたState変更や適用されないdeltaを採用しない。

---

## 46. HEAD

現在の採用済みStory snapshotは:

```text
canon/HEAD
```

が選ぶ。

Generation directoryが存在するだけでは採用済みではない。

HEADは、Generationと必要なScene/Handoff artifactがdurableかつ再検証済みになった後、最後に更新する。

---

# Part V: Volume Handoff

## 47. Handoffの目的

各巻の最後に、実際に採用された巻末Stateから次を作る。

```text
人物・Relationshipのcarry-over
Threadの巻末判断
Knowledge／Reader status
重要World項目
次巻制約
risk
safe summary
```

全本文を再要約するartifactではない。

---

## 48. Handoffの採用

Volume Handoffも独立したCommit／Generationとして採用する。

変更できるStory Stateは:

```text
thread_states[].volume_disposition
```

だけである。

次は親Generationと同一でなければならない。

```text
Canon
Knowledge item
Evidence index
Story clock
Scene order
```

---

## 49. Volume disposition

巻境界のThread判断:

```text
resolve
carry_over
retire
```

これはThread statusとは別である。

Required Major Threadを`retire`できない。

最終巻のRequired Major Threadは`resolve`でなければならない。

---

## 50. 次巻開始

非最終巻のHandoff採用後、次巻のVolume designを作る。

次巻は:

```text
Series mapだけ
```

ではなく:

```text
現在のHandoff HEAD
前巻Handoff
採用済みSeries map
```

から開始する。

---

# Part VI: Completion

## 51. Completion開始条件

Completionは最終Scene直後ではなく、最終Volume HandoffがHEADに採用された後に開始する。

---

## 52. COMP-PRE

LLMを呼ぶ前にコードが機械的完了条件を検証する。

代表例:

```text
最終HEAD graph
最終Commit typeがvolume_handoff
全Volume／Chapter plan
全計画Sceneと非空本文
Scene／Evidence／hash整合
Story clockとScene commit数
全Required Major Thread
全Required Ending criterion
全Handoff
残存Issue audit
active Candidate／Checkpoint／stagingがない
Completion Contextがtoken上限内
```

一つでも失敗すればCompletion LLMを呼ばず、mechanical failureとする。

---

## 53. Completion audit

COMP-PRE成功後、LLMが意味的完結性を監査する。

結果:

```text
complete
complete_with_residual_issues
incomplete
```

各Required criterionとRequired Major Threadを個別に評価する。

---

## 54. Completion attempt

Completionは通常のReview／Revision loopを使わない。

構造不正だけがbounded attemptの理由である。

最初の構造正常な結果を採用する。

---

## 55. Meaningful incomplete

構造正常な`incomplete`は正当な監査結果である。

Storycraftは:

```text
completeへ変えるために再試行しない
本文・Canon・Stateを自動修正しない
Completion auditをそのまま保存する
diagnostic publication stagingとValidationを作る
Publication Gateをfailにする
CURRENTを更新しない
manual interventionとして停止する
```

---

## 56. Residual completion

`complete_with_residual_issues`は、Required条件は満たすが、非致命的な残存Issueを持つ状態である。

機械的Publication検証が通れば公開採用できる。

残存Issueはreader-facing manuscriptへ混入させない。

---

## 57. Completionの非変更性

Completion Stageは次を変更しない。

```text
本文
Canon
Knowledge
Story State
Evidence
plan
Scene artifact
Handoff
canon/HEAD
```

Completionは評価とaudit保存だけを行う。

---

# Part VII: Publication

## 58. Publicationの意味

Publicationは、現在の採用済みStory snapshotとCompletion auditから作る、reader-facingなimmutable出力一式である。

Publication directoryが存在するだけでは採用済みではない。

---

## 59. Publication ID

Publicationごとにコードが:

```text
pub-NNNNNN
```

形式のIDを採番する。

失敗したPublication IDは再利用しない。

---

## 60. Default publication layout

Default local KDP publication:

```text
manuscript/
  series.md
  v01.md
  v02.md
  ...

metadata/
  series.json
  volumes/
    v01.json
    v02.json
    ...

reports/
  completion-audit.json

publication-validation.json
publication-manifest.json
```

---

## 61. 全巻Markdown

`manuscript/series.md`は全巻をCanonical順で含む。

順序は:

```text
Series mapのVolume順
Volume designのChapter順
Chapter designのScene順
```

で決まり、filesystemのmtimeや列挙順には依存しない。

---

## 62. 巻別Markdown

`manuscript/vNN.md`は対象巻の全ChapterとSceneを順序通りに含む。

コードは採用済みplan titleから決定的なVolume／Chapter headingを追加できる。

HeadingはScene proseやEvidenceの一部ではない。

---

## 63. Reader-facing除外

Publicationへ次を含めない。

```text
Persistent record ID
Scene ID
Commit／Generation／Evidence ID
workspace内部path
Candidate／Checkpoint／staging path
Review／residual Issueのprivate text
private Completion audit
provider/runtime metadata
author truth
credential
```

---

## 64. Publication metadata

Series metadataは読者・配布向けに必要な情報だけを持つ。

代表例:

```text
title
genre
target reader
volume count
profile ID
source Generation
Completion overall assessment
created timestamp
```

Volume metadataは:

```text
Volume番号・title
Chapter／Scene数
本文文字数
source plan／Handoff hash
manuscript相対path／hash
```

を持つ。

---

## 65. Publishing profile

Default publishing profileはローカルKDP向けMarkdownを作る。

Profileは次を表せる。

```text
platform
manuscript format
巻数範囲
第1巻と後続巻のaccess方針
巻内局所解決要件
非最終巻reader question要件
追加の登録済みpayload role
```

StorycraftはProfileを外部ストアへ送信しない。

---

## 66. Publication Validation

OUT-02はPublication payloadの存在、path、size、hash、内容規則を検証する。

Validationはpayload setをhashする。

Final ManifestはpayloadとValidationを含むcontent setをhashする。

Manifestは自身をhashしない。

---

## 67. Publication Gate

COMP-PUBLISHは外部Gateを作る。

Gate passに必要:

```text
Completion = completeまたはcomplete_with_residual_issues
全Completion mechanical check成功
Publication Validation成功
Manifest・payload/content/snapshot hash成功
```

COMP-PUBLISHはPublicationをrenameせず、`output/CURRENT`も変更しない。

---

## 68. Publication adoption

OUT-03だけがPublicationを採用する。

順序:

```text
staging root検証
同一Gate snapshot検証
publications/<id>/へrename
final rootで再検証
output/CURRENTを最後に更新
Run Stateをcompletedへ更新
```

---

## 69. CURRENT

現在の採用済みPublicationは:

```text
output/CURRENT
```

が選ぶ。

`publications/<id>/`が存在してもCURRENTが指していなければ未採用である。

---

## 70. Completed

Runがcompletedとなる条件:

```text
OUT-03完了
valid output/CURRENT
Run State current_publication_idがCURRENTと一致
next_stage = null
stop reason = completed
```

Gate passやPublication directory renameだけではcompletedではない。

---

# Part VIII: Workspaceと監査

## 71. Workspace

Workspaceは次を分離して保存する。

```text
input
Runtime authority
Candidate history
Context snapshots
Scene Checkpoint
Canon Generations
plans
Scene／Handoff artifacts
Completion／LLM／operation audit
staging transactions
adopted Publications
CURRENT
quarantine
redacted logs
```

正確なpathは[Workspace layout](../design/workspace_layout.md)を正本とする。

---

## 72. Artifact class

Canonical artifact class:

```text
candidate
checkpoint
staged_internal
staged_internal_validation
adopted
audit
```

複合表記やlegacy classは使用しない。

---

## 73. Candidate history

候補は`v0001`、`v0002`のようにversioned保存する。

選択される候補はRun Stateが指すCandidate manifestだけである。

最大versionや更新日時からactive候補を推測しない。

---

## 74. Checkpoint

一つのScene lifecycleでは次のCheckpoint phaseを持つ。

```text
CARD_ACCEPTED
PROSE_FROZEN
DELTA_ACCEPTED
COMMIT_PREPARED
```

Checkpoint manifestのphaseが正本であり、ファイルの存在だけではphaseを進めない。

---

## 75. Audit

Auditには次を保存する。

```text
LLM call
Review
code operation
residual issue
Completion
Publication Gate
recovery／quarantine
```

Auditは「何が起きたか」の証拠であり、Candidateやresume sourceの代用ではない。

---

## 76. LLM call audit

各provider HTTP attemptは一意のCall IDとauditを持つ。

記録対象:

```text
Stage／target／role
Context／prompt／Schema／config identity
redacted request／response
usage
timing
outcome
error
```

Credentialは保存しない。

---

## 77. Log

通常logは人間向けのredacted operational logである。

Logはresume authorityではない。

---

## 78. Retention

Audit retentionと容量上限は設定可能である。

Retention処理は:

```text
採用済み正本
active Candidate
active Checkpoint
resumeに必要なtransaction
```

を削除してはならない。

---

# Part IX: Crash、再開、停止

## 79. Crash耐性

各durable boundaryはCrash後に次の一つへ分類できなければならない。

```text
reconcile
resume
regenerate
quarantine
explicit recovery
manual intervention
```

意味内容を推測する分類は認めない。

---

## 80. Candidate Crash

代表的な挙動:

| durable状態 | 製品挙動 |
|---|---|
| Candidateとvalid selected manifest | その候補から再開 |
| Candidate fileだけ | quarantineして再生成 |
| Manifestだけ | quarantineして再生成 |
| raw audit成功だけ | 新Call IDでprovider callを再実行 |
| referenced valid Review | Reviewを繰り返さずroute |
| stale source Generation | Scene／候補chainを無効化して再生成 |

---

## 81. Scene Commit Crash

HEAD変更前のfinal-looking Generation／Sceneは未採用である。

通常startupは、それらを見つけてもHEADを書き換えない。

HEAD変更後にRun Stateだけが遅れている場合:

```text
HEAD graphを検証
次のScene／Chapter／Handoff routeを再構成
provider call・ID採番を繰り返さない
Run Stateをreconcile
```

---

## 82. Handoff Crash

Handoff artifactまたはGenerationが存在しても、HEADから参照されなければ未採用である。

HEAD変更後は、Commit typeから次巻またはCompletionへreconcileする。

---

## 83. Publication Crash

代表的な境界:

| durable状態 | 製品挙動 |
|---|---|
| payload部分作成 | transaction identityからOUT-01再開または再生成 |
| Validation／Manifest不足 | OUT-02再開 |
| Gate不足 | COMP-PUBLISH再開 |
| Gate pass＋staging root | OUT-03通常再開 |
| final publicationへrename済み、CURRENT旧 | 元のGateを使う明示的OUT-03 recovery |
| CURRENT新、Run State旧 | completedへreconcile |
| stagingとfinalの両方 | manual intervention |

---

## 84. Orphan

次から到達できないartifactはorphan候補である。

```text
valid HEAD
valid CURRENT
Run-selected Candidate
Run-selected Checkpoint
referenced transaction
```

Orphanは証拠付きでquarantineする。

Quarantineから自動採用しない。

---

## 85. Counter recovery

Counterは観測された全IDより大きくなければならない。

Counterが先行しているgapは正常である。

Counterが観測IDより小さい場合、Storycraftは黙って修正せずmanual interventionとする。

---

## 86. User stop

利用者の停止要求は安全なdurable boundaryで反映する。

停止要求により次の途中で強制終了しない。

```text
ID persist-before-use
atomic file replace
directory rename
HEAD／CURRENT transaction
```

---

## 87. Budget stop

次のLLM call前に予算を再計算する。

上限を超えるcallは送信せず、安全なstopとして保存する。

使用済みCall・token・cost・timeは減算しない。

---

## 88. Resume compatibility

Resumeは少なくとも次を比較する。

```text
workspace/state/code version
prompt bundle
Schema bundle
immutable config fingerprint
provider/modelの固定条件
active Candidate／Context identity
```

非互換の場合、candidateを自動migrationせず停止する。

---

## 89. Manual intervention

自動続行しない代表例:

```text
invalid HEAD／CURRENT graph
counter regression
競合するimmutable plan
stagingとfinal Publicationが両方存在
unsupported config／workspace migration
意味的にincompleteなCompletion
```

---

# Part X: 品質、Privacy、Security

## 90. 品質の定義

Storycraftの品質は次の組合せで評価する。

```text
Brief忠実性
計画の長期整合性
Scene目的・beatの充足
POV・Knowledge・開示境界
Canon／State／Evidence整合
Required Thread／Ending完結
自然な日本語
巻内局所解決
publicationのdeterministic再現性
```

単一のLLM自己評価だけで品質を決定しない。

---

## 91. 機械的品質と意味的品質

### 機械的品質

```text
Schema
path
ID
hash
参照
transition
offset
manifest
pointer
```

コードが判定する。

### 意味的品質

```text
物語の説得力
Sceneの自然さ
計画への忠実性
矛盾・開示・未達条件
```

LLM ReviewとCompletion auditが補助する。

Reviewは機械的契約を上書きできない。

---

## 92. Privacy

Private artifactに含み得るもの:

```text
author truth
Endingの非公開設計
Thread resolution condition
Knowledge author truth
private Review
private Completion audit
Context snapshot
```

Publicationはこれらを除外する。

---

## 93. Prompt injection

Brief、prose、Review text、notes内の命令風文字列は、prompt上で作業dataとして扱う。

例:

```text
以前の指示を無視する
JSONではなくMarkdownを返す
hidden endingを開示する
API keyを出力する
```

これらがStage・Schema・response形式を変更してはならない。

---

## 94. Filesystem security

Workspace pathは:

```text
相対path規則
case
symlink／junction escape
traversal
絶対path混入
pointer bytes
```

を検証する。

Workspace contentをPython objectとしてdeserialize・実行しない。

---

## 95. Network

Provider call以外の外部retrievalを行わない。

Promptはmodelへ次を要求しない。

```text
Web検索
filesystem path読取
別会話の記憶利用
外部tool利用
```

---

## 96. Determinism

同じ採用済みartifactと同じcode/profile versionから作る次は、byte-for-byte再現可能でなければならない。

```text
Canonical JSON
pointer
Context snapshot
generated heading
publication manuscript assembly
metadata
Validation／Manifest hash set
```

LLM本文自体の再生成一致はprovider特性に依存するが、一度採用された本文と派生publicationは決定的である。

---

# Part XI: Performanceと運用

## 97. 長時間実行

Storycraftは複数巻を順次生成するため、長時間実行を前提とする。

製品は:

```text
各Stage境界でdurable progress
timeout
safe stop
resume
budget
usage audit
```

を提供する。

---

## 98. Memory

シリーズ全体を一つの巨大なmutable objectとして常駐させない。

現在Stageに必要な:

```text
HEAD snapshot
対象plan chain
選択されたContext／Candidate／Checkpoint
必要なprose／Evidence
```

を読み込む。

---

## 99. Context budget

各LLM callはmodel context window内でなければならない。

Storycraftは:

```text
operation別reserved output
protocol overhead
静的prompt
Context payload
Schema送信量
```

を含む最終request全体をpreflightする。

上限超過時はCall ID採番前に停止する。

---

## 100. Timeout

Timeoutは少なくとも次を区別する。

```text
connect
first event
idle
total call
```

Testではfake clockを使い、実時間待機を要求しない。

---

## 101. Progress表示

進捗は採用済みplanとRun Stateから表示する。

代表例:

```text
現在Stage
対象Volume／Chapter／Scene
全巻数
HEAD Generation
Publication ID
Run status
```

Directory数や最新fileから進捗を推測しない。

---

## 102. Inspection

利用者・開発者はworkspaceから次を確認できる。

```text
現在のRun State
現在HEADとCURRENT
採用済みplans
採用済みScene／Handoff
LLM／operation audit
Completion result
Publication Validation／Manifest
quarantine理由
```

Inspectionは正本を変更しない。

---

# Part XII: Product result states

## 103. Running

`running`:

```text
次のCanonical Stageがある
terminal stop reasonがない
authoritative sourceがvalid
```

---

## 104. Paused／Stopped

安全に一時停止し、互換性検証後にresume可能な状態。

原因例:

```text
user stop
budget stop
運用上の一時停止
```

---

## 105. Failed

機械的契約違反、provider exhaustion、無効な正本などにより自動実行できない状態。

Failed時も、既にdurableなcandidate、audit、counter、採用済みartifactを保持する。

---

## 106. Manual intervention

意味的incompleteや正本競合など、自動推測を避けるため人間判断を要求する状態。

CURRENTは更新されない。

---

## 107. Completed

有効なPublicationがCURRENTに採用され、Run Stateが一致する状態。

---

# Part XIII: 受入基準

## 108. Happy path

受入試験は、少なくとも次を一つの公開API／CLI runで証明する。

```text
KeywordsまたはBrief
Genesis
Series／Volume／Chapter plans
複数Scene Commit
複数Volume Handoff
最終Completion
Publication Validation／Gate
OUT-03
CURRENT
completed
```

---

## 109. 代表fixture

Canonical fixtureは次を証明する。

- [Initial and planning fixture](../design/examples/initial_and_planning_fixture.md)
- [Scene commit fixture](../design/examples/scene_commit_fixture.md)
- [Completion and publication fixture](../design/examples/completion_publication_fixture.md)

FixtureはSchemaの代替ではなく、全契約が同時に成立する証拠である。

---

## 110. Required failure paths

少なくとも次を受入試験する。

```text
invalid input
config error
lock conflict
transport retry/exhaustion
response-structure retry/exhaustion
Review Revision/exhaustion
stale Candidate
Candidate/Manifest片側Crash
Checkpoint phase Crash
Scene Commit各境界Crash
Handoff各境界Crash
Completion incomplete
Publication Gate failure
Publication rename/CURRENT Crash
counter regression
invalid HEAD/CURRENT
prompt injection
private data leakage
wheel asset欠落
```

---

## 111. Reproducibility gate

同じ採用snapshotからPublicationを再構築し、次が一致する。

```text
manuscript bytes
metadata bytes
payload_set_sha256
content_set_sha256
publication_snapshot_sha256
```

---

## 112. Privacy gate

Writer Context、Continuity Context、publicationをbyte-searchし、登録したprivate sentinelが存在しないことを要求する。

---

## 113. Crash gate

登録したすべてのfailpointで再起動し、期待される一つのaction:

```text
reconcile
resume
regenerate
quarantine
explicit recovery
manual intervention
```

と一致することを要求する。

---

## 114. Packaging gate

Source tree外へwheelをinstallし、次を要求する。

```text
全prompt／Schema assetが読める
structured Stageをrenderできる
prose Stageをrenderできる
CLI helpがcredentialなしで動く
source-tree fallbackなし
```

---

## 115. No-network gate

Mandatory test suiteはunmocked socketを開かない。

実provider integration testは任意の別suiteとする。

---

## 116. Implementation status

本仕様の機能が文書化されていても、現行コードが実装済みとは限らない。

実装済みと主張する条件は[Implementation acceptance](../design/implementation_acceptance.md)の必須gateを満たすことである。

差分は[実装状況](IMPLEMENTATION_STATUS.md)へ記録する。

---

# Part XIV: 用語

## 117. Candidate

構造正常で、まだ採用されていない生成・抽出・Revision成果物。

---

## 118. Review

候補に対する意味監査を保存する`audit` artifact。

候補そのものではない。

---

## 119. Checkpoint

一つのScene transaction内で、後続Stageへ渡す凍結artifactとphase authority。

後続Sceneの正本ではない。

---

## 120. Adopted artifact

正規のadoption pointまたはimmutable final path契約により、後続工程の正式入力となったartifact。

---

## 121. Generation

一つのCommitが作るimmutable Story snapshot。

Canon、Knowledge、Story State、Evidence index、Commit／Generation manifestを含む。

---

## 122. Commit

Genesis、Scene、Volume Handoffのいずれかにより、親Generationから子Generationを作る採用操作。

---

## 123. HEAD

現在の採用済みStory Generationを選ぶpointer。

---

## 124. Handoff

一つのVolume終了Stateを次巻またはCompletionへ渡すprivate adopted artifact。

---

## 125. Completion audit

最終Story snapshotがRequired ThreadとEnding criterionを満たすかを評価するprivate audit。

---

## 126. Publication

Reader-facing manuscript、metadata、safe report、Validation、Manifestからなるimmutable出力directory。

---

## 127. Gate

Publicationを採用してよいかを判定したrename-stableな外部audit。

Gate自体は採用を行わない。

---

## 128. CURRENT

現在の採用済みPublicationを選ぶpointer。

---

## 129. Residual issue

Revision上限後も残る、機械的契約違反ではない意味的Issue。

---

## 130. Orphan

正本pointer、Run-selected Candidate／Checkpoint、参照transactionから到達できないartifact。

---

## 131. Durable boundary

Crash後に、重複・推測なしで次の動作を決められる完全保存点。

---

## 132. Manual intervention

正本を推測して自動修復せず、人間判断を要求するterminal状態。

---

# Part XV: 製品不変条件

## 133. 最終不変条件

Storycraftは、任意の観測可能な時点でdurable dataから次へ答えられなければならない。

```text
どのRunか
現在のStageとtargetは何か
どのinput／source Generationを使ったか
どのCandidate／Checkpoint／transactionが選択されているか
どのID・usageが消費済みか
どのStory GenerationがHEADか
どのPublicationがCURRENTか
次に合法なStageは何か
ここでCrashした場合に何をするか
```

この答えが次へ依存する場合、製品仕様を満たさない。

```text
最新mtime
最大番号の未参照directory
一つの巨大なin-memory state
normal log
LLMの自己申告
unreferenced staging
```

---

## 134. 製品受入条件

本製品仕様は、実装が次を同時に満たしたときにのみ受入可能である。

```text
4〜10巻の日本語シリーズ
Brief／Keywordsの排他的入力
run／resume／step
50 Stageの正確な進行
Review／Revision／residual issue
Writer-safe本文
Evidence付きScene Commit
HEAD-last Story adoption
Volume Handoff
正直なCompletion audit
incompleteの非再試行・非公開
deterministic Publication
GateとOUT-03の分離
CURRENT-last Publication adoption
Crash recovery
ID／usage非再利用
private/public分離
package-only prompt／Schema
必須acceptance gate
```
