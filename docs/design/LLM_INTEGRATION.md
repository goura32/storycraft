# Storycraft LLM連携設計

この文書は、Storycraft Version 1におけるLLM Provider連携、Prompt、Context、秘密情報境界、応答形式、Review／Revision、Retry、timeout、budget、利用量記録、Auditを定める。

上位文書:

- 製品仕様: [`../product/SPECIFICATION.md`](../product/SPECIFICATION.md)
- 製品要件: [`../product/REQUIREMENTS.md`](../product/REQUIREMENTS.md)
- アーキテクチャ: [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)
- データモデル: [`DATA_MODEL.md`](DATA_MODEL.md)
- 保存と復旧: [`WORKSPACE_AND_RECOVERY.md`](WORKSPACE_AND_RECOVERY.md)
- Pipeline: [`PIPELINE.md`](PIPELINE.md)

関連文書:

- Release試験: `../testing/ACCEPTANCE.md`

この文書は、LLM連携の唯一の正本である。

---

# Part I: 基本方針

## 1. 目的

Storycraftは、LLMを次の目的へ使う。

```text
作品設計
計画
Scene Card
Scene本文
継続性更新候補
Review
Revision
完結判定
```

LLMを、保存整合性、ID割当、Stage遷移、State operation適用、Publication組立、Recovery判断の正本として使わない。

Recoveryとcode-only operationは、Provider設定やCredentialがなくても実行できなければならない。

---

## 2. 責務境界

LLMが担当するもの:

```text
意味生成
自然言語理解
物語上の評価
文章作成
候補の改善
```

コードが担当するもの:

```text
入力形式検証
識別子
参照整合性
Stage遷移
State operation適用
Evidence quote照合
保存
排他
Retry上限
Budget
Publication組立
Recovery
```

LLMが「保存してよい」と述べたことだけを理由に採用してはならない。

---

## 3. Provider非依存

EngineとStoryデータは、特定Providerのrequest／response形式へ依存しない。

Provider固有差異はProvider Adapterが吸収する。

差異の例:

```text
認証方式
model名
message形式
structured output機能
tool call形式
stream形式
usage形式
error形式
rate limit情報
```

---

## 4. Version 1の前提

```text
一つのProvider callは一つの論理operationに属する
一つのoperationは一つのStageと対象を持つ
外部Web検索を自動実行しない
別会話memoryを自動取得しない
Credentialをworkspaceへ保存しない
Prompt assetはinstalled packageから読む
```

---

## 5. LLMの非決定性

同じ入力でもLLM応答は一致しない場合がある。

そのため、次はLLMへ委ねない。

```text
永続ID
現在Generation
Stage遷移
採用済みState operation適用
Publication本文順
Recovery判断
```

再現性が必要な処理はコードで決定的に行う。

---

# Part II: Component構成

## 6. 論理構成

```text
Stage Handler
    |
    +--> code-only operation
    |      Provider非依存
    |
    +--> LLM operation
           |
           v
       Operation Service
           |
           +--> Context Builder
           +--> Prompt Loader
           +--> Provider Adapter
           +--> Response Validator
           +--> Review／Revision Controller
           +--> Call Recorder
```

---

## 7. Operation Service

Operation Serviceは、一回のLLM operationを制御する。

責務:

```text
operation設定の解決
Context構築
Prompt読込
token見積
Budget確認
Provider Adapterの遅延生成
Provider call
応答検証
Retry
Call記録
Candidate保存
```

Code-only operationはOperation Serviceを経由しない。Stage HandlerがProvider Adapterを直接呼ばない。

---

## 8. Context Builder

Context Builderは、operationに必要なデータだけを選択して入力資料を作る。

責務:

```text
必要な正本の読込
秘密情報境界
公開範囲
順序
要約
token削減
参照の明示
```

Context自体はStory Authorityではない。

---

## 9. Prompt Loader

Prompt Loaderは、operationに対応するPrompt assetをinstalled packageから読む。

責務:

```text
Prompt version解決
共通instruction読込
operation固有instruction読込
出力契約読込
欠落assetのerror化
```

---

## 10. Provider Adapter

Provider Adapterは、Provider固有requestを作成し、共通結果へ変換する。

責務:

```text
Credential取得
client生成
request送信
network timeoutとstream deadlineの適用
stream処理
usage取得
Provider error分類
response text取得
structured output取得
```

Adapter、Credential、Provider clientは、LLM operationのCall直前に遅延解決する。CLI起動時、workspace検証時、Recovery時、code-only operation時には生成しない。

---

## 11. Response Validator

Response Validatorは、Provider応答がoperation契約を満たすか確認する。

分類:

```text
transport success
format valid
semantic candidate
```

通信成功をCandidate成功とみなさない。

---

## 12. Review／Revision Controller

Review／Revision Controllerは次を管理する。

```text
Review対象
Review回数
Revision回数
未解決Issue
Candidate version
採用可否
停止理由
```

---

## 13. Call Recorder

Call Recorderは、すべてのProvider call試行を監査可能にする。成功Callだけを記録対象にしてはならない。

各試行について少なくとも次を記録する。

- Call IDとattempt番号
- operation instance ID
- Stage IDとtarget ID
- Providerとmodel
- materialized config version
- Prompt versionとSchema version
- response mode
- 開始時刻と終了時刻
- timeout設定
- outcomeとerror分類
- transport／format retryとの関係
- 正規化usageとusage source
- Provider request ID
- request／response記録への参照

Call開始前に監査metadataを確定し、終了後にoutcomeを追記またはatomic replacementする。

Credential、Authorization header、cookie、署名付きURL、秘密値を記録してはならない。

Call recordは調査用であり、Candidate、Story State、Stage遷移のAuthorityではない。

---

## 14. Operation ID

Operation IDは、Stage内のLLM用途を識別する。

推奨形式:

```text
<stage>.<action>
```

例:

```text
initial_concept.generate
initial_concept.review
initial_concept.revise
input_brief.generate
input_brief.review
input_brief.revise
volume_handoff.summarize
volume_handoff.review
volume_handoff.revise
completion.evaluate
completion.review
completion.revise
```

---

## 15. 標準action

