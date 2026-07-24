# Storycraft Pipeline設計

この文書は、Storycraft Version 1の意味的Stage、各Loop、Stage間の入出力、Review／Revision、Scene確定、完結判定、Publicationまでの処理順を定める。

上位文書:

- 製品仕様: [`../product/SPECIFICATION.md`](../product/SPECIFICATION.md)
- 製品要件: [`../product/REQUIREMENTS.md`](../product/REQUIREMENTS.md)
- アーキテクチャ: [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)
- データモデル: [`DATA_MODEL.md`](DATA_MODEL.md)
- 保存と復旧: [`WORKSPACE_AND_RECOVERY.md`](WORKSPACE_AND_RECOVERY.md)

関連文書:

- LLM連携: `LLM_INTEGRATION.md`
- Release試験: `../testing/ACCEPTANCE.md`

この文書は、PipelineとStage遷移の唯一の正本である。

---

# Part I: 基本方針

## 1. Pipelineの目的

Pipelineは、利用者入力からPublicationまでの制作工程を、再開可能な意味的単位へ分ける。

Pipelineが管理するもの:

```text
どのStageを実行するか
どの対象を処理するか
どの入力を使うか
どの成果物を作るか
いつReviewするか
いつRevisionするか
いつ採用するか
どこで停止するか
どこから再開するか
```

---

## 2. Stageの定義

Stageは、利用者、生成モデル、再開処理にとって意味のある処理単位である。

Stageとして扱う例:

```text
初期Concept生成
シリーズ計画
Scene Card生成
Scene本文生成
継続性更新
Scene確定
巻Handoff
完結判定
Publication
```

Stageとして扱わない例:

```text
JSONの読込
Schema確認
ID割当
一時file作成
directory rename
run-state更新
Log出力
```

これらはStage内部の実装手順である。

---

## 3. Stageの責務

各Stageは、次を明示しなければならない。

```text
Stage ID
目的
対象
入力
出力
Review対象か
Revision可能か
採用条件
次Stage
停止条件
再開境界
```

---

## 4. Pipelineの外部Stage数

Version 1では、外部的なStageを必要以上に細分化しない。

推奨Stage数は20〜30程度とする。

内部処理を独立Stageへ昇格させる場合は、次のいずれかを満たさなければならない。

```text
利用者がそこで停止して確認する価値がある
別のProviderまたはmodelを選ぶ必要がある
独立したReview／Revisionが必要
Crash後にその境界から再開する意味がある
```

---

## 5. Pipelineの大分類

```text
入力
初期設計
計画
Scene生成
巻終了処理
完結判定
Publication
```

---

# Part II: 全体フロー

## 6. 全体図

```text
INPUT
  ↓
INITIAL_CONCEPT
  ↓
INITIAL_CHARACTERS
  ↓
INITIAL_RELATIONSHIPS
  ↓
INITIAL_WORLD
  ↓
INITIAL_KNOWLEDGE
  ↓
INITIAL_THREADS
  ↓
INITIAL_ENDING
  ↓
INITIAL_INTEGRATE
  ↓
INITIAL_ACCEPT
  ↓
SERIES_PLAN
  ↓
VOLUME_PLAN
  ↓
CHAPTER_PLAN
  ↓
SCENE_PLAN
  ↓
SCENE_CARD
  ↓
SCENE_PROSE
  ↓
SCENE_CONTINUITY
  ↓
SCENE_COMMIT
  ↓
SCENE_PLAN／CHAPTER_PLAN／VOLUME_HANDOFF
  ↓
VOLUME_HANDOFF
  ↓
COMPLETION
  ↓
PUBLICATION
  ↓
COMPLETED
```

Review／Revisionは、対象Stage内のoperationとして実行し、独立Stageとして数えない。

---

## 7. Loop構造

```text
Series Loop
  └── Volume Loop
      └── Chapter Loop
          └── Scene Loop
              └── Review／Revision Loop
```

---

## 8. Series Loop

Series Loopは、全Volumeが完了するまで繰り返す。

```text
対象VolumeのVolume Plan
対象ChapterごとのChapter Plan
対象SceneごとのScene Loop
Volume Handoff
次Volume判定
```

最終VolumeのHandoff後はCompletionへ進む。

---

## 9. Volume Loop

一つのVolumeについて次を行う。

```text
Volume Plan確認または生成
Volume Plan内のChapter概要を順に選択
対象ChapterのChapter Planを生成
各Chapterを順に処理
Volume Handoff作成
Volume完了
```

---

## 10. Chapter Loop

一つのChapterについて次を行う。

```text
対象ChapterのChapter Plan確認または生成
Chapter Plan内のScene概要を順に選択
対象SceneごとのScene Loop
Chapter完了
```

---

## 11. Scene Loop

一つのSceneについて次を行う。

```text
対象SceneのScene Plan生成または再利用
Scene Plan Review／Revision
Scene Card生成
Scene Card Review／Revision
Scene本文生成
Scene本文Review／Revision
継続性更新生成
継続性Review／Revision
Scene確定
```

