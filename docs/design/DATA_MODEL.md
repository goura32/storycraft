# Storycraft データモデル

この文書は、Storycraft Version 1が扱う物語データの意味、関係、不変条件を定める。

上位文書:

- 製品仕様: [`../product/SPECIFICATION.md`](../product/SPECIFICATION.md)
- 製品要件: [`../product/REQUIREMENTS.md`](../product/REQUIREMENTS.md)
- アーキテクチャ: [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)

関連する下位文書:

- 保存形式と復旧: `WORKSPACE_AND_RECOVERY.md`
- 処理順とStage: `PIPELINE.md`
- LLMへの入力と応答: `LLM_INTEGRATION.md`
- Release試験: `../testing/ACCEPTANCE.md`

この文書は、具体的なworkspace path、atomic write手順、Provider request、Python class配置を定義しない。

---

# Part I: 基本方針

## 1. データモデルの目的

Storycraftのデータモデルは、長編シリーズについて次を明示する。

```text
何が作品世界の確定事実か
現在どの状態にあるか
誰が何を知っているか
どのThreadが進行中か
どのEnding条件を目指すか
何を計画しているか
各Sceneで何が実際に起きたか
どの本文表現を根拠に状態を更新したか
シリーズが完結しているか
何を読者向けに公開するか
```

データモデルは、LLMの自由記述をそのまま正本にするためのものではない。

生成結果を、後続処理が一貫して解釈できる明示的な構造へ整理する。

---

## 2. この文書の責務

この文書が正本となる領域:

```text
物語データの意味
データ同士の関係
必須となる概念
主要な項目
状態遷移上の不変条件
公開情報と作者用情報の区別
代表的な値の例
```

この文書が正本ではない領域:

```text
保存directory
file名
atomic rename
Crash後の復旧
Stage順
Prompt文面
Provider API
試験scenario
```

---

## 3. データの分類

Storycraftのデータは、次の五分類へ分ける。

| 分類 | 意味 | 例 |
|---|---|---|
| 入力 | 利用者が与える作品条件 | Keywords、Brief |
| 設計 | 作品全体の作者用設計 | Concept、人物、World、Thread、Ending |
| 計画 | 将来の執筆方針 | Series plan、Volume plan、Chapter plan、Scene plan |
| 採用済み状態 | 本文に基づく確定状態 | Canon、State、Evidence、Generation |
| 出力 | 読者または利用者向け成果物 | Scene本文、Handoff、Completion、Publication |

未採用Candidate、Review、Revisionは作業データであり、作品世界の正本ではない。

---

## 4. Authority

Authorityは、情報の種類ごとに一つだけ定める。全データへ共通する単純な優先順位は設けない。

| 問い | Authority | 補足 |
|---|---|---|
| Sceneで何が描写されたか | 採用済みScene本文 | Plan、Review、要約より優先する |
| どの本文表現を根拠に状態を変更したか | 採用済みContinuity UpdateとEvidence | 本文を変更した場合は再生成する |
| 現在の作品状態は何か | 現在GenerationのState | 過去Generationや表示用summaryを正本にしない |
| 安定した設定・過去の確定事実は何か | 現在GenerationのCanon | 通常Sceneでは変更しない |
| 今後の執筆予定は何か | 対象に対する最新の採用済みPlan | 予定であり、本文上の事実ではない |
| 現在の実行位置はどこか | `run-state.json` | Generationや成果物内に重複pointerを持たない |

同じ値を検索・表示のために導出してよいが、導出値はAuthorityへの参照元を持ち、独立して更新してはならない。

---

## 5. 計画と事実の分離

Planに書かれた予定を、本文に書かれた事実として扱ってはならない。

例:

```text
Plan:
  主人公が鍵を妹へ渡す

本文:
  主人公は鍵を握ったまま、渡せずにSceneが終わる
```

この場合、Stateは「鍵を主人公が所持している」のままである。

Planと本文が異なる場合は、採用済み本文を優先する。

---

## 6. 公開情報と作者用情報

各データは、少なくとも次の情報区分を意識する。

```text
reader_visible:
  現時点で読者が知ってよい

character_visible:
  特定人物が知ってよい

writer_private:
  作者と計画処理だけが知る

system_private:
  実行制御だけに必要
```

Version 1では、すべての項目へ機械的なvisibility fieldを付ける必要はない。

ただし、Context Builderが公開範囲を判断できるよう、秘密情報の所在は明示しなければならない。

---

## 7. データの不変性

利用者入力、Initial Design、Plan、Scene成果物、Generation、Volume Handoff、Completion Result、Publicationその他の確定済み成果物はimmutableとする。

同じ識別子または同じversionの異なる内容で上書きしてはならない。

Version 1は、確定済みInitial Design、採用済みPlan、確定済みSceneその他の確定成果物をRevisionしない。

未採用CandidateのRevisionは、新しいCandidate versionとして作成し、旧Candidateを変更しない。

確定済み成果物が外部変更された場合は、新しい正式版として自動採用せず、Authority不整合として扱う。

---

## 8. Hashを識別子にしない

Version 1では、データ内容のHashを主要識別子にしない。

次をHashで表さない。

```text
Candidate identity
Context identity
Scene identity
Generation identity
Publication identity
Review identity
```

識別には、人間が追跡可能な永続IDと版番号を使う。

---

# Part II: 共通データ規則

## 9. JSONの基本規則

構造化データは原則としてJSONで表現する。

共通規則:

- UTF-8
- Unicode NFC
- 改行はLF
- 数値は有限値
- 日時はtimezoneを含む
- 未知項目は拒否
- 必須項目の省略は禁止
- 同じ意味を複数fieldへ重複保存しない

永続JSON成果物は、自身の`schema_version`または親metadataから、適用するSchema versionを一意に識別できなければならない。

同じSchema version識別子を異なるSchema内容へ解決してはならない。

厳密なSchemaは実装assetとして一元管理し、productionとtestで共用する。

---

## 10. 項目名

JSONの項目名は`snake_case`を使用する。

例:

```json
{
  "character_id": "char-mio",
  "current_location_id": "loc-lighthouse",
  "updated_at": "2026-07-23T12:00:00Z"
}
```

略語や同義語を乱立させない。

---

## 11. 識別子

永続データの識別子は文字列とする。

推奨形式:

```text
<kind>-<stable-name>
<kind>-<zero-padded-number>
```

例:

```text
char-mio
rel-mio-nagi
loc-lighthouse
thread-missing-memory
scene-v01-c001-s002
gen-000012
pub-000001
```

識別子は表示名と分離する。

表示名を変更しても、識別子を変更しない。

---

## 12. 版番号

未採用CandidateをRevisionする場合は、新しい単調増加versionを割り当てる。

版番号は1から始まり、失敗やrejectによって未使用となった番号を再利用しない。

Revision後も旧Candidate versionを変更または削除しない。

確定済みInitial Design、採用済みPlan、確定済みSceneその他の確定成果物には、Version 1のRevision用version系列を設けない。

---

## 13. 日時

永続日時は、ISO 8601形式のUTCを基本とする。

例:

```text
2026-07-23T12:00:00Z
```

作品世界内の時間と、システム上の作成日時を混同しない。

```text
created_at:
  システム日時

story_time:
  作品内日時
```

---

## 14. 並び順

意味のある順序は、配列順だけへ暗黙依存せず、必要に応じて明示する。

