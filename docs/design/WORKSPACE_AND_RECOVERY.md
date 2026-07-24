# Storycraft Workspace・保存・復旧設計

この文書は、Storycraft Version 1のworkspace構成、永続状態、排他制御、確定処理、Crash後の復旧を定める。

上位文書:

- 製品仕様: [`../product/SPECIFICATION.md`](../product/SPECIFICATION.md)
- 製品要件: [`../product/REQUIREMENTS.md`](../product/REQUIREMENTS.md)
- アーキテクチャ: [`../architecture/ARCHITECTURE.md`](../architecture/ARCHITECTURE.md)
- データモデル: [`DATA_MODEL.md`](DATA_MODEL.md)

関連する下位文書:

- 処理順とStage: `PIPELINE.md`
- LLM連携: `LLM_INTEGRATION.md`
- Release試験: `../testing/ACCEPTANCE.md`

この文書は、保存と復旧の唯一の正本である。

---

# Part I: 基本方針

## 1. 目的

この設計の目的は、次を最小限の仕組みで実現することである。

```text
一つのworkspaceへ安全に書き込める
途中停止後に再開できる
不完全な成果物を採用しない
確定済み成果物を上書きしない
Crash後の判断を人間が理解できる
現在位置を一か所で確認できる
特殊な解析toolなしにworkspaceを読める
```

---

## 2. 前提

Version 1は次を前提とする。

```text
単一writer
単一利用者
ローカルfilesystem
一つのactive run
一つのworkspace root
通常のatomic file replacement
通常の同一filesystem内directory rename
```

Network filesystem、remote storage、複数writer、分散lockは対象外である。

---

## 3. 保存原則

保存は次の原則へ従う。

```text
変更可能な単一file:
  完全な一時fileを作り、atomic replacementする

複数fileから成る確定成果物:
  staging directoryで完成させ、最終directoryへrenameする

確定済み成果物:
  上書きしない

現在位置:
  一つのrun-stateだけを正本にする

途中成果物:
  正本として扱わない

Hash:
  保存整合性の基本機構として使わない
```

---

## 4. Authority

保存上のAuthorityは次の通りである。

| 事実 | 正本 |
|---|---|
| 現在のrun status | `runtime/run-state.json` |
| 現在のStage | `runtime/run-state.json` |
| 現在Generation | `runtime/run-state.json` |
| 現在Publication | `runtime/run-state.json` |
| 永続IDの次番号 | `runtime/counters.json` |
| 採用済みStory状態 | `generations/<generation-id>/` |
| 採用済みScene | `scenes/<scene-id>/` |
| 採用済みHandoff | `handoffs/<handoff-id>/` |
| 完結判定 | `completion/<completion-id>/` |
| 読者向け成果物 | `publications/<publication-id>/` |

`HEAD`、`CURRENT`、Manifest、Gateなどを独立した正本にしない。

---

## 5. 補助情報

次は補助情報であり、正本ではない。

```text
Candidate
Review
Revision履歴
Context
Audit
Log
Staging
Orphan
進捗表示用summary
```

補助情報が欠落しても、採用済みStory状態を変更してはならない。

---

# Part II: Workspace構成

## 6. 推奨構成

```text
workspace/
├── input/
│   ├── brief.json
│   ├── keywords.json
│   └── source.json
│
├── runtime/
│   ├── run-state.json
│   ├── counters.json
│   ├── config.json
│   ├── lock
│   ├── staging/
│   ├── candidates/
│   ├── calls/
│   └── orphans/
│
├── design/
│   ├── initial/
│   ├── series-plans/
│   ├── volume-plans/
│   ├── chapter-plans/
│   └── scene-plans/
│
├── generations/
│   └── gen-000001/
│
├── scenes/
│   └── scene-v01-c001-s001/
│
├── handoffs/
│   └── handoff-v01/
│
├── completion/
│   └── completion-000001/
│
├── publications/
│   └── pub-000001/
│
└── logs/
    └── storycraft.log
```

`input/`には利用者入力、`design/`には採用済み設計と計画、`runtime/`には実行制御と一時情報を置く。

---

## 7. Workspace root

Workspace rootは、一作品シリーズの永続領域である。

一つのworkspaceへ複数シリーズを混在させない。

Workspace rootはCLIで明示するか、新規作成時に決定する。

---

## 8. Workspace識別

Workspaceは永続的な`workspace_id`を持つ。

`workspace_id`はrunごとに変えない。

推奨例:

```text
ws-01J2V6M1N6...
```

表示用作品名とworkspace識別子を分離する。

---

## 9. 初期作成

新規workspace作成時は、最終workspace pathへ直接大量のfileを順次書かない。

推奨手順:

```text
1. 親directory内に一時workspace directoryを作る
2. 必須directoryを作る
3. 初期config、run-state、countersを書く
4. 読み直して検証する
5. 最終workspace名へrenameする
6. lockを取得してrunを開始する
```

最終workspace pathが既に存在する場合は上書きしない。

---

## 10. 必須directory

起動時に次のdirectoryが存在しなければならない。

```text
input/
runtime/
runtime/staging/
runtime/candidates/
runtime/calls/
runtime/orphans/
design/
generations/
scenes/
handoffs/
completion/
publications/
logs/
```

不足している場合:

- 新規workspace作成中なら作成できる。
- 既存workspaceの再開時は、欠落理由を判断する。
- 正本directoryの欠落を黙って作り直してはならない。

---

## 11. Path命名

Pathは次を優先する。