Scene PlanからScene確定まで同じ`basis_generation_id`を使い、Scene確定前に次Sceneへ進まない。

---

## 12. Review／Revision Loop

Review対象Stageでは、次を繰り返す。

```text
Candidate生成
↓
形式確認
↓
Review
↓
acceptなら採用候補
reviseならRevision
rejectなら停止または再生成
```

Revision上限に達した場合は、無理に採用しない。

---

# Part III: Stage一覧

## 13. Stage ID

Version 1のStage ID:

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

合計21 Stageである。

---

## 14. Stage IDの安定性

Stage IDは、run-state、Audit、設定、試験で共用する。

一度公開したStage IDを、意味を変えずに再利用しない。

表示名は日本語へ変換してよい。

---

## 15. Review operation

Reviewは独立Stage IDにしない。

各対象Stageのoperationとして扱う。

例:

```text
stage:
  scene_prose

operation:
  generate
  review
  revise
```

これによりStage数を増やさず、Review／Revision履歴を区別できる。

---

# Part IV: 共通Stage契約

## 16. Stage入力

各Stageは、次の入力分類から必要なものだけを受け取る。

```text
利用者入力
採用済みInitial Design
採用済みPlan
現在Generation
前Volume Handoff
親Stage成果物
Stage設定
```

不要な作品全体情報を毎Stageへ渡さない。

---

## 17. Stage出力

Stage出力は次のいずれかである。

```text
Candidate
採用済み設計
採用済みPlan
Scene成果物
Generation
Handoff
Completion Result
Publication
```

Stageが複数の正本を独立に作ってはならない。

---

## 18. Stage開始条件

Stage開始前に確認する。

```text
run-stateがそのStageを示す
対象が一致
必要な入力が存在
基準Generationが一致
予算が残る
停止要求がない
pending commitがない
```

---

## 19. Stage完了条件

Stage完了時に確認する。

```text
出力が構造的に正しい
参照が解決
Review条件を満たす
採用または確定が完了
run-stateが次Stageへ更新
```

---

## 20. Stage停止条件

次の場合はStageを完了扱いにしない。

```text
通信失敗上限
形式不正上限
Revision上限
予算上限
停止要求
秘密情報違反
基準Generation変更
人間確認が必要
```

---

## 21. Stage再開

Stage再開時は、未採用Candidateを再利用できるか確認する。

再利用条件:

```text
Candidateが完全
基準Generationが現在と一致
対象が一致
設定versionが一致
Review状態が明確
```

一つでも満たさない場合は再生成する。

---

# Part V: 入力Stage

## 22. `input`

目的:

```text
BriefまたはKeywordsを検証し、作品開始入力を確定する
```

入力:

```text
Brief
または
Keywords
```

出力:

```text
採用済みBrief
```

---

## 23. `input`開始条件

```text
新規workspace
BriefとKeywordsの正確に一方が存在
既存Initial Designがない
```

---

## 24. Keywords処理

Keywordsの場合:

```text
Keywords検証
↓
Brief Candidate生成
↓
元条件保持確認
↓
必要ならReview／Revision
↓
Brief採用
```

---

## 25. Brief検証

確認:

```text
4〜10巻
必須要素とavoidが矛盾しない
Ending希望とavoidが矛盾しない
日本語生成前提
最低限のpremiseが存在
```

---

## 26. `input`完了

Brief採用後:

```text
current_stage:
  initial_concept
```

---

# Part VI: 初期設計Stage

## 27. 初期設計の分割

初期設計は次へ分ける。

```text
initial_concept
initial_characters
initial_relationships
initial_world
initial_knowledge
initial_threads
initial_ending
initial_integrate
initial_accept
```

分割理由:

```text
対象ごとに異なるContextが必要
独立Reviewが有効
巨大な一回応答を避ける
統合前に問題を特定しやすい
```

---

## 28. `initial_concept`

目的:

```text
作品の中心設定、問い、テーマ、読者への約束、物語を動かす仕組みを定める
```

入力:

```text
Brief
```

出力:

```text
Story Concept Candidate
```

Review対象:

```text
はい
```

---

## 29. Concept Review観点

```text
Brief保持
中心的な問い
シリーズとして継続可能
4〜10巻に耐える
Ending方向と整合
avoid違反なし
ジャンルとtoneの整合
```

---

## 30. `initial_characters`

目的:

```text
主要人物と長期変化を定める
```

入力:

```text
Brief
採用候補Concept
```

出力:

```text
Character Candidate集合
```

---

## 31. Character Review観点

```text
主人公が存在
人物の欲求と恐れが明確
役割重複が意図的
長期ArcがSeries Conceptと整合
秘密情報と公開情報が分離
人物数が過剰でない
```

---

## 32. `initial_relationships`

目的:

```text
主要人物間の開始関係と長期変化を定める
```

入力:

```text
Concept
Character Candidate
```

出力:

```text
Relationship Candidate集合
```