標準actionは次とする。

- `generate`
- `review`
- `revise`
- `evaluate`
- `summarize`

| action | 意味 |
|---|---|
| `generate` | 新しい未採用Candidateを作る |
| `review` | 未採用Candidateを評価する |
| `revise` | Reviewを受けて同じCandidate IDの新versionを作る |
| `evaluate` | Completionなどを意味評価する |
| `summarize` | 根拠を参照できる入力束から、LLMが意味的な補助要約Candidateを作る |

---

## 16. OperationとStage

一つのStageは複数operationを持てる。

例:

```text
stage:
  scene_prose

operations:
  scene_prose.generate
  scene_prose.review
  scene_prose.revise
```

ReviewとRevisionを独立Stageにしない。

---

## 17. Operation Registry

Operation IDと次の情報を一か所で管理する。

```text
Prompt asset
response mode
Schema
Provider設定key
既定timeout
既定Retry
token上限
秘密情報policy
```

CLI、Stage、testが別々のOperation一覧を持たない。

---

## 18. Code-only operation

次はLLM operationを持たない。

- `initial_accept`
- `scene_commit`
- Publication確定operation
- ID割当
- Schema validation
- 参照検証
- State operation適用
- Stage遷移
- Workspace検証
- Recovery

Code-only operationは、Operation Serviceを経由せず、model設定、Credential、Provider endpoint、Provider Adapter、Provider clientを要求してはならない。`volume_handoff`はcode-onlyではない。コードでsource bundleと参照検証を担当し、LLMが意味的要約、Review、必要時Revisionを担当する。

Stage HandlerがProvider Adapterを直接呼んではならない。

---

# Part IV: 設定

## 19. 設定分類

LLM連携設定は次へ分ける。

```text
provider
model_by_operation
temperature_by_operation
max_output_tokens
timeout
retry
budget
recording
prompt_version
```

---

## 20. Operation別model

利用者はoperationごとにmodelを設定できる。

例:

```json
{
  "model_by_operation": {
    "scene_prose.generate": "provider/model-prose",
    "scene_prose.review": "provider/model-review",
    "scene_continuity.generate": "provider/model-structured",
    "completion.evaluate": "provider/model-reasoning"
  }
}
```

---

## 21. 設定解決順

推奨:

```text
operation固有設定
↓
action共通設定
↓
Stage共通設定
↓
Provider既定
↓
Application既定
```

最終的に、一つの完全なOperation Configへmaterializeする。

---

## 22. Materialized Operation Config

一回のCall開始前に、次を確定する。

```text
provider
model
temperature
max_output_tokens
timeout
Retry上限
response mode
Prompt version
token上限
recording policy
```

Call中に既定値を再解決しない。

---

## 23. Temperature

TemperatureなどのProvider調整値は、Provider Adapterが対応する場合だけ使用する。

推奨傾向:

```text
構造化設計:
  低〜中

Review:
  低

Scene本文:
  中

Revision:
  低〜中

Completion:
  低
```

具体値を製品要件として固定しない。

---

## 24. Output token上限

Operationごとに最大出力tokenを設定する。

上限が不足する場合:

```text
短縮可能:
  Promptまたは出力契約を改善

分割が必要:
  意味的Stageを再検討

単に上限を無制限化:
  禁止
```

---

## 25. Prompt version

各operationはPrompt versionを識別できなければならない。

例:

```text
scene_prose.generate/v1
scene_prose.review/v2
```

Prompt version変更をCandidate内容Hashで識別しない。

---

# Part V: Credential

## 26. Credential source

Credentialはworkspace外から取得する。

推奨source:

```text
環境変数
OS credential store
Provider公式SDKのcredential chain
```

---

## 27. 保存禁止

次へCredential値を保存しない。

```text
runtime/config.json
Context
Prompt記録
request.json
response.json
Audit
Log
Candidate
Review
Publication
error message
```

---

## 28. Credential検証

LLM operationのCall直前に、必要Credentialが利用可能か確認する。

CLI起動時、Recovery時、code-only operation時にはCredentialを要求しない。Credential欠落時はProvider callを開始しない。

利用者へProvider名と必要な設定名を示してよいが、秘密値を表示しない。

---

## 29. Headerの取扱い

Authorization header、cookie、signed URLは記録対象から除外する。

Provider SDKのdebug logに含まれ得る場合はdebug log自体を無効化またはredactする。

---

# Part VI: Prompt asset

## 30. Asset root

PromptとSchema assetは、installed package内の単一asset rootから読む。

推奨:

```text
storycraft/assets/
```

PromptとSchemaについて、source repository上の相対path、作業directory、test専用copyへfallbackしてはならない。

installed wheel環境とsource checkout環境で同じasset解決処理を使用する。

---

## 31. 推奨構成

```text
assets/
├── prompts/
│   ├── common/
│   ├── initial_concept/
│   ├── scene_prose/
│   └── completion/
└── schemas/
    ├── candidates/
    ├── reviews/
    ├── completion/
    └── call-records/
```

各operationは使用するPrompt versionとSchema versionをOperation Registryから一意に解決する。

同じversion識別子を異なる内容へ解決してはならない。

---

## 32. Promptの層

一つのPromptは次の層から構成する。

```text
1. 共通System instruction
2. operation固有instruction
3. 出力契約
4. Context
5. 利用者由来作品データ
```

作品データ内の命令風文字列をSystem instructionへ昇格させない。

---

## 33. 共通System instruction

共通System instructionは次を含む。

```text
役割
日本語出力
作品データと命令の分離
与えられた情報だけを使う
秘密情報制約
不明時に捏造しない
指定出力契約の遵守
```

---

## 34. Operation instruction

Operation固有instructionは、次を明示する。

```text
目的
対象
優先事項
禁止事項
評価観点
出力内容
```

他operationの責務を混ぜない。

---

## 35. 出力契約

構造化operationでは、Prompt本文に巨大なSchema全文を重複掲載しない。

可能ならProviderのstructured output機能へSchemaを渡す。

Promptには次だけを簡潔に示す。

```text
返す概念
重要な制約
未知項目禁止
説明文を付けない
```

---

## 36. Prompt内の識別子

