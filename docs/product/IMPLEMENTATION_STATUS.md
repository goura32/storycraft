# Storycraft 実装状況

> [製品仕様](SPECIFICATION.md)が次期正式リリースの正本。本書は、現行コードがその仕様をどこまで満たすかを記録する差分文書であり、製品仕様を現行実装へ合わせて後退させてはならない。

## 1. 結論

現行コードは、旧state version 5と13個のlegacy semantic stageで動作する**機能的prototype**である。

一方、[製品仕様](SPECIFICATION.md)、[Pipeline contracts](../design/pipeline_contracts.md)、[Ledger contracts](../design/ledger_contracts.md)、[Implementation acceptance](../design/implementation_acceptance.md)が定めるversion-1実装としては、**未受入・未完成**である。

現在許可される表現:

```text
legacy prototype:
  動作確認済み

version-1 design:
  契約確定済み

version-1 implementation:
  未実装または部分基盤のみ

release candidate:
  ではない

production ready:
  ではない
```

---

## 2. 評価基準日と対象

```text
assessment_date = 2026-07-22
source_archive = storycraft-main (11).zip
source_archive_sha256 = 3d5e1f6c8ead0b8728596e3500582d7568c408ccb5af91d284ea6880bee138fc

project_version = 0.1.0
pyproject_sha256 = bacf5c72a20099e97c109c4ab5ce83968619acc5eb1e6cd9151731d1075828d

source_python_files = 12
source_lines = 1876
source_inventory_sha256 = c44bf1550a148eaf8a3f8c9e6a425bc6f3688e7d35566dd134b7d34da1e42e03

test_files = 8
test_lines = 1605
test_inventory_sha256 = 4a3b89194a56b4b67b18fd40c02e9eb8b2a0d391be0c732deaa9e3d036dadcde
```

この評価は上記snapshotだけを対象とする。

---

## 3. Status用語

| status | 意味 |
|---|---|
| `VERIFIED_LEGACY` | 旧実装としてコードとテストで確認できる |
| `PARTIAL_FOUNDATION` | version-1で考え方または低位部品を再利用できるが、契約を満たさない |
| `SPEC_ONLY` | 文書契約はあるが、対応するproduction code／acceptance testがない |
| `BLOCKED_UNVERIFIED` | 実行環境または外部依存の不足により確認できない |
| `DEPRECATED` | version-1では廃止し、互換authorityとして残さない |
| `ACCEPTED_V1` |全required acceptance gateを満たす。現時点では該当なし |

---

## 4. 証拠レベル

実装状況は次の順で判定する。

```text
production code
＋
同じproduction validator／serializer／transactionを使うautomated test
＋
Implementation acceptance IDへのtraceability
＋
canonical command成功
```

次だけではversion-1実装済みとしない。

```text
設計文書に記載されている
legacy testが通る
似た名前のfieldがある
happy pathでファイルが出る
LLM fakeがobjectを返す
```

---

## 5. Executive status

| 領域 | 現状 |
|---|---|
| 製品・設計契約 | 完成した実装前ベースライン |
| legacy CLI | `VERIFIED_LEGACY` |
| legacy end-to-end fake flow | `VERIFIED_LEGACY` |
| version-1 50 Stage engine | `SPEC_ONLY` |
| version-1 Ledger／Generation／HEAD | `SPEC_ONLY` |
| Candidate／Checkpoint／Transaction | `SPEC_ONLY` |
| Volume Handoff Commit | `SPEC_ONLY` |
| Completion／Publication Gate／CURRENT | `SPEC_ONLY` |
| Crash／orphan recovery | `SPEC_ONLY` |
| version-1 Acceptance suite | `SPEC_ONLY` |
| wheel release gate | `BLOCKED_UNVERIFIED` |
| real provider integration | `BLOCKED_UNVERIFIED` |
| release readiness | **未受入** |

---

# Part I: 現行コードの確認結果

## 6. 現行module

```text
src/storycraft/
  __init__.py
  cli.py
  config.py
  llm.py
  log.py
  prompt_template.py
  series_contracts.py
  series_engine.py
  series_model.py
  series_output.py
  series_store.py
  series_workflow.py
```

中心構造:

```text
SeriesService
  inherits SeriesWorkflow

SeriesWorkflow
  inherits ContractValidator

StateStore
  persists one state.json

OpenAIStoryModel
  generate / critique / revision

OutputWriter
  writes final Markdown directly
```

---

## 7. Public API

現行で確認できる公開操作:

```text
SeriesService.run
SeriesService.resume
SeriesService.step
```

Status:

```text
VERIFIED_LEGACY
```

制約:

- version-1の`SeriesService`／`EngineResult`契約ではない;
- `step`はCanonical Stageを1件だけ実行するとは限らない;
- Scene処理時はScene Card、本文、continuity、State更新を一つのlegacy `_run_one`で行う。