```text
人間が意味を理解できる
辞書順が実行順と一致する
永続IDを含む
大文字小文字の揺れがない
```

推奨:

```text
gen-000012
pub-000001
scene-v01-c003-s002
handoff-v04
series-plan-v0002
```

---

## 12. Path安全性

利用者入力からpathを作る場合は、次を拒否する。

```text
absolute path
..
NUL
path separatorを含む識別子
workspace外を指すsymlink
予約device名
空文字
```

保存先は解決後にworkspace root内であることを確認する。

---

# Part III: 実行状態

## 13. `run-state.json`

`runtime/run-state.json`は、現在の実行位置を表す唯一の正本である。

代表構造:

```json
{
  "schema_version": 1,
  "workspace_id": "ws-01J2V6M1N6",
  "run_id": "run-000001",
  "status": "running",
  "current_stage": "scene_prose",
  "current_target": {
    "volume_number": 1,
    "chapter_number": 1,
    "scene_number": 2
  },
  "current_generation_id": "gen-000005",
  "current_publication_id": null,
  "active_candidate": {
    "kind": "scene_prose",
    "candidate_id": "candidate-000018",
    "version": 2
  },
  "active_scene_id": "scene-v01-c001-s002",
  "pending_commit": null,
  "stop_reason": null,
  "last_error": null,
  "created_at": "2026-07-23T10:00:00Z",
  "updated_at": "2026-07-23T12:00:00Z"
}
```

---

## 14. Run status

推奨状態:

```text
initializing
running
stopping
stopped
blocked
failed
completed
```

意味:

| 状態 | 意味 |
|---|---|
| `initializing` | workspace初期化中 |
| `running` | 正常実行中 |
| `stopping` | 安全な停止境界へ移行中 |
| `stopped` | 再開可能な利用者停止 |
| `blocked` | 人間確認が必要 |
| `failed` | 自動再試行不能な技術失敗 |
| `completed` | Publication確定済み |

---

## 15. `current_stage`

`current_stage`は意味的Stage IDを持つ。

内部の次の処理をStage IDにしない。

```text
file_validate
allocate_id
rename_directory
update_state
write_log
```

Stage IDは`PIPELINE.md`で定義する。

---

## 16. `current_target`

`current_target`は、現在処理している論理対象を示す。

対象に応じて次を持つ。

```text
series
volume_number
chapter_number
scene_number
artifact_id
```

無関係なfieldを大量に`null`で持たせるより、対象型ごとの構造を使用してよい。

---

## 17. `current_generation_id`

`current_generation_id`は、現在採用済みStory状態を指す。

指し先が存在しない場合は重大な不整合である。

起動時に必ず確認する。

---

## 18. `current_publication_id`

Publicationが未作成なら`null`とする。

Publication作成後は、最新の正式Publicationを指す。

`completed`のrunでは`null`であってはならない。

---

## 19. `active_candidate`

未採用Candidateがない場合は`null`とする。

Candidateがある場合は、少なくとも次を示す。

```text
kind
candidate_id
version
```

Candidate path自体をAuthorityにしない。

---

## 20. `active_scene_id`

Scene処理中でない場合は`null`とする。

Scene処理中は、Scene CardからScene確定まで同じScene IDを保持する。

---

## 21. `pending_commit`

`pending_commit`は、immutable directoryの確定と最後の`run-state.json`更新をまたぐ操作で必ず使用する。

Version 1で対象となる操作は次の二つである。

| `kind` | 確定対象 | 必須field |
|---|---|---|
| `scene_commit` | Scene directoryとGeneration directory | `kind`, `target_id`, `expected_generation_id`, `phase` |
| `publication` | Publication directory | `kind`, `target_id`, `phase` |

Scene Commitの例:

```json
{
  "kind": "scene_commit",
  "target_id": "scene-v01-c001-s002",
  "expected_generation_id": "gen-000006",
  "phase": "prepared"
}
```

`pending_commit`設定中は、次を維持する。

```text
current_stage:
  確定操作のStage

current_target:
  確定対象

current_generation_id:
  Scene Commitでは親Generation

active_scene_id:
  Scene Commitではtarget_idと同じScene ID
```

`pending_commit`は確定意図と予定IDだけを示す短い状態であり、成果物一覧、hash、file graphを持つManifestではない。

---

## 22. Pending phase

Phaseは`kind`ごとに次へ固定する。

```text
scene_commit:
  prepared
  scene_finalized
  generation_finalized

publication:
  prepared
  publication_finalized
```

意味:

| Phase | 意味 |
|---|---|
| `prepared` | 全stagingを検証し、finalize開始をrun-stateへ記録済み |
| `scene_finalized` | Scene final directoryの存在と完全性を確認済み |
| `generation_finalized` | Generation final directoryの存在と完全性を確認済み |
| `publication_finalized` | Publication final directoryの存在と完全性を確認済み |

Directory rename直後、phase更新前にCrashし得る。Recoveryはphaseだけで判断せず、予定ID、staging、final directory、current pointerを再検証して、実在する完全な成果物まで前進する。

`state_updated` phaseは設けない。最後のrun-state更新では、pointer、次Stage、次target、active状態、`pending_commit: null`を一回のatomic replacementで確定する。

---

## 23. `stop_reason`

`stopped`、`blocked`、`failed`の場合は、利用者が理解できる停止理由を持つ。

推奨:

```text
user_requested
budget_exhausted
revision_limit
provider_unavailable
invalid_workspace
completion_incomplete
manual_review_required
```

自由記述だけでなく、機械判定用codeと説明を分ける。

