# Storycraft

**一度のBriefまたはKeywordsから、日本語の長編シリーズを計画・執筆・継続性管理・完結監査し、検証済みPublicationとしてローカルに採用するCLI。**

> **Repository status:** package metadataはversion-1開発用の`1.0.0.dev0`です。
> 評価元の`0.1.0` source snapshotには動作するlegacy prototypeがありますが、50 Stage、Generation／`canon/HEAD`、Candidate／Checkpoint、Completion、Publication Gate／`output/CURRENT`を含むproduction codeはまだ受入済みではありません。
> 現在の正確な到達状況は[実装状況](docs/product/IMPLEMENTATION_STATUS.md)を参照してください。

---

## 1. Storycraftが目指すもの

長編シリーズ生成では、Scene本文を一つずつ作るだけでは不十分です。

Storycraft version-1は、次を一つの検証可能なworkspaceで扱います。

```text
BriefまたはKeywords
→ Initial design
→ Series／Volume／Chapter plan
→ Scene Card
→ 日本語本文
→ Continuity／Evidence
→ Scene Commit
→ Volume Handoff
→ Completion audit
→ Publication Validation／Gate
→ Publication adoption
```

利用者が得るもの:

```text
4〜10巻のシリーズ構成
巻内で局所的に解決する物語
章・Scene単位の計画
POVと秘密開示を守る本文
本文根拠付きの状態更新
巻をまたぐHandoff
Required Thread／Endingの完結監査
全巻・巻別Markdown
検証済みmetadataとCompletion report
Crash後に再開可能なworkspace
```

---

## 2. 現在の状態

| 対象 | 状態 |
|---|---|
| version-1製品・設計契約 | 実装前baselineとして確定 |
| package metadata | `1.0.0.dev0`（version-1 development pre-release） |
| 評価元`0.1.0` CLI | legacy prototypeとして動作 |
| 現行fake-model回帰試験 | 合格実績あり |
| version-1 50 Stage engine | 未受入 |
| version-1 Ledger／Generation／HEAD | 未実装 |
| Candidate／Checkpoint／Transaction | 未実装 |
| Completion／Publication Gate／CURRENT | 未実装 |
| version-1 Acceptance ID | 合格証拠0件 |
| Release candidate | **いいえ** |
| Production ready | **いいえ** |

詳細:

- [製品仕様](docs/product/SPECIFICATION.md)
- [要件](docs/product/REQUIREMENTS.md)
- [実装状況](docs/product/IMPLEMENTATION_STATUS.md)
- [実装受入基準](docs/design/implementation_acceptance.md)

---

## 3. 文書の読み方

### 製品

| 文書 | 役割 |
|---|---|
| [要件](docs/product/REQUIREMENTS.md) | 136件のstable Requirement ID |
| [製品仕様](docs/product/SPECIFICATION.md) | 利用者へ保証する振る舞い |
| [実装状況](docs/product/IMPLEMENTATION_STATUS.md) | 現行コードとversion-1契約の差分 |

### 統合設計

| 文書 | 役割 |
|---|---|
| [Engine design](docs/design/series_engine_design.md) | package、engine、storage、provider、recovery構造 |
| [Engine flow](docs/design/series_engine_flow.md) | 50 StageとCrash境界のMermaid図 |
| [Pipeline contracts](docs/design/pipeline_contracts.md) | 全Stage、processor、transition、resume source |
| [Ledger contracts](docs/design/ledger_contracts.md) | Canon、State、Evidence、Runtimeの統合 |
| [Workspace layout](docs/design/workspace_layout.md) | pathとartifact authority |
| [Runtime and recovery](docs/design/runtime_and_recovery.md) | startup、resume、quarantine、manual intervention |
| [Configuration contracts](docs/design/configuration_contracts.md) | provider、retry、budget、profile |
| [Context contracts](docs/design/context_contracts.md) | Context view、秘密除外、token budget |
| [Prompt design](docs/design/prompt_template_design.md) | 30 LLM Stage、14 Schema、package assets |
| [Implementation acceptance](docs/design/implementation_acceptance.md) | stable `ACC-*` test scenarios |

### Field-level contracts

```text
docs/design/contracts/data/
docs/design/contracts/ledger/
docs/design/contracts/pipeline/
```

### Canonical examples

