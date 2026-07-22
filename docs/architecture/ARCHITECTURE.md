# Storycraft アーキテクチャ

この文書は、Storycraft Version 1の最上位アーキテクチャを定める。

この文書は、次の役割を一つに統合する。

```text
設計原則
システム全体像
主要componentの責務
正本と補助情報の区別
主要用語
文書間の責務
禁止する過剰設計
```

既存の`ARCHITECTURE_PRINCIPLES.md`は、この文書へ統合して廃止する。

以後の製品仕様、要件、詳細設計、実装、試験がこの文書と矛盾する場合は、下位文書または実装を修正する。

---

# Part I: 製品前提

## 1. Storycraftとは

Storycraftは、単一利用者がローカル環境で使う、日本語長編シリーズ生成CLIである。

一つの入力から、次を順に作成する。

```text
初期設計
シリーズ計画
巻計画
章計画
Scene Card
Scene本文
継続性更新
巻Handoff
完結判定
Publication
```

Storycraftの目的は、単に文章を生成することではない。

長編シリーズに必要な次の要素を、明示的な状態として管理しながら執筆を進める。

```text
人物
関係
世界
Knowledge
Thread
Ending
時間
所有物
位置
計画
Scene
```

---

## 2. Version 1の利用前提

Version 1は、次の前提へ限定する。

```text
一つのworkspace
一つの利用者
一つの書き込みprocess
ローカルfilesystem
一つの実行状態
一つのactive run
外部監査主体なし
悪意ある改ざんへの耐性は対象外
```

この制限は欠点ではなく、Version 1の設計を単純に保つための明示的な判断である。

---

## 3. 対象外

Version 1では次を対象外とする。

```text
複数writerによる同時編集
分散worker
remote database
object storage
network filesystem
shared workspace
外部署名
改ざん証明
第三者監査
高可用性cluster
自動的な外部Web検索
別会話memoryの利用
```

将来必要になった場合は、新しいmajor versionの設計課題として扱う。

---

## 4. 最優先事項

設計判断は、次の順で優先する。

```text
1. 実装しやすさ
2. Crash後の理解しやすさ
3. workspaceの人間可読性
4. データ喪失の防止
5. 生成品質
6. 将来拡張性
```

将来の可能性だけを理由に、現在不要な複雑性を導入してはならない。

---

# Part II: 設計原則

## 5. 単純さを優先する

Storycraftは、必要性を説明できない仕組みを持たない。

新しい仕組みを導入する場合は、次を説明しなければならない。

```text
何を防ぐのか
失敗時に何をするのか
より単純な方法では代替できないのか
利用者にどのような価値があるのか
```

説明できない場合、その仕組みは追加しない。

---

## 6. 単一writer

一つのworkspaceへ書き込めるprocessは常に一つだけとする。

実装は排他lockを取得する。

Lockを取得できない場合は、同じworkspaceで別の書き込みprocessが動作中として明確に失敗する。

Lockの目的は同時書き込みの防止であり、分散合意や複雑なlease protocolではない。

---

## 7. ローカルfilesystem

Version 1はローカルfilesystemだけを対象とする。

設計は次を前提にしてよい。

```text
同一machine
同一workspace root
通常のatomic file replacement
通常のdirectory rename
一つのprocessが書き込む
```

Network filesystem、remote storage、eventual consistencyは考慮しない。

---

## 8. 一つの実行状態

現在の実行位置を表す正本は、一つの実行状態ファイルとする。

推奨path:

```text
runtime/run-state.json
```

現在位置を複数のpointer、Manifest、Gateへ重複保存しない。

---

## 9. 完全ファイル更新

変更可能なJSONは、部分更新せず完全ファイルとして書き換える。

基本手順:

```text
一時ファイルへ完全な内容を書く
読み直して検証する
atomic replaceする
```

次は使用しない。

```text
JSON Patchによる永続状態更新
追記だけによる現在状態管理
file内のin-place edit
```

---

## 10. 確定済みdirectoryは上書きしない