---

## 24. `last_error`

`last_error`は期待された停止原因の要約である。

代表構造:

```json
{
  "code": "SCENE_REVISION_LIMIT",
  "message": "Scene本文のRevision上限に達しました。",
  "stage": "scene_prose",
  "target": "scene-v01-c001-s002",
  "recoverable": true
}
```

Credential、Provider raw body、不要なtracebackを含めない。

---

## 25. Run stateの更新

Run stateは必ず完全fileとして更新する。

手順:

```text
1. 現在値をmemoryで複製
2. 新しい状態へ変更
3. Schemaとcross-field制約を検証
4. 一時fileへ書く
5. fileをflushする
6. 必要に応じてfileをfsyncする
7. 一時fileを読み直す
8. 最終pathへatomic replaceする
9. 必要に応じて親directoryをfsyncする
```

OS互換性の詳細は実装で吸収する。

---

## 26. Run stateの不変条件

```text
statusがcompletedならcurrent_publication_idが存在
statusがrunningならstop_reasonはnull
active_scene_idがあるならcurrent_targetはSceneを示す
current_generation_idは存在するGenerationを指す
current_publication_idは存在するPublicationを指す
pending_commitは同時に一つだけ
updated_atは後退しない
```

---

# Part IV: Counter

## 27. `counters.json`

`runtime/counters.json`は永続IDの次番号を管理する。

代表構造:

```json
{
  "schema_version": 1,
  "next_run": 2,
  "next_generation": 7,
  "next_publication": 1,
  "next_candidate": 19,
  "next_review": 8,
  "next_revision": 5,
  "next_call": 41,
  "next_completion": 1,
  "next_evidence": 128,
  "next_update": 128,
  "updated_at": "2026-07-23T12:00:00Z"
}
```

---

## 28. Counterの対象

Counterは、全データ型へ機械的に追加しない。

必要な対象:

```text
run
generation
publication
candidate
review
revision
provider call
completion
evidence
update
```

自然な複合IDを持つScene、Volume、ChapterにはCounterを使わなくてもよい。

---

## 29. ID割当

IDは使用前に予約する。

手順:

```text
1. Counterを読む
2. 現在のnext値をIDとして予約
3. next値を増やしたCounterをatomic replacement
4. 予約したIDで処理を開始
```

処理失敗で番号が欠けても再利用しない。

---

## 30. Counter不整合

次の場合は人間対応とする。

```text
Counterが読めない
next値が0以下
既存最大ID以上になっていない
同じIDの成果物が既にある
複数種類で同じCounter fieldを誤用
```

自動的に既存directoryを走査して値を変更するRecoveryは標準動作にしない。

診断commandとして最大値候補を表示してよい。

---

# Part V: 設定

## 31. `config.json`

`runtime/config.json`は、run開始時にmaterializeした完全設定を保存する。

Credential値は保存しない。

代表分類:

```text
provider
model_by_operation
retry
timeout
budget
language
review
publication
logging
```

---

## 32. 設定の固定

Run開始後は、原則として同じmaterialized configを使用する。

再開時に環境側の既定値が変わっても、保存済み設定を優先する。

Credentialの実値だけは再開時に環境から取得する。

---

## 33. 設定変更

途中で設定を変更する場合は、明示的な操作とする。

少なくとも次を記録する。

```text
変更前
変更後
変更理由
変更時Stage
変更日時
```

単に環境変数や既定値が変わっただけで、run設定を黙って変更しない。

---

# Part VI: Lock

## 34. Lockの目的

Lockは、一つのworkspaceへ複数processが同時に書き込むことを防ぐ。

Lockは次を保証しない。

```text
remote host間の分散合意
network filesystem上の完全な安全性
強制終了後の完全なprocess生存判定
外部editorによる変更防止
```

---

## 35. Lock file

推奨path:

```text
runtime/lock
```

代表内容:

```json
{
  "workspace_id": "ws-01J2V6M1N6",
  "process_id": 12345,
  "host": "local-machine",
  "run_id": "run-000001",
  "acquired_at": "2026-07-23T10:00:00Z"
}
```

Lock fileの内容は診断用であり、排他自体はOSのfile lock機構で実現する。

---

## 36. Lock取得順

起動時:

```text
1. Workspace rootを解決
2. runtime/lockを開く
3. 排他lockを取得
4. 取得後にworkspace検証を行う
5. run-stateを読む
```

Workspace検証前に正本fileを書き換えない。

---

## 37. Lock競合

Lockを取得できない場合:

```text
別processが使用中
```

として終了する。

既存lock fileのprocess IDだけを見て、他processのlockを自動破棄しない。

---

## 38. Lock解放

正常終了、利用者停止、期待された失敗ではLockを解放する。

強制終了時はOSが排他lockを解放することを前提とする。

Lock file自体が残っていても、OS lockを取得できるなら再利用してよい。

---

# Part VII: Atomic file replacement

## 39. 対象

次の変更可能fileはatomic replacementする。

```text
runtime/run-state.json
runtime/counters.json
runtime/config.json
進捗用の再生成可能summary
```

確定済み成果物fileを個別に置換する用途には使わない。

---

## 40. 一時file名

一時fileは同じdirectoryに作る。

例:

```text
run-state.json.tmp-<process-id>-<random>
```

同一filesystem内のatomic replacementを確保するためである。

---

## 41. 書込検証

一時fileは最終fileへ置換する前に読み直し、少なくとも次を確認する。

```text
JSONとして読める
Schemaを満たす
workspace_idが一致
予想したversionである
必須参照が解決する
```