---

## 8. CLI

現行CLI:

```text
storycraft run
storycraft resume
storycraft step
```

Source-tree CLI helpは、import-only OpenAI stub下で4コマンドすべてexit 0を確認した。

Status:

```text
VERIFIED_LEGACY
```

不足:

```text
version-1 exit-code registry
safe-stop result
Run ID／HEAD／CURRENTを含むEngineResult
package-installed wheel smoke
credentialなしpackage asset validation
```

---

## 9. Input mode

現行はBriefまたはKeywordsの排他的入力を検証する。

```text
run:
  --brief or --keywords required and exclusive

step new workspace:
  brief or keywords exactly one

resume:
  initial inputなし
```

Status:

```text
PARTIAL_FOUNDATION
```

差分:

- version-1のKeyword source artifactがない;
- adopted Briefのimmutable source/hash/profile metadataがない;
- INPUT-01〜03 Stage境界がない。

---

## 10. Workspace lock

現行`StateStore.lock()`はPOSIX `fcntl.flock`のexclusive nonblocking lockを使う。

Status:

```text
PARTIAL_FOUNDATION
```

確認できること:

```text
別processによる同一workspaceの同時mutationを拒否
```

不足:

```text
lock metadata
platform capability validation
Windows対応方針
security preflight
startup authority validationとの統合
```

---

## 11. Legacy state persistence

現行は次を一つのファイルへ保存する。

```text
state.json
version = 5
```

保存は:

```text
temporary sibling
flush
file fsync
replace
directory fsync
```

で行う。

Status:

```text
PARTIAL_FOUNDATION
```

低位のatomic complete-file patternは再利用候補である。

ただしversion-1のRuntime／Ledger authorityではない。

---

## 12. Legacy state root

主なfield:

```text
brief
keywords
volume_map
characters
relationships
world
timeline
threads
chapters
cards
scenes
volume_summaries
attempts
quality_acceptances
closure
completed
last_completed_unit
stopped_at
stop_reason
_active
```

Status:

```text
DEPRECATED
```

理由:

```text
story truth
execution state
candidate history
review history
completion
```

が一つのmutable objectへ混在している。

---

## 13. Legacy workflow dispatch

現行`SeriesWorkflow._run_one()`は、state内の未設定fieldを順に調べて次の処理を決める。

Status:

```text
DEPRECATED
```

現行semantic stage名:

```text
brief
characters
relationships
world
timeline
threads
volume_map
volume_chapters
scene_card
scene
continuity
volume_summary
closure
```

Canonical 50 Stage IDはproduction sourceに0件である。

---

## 14. Brief validation

現行は:

```text
title
genre
want
avoid
ending
protagonist
key_people
volumes 4..10
chapters_per_volume
```

を検証する。

Status:

```text
PARTIAL_FOUNDATION
```

製品の4〜10巻要件は存在するが、version-1 Brief Schema／source metadata／unknown-field contractとは異なる。

---

## 15. Legacy initial ledgers

現行は別々に生成する。

```text
characters
relationships
world
timeline
threads
```

各候補を簡易validatorで検証後、コードがIDを追加する。

Status:

```text
PARTIAL_FOUNDATION
```

存在する概念:

```text
固定情報
initial_state
current_state
major/supporting Thread
author_truth
reader/character knowledge-like fields
```

version-1 Canon／Knowledge／Story State rootとは互換でない。

---

## 16. Legacy ID allocation

現行は各arrayへ:

```text
char-0001
rel-0001
entity-0001
time-0001
thread-0001
```

のように、stage完了後のenumerationでIDを付与する。

Status:

```text
DEPRECATED
```

不足:

```text
global persistent counters
persist-before-use
local_key
cross-stage deterministic allocation map
Evidence／Commit／Generation／Publication／Call ID
gap preservation
recovery reconciliation
```

---

## 17. Legacy planning

現行は:

```text
volume_map
volume_chapters
```

を生成する。

確認できる規則:

```text
4..10巻
Major Threadのintroduce→resolve巻配分
非最終巻reader question
章番号の連続性
1..4 Scene per Chapter
```

Status:

```text
PARTIAL_FOUNDATION
```

不足:

```text
Series／Volume／Chapterの独立adopted artifact
source HEAD
prior Handoff
plan hash chain
immutable plan transaction
canonical SERIES/VOL/CH Stage
```

---

## 18. Legacy Scene ID

現行Scene ID:

```text
vNN-cNN-sNN
```

Status:

```text
DEPRECATED
```

version-1 canonical format:

```text
vNN-cNNN-sNNN
```

既存IDをversion-1 workspaceへ自動migrationしない。

---

## 19. Legacy Scene Card

現行Scene Cardは次を持つ。