確定済み成果物directoryはimmutableとする。

例:

```text
generations/000012/
scenes/v01-c001-s002/
publications/pub-000001/
```

同じIDのdirectoryを上書きしてはならない。

修正が必要な場合は、新しいIDまたは新しいversionを作る。

---

## 11. 一時directoryから確定する

複数ファイルで構成される成果物は、一時directoryで完成させてから最終pathへrenameする。

例:

```text
runtime/staging/scene-v01-c001-s002/
→
scenes/v01-c001-s002/
```

最終directoryが存在し、必須ファイルが読めることを、確定完了の主要な証拠とする。

---

## 12. Hashは原則使用しない

SHA-256などのhashは、原則として保存契約へ含めない。

不要な例:

```text
本文hash
Context hash
Candidate hash
Review hash
計画hash
Canon root hash
State root hash
開始前確認hash
Publication集合hash
```

Hashを導入できるのは、次の条件をすべて満たす場合だけである。

```text
具体的な用途がある
検出後の処理が決まっている
IDとimmutable directoryでは代替できない
設計を大きく複雑化しない
```

「念のため」や「改ざん検知のため」だけでは導入しない。

---

## 13. Manifest graphを作らない

Version 1では、複数Manifestが互いを参照するgraphを作らない。

原則として不要:

```text
Candidate Manifest
Checkpoint Manifest
Commit Manifest
Generation Manifest
Publication Manifest
Publication Gate
Validation Manifest
```

必要な識別情報は、成果物directory内の単純な`metadata.json`または`commit.json`へまとめる。

---

## 14. 複数の正本を作らない

同じ事実について複数の独立authorityを持たない。

例:

```text
現在Generation
現在Publication
現在Stage
active Scene
run status
```

これらは一つの実行状態へ記録する。

補助pointerを設ける場合は、再生成可能な表示用情報とし、正本にしない。

---

## 15. 人間可読性を優先する

Workspaceは、特殊toolなしに通常のfile browserとeditorで理解できなければならない。

設計は、次を一目で確認できることを目指す。

```text
現在どこまで進んでいるか
最新の採用済みGeneration
各Sceneの本文
現在のStory State
完結判定
最新Publication
```

---

# Part III: システム全体像

## 16. 論理構成

Storycraftは、次の論理componentで構成する。

```text
+-----------------------+
| CLI                   |
| run / resume / step   |
+-----------+-----------+
            |
            v
+-----------------------+
| Engine                |
| Stage / Loop / Retry  |
+-----+------------+----+
      |            |
      v            v
+-----------+  +----------------+
| Provider  |  | Workspace      |
| Adapter   |  | Storage        |
+-----------+  +----------------+
      |
      v
+-----------------------+
| LLM Provider          |
+-----------------------+
```

補助component:

```text
Prompt loader
Context builder
Schema validator
Reviewer
Revision controller
Publication builder
Recovery controller
Audit logger
```

---

## 17. CLIの責務

CLIは、利用者からの操作を受け付ける。

公開command:

```text
run
resume
step
```

CLIの責務:

```text
argument確認
workspace選択
設定読込
lock取得要求
Engine起動
進捗表示
期待されたerrorの表示
終了codeの返却
```

CLIはStory状態を直接変更しない。

---

## 18. Engineの責務

Engineは、実行全体を制御する。

主な責務:

```text
現在Stageの決定
Stage入力の構築
Provider callの実行
形式確認
Review／Revision制御
Retry制御
成果物の確定
実行状態の更新
停止条件の評価
```

Engineは保存形式の詳細を直接散在させず、Workspace操作へ委譲する。

---

## 19. Provider Adapterの責務

Provider Adapterは、外部LLM providerとの差異を吸収する。

主な責務:

```text
request作成
credential取得
timeout
structured response
streamまたはnon-stream response
usage取得
error分類
```

Provider固有の形式を、EngineやStoryデータへ漏らしてはならない。

---

## 20. Workspaceの責務