例:

```json
{
  "volume_number": 1,
  "chapter_number": 2,
  "scene_number": 3
}
```

同じ番号の要素を重複させない。

---

## 15. 空値

「不明」「該当なし」「まだ決まっていない」を区別する。

推奨:

```text
null:
  値が未確定または不明

空配列:
  対象が存在しないことを確認済み

項目省略:
  原則禁止
```

自由記述で「なし」「不明」と書くだけにしない。

---

## 16. 参照

別データを参照する場合は、表示名ではなく永続IDを使う。

例:

```json
{
  "pov_character_id": "char-mio",
  "location_id": "loc-lighthouse"
}
```

必要な表示名は参照先から取得する。

---

## 17. 自由記述

自由記述は、説明が必要な場所へ限定する。

自由記述だけで次を表現してはならない。

```text
status
識別子
順序
公開範囲
対象人物
対象Thread
更新操作
```

これらは構造化項目で表す。

---

## 18. 列挙値

状態や分類は、定義済み列挙値を使用する。

列挙値は英小文字の`snake_case`を基本とする。

例:

```text
planned
active
resolved
abandoned
complete
complete_with_issues
incomplete
```

自由記述の似た表現を増やさない。

---

# Part III: 入力モデル

## 19. Keywords入力

Keywords入力は、短い作品条件からBriefを作るための入力である。

主要項目:

| 項目 | 意味 |
|---|---|
| `keywords` | 必ず作品設計へ反映する語句 |
| `avoid` | 避ける内容 |
| `ending_preference` | 結末の方向 |
| `volume_hint` | 希望巻数 |
| `language` | 基本生成言語 |
| `notes` | 補足 |

代表例:

```json
{
  "keywords": [
    "海辺の町",
    "失われた記憶",
    "姉妹",
    "静かな恐怖"
  ],
  "avoid": [
    "露悪的な残虐描写"
  ],
  "ending_preference": "救いのある結末",
  "volume_hint": 4,
  "language": "ja",
  "notes": null
}
```

---

## 20. Brief

Briefは、作品制作の利用者向け入力正本である。

主要項目:

| 項目 | 意味 |
|---|---|
| `title` | 仮題 |
| `genre` | ジャンル |
| `audience` | 想定読者 |
| `tone` | 雰囲気 |
| `premise` | 中心設定 |
| `central_question` | 作品全体の問い |
| `required_elements` | 必須要素 |
| `avoid` | 禁止・回避要素 |
| `ending_preference` | 結末の方向 |
| `volume_count` | 巻数 |
| `style_preferences` | 文体希望 |
| `user_notes` | 補足 |

Briefは、作者用の詳細設計ではない。

---

## 21. Briefの不変条件

Briefは次を満たす。

```text
volume_countは4〜10
required_elementsとavoidが直接矛盾しない
ending_preferenceがavoidと矛盾しない
languageはVersion 1ではja
作品開始に必要なpremiseが存在する
```

KeywordsからBriefを生成した場合、元Keywordsの必須条件を失ってはならない。

---

## 22. 入力由来

Briefがどの方式で作られたかを識別できるようにする。

推奨:

```text
source_type:
  brief
  keywords

source_reference:
  入力artifactの識別子
```

入力本文そのものを複数箇所へ複製しない。

---

# Part IV: 初期設計モデル

## 23. Initial Design

Initial Designは、シリーズ全体の作者用設計を統合した採用済みデータである。

構成:

```text
Story Concept
Characters
Relationships
World
Locations
World Rules
Knowledge Facts
Threads
Ending Design
Long-term Arcs
```

個別Candidateを採用するだけではなく、相互矛盾を解消した統合版を作る。

---

## 24. Story Concept

Story Conceptは、作品の中心的な意味を定義する。

主要項目:

| 項目 | 意味 |
|---|---|
| `logline` | 一文の作品説明 |
| `premise` | 中心設定 |
| `central_question` | シリーズを通す問い |
| `themes` | 主要テーマ |
| `dramatic_engine` | 物語を継続的に動かす仕組み |
| `tone` | 基本的な語りの雰囲気 |
| `reader_promise` | 読者が期待できる体験 |
| `ending_direction` | 結末の方向 |

Conceptは具体的なScene順を定義しない。

---

## 25. Character

Characterは、継続的に追跡する人物を表す。

主要項目:

| 項目 | 意味 |
|---|---|
| `character_id` | 永続ID |
| `name` | 表示名 |
| `aliases` | 別名 |
| `role` | 物語上の役割 |
| `public_profile` | 読者へ公開可能な人物概要 |
| `private_profile` | 作者用の非公開概要 |
| `desires` | 欲求 |
| `fears` | 恐れ |
| `misbeliefs` | 誤った信念 |
| `strengths` | 強み |
| `weaknesses` | 弱み |
| `long_term_arc` | 長期変化 |
| `initial_state` | 開始時状態 |

`initial_state`はInitial Generationを作るための初期値であり、Scene進行後の現在値ではない。`private_profile`を本文Contextへ無条件に渡してはならない。

---

## 26. Character Role

`role`は、計画とContext選択を補助する。

推奨値:

```text
protagonist
co_protagonist
antagonist
supporting
minor
```

役割は人物の善悪を表さない。

一人の人物が複数の機能を持つ場合でも、主要役割を一つ定め、補助tagを別に持たせる。

---

## 27. Relationship

Relationshipは、二人以上の人物間の継続的関係を表す。

主要項目:

| 項目 | 意味 |
|---|---|
| `relationship_id` | 永続ID |
| `participant_ids` | 関係する人物 |
| `relationship_type` | 家族、友情、敵対など |
| `public_description` | 公開可能な関係 |
| `private_truth` | 作者用の真相 |
| `initial_state` | 開始時状態 |
| `desired_arc` | 長期変化 |
| `constraints` | 崩してはいけない条件 |

`initial_state`はInitial Generationを作るための初期値であり、Scene進行後の現在値ではない。

二者関係だけに限定しない。ただし、三者以上の関係が複雑な場合は、個別Relationshipへ分ける。

---

## 28. World

Worldは、作品世界の前提をまとめる。

主要項目:

```text
setting_summary
historical_background
social_structure
technology_or_magic
cultural_norms
major_conflicts
public_knowledge
private_truths
```

WorldはLocationやRuleの一覧を参照する。

---

## 29. Location

Locationは、継続性を追跡する場所を表す。

主要項目:

| 項目 | 意味 |
|---|---|
| `location_id` | 永続ID |
| `name` | 表示名 |
| `parent_location_id` | 上位場所 |
| `description` | 場所の説明 |
| `access_constraints` | 出入り条件 |
| `public_facts` | 公開済み事実 |
| `private_facts` | 作者用事実 |

場所の階層例:

```text
町
└── 岬
    └── 灯台
        └── 地下室
```

---

## 30. World Rule

World Ruleは、作品世界の一貫性を支える規則である。

例:

```text
魔法の制約
技術上の制約
社会制度
時間移動の規則
怪異の発生条件
```

主要項目:

```text
rule_id
name
description
scope
exceptions
reader_visibility
change_policy
```

通常SceneでWorld Ruleを変更してはならない。

---

## 31. Knowledge Fact

Knowledge Factは、知識として追跡する一つの事実を表す。

主要項目:

| 項目 | 意味 |
|---|---|
| `knowledge_id` | 永続ID |
| `statement` | 事実内容 |
| `truth_status` | 作品世界での真偽 |
| `reader_visibility` | Initial Generation作成時の読者開示状態 |
| `source_type` | 事実の由来 |
| `private_notes` | 作者用説明 |

`truth_status`:

```text
true
false
uncertain
```

`reader_visibility`:

```text
hidden
partially_revealed
revealed
```

`reader_visibility`は初期値であり、Scene進行後の現在値のAuthorityではない。現在の読者開示状態はStory Stateの`reader_knowledge`で管理する。

人物が知っていること、読者へ開示済みであること、作品世界で真実であることを分離する。

---

## 32. Initial Character Knowledge

Initial Designは、開始時点で人物が持つKnowledgeだけを定義する。

```text
character_id
knowledge_id
initial_status
```

`initial_status`の列挙値とScene進行後のAuthorityは§45で定義する。未指定の組は`unknown`としてInitial Generationを作る。

---

## 33. Thread

Threadは、物語上追跡する未解決の問い、約束、対立、謎を表す。

主要項目:

| 項目 | 意味 |
|---|---|
| `thread_id` | 永続ID |
| `title` | 短い名称 |
| `question` | 何が未解決か |
| `importance` | 重要度 |
| `kind` | 謎、関係、目的、脅威など |
| `introduced_by` | 導入元 |
| `required_for_completion` | 完結に必須か |
| `planned_resolution` | 作者用解決方針 |
| `reader_visibility` | Initial Generation作成時の存在開示状態 |
| `initial_status` | 開始状態 |

`initial_status`:

```text
planned
open
progressing
resolved
abandoned
```

Scene進行後のThread状態は`threads`、読者への存在開示は`reader_knowledge`をAuthorityとする。

---

## 34. Ending Design

Ending Designは、シリーズ完結の作者用条件を定める。

主要項目:

| 項目 | 意味 |
|---|---|
| `ending_id` | 永続ID |
| `desired_effect` | 読後感 |
| `required_outcomes` | 必須結果 |
| `forbidden_outcomes` | 避ける結果 |
| `character_end_states` | 主要人物の到達状態 |
| `relationship_end_states` | 主要関係の到達状態 |
| `thread_requirements` | Threadの必要処理 |
| `final_revelations` | 最終開示 |
| `private_notes` | 作者用補足 |

Ending Designを本文生成へ一括で渡してはならない。

---

## 35. Long-term Arc

Long-term Arcは、シリーズ全体を通じた変化を表す。

対象:

```text
Character
Relationship
Thread
World
Theme
```

主要項目:

```text
arc_id
target_type
target_id
start_state
turning_points
desired_end_state
failure_modes
```

Turning pointは予定であり、本文確定前は事実ではない。

---

## 36. Initial Designの不変条件

Initial Designは次を満たす。

```text
すべての参照IDが存在する
主人公が少なくとも一人いる
必須Threadが少なくとも一つある
Ending Designが存在する
Characterの初期位置と初期Knowledgeを定義できる
Relationship参加者が存在する
World Rule同士が直接矛盾しない
Briefの必須要素を保持する
Briefのavoidへ違反しない
```

---

# Part V: CanonとState

## 37. Canon

Canonは、採用済みInitial Designから作られた安定した設定と過去の確定事実を表す。

通常SceneのContinuity UpdateはCanonを追加、更新、削除してはならない。

確定済みCanonの訂正が必要な場合、Version 1は既存workspaceを変更せず`blocked`として停止し、新しいworkspaceが必要であることを示す。

Canon上の真相が本文で開示された場合もCanon自体は変更せず、Character KnowledgeまたはReader KnowledgeだけをEvidenceに基づいて更新する。

---

## 38. Canon Record

Canon Recordは少なくとも次を持つ。

- `canon_id`
- `category`
- `subject_id`
- `statement`
- `source_type`
- `source_id`
- `status`
- `created_at`

`source_type`は`initial_design`だけを許可し、`source_id`は採用済みInitial Designを参照する。

Version 1の`status`は`active`だけを許可する。

`design_revision`、`superseded`、`superseded_by_canon_id`はVersion 1の永続契約へ含めない。

---

## 39. Story StateとAuthority

Story Stateは、一つのGenerationに属する現在状態である。

構成:

```text
characters
relationships
locations
world
threads
character_knowledge
reader_knowledge
timeline
inventory
commitments
```

現在値のAuthorityは次のとおりとする。

| 現在値 | Authority |
|---|---|
| 人物の位置・身体・感情・目標・生死 | `characters` |
| 関係の状態・感情・公私の関係 | `relationships` |
| 場所の利用可否・損傷・危険 | `locations` |
| 作品全体へ影響する現在状況 | `world` |
| Threadの進行状態 | `threads` |
| 人物が知る・信じる・疑う内容 | `character_knowledge` |
| 読者へ本文上で開示済みの内容 | `reader_knowledge` |
| 時間順・期限・経過時間 | `timeline` |
| 物品の所有者・所持者・所在・状態 | `inventory` |
| 約束・契約・義務の履行状態 | `commitments` |

別領域へ同じ現在値を複製しない。検索用indexやsummaryはAuthorityから再生成する。

---

## 40. Character State

人物の現在状態は次を持つ。

```text
current_location_id
physical_condition
emotional_condition
goals
active_constraints
availability
alive_status
last_change_scene_id
```

次はCharacter Stateへ複製しない。

```text
所持品: inventoryを参照
Knowledge: character_knowledgeを参照
関係状態: relationshipsを参照
安定した人物設定: CanonまたはInitial Designを参照
```

---

## 41. Relationship State

Relationshipの現在状態は次を持つ。

```text
status
trust
affection
fear
hostility
public_status
private_status
last_change_scene_id
```

約束・義務は`commitments`、共有された知識は`character_knowledge`をAuthorityとする。

数値尺度を使用する場合でも、数値だけで関係を表さず短い説明を持つ。

---

## 42. Location State

Location Stateは、場所の変化する現在状態だけを持つ。

```text
accessibility
condition
active_hazards
temporary_features
last_change_scene_id
```

人物の所在は`characters.current_location_id`、人物が場所を知っているかは`character_knowledge`から導出する。Location Stateへ`occupied_by`や`known_to_characters`を持たない。

安定した場所説明はLocation定義またはCanonを参照する。

---

## 43. World State

World Stateは、複数の人物・場所・Sceneへ影響する現在状況だけを持つ。

```text
public_alert_level
active_conditions
institutional_changes
public_events
last_change_scene_id
```

局所的な天候・危険・損傷はLocation State、時間上の事実はTimeline StateをAuthorityとする。Scene局所の描写をWorld Stateへ昇格させない。

---

## 44. Thread State

Thread Stateは次を持つ。

```text
status
progress_summary
open_questions
latest_development_scene_id
resolution_scene_id
completion_notes
```

`resolved`へ変更する場合は、本文上の解決Evidenceを必須とする。

---

## 45. Knowledge State

人物ごとのKnowledge状態は、`character_id`と`knowledge_id`の組で管理する。論理target IDは`<character_id>::<knowledge_id>`とし、filesystem pathには使用しない。

```text
character_knowledge:
  status
  last_change_scene_id
```

人物の`status`:

```text
knows
believes
suspects
disbelieves
unknown
```