---

## 42. 古い一時file

起動時に残った`.tmp-*`は正本として採用しない。

処理:

```text
最終fileが正常:
  古い一時fileをorphansへ移動または削除

最終fileが不正:
  一時fileから自動復元しない
  人間対応
```

一時fileが新しいという理由だけで正本にしない。

---

# Part VIII: Staging directory

## 43. Stagingの目的

`runtime/staging/`は、複数fileから成る成果物を最終確定前に完成させる場所である。

Stagingは採用済み成果物ではない。

---

## 44. Staging命名

推奨:

```text
runtime/staging/
  scene-scene-v01-c001-s002/
  generation-gen-000006/
  publication-pub-000001/
  completion-completion-000001/
```

同じ論理対象について複数のactive staging directoryを作らない。

---

## 45. Staging metadata

必要なら、各staging directoryへ短い`staging.json`を置いてよい。

例:

```json
{
  "kind": "scene",
  "target_id": "scene-v01-c001-s002",
  "run_id": "run-000001",
  "stage": "scene_commit",
  "created_at": "2026-07-23T12:00:00Z"
}
```

これは診断情報であり、Manifest graphではない。

---

## 46. Staging完成条件

最終rename前に、成果物種別ごとの必須fileと不変条件を確認する。

共通確認:

```text
必須fileが存在
一時fileが残っていない
JSONが読める
参照が解決
target IDがdirectory名と一致
空本文がない
同じ最終pathが存在しない
```

---

## 47. Finalize

一つのimmutable directoryをfinalizeする共通手順:

```text
1. staging directoryを完成させる
2. 全fileを読み直して成果物契約を検証する
3. 必要に応じてfileとstaging directoryをfsyncする
4. 最終pathが不存在であることを確認する
5. 同一filesystem内でrenameする
6. 最終directoryを読み直して同じ契約を検証する
7. 必要に応じて親directoryをfsyncする
```

この共通処理は`run-state.json`を更新しない。複数directoryを扱うScene Commitと、Publication finalizeは、それぞれの確定手順ですべてのdirectoryを確認した後にrun-stateを更新する。

---

## 48. 最終path競合

最終pathが既に存在する場合は上書きしない。

次を確認する。

```text
既に同じ操作で確定済みなのか
別内容の競合作品なのか
Recovery途中なのか
```

自動削除、自動置換、自動version繰上げを行わない。

---

# Part IX: Candidate

## 49. Candidate領域

未採用Candidateは次へ置く。

```text
runtime/candidates/<kind>/<candidate-id>/v0001/
```

例:

```text
runtime/candidates/scene-prose/candidate-000018/v0002/
```

---

## 50. Candidate構成

推奨:

```text
candidate.json
content.md
context.json
review.json
revision.json
status.json
```

成果物種別に応じ、不要fileは省略できる。

本文Candidateでは、本文を`content.md`へ置き、metadataを`candidate.json`へ置く。

---

## 51. Candidate status

推奨:

```text
generated
reviewed
needs_revision
accepted
rejected
superseded
```

Candidate statusは作業状態であり、Story世界のAuthorityではない。

---

## 52. Candidate上書き

同じCandidate versionを上書きしない。

Revisionは新しいversion directoryを作る。

未完成のversionはstagingまたは一時fileで作り、完成後にversion directoryとして確定する。

---

## 53. Candidate保持

Version 1では、次を保持する。

```text
採用されたCandidate
最後にRejectされたCandidate
対応するReviewとRevision情報
```

古いCandidateを無期限に保持するかは設定可能にしてよい。

削除しても採用済みStory状態へ影響してはならない。

---

# Part X: DesignとPlan

## 54. Initial Design

採用済みInitial Designは次へ置く。

```text
design/initial/v0001/
```

推奨構成:

```text
concept.json
characters.json
relationships.json
world.json
knowledge.json
threads.json
ending.json
arcs.json
metadata.json
```

統合版として一つの`initial-design.json`へまとめてもよい。

実装では、読みやすさとatomic確定単位を優先して選ぶ。

---

## 55. Plan directory

推奨:

```text
design/series-plans/series-plan-v0001/
design/volume-plans/v01-v0001/
design/chapter-plans/v01-c001-v0001/
design/scene-plans/v01-c001-s001-v0001/
```

採用済みPlanはimmutableとする。

---

## 56. Plan metadata

各Planは少なくとも次を識別できる。

```text
plan_id
version
basis_generation_id
parent_plan_id
status
created_at
```

採用済みPlanは`status: accepted`とする。

---

## 57. Planの現在版

「現在のPlan」を示す独立pointerを正本にしない。

現在使用するPlan versionは、run-stateのtargetと上位Plan参照から決定する。

必要なら再生成可能なindexを作ってよい。

---

# Part XI: Generation

## 58. Generation構成

```text
generations/gen-000006/
├── canon.json
├── state.json
├── evidence.json
└── commit.json
```

Generation directoryはimmutableとする。

---

## 59. Generation必須条件

```text
generation_idがdirectory名と一致
parent_generation_idが存在、またはInitial Generation
canon.jsonが読める
state.jsonが読める
evidence.jsonが読める
commit.jsonが読める
全参照IDが解決
State不変条件を満たす
```

---

## 60. Generation確定

Scene Commitでは、Scene stagingとGeneration stagingをどちらも完成・検証してから確定を開始する。順序は次へ固定する。