Workspaceは、永続状態と成果物を保存する。

主な責務:

```text
path管理
atomic file replacement
staging directory管理
確定済みdirectoryのrename
run-state読書き
counter管理
採用済み成果物の読込
Recovery用の存在確認
```

WorkspaceはStoryの意味判断を行わない。

---

## 21. Prompt Loaderの責務

Prompt Loaderは、installed package内のprompt assetを読み込む。

主な責務:

```text
operationに対応するprompt選択
共通instructionの組立
version確認
欠落assetのerror化
```

Source tree fallbackを前提にしない。

---

## 22. Context Builderの責務

Context Builderは、各StageでLLMへ渡す入力資料を組み立てる。

主な責務:

```text
必要情報の選択
不要情報の除外
Writer秘密境界の適用
token量の確認
Stage固有構造への整形
```

Contextは正本ではなく、一時的な入力資料である。

---

## 23. Schema Validatorの責務

Schema Validatorは、構造化応答と保存JSONの形式を検証する。

主な責務:

```text
必須field確認
型確認
enum確認
未知field拒否
cross-field制約
UTF-8／NFC／有限数確認
```

Schema定義はproductionとtestで共用する。

---

## 24. Review／Revision制御の責務

Reviewは候補の問題点を返す。

Revisionは候補全体の置換版を返す。

制御componentは次を管理する。

```text
Review回数
Revision回数
issueの受入
修正版候補
停止条件
```

Reviewが直接候補を書き換えてはならない。

---

## 25. Publication Builderの責務

Publication Builderは、採用済みplanとScene本文からreader-facing成果物を組み立てる。

主な責務:

```text
Scene順の確認
巻別Markdownの作成
全巻Markdownの作成
metadataの作成
completion resultの添付
private情報の除外
```

Publication Builderは新しいStory事実を生成してはならない。

---

## 26. Recovery Controllerの責務

Recovery Controllerは、Crash後の状態を分類する。

分類:

```text
再開
再生成
人間対応
```

複雑なManifest graphやhash chainを使用しない。

---

## 27. Audit Loggerの責務

Audit Loggerは、開発・障害調査・利用量確認に必要な情報を記録する。

代表的な内容:

```text
Stage
target
provider
model
request時刻
response時刻
usage
result
error
```

AuditはStory状態やCandidateの正本ではない。

---

# Part IV: データとAuthority

## 28. Authorityの階層

Storycraftの正本は、次の優先順で扱う。

```text
1. 実行状態
2. 確定済みGeneration
3. 確定済みplan
4. 確定済みScene
5. 完結結果
6. 確定済みPublication
```

Audit、Context、Review、staging成果物は補助情報であり、正本ではない。

---

## 29. 実行状態

実行状態は、現在のrun位置を表す唯一の正本である。

最低限持つ情報:

```text
run_id
status
current_stage
current_target
current_generation
current_publication
active_candidate
active_scene
stop_reason
updated_at
```

詳細なfield契約は`design/WORKSPACE_AND_RECOVERY.md`へ置く。

---

## 30. Generation

Generationは、一つの採用済みStory状態を表すimmutable directoryである。

推奨構成:

```text
generations/000012/
  canon.json
  state.json
  evidence.json
  commit.json
```

GenerationはScene確定や初期設計採用など、Story状態が変わる境界で作る。

---

## 31. Scene

Sceneは、採用済みScene成果物をまとめたimmutable directoryである。

推奨構成:

```text
scenes/v01-c001-s002/
  scene-card.json
  prose.md
  continuity.json
  commit.json
```

Scene本文と継続性更新を別々のauthorityにしない。

---

## 32. Candidate

Candidateは、Review前またはRevision中の未採用候補である。

Candidateは正本ではない。

Candidateは上書きしてよいが、Reviewや障害調査に必要な範囲でversionを保持してよい。

Candidateを採用済み成果物と同じdirectoryへ置かない。

---

## 33. Review

Reviewは、Candidateに対する問題点の集合である。

Reviewは次を行わない。