記録が存在しない組は`unknown`として扱い、最初の非`unknown`更新時に記録を作成できる。新しいCharacter IDやKnowledge IDをScene Continuityで作成してはならない。

読者への現在の開示状態は、開示対象の種類とIDの組で管理する。

```text
reader_knowledge:
  target_type
  target_id
  status
  last_change_scene_id
```

`target_type`:

```text
knowledge_fact
thread
```

読者の`status`:

```text
hidden
partially_revealed
revealed
```

論理target IDは`<target_type>::<target_id>`とする。Initial GenerationではKnowledge FactとThreadの`reader_visibility`から初期化する。以後は、採用済み本文にEvidenceがある場合だけ更新する。

Knowledge Factの`truth_status`、人物のKnowledge State、読者のKnowledge Stateは独立して管理する。Plan、Scene Cardの開示許可、作者用説明だけを根拠にKnowledge Stateを変更してはならない。

---

## 46. Timeline State

Timeline Stateは、Scene間の時間関係を追跡する。

```text
current_story_time
calendar_system
elapsed_time
known_deadlines
event_order
time_constraints
```

正確な日付を使用しない作品でも、Scene順と相対時間を矛盾なく追跡できなければならない。

---

## 47. Inventory State

重要な物品は永続IDを持つ。

```text
item_id
name
owner_character_id
holder_character_id
location_id
whereabouts_status
condition
significance
visibility
last_change_scene_id
```

`whereabouts_status`:

```text
held
placed
unknown
destroyed
```

`held`では`holder_character_id`だけ、`placed`では`location_id`だけを設定する。`unknown`または`destroyed`では両方をnullとする。

所有者と現在の所持者を区別する。同じ物品の現在所持者・所在をCharacter StateやLocation Stateへ複製しない。

---

## 48. Commitment State

約束、契約、義務を追跡する。

```text
commitment_id
participants
description
status
deadline
created_scene_id
resolved_scene_id
last_change_scene_id
```

`status`:

```text
active
fulfilled
broken
cancelled
expired
```

Relationship Stateへ同じ義務を複製しない。単なる将来予定はPlanまたはTimelineで扱い、当事者間に成立した約束・契約・義務だけをCommitmentとする。

---

## 49. Stateの不変条件

一つのStateは次を満たす。

```text
同一人物が同時に複数のcurrent_location_idを持たない
alive_statusがdeadの人物を通常参加者として扱わない
Inventoryのwhereabouts_statusとholder_character_id・location_idが整合する
resolved Threadにresolution_scene_idとEvidenceがある
Reader Knowledgeの更新に本文Evidenceがある
時間順がWorld Ruleなしに逆転しない
存在しないIDを参照しない
active Canonと直接矛盾しない
同じ現在値を複数領域へ重複保存しない
```

超自然的設定などで例外が必要な場合は、World Ruleとして明示する。

---

# Part VI: 計画モデル

## 50. Plan共通規則

Planは将来の執筆方針であり、確定したStory事実ではない。

Plan本体は少なくとも次を持つ。

- `plan_id`
- `plan_type`
- `basis_generation_id`
- 対象を一意に示すfield
- `objectives`
- `constraints`
- `created_at`

未採用PlanはCandidate領域で管理する。

採用済みPlanはimmutableであり、Version 1では対象ごとに正確に一件だけ存在できる。

Version 1のPlan本体へ`superseded`状態、`parent_plan_id`、`supersedes_version`などのRevision用fieldを持たせない。

---

## 51. Series Plan

Series Planは全巻の物語構造を定める。

主要項目:

- `series_plan_id`
- `title`
- `basis_generation_id`
- `volume_count`
- `series_objectives`
- `volume_summaries`
- `character_arc_map`
- `relationship_arc_map`
- `thread_progression`
- `revelation_schedule`
- `ending_path`
- `global_constraints`

`title`はPublicationで使用する確定シリーズ名である。Briefの`title`が空でなければ同じ値とし、空の場合はSeries Planで空でない表示名を一件確定する。

`volume_summaries`は`volume_number`による順序付き集合とする。

一workspaceに採用済みSeries Planは一件だけ存在できる。

---

## 52. Volume Plan

Volume Planは一巻の役割と到達点を定める。

主要項目:

- `volume_plan_id`
- `title`
- `volume_number`
- `basis_generation_id`
- `series_plan_id`
- `previous_handoff_id`
- `starting_state_summary`
- `volume_purpose`
- `central_conflict`
- `character_changes`
- `relationship_changes`
- `thread_goals`
- `revelations`
- `chapter_summaries`
- `required_end_state`
- `handoff_expectations`

`title`は空でない巻題とし、Publicationの巻題Authorityとする。

第1巻では`previous_handoff_id`をnullとする。

第2巻以降では直前巻の確定済みHandoffを参照する。ただし詳細AuthorityはHandoffの`basis_generation_id`が示すGenerationである。

同じ`volume_number`の採用済みVolume Planは一件だけ存在できる。

---

## 53. Chapter Plan

Chapter Planは一章を順序付きSceneへ具体化する。

主要項目:

- `chapter_plan_id`
- `title`
- `volume_number`
- `chapter_number`
- `basis_generation_id`
- `volume_plan_id`
- `chapter_purpose`
- `starting_conditions`
- `ending_changes`
- `scene_summaries`
- `required_revelations`
- `constraints`

`title`は空でない章題とし、Publicationの章題Authorityとする。

同じ`volume_number`と`chapter_number`の採用済みChapter Planは一件だけ存在できる。

---

## 54. Scene Plan

Scene Planは章計画内の一Sceneの予定を表す。

主要項目:

- `scene_plan_id`
- `volume_number`
- `chapter_number`
- `scene_number`
- `basis_generation_id`
- `chapter_plan_id`
- `purpose`
- `pov_character_id`
- `participant_ids`
- `location_id`
- `starting_conditions`
- `intended_beats`
- `intended_revelations`
- `intended_changes`
- `prohibited_disclosures`

Scene PlanはScene Cardより粗い計画である。

同じ巻・章・Scene番号の採用済みScene Planは一件だけ存在できる。

---

## 55. Planの基準Generation

すべてのPlanは、どの採用済みGenerationを基準に作られたかを`basis_generation_id`で識別する。

Planを採用または使用する前に、基準Generationから解決した関連Authority入力が現在も同一であることをコードで確認する。

関連Authority入力が変化している未採用Plan Candidateは破棄またはrejectし、新しいbasis Generationから再生成する。

Generation IDだけが異なり、関連Authority入力と内容が同一であることをコードで証明できる場合だけ、Candidateを現在の基準で再検証できる。

HashだけでPlanの有効性を判断しない。

---

## 56. Planの採用と不変性

Plan採用時は、対象に既存の採用済みPlanがないことを確認する。

採用済みPlanを修正、置換、supersede、上書きしてはならない。

採用後に構造変更が必要になった場合は、既存Planと確定済み成果物を保持したまま`blocked`として停止し、新しいworkspaceが必要であることを示す。

Version 1にはPlan Revision遷移を設けない。

---

# Part VII: Sceneモデル

## 57. Scene Card

Scene Cardは、実際のScene生成に使用する詳細な未採用設計Candidateである。

主要項目:

