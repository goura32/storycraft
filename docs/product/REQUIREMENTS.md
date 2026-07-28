# Storycraft 要件

この文書は、Storycraft Version 1が満たすべき検証可能な要件を定める。

上位文書:

- 製品仕様: [`SPECIFICATION.md`](SPECIFICATION.md)
- アーキテクチャ: [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)

実装状況は`IMPLEMENTATION_STATUS.md`、具体的な保存形式・処理手順・データ構造は`../design/`以下、Release判定に使う試験は`../testing/ACCEPTANCE.md`で定める。

---

# Part I: 文書の使い方

## 1. 要件の役割

この文書は「実装が何を満たすべきか」を定める。

次の詳細は定義しない。

```text
具体的なworkspace path
JSON field名
directory内のfile名
Python module
内部関数
Provider固有request
詳細なatomic write手順
```

これらは下位の設計文書で定める。

---

## 2. 要件ID

要件IDは次の形式とする。

```text
REQ-<分類>-<連番>
```

| 分類 | 意味 |
|---|---|
| `FR` | 機能 |
| `DATA` | データと保存 |
| `OPS` | 運用 |
| `REC` | 再開と復旧 |
| `SEC` | 安全性と秘密情報 |
| `NFR` | 非機能とRelease |

---

## 3. 必須度

この文書の要件は、明示がない限りすべてVersion 1の必須要件である。

すべてを`P0`など同じ優先度で表示する方式は使用しない。

実装順は次を優先する。

```text
永続状態と排他
Sceneの正常系
Crash後の再開
秘密情報の分離
完結判定
Publication
追加最適化
```

---

## 4. 仕様との追跡

各要件は、対応する`SPECIFICATION.md`の節を示す。

製品仕様に直接現れない内部整合性要件は、`ARCHITECTURE.md`の該当節を示す。

対応節は、上位文書の説明をこの文書へ再掲するためではなく、要件の根拠を確認するために使う。

---

# Part 2: 機能要件

## 5. 機能要件