```text
1. Scene stagingとGeneration stagingを完成・検証
2. pending_commitをscene_commit / preparedとしてatomic replacement
3. Scene stagingをfinalize
4. pending_commit.phaseをscene_finalizedへatomic replacement
5. Generation stagingをfinalize
6. pending_commit.phaseをgeneration_finalizedへatomic replacement
7. 次Stageと次targetを採用済みPlanからコードで決定
8. run-stateを一回のatomic replacementで最終更新
```

手順8では少なくとも次を同時に更新する。

```text
current_generation_id:
  新Generation ID

current_stage:
  scene_plan、chapter_plan、またはvolume_handoff

current_target:
  PIPELINE.md §78で決定した次対象

active_candidate:
  null

active_scene_id:
  null

pending_commit:
  null
```

Scene Commit中は`current_generation_id`を親Generationのまま維持する。手順8より前に新Generationを現在状態として公開してはならない。

---

## 61. Scene確定順の理由

GenerationのEvidenceとCommitは確定済みSceneを参照するため、Sceneを先にfinalizeする。

これにより、Sceneが存在しないGenerationを現在状態として採用する経路をなくす。Scene finalize後、Generation finalize前のCrashは§93の前進Recoveryで処理する。

---

## 62. Initial Generation

Initial GenerationはInitial Design採用後に作る。

Initial Generation確定後に、初めて`current_generation_id`を設定する。

Initial Generationがない状態でSeries Plan以降へ進まない。

---

# Part XII: Scene

## 63. Scene構成

```text
scenes/scene-v01-c001-s002/
├── scene-card.json
├── prose.md
├── continuity.json
└── commit.json
```

必要に応じて`metadata.json`を追加してよいが、`commit.json`と内容を重複させない。

---

## 64. Scene必須条件

```text
scene_idがdirectory名と一致
scene-card.jsonとcontinuity.jsonのscene_idが一致
prose.mdが空でない
basis_generation_idが一致
Evidenceのquoteがprose.mdに存在
許可外更新がない
result_generation_idが予定値と一致
```

---

## 65. Scene本文

`prose.md`には物語本文だけを置く。

次を含めない。

```text
JSON front matter
Review
内部ID一覧
Prompt
Provider情報
継続性操作
```

Publication時の章題などは別情報から組み立てる。

---

## 66. Scene version

同じ論理Sceneを修正して再採用する必要がある場合は、Scene versionを明示する。

推奨選択肢:

```text
scene-v01-c001-s002-v0002/
```

またはScene directory内にversion別directoryを持つ。

Version 1の初期実装では、採用後Sceneの修正workflowを必須にせず、将来追加してよい。

---

# Part XIII: Handoff

## 67. Handoff構成

```text
handoffs/handoff-v01/
├── handoff.json
└── summary.md
```

`summary.md`は人間確認用であり、構造化正本は`handoff.json`である。

同じ内容を独立authorityとして扱わない。

---

## 68. Handoff確定

HandoffはVolume末尾のGenerationを基準にstagingで作成し、検証後にfinalizeする。

Run stateは、次のVolume計画またはCompletion Stageへ移るときに更新する。

---

# Part XIV: Completion

## 69. Completion構成

```text
completion/completion-000001/
├── result.json
└── summary.md
```

`summary.md`は利用者向け表示用であり、`result.json`から再生成可能でなければならない。

---

## 70. Completion確定

Completion Resultは一度の意味評価結果として保存する。

`incomplete`も正式なCompletion Resultである。

ただし、Publication作成条件は満たさない。

---

## 71. Completionとrun-state

Completion Resultが:

```text
complete:
  Publicationへ進む

complete_with_issues:
  注意事項を保持してPublicationへ進む

incomplete:
  statusをblocked
  stop_reasonをcompletion_incomplete
```

`incomplete`を`failed`として扱わない。

---

# Part XV: Publication

## 72. Publication構成

```text
publications/pub-000001/
├── series.md
├── v01.md
├── v02.md
├── metadata.json
└── completion.json
```

巻数に応じて巻別Markdownを増やす。

---

## 73. Publication staging

Publicationは次へ全内容を作る。

```text
runtime/staging/publication-pub-000001/
```

最終directory内へ順次fileを書き足さない。

---

## 74. Publication検証

Finalize前に確認する。

```text
Completionがcompleteまたはcomplete_with_issues
series.mdが空でない
全巻Markdownが存在
巻順とScene順がPlanと一致
metadataの巻数がfile数と一致
private情報がない
JSONが読める
最終pathが存在しない
```

---

## 75. Publication finalize

手順は次へ固定する。

```text
1. Publication stagingを完成・検証
2. pending_commitをpublication / preparedとしてatomic replacement
3. Publication stagingをfinalize
4. pending_commit.phaseをpublication_finalizedへatomic replacement
5. run-stateを一回のatomic replacementで最終更新
```

手順5では次を同時に更新する。

```text
current_publication_id:
  新Publication ID

status:
  completed

active_candidate:
  null

active_scene_id:
  null

pending_commit:
  null
```

独立Publication Gateは作らない。

---

## 76. Publication再生成

同じGenerationから再生成する場合も、新しいPublication IDを使う。

過去Publicationを上書きしない。

同じ内容であっても、再生成操作として別Publicationにしてよい。

---

# Part XVI: AuditとLog

## 77. Provider call記録

各Provider callは次へ保存する。

```text
runtime/calls/call-000041/
```

推奨構成:

```text
request.json
response.json
result.json
error.json
```

CredentialやAuthorization headerを含めない。

---

## 78. Call result

`result.json`は少なくとも次を持つ。