```text
scene_id
pov_character_id
location_id
start_time_id
end_time_id
character_ids
purpose
required_events
thread_actions
reader_disclosure
withheld_information
presentation_rules
end_change
visible_ids
allowed_update_ids
```

Status:

```text
PARTIAL_FOUNDATION
```

存在する有用概念:

```text
POV
visible set
allowed update set
Thread action
reader disclosure
withheld information
time monotonicity
```

不足:

```text
content-only candidateとfrozen cardの分離
source Generation／plan hash
code-owned before values
allowed_update_targets union
new_item_policy
Knowledge／Ending targets
Checkpoint manifest
```

---

## 20. Legacy Writer context

現行はScene Cardの`visible_ids`からWriter contextを構成する。

Status:

```text
PARTIAL_FOUNDATION
```

既存テストは一部の非可視record除外を確認する。

ただしversion-1で必要なbyte-level secret sentinel試験、Writer-safe exact view Schema、non-POV private State filteringは存在しない。

---

## 21. Legacy prose

現行model responseは:

```json
{"content":"..."}
```

を要求し、空でない本文を検証する。

Status:

```text
DEPRECATED
```

version-1はraw prose text responseであり、JSON wrapperを禁止する。

現行はheading／list／table／code fenceなどのprose format contractも完全には検証しない。

---

## 22. Legacy continuity

現行continuityは:

```text
handoff_summary
state_updates[]
```

を返す。

各updateは:

```text
source_scene_id
id
field
value
evidence
```

を持つ。

Status:

```text
PARTIAL_FOUNDATION
```

存在する有用概念:

```text
Scene Cardのallowed_update_ids
本文substring evidence
Character／Major Threadのfield制限
最終SceneでMajor Thread resolve要求
```

不足:

```text
candidate／committed delta分離
before値
typed union
Knowledge update
new item proposal
Ending Evidence proposal
literal quote一意性
Unicode code-point offset
quote/prose hash
Evidence ID／index
bidirectional root diff
```

---

## 23. Legacy State mutation

continuityの`state_updates`を、同じ`state.json`内のrecord `current_state`へ直接適用する。

Status:

```text
DEPRECATED
```

Scene Card、prose、delta、State、Scene appendを一つのGeneration transactionとして保存しない。

`canon/HEAD`も存在しない。

---

## 24. Legacy Review／Revision

現行は全legacy stageで:

```text
generate
critique
revision
```

を実行できる。

`quality.max_critique_passes`に従ってloopし、上限後はknown issueを`quality_acceptances`へ記録して採用する場合がある。

Status:

```text
PARTIAL_FOUNDATION
```

有用概念:

```text
semantic issueとcandidate revision
full root objectを求める一部prompt
known issue persistence
```

不足:

```text
generic Review Schema
versioned candidate directory
version-local Review
Candidate manifest
logical owner
residual issue JSONL
mechanical／semantic分類の完全分離
max_revision_rounds契約
```

`critique`用語とAPIはversion-1で廃止する。

---

## 25. Legacy attempt history

現行`state["attempts"]`へ、draft／critique／revisionのinput、response、validationを記録する。

Status:

```text
PARTIAL_FOUNDATION
```

これはcandidate/audit authorityではない。

不足:

```text
Call ID
immutable unique filename
Context hash
prompt／Schema version
usage
provider timing
redaction contract
candidate linkage
```

---

## 26. Legacy Volume summary

各巻後に`volume_summary`と`unresolved_thread_ids`を生成する。

Status:

```text
DEPRECATED
```

version-1 Volume Handoffの代用ではない。

現行summaryは独立Commit／Generationを作らず、`volume_disposition`だけを更新するtransactionもない。

---

## 27. Legacy closure

全巻後に`closure`を生成し:

```text
resolved_ids
ending_evidence
ending_authority
```

を検証する。

Status:

```text
DEPRECATED
```

version-1 Completion auditの代用ではない。

不足:

```text
COMP-PRE
Completion Context
attempt-NN
complete／complete_with_residual_issues／incomplete
first structurally valid attempt
private accepted audit
valid incomplete nonretry
```

---

## 28. Legacy output

現行`OutputWriter`は:

```text
output/
  volume-01.md
  volume-02.md
  ...
  series.md
  quality-acceptances.json
```

を作る。

一時directoryへ書き、既存outputをbackupしてrenameする。

Status:

```text
PARTIAL_FOUNDATION
```

有用概念:

```text
plan順のVolume／Chapter／Scene assembly
空本文・重複本文の簡易検証
staging directory
```

不足:

```text
Publication ID
manuscript/metadata/reports layout
Publication Validation
payload/content/snapshot hash
final Manifest
external Gate
output/CURRENT
OUT-01〜03
post-rename recovery
directory fsync
```