---

## 33. Relationship Review観点

```text
参加人物が存在
関係が物語を動かす
長期変化が人物Arcと整合
private truthが公開説明へ混入しない
関係が過剰に重複しない
```

---

## 34. `initial_world`

目的:

```text
舞台、Location、World Rule、社会構造を定める
```

入力:

```text
Brief
Concept
Characters
Relationships
```

出力:

```text
World Candidate
Location Candidate集合
World Rule Candidate集合
```

---

## 35. World Review観点

```text
BriefとGenreに適合
Rule同士が矛盾しない
物語を制約する意味がある
Location階層が理解可能
後付け万能Ruleがない
```

---

## 36. `initial_knowledge`

目的:

```text
作品世界の真実、虚偽、人物ごとのKnowledge状態を定める
```

入力:

```text
Concept
Characters
Relationships
World
```

出力:

```text
Knowledge Fact Candidate集合
Character Knowledge Candidate集合
```

---

## 37. Knowledge Review観点

```text
真実と人物のbeliefが分離
読者公開状態が明確
重要な秘密が識別可能
人物が開始時に知り得ない情報を知らない
```

---

## 38. `initial_threads`

目的:

```text
シリーズで追跡する主要Threadを定める
```

入力:

```text
Concept
Characters
Relationships
World
Knowledge
```

出力:

```text
Thread Candidate集合
```

---

## 39. Thread Review観点

```text
主要な問いが存在
完結必須Threadが識別
導入可能性がある
人物Arcと関係する
予定解決がEndingへ接続
Thread数が過剰でない
```

---

## 40. `initial_ending`

目的:

```text
シリーズ完結条件と望ましい読後感を定める
```

入力:

```text
Brief
Concept
Characters
Relationships
Threads
```

出力:

```text
Ending Design Candidate
Long-term Arc Candidate
```

---

## 41. Ending Review観点

```text
BriefのEnding希望と整合
主要Threadを評価可能
主人公の終着点が明確
禁止Endingへ違反しない
結末を本文へ早期漏洩させる構造でない
```

---

## 42. `initial_integrate`

目的:

```text
個別初期設計Candidateを一つの整合したInitial Designへ統合する
```

入力:

```text
すべての初期設計Candidate
```

出力:

```text
統合Initial Design Candidate
```

---

## 43. Initial Integrate確認

```text
参照IDが解決
同名人物重複なし
World Rule矛盾なし
KnowledgeとThread整合
EndingとThread整合
Brief必須条件保持
avoid違反なし
```

---

## 44. `initial_accept`

目的:

```text
Initial Designを採用し、Initial Generationを作る
```

入力:

```text
Review済み統合Initial Design
```

出力:

```text
採用済みInitial Design
Initial Generation
```

LLM callは原則不要である。

---

## 45. Initial Accept完了

```text
current_generation:
  Initial Generation

current_stage:
  series_plan
```

---

# Part VII: 計画Stage

## 46. `series_plan`

目的:

```text
全Volumeを通したシリーズ構造を作る
```

入力:

```text
Brief
Initial Design
Initial Generation
```

出力:

```text
Series Plan Candidate
```

Review対象:

```text
はい
```

---

## 47. Series Plan Review観点

```text
4〜10巻
各巻に固有の役割
人物Arcの段階的進行
Relationship変化
Thread進行
重要開示の順序
危機の拡大
Endingへの接続
```

---

## 48. `volume_plan`

目的:

```text
一つのVolumeを現在状態から具体化する
```

入力:

```text
Series Plan
current Generation
前Volume Handoff
```

最初のVolumeではHandoffはない。

出力:

```text
Volume Plan Candidate
```

---

## 49. Volume Plan Review観点

```text
Series Planと整合
実際の開始Stateを反映
前Volume Handoffを反映
巻固有の中心対立
巻末の意味ある変化
次巻への接続
```

---

## 50. `chapter_plan`

目的:

```text
Volume Plan内の一つの対象Chapterを、順序付きScene概要へ具体化する
```

入力:

```text
Volume Plan
対象Chapter番号
current Generation
前Chapterまでの確定結果
```

出力:

```text
一つのChapter Plan Candidate
```

複数Chapterを一回のCandidateで確定しない。

---

## 51. Chapter Plan Review観点

```text
対象ChapterがVolume Plan上の次Chapterである
前Chapterまでの確定結果と開始状態が整合する
Chapter目的と終了変化が明確である
Scene概要の順序が因果的である
Scene数が過剰でない
必要な開示が配置されている
Volume終点へ寄与する
```

---

## 52. `scene_plan`

目的:

```text
Chapter Plan内の一つの対象Sceneを、Scene Card作成前の実行計画へ具体化する
```

入力:

```text
Chapter Plan
対象Scene番号
current Generation
直前Sceneまでの確定結果
```

出力:

```text
一つのScene Plan Candidate
```

複数Sceneを一回のCandidateで確定しない。

---

## 53. Scene Plan Review観点