```text
call_id
stage
target
provider
model
started_at
finished_at
usage
outcome
```

`outcome`:

```text
success
transport_error
timeout
format_error
cancelled
```

---

## 79. Raw response

Raw response保存は設定可能とする。

保存する場合でも、秘密情報を除去する。

Raw responseを採用済みCandidateの正本にしない。

---

## 80. Application log

`logs/storycraft.log`は診断用の追記logである。

Logをrun-stateの代わりにしない。

Logが途中で欠落またはtruncateしても、Recovery判断を変えてはならない。

---

# Part XVII: 起動検証

## 81. 起動順

既存workspaceを開くときは次の順で確認する。

```text
1. Workspace rootを安全に解決
2. Lockを取得
3. 必須directoryを確認
4. run-state、counters、configを読み、各Schemaを検証
5. workspace_idの一致を確認
6. current Generationとcurrent Publicationを確認
7. pending_commitがあれば、ProviderやStageを起動する前にRecovery
8. pending_commitがなければ、stagingとactive Candidateを確認
9. resume、regenerate、manualを決定
```

Recovery完了前にProvider clientを生成せず、Provider callを行わない。

---

## 82. Schema version

各制御fileは`schema_version`を持つ。

対応外versionの場合は自動的に解釈しない。

移行処理がある場合だけ明示的に実行する。

---

## 83. Workspace ID整合性

次の`workspace_id`は一致しなければならない。

```text
run-state
config
lock診断情報
必要なroot metadata
```

別workspaceのfileが混在している場合は人間対応とする。

---

## 84. Current Generation確認

確認:

```text
directoryが存在
必須fileが存在
JSONが読める
generation_idが一致
parent参照が妥当
State不変条件を満たす
```

不正なら自動的に一つ前のGenerationへ戻らない。

---

## 85. Current Publication確認

`current_publication_id`がある場合:

```text
directoryが存在
metadataが読める
completionが読める
全必須Markdownが存在
```

`status: completed`なのに不正なら人間対応とする。

---

# Part XVIII: Recovery分類

## 86. 三分類

Recovery結果は次のいずれかである。

```text
resume:
  既存の確定状態から続行

regenerate:
  未採用の途中作業を捨て、同じStageを再実行

manual:
  自動判断せず利用者対応を要求
```

---

## 87. Resume

Resume可能条件:

```text
run-stateが正常
current Generationが正常
必要な採用済みPlanが正常
pending_commitがない、または自動確定可能
現在Stageの入力が揃っている
競合する最終成果物がない
```

---

## 88. Regenerate

Regenerate対象:

```text
不完全Candidate
不完全Review
Contextだけ存在
Stagingだけ存在
format error後の未採用応答
Scene本文はあるがContinuityが未完成
Publication stagingが不完全
```

採用済み成果物は削除しない。

---

## 89. Manual

人間対応条件:

```text
run-stateが読めない
countersが読めない
current Generationがない
Generation内容が不正
同じIDのfinal directoryが競合
pending_commitの意図と実在成果物が矛盾
workspace_idが不一致
Completionがincomplete
completed runのPublicationが不正
```

---

# Part XIX: Scene Commit Recovery

## 90. Scene Commitの正常状態

正常完了後は次をすべて満たす。

```text
Scene final directory:
  完全な予定Sceneが存在

Generation final directory:
  完全な予定Generationが存在

run-state.current_generation_id:
  予定Generation ID

run-state.current_stage / current_target:
  PIPELINE.md §78で決定した次処理

run-state.active_candidate:
  null

run-state.active_scene_id:
  null

run-state.pending_commit:
  null
```

Recoveryは後退させず、この正常状態へだけ前進する。

---

## 91. Crash位置A: pending設定前

`pending_commit`がなく、Scene finalとGeneration finalもない場合、stagingは未採用である。

```text
完全または不完全なstaging:
  orphansへ移す

run-state:
  current Generationとscene_commit targetを維持

再開:
  scene_commit入力を再検証し、必要なstagingをコードで再構築
```

Provider callは不要である。予定IDと一致しないfinal directoryがある場合は§96のmanualとする。

---

## 92. Crash位置B: pending設定後・Scene finalize前

条件:

```text
pending_commit:
  scene_commit / prepared

Scene final:
  なし

Generation final:
  なし
```

両stagingが完全で予定IDと一致すれば、§60の手順3から再開する。

stagingが欠落または不完全でもfinal directoryが一つもなければ、安全に次を行う。

```text
不完全stagingをorphansへ移す
pending_commitをnullへatomic replacement
同じscene_commitをコードだけで再準備
```

---

## 93. Crash位置C: Scene finalize後

Scene finalが完全で予定IDと一致し、Generation finalがない場合は、Scene finalを削除・置換しない。

Generation stagingが完全なら、そのstagingをfinalizeする。欠落または不完全なら、次からGeneration stagingを決定的に再構築する。

```text
run-state.current_generation_idが指す親Generation
確定済みSceneのcontinuity.json
確定済みSceneのcommit.json
確定済みScene本文に一致するEvidence
pending_commit.expected_generation_id
```

再構築時は新しいID、物語上の事実、commit時刻を生成しない。Generationの`created_at`などの確定metadataは親Generation、Sceneの`commit.json`、既存の予定IDから決定し、同じ入力から同じ論理成果物を作る。

再構築後にGeneration契約を満たせば、Generationをfinalizeして§60の手順6以降へ進む。再構築結果が契約を満たさない場合だけmanualとする。