---

## 29. Legacy LLM adapter

現行`LLMClient`はOpenAI-compatible endpointへstreaming callを行う。

Status:

```text
PARTIAL_FOUNDATION
```

存在:

```text
provider base URL／model
streaming content収集
thinking metadata
attempt seed
transport error capture
raw log保存
```

重大な差分:

```text
api_key = "ollama" hardcoded
timeout=None
strict json_schema未使用
usage accountingなし
Call ID counterなし
request cancellationなし
provider adapter protocolなし
```

---

## 30. Timeout実装

設定には:

```text
first_event_timeout_seconds
idle_timeout_seconds
```

がある。

しかし現行同期stream反復は`next(chunk)`でblockし、watchdog threadはlogだけを行う。

`idle_timeout`判定も次のchunk受信後に実行される。

Status:

```text
SPEC_ONLY for reliable timeout
```

現行は次を保証しない。

```text
first-event timeoutで実際にcallを中断
idle timeout中のblockを中断
total call timeout
connect timeout
safe cancellation
```

---

## 31. Legacy prompt loader

現行は:

```text
one common system prompt
category/stage inference
critique special case
Jinja generic kwargs
source-tree fallback
singleton loader
```

を使う。

Status:

```text
DEPRECATED
```

---

## 32. Legacy prompt assets

現行inventory:

```text
Jinja templates = 40
JSON Schema files = 14
legacy semantic stages = 13
```

Schemaはprompt textへ整形して埋め込み、providerには:

```text
{"type":"json_object"}
```

を渡す。

Status:

```text
DEPRECATED
```

version-1 strict `json_schema`、30 LLM Stage registry、package-only asset bundleではない。

---

## 33. Raw LLM logs

現行は各callの送信message、受信content、timing metadataを:

```text
raw/*.json
raw/*.md
```

へ保存する。

Status:

```text
PARTIAL_FOUNDATION
```

不足:

```text
persistent Call ID
append-safe unique filename
credential／body redaction policy
audit compression
retention/capacity
prompt／Schema／Context/config identity
raw audit nonpromotion recovery
```

---

## 34. Configuration

現行`Settings`はYAML、default、いくつかの環境変数overrideを扱う。

Status:

```text
PARTIAL_FOUNDATION
```

現行主なsection:

```text
llm
retry
quality
output
diversity
```

version-1のcomplete Effective config、immutable fingerprint、operation map、budget、pricing、publishing profile、audit policy、resume mutabilityはない。

---

## 35. Signal handling

現行CLIはSIGTERMで`SystemExit`を即時raiseし、終了logをflushする。

Status:

```text
PARTIAL_FOUNDATION
```

version-1 safe-stopではない。

atomic transactionまたはprovider call中にsignalを受けた場合、登録されたdurable boundaryまで待つStopControllerがない。

---

# Part II: 現行テスト証拠

## 36. Syntax gate

実行結果:

```text
PYTHONPATH=<import-only-openai-stub>:src
python -m compileall -q src tests

result = PASS
```

Status:

```text
VERIFIED_LEGACY
```

---

## 37. Canonical unittest command

実行結果:

```text
PYTHONPATH=<import-only-openai-stub>:src
python -m unittest discover -s tests -p "test_*.py"

Ran 83 tests
16 subtests
OK
```

Status:

```text
VERIFIED_LEGACY
```

注意:

- `openai` packageが評価環境に無かったため、importだけを成立させるtemporary stubを使用した;
- testsはreal provider clientを生成しない;
- この成功はlegacy test contractの証拠である;
- version-1 acceptance IDの証拠ではない。

---

## 38. Dependency-independent subset

OpenAI依存moduleをimportしない6 test file:

```text
52 passed
3 subtests passed
```

Status:

```text
VERIFIED_LEGACY
```

---

## 39. Direct pytest result

通常の:

```text
python -m pytest -q
```

はpackage未installのため:

```text
ModuleNotFoundError: storycraft
```

でcollection失敗した。

`PYTHONPATH=src`では:

```text
ModuleNotFoundError: openai
```

で2 test moduleがcollection失敗した。

これはcode defectと断定しないが、評価環境でcanonical dependency installationが成立していないことを示す。

---

## 40. Acceptance traceability

現行tests内の:

```text
ACC-*
```

記載数:

```text
0
```

Status:

```text
SPEC_ONLY
```

現行83 testsをversion-1 acceptance IDへ自動的に対応付けてはならない。

---

## 41. Source-tree CLI smoke

import-only OpenAI stub＋`PYTHONPATH=src`で:

```text
storycraft --help
storycraft run --help
storycraft resume --help
storycraft step --help
```

相当のmodule実行は全てexit 0だった。

Status:

```text
VERIFIED_LEGACY
```

これはwheel-installed CLI smokeではない。