| 要件ID | 要件 | 対応仕様節 | 主な確認方法 |
|---|---|---|---|
| `REQ-FR-001` | BriefまたはKeywordsから、日本語長編シリーズの初期設計、計画、Scene執筆、継続性管理、完結判定、Publication作成までを一つの制作工程として実行できなければならない。 | 1, 5, 18 | 全体試験 |
| `REQ-FR-002` | 一つのシリーズは4〜10巻で構成しなければならない。 | 7 | 入力・計画試験 |
| `REQ-FR-003` | 公開CLIの`run`は新しいworkspaceを作成して新規実行し、`resume`と`step`は既存workspaceだけを対象にしなければならない。 | 13〜15 | CLI境界試験 |
| `REQ-FR-004` | 新規実行は、既存作品を確認なしで上書きしてはならない。 | 13 | CLI・workspace試験 |
| `REQ-FR-005` | 再開時は、入力Stage途中を含め、workspaceに保存した元のBriefまたはKeywordsを使用し、利用者へ再入力を要求してはならない。 | 12, 14 | 入力・再開試験 |
| `REQ-FR-006` | `step`は一つの意味的Stageだけを完了して終了しなければならない。起動時RecoveryでCrash前のStageが完了した場合はそこで終了し、次Stageを追加実行してはならない。 | 15 | Stage境界・Recovery試験 |
| `REQ-FR-007` | 新規実行時に外部から指定する入力はBriefまたはKeywordsの正確に一方でなければならない。Keywordsと生成途中のBrief Candidateの内部共存は同時入力として扱ってはならない。 | 9, 12 | 入力Authority試験 |
| `REQ-FR-008` | 採用対象Briefにpremise不足または巻数範囲外がある場合、もしくは外部入力の必須条件と避ける内容に明示的矛盾がある場合は、後続の作品生成を開始せず問題を利用者へ示さなければならない。外部入力だけで決定できる不正はProvider call前に拒否しなければならない。 | 7, 10〜12 | 入力検証試験 |
| `REQ-FR-009` | Keywordsから生成したBriefは、必須Keyword、避ける内容、Endingの希望、巻数の希望、補足条件およびnotesを保持し、採用時点で4〜10のvolume_countと日本語を確定していなければならない。明示条件はコードで検証し、premise・Ending・avoidの実質的整合と日本語品質は必須のLLM Reviewで確認し、error時はRevision後に再Reviewしなければならない。 | 10, 11, 26〜28 | Brief生成・条件保持・Review試験 |
| `REQ-FR-010` | 初期設計は、Concept、主要人物、主要Relationship、世界、Knowledge、主要Thread、Endingの方向、長期的な人物変化を含む一つの整合した作品設計でなければならない。 | 19 | 初期設計試験 |
| `REQ-FR-011` | シリーズ計画は、各巻の役割、主人公変化、主要Relationship変化、主要Thread進行、重要な開示、危機の拡大、Endingへの到達を定義しなければならない。 | 20 | シリーズ計画試験 |
| `REQ-FR-012` | 巻計画は、シリーズ計画に加え、巻開始時の実際の作品状態と前巻Handoffを参照しなければならない。 | 21, 36 | 巻計画試験 |
| `REQ-FR-013` | 章計画は一つの対象章を順序付きScene概要へ具体化し、各Scene計画はそのうち一つのSceneだけをScene開始直前の採用済み作品状態から具体化しなければならない。 | 22 | 章・Scene計画単位試験 |
| `REQ-FR-014` | Version 1は採用済みPlanを変更または置換してはならない。変更が必要な場合は既存Planを保持して停止し、変更理由と新しいworkspaceが必要であることを利用者へ示さなければならない。 | 20〜22, 32 | 採用済みPlan不変性試験 |
| `REQ-FR-015` | Scene Cardは、単一POV、参加人物、場所、目的、開始状況、必須beat、Conflict、required／allowed／forbidden revelation、許可する継続性更新、終了時の変化を定義しなければならない。required revelationはallowedに含まれ、forbiddenと重複してはならない。 | 23, 59, 60 | Scene Card・開示制約試験 |
| `REQ-FR-016` | 本文生成へ渡す情報は、そのSceneの執筆に必要で、現在Sceneで利用を許可された情報へ限定しなければならない。Scene固有の許可によってPOV制約または永続的な公開状態を上書きしてはならない。 | 24, 58〜60 | Writer入力・POV境界試験 |
| `REQ-FR-017` | Scene本文は自然な日本語散文でなければならない。JSONその他の内部構造化データ、内部識別子、Review結果、Provider・Prompt・Schema・Budget・Audit情報、実装metadata、生成指示を例外なく本文へ含めてはならない。 | 24 | 本文内部情報禁止試験 |
| `REQ-FR-018` | 一つのSceneでは、Scene計画、Scene Card、本文、継続性更新、Scene確定が完了するまで同じGenerationを基準にし、関連入力が変化した古い候補を採用してはならない。 | 25 | Scene基準状態試験 |
| `REQ-FR-019` | 継続性更新は、確定対象の本文に実際に書かれた現在状態の変化と読者への開示だけを反映しなければならない。 | 30, 31, 60 | 継続性試験 |
| `REQ-FR-020` | 継続性更新は、Scene Cardで許可され、現在状態に存在する対象とfieldだけを変更しなければならない。Version 1は人物、Relationship、Location、World、Thread、人物Knowledge、読者開示、時間、重要物品、約束・義務の状態を扱えなければならない。 | 30, 32 | 許可更新・状態種別試験 |
| `REQ-FR-021` | 通常Sceneの継続性更新はCanon、Initial Design、採用済みPlan、Ending Design、World Rule、新しい主要Thread定義、重要人物の過去の真相を変更してはならない。これらの変更が必要なCandidateは採用せず、確定済み成果物を変更しないまま停止理由を利用者へ示さなければならない。 | 32 | 禁止更新・安全停止試験 |
| `REQ-FR-022` | 継続性更新の各変更には、対象Scene、本文引用と出現位置、更新対象、変更前後、変更理由を確認できるEvidenceを必ず関連付けなければならない。 | 33 | Evidence試験 |
| `REQ-FR-023` | 本文が曖昧で状態変化を一意に判断できない場合は変更してはならない。不確定値は対象fieldの契約と本文Evidenceがある場合だけ許可し、それ以外はReview後に人間確認を要求しなければならない。 | 34 | 曖昧性試験 |
| `REQ-FR-024` | ReviewはCandidateを書き換えず、Issueをerror、warning、noteへ分類しなければならない。errorは採用を禁止し、warningとnoteだけの場合は採用可能だが利用者が確認できなければならない。 | 26, 28 | Review severity・採用境界試験 |
| `REQ-FR-025` | Revisionはerrorを持つ未採用Candidateの完全な置換候補を返し、Revision後に再Reviewしなければならない。warningまたはnoteだけを理由にRevision回数を消費してはならず、確定成果物をRevision対象としてはならない。 | 27, 28 | Candidate Revision・再Review試験 |
| `REQ-FR-026` | 通信失敗、形式不正、意味的Revisionは区別し、それぞれ独立した上限を使用しなければならない。形式不正を意味的Reviewへ渡したり推測補完したりしてはならない。 | 28, 29, 48〜50, 54 | Retry分類・形式境界試験 |
| `REQ-FR-027` | errorがRevision上限後も残る場合、または同じoperation内で修正不能な場合はCandidateを採用せず`blocked`として停止し、`revision_limit`、`semantic_reject`その他の安定した停止理由を示さなければならない。 | 28, 50 | Revision上限・reject遷移試験 |
| `REQ-FR-028` | 最終巻を含む各巻終了時に、巻末Generation、確定Scene、Evidence、採用済みPlanから構築したsource bundleを根拠に、LLM生成・Review・必要時Revisionを通したHandoffを作成し、次巻計画または完結判定へ引き渡さなければならない。Handoffの主張は出典へ解決できなければならない。Generationを詳細Authority、Handoffを補助要約とし、Handoffから状態を復元または上書きしてはならない。 | 35, 36 | 全巻Handoff・根拠・品質ループ試験 |
| `REQ-FR-029` | 完結判定は、各対象の採用済みPlanが一件に確定し、全巻、全予定Scene、全巻Handoff、最終Generation、主要Thread、Ending条件、主要Arcを評価でき、未完了処理がない場合だけ実行しなければならない。 | 37, 38 | 完結開始条件・集合一致試験 |
| `REQ-FR-030` | 完結判定は`complete`、`complete_with_issues`、`incomplete`のいずれかを返し、Thread、Ending、Character Arc、Relationship Arc、Issueとのcross-field条件を満たさなければならない。結果は独立したLLM Reviewを受ける。意味的な`incomplete`を`complete`になるまで再試行してはならず、Revisionでstatus、各Checkの判定、評価対象ID集合またはEvidenceの意味を変更してはならない。 | 39, 40 | 完結cross-field・Review境界試験 |
| `REQ-FR-031` | Publicationは、Completionが`complete`または`complete_with_issues`であり、Completionが評価したPlan集合、Scene集合、Scene内容および確定由来が現在も同一である場合だけ作成しなければならない。 | 42, 43, 45 | Publication入力同一性試験 |
| `REQ-FR-032` | `complete_with_issues`でPublicationを作成する場合は、残る非blockingの注意事項を利用者が確認できるようにし、読者向け本文へ内部警告を自動挿入してはならない。 | 39, 46 | Publication注意事項試験 |
| `REQ-FR-033` | Publicationは、Brief、採用済みPlan階層、確定済みScene本文、Completion Resultからコードだけで決定的に構築し、新しいScene、設定、人物の内面、結末、要約本文を追加してはならない。 | 42, 43, 47 | Publication決定性・Provider非依存試験 |
| `REQ-FR-034` | Publicationには、内部Review、Revision指示、作者用秘密情報、Provider情報、利用量記録、内部Context、障害調査情報を含めてはならない。既存Publicationまたは入力の競合を自動補完してはならない。 | 44, 47 | Publication公開範囲・競合試験 |