Recovery中にScene生成、Continuity生成、その他のProvider callを行わない。

---

## 94. Crash位置D: Generation finalize後

Scene finalとGeneration finalがどちらも完全で予定IDと一致し、`current_generation_id`が親Generationのままなら、次を行う。

```text
pending_commit.phaseをgeneration_finalizedとして整合
次Stageと次targetを採用済みPlanから再計算
§60の最終run-state更新を実行
```

Phaseが`prepared`または`scene_finalized`のままでも、完全なfinal directoryを再検証できれば前進してよい。新しいProvider callは行わない。

---

## 95. Crash位置E: 最終run-state更新の前後

最終run-state更新は一回のatomic replacementであるため、起動後に観測される正常形は次のどちらかである。

```text
更新前:
  current Generationは親
  current_stageはscene_commit
  pending_commitあり

更新後:
  current Generationは新Generation
  current_stageとcurrent_targetは次処理
  active_candidateはnull
  active_scene_idはnull
  pending_commitはnull
```

両final directoryが完全なのに更新前の形なら§94として完了する。新Generationを指しながら`pending_commit`が残る状態はVersion 1の書込手順では生成しないため、発見した場合は全fieldと成果物が正常形に一致するときだけpendingを除去し、それ以外はmanualとする。

---

## 96. Scene Commitのmanual条件

次のいずれかは自動修復しない。

```text
pending_commitがないのにScene finalだけが存在
予定IDと異なるSceneまたはGeneration finalが存在
同じ予定IDのfinal内容がpendingの意図と競合
親Generationが欠落または不正
確定済みSceneが不完全
Generationの決定的再構築が契約違反
current_generation_idが親でも予定Generationでもない
```

Final directoryを削除、上書き、別IDへ移動して推測修復してはならない。

---

# Part XX: Publication Recovery

## 97. Crash位置A: Publication rename前

`pending_commit`がなくPublication finalもない場合、stagingは未採用としてorphansへ移し、Publication Stageを再実行できる。

`publication / prepared`があり、完全な予定stagingが存在する場合はfinalizeを再開する。stagingが不完全でfinalがなければ、stagingをorphansへ移し、pendingをnullへ戻して決定的に再生成する。

---

## 98. Crash位置B: Publication rename後

Publication finalが完全で予定IDと一致する場合は、phaseにかかわらず次へ前進する。

```text
pending_commit.phaseをpublication_finalizedとして整合
current_publication_idを予定IDへ設定
statusをcompletedへ設定
active状態とpending_commitをnullへ設定
```

これらは最後の一回のatomic run-state replacementで行う。Provider callや本文再生成は行わない。

---

## 99. Publicationのmanual条件

次のいずれかはmanualとする。

```text
予定IDと異なるPublication finalが存在
同じ予定IDのPublication内容がpendingの意図と競合
Completion参照が不正
completed runのPublicationが不完全
current_publication_idが予定IDと競合
```

`completed`かつ正常なPublicationを指している場合、`pending_commit`は必ずnullでなければならない。

---

# Part XXI: Orphan

## 100. Orphanの目的

`runtime/orphans/`は、自動採用しない途中成果物を隔離する。

例:

```text
古い一時file
不完全staging
基準Generationが古いCandidate
Recoveryで利用しなかったContext
```

Quarantine分類を複雑化しない。

---

## 101. Orphan命名

推奨:

```text
runtime/orphans/
  20260723T120000Z-scene-v01-c001-s002/
```

必要に応じて`reason.json`を置く。

```json
{
  "reason": "incomplete_staging",
  "original_path": "runtime/staging/scene-scene-v01-c001-s002",
  "moved_at": "2026-07-23T12:00:00Z"
}
```

---

## 102. Orphan保持

Orphan保持期間は設定可能とする。

自動削除する場合も、確定済み成果物を対象にしてはならない。

---

# Part XXII: 利用者操作

## 103. `run`

`run`は新規workspaceだけを対象にする。

既存workspaceがある場合は、`resume`を案内する。

---

## 104. `resume`

`resume`は起動検証とRecovery分類を行う。

結果:

```text
resume:
  実行続行

regenerate:
  利用者へ再生成対象を表示して続行

manual:
  理由と必要な確認を表示して終了
```

---

## 105. `step`

`step`は一つの意味的Stageを完了する。

Stage内部の確定処理が完了する前に正常終了しない。

Crashした場合は通常のRecovery規則を使う。

---

## 106. 停止要求

停止要求を受けた場合:

```text
新しいProvider callを開始しない
現在のresponse処理を安全に終了
未採用Candidateを保存
run-stateをstoppedへ更新
lockを解放
```

Scene CommitまたはPublication finalize中は、確定操作を完了してから停止してよい。

---

# Part XXIII: Error分類

## 107. Expected error

利用者へ簡潔に示すerror:

```text
入力不正
lock競合
budget到達
Revision上限
Completion incomplete
Provider timeout
対応外Schema
人間確認が必要なworkspace不整合
```

---

## 108. Internal error

予期しない実装errorは、診断IDとlog位置を示す。

利用者表示へ不要なstack traceを直接出さない。

開発modeではtracebackを別出力してよい。

---

## 109. Error code

Error codeは安定した文字列とする。

例:

```text
WORKSPACE_LOCKED
RUN_STATE_INVALID
CURRENT_GENERATION_MISSING
COUNTER_CONFLICT
SCENE_REVISION_LIMIT
PROVIDER_TIMEOUT
COMPLETION_INCOMPLETE
PUBLICATION_INVALID
```