```text
対象SceneがChapter Plan上の次Sceneである
Sceneに固有目的がある
POVの選択が妥当である
Locationと参加人物がbasis Generationと整合する
予定beatと状態変化がChapter目的へ寄与する
開示予定と禁止開示が現在の読者開示状態と整合する
```

---

## 54. Plan採用

Review済みPlanは、各Stage完了時に採用する。

採用済みPlanは上書きしない。

Plan採用後:

```text
series_plan:
  volume_planへ

volume_plan:
  chapter_planへ

chapter_plan:
  scene_planへ

scene_plan:
  scene_cardへ
```

---

## 55. 古いPlan

`basis_generation_id`が現在Generationと異なるPlanは、そのまま採用または実行しない。

再利用できるのは、Planが参照する対象とfieldをコードで比較し、基準Generation以降の変更が入力へ影響しないと証明できる場合だけである。

```text
影響なしを証明できる:
  同じPlan版を再検証して利用可能

関連入力に変更がある、または影響なしを証明できない:
  新しいbasis GenerationでPlanを再生成し、旧版をsupersededにする
```

LLM判断だけで古いPlanを再利用せず、Hash一致も使わない。

---

# Part VIII: Scene Card Stage

## 56. `scene_card`

目的:

```text
一つのScene本文を生成するための詳細設計を作る
```

入力:

```text
採用済みScene Plan
採用済みChapter Plan
採用済みVolume Plan
Scene Planのbasis Generation
必要なHandoff
```

出力:

```text
Scene Card Candidate
```

---

## 57. Scene Card Context

含める:

```text
basis Generation内の関連する現在State
参加人物の公開可能状態
POV人物のKnowledge
現在の読者開示状態
関連するRelationship、Location、World、Thread、Inventory、Commitment
必要なCanonとWorld Rule
採用済みScene Plan
直前Sceneの必要要約
```

含めない:

```text
無関係な全Canon
将来巻の詳細
未公開Ending全体
非POV人物の非公開内面
無関係なThread
```

---

## 58. Scene Card Review観点

```text
POVが参加人物である
場所と参加人物がbasis Generationと整合する
開始状態がScene Planのbasis Generationと一致する
目的がScene Planと一致する
必須beatが具体的である
開示許可と禁止が読者開示状態と整合する
allowed_updatesが必要最小限である
Ending目標が予定であり事実化されていない
```

---

## 59. Scene Card Revision

RevisionはScene Card全体を置換する。

差分だけを保存しない。

current GenerationがScene Planの`basis_generation_id`から変わった場合は、Scene CardだけをRevisionせず、§55に従ってScene Planから再評価する。

---

## 60. Scene Card採用

採用後:

```text
active_scene_id:
  Scene ID

current_stage:
  scene_prose
```

採用済みScene Planの`basis_generation_id`を、本文、継続性更新、Scene Commitまで固定する。

---

# Part IX: Scene本文Stage

## 61. `scene_prose`

目的:

```text
Scene Cardに基づく自然な日本語本文を生成する
```

入力:

```text
採用済みScene Card
Scene Planのbasis Generationから抽出した必要情報
直前本文の必要最小限
文体設定
```

出力:

```text
Scene本文Candidate
```

---

## 62. 本文応答形式

本文応答は、原則として本文だけを返す。

禁止:

```text
JSON
front matter
内部ID
Review説明
自己評価
箇条書き
Prompt引用
```

---

## 63. Prose Review観点

```text
Scene Card遵守
POV遵守
Knowledge制約
禁止開示なし
必須beat達成
人物行動の自然さ
現在Stateとの整合
本文品質
前後Scene接続
```

---

## 64. 本文の構造確認

Review前にコードで確認する。

```text
空でない
最低限の文字数
JSONらしい応答でない
code fenceを含まない
内部metadataを含まない
encodingが正常
```

形式不正はReviewへ送らず再取得する。

---

## 65. Prose Revision

Revision入力:

```text
元本文
Review Issue
Scene Card
必要なContext
```

出力:

```text
完全な置換本文
```

Issueだけを直すPatchは受け付けない。

---

## 66. 本文凍結

本文Candidateが採用可能になったら凍結する。

凍結後:

```text
本文versionを固定
継続性抽出へ進む
```

継続性抽出後に本文を変えた場合は、Continuityを作り直す。

---

# Part X: 継続性Stage

## 67. `scene_continuity`

目的:

```text
凍結本文に実際に書かれた変化を抽出する
```

入力:

```text
凍結本文
採用済みScene Card
Scene Planのbasis Generation
```

出力:

```text
Continuity Update Candidate
Evidence Candidate
```

---

## 68. Continuity抽出範囲

抽出対象は、`DATA_MODEL.md` §39の現在Stateと§61の`allowed_updates`に含まれる対象・fieldだけである。

本文に変化または開示のEvidenceがある場合だけUpdate Operationを作る。Scene Cardの予定、Plan、Review指摘だけを根拠に更新しない。

