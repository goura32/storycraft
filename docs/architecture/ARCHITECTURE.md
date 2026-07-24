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
Scene計画
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
+---------------------------+
| Engine                    |
| Recovery / Stage / Loop   |
+-----+-----------------+---+
      |                 |
      | LLM operation   | code-only operation
      v                 v
+---------------+  +----------------+
| Provider      |  | Workspace      |
| Adapter       |  | Storage        |
+-------+-------+  +----------------+
        |
        v
+-----------------------+
| LLM Provider          |
+-----------------------+
```

Provider Adapterは、現在のoperationがLLMを必要とする場合だけ生成・使用する。Recoveryとcode-only operationはProviderから独立して実行する。

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
lock取得後の起動検証とRecovery
現在Stageと対象の決定
code-only operationとLLM operationの振り分け
Stage入力の構築
必要な場合だけOperation Serviceを呼び出す
形式・参照・意味契約の確認
Review／RevisionとRetryの制御
成果物の確定
実行状態の更新
停止条件の評価
```

Engineは、RecoveryをProvider初期化より先に完了させる。`initial_accept`、`scene_commit`、`publication`などのcode-only operationでは、Provider設定、Credential、Provider clientを要求しない。

保存形式の詳細はWorkspaceへ、LLM callの詳細はOperation Serviceへ委譲する。

---

## 19. Provider Adapterの責務

Provider Adapterは、外部LLM providerとの差異を吸収する。

主な責務:

```text
request作成
Credential取得
client生成
network timeoutとstream deadlineの適用
structured response
streamまたはnon-stream response
usage取得
Provider error分類
```

AdapterとProvider clientは、LLM operationのCall直前に遅延生成する。CLI起動時やRecovery開始時にmodel一覧取得などの接続確認を行わない。

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
run-state読み書き
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

ReviewはCandidateの問題点を返し、RevisionはCandidate全体の置換版を返す。

制御componentは次を管理する。

```text
Review回数
Revision回数
未解決Issue
Candidate version
停止条件
```

ReviewがCandidateを書き換えたり、予期しない内部例外をReview Issueへ変換したりしてはならない。形式・参照・State operationなどコードで決定できる検証は、LLM Reviewとは分離する。

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

Recovery Controllerは、Crash後のworkspaceを検証し、`WORKSPACE_AND_RECOVERY.md`で定めた前進型Recoveryを実行する。

RecoveryはProvider clientを生成せず、Provider callを行わない。分類、`pending_commit`の解決、再構築可能なstagingの再構築、人間対応への停止をコードだけで決定する。

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

## 28. Authority Registry

全データへ共通する単純な優先順位は設けない。情報種別ごとにAuthorityを一つだけ定める。

```text
現在の実行位置:
  run-state.json

物語の現在状態:
  current_generation_idが指すGeneration

採用済み計画:
  対応する確定済みPlan

確定済みScene本文と継続性結果:
  Scene directory

完結判定:
  採用済みCompletion Result

公開成果物:
  current_publication_idが指すPublication
```

Storyデータ内の詳細なAuthorityは`DATA_MODEL.md` §4および§39、保存上のAuthorityは`WORKSPACE_AND_RECOVERY.md`に従う。Audit、Context、Review、Candidate、staging成果物は補助情報であり、現在状態の正本ではない。

---

## 29. 実行状態

実行状態は、現在のrun位置を表す唯一の正本である。

代表的な情報:

```text
run_id
status
current_stage
current_target
current_generation_id
current_publication_id
active_candidate
active_scene_id
pending_commit
stop_reason
last_error
updated_at
```

field、enum、不変条件の唯一の正本は`design/WORKSPACE_AND_RECOVERY.md`とし、この文書では再定義しない。

---

## 30. Story成果物のAuthority

Generation、Scene、Candidate、Review、Revision、Evidence、Handoff、Completion、Publicationの意味、field、参照関係は`design/DATA_MODEL.md`を唯一の正本とする。

アーキテクチャ上の分類だけを次へ固定する。

| 分類 | 対象 | 性質 |
|---|---|---|
| 現在状態 | Generation | immutable。現在のStory Stateを表す |
| 確定済み本文 | Scene | immutable。Scene Card、本文、Continuity、Commitをまとめる |
| 未採用成果物 | Candidate、Review、Revision | 補助情報。Story Authorityではない |
| 根拠 | Evidence | 本文由来のState変更を人間が確認する情報 |
| 巻境界 | Handoff | 確定済み状態の要約。新しい事実を作らない |
| 完結評価 | Completion | `complete`、`complete_with_issues`、`incomplete` |
| 公開成果物 | Publication | immutable。採用済み成果物からコードで組み立てる |

Scene本文とContinuity結果を別々のAuthorityにせず、Scene Commitで一体として確定する。

---

# Part V: 実行モデル

## 31. 意味的Stage

Stageは、利用者、生成モデル、再開処理にとって意味のある工程だけにする。

Stage ID、順序、入力、出力、正常遷移の唯一の正本は`design/PIPELINE.md`とする。

アーキテクチャ上は、少なくとも次を意味的Stageとして扱う。

```text
入力
初期設計
シリーズ計画
巻計画
章計画
Scene計画
Scene Card
本文
継続性更新
Scene確定
巻Handoff
完結判定
Publication
```