# Part 3: データ・保存要件

## 6. データ・保存要件

| 要件ID | 要件 | 対応仕様節 | 主な確認方法 |
|---|---|---|---|
| `REQ-DATA-001` | 現在のrun状態を表す変更可能な正本は一つだけでなければならない。その正本は`run status`と`current_stage`を別の値として保持し、`current_stage`へ`stopped`、`blocked`、`failed`、`completed`などのrun status値を格納してはならない。 | 14, 17, 51, 52 | Run状態Authority・Stage分離試験 |
| `REQ-DATA-002` | 変更可能な永続状態は、部分的な書換えではなく完全な状態として安全に更新しなければならない。 | 14, 51 | 状態更新Crash試験 |
| `REQ-DATA-003` | 複数ファイルで構成される成果物は、不完全な構成を確定済みとして観察できない方法で確定しなければならない。 | 51, 52 | 成果物確定Crash試験 |
| `REQ-DATA-004` | 入力、Initial Design、Plan、Scene成果物、Generation、Handoff、Completion、Publicationその他の全確定成果物はimmutableでなければならず、同じ識別子の異なる内容で上書きしてはならない。 | 25, 35, 39, 47, 61, 62 | 確定成果物不変性試験 |
| `REQ-DATA-005` | Evidenceは、対象Scene、本文引用、更新対象、変更内容を識別できなければならない。 | 33 | Evidence形式試験 |
| `REQ-DATA-006` | Hashは、具体的な利用目的、検出後の処理、より単純な代替がない理由を説明できない限り、永続データ契約へ含めてはならない。 | 製品仕様外・アーキテクチャ12 | 設計レビュー |
| `REQ-DATA-007` | 同じ現在状態を表す複数の独立pointer、Manifest、Gateを正本として使用してはならない。 | 製品仕様外・アーキテクチャ13〜14 | Authority構成試験 |
| `REQ-DATA-008` | 永続識別子は必要な種類だけを単調に割り当て、失敗により未使用となった番号を再利用してはならない。 | 51, 52 | ID試験 |