- `scene_id`
- `version`
- `basis_generation_id`
- `scene_plan_id`
- `pov_character_id`
- `participant_ids`
- `location_id`
- `story_time`
- `purpose`
- `opening_state`
- `required_beats`
- `conflict`
- `allowed_revelations`
- `required_revelations`
- `forbidden_revelations`
- `allowed_updates`
- `ending_state_targets`
- `style_constraints`

`pov_character_id`は`participant_ids`に含まれなければならない。

---

## 58. POV

Version 1では一Sceneにつき一つの`pov_character_id`を指定する。

本文へ出せる情報は、POV人物が自然に知覚、記憶、認識、または推測できる範囲に限定する。

非POV人物の非公開の思考、感情、意図を事実として断定してはならない。

Scene CardはPOV制約を緩和または上書きできない。

Version 1は全知視点、複数POV、無表示のPOV切替を提供しない。

---

## 59. Beat

Beatは、Sceneで起きるべき意味的な出来事である。

主要項目:

```text
beat_id
description
required
order_hint
participants
expected_effect
```

Beatを台詞や完成文章として過剰に固定しない。

---

## 60. 開示制約

Scene Cardは情報開示を次へ分類する。

- `allowed_revelations`: このSceneで開示してよい
- `required_revelations`: このSceneで開示しなければならない
- `forbidden_revelations`: このSceneでは開示してはならない

各値は、安定したKnowledge IDまたはThread IDを参照する。

`required_revelations`は`allowed_revelations`の部分集合でなければならない。

`forbidden_revelations`は`allowed_revelations`および`required_revelations`と重複してはならない。

Scene固有のallowedまたはrequired指定はWriterへの一時的な利用許可であり、Reader KnowledgeまたはCharacter Knowledgeを直接更新しない。

確定本文に対応するEvidenceが存在する場合だけ、永続的な開示状態を更新する。

開示許可によってPOV制約を上書きしてはならない。

---

## 61. 許可更新

`allowed_updates`は、Scene後に変更してよい現在状態の範囲を定義する。

`target_type`は次のいずれかとする。

```text
character_state
relationship_state
location_state
world_state
thread_state
character_knowledge
reader_knowledge
timeline_state
inventory_state
commitment_state
```

例:

```json
[
  {
    "target_type": "character_state",
    "target_id": "char-mio",
    "allowed_fields": [
      "current_location_id"
    ]
  },
  {
    "target_type": "reader_knowledge",
    "target_id": "knowledge_fact::know-lighthouse-key-owner",
    "allowed_fields": [
      "status"
    ]
  }
]
```

許可は変更の義務ではない。本文にEvidenceがなければ更新しない。Canon、Initial Design、Planの変更を`allowed_updates`へ含めてはならない。

---

## 62. Scene本文

Scene本文は、採用対象となる日本語散文である。

本文データの主要属性:

```text
scene_id
version
text
language
created_at
```

最終的な保存時に、本文とmetadataを別ファイルへ分けてもよい。

本文文字列へ内部metadataを埋め込まない。

---

## 63. Scene本文の凍結

継続性更新を抽出する前に、対象本文を凍結する。

凍結後に本文を変更した場合、古い継続性更新とEvidenceを再利用してはならない。

Hashだけに依存せず、未採用Candidate ID、Candidate version、確定Scene ID、採用関係で識別する。

---

## 64. Continuity Update

Continuity Updateは、凍結済みScene本文から導かれる現在状態の変更候補である。

```text
scene_id
basis_generation_id
operations
evidence
unchanged_assertions
issues
```

検証とScene Commitが完了するまで未採用である。

---

## 65. Update Operation

一つの状態変更を明示的な操作として表す。

`operation`:

```text
set
add
remove
transition
resolve
```

主要項目:

```text
operation_id
target_type
target_id
field
operation
old_value
new_value
reason
evidence_ids
```

`target_type`は§61の列挙値だけを使用する。`old_value`はbasis Generationとの競合検出に使用する。

---

## 66. Updateの禁止事項

Continuity Updateは次を行ってはならない。

```text
Scene Cardで許可されていない対象・fieldの変更
本文にない出来事の追加
Planだけを根拠にした変更
秘密情報の早期公開
Canon、Initial Design、採用済みPlanの変更
存在しないIDの作成
Ending条件の暗黙変更
同じ現在値の別領域への複製
```

---

## 67. Evidence

Evidenceは、一つ以上のUpdate Operationの根拠となる本文表現を示す。

```text
evidence_id
scene_id
quote
occurrence
context_before
context_after
```

`quote`は保存済みScene本文の完全一致部分文字列、`occurrence`は本文先頭から数えた1始まりの出現番号とする。`context_before`と`context_after`は、同一引用の識別や人間確認に必要な場合だけ持つ。

更新対象、field、変更前後、変更理由はEvidenceを参照するUpdate Operationから確認する。Evidence側へ同じ値を複製しない。

---

## 68. Evidenceの照合

Evidenceは次を満たさなければならない。

```text
scene_idが確定対象Sceneと一致する
quoteのoccurrence番目が本文に存在する
参照元Operationが一つ以上存在する
参照元Operationのtargetとfieldがallowed_updates内である
```

文字offsetは使用しない。本文を変更した場合、古いContinuity UpdateとEvidenceを再利用してはならない。

---

## 69. Scene Commit

Scene Commitは、Scene Card、本文、Continuity Update、新Generationを一つの採用判断として関連付ける。

主要項目:

```text
scene_id
parent_generation_id
result_generation_id
scene_card_candidate_id
scene_card_candidate_version
prose_candidate_id
prose_candidate_version
continuity_update_id
committed_at
commit_summary
```

独立した複雑なCommit Manifest graphは作らない。

---

## 70. Scene成果物の不変条件

採用済みSceneは次を満たす。

```text
Scene Cardと本文のscene_idが一致する
basis_generation_idが一致する
Evidenceが本文に存在する
Updateがallowed_updates内である
result_generation_idがparent_generation_idの直接後継である
同じ確定Scene IDが異なるresult Generationへ競合確定されていない
本文が空でない
```

---

# Part VIII: Generationモデル

## 71. Generation

Generationは、一つの採用済みStory状態を表すimmutable snapshotである。

論理構成:

```text
generation_id
parent_generation_id
canon
state
evidence
commit
created_at
```

GenerationはScene確定または初期設計採用など、Story状態が変わる採用境界で作る。

---

## 72. Generation ID

Generation IDは単調増加させる。

例:

```text
gen-000001
gen-000002
gen-000003
```

番号の欠けを許容する。

一度割り当てた番号を再利用しない。

---

## 73. Parent関係

通常のGenerationは、直前の採用済みGenerationを一つだけ親として持つ。

Version 1ではGenerationのbranch、merge、過去Generationの修正を提供しない。

確定済みInitial Design、Canon、State、Generationの訂正が必要な場合は、現在系統へ修正Generationを追加せず`blocked`として停止し、新しいworkspaceが必要であることを示す。

---

## 74. Initial Generation

最初のGenerationは、採用済みInitial Designから作る。

`parent_generation_id`は`null`とする。

Initial Generationは、少なくとも次を含む。

```text
初期Canon
初期State
初期Thread状態
初期Knowledge状態
初期Relationship状態
```

---

## 75. Generation Commit

Generation Commitは、そのGenerationが作られた確定境界を示す。

主要項目:

- `commit_type`
- `source_artifact_type`
- `source_artifact_id`
- `summary`
- `changed_targets`
- `created_at`

`commit_type`は次のいずれかとする。