---

## 42. Wheel smoke

Repositoryには:

```text
scripts/wheel_smoke.sh
```

がある。

しかし評価環境では:

```text
hatchling = missing
build = missing
openai = missing
```

であり、`pip wheel --no-build-isolation`は:

```text
BackendUnavailable: Cannot import hatchling.build
```

で失敗した。

Status:

```text
BLOCKED_UNVERIFIED
```

さらに現行scriptはlegacy `closure`／legacy prompt assetを確認するため、成功してもversion-1 packaging gateにはならない。

---

## 43. Real provider test

実provider endpoint、credential、stream timeout、strict Schema、usage取得を含むintegration testは実行していない。

Status:

```text
BLOCKED_UNVERIFIED
```

Mandatory version-1 suiteはreal networkを必要としないため、これはrelease acceptanceの代用ではない。

---

# Part III: Version-1との差分

## 44. Canonical Stage engine

Required:

```text
50 exact Stage IDs
one StageRegistry
typed StageSpec
validated transition graph
one canonical Stage per step
```

Current:

```text
13 legacy semantic names
one large _run_one conditional
missing-field inference
```

Status:

```text
SPEC_ONLY
```

---

## 45. Engine architecture

Required:

```text
SeriesService
Engine
StageRegistry
Stage executors
Domain services
Repositories
Provider adapter
```

Current:

```text
SeriesService inherits SeriesWorkflow
SeriesWorkflow inherits ContractValidator
```

Status:

```text
SPEC_ONLY
```

---

## 46. Runtime roots

Required:

```text
runtime/run-manifest.json
runtime/run-state.json
runtime/counters.json
runtime/effective-config.json
```

Current:

```text
state.json version 5
```

Status:

```text
SPEC_ONLY
```

---

## 47. Canonical serialization

Required:

```text
NFC
deterministic key order
strict numeric handling
contract array order
compact canonical JSON
exact final LF
stable SHA-256
```

Current:

```text
json.dump(..., ensure_ascii=False, indent=2)
```

Status:

```text
SPEC_ONLY
```

Atomic replacement aloneはcanonical serializationの証拠ではない。

---

## 48. Managed path security

Required:

```text
relative POSIX path
fixed case
no traversal
no absolute path
symlink／junction escape prevention
fixed-width coordinates
```

Current production codeに専用path validatorはない。

Status:

```text
SPEC_ONLY
```

---

## 49. Canon／Knowledge roots

Required:

```text
current-canon.json
knowledge-items.json
```

Current:

```text
characters
relationships
world
timeline
threads
```

をstate.json内へ保存する。

Status:

```text
SPEC_ONLY
```

---

## 50. Story State root

Required:

```text
character_states
relationship_states
thread_states
knowledge_states
story_clock
```

Current:

```text
各legacy record内のcurrent_state
```

Status:

```text
SPEC_ONLY
```

---

## 51. Evidence ledger

Required:

```text
evidence-index.json
Evidence ID
quote uniqueness
code-point offsets
quote／prose hash
Commit link
```

Current:

```text
state_update.evidence substring
```

Status:

```text
SPEC_ONLY
```

---

## 52. Genesis

Required:

```text
INIT-01〜06／REV／ID
integrated bundle
local_key
deterministic ID mapping
Generation 00000000
Commit 00000000
HEAD-last
```

Currentは5個のlegacy ledgerを順次生成・即採番する。

Status:

```text
SPEC_ONLY
```

---

## 53. Immutable planning artifacts

Required:

```text
plans/series-map.json
plans/volumes/vNN/volume-design.json
plans/volumes/vNN/chapters/cNNN/chapter-design.json
```

Currentは`state.json`内の`volume_map`／`chapters`だけである。

Status:

```text
SPEC_ONLY
```

---

## 54. Candidate versions

Required:

```text
runtime/candidates/.../vNNNN/
candidate artifact
review.json
candidate-manifest.json
```

Currentはstate内`attempts`と現在candidateのin-memory variableである。

Status:

```text
SPEC_ONLY
```

---

## 55. Scene Checkpoint

Required phases:

```text
CARD_ACCEPTED
PROSE_FROZEN
DELTA_ACCEPTED
COMMIT_PREPARED
```

CurrentにCheckpoint manifestはない。

Status:

```text
SPEC_ONLY
```

---

## 56. Scene Commit

Required:

```text
COMMIT-01
COMMIT-02
COMMIT-03
COMMIT-04
copy-on-write roots
Evidence
Scene／Commit／Generation manifest
HEAD-last
```

Currentはcontinuity後にstate.jsonへ直接mutationする。

Status:

```text
SPEC_ONLY
```

---

## 57. `canon/HEAD`

Current sourceの:

```text
canon/HEAD
generation-manifest
commit-manifest
candidate-manifest
checkpoint-manifest
```

実装参照数:

```text
0
```

Status:

```text
SPEC_ONLY
```

---

## 58. Volume Handoff Commit

Required:

```text
VH-01／02／REV／ID
artifacts/handoffs/vNN.json
commit_type = volume_handoff
volume_disposition-only change
Story clock unchanged
```

Currentには`volume_summary`だけがある。

Status:

```text
SPEC_ONLY
```

---

## 59. Completion

Required:

```text
COMP-PRE
COMP-AUDIT
COMP-SAVE
first structurally valid attempt
complete／complete_with_residual_issues／incomplete
```

Currentにはlegacy `closure`だけがある。

Status:

```text
SPEC_ONLY
```

---

## 60. Publication

Required:

```text
OUT-01
OUT-02
COMP-PUBLISH
OUT-03
Publication ID
Validation
Manifest
Gate
CURRENT-last
```

Currentは`output/`を直接置換する。

Status:

```text
SPEC_ONLY
```

---

## 61. Recovery

Required:

```text
reconcile
resume
regenerate
quarantine
explicit recovery
manual intervention
```

Current`resume`はstate.jsonをloadし、missing fieldから続行する。

Status:

```text
SPEC_ONLY
```

Candidate／Checkpoint／transaction／HEAD／CURRENTのcrash matrixはない。

---

## 62. Counters and usage

Required:

```text
Call ID
Commit／Generation ID
Evidence ID
Publication ID
story-record IDs
usage
retry／revision
cost
active elapsed
```

Current:

```text
in-memory seed sequence
state attempts
quality_acceptances
```

Status:

```text
SPEC_ONLY
```

---

## 63. Safe stop

Required:

```text
stop request flag
registered durable boundary
no asynchronous mutation interruption
resume-compatible stopped state
```

Current:

```text
SIGTERM → immediate SystemExit
```

Status:

```text
SPEC_ONLY
```

---

## 64. Prompt bundle

Required:

```text
package-only asset root
prompt-bundle.json
schema-bundle.json
registry.json
30 exact LLM Stage specs
14 exact current response Schemas
strict Stage/version compatibility
```

Current:

```text
legacy source-tree templates
source-tree fallback
category/stage inference
```

Status:

```text
SPEC_ONLY
```

---

## 65. Context snapshots

Required:

```text
hash-named immutable Context
source refs
view type／sensitivity
token budget
Writer／Continuity secret exclusion
```

CurrentはPython dictを直接templateへ渡す。

Status:

```text
SPEC_ONLY
```

---

## 66. Security acceptance

Required:

```text
credential absent everywhere
prompt injection boundary
Writer／Continuity private sentinel exclusion
managed path security
audit redaction
no external retrieval
```

Currentには一部のvisible context、safe error type、hardcoded Ollama keyがあるが、version-1 security gateはない。

Status:

```text
SPEC_ONLY
```

---

## 67. Performance acceptance

Required:

```text
fake clock
no real wait
deterministic tokenizer
Context scaling
startup scaling
large manuscript assembly
```

Current mandatory testsに完全なfake clock／tokenizer／capacity／fault-injecting filesystemはない。

Status:

```text
SPEC_ONLY
```

---

# Part IV: Acceptance group status

## 68. Core and path

| acceptance area | status | current evidence |
|---|---|---|
| `ACC-CORE-*` | `SPEC_ONLY` | atomic pretty-JSON saveのみ |
| `ACC-PATH-*` | `SPEC_ONLY` | managed path validatorなし |

---

## 69. Configuration

| acceptance area | status | current evidence |
|---|---|---|
| `ACC-CFG-*` | `PARTIAL_FOUNDATION` | YAML/default/env override、legacy retry/quality/timeouts |
| complete Effective config | `SPEC_ONLY` | なし |
| immutable fingerprint | `SPEC_ONLY` | なし |
| budgets/pricing/publishing/audit limits | `SPEC_ONLY` | なし |

---

## 70. Ledger data

| acceptance area | status |
|---|---|
| `ACC-CANON-*` | `SPEC_ONLY` |
| `ACC-STATE-*` | `SPEC_ONLY` |
| `ACC-EVID-*` | `SPEC_ONLY` |
| `ACC-INIT-DATA-*` | `SPEC_ONLY` |
| `ACC-PLAN-DATA-*` | `SPEC_ONLY` |
| `ACC-SCENE-DATA-*` | `PARTIAL_FOUNDATION` only for legacy analogous concepts |
| `ACC-REV-*` | `PARTIAL_FOUNDATION` only for legacy critique/revision |

---

## 71. Context and Runtime

| acceptance area | status |
|---|---|
| `ACC-CTX-*` | `SPEC_ONLY` |
| `ACC-RUN-*` | `SPEC_ONLY` |