- [Initial and planning fixture](docs/design/examples/initial_and_planning_fixture.md)
- [Scene commit fixture](docs/design/examples/scene_commit_fixture.md)
- [Completion and publication fixture](docs/design/examples/completion_publication_fixture.md)
- [Data-contract example catalog](docs/design/data_contract_examples.md)

FixturesはSchemaの代替ではなく、複数契約が同時に成立する証拠です。

---

# Legacy `0.1.0` source snapshot

## 4. Legacy prototypeでできること

評価元の`0.1.0`コードは、一つの`state.json`を使うlegacy workflowとして次を実行します。

```text
BriefまたはKeywords
→ Characters
→ Relationships
→ World
→ Timeline
→ Threads
→ Volume map
→ Volume chapters
→ Scene Card
→ JSON-wrapped Scene prose
→ Continuity state updates
→ Volume summary
→ Closure
→ Markdown output
```

公開surface:

```text
storycraft run
storycraft resume
storycraft step
```

これはversion-1のCanonical 50 Stage workflowとは異なります。

---

## 5. 必要環境

Target package metadata:

```text
Python >= 3.11
Jinja2 >= 3.1,<4
jsonschema >= 4.23,<5
OpenAI Python client >= 1.50,<3
PyYAML >= 6,<7
Hatchling build backend >= 1.25,<2
OpenAI-compatible endpoint
```

Package metadataの正本は[`pyproject.toml`](pyproject.toml)です。

`1.0.0.dev0`はpre-release markerです。全Required Acceptance Gate通過前にstable `1.0.0`へ変更してはなりません。

Target wheelは`src/storycraft/templates/prompts/`だけをprompt／Schema package-data rootとして含めます。旧repository-root `templates/prompts/`へのfallbackはありません。

---

## 6. 開発install

`venv`と`pip`の例:

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
storycraft --help
```

`uv`を使う例:

```bash
uv venv --python 3.11 .venv
uv pip install -e .
.venv/bin/storycraft --help
```

Source treeを直接使う場合:

```bash
PYTHONPATH=src python -m storycraft.cli --help
```

---

## 7. 現行provider設定

現行prototypeはOpenAI-compatible endpointを想定します。

環境変数:

```bash
export STORYCRAFT_LLM_BASE_URL='http://localhost:11434/v1'
export STORYCRAFT_LLM_MODEL='your-model-name'
```

任意:

```bash
export STORYCRAFT_LLM_FIRST_TIMEOUT='3600'
export STORYCRAFT_LLM_IDLE_TIMEOUT='600'
```

現行prototypeのcredential、timeout cancellation、usage accountingはversion-1契約を満たしていません。外部providerを本番運用する前に[実装状況](docs/product/IMPLEMENTATION_STATUS.md)を確認してください。

---

## 8. 現行config YAML

```yaml
llm:
  base_url: http://localhost:11434/v1
  model: your-model-name
  thinking: true
  stream: true
  first_event_timeout_seconds: 3600
  idle_timeout_seconds: 600
  stream_progress_log_interval_seconds: 60

retry:
  max_attempts: 4

quality:
  max_critique_passes: 1
  improvement_directions:
    - 地の文を削り、くどさを排除する
    - 対話を自然にする
  content_length_target_chars: 2200
  content_length_tolerance_chars: 400

output:
  dir: ./storycraft-out

diversity:
  archive_dir: ~/.storycraft/archive
  recent_window: 5
```

実行:

```bash
storycraft run \
  --out ./my-series \
  --config ./storycraft.yaml \
  --brief ./brief.json