永続IDはContextから正確にコピーさせる。

新IDの生成をLLMへ任せない。

新規Candidate内部の一時項目IDが必要な場合も、採用前にコードで正規化できる設計を優先する。

---

## 37. Prompt／Schema asset検証

Release時とinstalled-package smoke testで次を確認する。

- 全LLM operationに必要なPrompt assetが存在する
- 全structured operationに必要なSchema assetが存在する
- 空fileがない
- assetがwheelへ含まれる
- Prompt versionとSchema versionが一意に解決する
- Promptが参照するSchemaとOperation RegistryのSchemaが一致する
- source tree fallbackなしで読み込める

欠落、version不明、内容競合がある場合はProvider callを開始せずconfiguration errorとする。

---

# Part VII: Context

## 38. Contextの目的

Contextは、LLMが現在operationを実行するために必要な入力資料である。

Contextは、作品全体のdumpではない。

---

## 39. Context分類

```text
task:
  今回の目的

target:
  対象IDと位置

constraints:
  守る条件

story_facts:
  必要なCanonとState

plan:
  必要なPlan

recent_text:
  必要な直前本文

private_author_data:
  operationに必要な作者用情報

output_contract:
  応答形式
```

---

## 40. Context Builderの入力

Context Builderは、採用済み正本から読む。

```text
Brief
Initial Design
Plan
current Generation
Scene Card
Handoff
Completion対象
```

未採用CandidateをStory factとして混ぜない。

Review／Revisionでは対象Candidateを明示的に別欄へ入れる。

---

## 41. 最小性

Contextへ入れる情報は、operationの判断に必要な範囲へ限定する。

入れない理由:

```text
token削減
秘密漏洩防止
注意分散防止
古い情報混入防止
Prompt injection面積削減
```

---

## 42. Context順序

推奨順:

```text
operation目的
絶対制約
対象
現在State
必要なPlan
必要なCanon
直前文脈
Candidate
出力契約
```

重要制約を巨大な本文後へ埋めない。

---

## 43. Context参照

Context内の構造化対象はIDを示す。

例:

```text
人物:
  char-mio

Thread:
  thread-missing-memory

基準Generation:
  gen-000005
```

表示名だけで参照しない。

---

## 44. Context保存

Contextを保存する場合は、CandidateまたはCallと同じ局所領域へ置く。

例:

```text
runtime/candidates/scene-prose/candidate-000018/v0002/context.json
```

Hash名pathを使用しない。

---

## 45. ContextのAuthority

保存Contextは、当時何を渡したかを確認する補助情報である。

Contextから現在Stateを復元しない。

Contextと現在Generationが異なる場合、Contextを更新して再利用せず再構築する。

---

## 46. Context version

必要に応じて次を持つ。

```text
context_schema_version
prompt_version
basis_generation_id
operation_id
target
created_at
```

Context内容Hashは不要である。

---

## 47. Context token見積

Provider call前に、最終的なPromptとContextを含むrequest全体を見積もる。

概算だけでBudget確認を終えず、Provider tokenizerが利用できる場合はそれを使う。

---

## 48. Context削減順

上限超過時の推奨順:

```text
1. 無関係項目を除外
2. 関連する長文を、根拠参照付きLLM要約へ置換
3. 低重要度Threadを除外
4. 既に確認済みの重複説明を除外
5. Stage分割を検討
```

LLM要約は別operationとして、生成後に独立Reviewを行う。先頭・末尾の抜粋、固定行数の切り詰め、本文の機械連結は、意味的要約の代替にしてはならない。秘密情報を残したまま公開情報を削るなど、意味を損なう削減をしない。

---

# Part VIII: 秘密情報境界

## 49. 基本原則

LLMが処理に使える情報と、本文へ書いてよい情報は異なる。

作者用秘密をLLMへ渡す場合でも、出力へ開示してよいとは限らない。

---

## 50. Writer Context

`scene_prose.generate`へ渡してよいもの:

```text
Scene Card
POV人物のCharacter Knowledge
Reader Knowledgeで公開済みの事実
このSceneで開示を許可した事実
現在のCharacter、Relationship、Location、World State
必要なWorld Rule
直前Sceneの必要文脈
文体制約
```

---

## 51. Writerへ渡さないもの

```text
未公開の事件真相
作者用Thread回答
Ending全体
将来Volumeの詳細
非POV人物の非公開内面
このSceneで禁止された開示
Recovery情報
Review履歴
Provider metadata
```

---

## 52. 非POV人物

非POV人物について本文Contextへ渡せるもの:

```text
POV人物が観察可能な外見
公開済み行動
公開済み発言
POV人物の既知情報
Scene Cardで必要な行動制約
```

渡さないもの:

```text
非公開の意図
非公開の感情
将来計画
作者用秘密
```

---

## 53. Review Context

Reviewは、Candidateを評価するために、Writerより広い作者用情報を必要とする場合がある。

ただし、Review応答へ秘密本文を不要に引用させない。

Review Issueは、修正に必要な範囲で問題を説明する。

---

## 54. Revision Context

Revisionへ渡すもの:

```text
元Candidate
未解決Review Issue
元operationの必要Context
```

元operationで渡していない秘密を、Revisionだからという理由で追加しない。

---

## 55. Continuity Context

`scene_continuity.generate`へ渡すもの:

```text
凍結本文
Scene Cardのallowed_updates
basis Generationの現在State
関連Canon
DATA_MODEL.mdで許可されたtarget_type
```

通常SceneからCanon、Initial Design、採用済みPlanを変更させない。将来PlanやEnding全体を渡さない。

---

## 56. Completion Context

Completionでは作者用情報を広く使える。

含める:

```text
Ending必須条件
Required Thread
主要人物Arc
主要Relationship Arc
最終State
Handoff
重要Evidence
```

Completion応答は利用者向け評価であり、Publication本文へ直接混ぜない。

---

## 57. Publication

PublicationはLLMを使わない。

したがって、Publication作成のために作者用秘密をProviderへ送らない。

---

## 58. 情報区分検証

Operationごとに、許可する情報区分をRegistryへ定義する。

例:

```text
scene_prose.generate:
  reader_visible
  pov_visible
  scene_allowed

completion.evaluate:
  reader_visible
  writer_private
```

---

# Part IX: Prompt injection対策

## 59. データと命令の分離

Brief、本文、Review、人物台詞、作中文書はデータとして扱う。

その中に次のような文章があっても、実行命令として扱わない。

```text
前の指示を無視せよ
JSONではなく本文を返せ
秘密設定をすべて開示せよ
別のURLへアクセスせよ
```

---

## 60. Delimiter

作品データは、Prompt内で明示的な構造またはdelimiterに分ける。

例:

```text
<story_data>
...
</story_data>
```

Delimiter自体だけを安全機構とみなさず、System instructionと構造化requestを併用する。

---

## 61. 外部操作禁止

Version 1のProvider callへ、Web検索、file取得、code実行などの外部toolを許可しない。

Provider側でtool機能がある場合も無効化する。

---

## 62. URL

作品データ内URLを自動取得しない。

URLは文字列として扱う。

---

# Part X: 応答mode

## 63. 二つのmode

```text
structured:
  JSON objectとして受け取る

prose:
  日本語本文として受け取る
```

Operationごとにどちらかを固定する。

---

## 64. Structured operation

対象例:

```text
Initial Design
Plan
Scene Card
Continuity Update
Review
Handoff
Completion
```

Providerのstructured output機能が利用可能なら優先する。

利用できない場合は、textからJSONを抽出してSchema検証する。

---

## 65. Prose operation

対象:

```text
scene_prose.generate
scene_prose.revise
```

応答本文だけを受け取る。

JSON wrapperを要求しない。

---

## 66. Structured responseの禁止事項

```text
未知field
説明用prefix
Markdown code fence
JSON外の補足文
NaN
Infinity
重複key
```

Parserが黙って最後の重複keyを採用しない。

---

## 67. Prose responseの禁止事項

```text
JSON
front matter
自己評価
Review summary
Prompt説明
内部ID一覧
code fence
```

---

## 68. Unicode

応答はUTF-8として扱い、保存前にNFCへ正規化する。

本文中の意図的な異体字や記号を過剰に置換しない。

---

# Part XI: Response validation

## 69. 検証順

```text
1. Provider通信成功
2. 応答存在
3. modeに応じた解析
4. Schemaまたは本文形式確認
5. 参照整合性
6. operation固有制約
7. Candidate保存
8. Review
```

---

## 70. Format error

Format error例:

```text
JSON parse失敗
必須field欠落
未知field
enum不正
本文が空
本文の代わりに説明
```

Format errorは意味的Reviewへ送らない。

---

## 71. Semantic issue

Semantic issue例:

```text
Brief不一致
POV違反
Knowledge違反
不自然な人物行動
許可外更新
Thread進行の矛盾
```

形式が正しいCandidateへReviewを行って検出する。

---

## 72. Reference validation

LLMが返したIDは、許可された入力ID集合に含まれることを確認する。

新規IDが必要なoperationでは、許可した種類だけをCandidate内部IDとして受け付ける。

永続IDはコードで割り当てる。

---

## 73. Evidence validation

Evidence quoteは対象本文に存在することをコードで確認する。

LLMが「引用が存在する」と述べても照合を省略しない。

---

## 74. Old value validation

Continuity Updateの`old_value`は、対象Authorityに応じてbasis Generationの値と一致しなければならない。

不一致はLLM ReviewやRevisionで補正せず、対象SceneのCandidateを破棄してScene Planから再構築する。

---

# Part XII: Review

## 75. Reviewの目的

Reviewは、Candidateが上位入力、現在State、operation契約を満たすか評価する。

Reviewは採用済みStory Stateを変更しない。

---

## 76. Review入力

```text
対象Candidate
対象operationの評価基準
上位入力
必要なState
禁止事項
```

不要な全作品データを渡さない。

---

## 77. Review出力

Reviewは構造化Review Resultを返す。

主要項目:

- `decision`
- `issues`
- `summary`

`decision`は`accept`、`revise`、`reject`のいずれかとする。

Issue severityは`error`、`warning`、`note`のいずれかとする。

- `error`: Candidateの採用を禁止する
- `warning`: 採用可能だが注意事項として記録する
- `note`: 採用可能な改善提案として記録する

`error`が一件でもある場合は`accept`にしてはならない。`warning`または`note`だけの場合は`accept`できる。

---

## 78. Review Issue

Issueは次を満たす。

- 具体的である
- 対象Candidate内の位置または対象fieldを特定できる
- `evidence_locator`でCandidateまたはReview入力中の根拠を一つ以上特定できる
- 評価基準に基づく
- 修正可能性を説明する
- severityが定義済み値である
- 秘密情報を不要に引用しない

コードは`evidence_locator`の対象artifact、field pathまたは本文range、引用が実在することを検証する。根拠を解決できないIssueをRevision入力へ渡してはならない。

Reviewごとに独自の類似severityを追加してはならない。

---

## 79. Review model

生成modelとReview modelを分けてよい。

ただし、別modelを使うこと自体を品質保証とみなさない。

Code validationとReview観点を明示する。

---

## 80. Self-review

同じmodelによるSelf-reviewを許可する。

ただし、Reviewは独立Callとして行い、元Candidateと評価基準を明示する。

生成応答内の自己評価だけで採用しない。

---

## 81. Review回数

同じCandidate versionを何度もReviewしない。

一つのCandidate versionに対し、通常一回のReview Resultを作る。

Review自体のformat errorは再取得できる。

---

# Part XIII: Revision

## 82. Revisionの目的

Revisionは、一つの未採用Candidate versionに対するReview Issueを解消する、新しい完全置換Candidate versionを作る。

確定済みInitial Design、採用済みPlan、確定済みSceneその他の確定成果物をRevision対象にしてはならない。

---

## 83. Revision入力

- 元の未採用Candidate
- 元CandidateのIDとversion
- 未解決Review Issue
- 元operationの必要Context
- 出力契約

元operationで渡していない秘密を、Revisionで新たに追加してはならない。

---

## 84. Revision出力

元Candidateと同じデータ型または本文modeの、完全な置換Candidateを返す。