- `initial_design`
- `scene`
- `recovery_finalize`

`recovery_finalize`は新しいStory変更ではなく、Crash前に完成していた同一成果物の確定処理を完了したことを表す。

`manual_revision`や確定成果物の再採用を表す値はVersion 1で使用しない。

---

## 76. Generationの不変条件

Generationは次を満たす。

```text
IDが一意
親が存在する、またはInitial Generationである
親より後のIDである
CanonとStateの参照が解決する
Evidenceが存在するSceneを参照する
Commitのsource artifactが存在する
同じGenerationを上書きしない
```

---

# Part IX: Handoffモデル

## 77. Volume Handoff

Volume Handoffは、一巻の最終Generationと確定済み成果物を根拠として、LLMが作る**補助要約**である。詳細なStory Authorityではなく、次巻計画とCompletionが必要な情報を理解しやすく受け渡すために使う。

最終巻を含むすべてのVolumeについて、一件の確定済みHandoffを作成する。

主要項目:

- `handoff_id`
- `volume_number`
- `basis_generation_id`
- `completed_chapter_ids`
- `completed_scene_ids`
- `character_states`
- `relationship_states`
- `resolved_threads`
- `open_threads`
- `new_constraints`
- `ending_progress`
- `next_volume_requirements`
- `source_refs`
- `created_at`

コードはLLM呼出し前に、巻開始・巻末Generation、確定Scene、Evidence、採用済みPlan、Thread、Ending Designから**Handoff source bundle**を構築する。source bundleは、ID・状態値・Evidence・参照関係を落とさず保持する構造化入力であり、先頭や末尾を切り出すだけの機械的要約ではない。

LLMはsource bundleだけを根拠に、次を含む読みやすい構造化Handoffを生成する。

- 主要人物とRelationshipの巻末状態および、次巻で重要な変化
- 解決済み／未解決Threadと、その根拠Scene
- 新たな制約、Endingへの進捗、次巻で無視できない結果
- 各意味的主張を解決できる`source_refs`

`character_states`、`relationship_states`、`resolved_threads`、`open_threads`、`new_constraints`、`ending_progress`、`next_volume_requirements`は、自然言語の印象だけで作成してはならない。LLM出力はsource bundle内のID・状態・Evidenceへ参照を持ち、コードは参照先、対象Volume、巻末Generation、完了済みScene、列挙値を検証する。

生成済みHandoffは独立したLLM Reviewの対象とする。Reviewは、根拠のない出来事、重要な未解決事項の脱落、状態の取り違え、次巻またはCompletionに必要な情報の不足を確認する。`error`があれば未採用HandoffをRevisionし、再Reviewする。

同じ`volume_number`に確定済みHandoffを複数作成してはならない。

---

## 78. HandoffのAuthority

Handoffは、すべてのCanonとStateを複製しない。

巻中の重要変化、巻末時点の主要状態、未解決事項、Endingへの進捗など、後続処理に必要な要約と参照だけを持つ。

詳細なStory Authorityは`basis_generation_id`が示すGenerationである。

Handoffの各要約は、`source_refs`を通じてbasis Generationと確定済み成果物へ解決できなければならない。参照先が変化または不整合ならHandoffをAuthorityとして使わず、再評価または人間確認を要求する。

最終巻のHandoffは次巻入力ではなく、Completion入力として使用する。

---

## 79. Handoffの禁止事項

Handoffは次を行ってはならない。

- 本文またはGenerationにない出来事の追加
- 未解決Threadの無断解決
- 次巻の本文またはPlanの作成
- CanonまたはStateの変更
- Ending条件の変更

Handoffは新しい物語生成、Story Authority、確定成果物のRevisionではない。

---


# Part X: ReviewとRevisionモデル

## 80. Review Result

Review Resultは、一つの未採用Candidate versionに対する評価である。

主要項目:

- `review_id`
- `target_type`
- `target_id`
- `target_version`
- `decision`
- `issues`
- `summary`
- `created_at`

`decision`は次のいずれかとする。

- `accept`
- `revise`
- `reject`

`error`が一件でも存在する場合、`accept`にしてはならない。

`warning`または`note`だけの場合は`accept`できる。

---

## 81. Review Issue

一つのIssueは、具体的で対象Candidateに関連付け可能でなければならない。

主要項目:

- `issue_id`
- `category`
- `severity`
- `location`
- `evidence_locator`
- `description`
- `expected`
- `suggestion`

`category`例:

- `schema`
- `brief_mismatch`
- `continuity`
- `knowledge`
- `pov`
- `disclosure`
- `character`
- `plot`
- `style`
- `safety`

`evidence_locator`は、対象CandidateまたはReview入力に含まれるartifact ID、field pathまたは本文range、必要時の引用を持つ。コードで解決できないlocatorを持つIssueは無効とし、Revision Recordへ渡してはならない。

---

## 82. Issue Severity

`severity`は次のいずれかとする。

- `error`: Candidateの採用を禁止する
- `warning`: 採用可能だが注意事項として記録する
- `note`: 採用可能な改善提案として記録する

Reviewごとに独自の類似severityを追加してはならない。

---

## 83. Revision Record

Revision Recordは、Reviewを受けて新しい未採用Candidate versionが作られた関係を示す作業データである。

主要項目:

- `revision_id`
- `original_candidate_id`
- `original_version`
- `review_id`
- `result_candidate_id`
- `result_version`
- `addressed_issue_ids`
- `unresolved_issue_ids`
- `created_at`

Revision RecordはCandidate本文を複製せず、Story Authorityにもならない。

確定済みInitial Design、採用済みPlan、確定済みSceneその他の確定成果物をRevision対象にしてはならない。

---

## 84. Reviewの不変条件

ReviewとRevisionは次を満たす。

- Review対象は一つの未採用Candidate versionである
- Review対象のIDとversionが一意に特定できる
- Reviewが対象Candidateを直接変更しない
- Revision結果は同じCandidate IDの新しいversionである
- Revision結果は完全な置換Candidateである
- 未解決`error`があるCandidateを採用しない
- `warning`と`note`だけを理由に採用を禁止しない
- 採用後のCandidateへRevisionを適用しない

---


# Part XI: Completionモデル

## 85. Completion前確認

Completion callの前に、コードで次を確認する。

- Series Planが要求する全Volumeが完了している
- 対象ごとに採用済みPlanが正確に一件存在する
- 全Chapterと全予定Sceneが確定している
- 最終巻を含む全Volume Handoffが存在する
- 現在Generationが最終予定Sceneの確定結果である
- 未完了の執筆、採用、確定、Recovery処理がない
- 主要Thread、Ending条件、主要Arcを評価できる
- Plan、Scene、Handoffの実集合が期待集合と一致する

競合PlanやAuthority不整合がある場合は、推測せず人間確認を要求する。

この確認を独立したhash付き永続artifactにする必要はない。

---

## 86. Completion Result

Completion Resultは、特定の確定済み入力集合を評価した完結判定である。

主要項目:

- `completion_id`
- `basis_generation_id`
- `evaluated_series_plan_id`
- `evaluated_volume_plan_ids`
- `evaluated_chapter_plan_ids`
- `evaluated_scene_plan_ids`
- `evaluated_scene_refs`
- `evaluated_handoff_ids`
- `status`
- `summary`
- `precheck_summary`
- `thread_checks`
- `ending_checks`
- `character_arc_checks`
- `relationship_arc_checks`
- `issues`
- `created_at`