```

このYAMLは現行prototype用です。version-1のEffective config、operation map、budget、publishing／audit profileとは異なります。

---

## 9. 現行Brief形式

評価元のlegacy `0.1.0` validatorが受理する例:

```json
{
  "title": "霧の島の灯",
  "genre": "海洋幻想譚",
  "protagonist": {
    "name": "澪",
    "present_position": "島の灯台守の娘",
    "core_trait": "好奇心が強く粘り強い",
    "current_pressure": "父の不在で灯台を守っている",
    "initial_wish": "父の消息を知りたい"
  },
  "key_people": [
    {
      "name": "父",
      "present_position": "島の灯台守",
      "initial_relation_to_protagonist": "澪の父"
    },
    {
      "name": "凪",
      "present_position": "島へ来た航海士",
      "initial_relation_to_protagonist": "協力者候補"
    }
  ],
  "want": "父の失踪と灯台の秘密を解く",
  "avoid": "救いのない結末",
  "ending": "澪が父の真実を受け入れ、自ら島に残ることを選ぶ",
  "volumes": 4,
  "chapters_per_volume": [3, 3, 3, 3]
}
```

注意:

- Rootの[`example_brief.json`](example_brief.json)は、version-1 Brief modeへ渡す**Brief content candidate**のcanonical exampleです。
- `brief_version`、profile ID、source hash、timestampは含みません。INPUT-01がadopted `input/brief.json`へ追加します。
- 評価元のlegacy `0.1.0` validatorは`avoid`をstringとして扱い、`chapters_per_volume`も使用するため、このversion-1 exampleをそのまま受理しません。legacy prototypeには上記legacy exampleを使用してください。
- Normative Brief定義は[Brief and initial contract](docs/design/contracts/data/brief_and_initial.md)です。

---

## 10. Briefから開始

```bash
storycraft run \
  --out ./my-series \
  --brief ./brief.json
```

JSONまたはYAML objectを指定できます。

既に保存済みのworkspaceへ`run`すると上書きせず失敗します。

---

## 11. Keywordsから開始

```bash
storycraft run \
  --out ./my-series \
  --keywords '霧の島' \
  --keywords '灯台守の娘' \
  --keywords '海洋幻想譚' \
  --keywords '4巻'
```

現行prototypeはKeywordsからlegacy Briefを生成します。

version-1では、Keyword sourceとBriefを別のimmutable adopted artifactとして扱う予定です。

---

## 12. Resume

```bash
storycraft resume \
  --out ./my-series
```

現行prototypeは`state.json`を読み、未完了fieldから処理を続けます。

これはversion-1のpointer、Candidate、Checkpoint、transactionを検証するrecoveryではありません。

---

## 13. Step

新規workspaceの最初のStep:

```bash
storycraft step \
  --out ./my-series \
  --brief ./brief.json
```

既存workspace:

```bash
storycraft step \
  --out ./my-series
```

現行prototypeでは、一つのlegacy semantic工程を進めます。

Scene工程はScene Card、本文、continuity、State mutationを一つの`_run_one`内で処理するため、version-1の「一つのCanonical Stage」とは一致しません。

---

## 14. 現行workspace

代表的な現行layout:

```text
my-series/
  state.json
  storycraft.log

  raw/
    <sequential request/response logs>

  output/
    series.md
    volume-01.md
    volume-02.md
    ...
    quality-acceptances.json
```

現行`state.json`:

```text
version = 5
```

Story truth、execution state、attempts、Closureが一つのmutable objectへ混在します。

version-1はこのlayoutをauthorityとして使用しません。

---

## 15. 現行出力

現行prototypeは最終時に直接`output/`を作ります。

```text
output/
  series.md
  volume-01.md
  volume-02.md
  ...
  quality-acceptances.json