```text
Candidateの書換え
採用済み状態の更新
次Stageの決定
Story事実の追加
```

Reviewは正本ではない。

---

## 34. Revision

Revisionは、Reviewを受けて作られたCandidate全体の置換版である。

Patchやdiffだけを永続成果物として使用しない。

---

## 35. Evidence

Evidenceは、継続性更新の根拠となる本文箇所を人間が確認できるようにする情報である。

最低限:

```text
scene_id
quote
target
change
```

改ざん証明や法的証拠を目的としない。

---

## 36. Handoff

Handoffは、Volume終了時点の実際のStory状態を、次のVolumeまたは完結判定へ引き渡すための要約である。

Handoffは新しいStory事実を作らない。

---

## 37. Completion

Completionは、シリーズがPublication可能な完結状態かを評価した結果である。

状態:

```text
complete
complete_with_issues
incomplete
```

`incomplete`を意味的失敗として無制限に再試行してはならない。

---

## 38. Publication

Publicationは、reader-facing成果物をまとめたimmutable directoryである。

推奨構成:

```text
publications/pub-000001/
  series.md
  v01.md
  v02.md
  metadata.json
  completion.json
```

Publicationは採用済み成果物から決定的に組み立てる。

---

# Part V: 実行モデル

## 39. 意味的Stage

Stageは、利用者、生成モデル、再開処理にとって意味のある工程だけにする。

推奨分類:

```text
入力
初期設計
シリーズ計画
巻計画
章計画
Scene Card
本文
継続性更新
Scene確定
巻Handoff
完結判定
Publication
```

Schema確認、ID割当、rename、状態更新などは内部処理であり、原則として独立Stageにしない。

---

## 40. Loop

Storycraftは、次のloopを持つ。

```text
Series loop
Volume loop
Chapter loop
Scene loop
Review／Revision loop
```

Loopの境界は`design/PIPELINE.md`で定義する。

---

## 41. Scene中の基準状態固定

一つのSceneについて、次が完了するまで基準Generationを変えない。

```text
Scene Card
本文
継続性更新
Scene確定
```

途中で基準Generationが変わった場合は、そのScene処理を再利用せずやり直す。

---

## 42. Retryの分類

次を別々に扱う。

```text
通信失敗
応答形式不正
意味的Revision
```

それぞれに独立した上限を持たせる。

無制限に成功まで繰り返してはならない。

---

## 43. 完結前確認

完結判定の前に、コードで次を確認する。

```text
全Volumeが完了している
全計画Sceneが確定している
Required Threadが存在する
Ending条件が存在する
未完了のScene処理がない
```

確認結果をhash付きの独立artifactにする必要はない。

---

## 44. Publication確定

Publicationは次の手順で確定する。

```text
一時directoryへ全ファイルを書く
必須ファイルを確認する
JSONとMarkdownを読み直す
最終directoryへrenameする
実行状態を更新する
run statusをcompletedにする
```

独立Publication Gateは作らない。

---

# Part VI: 秘密情報とContext

## 45. Writer秘密境界

本文生成へは、Scene執筆に必要な情報だけを渡す。

除外する情報:

```text
未公開の真相
Threadの作者用回答
Endingの内部設計
非POV人物の非公開内面
将来Sceneの詳細
継続性更新の内部処理
```

この境界はhashやManifestより優先する。

---

## 46. Contextの位置付け

ContextはLLMへ渡す一時的な入力資料である。

原則として、hash名fileや恒久的な参照graphを作らない。

保存する場合はCandidateまたはAuditと同じ局所directoryへ置く。

---

## 47. Prompt injectionへの対応

Brief、本文、Review、外部入力内の命令風文字列を、System instructionやStage制御として扱ってはならない。

Story dataと実行命令を分離する。

---

## 48. Credentialの分離

Credential値は次へ保存しない。

```text
設定file
Context
Prompt
Candidate
Audit
Log
Publication
error message
```

Credentialは環境変数など、workspace外のsourceから取得する。

