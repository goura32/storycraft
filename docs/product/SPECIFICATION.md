# Storycraft 製品仕様

この文書は、Storycraft Version 1について、利用者から見える振る舞いと製品としての約束を定める。

実装が満たすべき検証可能な要件は[`REQUIREMENTS.md`](REQUIREMENTS.md)、システム全体の設計方針は[`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)で定める。

この文書では、内部の保存形式、ファイル配置、データ項目、実装moduleなどは定義しない。

---

# Part I: 製品の目的

## 1. Storycraftとは

Storycraftは、日本語の長編シリーズを計画し、執筆し、継続性を管理し、完結可能性を確認し、読者向け原稿へまとめるCLIである。

一つの作品について、次を一連の作業として扱う。

```text
作品の初期設計
シリーズ全体の計画
各巻と各章の計画
各Sceneの設計
Scene本文の執筆
本文に基づく継続性更新
巻間の引継ぎ
シリーズの完結判定
読者向け原稿の作成
```

Storycraftは、単発の文章生成器ではない。

長編執筆中に変化する人物、関係、Knowledge、Thread、世界状態を追跡し、後続Sceneへ引き継ぐことを中心的な責務とする。

---

## 2. 製品の目的

Storycraftの目的は、長編シリーズ制作で発生しやすい次の問題を減らすことである。

```text
巻をまたいだ設定の矛盾
人物のKnowledgeの不整合
Relationship変化の欠落
未回収Threadの放置
計画と本文の乖離
前Sceneの結果を無視した後続Scene
作者だけが知る秘密の早すぎる開示
完結していない作品の公開
```

Storycraftは、これらを完全に自動解決すると約束するものではない。

しかし、問題を発見しやすくし、作品状態を明示し、再開可能な制作工程として管理する。

---

## 3. 想定利用者

Version 1の主な利用者は、次の条件に当てはまる個人である。

```text
自分のローカル環境で執筆する
一度に一つのprocessで作品を進める
CLI操作に抵抗がない
AIによる長編生成を段階的に確認したい
最終的な品質判断を自分で行う
```

複数人による同時共同編集は、Version 1の対象ではない。

---

## 4. 基本方針

Storycraftは、次を基本方針とする。

```text
日本語作品を生成する
作品状態を明示的に管理する
本文に書かれた事実だけを継続性へ反映する
ReviewとRevisionを分ける
公開前に完結状態を確認する
途中停止後に再開できる
確定済み成果物を不用意に書き換えない
```

利用者が理解できない内部複雑性を、製品価値として扱わない。

---

# Part II: 対象範囲

## 5. Version 1で提供するもの

Version 1は、次を提供する。

```text
BriefまたはKeywordsからの作品開始
4〜10巻のシリーズ計画
巻計画
章計画
Scene Card
日本語Scene本文
Review
Reviewで指摘された未採用CandidateのRevision
継続性更新
Evidence
巻Handoff
完結判定
全巻原稿
巻別原稿
途中停止と再開
一段階ずつの実行
```

---

## 6. Version 1で提供しないもの

Version 1は、次を提供しない。

```text
複数利用者の同時編集
クラウド共同作業
外部Web検索による自動調査
別の会話や別作品からの自動memory取得
出版プラットフォームへの自動投稿
電子書籍形式への直接変換
表紙画像生成
校正者や編集者の代替
法的・医学的・歴史的正確性の保証
商業的成功の保証
確定済みInitial DesignのRevision
採用済みPlanのRevision
確定済み成果物の手動編集取込
```

---

## 7. 作品規模

一つのシリーズは、4〜10巻で構成する。

巻数は、利用者の入力または作品設計から決定する。

指定が不可能、不整合、または範囲外の場合は、処理を開始せず利用者へ問題を示す。

---

## 8. 基本言語

Version 1の生成本文、計画、Review、完結判定、Publicationは日本語を基本とする。

固有名詞、作中用語、CLI command、設定値などは必要に応じて英語を使用できる。

---

# Part III: 入力

## 9. 入力方式

新しい作品は、次のいずれか一方から開始する。

```text
Brief
Keywords
```

両方を同時に指定してはならない。

どちらも指定されていない場合は開始しない。

---

## 10. Brief入力

Briefは、利用者が作品の方向性を比較的詳しく指定する方式である。

Briefでは、必要に応じて次を指定できる。

```text
仮題
ジャンル
対象読者
雰囲気
中心的な問い
主要人物
舞台
避ける内容
希望するEnding
希望巻数
文体上の希望
```

すべての項目が必須ではない。ただし、採用可能なBriefは次を満たさなければならない。

```text
作品の中心となるpremiseが空でない
volume_countが4〜10の整数として確定している
作品の基本言語が日本語として確定している
必須条件と避ける内容に明示的な矛盾がない
```

条件を満たさないBriefでは、Initial Design以降の作品生成を開始せず、問題を利用者へ示す。

---

## 11. Keywords入力

Keywordsは、短い語句や条件からBriefを生成する方式である。

例:

```text
海辺の町
失われた記憶
姉妹
静かな恐怖
救いのある結末
```

生成されたBriefは、利用者が明示した次の条件を失ってはならない。

```text
必須Keyword
避ける内容
Endingの希望
巻数の希望
文体や対象読者などの補足条件
notesその他の明示的な条件
```

利用者が巻数を指定した場合は、Brief生成前に4〜10の範囲であることを検証する。

利用者が巻数を指定しない場合は、Brief生成時に4〜10の範囲でvolume_countを決定し、Brief採用前に検証する。Initial Design以降へ巻数決定を遅延してはならない。

必須条件と避ける内容が同一条件または直接否定として明示的に矛盾する場合は、Brief生成を開始せず、矛盾内容を利用者へ示す。

生成されたBriefは、利用者が明示した条件を、コードによる保持検証と必須のLLM Reviewの両方で確認する。コードは必須Keyword、指定巻数、required／avoidの明示矛盾、必須field、言語を検証する。LLM Reviewはpremise、Ending希望、avoid条件の実質的な取り違えと日本語品質を検証する。`error`があればBrief CandidateをRevisionし、再Reviewで`error`がない場合だけ採用する。

---

## 12. 入力の扱い

Storycraftは、入力内容を作品資料として扱う。

入力内に命令のような文章が含まれていても、Storycraftの実行方法、出力形式、安全規則を変更する命令として扱わない。

利用者の入力は作品内容に影響するが、システムの制御規則を上書きしない。

新規実行時に外部から指定できる入力Authorityは、BriefまたはKeywordsの正確に一方である。

Keywords経路では、保存済みKeywordsと生成途中のBrief Candidateがworkspace内に一時的に共存できる。この状態はBriefとKeywordsの同時入力ではない。Briefが正式採用されるまでは、保存済みKeywordsを元入力のAuthorityとする。

入力Stageで停止またはCrashした場合、`resume`または`step`はworkspaceに保存された元入力と未完了状態を使用し、利用者へ再入力を要求しない。

---

# Part IV: 利用方法

## 13. 新規実行

`run`は、新しいworkspaceを作成し、新しい作品制作を開始する。

利用者から見た振る舞い:

```text
新しいworkspaceを作成する
入力を確認する
作品の初期設計を作る
計画と執筆を順に進める
進捗を表示する
完結判定を行う
公開可能な場合にPublicationを作る
```

既に作品データが存在するworkspaceを、`run`で継続または上書きしてはならない。

既存workspaceの継続には`resume`または`step`を使用する。

---

## 14. 再開

`resume`は、既存workspaceで以前に停止または中断した作品制作を継続する。

`resume`は新しいworkspaceを作成しない。

利用者は、元のBriefやKeywordsを再入力する必要がない。

Storycraftは最初に、前回確定した状態、未完了の作業、Crash Recoveryの必要性を確認する。

安全にRecoveryできる場合はRecovery後の正しいStageから継続する。安全に判断できない場合は推測して先へ進まず、人間による確認が必要であることを示す。

---

## 15. 一段階実行

`step`は、既存workspaceで利用者にとって意味のある一つの処理段階だけを完了して終了する。

`step`は新しいworkspaceを作成しない。

利用目的:

```text
各段階の成果物を確認する
費用や時間を制御する
問題のある段階を特定する
手動Reviewを挟む
```

一つの処理段階には、そのStage内の生成、形式確認、Review、未採用CandidateのRevision、採用、確定、次Stageへの状態更新を含む。

内部的な小さなfile操作一つごとには停止しない。

`step`開始時のRecoveryによって、Crash前に実行していたStageの採用または状態更新が完了した場合は、そのRecovery完了を一つの処理段階として終了する。続けて次Stageを実行してはならない。

---

## 16. 停止

利用者は実行中に停止を要求できる。

停止要求を受け付けた状態と、停止が完了した状態を区別する。

- `stopping`: 停止要求を受け付け、安全な処理境界へ移動している一時状態
- `stopped`: 安全な処理境界で停止が完了し、同じworkspaceから再開できる状態

外部Provider応答待ちでは、安全に取消可能なら取消し、取消不能なら応答またはtimeoutまで待つ。停止要求後に受信した未採用Candidateを自動採用してはならない。

複数file成果物の確定中は、部分的な成果物を完成扱いせず、atomicな確定または安全な未確定状態まで処理してから停止する。

制御された停止が完了した場合は、再入力や確定済み成果物の再生成を必要としない再開可能な状態を残す。

---

## 17. 進捗表示

Storycraftは、少なくとも次を利用者へ示す。

```text
現在のrun status
現在の処理Stage
現在の巻・章・Scene
完了した範囲
停止理由
再開可能か
完結判定結果
Publication作成結果
```

`run status`と`current_stage`は別の概念として管理する。

`run status`は実行状態を表し、`current_stage`は現在処理中または再開判断の基準となる意味的Stageを表す。

`current_stage`へ`stopped`、`blocked`、`failed`、`completed`などのrun status値を格納してはならない。

停止または失敗時も、停止した意味的Stageを保持する。

内部識別子だけを表示し、利用者が状況を理解できない状態にしてはならない。

---

# Part V: 生成工程

## 18. 全体の流れ

標準的な生成工程は次である。

```text
入力確認
↓
初期設計
↓
シリーズ計画
↓
巻計画
↓
章計画
↓
Scene計画
↓
Scene Card
↓
Scene本文
↓
継続性更新
↓
Scene確定
↓
次のScene計画、次の章計画、または巻Handoff
↓
次の巻
↓
完結判定
↓
Publication
```

ReviewとRevisionは、対象候補を生成するStageの内部で行う。

---

## 19. 初期設計

初期設計では、作品全体の基盤を作る。

少なくとも次を扱う。

```text
Concept
主要人物
主要Relationship
世界と舞台
Knowledge
主要Thread
Endingの方向
長期的な人物変化
```

初期設計内の要素は、互いに矛盾しない一つの作品設計として統合する。

---

## 20. シリーズ計画

シリーズ計画は、全巻を通した物語の進行を定める。

少なくとも次を示す。

```text
各巻の役割
主人公の変化
主要Relationshipの変化
主要Threadの進行
重要な開示
危機の拡大
Endingへの到達
```

各巻が独立した出来事の羅列にならず、シリーズ全体の因果関係を持つようにする。

---

## 21. 巻計画

巻計画は、シリーズ計画と巻開始時点の実際の作品状態から作る。

前巻の結果がある場合は、その結果を反映する。

巻計画は、計画上そうなる予定だった状態ではなく、実際に確定した本文と作品状態を基準にする。

---

## 22. 章計画とScene計画

章計画は、一つの章を順序付きSceneの概要へ具体化する。

章計画は、対象章の開始直前に、巻計画とその時点の採用済み作品状態から作る。複数章を一度に確定しない。

一つの章計画は少なくとも次を持つ。

```text
章の目的
章開始時の状況
章終了時の変化
順序付きScene概要
主要な対立
必要な開示
次章への接続
```

Scene計画は、章計画内の一つのScene概要を、Scene Card作成前に具体化する。複数Sceneを一つのScene計画として確定しない。

Scene計画は、そのScene開始直前の採用済み作品状態を基準にし、少なくとも次を持つ。

```text
Sceneの目的
POV
参加人物
場所
予定beat
予定する開示
予定する状態変化
禁止する開示
```

---

## 23. Scene Card

Scene Cardは、一つのSceneで何を書くかを定義する。

少なくとも次を扱う。

```text
POV
参加人物
場所
Sceneの目的
開始状況
必須beat
Conflict
開示してよい情報
開示してはいけない情報
許可する継続性更新
終了時の変化
```

Scene Cardは本文そのものではない。

---

## 24. Scene本文

Scene本文は、Scene Cardと現在の作品状態に基づく自然な日本語散文である。

本文へ次の内部情報を含めてはならない。

```text
JSONその他の内部構造化データ
Storycraftの内部識別子
ReviewのIssueまたは判定
Provider、Prompt、Schema、Budget、Auditの情報
実装用metadata
候補生成やRevisionの指示
Storycraft内部の設定値
```

この禁止は「原則」ではなく、物語表現を理由に例外化しない。

見出し、章番号、手紙、作中の一覧などは、作品本文として意図された表現であり、内部情報を漏らさない場合だけ使用できる。

Scene生成段階の本文は、そのまま物語本文として利用できる完全な散文でなければならない。

---

## 25. 本文の基準情報

一つのSceneについて、Scene計画、Scene Card、本文、継続性更新、Scene確定は、同一のbasis Generationと、そのGenerationから解決された同一の確定済みAuthority入力を基準にする。

基準となるGenerationが変化した作業は、そのまま採用しない。人物状態、場所、Knowledge、Thread、開示条件、時間、所有物、採用済みPlanその他の関連Authority入力が変化している場合は、Scene計画から作り直す。

basis Generationの識別子だけが異なり、関連するAuthority入力とその内容に差がないことをコードで確認できる場合に限り、既存Candidateを現在の基準で再検証して利用できる。

再検証なしに、異なるbasis GenerationのCandidate、Review、継続性更新、Scene Commitを混在させてはならない。

---

# Part VI: ReviewとRevision

## 26. Review

Reviewは生成Candidateの問題点を評価し、Candidate自体を書き換えない。

各Issueは次のseverityを持つ。

```text
error    採用を禁止する問題
warning  採用は可能だが利用者へ示す問題
note     採用可否へ影響しない補足
```

Reviewの対象例:

```text
入力条件との不一致
内部矛盾
人物行動の不自然さ
Knowledge違反
POV違反
未許可の開示
計画との不整合
文章品質
構造不足
```

`error`が一件でも存在するCandidateを採用してはならない。

`warning`または`note`だけの場合は採用できるが、Review結果を保存し、利用者が確認できるようにする。

---

## 27. Revision

Revisionは、Reviewで指摘された問題を修正した完全な置換候補を作る。

Revisionの対象は、まだ採用されていないCandidateに限る。確定済みInitial Design、採用済みPlan、確定済みSceneその他の確定成果物を変更する処理ではない。

Revisionは、差分だけを返すものではない。

利用者や後続処理は、修正済みの完全な候補を確認できる。

---

## 28. Reviewと採用

Review結果から次の処理を決定する。

```text
errorなし
  Candidateを採用できる

errorあり、同じoperation内で修正可能、Revision上限未到達
  Revisionを実行する

errorあり、同じoperation内で修正不能
  Candidateをrejectし、blockedとして停止する

errorあり、Revision上限到達
  Candidateを採用せず、blockedとして停止する
```

`warning`と`note`だけを理由にRevision回数を消費してはならない。

Revision済みであることだけを理由に採用せず、Revision後も再度Reviewする。

reject時は、上流成果物の変更が必要か、同じoperationでは修正不能かを判定し、安定した停止理由を利用者へ示す。

---

## 29. 形式不正との区別

通信失敗、形式不正、意味的Issueを区別する。

```text
通信失敗
  Providerへ到達できない
  timeout
  応答が途中で終了した

形式不正
  必須fieldがない
  JSONまたは指定形式として読めない
  Schemaに適合しない

意味的Issue
  矛盾
  品質不足
  POVまたは計画違反
```

通信再試行、形式不正の再取得、Reviewを受けたRevisionは、それぞれ独立した回数上限を使用する。

形式不正な応答を意味的Reviewへ渡したり、推測で補完して採用したりしてはならない。

---

# Part VII: 継続性

## 30. 継続性管理の目的

継続性管理は、Scene本文によって実際に変化した現在状態と読者への開示状態を、後続Sceneへ引き継ぐために行う。

Version 1で更新対象とする状態は次である。

```text
人物状態
Relationship状態
Location状態
World状態
Thread状態
人物Knowledge状態
読者への開示状態
時間状態
重要物品の所在・状態
約束・義務の状態
```

安定した設定や過去の確定事実はCanonとして参照し、通常のScene継続性更新では変更しない。

---

## 31. 本文優先

継続性更新は、Scene Cardの予定ではなく、確定した本文に基づく。

本文に書かれていない変化を、予定されていたという理由だけで作品状態へ追加してはならない。

---

## 32. 許可された更新

各Sceneで変更できる対象とfieldは、Scene Cardで明示し、現在の作品状態に存在する対象だけを更新する。

通常のScene継続性更新は、現在状態と読者への開示状態だけを変更する。次を変更しない。

```text
Canon
Initial Design
採用済みPlan
Ending Design
World Rule
新しい主要Threadの定義
重要人物の過去の真相
```

これらの変更を通常のScene継続性更新として採用してはならない。

Version 1は、確定済みInitial Designまたは採用済みPlanのRevisionを提供しない。これらの変更が必要な場合は、確定済み成果物を変更せず、必要な変更と停止理由を利用者へ示して停止する。

利用者は新しいworkspaceで作品制作を開始するか、将来提供される正式なRevision機能を使用する。

---

## 33. Evidence

継続性更新の各変更には、確定対象の本文中に存在するEvidenceを必ず関連付ける。

Evidenceは、利用者が次を確認できる情報を持つ。

```text
対象Scene
本文引用と出現位置
更新対象
変更前と変更後
変更理由
```

本文に根拠を特定できない変更は採用しない。Evidenceは改ざん証明ではなく、人間による確認と機械的な再検証のための情報である。

---

## 34. 未確定情報

本文が曖昧で、状態変化を一意に判断できない場合は変更しない。

対象fieldが明示的な不確定値を契約として持ち、本文中にその不確定性のEvidenceがある場合に限り、不確定状態へ更新できる。

それ以外はReview対象とし、Revision後も判断できなければ人間確認を要求する。推測による補完は行わない。

---

# Part VIII: 巻間処理

## 35. 巻Handoff

最終巻を含む各巻の終了時に、その巻の実際の結果を表すHandoffを作成する。

Handoffは少なくとも次を要約する。

```text
対象巻
対象巻終了時のGeneration
主要人物の現在状態
主要Relationshipの現在状態
解決したThread
未解決Thread
新しく生じた制約
次巻または完結判定で無視できない結果
Endingへの進捗
```

Handoffは確定済みGenerationから導出する要約であり、作品状態の詳細Authorityではない。

HandoffとGenerationが矛盾する場合はGenerationを優先し、矛盾するHandoffを次巻計画または完結判定へ使用してはならない。

Handoffから作品状態を復元、上書き、または巻き戻してはならない。新しい出来事を追加する文章生成としても扱わない。

---

## 36. 次巻への反映

第2巻以降の巻計画は、採用済みシリーズ計画、巻開始時のGeneration、および直前巻のHandoffを参照する。

前巻本文が当初計画から変化した場合は、実際のGenerationをAuthorityとして次巻計画を作る。Handoffは、Generation・確定Scene・Evidence・採用済みPlanから構築したsource bundleを根拠に、LLMが生成・Review・必要時Revisionした意味的補助要約として使用する。Handoffの主張は出典へ解決できなければならず、Generationを上書きしてはならない。

最終巻のHandoffは次巻計画ではなく完結判定へ引き渡す。

---

# Part IX: 完結判定

## 37. 完結判定の目的

完結判定は、作品が読者向けPublicationを作成できる状態かを評価する。

単に最終巻の予定Sceneが終了しただけでは、必ずしも完結とはみなさない。

---

## 38. 完結判定の開始条件

完結判定は、次のすべてを確認した後に行う。

```text
Series Planが要求する全巻の処理が終了している
対象ごとに採用済みPlanが正確に一件存在する
全Chapterと全予定SceneがPlanどおり確定している
最終巻を含む全巻のHandoffが存在する
現在のGenerationが最終予定Sceneの確定結果である
未完了の執筆、採用、確定、Recovery処理がない
全主要Threadを評価できる
全Ending条件を評価できる
全主要Character ArcとRelationship Arcを評価できる
```

実際のScene集合、Handoff集合、またはPlan集合が期待される集合と一致しない場合は完結判定を行わない。

複数の競合する採用済みPlanがある場合は、安全なAuthorityを決定できない状態として人間確認を要求する。

---

## 39. 完結判定の結果

完結判定は次のいずれかを返す。

### `complete`

次をすべて満たす。

```text
全必須Threadがresolved
全必須Ending条件がsatisfied
全主要Character ArcとRelationship Arcがsatisfied
未解決Issueがない
```

Publication作成へ進める。

### `complete_with_issues`

Publicationを妨げる必須未達はないが、次のいずれかが存在する。

```text
部分達成または適用不能として説明されたArc
Publicationを妨げない具体的なIssue
```

注意事項を保持してPublication作成へ進める。

### `incomplete`

次のいずれかの必須条件が未達である。

```text
必須Threadが未解決
必須Ending条件が未達
主要Character ArcまたはRelationship Arcがnot_satisfied
その他のPublicationを妨げる必須条件
```

未達内容を具体的なIssueとして記録し、Publication作成へ進めない。

Completion statusと各CheckおよびIssueが矛盾する結果は採用しない。

---

## 40. `incomplete`の扱い

`incomplete`は、完結条件を満たしていないことを示す正常な意味的判定である。Crash、workspace破損、Recovery失敗ではない。

Completion Resultを正式に保存した後、run statusを`blocked`、停止理由を`completion_incomplete`として停止する。

Publicationは作成しない。`complete`になるまで同じCompletion処理を自動再試行してはならない。

不足しているThread、Ending条件、Arc、その他の問題を利用者へ示す。

Version 1は確定済みPlanやSceneの正式Revisionを提供しないため、修正が必要な場合は新しいworkspaceで開始する。

---

## 41. 完結上の注意

Storycraftの完結判定は、作品の意味的な評価を支援する。

次を保証するものではない。

```text
すべての読者が満足する
文学的に優れている
商業出版に適している
伏線が一つも漏れていない
外部編集者の確認が不要である
```

---

# Part X: Publication

## 42. Publicationとは

Publicationは、完結判定が評価した確定済み作品状態から、コードだけで構築する読者向け成果物である。

Version 1には、独立したPublication Plan成果物またはPublication Plan生成Stageは存在しない。

Publicationは次の確定済み入力だけを使用する。

```text
Brief
採用済みSeries Plan
採用済みVolume Plan
採用済みChapter Plan
確定済みScene本文
Completion Result
```

Version 1では、各対象の採用済みPlanは正確に一件でなければならない。

少なくとも次を含む。

```text
シリーズ全体原稿
各巻の原稿
作品metadata
完結判定結果
```

---

## 43. Publicationの内容

Publicationの表示内容と順序は次のAuthorityから決定する。

```text
シリーズ名              Briefの仮題
巻数と巻順              Series Plan
巻タイトルと章順        Volume Plan
章タイトルとScene順     Chapter Plan
本文                    確定済みScene本文
完結状態と注意事項      Completion Result
```

Briefに仮題がない場合は、下位設計で定めた一つの決定的な代替表示名を使用する。

Publication作成時に、新しいScene、設定、人物の内面、結末、要約本文を追加してはならない。

Scene Planは執筆工程のAuthorityとして使用するが、Publicationの本文順はChapter PlanのScene順から決定する。

---

## 44. Publicationから除外するもの

Publicationへ次を含めない。

```text
内部Review
Revision指示
作者用の秘密情報
非公開のThread回答
Provider情報
利用量記録
内部Context
障害調査情報
```

---

## 45. Publicationの作成条件

次のすべてを満たす場合だけPublicationを作成する。

```text
Completion statusがcompleteまたはcomplete_with_issues
Completion Resultが正式に確定している
Completionが評価したPlan集合とScene集合が現在も同一
Completionが評価した各Scene本文と現在の確定済みScene本文が同一
全Sceneの確定由来を確認できる
未完了の採用、確定、Recovery処理がない
```

`incomplete`の場合はPublicationを作成しない。

Completion確定後にScene Card、Scene本文、継続性成果物、Scene Commit、Generationその他のPublication根拠が変更された場合は、Publicationを作成してはならない。

変更された成果物をCompletionが評価済みであるとみなさず、停止理由を示して人間確認を要求する。

---

## 46. `complete_with_issues`の表示

`complete_with_issues`でPublicationを作る場合は、残っている注意事項を利用者が確認できるようにする。

読者向け本文へ内部的な警告文を自動挿入してはならない。

---

## 47. 再作成

同じCompletion Resultと同じ確定済みPlanおよびSceneからPublicationを再作成した場合、file構成、本文の順序、本文内容、metadata上の根拠は同じでなければならない。

Publication作成または再作成で生成モデルを使用してはならない。

既に確定したPublicationと同じ内容である場合は冪等に扱う。異なる内容で上書きしてはならない。

既存Publicationまたはその入力に改変、欠落、競合がある場合は、自動的に内容を補完せず、人間確認を要求する。

---

# Part XI: 中断・失敗・再開

## 48. 通信失敗

外部Providerとの通信に失敗した場合は、設定された範囲で再試行できる。

再試行上限、timeout、Credential不足、Provider利用不能により新しいCallを継続できない場合は、確定済み成果物を保持し、run statusを`stopped`として停止する。

停止理由は、通信失敗、timeout、Credential不足、Provider利用不能を区別できなければならない。

Providerが利用可能になった後、同じworkspaceから再開できる。

---

## 49. 応答形式不正

外部Providerの応答が必要な形式を満たさない場合は、設定された範囲で再取得できる。

形式不正な応答を推測で補完して採用してはならない。

---

## 50. 意味的失敗

Reviewで解消できない矛盾や品質問題が残るCandidateを無理に採用してはならない。

Revision上限へ達した場合、または確定済みInitial DesignやPlanの変更が必要な場合は、run statusを`blocked`として停止する。

代表的な停止理由は次とする。

```text
revision_limit
design_change_required
plan_change_required
semantic_reject
completion_incomplete
```

利用者へ少なくとも次を示す。

```text
問題が発生した処理
対象となる巻・章・Scene
残っている問題
停止理由
再開または新規実行に必要な行動
```

---

## 51. Crash後の再開

予期しない終了後、Storycraftは起動時にRecoveryを実行し、次を区別する。

```text
確定済み状態からそのまま継続できる
唯一の完全な途中成果物を状態へ反映して継続できる
再生成可能な未採用途中作業を破棄して再実行できる
安全な自動判断ができず人間確認が必要
```

利用者が入力したBriefまたはKeywords、および既に確定した成果物をRecoveryで再生成してはならない。

不完全なCandidate、Review、Provider用一時Contextその他の再生成可能な途中作業を、完成した成果物として推測採用してはならない。

Recoveryが一意に完了できる場合は、同じRecoveryを繰り返しても新しいProvider call、成果物、識別子、利用量を増やしてはならない。

---

## 52. 人間確認が必要な状態

安全な自動判断ができない場合は、run statusを`failed`、停止理由を`manual_review_required`として停止する。

対象は次のようなworkspaceまたはAuthorityの不整合である。

```text
現在状態を読み取れない
現在状態が必要とする確定済み成果物が見つからない
同じ識別子の確定済み成果物が競合している
永続識別子の管理状態が既存成果物と矛盾している
確定済み成果物が外部変更され由来を確認できない
```

`incomplete`やRevision上限のように意味が確定している正常な停止を、人間確認が必要なRecovery失敗として扱ってはならない。

Storycraftは、データを隠れて作り直したり、過去へ巻き戻したりして問題を隠さない。

---

# Part XII: 設定と制限

## 53. Provider設定とCall監査

利用者は、operationごとに利用するProviderとmodelを設定できる。

workspace作成時に、利用する設定をversion付きの完全な設定として確定する。`resume`と`step`は保存済み設定を使用する。

各Provider callには、少なくとも次を記録する。

```text
call_id
operation_instance_id
attempt_number
処理Stageと対象
Providerとmodel
operation_config_id
prompt_version
output_schema_version
basis_generation_id
ContextおよびCandidateの識別情報
token preflightの見積値、予約出力値、上限、判定
開始時刻と終了時刻
usageまたはusage取得不能の明示
成功結果またはerror分類
```

Prompt version、Schema version、operation config versionは、同じ識別子から異なる内容へ暗黙に解決されてはならない。

Call監査へCredential、Authorization header、cookie、secret token、不要な本文全文を保存してはならない。

---

## 54. Retryとtimeout

利用者は、通信失敗、形式不正、Revisionについて上限を設定できる。

外部応答待ちにはtimeoutを設定できる。

Storycraftは、無制限に待機または再試行してはならない。

---

## 55. 利用量とtokenの制御

利用者は、次の利用上限を設定できる。

```text
Provider call数
入力token量
出力token量
推定費用
実処理経過時間
```

上限はworkspaceの一つの制作runに対して累積し、`resume`または`step`を跨いで引き継ぐ。

RetryとRevisionによるCallも利用量へ含める。

各Callの直前に、最終送信payloadの入力tokenと予約出力tokenを確認する。

Providerの正確なtokenizerを利用できない場合は、保守的な推定と安全余裕を使用する。安全に上限内と確認できない場合はCallを開始しない。

Providerからusageを取得できない場合もCall数へ算入する。入力tokenはpreflight見積値、出力tokenはローカル計測値を使用し、計測できない場合は予約出力上限を使用する。

費用上限を安全に算出できない場合は、新しい有料Callを開始せず、停止理由を`usage_unknown`として停止する。

実処理経過時間にはStorycraftが処理を実行している時間を含め、停止中に利用者操作を待つ時間は含めない。

上限到達時は新しいProvider callを開始せず、停止理由を`budget_limit`として`stopped`へ移行する。

Budget到達後も、検証済み成果物のatomic確定、Recovery、状態更新、Audit保存、安全停止など、Providerを必要としない処理は完了できる。

---

## 56. Credential

Credentialは、利用者の環境から取得する。

作品データ、Publication、通常の進捗表示へCredential値を含めない。

---

## 57. 外部情報

Version 1は、作品生成中に自動的なWeb検索、外部file取得、別会話memory取得を行わない。

Version 1の独立した外部資料入力は存在しない。

外部事実を作品へ使用する場合は、利用者がBriefまたはKeywordsの作品条件として必要情報を含める。

入力された外部事実の正確性、最新性、権利処理は利用者が確認する。

---

# Part XIII: 秘密情報と視点

## 58. 作者用情報

作品設計には、読者や登場人物へまだ公開されていない作者用情報が含まれることがある。

例:

```text
事件の真相
黒幕
人物の隠された目的
Endingの詳細
後の巻で明かす情報
```

作者用情報を本文生成や継続性判定へ無条件に渡してはならない。

情報の永続的な公開状態と、現在Sceneでの一時的な利用許可を区別する。

現在Sceneの執筆に必要で、Scene Cardが開示または利用を明示的に許可した情報だけをWriterへ渡せる。

Scene固有の利用許可だけで、その情報を読者へ開示済み、または登場人物が既知であるとは扱わない。

Credentialやsystem内部secretは作品上の作者用情報ではなく、Provider入力や作品成果物へ含めてはならない。

---

## 59. POV制約

Version 1では、一つのSceneに一つのPOVを指定する。

本文へ出せる情報は、指定POV人物が自然に知覚、記憶、認識、または推測できる範囲に限る。

非POV人物の非公開の思考、感情、意図を事実として断定してはならない。外見、発言、行動などの観察可能な情報と、POV人物による推測は区別して表現する。

Scene CardはPOV制約を緩和または上書きできない。

Version 1は、同一Scene内の全知視点や無表示のPOV切替を提供しない。

---

## 60. 開示制御

情報は、計画とScene Cardで許可された段階に従って開示する。

次を区別する。

```text
作品世界で真実か
各人物が何を知る、信じる、疑うか
読者へ本文上でどこまで開示済みか
現在SceneでWriterが利用できるか
```

Scene Cardは開示対象を次に分類する。

```text
required_revelations
allowed_revelations
forbidden_revelations
```

`required_revelations`は`allowed_revelations`に含まれなければならない。`forbidden_revelations`はrequiredおよびallowedと重複してはならない。

現在Sceneで開示を許可された情報は、そのSceneの執筆に必要な範囲でWriterへ渡せる。ただし、POV制約を破ってはならない。

将来読者へ開示され得る作者用情報は、KnowledgeまたはThreadなどの安定した識別対象へ関連付け、開示状態を追跡できなければならない。

読者への開示状態は確定済み作品状態としてScene間で引き継ぐ。計画上の予定やScene Cardの許可だけでは開示済みとして扱わない。

確定本文に対応するEvidenceがある場合だけ、読者への開示状態を更新する。

---

# Part XIV: 成果物の利用

## 61. 成果物の確認とpath境界

Storycraftの成果物は、人間が通常のfile browserとeditorで読んで確認できることを前提とする。

利用者は、少なくとも次を確認できる。

```text
入力
初期設計
計画
Scene Card
Scene本文
Review
継続性
Generation
Handoff
完結判定
Publication
```

CLIで利用者が明示するworkspace rootはabsolute pathでもよい。

作品入力、識別子、titleその他の作品データから導出する内部pathは、正規化後もworkspace root内に限定する。

次を拒否する。

```text
親directory traversal
作品データから導出されたabsolute path
symlinkを経由したworkspace外参照
正規化後にworkspace外となるpath
```

入力、Initial Design、Plan、Scene、Generation、Handoff、Completion、Publicationその他の確定成果物はimmutableとし、同じ識別子の異なる内容で上書きしてはならない。

永続JSON成果物は、自身のfieldまたは所属する成果物metadataから、適用されるschema versionを一意に識別できなければならない。

---

## 62. 手動編集

Version 1は、確定済み成果物の直接編集および編集済み成果物の正式な再取込を提供しない。

利用者が外部editorで確定済み成果物を変更した場合、そのworkspaceの整合性と再開可能性は保証されない。

Storycraftは、直接変更された成果物を新しいCandidateまたは新しいversionとして自動採用してはならない。

正式な手動編集取込は将来拡張とする。

---

## 63. バックアップ

Storycraftは、利用者のstorage障害、誤削除、端末紛失に対する完全なバックアップサービスではない。

利用者は、通常のバックアップまたはVersion管理を利用することが推奨される。

---

# Part XV: 製品としての保証

## 64. Version 1で保証すること

正しく設定された対応環境で、Storycraftは次を保証対象とする。

```text
一つの入力方式から作品を開始できる
4〜10巻の計画を作成できる
段階的にScene本文を生成できる
Reviewと未採用CandidateのRevisionを分離する
本文に基づいて継続性を更新する
制御された停止後に再開可能な状態を保持する
Crash後に安全な自動Recoveryが可能な場合は同じworkspaceから継続する
安全なRecoveryが不可能な場合は推測修復せず人間確認を要求する
未完結作品を自動的に完結扱いしない
採用済み本文からPublicationを作る
作者用秘密情報を本文から分離する
確定成果物を異なる内容で上書きしない
永続JSONのschema versionを識別できる
```

配布packageをinstallした環境では、repositoryの作業treeへ依存せず、実行に必要なPromptとSchema assetを解決できなければならない。

同じPrompt versionまたはSchema versionが、異なるasset内容へ暗黙に解決されてはならない。

ここでいう保証は仕様に従った振る舞いを意味し、文学的品質の絶対保証ではない。

制御された停止の再開保証は、workspace破損、確定済み成果物の外部変更、storage障害などのAuthority不明状態には適用しない。

---

## 65. Version 1で保証しないこと

Storycraftは次を保証しない。

```text
生成内容が常に面白い
事実関係が常に正確
差別的・不快な表現が完全に存在しない
利用者の意図を一度で完全に理解する
Providerが常に利用可能
同じPromptからProviderが同じ文面を返す
第三者が手動変更した成果物との整合性
複数processからの同時操作
```

---

## 66. 利用者の責任

利用者は、次を確認する責任を持つ。

```text
入力条件
生成本文
事実関係
著作権・商標・名誉・privacy
公開可否
費用
Provider利用規約
バックアップ
```

Storycraftは制作支援toolであり、最終的な作者・編集者・発行者ではない。

---

# Part XVI: Version 1の完成条件

## 67. 製品完成の基準

Storycraft Version 1は、production codeを使用する必須自動試験で、少なくとも次を確認できなければならない。

```text
Brief経路とKeywords経路
最低対応規模である4巻の全工程
全巻の全予定Scene
最終巻を含む全巻Handoff
Completionのcomplete
Completionのcomplete_with_issues
CompletionのincompleteとPublication禁止
Completionが評価したSceneとPublication入力の同一性
停止後のresume
stepのStage境界
代表StageのCrash Recovery
確定成果物のimmutable性
作者用秘密情報とPOV境界
Path境界
必須suiteのNetwork遮断
installed packageからのPromptとSchema解決
決定的なPublication作成
```

必須自動試験は、実Provider、実Credential、実network、長時間の実待機を必要としてはならない。

手動確認だけでVersion 1完成と判定してはならない。

---

## 68. Release前に確認する利用者体験

自動Release Gateの成功後、補助的な手動確認として次を確認する。

```text
新規利用者が開始方法を理解できる
途中停止後の再開方法を理解できる
blocked、stopped、failedの違いを理解できる
失敗理由と必要な行動が分かる
作品本文とPublicationを容易に読める
進捗が分かる
注意事項を確認できる
完成原稿を取得できる
```

手動確認は、自動試験の代替にはならない。

---

## 69. 将来拡張

次は将来候補であり、Version 1の必須範囲ではない。

```text
複数利用者の共同編集
remote storage
GUI
外部資料検索
引用管理
電子書籍出力
出版社向けworkflow
手動編集の正式な取込
確定済みInitial DesignおよびPlanの正式Revision
複数言語対応
外部監査や署名
```

将来拡張は、Version 1の単純性と信頼性を損なう形で先行実装しない。

---

## 70. 最終的な製品原則

Storycraftは、次の製品でなければならない。

> 利用者が作品の現在状態を理解でき、長編シリーズを段階的に生成でき、途中で止めても再開でき、本文に基づいて継続性を保ち、未完結作品を無理に公開しない、日本語長編制作CLI。