```

現行には次がありません。

```text
Publication ID
Publication Validation
Publication manifest
Publication Gate
output/CURRENT
```

---

## 16. 現行prototypeの制約

現行コードを次の用途へ使わないでください。

```text
version-1 crash-safety検証
strict structured-output保証
credential安全性保証
private/public projection保証
Evidence offset／hash保証
Generation／HEAD保証
Publication Gate保証
production release判定
```

主なlegacy構造:

```text
13 semantic stage names
one mutable state.json
critique／closure terminology
JSON-wrapped prose
source-tree prompt fallback
json_object response mode
direct State mutation
direct final output replacement
```

---

# Version-1 target

## 17. 50 Stage

Canonical Stage family:

| family | count |
|---|---:|
| Input | 3 |
| Initial design | 8 |
| Planning | 12 |
| Scene generation | 12 |
| Scene commit | 4 |
| Volume Handoff | 4 |
| Completion | 3 |
| Publication | 4 |
| **total** | **50** |

完全なregistryは[Pipeline contracts](docs/design/pipeline_contracts.md)を参照してください。

---

## 18. Canonical lifecycle

```text
INPUT-01
→ INPUT-02／03 when Keywords
→ INIT-01..06／REV／ID
→ SERIES-01..ID
→ VOL-01..ID
→ CH-01..ID
→ SC-01..CHK
→ PROSE-01..CHK
→ DELTA-01..CHK
→ COMMIT-01..04
→ next Scene／Chapter／VH
→ VH-01..ID
→ next Volume／COMP-PRE
→ COMP-AUDIT
→ COMP-SAVE
→ OUT-01
→ OUT-02
→ COMP-PUBLISH
→ OUT-03
→ completed
```

未登録transitionは拒否します。

---

## 19. Story adoption

現在の採用済みStory snapshot:

```text
canon/HEAD
```

HEADが選ぶimmutable Generation:

```text
current-canon.json
knowledge-items.json
story-state.json
evidence-index.json
commit-manifest.json
generation-manifest.json
```

Generation directoryが存在するだけではadoptedではありません。

HEADの通常mutation owner:

```text
INIT-ID
COMMIT-04
VH-ID
```

---

## 20. Canon、State、Evidence

### Canon

固定identityと不変事実:

```text
Character
Relationship
World entity
Temporal rule
Thread
Ending criterion
Knowledge item
```

### Story State

現在変化する値:

```text
Character State
directional Relationship State
Thread status／progress／volume disposition
Character／Reader Knowledge
Story clock
```

### Evidence

Scene本文で裏付けられた更新:

```text
literal unique quote
Unicode code-point offsets
quote hash
prose hash
Scene／Commit identity
```

---

## 21. CandidateとReview

候補はversioned immutable historyとして保存します。

```text
runtime/candidates/.../v0001/
runtime/candidates/.../v0002/
```

各version:

```text
candidate artifact
review.json
candidate-manifest.json
```

Active candidateはRun Stateが指すManifestだけです。

次から選択しません。

```text
最大version
最新mtime
raw provider audit
directory scan
```

---

## 22. ReviewとRevision

Review response:

```text
summary
issues
```

Revision:

```text
元candidate contractの完全置換
```

禁止:

```text
patch
diff
修正箇所だけ
Reviewがnext Stageを決める
mechanical errorをresidual issueにする
```

---

## 23. Scene lifecycle

```text
SC-CHK
  → CARD_ACCEPTED

PROSE-CHK
  → PROSE_FROZEN

DELTA-CHK
  → DELTA_ACCEPTED

COMMIT-03
  → COMMIT_PREPARED

COMMIT-04
  → Scene／Generation adoption
```

一つのScene lifecycleは同じsource Generationを使います。

HEADが変わったstale Scene chainをrebaseしません。

---

## 24. Writer-safe本文

Writer Contextは次を含みません。

```text
Thread author truth
Thread resolution condition
Knowledge author truth
Ending private source
非POV人物のprivate emotion／goal／pressure
continuity update mechanics
```

Prose responseは本文だけです。

```text
JSONなし
headingなし
metadataなし
continuity deltaなし
```

---

## 25. Scene Commit

```text
COMMIT-01:
  dry validation
  ID allocationなし

COMMIT-02:
  ID persist-before-use
  Evidence／merge plan
  staged roots

COMMIT-03:
  committed delta
  Scene／Commit／Generation manifests
  transaction Validation
  COMMIT_PREPARED

COMMIT-04:
  final move
  final graph再検証
  canon/HEADを最後に更新
  Run State route
```

Committed deltaとafter rootsは双方向に一致しなければなりません。

---

## 26. Volume Handoff

各巻後に、実際のfinal Scene HEADからHandoffを作ります。

Handoff Commitで変更できるのは:

```text
story-state.json
  thread_states[].volume_disposition
```

だけです。

次は親Generationと同一です。

```text
Canon
Knowledge items
Evidence index
Story clock
Scene order
```

Generation IDは進みますが、Scene orderは進みません。

---

## 27. Completion

Completionはfinal Volume Handoff HEADから開始します。

結果:

```text
complete
complete_with_residual_issues
incomplete
```

最初のstructurally valid assessmentを選びます。

Validな`incomplete`:

```text
再試行しない
本文・Canon・Stateを修正しない
diagnostic artifactsを保存する
Gateをfailにする
CURRENTを変更しない
manual interventionで停止する
```

---

## 28. Publication

Default layout:

```text
publications/pub-000001/
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

Current publication:

```text
output/CURRENT
```

---

## 29. Publication transaction

```text
OUT-01:
  Publication ID
  payload
  provisional build manifest

OUT-02:
  payload_set_sha256
  Publication Validation
  content_set_sha256
  final Manifest

COMP-PUBLISH:
  external rename-stable Gate
  adoptionなし

OUT-03:
  staging rename
  final-root validation
  output/CURRENTを最後に更新
  completed
```