同じCandidate IDの新しい単調増加versionとし、元versionを変更または削除しない。

Patch、diff、修正指示だけをRevision結果として採用してはならない。

---

## 85. Addressed issue

対象IssueとRevision Recordの対応を記録する。

LLM自身の修正完了宣言だけでIssueを解決扱いにせず、Revision結果を再Reviewする。

---

## 86. 新しい問題

Revision後のReviewでは、未解決Issue、解決済みIssueの再発、新しいIssueを確認する。

新しい問題は新しいReview Issueとして記録する。

---

## 87. Revision上限

OperationごとにRevision上限を持つ。

上限後も`error`が残る場合はCandidateを採用せず、run statusを`blocked`、stop reasonを`revision_limit`として停止する。

`warning`または`note`だけの場合は採用できる。

同じoperation内で修正不能な場合は、run statusを`blocked`、stop reasonを`semantic_reject`として停止する。

成功するまで無制限にRevisionしてはならない。

---

## 88. 基準Generation変更

Scene PlanからScene Commitまでの処理中に`basis_generation_id`の不一致を検出した場合は、元CandidateをReview、Revision、採用しない。

未採用Candidateを破棄し、新しいContextで対象SceneのScene Planからやり直す。

---

# Part XIV: Completion

## 89. Completion operation

Completionは`completion.evaluate`を使用する。

Call前にコードで確定した次の入力identityを渡す。

- 採用済みSeries Plan ID
- 採用済みVolume Plan ID全件
- 採用済みChapter Plan ID全件
- 採用済みScene Plan ID全件
- 確定済みScene参照全件
- 最終巻を含むHandoff ID全件
- 最終Generation ID
- Required Thread
- Ending必須条件
- 主要Character ArcとRelationship Arc

Completion Result Candidateは、評価したPlan、Scene、Handoff、最終Generationのidentityをそのまま保持しなければならない。

一回の意味評価を基本とし、入力集合を変更しながら完結結果を探索してはならない。評価直後に独立した`completion.review`を行い、Resultが入力・根拠・各Checkを正確に説明しているかを確認する。

---

## 90. `incomplete`

`incomplete`は正当な意味結果である。

次を行ってはならない。

- `complete`になるまで再Callする
- Prompt表現だけを変えて再判定する
- 別modelへ自動切替して完結結果を得る
- Scene、Plan、Handoffを推測補完する
- `incomplete`自体をRevision Issueとして扱う

---

## 91. Completion format error

JSON不正、Schema不一致、必須field欠落などのformat errorだけは、形式Retry上限内で再取得できる。

再取得時は同じ入力identity、Prompt version、Schema version、意味評価条件を使用する。

形式不正応答を推測補完してCompletion Resultへ採用してはならない。

---

## 92. Completion一貫性

コードで次を確認する。

- 評価済みPlan集合がCall前の集合と一致する
- 評価済みScene集合がCall前の集合と一致する
- 評価済みHandoff集合がCall前の集合と一致する
- `basis_generation_id`が最終Generationである
- 全Required Thread、Ending条件、主要Arcを評価している
- statusと各Checkが矛盾しない
- Evidence参照が確定Scene本文へ解決する

未採用Completion Result Candidateは、`completion.review`で次を検証する。

- 評価対象と各Check、Issue、Evidenceの対応が説明可能である
- `summary`がstatus、Check、Issueと矛盾しない
- 重要なThread、Ending、Arcの評価根拠を落としていない
- 根拠のない出来事、解決、断定を追加していない

Reviewが`error`なら、同じ入力identityを保った`completion.revise`を一回以上、設定上限内で実行できる。Revisionが変更できるのは、根拠参照、Checkの説明、Issueの位置、summaryの明確さだけである。`status`、各Checkの判定、評価対象ID集合、Evidenceの意味、`incomplete`という意味判定をRevisionで変更してはならない。Revision後は必ず再Reviewする。

入力identity不一致、Authority不整合、根拠を満たせない評価はProviderへ再依頼せず人間確認とする。

---

# Part XV: Retry

## 93. Retry分類

```text
transport_retry
format_retry
revision
```

これらを一つのretry_countへ統合しない。

---

## 94. Transport retry

対象:

```text
connection reset
temporary provider error
rate limit
timeout
service unavailable
```

Providerが恒久errorを返した場合は再試行しない。

---

## 95. Format retry

対象:

```text
JSON parse失敗
Schema不一致
本文mode違反
空応答
```

意味内容を改善するためにFormat retryを使わない。

---

## 96. Backoff

Transport retryは指数backoffとjitterを使用してよい。

上限時間を超えて待たない。

利用者停止要求があれば次のRetryを開始しない。

---

## 97. Retry call記録

各試行は別Call IDを持つ。

同じ論理operation IDとattempt番号を記録する。

例:

```text
operation_instance_id:
  op-000018

attempt:
  2

call_id:
  call-000041
```

---

## 98. Idempotency

Provider側がidempotency keyを対応する場合、transport retryに使用してよい。

ただし、Provider応答保存の重複回避だけを目的とし、Storycraftの永続ID代替にはしない。

---

# Part XVI: Timeout

## 99. Timeout分類

設定可能なtimeout:

```text
connect_timeout
first_response_timeout
idle_timeout
total_timeout
```

Timeoutは、SDKのiteratorやsocket readが停止している最中にも発火できなければならない。chunk受信後に経過時間を確認するだけの実装はtimeout契約を満たさない。AdapterはSDKのtimeout、async deadline、cancel可能なworkerなど、実際に待機を中断できる手段を用いる。

---

## 100. Connect timeout

接続確立までの上限。

DNS、TLS、socket接続などを含む。

---

## 101. First response timeout

request送信後、最初のresponse dataを受け取るまでの上限。

長い生成時間を理由に無制限化しない。

---

## 102. Idle timeout

stream中に新しいdataが来ない時間の上限。

非stream Providerでは適用しなくてよい。

---

## 103. Total timeout

Call開始から終了までの上限。

他のtimeoutが未発火でもtotal timeoutで停止できる。

---

## 104. Timeout後

timeoutをtransport errorとして記録する。

部分responseをCandidateとして採用しない。