---

## 69. Continuity禁止事項

```text
PlanまたはScene Cardの予定だけを根拠に更新する
本文にない出来事を追加する
allowed_updates外の対象・fieldを変更する
禁止された開示をreader_knowledgeへ反映する
本文Evidenceなしに人物Knowledgeや読者開示を変更する
Canon、Initial Design、採用済みPlanを変更する
存在しない対象IDを作る
```

---

## 70. Evidence確認

Evidenceの形式と照合規則は`DATA_MODEL.md` §67〜68を正本とする。Pipelineでは少なくとも次をコードで確認する。

```text
scene_idが対象Sceneと一致する
quoteのoccurrence番目が凍結本文に存在する
各Evidenceが一つ以上のOperationから参照される
各Operationの対象・fieldがallowed_updates内である
old_valueがbasis Generationと一致する
```

同じquoteが複数ある場合は1始まりの`occurrence`で識別し、文字offsetは使わない。

---

## 71. Continuity Review観点

```text
すべてのOperationに本文Evidenceがある
対象・fieldがallowed_updates内である
old_valueがbasis Generationと一致する
new_valueが対象Stateの契約を満たす
人物Knowledgeと読者開示を混同していない
Location、World、Inventory、CommitmentのAuthorityを重複させていない
時間順とThread遷移が妥当である
変更不要なStateを更新していない
```

---

## 72. Continuity Revision

RevisionはContinuity Update全体を置換する。

本文は変更しない。

本文自体の問題が原因なら、`scene_prose`へ戻り本文Revision後にContinuityを再生成する。

---

## 73. Continuity採用候補

Continuityが採用可能になっても、まだStory Stateへ反映しない。

Scene Commitで本文、Continuity、新Generationを一つの確定操作として採用する。

---

# Part XI: Scene Commit Stage

## 74. `scene_commit`

目的:

```text
Scene Card、本文、Continuity Update、Evidence、新Generationを一つの採用判断として確定する
```

LLM call:

```text
なし
```

---

## 75. Scene Commit入力

```text
採用済みScene Plan
採用可能なScene Card
凍結本文
採用可能なContinuity UpdateとEvidence
basis Generationである親Generation
予約済みresult Generation ID
```

Scene PlanからContinuityまでの`scene_id`、`scene_plan_id`、`basis_generation_id`は一致しなければならない。

---

## 76. Scene Commit検証

```text
Scene Plan、Scene Card、本文、Continuityの識別子が一致する
basis Generationがrun-state.current_generation_idと一致する
本文versionがContinuityの対象versionと一致する
Evidenceが凍結本文と一致する
全Operationがallowed_updates内である
old_valueが親Generationと一致する
新StateがDATA_MODEL.mdのAuthorityと不変条件を満たす
対象SceneがChapter Plan上の未確定な次Sceneである
result Generation IDが予約済みIDと一致する
```

---

## 77. Scene Commit出力

```text
採用済みScene directory
新Generation directory
更新済みrun-state
```

詳細な確定順は`WORKSPACE_AND_RECOVERY.md`へ従う。

---

## 78. Scene Commit完了後

新Generationを`current_generation_id`へ設定した後、採用済みPlanの順序だけから次Stageと`current_target`を決定する。

```text
同Chapterに未確定の次Sceneがある:
  scene_plan
  next targetは次Scene

Chapterが完了し、同Volumeに未計画の次Chapterがある:
  chapter_plan
  next targetは次Chapter

Volume内の全ChapterとSceneが完了した:
  volume_handoff
  next targetは現在Volume
```

次Sceneへ直接`scene_card`で進まず、新Generationを基準に一Scene分のScene Planを作る。

---

## 79. Scene Commit失敗

確定途中Crashは、Provider callを再実行せず`WORKSPACE_AND_RECOVERY.md`のRecovery規則で処理する。

確定開始前の内容検証失敗は原因別に戻す。

```text
ContinuityまたはEvidenceだけが不正:
  scene_continuity

凍結本文が原因:
  scene_prose

Scene CardまたはScene Planの前提が不正:
  scene_planから再評価

内部処理またはfilesystemの予期しない失敗:
  failedとして停止
```

---

# Part XII: Chapter・Volume境界

## 80. Chapter完了

採用済みChapter Planの全Scene概要に対応するSceneが、順序どおり一度ずつ確定したらChapter完了とする。

Chapter完了専用Stageは作らない。コードで次を確認する。

```text
Chapter Plan上の全Sceneが存在する
確定Sceneの順序と番号が一致する
重複または欠番がない
未完了active Sceneとpending commitがない
```

---

## 81. Volume完了

採用済みVolume Plan上の全ChapterについてChapter Planが採用され、その全Sceneが§80を満たしたら`volume_handoff`へ進む。

Volume完了専用のManifestやGateは作らず、採用済みPlanと確定済みSceneから決定する。

---

# Part XIII: Volume Handoff Stage

## 82. `volume_handoff`

目的:

```text
巻末の実際のStory状態を次巻またはCompletionへ渡す
```

入力:

```text
Volume Plan
巻内の採用済みScene
巻末Generation
Series Plan
```

出力:

```text
Volume Handoff Candidate
```

---

## 83. Handoff生成内容

```text
主要人物の巻末状態
主要Relationshipの巻末状態
解決Thread
未解決Thread
新しい制約
次巻で無視できない結果
Ending進捗
```

---

## 84. Handoff Review観点

```text
巻末Generationと一致
本文にない出来事なし
未解決Threadを勝手に解決しない
次巻本文を先に書かない
Canonを変更しない
Series Planへの接続
```

---

## 85. Handoff採用

Review済みHandoffを確定する。

次Stage:

```text
次Volumeあり:
  volume_plan

最終Volume:
  completion
```

---

# Part XIV: Completion Stage

## 86. `completion`

目的:

```text
シリーズが正式Publication可能な完結状態かを評価する
```

入力:

```text
最終Generation
全Volume Handoff
Series Plan
Initial Design
Ending Design
Required Thread
主要人物Arc
主要Relationship Arc
```

出力:

```text
Completion Result Candidate
```

---

## 87. Completion前確認

LLM call前にコードで確認する。

```text
全Volume完了
全計画Scene確定
未完了active Sceneなし
最終Handoff存在
必須Thread存在
Ending条件存在
```

満たさない場合はCompletion callを行わない。

---

## 88. Completion Context

含める:

```text
最終Generationの必要状態
Required Thread一覧
Ending必須条件
主要人物の開始と終了状態
主要Relationshipの開始と終了状態
各Volume Handoff
重要Evidence参照
```

含めない:

```text
不要な全本文
Provider Audit
Review履歴
秘密でないものまで含む巨大Context
```

---

## 89. Completion Review

Completion Resultは、構造確認と一貫性確認を行う。

確認:

```text
全必須Threadを評価
全Ending条件を評価
statusとchecksが一致
basis Generationが最終
Evidence参照が解決
```

意味的Review／Revisionは原則一回まで許可してよい。

`incomplete`をRevision対象にしない。

---

## 90. Completion結果遷移

```text
complete:
  publication

complete_with_issues:
  publication

incomplete:
  blocked
```

`incomplete`の場合:

```text
stop_reason:
  completion_incomplete
```

---

# Part XV: Publication Stage

## 91. `publication`

目的:

```text
採用済みScene本文から読者向け原稿を組み立てる
```

LLM call:

```text
なし
```

---

## 92. Publication入力

```text
採用済みSeries／Volume／Chapter Plan
採用済みScene本文
Publication formatting設定
Completion Result
```

---

## 93. Publication処理

```text
Scene順を確認
巻別本文を組み立て
全巻本文を組み立て
目次・題名・区切りを付加
metadataを作成
Completion Resultを添付
private情報を除外
```

---

## 94. Publication禁止事項

```text
新しい本文生成
Scene本文の書換え
未公開情報の追加
ReviewやAuditの混入
Provider call
```

---

## 95. Publication完了

確定後:

```text
current_publication:
  新Publication

run status:
  completed

current_stage:
  publication
```

`completed`はPublication確定後だけ設定する。

---

# Part XVI: Review／Revision共通制御

## 96. Review対象Stage

標準Review対象:

```text
initial_concept
initial_characters
initial_relationships
initial_world
initial_knowledge
initial_threads
initial_ending
initial_integrate
series_plan
volume_plan
chapter_plan
scene_plan
scene_card
scene_prose
scene_continuity
volume_handoff
completion
```

`input`、`initial_accept`、`scene_commit`、`publication`はコード検証中心である。

---

## 97. Review決定

```text
accept:
  採用可能

revise:
  Revisionへ

reject:
  再生成または人間対応
```

---

## 98. Revision回数

Revision上限はoperationごとに設定できる。

推奨既定:

```text
Initial Design:
  2

Plan:
  2

Scene Card:
  2

Scene本文:
  3

Continuity:
  2

Handoff:
  2

Completion:
  1
```

---

## 99. Review Issueの引継ぎ

Revisionには未解決Issueだけを渡す。

過去に解決したIssueを毎回再提示しない。

ただし、Revision後に再発していないかReviewで再確認する。

---

## 100. Revision後Review

Revision結果は再Reviewする。

Revisionしたという事実だけで採用しない。

---

## 101. Reject

`reject`は次の場合に使う。

```text
前提から全面的に外れている
Revisionでは修正困難
安全上採用不可
基準Generationが古い
入力自体が矛盾
```

---

# Part XVII: Retry・停止・Budget

## 102. 通信Retry

対象:

```text
connection error
temporary provider error
timeout
rate limit
```

同じCall IDを再利用せず、新しいCallとして記録する。

論理operationは同じまま保持する。

---

## 103. 形式Retry

対象:

```text
JSON不正
必須field欠落
enum不正
本文ではなく説明が返る
```

意味的Review Issueを形式Retryへ含めない。