# Part 4: 運用要件

## 7. 運用要件

| 要件ID | 要件 | 対応仕様節 | 主な確認方法 |
|---|---|---|---|
| `REQ-OPS-001` | 一つのworkspaceへ同時に書き込めるprocessは一つだけでなければならない。 | 3, 65 | 排他試験 |
| `REQ-OPS-002` | Version 1はローカルfilesystem上の単一利用者workspaceを動作対象としなければならない。 | 3, 6 | 対応環境試験 |
| `REQ-OPS-003` | workspace作成時に利用する設定を一つの完全な設定として確定し、`resume`と`step`では保存済み設定を引き継がなければならない。 | 13〜15, 53〜55 | 設定固定試験 |
| `REQ-OPS-004` | 利用者は、処理の種類ごとに利用するProviderまたはmodelを設定できなければならない。 | 53 | Provider設定試験 |
| `REQ-OPS-005` | Credentialはworkspaceへ保存せず、利用者環境の外部sourceから取得しなければならない。 | 56 | Credential試験 |
| `REQ-OPS-006` | 外部Providerとの通信には、接続、応答開始、応答停止、処理全体を制限できるtimeoutを設定できなければならない。 | 48, 54 | Timeout試験 |
| `REQ-OPS-007` | Call数、token量、推定費用、実処理経過時間の上限をworkspaceの制作run全体で累積し、`resume`と`step`を跨いで引き継がなければならない。上限は新しいProvider call前に確認し、到達後もcode-onlyの確定、Recovery、状態更新、安全停止を妨げてはならない。 | 55 | Budget累積・code-only試験 |
| `REQ-OPS-008` | 各Provider callは、Call・operation・attempt・対象・Provider・model・設定・Prompt・Schema・basis Generation・Context・Candidate・token preflight・時刻・usage・結果またはerrorを識別できる監査記録を残さなければならない。秘密情報と不要な本文全文を記録してはならない。 | 53〜56 | Call監査・redaction試験 |
| `REQ-OPS-009` | 進捗表示は、run statusと意味的なcurrent Stageを区別し、巻・章・Scene、完了範囲、停止理由、再開可否、完結判定、Publication結果を利用者が理解できる形で示さなければならない。 | 17 | 進捗表示・状態分離試験 |
| `REQ-OPS-010` | 利用者による停止要求受付中の`stopping`と、安全な処理境界で停止が完了した`stopped`を区別し、停止完了時には同じworkspaceから再開可能な状態を残さなければならない。 | 16 | 停止状態・再開試験 |

# Part 5: 再開・復旧要件

## 8. 再開・復旧要件