`evaluated_scene_refs`は各確定Scene本文を一意に解決できる情報を計画順で保持する。

各要素は、Scene ID、Scene Plan ID、result Generation ID、採用元Scene Card／本文CandidateのIDとversion、および`scene-card.json`、`prose.md`、`continuity.json`、`commit.json`のSHA-256 digestを保持する。

このdigestはCompletion評価後の外部変更をPublication確定時とRecovery時に検出する目的だけに使用する。相違時はPublicationを作成せず`failed`かつ`manual_review_required`とする。Manifest、hash chain、Story Authorityとして使用しない。

`status`は`complete`、`complete_with_issues`、`incomplete`のいずれかとする。

Completion Resultはimmutableとする。

---

## 87. Thread Check

完結必須Threadが未解決の場合、`complete`または`complete_with_issues`にしてはならない。

Thread Checkは少なくともThread ID、必須性、状態、Evidence Scene、評価、Issueを持つ。

---

## 88. Ending Check

Ending必須条件が満たされない場合、`complete`または`complete_with_issues`にしてはならない。

Ending Checkは少なくとも条件ID、状態、Evidence Scene、評価、Issueを持つ。

---

## 89. Arc Check

主要Character ArcとRelationship Arcについて、計画上と確定本文上の到達点を評価する。

計画との差異だけで未完結とせず、意味のある代替到達点かを評価する。

---

## 90. `complete_with_issues`

`complete_with_issues`は完結必須条件を満たし、軽微な注意事項だけが残る場合に使用する。

次の場合は`incomplete`とする。

- 主要Threadが未解決
- Ending必須条件を満たさない
- 予定Sceneまたは最終Sceneが欠落
- 必須Arcを評価できない
- Plan、Scene、Handoff集合が期待集合と一致しない

---

## 91. Completionの不変条件

Completion Resultは次を満たす。

- `basis_generation_id`が最終採用Generationである
- 評価したPlan、Scene、Handoffの全IDを保持する
- 評価入力集合がCompletion前確認の集合と一致する
- 全必須Thread、Ending条件、主要Arcを評価している
- statusと各Checkが矛盾しない
- Evidenceが確定本文へ解決する
- `incomplete`を通信失敗として扱わない
- 同じ入力を成功まで無制限に再評価しない

---

# Part XII: Publicationモデル

## 92. Publication Metadata

Publication Metadataは、読者向け成果物の構成と使用入力を示す。

主要項目:

- `publication_id`
- `brief_id`
- `title`
- `language`
- `volume_count`
- `volume_entries`
- `completion_id`
- `basis_generation_id`
- `series_plan_id`
- `volume_plan_ids`
- `chapter_plan_ids`
- `scene_plan_ids`
- `scene_refs`
- `created_at`

`volume_entries`は少なくとも巻番号、題名、章数、Scene数、出力名を持つ。

Metadataから、使用したBrief、採用済みPlan階層、確定Scene本文、Completion Resultを一意に解決できなければならない。

---

## 93. Publication本文

Publication本文は、次の確定済み入力だけからコードで構築する。

- Brief
- 採用済みSeries／Volume／Chapter／Scene Plan
- 確定済みScene本文
- Completion Result

Scene本文は採用済みPlanの順序に従って連結する。

Publication Builderが追加できるものは、題名、巻題、章題、区切り、目次、決定的なformattingに限定する。

新しい物語本文、出来事、説明、要約を生成してはならない。

---

## 94. Publicationから除外する情報

Publicationへ次を含めてはならない。

- 作者用秘密
- Review Issue
- Revision Record
- Provider requestまたはresponse metadata
- Credential
- 利用量
- 内部Context
- Recovery情報
- 未公開Ending Design
- Candidateまたはstaging成果物

---

## 95. Publicationの完結条件

正式Publicationは、Completion Resultが`complete`または`complete_with_issues`の場合だけ確定できる。

`incomplete`の場合は正式Publicationを作成しない。

Version 1ではpreviewを正式Publicationの代替成果物として扱わない。

---

## 96. Publicationの決定性

同じBrief、採用済みPlan階層、確定Scene本文、Completion Resultから再構築したPublicationは、同じ本文順と内容にならなければならない。

Publication確定前に次を確認する。

- Completionの評価済みPlan集合と現在の採用済みPlan集合が一致する
- Completionの評価済みScene集合とPublicationのScene集合が一致する
- `basis_generation_id`がCompletion Resultと一致する
- 各Scene本文がCompletion評価時と同じ確定成果物である

Provider call、生成モデル、独立Publication Plan、Publication Gate、Publication Manifest、LLMによる再監査を使用してはならない。

---

# Part XIII: データ間関係

## 97. 全体関係

外部入力は、BriefまたはKeywordsのどちらか一つである。

```text
Keywords
  └── Brief
```

Briefを直接入力した場合、Keywords成果物は存在しない。

主要成果物の関係:

```text
Brief
  └── Initial Design
      └── Initial Generation
          └── Series Plan
              └── Volume Plan
                  └── Chapter Plan
                      └── Scene Plan
                          └── Scene Card
                              └── Scene本文
                                  └── Continuity Update
                                      ├── Evidence
                                      └── Generation

各Volumeの最終Generation
  └── Volume Handoff

全Plan + 全Scene + 全Handoff + 最終Generation
  └── Completion Result

Brief + 全Plan + 全Scene本文 + Completion Result
  └── Publication
```

---

## 98. SceneとGenerationの関係

一つのScene処理は、Scene PlanからScene確定まで同じ`basis_generation_id`と、そこから解決した同一のAuthority入力を使用する。

Scene確定では、親Generationの直接後継Generationを一件作成する。

異なるbasis GenerationのScene Card、本文、Continuity Update、Evidence、Scene Commitを混在させてはならない。

---

## 99. PlanとGenerationの関係

すべてのPlanは`basis_generation_id`を持つ。

Planの採用または使用前に、基準Generationから解決した関連Authority入力が現在も同一であることを確認する。

採用済みPlanは将来方針であり、Story StateのAuthorityではない。

---

## 100. CompletionとPublicationの関係

Completion Resultは、評価したPlan、Scene、Handoff、最終Generationのidentityを保持する。

Publicationは、Completionが評価したものと同一の採用済みPlan集合、確定Scene集合、Scene本文、最終Generationを使用する。

Publication Metadataの`completion_id`と`basis_generation_id`はCompletion Resultと一致しなければならない。

別の入力集合または別GenerationのCompletion Resultを流用してはならない。

---

# Part XIV: Validation

## 101. 参照整合性

構造化データを採用する前に、すべての参照IDが解決できなければならない。

例外:

```text
parent_generation_idがnullのInitial Generation
まだ存在しない将来Sceneを表すPlan内の論理番号
```

将来Sceneには永続Scene IDを先行割当してよいが、確定済みSceneと混同しない。

---

## 102. Cross-field制約

単純な型確認だけでなく、項目間の整合性を確認する。

例:

```text
statusがresolvedならresolution_scene_idが必要
statusがcompleteなら必須Ending Checkがすべてsatisfied
pov_character_idはparticipant_idsに含まれる
volume_numberはSeries Planの範囲内
basis_generation_idは存在する
result_generation_idはparentの後継
```

---

## 103. 秘密情報制約