Manifestは自身をhashしません。

ValidationはManifestをhashしません。

---

## 30. CrashとResume

Recovery action:

```text
reconcile
resume
regenerate
quarantine
explicit_recovery
manual_intervention
```

禁止:

```text
最大GenerationをHEADにする
最大PublicationをCURRENTにする
raw audit responseをCandidateへ昇格する
stale Checkpointをrebaseする
ID／usageを返却する
quarantineを自動採用する
```

Pointer更新後にRun Stateだけが遅れている場合、provider callやID allocationを繰り返さずreconcileします。

---

## 31. PrivacyとSecurity

Version-1は次を要求します。

```text
credential値をworkspaceへ保存しない
Writer／Continuity requestからprivate sentinelを除外
Prompt injection文字列をdataとして固定
Publicationからprivate author truthを除外
workspace-relative managed path
path traversal／absolute path／symlink escape拒否
provider以外の外部retrievalなし
```

---

## 32. Package prompt assets

Target asset root:

```text
src/storycraft/templates/prompts/
  prompt-bundle.json
  schema-bundle.json
  registry.json
  system/
  user/
  schemas/
```

Requirements:

```text
30 exact LLM Stage specs
14 exact structured-output Schemas
Prose専用raw-text contract
package-only loading
source-tree fallbackなし
StrictUndefined
strict json_schema
prompt／Schema version resume compatibility
```

---

# Development

## 33. Target architecture

```text
CLI／public API
→ Engine
→ 50-Stage Registry
→ Stage executor
→ Domain services
→ Workspace repositories
→ filesystem
```

LLM path:

```text
Validated authority
→ Context snapshot
→ Prompt bundle
→ Provider adapter
→ Response validation
→ Candidate／Review durability
```

Recommended package structureは[Engine design](docs/design/series_engine_design.md)を参照してください。

---

## 34. 現行repository layout

```text
src/storycraft/
templates/prompts/
tests/
docs/product/
docs/design/
scripts/
pyproject.toml
README.md
example_brief.json
```

Target version-1ではprompt assetsを`src/storycraft/templates/prompts/`へ一本化します。

---

## 35. 現行回帰試験

依存をinstallした環境で:

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -p "test_*.py"
```

現行testsはlegacy behaviorの回帰試験です。

```text
version-1 Acceptance IDの合格証拠ではない
```

評価時の正確な結果は[実装状況](docs/product/IMPLEMENTATION_STATUS.md)を参照してください。

---

## 36. Version-1 canonical release commands

[Implementation acceptance](docs/design/implementation_acceptance.md)が定めるCanonical command:

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -p "test_*.py"
bash scripts/wheel_smoke.sh
```

Version-1 releaseでは、これらが更新済みproduction contractsに対して成功しなければなりません。

現在の`wheel_smoke.sh`はlegacy `closure`／legacy prompt assetsを検証するため、version-1 Gateへ更新が必要です。

---

## 37. Mandatory release gates

少なくとも次を通過する必要があります。

```text
Core serialization／path
Configuration
Canon／State／Evidence
Initial／Planning／Scene data
Context
Runtime
50 Stage Pipeline
Scene Commit
Volume Handoff
Completion／Publication
Recovery failpoints
Security／Privacy
CLI
Wheel／package assets
Canonical fixtures
Prompt／Schema
Performance／no-wait
```

Requirement trace:

```text
REQ-*
→ design authority
→ ACC-*
→ automated test
→ fixture
→ result
```

---

## 38. Deterministic test doubles

Mandatory testsは次をinjectします。

```text
fake wall／monotonic clock
fake sleeper
scripted provider
deterministic tokenizer
fault-injecting filesystem
fake lock
fake capacity monitor
test Prompt bundle
```

Mandatory suiteはreal networkやreal waitingを必要としません。

---

## 39. Implementation order

```text
Phase 1:
  canonical serialization
  typed IDs／paths
  atomic storage
  Runtime／config roots
  package Prompt／Schema loader

Phase 2:
  50 Stage registry
  Engine loop
  Run State／Counters
  startup／safe stop

Phase 3:
  Context
  Provider adapter
  Call audit
  Candidate／Review／Revision

Phase 4:
  INPUT／INIT／Genesis／Planning

Phase 5:
  Scene／Checkpoint／Evidence／COMMIT／HEAD

Phase 6:
  Handoff／Completion／Publication／CURRENT

Phase 7:
  Recovery／Security／Packaging／Acceptance
```