---

## 104. Budget確認

新しいProvider call前に確認する。

```text
Call数
token
推定cost
経過時間
```

上限到達時はCallを開始せず停止する。

---

## 105. 利用者停止

停止要求後:

```text
新しいProvider callを開始しない
現在のresponse処理を安全に完了
未採用Candidateを保存
run-stateをstopped
```

Scene CommitやPublication確定中は、確定処理を完了してから停止してよい。

---

## 106. BlockedとFailed

```text
blocked:
  人間判断または作品修正が必要

failed:
  自動継続不能な技術失敗
```

Completion `incomplete`は`blocked`であり`failed`ではない。

---

# Part XVIII: Resume

## 107. Resume判定

`WORKSPACE_AND_RECOVERY.md`のRecovery結果に従う。

```text
resume
regenerate
manual
```

---

## 108. Candidate再利用

Candidate再利用条件:

```text
完全
対象一致
Stage一致
basis Generation一致
設定version一致
Review状態明確
```

---

## 109. Scene再開

再開前に、active Sceneの`basis_generation_id`が`current_generation_id`と一致することを確認する。一致しない場合は§55に従って`scene_plan`から再評価する。

```text
Scene Plan採用済み・Scene Cardなし:
  scene_cardから再開

Scene Card採用済み・本文なし:
  scene_proseから再開

本文凍結済み・Continuityなし:
  scene_continuityから再開

Continuity採用候補が完全:
  scene_commitから再開
```

---

## 110. Commit途中

Scene CommitまたはPublication確定途中は、PipelineでStageを再実行せず、Recovery処理を先に行う。

---

# Part XIX: `step`の意味

## 111. 一回の`step`

`step`は、現在Stageを一つ完了する。

例:

```text
current_stage:
  scene_prose

step:
  本文生成、Review、必要なRevision、本文凍結まで
```

Review／Revisionを別stepへ分割しない。

---

## 112. `step`とLoop

`step`はLoop全体を完了しない。

例:

```text
scene_commitを一回実行:
  一Sceneだけ確定

次回step:
  次Sceneのscene_plan、次Chapterのchapter_plan、またはvolume_handoff
```

---

## 113. `step`の停止

Stageがblockedまたはfailedになった場合は、完了せずその状態で返る。

---

# Part XX: Stage遷移表

## 114. 主遷移

| 現在Stage | 正常完了後 |
|---|---|
| `input` | `initial_concept` |
| `initial_concept` | `initial_characters` |
| `initial_characters` | `initial_relationships` |
| `initial_relationships` | `initial_world` |
| `initial_world` | `initial_knowledge` |
| `initial_knowledge` | `initial_threads` |
| `initial_threads` | `initial_ending` |
| `initial_ending` | `initial_integrate` |
| `initial_integrate` | `initial_accept` |
| `initial_accept` | `series_plan` |
| `series_plan` | `volume_plan` |
| `volume_plan` | `chapter_plan` |
| `chapter_plan` | `scene_plan` |
| `scene_plan` | `scene_card` |
| `scene_card` | `scene_prose` |
| `scene_prose` | `scene_continuity` |
| `scene_continuity` | `scene_commit` |
| `scene_commit` | 次Sceneの`scene_plan`、次Chapterの`chapter_plan`、または`volume_handoff` |
| `volume_handoff` | 次Volumeの`volume_plan`または`completion` |
| `completion` | `publication`または`blocked` |
| `publication` | `completed` |

---

## 115. 戻り遷移

許可する戻り:

```text
Review revise:
  同じStage内

Continuity原因が本文:
  scene_prose

Scene Card候補だけが不正:
  scene_card内でRevisionまたは再生成

Scene Cardの前提であるScene Planが不正:
  scene_plan

Planが古い:
  対応Plan Stageで新versionを生成
```

任意の過去Stageへ自由に戻らない。

---

## 116. Plan Revision遷移

Scene処理中にPlan Revisionが必要な場合:

```text
active Sceneの未採用Candidateを履歴として保持する
current Generationは変更しない
必要なPlan Stageへ戻る
新Plan版を採用する
下位Planを順に再評価する
対象SceneのScene Planから再開する
```

旧Planを上書きせず、古いbasis Generationに依存するScene Card、本文、Continuityを採用しない。

---

# Part XXI: Invariant

## 117. Pipeline全体

```text
一度にactive Stageは一つ
一度にactive Sceneは一つ
一度にpending commitは一つ
採用前CandidateはStory Authorityではない
Stage完了前に次Stageへ進まない
```

---

## 118. Initial Design

```text
Brief必須条件を保持
統合前Candidateを採用済み扱いしない
Initial Generation前にSeries Planへ進まない
```

---

## 119. Plan

```text
Volume、Chapter、Scene Planは基準Generationを持つ
Chapter Planは一Chapter、Scene Planは一Sceneだけを対象にする
Planを事実としてStateへ反映しない
採用済みPlanを上書きしない
古いPlanは影響なしをコードで証明できる場合だけ再利用する
```