---

## 72. Pipeline

| acceptance area | status |
|---|---|
| `ACC-PIPE-INIT-*` | `SPEC_ONLY` |
| `ACC-PIPE-PLAN-*` | `SPEC_ONLY` |
| `ACC-PIPE-SCENE-*` | `SPEC_ONLY` |
| `ACC-COMMIT-*` | `SPEC_ONLY` |
| `ACC-VH-*` | `SPEC_ONLY` |
| `ACC-OUT-*` | `SPEC_ONLY` |

Legacy flow tests are not these acceptance groups.

---

## 73. Recovery and security

| acceptance area | status |
|---|---|
| `ACC-REC-*` | `SPEC_ONLY` |
| `ACC-SEC-*` | `SPEC_ONLY` |

---

## 74. CLI, package, prompt, performance

| acceptance area | status |
|---|---|
| `ACC-CLI-*` | `PARTIAL_FOUNDATION` for source-tree legacy help/API |
| `ACC-PKG-*` | `BLOCKED_UNVERIFIED` and legacy script |
| `ACC-PROMPT-*` | `SPEC_ONLY` |
| `ACC-PERF-*` | `SPEC_ONLY` |
| `ACC-FIX-*` | `SPEC_ONLY` in production tests |

---

## 75. Accepted version-1 IDs

```text
accepted_version_1_acceptance_ids = 0
```

この値は、current testsが0件という意味ではない。

```text
legacy automated tests:
  83 tests + 16 subtests pass under stated stub condition

version-1 acceptance proof:
  0 IDs
```

---

# Part V: 再利用判断

## 76. 再利用可能な低位pattern

次は設計を合わせて書き直す前提で再利用候補である。

```text
fcntl exclusive nonblocking lockの基本
temporary sibling＋file fsync＋replace＋directory fsync
argparseのrun／resume／step表面
fake StoryModelによるnetworkなしflow testの考え方
plan順Markdown assemblyの考え方
substring Evidenceを拒否する既存negative testの意図
raw request／responseを保存する監査の意図
```

Status:

```text
PARTIAL_FOUNDATION
```

---

## 77. そのまま再利用してはいけないmodule

```text
series_workflow.py
series_store.py
series_contracts.py
series_model.py
prompt_template.py
series_output.py
llm.py
```

理由:

- authority、Stage、Schema、storage、retry、audit契約がversion-1と異なる;
- 小修正で互換化すると旧state semanticsが新実装へ混入する;
- acceptance failureの原因を追跡しにくくなる。

---

## 78. 薄く保てるmodule

```text
cli.py
series_engine.py
config.py
log.py
```

も全面的なcontract updateが必要だが、公開command名や責務の一部は保持できる。

最終的には[Series engine design](../design/series_engine_design.md)のpackage構造へ移行する。

---

## 79. Legacy compatibility方針

version-1は次を提供しない。

```text
state.json version 5 migration
legacy Stage alias
legacy ID自動変換
legacy raw logからCandidate復元
legacy outputをCURRENTへ自動採用
```

旧workspaceはread-only historical artifactとして保持し、新しいworkspaceでrunを開始する。

---

# Part VI: 実装順序

## 80. Phase 1 — Foundation

Required:

```text
typed IDs／paths
canonical JSON／text
hash utilities
atomic storage
lock capability validation
exact config/runtime Schemas
package prompt/schema loader
```

Current status:

```text
NOT STARTED as version-1
```

---

## 81. Phase 2 — Runtime and Registry

Required:

```text
50 Stage registry
Run manifest／Run state／counters／Effective config
Engine loop
Stage result validation
operation audit
safe stop
startup authority validation
```

Current status:

```text
NOT STARTED
```

---

## 82. Phase 3 — LLM Candidate framework

Required:

```text
Context snapshots
Prompt renderer
Provider adapter
retry coordinator
Call ID
LLM audit
versioned Candidate
generic Review／Revision
residual issues
```

Current status:

```text
NOT STARTED
```

---

## 83. Phase 4 — Genesis and Planning

Required:

```text
INPUT
INIT
Genesis
Series／Volume／Chapter planning
immutable plan adoption
```

Current status:

```text
NOT STARTED
```

Legacy analogous logic exists but is not a compatible base state.

---

## 84. Phase 5 — Scene and Commit

Required:

```text
Scene Card
Writer-safe prose
continuity
Checkpoint
Evidence
merge
COMMIT-01〜04
HEAD
```

Current status:

```text
NOT STARTED
```

---

## 85. Phase 6 — Handoff, Completion, Publication

Required:

```text
VH
Completion
Publication
Gate
CURRENT
```

Current status:

```text
NOT STARTED
```

---

## 86. Phase 7 — Recovery and Release

Required:

```text
all crash classifiers
quarantine
idempotent startup
counter/usage reconciliation
wheel smoke
CLI gate
acceptance trace report
security/privacy/performance gates
```

Current status:

```text
NOT STARTED
```

---

# Part VII: 実装claim policy

## 87. 言ってよいこと

```text
現行legacy prototypeにはrun／resume／stepがある
旧fake flow testsは通る
state.jsonはcomplete-file atomic replacementを使う
legacy continuityは本文substring evidenceを要求する
legacy outputはstaging directoryから置換する
version-1仕様文書は実装前baselineとして整備済み
```

---

## 88. 言ってはいけないこと

現時点で次を主張してはならない。

```text
50 Stage engine implemented
Canon／Story State／Evidence ledger implemented
HEAD／Generation implemented
Candidate manifest／Checkpoint implemented
Volume Handoff implemented
Completion audit implemented
Publication Gate／CURRENT implemented
crash-safe resume implemented
strict structured output implemented
privacy gate passed
wheel gate passed
version-1 acceptance passed
production ready
```

---

## 89. Status更新条件

本書のstatusを上げるには、同じcommitで次が必要である。

```text
production implementation
corresponding acceptance test
acceptance ID traceability
canonical command pass
negative and crash tests where applicable
```

設計文書の追加だけではstatusを上げない。

---

## 90. Partial status更新

一つのacceptance area内で一部だけ実装した場合:

```text
実装したexact IDs
未実装IDs
実行command
fixture
known blockers
```

を記録する。

area全体を`implemented`とまとめない。

---

## 91. Release-candidate条件

Release candidateと呼べるのは少なくとも次が全成功した場合だけである。

```text
compile/import gate
full deterministic automated suite
wheel smoke
installed CLI smoke
all required ACC IDs
full success fixture
valid incomplete fixture
crash/failpoint matrix
privacy/security gate
no-network mandatory suite
reproducible Publication gate
```

---

# Part VIII: 次の作業

## 92. 最初のcode change

最初に実装すべきproduction change:

```text
canonical serialization
typed managed paths
atomic storage primitives
exact Runtime/config roots
50 Stage registry skeleton
```

legacy `_run_one`へ新Stageを継ぎ足してはならない。

---

## 93. 最初のtest change

最初に追加すべきtest infrastructure:

```text
acceptance ID helper/report
fake clock
scripted provider
deterministic tokenizer
fault-injecting filesystem
fake credential source
network prohibition
```

既存legacy testsは、version-1 testsが立つまで回帰用として残してよい。

---

## 94. First milestone exit

Phase 1／2の最初のexit criteria:

```text
new workspace initialization
Run manifest／Run state／counters／Effective config
50 Stage registry validation
run／resume／stepが同じstartup pathを使う
LLM callなしでINPUT-01または初期positionまで進む
crash-safe complete-file replacement
corresponding ACC-CORE／PATH／CFG／RUN／CLI IDs
```

---

## 95. Documentation next step

製品文書の次の整合対象:

```text
docs/product/REQUIREMENTS.md
README.md
```

これらは、新しい製品仕様と本Statusの用語・claim policyへ合わせる必要がある。

---

# Part IX: Mechanical status checks

## 96. Current snapshot assertions

```text
source Python files = 12
legacy source lines = 1876
test files = 8
legacy test lines = 1605
legacy semantic stages = 13
legacy Jinja templates = 40
legacy JSON Schema files = 14
canonical Stage IDs in production source = 0
ACC ID mentions in tests = 0
HEAD／CURRENT／manifest implementation references = 0
local_key implementation references = 0
strict json_schema implementation references = 0
```

---

## 97. Test assertions

```text
compileall:
  pass

legacy unittest with import-only OpenAI stub:
  83 tests
  16 subtests
  pass

dependency-independent subset:
  52 tests
  3 subtests
  pass

source-tree CLI help with stub:
  pass

wheel smoke:
  not completed
  build backend unavailable in assessment environment

real provider integration:
  not executed
```

---

## 98. Status consistency

本書は次を満たさなければならない。

```text
製品仕様をlegacy実装へ合わせて弱めない
legacy test successをversion-1 acceptanceへ数えない
環境不足とcode failureを区別する
実装済みと設計済みを区別する
reuse candidateとcompatible implementationを区別する
unknown／unverifiedを推測でpassにしない
```

---

## 99. Final status

```text
documentation_baseline:
  ready for implementation

legacy_prototype:
  functioning under local deterministic tests

version_1_code:
  not accepted

version_1_acceptance_ids_passed:
  0

release_status:
  NOT A RELEASE CANDIDATE
```

version-1の実装は、legacy prototypeの延長ではなく、確定したRuntime／Pipeline／Ledger／Prompt／Publication契約に沿う新しいengineとして開始する。