Legacy `_run_one`へ新Stageを継ぎ足さないでください。

---

## 40. Contribution rules

Code changeには次を含めます。

```text
対応Requirement ID
対応Acceptance ID
production implementation
positive test
negative test
Crash test when durable boundary changes
fixture／hash update when bytes change
Implementation Status update
```

してはいけないこと:

```text
current implementationに合わせてRequirementを弱める
legacy test成功をversion-1 passと数える
newest fileをauthorityにする
expected pathをguessする
raw auditをCandidateへ昇格する
mechanical errorをsemantic residualへ変える
```

---

## 41. Documentation changes

契約変更時は依存順を守ります。

```text
field-level data／pipeline contract
→ integration design
→ examples／fixtures
→ Implementation acceptance
→ Requirements／Specification
→ Implementation Status
→ README
```

Canonical hashやpathが変わる場合、関連fixtureをすべて再生成します。

---

## 42. 問題を報告するとき

次を含めてください。

```text
package／commit version
Python version
OS／filesystem
command
redacted config
Run status
current Stage／target
HEAD／CURRENT value
safe error code
関連audit path
再現手順
```

含めないでください。

```text
credential
Authorization header
private full Context
private author truth
unredacted provider request
```

---

# Terminology

## 43. Candidate

まだ採用されていない、構造正常な生成・抽出・Revision成果物。

---

## 44. Review

Candidateの意味監査を保存する`audit` artifact。

Candidate自体を変更しません。

---

## 45. Checkpoint

一つのScene transaction内で凍結したScene Card、prose、candidate delta、Commit準備phase。

---

## 46. Generation

一つのCommitが作るimmutable Story snapshot。

---

## 47. HEAD

現在の採用済みGenerationを選ぶ`canon/HEAD` pointer。

---

## 48. Handoff

Volume終了Stateを次巻またはCompletionへ渡すprivate adopted artifact。

---

## 49. Completion audit

Required ThreadとEnding criterionの意味的完結性を評価するprivate audit。

---

## 50. Publication

Reader-facing manuscript、metadata、safe report、Validation、Manifestからなるimmutable directory。

---

## 51. Gate

Publicationを採用してよいかを判定するexternal audit。

Gateはadoptionを実行しません。

---

## 52. CURRENT

現在の採用済みPublicationを選ぶ`output/CURRENT` pointer。

---

## 53. Orphan

HEAD、CURRENT、Run-selected Candidate／Checkpoint、referenced transactionから到達できないartifact。

---

## 54. Durable boundary

Crash後に推測なしで次のactionを決められる完全保存点。

---

# Project claim policy

## 55. 現在言ってよいこと

```text
Storycraft 0.1.0にはlegacy run／resume／stepがある
legacy fake-model testsの合格実績がある
version-1製品・設計contractが整備されている
version-1実装を開始できるbaselineがある
```

---

## 56. 現在言ってはいけないこと

```text
50 Stage engine implemented
Canon／State／Evidence ledgers implemented
Generation／HEAD implemented
Candidate／Checkpoint recovery implemented
Completion／Publication Gate implemented
CURRENT adoption implemented
strict structured output implemented
privacy gate passed
version-1 acceptance passed
release candidate
production ready
```

---

## 57. 次のrepository artifact

Package versionのsingle source of truthと公開import surfaceを`1.0.0.dev0`へ合わせるため、次に更新すべきartifactは:

```text
src/storycraft/__init__.py
```

`pyproject.toml`はpackage-only prompt assetsを要求するversion-1 development metadataへ更新済みです。Target asset rootが実装されるまでwheel gateは意図的にpassしません。

---

## 58. 最終原則

Storycraft version-1は、任意の時点でdurable validated dataから次を説明できなければなりません。

```text
どのRunか
現在のStageとtarget
どのsource Generationを使ったか
どのCandidate／Checkpoint／transactionが選択されているか
どのID／usageが消費済みか
どのGenerationがHEADか
どのPublicationがCURRENTか
次に合法なStage
Crash後の一意なrecovery action
```

その答えが次へ依存する実装は受入できません。

```text
最新mtime
最大番号の未参照directory
一つの巨大なmutable state
normal log
raw provider success
unreferenced staging
```