---

# Part VII: CrashとRecovery

## 49. Recovery分類

Crash後の処理は、原則として次の三つに分類する。

```text
再開
再生成
人間対応
```

必要に応じて、不完全な一時directoryを`runtime/orphans/`へ移動してよい。

---

## 50. 再開

次の場合は再開する。

```text
run-state.jsonが読める
現在Stageが分かる
必要な確定済み入力が存在する
途中成果物が完全である
```

---

## 51. 再生成

次の場合は再生成する。

```text
一時directoryが不完全
Candidate fileが不完全
Reviewだけ存在する
Contextだけ存在する
Stage出力が読めない
```

不完全成果物を推測して採用しない。

---

## 52. 人間対応

次の場合は自動修復しない。

```text
run-state.jsonが読めない
run-stateが指す確定済みdirectoryがない
同じIDの最終directoryが競合している
counterが既存IDより小さい
完結判定がincomplete
```

---

## 53. Rename後のCrash

最終directoryへのrename後、実行状態更新前にCrashした場合は、次を確認する。

```text
対象Stageがそのdirectoryを作る予定だった
同じIDの候補が一つだけ存在する
directory内の必須ファイルが読める
```

条件を満たす場合は実行状態を更新して再開する。

---

# Part VIII: 文書構造

## 54. 文書階層