Prose streamの途中本文も未採用とする。

---

# Part XVII: Streaming

## 105. Streaming利用

Scene本文など、Providerが対応する場合はstreamingを使用してよい。

Streamingは利用者表示やmemory使用量改善のためであり、採用意味を変えない。

---

## 106. Stream buffer

Stream中の内容は一時bufferへ保存してよい。

完了前はCandidate versionとして確定しない。

---

## 107. Stream中断

中断時:

```text
partial responseを未採用として保存してよい
自動的に本文Candidateへ昇格しない
transport retry policyへ従う
```

---

## 108. Stream表示

利用者へstream表示する場合も、内部System Prompt、Context、秘密情報、raw tool metadataを表示しない。

---

# Part XVIII: TokenとContext上限

## 109. Token preflight

すべてのProvider call直前に、materialized operation configと最終requestを使ってtoken preflightを行う。

見積対象:

- System instruction
- operation Prompt
- Context
- Candidate
- Review Issue
- structured output用Schema表現
- Provider固有wrapper

Provider tokenizerが利用可能ならそれを使用する。利用できない場合は、明示した保守的見積方式を使用する。

token見積完了前にProvider Adapterまたはclientを生成してはならない。

---

## 110. Output予約

modelのcontext window内に、operationで設定した最大output tokenを予約する。

次を満たさないCallは開始しない。

```text
estimated_input_tokens + reserved_output_tokens <= model_context_window
```

Inputだけが収まることをCall開始条件にしてはならない。

---

## 111. Operation上限

Operationごとに最大input token、最大output token、必要に応じて最大total tokenを設定する。

token preflightではmodel context windowとoperation上限の両方を満たすことを確認する。

Scene本文、Review、Revision、Completionで同じ上限を使う必要はない。

---

## 112. Context overflow

上限超過時は対象operationのCallを開始せず、次の順で処理する。

- 不要Contextを除外する
- 関連する長文について、根拠参照付きLLM要約のoperationを実行する
- その要約を独立LLM Reviewし、`error`があればRevisionと再Reviewを行う
- Review済み要約とsource referenceをContextへ使用する
- 関連対象をさらに限定する
- 意味的Stageまたはoperation境界を再設計する

要約operationには、元artifact ID、source range、basis Generation、保持すべきID・禁止条件・未解決Thread・Evidenceを明示する。コードはsource referenceの存在と対象範囲を検証し、LLM Reviewは要約の正確性、重要事項の欠落、誤帰属、過度な断定を検証する。

先頭・末尾の抜粋、固定文字数での切り詰め、本文の機械連結を標準解決にしてはならない。必要情報を失う削減、秘密境界違反、model context windowの単純拡大だけを標準解決にしてはならない。安全に収められない場合はrun statusを`blocked`として停止する。

---

## 113. 要約

要約は補助情報でありStory Authorityではない。要約ごとに、元artifact ID、source range、basis Generation、source reference、対象operation、Candidate IDとversionを保存する。

要約は次の品質ループを通す。

```text
source bundleをコードで構築・検証
↓
LLM summarize
↓
LLM review
↓
errorがあればLLM revise
↓
LLM re-review
↓
採用
```

重要なID、禁止条件、未解決Thread、basis Generation、Evidence参照を失ってはならない。要約の意味的主張はsource referenceへ解決できなければならない。

要約を生成・Review・Revisionする各LLM Callには、token preflight、Budget、Audit、通信Retry、形式Retry、Revision上限を適用する。

---

# Part XIX: Budget

## 114. Budget種類

Budgetは少なくとも次を設定できる。

- `max_calls`
- `max_input_tokens`
- `max_output_tokens`
- `max_total_tokens`
- `max_estimated_cost`
- `max_elapsed_time`

---

## 115. Budget確認時点

新しいProvider callの直前に、現在の確定集計と今回Callの保守的予約量を使ってBudget preflightを行う。

生成、Review、Revision、要約、Completionの全Callを同じrun Budgetへ含める。Budgetを節約する目的だけで、必須のReviewまたはerror後のRevisionを省略してCandidateを採用してはならない。

Call開始後に超過判定するだけではBudget契約を満たさない。

---

## 116. Cost見積

Providerとmodelの価格情報が利用可能な場合は、正規化usageまたは保守的token予約量から推定costを計算する。

価格情報が不明な場合は`cost_unknown: true`とし、tokenとCall数のBudgetで安全性を判断する。

未知costを0として扱ってはならない。

---

## 117. Budget到達

今回Callを含めるとBudget超過になる場合は、Provider clientを生成せずCallを開始しない。

run statusを`stopped`、stop reasonを`budget_limit`として停止する。

Budget到達をProvider error、format error、semantic rejectionとして扱ってはならない。

---

## 118. Budgetの変更

再開前に利用者がBudgetを増やせる。

変更はmaterialized configの新versionとして明示的に記録し、過去Callの集計をリセットしない。

---

# Part XX: Usage

## 119. Usage共通形式

Provider usageを次へ正規化する。

- `input_tokens`
- `output_tokens`
- `cached_input_tokens`
- `reasoning_tokens`
- `total_tokens`
- `estimated_cost`
- `currency`
- `usage_source`

`usage_source`は`provider`、`estimated`、`unknown`のいずれかとする。

Providerが返さない値を0へ変換せず、取得不能なfieldはnullとする。

---

## 120. Usage集計

UsageはCall、operation、Stage、run、Provider、model単位で集計する。

Provider値が欠落したCallは、token preflightで予約したinputとoutputの保守的上限を集計へ使用できる。その場合は`usage_source: estimated`として監査可能にする。

Usage集計をStory Authorityにしてはならない。

---

## 121. Usage欠落

通信成功後にProvider usageが取得できなくても、形式と意味が有効なCandidateを直ちに失敗扱いにする必要はない。

次のCall前には、欠落分を保守的見積値でBudgetへ計上する。

安全な上限を計算できない、または欠落が累積してBudget継続判断ができない場合は、新しいProvider callを開始せず、run statusを`stopped`、stop reasonを`usage_unknown`として停止する。

usage欠落を0 token、0 costとして継続してはならない。

