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
次Scene／次Chapter／次Volume
  ↓
VOLUME_HANDOFF
  ↓
COMPLETION
  ↓
PUBLICATION
  ↓
COMPLETED
```

Review／Revisionは、対応する生成Stageの後へ挿入する。

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
Volume Plan
Chapter Plan
Scene Loop
Volume Handoff
次Volume判定
```

最終VolumeのHandoff後はCompletionへ進む。

---

## 9. Volume Loop

一つのVolumeについて次を行う。

```text
Volume Plan確認または生成
Chapter一覧確認
各Chapterを順に処理
Volume Handoff作成
Volume完了
```

---

## 10. Chapter Loop

一つのChapterについて次を行う。

```text
Chapter Plan確認または生成
Scene一覧確認
各Sceneを順に処理
Chapter完了
```

---

## 11. Scene Loop

一つのSceneについて次を行う。

```text
Scene Plan確認
Scene Card生成
Scene Card Review／Revision
Scene本文生成
Scene本文Review／Revision
継続性更新生成
継続性Review／Revision
Scene確定
```

Scene確定前に次Sceneへ進まない。

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
一つのVolumeをChapterへ具体化する
```

入力:

```text
Volume Plan
current Generation
```

出力:

```text
Chapter Plan Candidate集合
```

---

## 51. Chapter Plan Review観点

```text
Chapter順が因果的
各Chapterに目的
開始状態と終了変化が明確
Scene数が過剰でない
必要な開示が配置
Volume終点へ収束
```

---

## 52. `scene_plan`

目的:

```text
一つのChapterを順序付きSceneへ具体化する
```

入力:

```text
Chapter Plan
current Generation
```

出力:

```text
Scene Plan Candidate集合
```

---

## 53. Scene Plan Review観点

```text
Scene順が因果的
各Sceneに固有目的
POVの選択が妥当
Locationと参加人物が現在Stateと整合
予定変更がChapter目的へ寄与
禁止開示が守られる
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

`basis_generation_id`が現在Generationと異なる場合:

```text
差分が無関係:
  利用可能

差分がScene前提へ影響:
  Plan Revision

判断不能:
  Reviewまたは人間確認
```

Hash一致を使わない。

---

# Part VIII: Scene Card Stage

## 56. `scene_card`

目的:

```text
一つのScene本文を生成するための詳細設計を作る
```

入力:

```text
Scene Plan
Chapter Plan
Volume Plan
current Generation
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
現在の人物位置
参加人物の公開可能状態
POV人物のKnowledge
関連Relationship状態
関連Thread状態
必要なWorld Rule
Scene Plan
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
POVが参加人物
場所が現在Stateと整合
開始状態がcurrent Generationと一致
目的がScene Planと一致
必須beatが具体的
開示許可と禁止が明確
allowed_updatesが過剰でない
Ending目標が予定であり事実化されていない
```

---

## 59. Scene Card Revision

RevisionはScene Card全体を置換する。

差分だけを保存しない。

基準Generationが変わった場合は、Revisionではなく再生成する。

---

## 60. Scene Card採用

採用後:

```text
active_scene_id:
  Scene ID

current_stage:
  scene_prose
```

同じSceneの基準Generationを固定する。

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
current Generationの必要情報
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
Scene Card
current Generation
```

出力:

```text
Continuity Update Candidate
Evidence Candidate
```

---

## 68. Continuity抽出範囲

抽出対象:

```text
人物位置
所有物
Knowledge
Relationship
負傷・状態
Commitment
Thread進行
時間経過
Location状態
World状態
```

---

## 69. Continuity禁止事項

```text
Planだけを根拠に更新
Scene Cardの予定だけを根拠に更新
本文にない出来事を追加
allowed_updates外を変更
秘密情報を公開状態へ変更
Canonを無言上書き
```

---

## 70. Evidence確認

コードで確認する。

```text
quoteが本文に存在
対象IDが存在
同じEvidence IDが重複しない
変更内容がoperationと一致
```

同じquoteが複数ある場合は出現順または前後文脈を使う。

---

## 71. Continuity Review観点

```text
本文根拠
許可範囲
old_value一致
new_value妥当
State不変条件
Thread status妥当
Knowledge状態妥当
時間順妥当
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
Scene Card、本文、Continuity Updateを採用し、新Generationを確定する
```

LLM call:

```text
なし
```

---

## 75. Scene Commit入力

```text
採用可能なScene Card
凍結本文
採用可能なContinuity Update
Evidence
current Generation
予約済みGeneration ID
```

---

## 76. Scene Commit検証

```text
Scene ID一致
basis Generation一致
本文version一致
Evidenceが本文に存在
allowed_updates内
old_valueがcurrent Generationと一致
新Stateが不変条件を満たす
PlanのScene順と一致
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

次を決定する。

```text
同Chapterに次Scene:
  scene_card

Chapter完了・同Volumeに次Chapter:
  chapter_planまたはscene_plan

Volume完了:
  volume_handoff
```

---

## 79. Scene Commit失敗

確定途中Crashは、Provider callを再実行せずRecovery規則で処理する。

内容検証失敗なら:

```text
Continuity Revision
または
本文Revision
```

へ戻す。

---

# Part XII: Chapter・Volume境界

## 80. Chapter完了

Chapter内の全予定Sceneが確定したらChapter完了とする。

Chapter完了専用Stageは作らない。

コードで次を確認する。

```text
全Sceneが存在
Scene順が一致
未完了active Sceneなし
```

---

## 81. Volume完了

Volume内の全Chapterと全Sceneが確定したら、`volume_handoff`へ進む。

Volume完了専用のManifestやGateは作らない。

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

Scene Card採用後に停止した場合:

```text
Scene Cardが完全:
  scene_proseから再開
```

本文凍結後に停止した場合:

```text
本文が完全・Continuityなし:
  scene_continuityから再開
```

Continuity採用候補後に停止した場合:

```text
すべて完全:
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
  次Sceneのscene_card
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
| `scene_commit` | 次Scene、次Chapter、または`volume_handoff` |
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

Scene Card前提不正:
  scene_card再生成

Planが古い:
  対応Plan Stage
```

任意の過去Stageへ自由に戻らない。

---

## 116. Plan Revision遷移

Scene処理中にPlan Revisionが必要な場合:

```text
active Sceneを未採用として保存
current Generationは変更しない
必要なPlan Stageへ戻る
新Plan版を採用
Scene Cardから再開
```

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
Planは基準Generationを持つ
Planを事実としてStateへ反映しない
採用済みPlanを上書きしない
```

---

## 120. Scene

```text
Scene中の基準Generation固定
本文変更後はContinuity再生成
Continuity採用前にState更新しない
Scene Commit前に次Sceneへ進まない
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
Scene Card不正
本文POV違反
禁止開示
Evidence quote不一致
allowed_updates外
old_value競合
本文Revision後Continuity再生成
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
Review／Revisionが共通化
Scene基準Generation固定
Scene Commitがcode-only
Completion incompleteを正当結果として扱う
Publicationが決定的
保存詳細を再定義していない
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

> 利用者と生成モデルに意味のあるStageだけを外部Stageとし、ReviewとRevisionを共通処理として扱い、Scene Card・本文・継続性・Scene確定を一つの基準Generation上で進め、未完結作品をPublicationしない。

内部の検証、ID割当、file確定、状態更新を大量の独立Stageへ分解してはならない。