データが正しくても、渡す相手に不適切なら使用してはならない。

例:

```text
Ending Design:
  Completionには必要
  Scene本文生成には原則不要

private_truth:
  Planには必要な場合がある
  POV本文には未公開なら渡さない
```

Schema validationだけで秘密境界を保証できるとは考えない。

---

## 104. Candidate検証

Candidateは採用前に次を確認する。

```text
構造が正しい
参照が解決する
上位入力を保持する
禁止内容へ違反しない
基準Generationが現在有効
Review errorが解消している
```

形式不正Candidateを意味的Reviewへ送らない。

---

## 105. Scene確定検証

Scene確定前に少なくとも次を確認する。

```text
本文が空でない
Scene Cardと本文が対応
禁止開示がない
Continuity Updateが構造的に正しい
Evidenceが本文に存在
許可外更新がない
基準Generationが変わっていない
新Stateが不変条件を満たす
```

---

## 106. Completion検証

Completion採用前に次を確認する。

```text
すべての必須対象を評価
statusが定義済み
checksとstatusが矛盾しない
basis_generation_idが最終Generation
Evidence参照が解決する
```

---

## 107. Publication検証

Publication確定前に次を確認する。

```text
Completionが公開可能
全Sceneが順序通り存在
本文が空でない
巻数が計画と一致
private情報を含まない
metadataが本文構成と一致
```

---

# Part XV: 代表例

## 108. 人物Knowledgeの例

```json
{
  "knowledge_id": "know-lighthouse-key-owner",
  "statement": "灯台の鍵は凪が持っている",
  "truth_status": "true",
  "reader_visibility": "revealed"
}
```

```json
{
  "character_id": "char-mio",
  "knowledge_id": "know-lighthouse-key-owner",
  "status": "knows",
  "last_change_scene_id": "scene-v01-c001-s002"
}
```

```json
{
  "target_type": "knowledge_fact",
  "target_id": "know-lighthouse-key-owner",
  "status": "revealed",
  "last_change_scene_id": "scene-v01-c001-s002"
}
```

---

## 109. Thread更新の例

Scene前:

```json
{
  "thread_id": "thread-missing-memory",
  "status": "open",
  "progress_summary": "澪は記憶喪失の原因を知らない"
}
```

Scene後:

```json
{
  "thread_id": "thread-missing-memory",
  "status": "progressing",
  "progress_summary": "灯台の火災と記憶喪失が同じ夜に起きたと判明",
  "latest_development_scene_id": "scene-v01-c001-s002"
}
```

---

## 110. Evidenceの例

```json
{
  "evidence_id": "evidence-000127",
  "scene_id": "scene-v01-c001-s002",
  "quote": "火事の夜、私はここにいた。",
  "occurrence": 1,
  "context_before": "凪は錆びた扉に背を預けた。",
  "context_after": "澪は息を止めた。"
}
```

---

## 111. Update Operationの例

```json
{
  "operation_id": "update-000127",
  "target_type": "character_knowledge",
  "target_id": "char-mio::know-nagi-at-fire",
  "field": "status",
  "operation": "transition",
  "old_value": "unknown",
  "new_value": "knows",
  "reason": "凪本人が火事の夜に灯台へいたと明言した",
  "evidence_ids": [
    "evidence-000127"
  ]
}
```

---

## 112. Completion Resultの例

```json
{
  "completion_id": "completion-000001",
  "basis_generation_id": "gen-000240",
  "status": "complete_with_issues",
  "summary": "主要ThreadとEnding条件は満たしている。副次的な町長選Threadの余韻が弱い。",
  "precheck_summary": {
    "all_volumes_complete": true,
    "all_planned_scenes_committed": true,
    "unfinished_scene_work": false
  },
  "thread_checks": [],
  "ending_checks": [],
  "character_arc_checks": [],
  "relationship_arc_checks": [],
  "issues": [
    {
      "category": "minor_thread",
      "evidence_locator": {
        "scene_id": "scene-000024",
        "artifact": "prose.md",
        "range": "最終二段落"
      },
      "description": "町長選Threadの最終的な影響が本文で短くしか触れられていない"
    }
  ],
  "created_at": "2026-07-23T12:00:00Z"
}
```

---

# Part XVI: 禁止事項

## 113. 重複正本の禁止

§4と§39で定めたAuthorityを一つだけ保持する。

特に次を別領域へ複製しない。

```text
人物の現在位置
物品の現在holder・所在
人物Knowledge
読者への開示状態
約束・義務
Threadの現在status
```

検索用index、表示用summary、参加者一覧などの導出値は保存できるが、Authorityから再生成可能であり、独立して更新されてはならない。

---

## 114. 予定の事実化禁止

次を採用済み事実として扱わない。

```text
Planのintended_changes
Scene Cardのending_state_targets
Reviewのsuggestion
Revision prompt
Completionの推測だけで追加された出来事
```

本文と採用処理を通じて確定する。

---

## 115. 秘密の無条件複製禁止

作者用秘密情報を、便利だからという理由で次へ複製しない。

```text
Scene Card
本文Context
Publication metadata
Handoff summary
Progress表示
Audit message
```

必要な処理へ必要な範囲だけ渡す。

---

## 116. Hash依存禁止

次の関係をHash一致だけで判断しない。

```text
CandidateとReview
Scene本文とEvidence
SceneとGeneration
CompletionとPublication
Planと基準State
```

永続ID、版、直接参照、immutable成果物で関係を表す。

---

## 117. 自由記述statusの禁止

次を自由記述だけで表現しない。

```text
Thread status
Completion status
Review decision
Knowledge state
Relationship status
Commitment status
```

定義済み列挙値と説明を併用する。

---

# Part XVII: 実装への要求

## 118. Schemaの一元化

各構造化データの厳密なSchemaは、一つの実装asset rootへ置く。

次を作らない。

```text
production専用Schema
test専用Schema
Markdown例だけの非実装Schema
source treeだけで動くfallback Schema
```

---

## 119. Serializerの一元化

同じデータ型について、productionとtestで別serializerを使用しない。

Canonical JSONが必要な場合でも、Hash計算を目的に過剰な規則を増やさない。

目的は、読み書きの一貫性とdiffの読みやすさである。

---

## 120. Migration

Version 1のSchema変更が必要な場合は、次を明示する。

```text
旧schema_version
新schema_version
変更内容
自動移行可能か
人間確認が必要か
```

黙って意味を変更しない。

初期実装段階で未公開workspaceしか存在しない場合は、移行処理を作るより明示的な再生成を選べる。

---

## 121. データモデル完成条件

データモデル実装は、少なくとも次を満たす。

```text
BriefからInitial Designを表現できる
Initial Generationを作れる
Series／Volume／Chapter／Scene Planを表現できる
Scene Cardと本文を関連付けられる
本文からContinuity UpdateとEvidenceを作れる
新Generationを作れる
Handoffを作れる
Completionを評価できる
Publication metadataを作れる
すべての参照を検証できる
作者用秘密情報を区別できる
```

---

## 122. 最終原則

Storycraftのデータモデルは、次を守る。

> Planは予定、本文は描写、Canonは確定事実、Stateは現在、Evidenceは更新根拠、Generationは採用済みSnapshot、Completionは公開可否評価、Publicationは読者向け構成である。

これらの役割を一つの巨大なobjectまたは複数の重複正本へ統合してはならない。