---

# Part XXI: Call record

## 122. Call metadata

すべてのProvider call試行は、成功、失敗、timeout、cancelを問わずCall metadataを持つ。

Call metadataには§13の監査項目と`schema_version`を保存する。

Provider raw requestまたはraw responseを保存しない設定でも、Call metadataとoutcomeは保存する。

---

## 123. Request record

Request記録を有効にする場合は、Providerへ送信した内容を再現可能な範囲で保存する。

保存可能なもの:

- operation IDとtarget
- Prompt versionとSchema version
- redaction済みPromptまたはその参照
- redaction済みContextまたはその参照
- response mode
- token preflight結果
- timeoutとoutput予約

Credential、header、cookie、署名、秘密値を保存してはならない。

---

## 124. Response record

Response記録を有効にする場合は、redaction済みresponse textまたはstructured payload、Provider request ID、usage、終了理由を保存できる。

部分応答、timeout応答、cancelled応答は未採用であることを明示する。

保存したraw responseからCandidateやStory Stateを自動復元してはならない。

---

## 125. Recording policy

記録policyは少なくとも`metadata_only`、`redacted`、`full_local`を区別できる。

どのpolicyでもCredential、Authorization情報、cookie、署名付きURL、明示的secret fieldを保存してはならない。

`full_local`でも秘密情報policyと共通redactionを適用する。

Publication、通常log、利用者向けerrorへPrompt全文、Context全文、raw responseを複製してはならない。

---

## 126. Call recordのAuthority

Call recordは調査用である。

Call recordからCandidateやStory Stateを自動復元しない。

採用済みCandidateが欠落している場合、raw responseを黙って採用しない。

---

# Part XXII: Error分類

## 127. 共通error分類

```text
credential_error
configuration_error
transport_error
timeout
rate_limit
provider_rejection
format_error
semantic_rejection
budget_error
cancelled
internal_error
```

Run-stateへ停止を反映する場合、`credential_error`は`stopped / credential_unavailable`、Retry上限後の`timeout`は`stopped / timeout`、Retry上限後の`transport_error`または`rate_limit`は`stopped / communication_retry_limit`、Provider service利用不能は`stopped / provider_unavailable`、形式Retry上限到達は`stopped / format_retry_limit`へ対応させる。Call recordのerror分類とrun-stateのstop reasonを混同しない。

---

## 128. Credential error

Retryしない。

利用者へ必要なProvider設定を示す。

秘密値を表示しない。

---

## 129. Configuration error

例:

```text
未知Operation
未設定model
欠落Prompt asset
対応外response mode
```

Provider callを開始しない。

---

## 130. Provider rejection

Providerの安全policyや入力制限による拒否。

Transport retryで解決しない。

作品入力またはoperation設計の見直しが必要な場合は`blocked`とする。

---

## 131. Semantic rejection

Reviewで`reject`となったCandidate。

Provider errorではない。

---

## 132. Internal error

Adapter、Validator、Stage Handler、Workspace連携の予期しないerror。

`internal_error`をformat error、semantic rejection、Review Issue、`manual_review_required`へ変換しない。Runを`failed`として停止し、Call recordまたは診断logへ診断IDとtracebackを残す。利用者表示へ秘密情報を含めない。

明示的に安全と定義した例外型以外を広い`except Exception`でCandidate不採用へ丸めない。

---

# Part XXIII: Cancellation

## 133. 停止要求

停止要求後、新しいProvider callを開始しない。

進行中Callを安全にcancelできる場合はcancelする。

---

## 134. Cancel不可

Providerがcancelに対応しない場合:

```text
responseを待つ
timeoutまで待つ
応答到着後に未採用として処理
```

安全なrun-state境界へ到達して停止する。

---

## 135. Cancelled response

Cancelled Callの部分応答をCandidateとして採用しない。

Call outcomeを`cancelled`とする。

---

# Part XXIV: Provider Adapter契約

## 136. 共通request

概念構造:

```text
operation_id
model
system_instructions
input_messages
response_mode
schema
temperature
max_output_tokens
timeout
metadata
```

---

## 137. 共通response

概念構造:

```text
text
structured_data
usage
provider_request_id
finish_reason
raw_metadata
```

`raw_metadata`をStoryデータへ渡さない。

---

## 138. Adapter interface

概念例:

```text
send(request, credential, cancellation)
supports_structured_output()
supports_streaming()
count_tokens(request)
normalize_usage(response)
classify_error(error)
```

実際のPython名は実装で決める。

---

## 139. Adapter禁止事項

Provider Adapterは次を行わない。

```text
Stage遷移
Candidate採用
Review判断
Story State変更
ID割当
Retry loop全体
Publication組立
```

---

## 140. Provider SDK

公式SDKが利用可能で安定している場合は優先する。

ただし、SDK型をCore data modelへ漏らさない。

---

# Part XXV: Operation別方針

## 141. Initial Design

```text
response mode:
  structured

秘密情報:
  作者用情報を生成可能

Review:
  必須

Revision:
  設定上限内
```

---

## 142. Plan

```text
response mode:
  structured

処理単位:
  Series、Volume、対象Chapter、対象Sceneごとに一つ

basis Generation:
  必須

Review:
  必須

古いbasis:
  Candidateを破棄して同じ計画Stageから再生成
```

---

## 143. Scene Card

```text
response mode:
  structured

Context:
  現在State中心

秘密情報:
  このSceneに必要な範囲

Review:
  必須
```

---

## 144. Scene本文

```text
response mode:
  prose

Context:
  Writer秘密境界を厳格適用

Review:
  必須

Revision:
  完全本文
```

---

## 145. Continuity

```text
response mode:
  structured

入力本文:
  凍結版

Context:
  allowed_updatesとcurrent State

Review:
  必須

コード検証:
  Evidence、old_value、参照
```

---

## 146. Handoff

Volume HandoffはLLM operationではない。

巻の最終Generation、採用済みPlan、確定済みSceneからコードで決定的に導出する。

Prompt、Context、Provider call、Review、Revisionを使用しない。

---

## 147. Completion

```text
response mode:
  structured

action:
  evaluate

incomplete:
  正当結果

再試行:
  format errorだけ
```