| 要件ID | 要件 | 対応仕様節 | 主な確認方法 |
|---|---|---|---|
| `REQ-REC-001` | 起動時は、排他状態、現在の実行状態、必要な確定済み成果物、途中作業の有無を確認しなければならない。 | 14, 51 | 起動確認試験 |
| `REQ-REC-002` | 現在状態を読み取れ、必要な確定済み入力が存在する場合は、安全に判断できる位置から再開しなければならない。 | 14, 51 | 再開試験 |
| `REQ-REC-003` | 不完全な未採用Candidate、Review、Provider用一時Context、複数file成果物の未確定stagingを推測採用してはならない。必要な場合は再生成できる途中作業だけを再実行し、利用者入力と確定済み成果物を再生成してはならない。 | 51 | Recovery再生成境界試験 |
| `REQ-REC-004` | 成果物の確定後、現在状態への反映前に中断した場合は、予定された唯一の完全な成果物であると確認できるときだけ現在状態へ反映して再開しなければならない。 | 51 | 確定直後Crash試験 |
| `REQ-REC-005` | 現在状態を安全に読み取れない場合は、run statusを`failed`、停止理由を`manual_review_required`として停止し、自動的に推測修復してはならない。 | 52 | 状態破損・状態分類試験 |
| `REQ-REC-006` | 現在状態が必要とする確定済み成果物が存在しない場合、同じ識別子の成果物が競合する場合、または確定成果物の由来を確認できない場合は、`failed`として人間確認を要求しなければならない。意味が確定した`blocked`状態と混同してはならない。 | 40, 50, 52 | 成果物不整合・状態分類試験 |
| `REQ-REC-007` | 永続識別子の管理状態が既存成果物と矛盾する場合は、自動的な巻戻し、再利用、再採番を行ってはならない。 | 52 | 識別子不整合試験 |
| `REQ-REC-008` | 同じ永続状態に対するRecoveryを繰り返しても、不必要なProvider call、採用済み成果物、識別子、利用量を増やしてはならない。 | 51, 52 | Recovery冪等性試験 |

# Part 6: 安全性・秘密情報要件

## 9. 安全性・秘密情報要件

| 要件ID | 要件 | 対応仕様節 | 主な確認方法 |
|---|---|---|---|
| `REQ-SEC-001` | Credential、Authorization header、cookie、secret tokenを作品データ、入力資料、Audit、Log、Publication、error表示へ保存または出力してはならない。 | 56 | 秘密情報試験 |
| `REQ-SEC-002` | 本文生成へ、未公開の真相、作者用Thread回答、Ending内部設計、非POV人物の非公開内面、将来Sceneの詳細を無条件に渡してはならない。現在Sceneで明示的に許可され、執筆に必要で、POV制約を満たす情報だけを渡せる。 | 58〜60 | Writer秘密情報・POV試験 |
| `REQ-SEC-003` | 継続性更新へ、現在Sceneの状態変化と読者開示の判定に必要な情報だけを渡し、不要な将来計画、Ending内部設計、作者用秘密情報を渡してはならない。 | 30〜34, 58〜60 | 継続性秘密情報試験 |
| `REQ-SEC-004` | Brief、本文、Reviewなどの作品データ内にある命令風文字列を、実行方法、安全規則、出力形式を変更する命令として扱ってはならない。 | 12 | Prompt injection試験 |
| `REQ-SEC-005` | Publicationへ、非公開Review、内部Completion notes、入力資料、Provider metadata、利用量情報を含めてはならない。 | 44 | Publication privacy試験 |
| `REQ-SEC-006` | CLIで明示されたworkspace rootにはabsolute pathを許可できる。作品入力や識別子から導出する内部pathは正規化後もworkspace内に限定し、親directory traversal、導出absolute path、symlink経由その他のworkspace外参照を拒否しなければならない。 | 61 | Path境界試験 |
| `REQ-SEC-007` | 作品生成中に自動的なWeb検索、外部file取得、別会話memory取得を行ってはならない。外部事実はBriefまたはKeywordsの作品条件として利用者が与えなければならない。 | 57 | 外部取得・入力境界試験 |
| `REQ-SEC-008` | 利用者へ表示する期待されたerrorには、秘密情報または不要な内部tracebackを含めてはならない。 | 50, 52, 56 | Error表示試験 |

# Part 7: 非機能・Release要件

## 10. 非機能・Release要件