Storycraftの文書は次の階層へ整理する。

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
```

---

## 55. 文書の正本

正本となる文書:

```text
SPECIFICATION.md
REQUIREMENTS.md
ARCHITECTURE.md
DATA_MODEL.md
WORKSPACE_AND_RECOVERY.md
PIPELINE.md
LLM_INTEGRATION.md
ACCEPTANCE.md
```

`IMPLEMENTATION_STATUS.md`は現状報告であり、仕様や設計の正本ではない。

---

## 56. READMEの責務

Root `README.md`は次だけを扱う。

```text
製品の短い紹介
現在の実装状況
install
quick start
文書への入口
```

詳細設計を再掲しない。

---

## 57. docs/README.mdの責務

`docs/README.md`は文書一覧と推奨読書順だけを扱う。

独立した`DOCUMENT_STRUCTURE.md`は作らない。

---

## 58. SPECIFICATIONの責務

`product/SPECIFICATION.md`は、利用者から見た製品仕様だけを扱う。

書かないもの:

```text
directory path
JSON field
atomic rename
Python module
Stage ID
```

---

## 59. REQUIREMENTSの責務

`product/REQUIREMENTS.md`は、検証可能な要件IDと主な確認方法だけを扱う。

利用者向け説明や詳細設計を再掲しない。

---

## 60. IMPLEMENTATION_STATUSの責務

`product/IMPLEMENTATION_STATUS.md`は次だけを扱う。

```text
実装済み
未実装
試験結果
既知の阻害要因
次の実装段階
```

新しい仕様や設計判断を追加しない。

---

## 61. DATA_MODELの責務

`design/DATA_MODEL.md`は、Storyデータの意味と関係の唯一の正本である。

対象:

```text
Brief
初期設計
Canon
State
Knowledge
Thread
Plan
Scene Card
Continuity
Evidence
Handoff
Completion
Publication metadata
```

Stage遷移やCrash処理を定義しない。

---

## 62. WORKSPACE_AND_RECOVERYの責務

`design/WORKSPACE_AND_RECOVERY.md`は、保存とRecoveryの唯一の正本である。

対象:

```text
workspace layout
run-state
counters
atomic write
staging
immutable directory
確定処理
起動確認
resume
再生成
人間対応
```

---

## 63. PIPELINEの責務

`design/PIPELINE.md`は、意味的Stage、Loop、Stage入力出力、Review／Revision、Completion、Publicationの流れを定義する。

JSON fieldや保存手順を再定義しない。

---

## 64. LLM_INTEGRATIONの責務

`design/LLM_INTEGRATION.md`は、Provider、Prompt、Context、秘密情報、structured response、Retry、timeout、budget、Auditを定義する。

StoryデータSchemaやRecovery規則を再定義しない。

---

## 65. ACCEPTANCEの責務

`testing/ACCEPTANCE.md`は、Release判断に必要な試験を定義する。

新しいpath、field、Stage、Recovery規則を追加してはならない。

---

## 66. Exampleとfixture

巨大なMarkdown exampleを正本として持たない。

実際のfixtureは次へ置く。

```text
tests/fixtures/
```

Fixtureの値は実ファイルを正本とする。

`tests/fixtures/README.md`は、目的と利用する試験だけを説明する。

---

# Part IX: 主要用語

## 67. Run

一つのworkspaceで開始され、停止または完了するまでの実行単位。

---

## 68. Stage

利用者、生成モデル、再開処理にとって意味のある処理単位。

内部のfile操作や検証stepをStageとは呼ばない。

---

## 69. Candidate

Reviewまたは採用前の未確定成果物。

正本ではない。

---

## 70. Review

Candidateの問題点を返す評価。

Candidateを直接書き換えない。

---

## 71. Revision

Reviewを受けて作られるCandidate全体の置換版。

---

## 72. Generation

一つの採用済みStory状態を表すimmutable snapshot。

---

## 73. Scene

Scene Card、本文、継続性更新を一つにまとめた採用済み物語単位。

---

## 74. Evidence

継続性更新が本文のどこに基づくかを示す、人間確認用の根拠情報。

---

## 75. Handoff

Volume終了時の実際の状態を、次のVolumeまたは完結判定へ渡す要約。

---

## 76. Completion

シリーズがPublication可能な完結状態かを評価した結果。

---

## 77. Publication

採用済み成果物から組み立てたreader-facing出力directory。

---

## 78. Authority

同じ事実について最終判断に使う正本。

補助情報と区別する。

---

## 79. Immutable

確定後に上書きしないこと。

修正は新しいIDまたはversionとして作る。

---

## 80. Atomic replacement

完全な一時ファイルを、変更対象fileへ一度に置き換えること。

---

## 81. Atomic rename

完成済み一時directoryを、最終directory名へ一度に切り替えること。

---

# Part X: 禁止する過剰設計

## 82. Version 1で導入しないもの

具体的な追加要件がない限り、次を導入しない。

```text
Manifest graph
hash chain
Publication Gate
複数pointer authority
外部署名
改ざん証明
分散lock
event sourcing
複雑なreachability解析
artifactごとの独立status machine
fileごとのhash検証
```

---

## 83. Hash導入チェック

Hashを追加する場合は、次を文書へ記載する。

```text
対象データ
検出する具体的な問題
検出時の処理
ID／path／immutable directoryでは不足する理由
保存期間
利用する処理
```

一つでも説明できない場合は追加しない。

---

## 84. Authority追加チェック

新しいpointer、Manifest、Gate、indexを追加する場合は、次を明確にする。

```text
正本か補助情報か
既存の正本と矛盾した場合どちらを優先するか
Crash後にどう再構築するか
削除できない理由
```

複数の正本を作らない。

---

## 85. 新しい仕組みの追加チェック

新しい仕組みを追加する前に、次を確認する。

```text
利用者のどの問題を解決するか
単一writerでも必要か
ローカルfilesystemでも必要か
実行状態ファイルでは代替できないか
immutable directoryでは代替できないか
atomic renameでは代替できないか
障害時の処理が明確か
文書量と実装量に見合うか
```

---

# Part XI: 最終原則

## 86. Storycraft Version 1の原則

Storycraft Version 1は、次に従う。

```text
Single Writer
Local Filesystem
One Run State
Immutable Final Directories
Atomic Replacement
Atomic Rename
Readable Workspace
Minimal Metadata
Hash Only with a Concrete Use
No Manifest Graph
No External Gate
Simple Recovery
Simple Before Clever
```

任意の設計判断がこの原則より複雑な仕組みを必要とする場合、その必要性を具体的に証明しなければならない。