---

## 148. Publication

```text
LLM operation:
  なし
```

---

# Part XXVI: Test

## 149. Unit test

```text
Operation設定解決
Prompt asset解決
Context秘密情報filter
token見積
Budget判定
Response Validator
error分類
usage正規化
code-only operationでProvider factoryを呼ばない
RecoveryでProvider factoryを呼ばない
internal_errorをReview Issueへ変換しない
```

---

## 150. Adapter contract test

各Provider Adapterで共通fixtureを使用する。

```text
structured success
prose success
connect timeout
first response timeout
idle timeout
total timeout
blocking streamの中断
rate limit
credential error
format error
usage欠落
stream中断
```

実networkを必須にしない。

---

## 151. Prompt test

Prompt textの完全一致だけへ過度に依存しない。

確認:

```text
必要assetが存在
重要instructionが含まれる
秘密情報policyが適用
出力契約が一致
```

Golden snapshotを使う場合は意図的変更時に更新する。

---

## 152. Context test

Operationごとに確認する。

```text
必要情報が入る
不要情報が入らない
作者用秘密がWriterへ漏れない
非POV内面が漏れない
basis Generationが正しい
token上限を守る
```

---

## 153. Review／Revision test

```text
accept
revise
reject
Revision後再Review
Revision上限
新Issue発生
basis Generation変更
```

---

## 154. Retry test

```text
transport retry回数
format retry回数
Revision回数
backoff
停止要求
Budget到達
```

三つの回数が混ざらないことを確認する。

---

## 155. Completion test

```text
complete
complete_with_issues
incomplete
format error再取得
incomplete再試行なし
```

---

## 156. Package smoke

Installed wheel環境で次を確認する。

```text
Prompt asset読込
Schema asset読込
Operation Registry
Provider Adapter import
source treeなしで実行
```

---

# Part XXVII: Hash非依存

## 157. 識別方針

LLM連携では、Context、Prompt、Candidate、Review、Call、Completionのhashやhash chainをAuthorityにしない。

調査と再開には次の明示的な識別子を使う。

```text
Operation ID
Operation instance ID
Call IDとattempt
Candidate IDとversion
Prompt version
basis Generation ID
target ID
```

将来hashを追加する場合は、識別対象、既存IDでは不足する理由、検出後の処理、保存期間、利用者価値を先に定義する。「念のため」には追加しない。

---

# Part XXVIII: Invariant

## 158. Operation不変条件

```text
一つのCallは一つのoperationに属する
operationは一つのStageと対象を持つ
Call前に設定・token・Budgetを確定
Credentialを記録しない
```

---

## 159. Context不変条件

```text
basis Generationが明示
必要情報だけ
秘密境界を適用
未採用Candidateを事実として混ぜない
HashをAuthorityにしない
```

---

## 160. Response不変条件

```text
modeが固定
形式検証後にCandidate化
参照検証
本文と構造化応答を混ぜない
```

---

## 161. Review不変条件

```text
ReviewがCandidateを書き換えない
Revisionが完全置換
Revision後に再Review
未解決errorを自動採用しない
```

---

## 162. Retry不変条件

```text
transport、format、revisionを分離
各上限あり
停止要求後に新Retryなし
Budget超過Callなし
```

---

## 163. Completion不変条件

```text
incompleteは正当結果
completeになるまで再試行しない
最終Generationだけを評価
```

---

# Part XXIX: 実装指針

## 164. CoreとAdapter

推奨package境界:

```text
storycraft/
├── core/
│   ├── operations/
│   ├── context/
│   ├── review/
│   └── budget/
├── providers/
│   ├── base.py
│   └── ...
└── assets/
    ├── prompts/
    └── schemas/
```

具体配置は実装で調整できる。

---

## 165. Dependency injection

Testでは次を差し替えられるようにする。

```text
Provider Adapter factory
Provider client factory
clock
sleep
token counter
cost table
credential source
cancellation token
```

---

## 166. Logging

Logへ次を出してよい。

```text
Call ID
operation
Provider
model
attempt
elapsed
outcome
usage
```

Prompt全文、Context全文、Credentialは通常logへ出さない。

---

## 167. Redaction

共通redaction処理を一か所に実装し、Call record、Audit、application log、error表示、Provider raw errorへ同じ規則を適用する。

少なくとも次を除去または置換する。

- CredentialとAPI key
- Authorization、cookie、session header
- signed URLとquery内secret
- Schemaでsecret指定されたfield
- Provider raw errorに含まれる認証情報
- PromptまたはContext内の保存禁止情報
- filesystem上の不要な秘密path

入れ子構造、配列、文字列化JSON、例外chainにもredactionを適用する。

redaction後に秘密値が残らないことをtestする。

安全にredactできるか判断できない場合は、対象内容の保存または表示を中止する。

---

## 168. Fail closed

秘密情報policy、Schema、Credential redactionが判断不能な場合は、Callや保存を中止する。

便利さを優先して未知情報を通さない。

---

# Part XXX: 文書境界

Release判断に必要な試験項目は`../testing/ACCEPTANCE.md`を唯一の正本とする。この文書では、試験ケース一覧や実装進捗を重複管理しない。

LLM連携の実装は、少なくとも次の設計境界を守る。

```text
LLMは意味生成と意味評価だけを担当する
Code-only operationとRecoveryはProvider非依存である
Provider AdapterとclientはCall直前に遅延生成する
Contextは必要最小限で、operationごとの秘密境界を守る
structured responseとprose responseを分離する
transport、format、revisionを別々に制御する
Timeoutは待機中のI/Oを実際に中断できる
予期しない内部例外を意味的失敗へ変換しない
Credentialをworkspaceとlogへ保存しない
PublicationにLLMを使用しない
```

---

## 169. 最終原則

Storycraft Version 1のLLM連携は、次に従う。

> LLMには物語の意味生成と評価だけを任せる。保存、State適用、Stage遷移、Recovery、Publicationはコードで決定し、Providerを必要としない処理からProvider初期化を分離する。

Providerの便利な機能を理由に、Story Authority、Stage遷移、Recovery、PublicationをLLMへ委ねてはならない。