Review／Revisionは対象Stage内のoperationである。Schema確認、ID割当、rename、State operation適用、実行状態更新は内部処理であり、独立Stageにしない。

---

## 32. Loop

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

## 33. Scene中の基準状態固定

一つのSceneについて、次が完了するまで同じ`basis_generation_id`を使う。

```text
Scene Plan
Scene Card
本文
継続性更新
Scene確定
```

途中で不一致を検出した場合は、対象Sceneの未採用Candidateを再利用せず、Scene Planからやり直す。

---

## 34. Retryの分類

次を別々に扱う。

```text
通信失敗
応答形式不正
意味的Revision
```

それぞれに独立した上限を持たせる。

無制限に成功まで繰り返してはならない。

---

## 35. 完結前確認

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

## 36. Publication確定

Publicationの保存、`pending_commit`、rename、最後の`run-state.json`更新は`design/WORKSPACE_AND_RECOVERY.md`を唯一の正本とする。

Publication Builderは採用済み成果物から決定的に内容を組み立て、独立Publication GateやLLM監査を作らない。

---

# Part VI: 秘密情報とContext

## 37. Writer秘密境界

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

## 38. Contextの位置付け

ContextはLLMへ渡す一時的な入力資料である。

原則として、hash名fileや恒久的な参照graphを作らない。

保存する場合はCandidateまたはAuditと同じ局所directoryへ置く。

---

## 39. Prompt injectionへの対応

Brief、本文、Review、外部入力内の命令風文字列を、System instructionやStage制御として扱ってはならない。

Story dataと実行命令を分離する。

---

## 40. Credentialの分離

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

## 41. Recovery境界

Recoveryの状態分類、起動検証、`pending_commit`、Scene／Generation／Publication確定、再構築条件、人間対応条件の唯一の正本は`design/WORKSPACE_AND_RECOVERY.md`とする。

アーキテクチャ上の不変条件は次のとおりである。

```text
Recoveryを通常Stageより先に実行する
Recovery中にProvider clientを生成しない
Recovery中にProvider callを行わない
完全なfinal成果物がある場合は後退せず前進する
不完全stagingは採用しない
決定的に再構築できない事実を推測しない
run-stateまたはAuthorityが曖昧なら人間対応にする
```

---

# Part VIII: 文書構造

## 42. 文書階層

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

## 43. 文書の正本

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

## 44. READMEの責務

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

## 45. docs/README.mdの責務

`docs/README.md`は文書一覧と推奨読書順だけを扱う。

独立した`DOCUMENT_STRUCTURE.md`は作らない。

---

## 46. SPECIFICATIONの責務

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

## 47. REQUIREMENTSの責務

`product/REQUIREMENTS.md`は、検証可能な要件IDと主な確認方法だけを扱う。

利用者向け説明や詳細設計を再掲しない。

---

## 48. IMPLEMENTATION_STATUSの責務

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

## 49. DATA_MODELの責務

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

## 50. WORKSPACE_AND_RECOVERYの責務

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

## 51. PIPELINEの責務

`design/PIPELINE.md`は、意味的Stage、Loop、Stage入力出力、Review／Revision、Completion、Publicationの流れを定義する。

JSON fieldや保存手順を再定義しない。

---

## 52. LLM_INTEGRATIONの責務

`design/LLM_INTEGRATION.md`は、Provider、Prompt、Context、秘密情報、structured response、Retry、timeout、budget、Auditを定義する。

StoryデータSchemaやRecovery規則を再定義しない。

---

## 53. ACCEPTANCEの責務

`testing/ACCEPTANCE.md`は、Release判断に必要な試験を定義する。

新しいpath、field、Stage、Recovery規則を追加してはならない。

---

## 54. Exampleとfixture

巨大なMarkdown exampleを正本として持たない。

実際のfixtureは次へ置く。

```text
tests/fixtures/
```

Fixtureの値は実ファイルを正本とする。

`tests/fixtures/README.md`は、目的と利用する試験だけを説明する。

---

# Part IX: 用語の正本

主要用語は、その意味を所有する文書で一度だけ定義する。

| 用語群 | 正本 |
|---|---|
| Run、Stage、Loop、遷移 | `design/PIPELINE.md` |
| Generation、Scene、Candidate、Review、Revision、Evidence、Handoff、Completion、Publication、Authority | `design/DATA_MODEL.md` |
| Immutable、atomic replacement、atomic rename、pending commit、Recovery | `design/WORKSPACE_AND_RECOVERY.md` |
| Operation、Context、Provider、Retry、timeout、Budget | `design/LLM_INTEGRATION.md` |

この文書では、上記用語のfieldや手順を重複定義しない。

---

# Part X: 禁止する過剰設計

## 55. Version 1で導入しないもの

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

## 56. Hash導入チェック

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

## 57. Authority追加チェック

新しいpointer、Manifest、Gate、indexを追加する場合は、次を明確にする。

```text
正本か補助情報か
既存の正本と矛盾した場合どちらを優先するか
Crash後にどう再構築するか
削除できない理由
```

複数の正本を作らない。

---

## 58. 新しい仕組みの追加チェック

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

## 59. Storycraft Version 1の原則

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