---

# Part XXIV: Invariant

## 110. Workspace全体の不変条件

```text
書き込みwriterは一つ
run-stateは一つ
current Generationは一つ
current Publicationは0または1
pending commitは0または1
確定済みdirectoryは上書きしない
最終directoryに一時fileを残さない
採用済み成果物は参照解決可能
```

---

## 111. Run不変条件

```text
running中はlockを保持
completedならPublicationが存在
blockedなら停止理由が存在
active Scene中は基準Generationが固定
新しいIDはCounter予約済み
```

---

## 112. Scene Commit不変条件

```text
Scene PlanからScene Commitまでbasis Generationが固定
pending開始前にSceneとGenerationの両stagingが完全
Scene finalより先にGeneration finalを作らない
Scene finalとGeneration finalは予定IDと一致
Canonは親Generationから変更しない
Evidenceは確定本文に存在
Updateはallowed_updatesとAuthorityの範囲内
current Generationの切替は最後のrun-state更新だけで行う
正常完了後はactive_scene_idとpending_commitがnull
確定済みfinal directoryを削除または上書きしない
```

---

## 113. Publication不変条件

```text
Completionが公開可能
全巻が存在
本文順がPlanと一致
private情報がない
completed runはPublicationを指す
```

---

# Part XXV: 削除する旧設計

## 114. 削除対象

新設計では次を使用しない。

```text
canon/HEADを正本にする仕組み
output/CURRENTを正本にする仕組み
Candidate Manifest
Checkpoint Manifest
Commit Manifest graph
Generation Manifest graph
Publication Validation Manifest
Publication Gate
Context hash path
本文hash
Evidence hash
Publication集合hash
Manifest reachabilityによるRecovery
```

---

## 115. 旧workspaceの扱い

旧設計workspaceから新設計workspaceへの自動移行は、Version 1初期実装の必須範囲にしない。

選択肢:

```text
開発中workspace:
  再生成

保存価値のあるworkspace:
  専用migration commandを別途設計

公開済み成果物:
  読取専用archiveとして保持
```

---

# Part XXVI: 実装指針

## 116. Workspace API

Production codeは、file操作をWorkspace APIへ集約する。

代表操作:

```text
load_run_state
replace_run_state
allocate_id
load_generation
prepare_staging
finalize_directory
load_candidate
save_candidate_version
inspect_recovery
move_to_orphans
```

Stage実装が自由にpathを組み立てて直接書き込むことを避ける。

---

## 117. Productionとtest

Testはproductionと同じ次を使用する。

```text
serializer
Schema validator
path builder
atomic replacement
finalize処理
Recovery判定
```

Test専用の簡略保存形式を作らない。

---

## 118. Clockとfilesystem

Testでは次をdependency injectionしてよい。

```text
clock
random suffix
process ID
filesystem root
Provider adapter
```

保存意味そのものは変えない。

---

## 119. Crash test

Scene Commitは少なくとも次の故障境界を個別に試験する。

```text
pending_commit保存直前
pending_commit prepared保存直後
Scene rename直後・phase更新前
scene_finalized保存直後
Generation rename直後・phase更新前
generation_finalized保存直後
最終run-state replacement直前
最終run-state replacement直後
```

各ケースでRecoveryを二回以上実行し、次を確認する。

```text
Provider callが発生しない
同じSceneまたはGenerationを重複作成しない
確定済みdirectoryを変更しない
最終run-stateが§90の正常状態と一致
```

Publicationも`prepared`、rename、`publication_finalized`、最終run-state更新の各境界を試験する。

---

## 120. 可観測性

利用者または開発者が次を確認できる診断commandを将来追加してよい。

```text
workspace summary
current run state
current Generation
pending commit
orphan一覧
Recovery判定
Counter状態
```

診断commandは正本を変更しない。

---

# Part XXVII: 受入条件

## 121. 文書受入条件

この文書は次を満たす。

```text
workspace構成とAuthorityが一意
run-stateが唯一の現在位置Authority
変更可能fileとimmutable directoryの更新境界が明確
Scene CommitとPublicationのphaseが固定
SceneとGenerationの確定順が一意
最後のrun-state更新fieldが一意
Crash位置ごとのresume、regenerate、manualが決定的
Scene finalからGenerationをcode-onlyで再構築可能
Recovery中にProvider callを行わない
Hash、Manifest graph、複数pointerへ依存しない
確定済みdirectoryを削除または上書きしない
単一writer・ローカルfilesystem前提と一致
```

---

## 122. 実装完成条件

実装は少なくとも次を自動試験で示す。

```text
新規workspaceを安全に作り、既存workspaceを上書きしない
lock競合を拒否する
run-stateをatomic replacementできる
Counterを安全に予約できる
SceneとGenerationを§60の順序で確定できる
全Scene Commit crash境界からProviderなしで前進できる
Scene finalからGeneration stagingを決定的に再構築できる
Recoveryを反復しても結果が変わらない
Publication crash境界からProviderなしで完了できる
不完全stagingをorphansへ隔離して再生成できる
不正run-state、競合final、欠落Generationを推測修復しない
確定済み成果物を削除または上書きしない
```

---

## 123. 最終原則

Storycraft Version 1の保存と復旧は、次で成立させる。

> 一つのLock、一つのrun-state、完全file更新、immutableな確定済みdirectory、stagingからのrename、単調なID、そして再開・再生成・人間対応の三分類。

これを超えるHash、Manifest、Gate、複数pointer、reachability解析は、具体的な要件が生じるまで導入しない。