---

## 120. Scene

```text
Scene PlanからScene Commitまで基準Generationを固定する
本文変更後はContinuityとEvidenceを再生成する
Continuity採用前にStateを更新しない
Scene Commit前に次Sceneへ進まない
次Sceneは新Generationを基準にscene_planから開始する
```

---

## 121. Completion

```text
全Volume完了前に実行しない
incompleteを再試行しない
最終Generation以外を評価しない
```

---

## 122. Publication

```text
公開可能Completionが必要
LLMで本文再生成しない
採用済みScene順を変更しない
確定前にcompletedへしない
```

---

# Part XXII: 旧Stage設計の廃止

## 123. 廃止する外部Stage

次のような内部処理を独立Stageとして扱わない。

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

---

## 124. 廃止理由

```text
利用者価値がない
再開単位として細かすぎる
run-stateが複雑になる
文書と試験が増える
atomic確定内部手順と重複する
```

---

## 125. 内部operationとして残すもの

必要な検証や確定処理は削除せず、Stage内部operationとして残す。

```text
validate
allocate
prepare
review
revise
finalize
update_state
```

---

# Part XXIII: 実装指針

## 126. Stage Handler

各Stageは共通interfaceを実装する。

概念例:

```text
can_start(context)
prepare_input(context)
execute(context)
validate_output(output)
review(output)
revise(output, issues)
accept(output)
next_stage(context)
```

実際のPython interface名は実装で決定する。

---

## 127. Stage Registry

Stage IDとHandlerの対応は一か所で管理する。

CLI、Recovery、試験が別々のStage一覧を持たない。

---

## 128. Transition Engine

次Stage決定はStage Handlerまたは共通Transition Engineへ集約する。

各所に`if current_stage == ...`を散在させない。

---

## 129. Provider operation

StageとProvider operationを分ける。

例:

```text
stage:
  scene_prose

operation:
  generate
  review
  revise
```

設定はoperation単位でmodelを選択できる。

---

## 130. Code-only Stage

`scene_commit`と`publication`は原則code-onlyである。

`initial_accept`もcode-onlyを基本とする。

---

## 131. Deterministic処理

次は決定的に実行する。

```text
ID割当
Schema validation
State operation適用
Plan順の確認
Publication組立
Stage遷移
Recovery判定
```

LLMへ委ねない。

---

# Part XXIV: 試験観点

## 132. 正常系

```text
BriefからPublicationまで
KeywordsからBrief生成
複数Volume
複数Chapter
複数Scene
Reviewなし採用
Revisionあり採用
complete_with_issues
```

---

## 133. 失敗系

```text
入力矛盾
通信Retry上限
形式Retry上限
Revision上限
Budget到達
秘密情報違反
古いbasis Generation
```

---

## 134. Scene系

```text
Chapter PlanとScene Planが一対象単位である
次Sceneがscene_planから開始する
Scene Card不正
本文POV違反
禁止開示
人物Knowledgeと読者開示の混同
Evidence quoteまたはoccurrence不一致
allowed_updates外
old_value競合
Location、World、Inventory、CommitmentのAuthority重複
本文Revision後ContinuityとEvidenceを再生成
```

---

## 135. Completion系

```text
前提不足でCallしない
complete
complete_with_issues
incomplete
statusとcheck矛盾
incompleteを再試行しない
```

---

## 136. Publication系

```text
全巻順
Scene順
private情報除外
LLM callなし
rename後Crash
completed更新前Crash
```

---

# Part XXV: 受入条件

## 137. 文書受入条件

```text
Stage一覧が一意
Stage数が過剰でない
全体Loopが明確
Chapter PlanとScene Planの処理単位が一意
Review／RevisionがStage内operationとして共通化
Scene PlanからScene Commitまで基準Generation固定
Scene Commit後の次Stageが決定的
データ型とAuthorityをDATA_MODEL.mdから重複定義しない
Scene Commitがcode-only
Completion incompleteを正当結果として扱う
Publicationが決定的
保存手順を再定義していない
Hash・Manifest・Gateへ依存しない
```

---

## 138. 実装完成条件

```text
21 StageをRegistryから解決できる
run／resume／stepが同じTransition規則を使う
各Stageの開始条件を検証できる
Review／Revision上限を守る
Scene Loopを複数回実行できる
Volume Loopを複数回実行できる
CompletionからPublicationへ遷移できる
incompleteでblockedになる
Crash Recovery後に正しいStageへ戻る
```

---

## 139. 最終原則

Storycraft Version 1のPipelineは、次の原則に従う。

> 利用者と生成モデルに意味のあるStageだけを外部Stageとし、ReviewとRevisionをStage内operationとして扱い、一Scene分のScene Plan・Scene Card・本文・継続性・Scene確定を一つの基準Generation上で進め、未完結作品をPublicationしない。

内部の検証、ID割当、file確定、状態更新を大量の独立Stageへ分解してはならない。