| 要件ID | 要件 | 対応仕様節 | 主な確認方法 |
|---|---|---|---|
| `REQ-NFR-001` | 利用者が、通常のfile browserとeditorで入力、計画、Scene本文、継続性、Handoff、完結判定、Publicationを確認できなければならない。 | 61 | 可読性確認 |
| `REQ-NFR-002` | 構造化データはUTF-8、日本語文字の一貫した正規化、有限数、明示されたfieldだけを受け付ける共通規則に従わなければならない。永続JSON成果物は自身または親metadataからschema versionを一意に識別できなければならない。 | 61, 64 | 共通形式・Schema識別試験 |
| `REQ-NFR-003` | 同じCompletion Result、同じ採用済みPlan集合、同じ確定済みScene集合およびScene内容からPublicationを再作成した場合、file構成、本文の順序、本文内容、metadata上の根拠を決定的に再構成できなければならない。 | 42, 43, 47 | Publication再現試験 |
| `REQ-NFR-004` | 外部Providerへ渡す入力資料は処理に必要な情報へ限定し、作品全体の無制限な読込み、未許可の秘密情報、POV外の非公開情報を含めてはならない。 | 16, 58〜60 | 入力資料量・秘密境界試験 |
| `REQ-NFR-005` | 各Provider callは最終payloadの入力tokenと予約出力tokenを開始前に確認しなければならない。正確なtokenizerがない場合は保守的推定を使用し、安全な上限を確認できない場合はCallを開始してはならない。usage欠落時は保守値をBudgetへ算入しなければならない。 | 53, 55 | Token preflight・usage欠落試験 |
| `REQ-NFR-006` | 必須自動試験は実Credentialと実時間の長い待機を必要としてはならない。また、標準の必須suite実行経路で実network接続を遮断し、予期しないnetwork接続を試験失敗として検出しなければならない。 | 64, 67, 68 | Hermetic・Network遮断試験 |
| `REQ-NFR-007` | 配布packageをinstallした環境だけで、repository作業treeへ依存せず、実行に必要なPromptとSchema assetをversion識別子から一意に解決できなければならない。同じversionが異なるasset内容へ暗黙に解決されてはならない。 | 64, 67 | Package asset・version試験 |
| `REQ-NFR-008` | Release前に、4巻全工程、全Sceneと全Handoff、Completion三状態、Publication入力同一性、Review／Revision、停止・step・Crash Recovery、秘密・POV・Path境界、immutable成果物、Network遮断、installed package、決定的Publicationをproduction codeによる必須自動試験で確認しなければならない。手動確認だけでReleaseしてはならない。 | 67, 68 | Release必須suite |

# Part 8: 管理

## 11. 要件数

| 分類 | 範囲 | 件数 |
|---|---|---:|
| `FR` | `REQ-FR-001`〜`REQ-FR-034` | 34 |
| `DATA` | `REQ-DATA-001`〜`REQ-DATA-008` | 8 |
| `OPS` | `REQ-OPS-001`〜`REQ-OPS-010` | 10 |
| `REC` | `REQ-REC-001`〜`REQ-REC-008` | 8 |
| `SEC` | `REQ-SEC-001`〜`REQ-SEC-008` | 8 |
| `NFR` | `REQ-NFR-001`〜`REQ-NFR-008` | 8 |
| **合計** |  | **76** |

## 12. 実装状況との分離

この文書へ実装済み、部分実装、未実装の状態を書かない。

実装状況は`IMPLEMENTATION_STATUS.md`へ記録する。

次だけでは要件を満たしたことにならない。

```text
設計書へ記載した
似た名前のfieldが存在する
V1の正規test suiteが通る
正常系だけ動く
手動確認だけを行った
```

要件を満たしたと判断するには、production codeと対応する自動試験が必要である。

## 13. 下位設計の制約

下位設計は、この文書の要件を満たす範囲で具体的なpath、field、処理順を決定する。

下位設計は次を行ってはならない。

```text
製品仕様を狭める
新しい利用者制約を暗黙に追加する
複数の現在状態authorityを作る
HashやManifestを根拠なく必須化する
Acceptance文書だけで新しい仕様を追加する
```

## 14. 変更管理

要件を変更する場合は、次の順で確認する。

1. `SPECIFICATION.md`の利用者向け意味が変わるか確認する。
2. `ARCHITECTURE.md`の原則と矛盾しないことを確認する。
3. 対応する設計文書を更新する。
4. 対応する自動試験を更新する。
5. `IMPLEMENTATION_STATUS.md`を更新する。
6. 最後にREADMEを更新する。

既存実装へ合わせるためだけに必須要件を弱めてはならない。

## 15. この文書の受入条件

この文書は次を満たさなければならない。

```text
要件IDが一意
分類内に欠番がない
合計76件
各要件が検証可能
各要件に上位文書の根拠がある
具体pathやJSON fieldを要件として固定していない
Hash、Manifest、Gateを根拠なく再導入していない
単一writer・ローカルfilesystem前提と一致する
実装状況を記載していない
```

---

## 16. 要件追加時の確認

新しい要件を追加する前に、次を確認する。

```text
利用者または実装のどの問題を解決するか
既存要件と重複していないか
製品仕様に根拠があるか
単一writerでも必要か
ローカルfilesystemでも必要か
下位設計だけで解決できないか
自動試験で確認できるか
```

説明できない要件は追加しない。
