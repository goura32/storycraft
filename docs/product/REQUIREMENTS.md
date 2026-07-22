# Storycraft 要件

> version-1製品の検証可能な要件正本。利用者向けの意味と振る舞いは[製品仕様](SPECIFICATION.md)、現行コードの到達状況は[実装状況](IMPLEMENTATION_STATUS.md)、実行可能な試験シナリオは[Implementation acceptance](../design/implementation_acceptance.md)を正本とする。

Storycraftは、一度のBriefまたはKeywords入力から、日本語の長編シリーズを計画・執筆・継続性管理・完結監査し、検証済みPublicationをローカルに採用するCLI製品である。

この文書は、製品仕様をstable requirement IDへ分解し、設計authorityとAcceptance IDへ追跡可能にする。

---

## 1. 文書の役割

本書は次を定義する。

```text
何を満たす必要があるか
どのRequirement IDで追跡するか
どの設計文書が詳細を所有するか
どのAcceptance IDが検証するか
```

本書は次を定義しない。

```text
現行コードが実装済みか
Python class／moduleの具体名
JSON fieldの完全Schema
fsync／renameの詳細手順
LLM promptの全文
```

実装状況は`IMPLEMENTATION_STATUS.md`へ記録し、本要件を現行prototypeへ合わせて弱めてはならない。

---

## 2. Normative language

```text
しなければならない / MUST:
  version-1 release blocker

してはならない / MUST NOT:
  version-1 release blocker

してよい / MAY:
  optional behavior。実装した場合は同じ契約に従う
```

この文書のRequirement tableは、明示がない限りすべて`MUST`または`MUST NOT`である。

---

## 3. Requirement ID

形式:

```text
REQ-<AREA>-<NNN>
```

Area:

| Area | 意味 |
|---|---|
| `FR` | Functional requirement |
| `PUB` | Publication and adoption |
| `OPS` | Runtime and operational behavior |
| `REC` | Recovery and stop behavior |
| `SEC` | Security and privacy |
| `NFR` | Non-functional and release quality |

IDは意味変更時も再利用しない。

廃止する要件はIDを削除せず、change logで`retired`にする。version-1 initial baselineにはretired IDはない。

---

## 4. Acceptance参照

`Verification`欄の`ACC-*`は`implementation_acceptance.md`のstable scenario IDである。

範囲表記:

```text
ACC-COMMIT-001..014
```

はinclusive rangeを表す。

複数Requirementが同じAcceptance scenarioを共有してよいが、release trace reportでは各Requirementから少なくとも一つのpassing Acceptance IDへ到達できなければならない。

---

## 5. Authority precedence

解釈が衝突する場合:

```text
field-level data／pipeline contract
→ integration design contract
→ Implementation acceptance
→ Product specification
→ Requirements summary
→ README／status prose
```

よりspecificなcontractを優先し、矛盾をrelease前に修正する。

---

## 6. 主要authority

- [製品仕様](SPECIFICATION.md)
- [実装状況](IMPLEMENTATION_STATUS.md)
- [Implementation acceptance](../design/implementation_acceptance.md)
- [Pipeline contracts](../design/pipeline_contracts.md)
- [Ledger contracts](../design/ledger_contracts.md)
- [Configuration contracts](../design/configuration_contracts.md)
- [Context contracts](../design/context_contracts.md)
- [Workspace layout](../design/workspace_layout.md)
- [Runtime and recovery](../design/runtime_and_recovery.md)
- [Prompt template design](../design/prompt_template_design.md)
- [Series engine design](../design/series_engine_design.md)

---

## 7. Scope

version-1 scope:

```text
4〜10巻
日本語fiction
BriefまたはKeywords
ローカルCLI
OpenAI-compatible provider adapter
Series／Volume／Chapter／Scene planning
Scene prose
Continuity／Evidence／Commit
Volume Handoff
Completion audit
ローカルKDP向けMarkdown Publication
workspace、audit、resume、recovery
```

---

## 8. Out of scope

```text
KDP／外部storeへの自動upload
Web UI
RAG／Web search
人間承認UI
複数writerによる同一workspace同時mutation
remote database／object store authority
legacy workspace自動migration
既存作品途中からの自動import
複数model自動投票
売上／文学的成功の保証
```

---

## 9. Release priority

このbaselineに列挙する136件のRequirementはすべてversion-1 releaseの`P0`である。

部分実装またはlegacy類似機能はRequirement passと数えない。

---
# Part 1: 機能要件

## 10. 機能要件

利用者に見える生成・計画・Ledger・Completionの必須動作。

| Requirement ID | P | Normative requirement | Verification | Primary authority |
|---|---:|---|---|---|
| `REQ-FR-001` | P0 | Storycraftは、一度のBriefまたはKeywords入力から、計画、本文、継続性更新、巻Handoff、完結監査、検証済みPublicationまでを一つのローカルworkspaceで実行しなければならない。 | `ACC-FIX-001..007` | `SPECIFICATION.md`; `pipeline_contracts.md` |
| `REQ-FR-002` | P0 | 生成対象は4〜10巻の日本語シリーズでなければならず、巻数は採用BriefとSeries mapで一致しなければならない。 | `ACC-INIT-DATA-002`; `ACC-PLAN-DATA-001`; `ACC-FIX-001..007` | `SPECIFICATION.md`; `brief_and_initial.md`; `planning_artifacts.md` |
| `REQ-FR-003` | P0 | 正常な自動実行では、開始後に巻・章・Sceneごとの利用者判断を要求せず、terminalまたは安全な停止条件まで進行しなければならない。 | `ACC-PIPE-INIT-001..007`; `ACC-PIPE-PLAN-001..007`; `ACC-PIPE-SCENE-001..012`; `ACC-REC-027..032` | `SPECIFICATION.md`; `pipeline_contracts.md` |
| `REQ-FR-004` | P0 | 公開CLIは`run`、`resume`、`step`を提供し、各commandは同じstartup／authority validation経路を使用しなければならない。 | `ACC-CLI-001..005`; `ACC-REC-004` | `SPECIFICATION.md`; `series_engine_design.md` |
| `REQ-FR-005` | P0 | 新規runはBrief modeまたはKeywords modeの正確に一方だけを受け付け、両方指定または両方未指定を拒否しなければならない。 | `ACC-CLI-002`; `ACC-PIPE-INIT-001..002` | `SPECIFICATION.md`; `input_and_initial.md` |
| `REQ-FR-006` | P0 | Briefはtitle、genre、target reader、protagonist、key people、want、avoid、ending direction、4〜10のvolume countを完全に表現しなければならない。 | `ACC-INIT-DATA-002`; `ACC-INIT-DATA-004`; `ACC-INIT-DATA-006` | `brief_and_initial.md` |
| `REQ-FR-007` | P0 | Keywords modeはKeyword、notes、title／genre／ending／volumes hint、avoidを正規化し、source identityを持つimmutable Keyword sourceとadopted Briefを作らなければならない。 | `ACC-INIT-DATA-001..002`; `ACC-PIPE-INIT-002` | `brief_and_initial.md`; `input_and_initial.md` |
| `REQ-FR-008` | P0 | `run`は既に初期化済みのworkspaceを上書きまたは再利用してはならず、明確なusage／workspace errorとして終了しなければならない。 | `ACC-CLI-002..003`; `ACC-REC-001..004` | `series_engine_design.md`; `runtime_and_recovery.md` |
| `REQ-FR-009` | P0 | `resume`は初回inputの再指定を要求せず、既存workspaceのdurable authorityを検証して正確な次Stageから続行しなければならない。 | `ACC-CLI-004`; `ACC-REC-004..026` | `SPECIFICATION.md`; `runtime_and_recovery.md` |
| `REQ-FR-010` | P0 | `step`は最大一つのCanonical Stage boundaryを完了して返り、次Stageを先行実行してはならない。 | `ACC-CLI-005`; `ACC-RUN-004`; `ACC-FIX-011` | `pipeline_contracts.md`; `series_engine_design.md` |
| `REQ-FR-011` | P0 | 実行順序は50件の一意なCanonical Stage registryから決定し、未登録Stage、alias、欠落field、directoryの新しさから推測してはならない。 | `ACC-PROMPT-001`; `ACC-PIPE-INIT-001..007`; `ACC-PIPE-PLAN-001..007`; `ACC-PIPE-SCENE-001..012`; `ACC-COMMIT-001..014`; `ACC-VH-001..008`; `ACC-OUT-001..016` | `pipeline_contracts.md`; `series_engine_design.md` |
| `REQ-FR-012` | P0 | Initial designはConcept、People、World／Temporal、Arcs／Threads／Ending／Knowledge、integrated bundleの異なる完全rootを生成・Reviewしなければならない。 | `ACC-INIT-DATA-003..008`; `ACC-PIPE-INIT-003..005` | `brief_and_initial.md`; `input_and_initial.md` |
| `REQ-FR-013` | P0 | INIT-IDは完全なintegrated bundleをdry validationした後にpersistent IDを決定的に割り当て、Genesis Commit／Generation `00000000`と`canon/initial-design.json`を作り、`canon/HEAD`を最後に更新しなければならない。 | `ACC-INIT-DATA-009`; `ACC-PIPE-INIT-006..007`; `ACC-RUN-012`; `ACC-REC-019` | `input_and_initial.md`; `commit_and_output.md`; `runtime_records.md` |
| `REQ-FR-014` | P0 | Series mapは全巻の役割、主人公／Relationship target chain、Required Major Thread chain、Ending coverage、巻内解決、非最終reader question、最終解決を完全に定義しなければならない。 | `ACC-PLAN-DATA-001`; `ACC-PIPE-PLAN-001`; `ACC-FIX-001..007` | `planning_artifacts.md`; `planning.md` |
| `REQ-FR-015` | P0 | 各Volume designは対象巻開始時の実際のHEADと、2巻目以降は前巻のadopted Handoffをsourceとして作らなければならない。 | `ACC-PLAN-DATA-002`; `ACC-PIPE-PLAN-002`; `ACC-VH-008` | `planning_artifacts.md`; `planning.md` |
| `REQ-FR-016` | P0 | 各Chapter designは対象Chapter開始時のHEAD、親plans、必要な前Chapter safe handoffをsourceとして、連続したScene planを作らなければならない。 | `ACC-PLAN-DATA-003`; `ACC-PIPE-PLAN-003`; `ACC-PIPE-PLAN-007` | `planning_artifacts.md`; `planning.md` |
| `REQ-FR-017` | P0 | 採用済みSeries／Volume／Chapter planはimmutableであり、後続HEAD移動や本文差分に合わせて上書きしてはならない。 | `ACC-PLAN-DATA-004..005`; `ACC-PIPE-PLAN-005..006` | `planning_artifacts.md`; `planning.md` |
| `REQ-FR-018` | P0 | SC-01はcontent-only Scene-card candidateを返し、SC-CHKがScene identity、source／plan hashes、開始State、許可更新、禁止開示、length guidance、timestampをcode-owned fieldとして注入・凍結しなければならない。 | `ACC-SCENE-DATA-001`; `ACC-PIPE-SCENE-001..003` | `scene_artifacts.md`; `scene_generation.md` |
| `REQ-FR-019` | P0 | 本文生成へ渡すWriter Contextは必要なdramatic targetを保持しつつ、author truth、Ending private text、非POV private State、更新mechanicsを含んではならない。 | `ACC-CTX-006..009`; `ACC-SCENE-DATA-002..004`; `ACC-PIPE-SCENE-004`; `ACC-SEC-005` | `context_contracts.md`; `scene_generation.md` |
| `REQ-FR-020` | P0 | PROSE-01／PROSE-REVは自然な日本語のScene本文だけを返し、JSON、front matter、heading、list、table、code fence、HTML、link、metadata prefaceを返してはならない。 | `ACC-SCENE-DATA-005..006`; `ACC-PIPE-SCENE-005..006` | `scene_artifacts.md`; `prompt_template_design.md` |
| `REQ-FR-021` | P0 | DELTA-01は凍結本文から実際に成立した永続的変化だけを抽出し、provider responseにbefore値、persistent ID、Evidence ID、offset、hash、Commit／Generation ID、timestampを含めてはならない。 | `ACC-EVID-001`; `ACC-PIPE-SCENE-007`; `ACC-PROMPT-006` | `evidence_and_updates.md`; `scene_generation.md` |
| `REQ-FR-022` | P0 | Continuity candidateの全更新はfrozen Scene Cardの`allowed_update_targets`と`new_item_policy`に一致し、source HEADのbefore値およびtransition matrixに適合しなければならない。 | `ACC-EVID-006..008`; `ACC-SCENE-DATA-003`; `ACC-PIPE-SCENE-008..010` | `scene_artifacts.md`; `evidence_and_updates.md` |
| `REQ-FR-023` | P0 | LLMが提案する新規項目はcandidate-local keyを使用し、codeがCommit中にpersistent IDへ決定的に解決し、IDをpersist-before-useしなければならない。 | `ACC-EVID-002`; `ACC-INIT-DATA-005`; `ACC-INIT-DATA-009`; `ACC-COMMIT-003..005` | `canon_records.md`; `evidence_and_updates.md`; `runtime_records.md` |
| `REQ-FR-024` | P0 | 通常SceneはTemporal rule、Major Thread、Ending criterion、required Threadを新規作成してはならず、新規項目数、type、scopeはScene Card policyを超えてはならない。 | `ACC-CANON-005..006`; `ACC-EVID-008`; `ACC-PIPE-SCENE-008` | `canon_records.md`; `scene_artifacts.md` |
| `REQ-FR-025` | P0 | 通常Reviewはmechanically validなcandidateだけを対象とし、responseは`summary`と`issues`だけで、修正版、pass／fail、next Stage、adoption判断を含んではならない。 | `ACC-REV-001..005`; `ACC-PROMPT-004`; `ACC-PIPE-INIT-004..005` | `review_and_audit.md`; `prompt_template_design.md` |
| `REQ-FR-026` | P0 | Revisionは元generator／extractorと同じ完全response contractによる全体置換でなければならず、patch、diff、変更箇所だけを返してはならない。 | `ACC-INIT-DATA-008`; `ACC-PROMPT-005`; `ACC-PIPE-PLAN-004`; `ACC-PIPE-SCENE-005,009`; `ACC-VH-003` | `review_and_audit.md`; `prompt_template_design.md` |
| `REQ-FR-027` | P0 | Revision上限後に残るsemantic issueは、candidateがmechanically validである場合だけimmutable residual recordとして保存し、機械的欠陥を残存Issueとして採用してはならない。 | `ACC-REV-005..006`; `ACC-FIX-008`; `ACC-PERF-002` | `review_and_audit.md`; `pipeline_contracts.md` |
| `REQ-FR-028` | P0 | Transport retry、response-structure retry、semantic Revision、Completion attemptは別々に分類・計数し、一つの上限を別カテゴリの再試行へ流用してはならない。 | `ACC-CFG-005..008`; `ACC-FIX-010`; `ACC-PERF-001..003` | `configuration_contracts.md`; `pipeline_contracts.md` |
| `REQ-FR-029` | P0 | Candidateはversioned immutable directoryへ保存し、active candidateはRun Stateが指すvalid Candidate manifestだけで選択しなければならない。 | `ACC-RUN-006..010`; `ACC-REC-011..018` | `runtime_records.md`; `workspace_layout.md` |
| `REQ-FR-030` | P0 | 一つのScene lifecycleは`CARD_ACCEPTED`、`PROSE_FROZEN`、`DELTA_ACCEPTED`、`COMMIT_PREPARED`のCheckpoint phaseを持ち、file存在だけでphaseを進めてはならない。 | `ACC-PIPE-SCENE-001,006,010..011`; `ACC-COMMIT-010`; `ACC-REC-021` | `scene_generation.md`; `runtime_records.md` |
| `REQ-FR-031` | P0 | 各adopted Generationは`current-canon.json`と`knowledge-items.json`を別rootとして持ち、Knowledge itemをcurrent Canonへ混在させてはならない。 | `ACC-CANON-001..002`; `ACC-RUN-011..015` | `canon_records.md`; `ledger_contracts.md` |
| `REQ-FR-032` | P0 | Story StateはCharacter、Relationship、Thread、Knowledge audience、Story clockの現在値を完全な専用rootで管理し、Canon固定情報と重複させてはならない。 | `ACC-STATE-001..002`; `ACC-CANON-003..008` | `story_state.md`; `ledger_contracts.md` |
| `REQ-FR-033` | P0 | Knowledge StateはCharacter=`unknown`、Reader=`withheld`をsparse defaultとし、defaultと同じ明示rowを保存してはならない。 | `ACC-STATE-003..004`; `ACC-INIT-DATA-007` | `story_state.md`; `canon_records.md` |
| `REQ-FR-034` | P0 | Required Major Threadはretireできず、Scene actionとstatus／progress transition、巻境界のvolume dispositionを別のcontractとして管理しなければならない。 | `ACC-CANON-005`; `ACC-STATE-005,007`; `ACC-VH-002,005` | `canon_records.md`; `story_state.md` |
| `REQ-FR-035` | P0 | Story clockは採用Scene順、時刻label、parallel group、最後のScene、現在座標を管理し、Scene Commitだけが`current_order`を一つ増加させなければならない。 | `ACC-STATE-006`; `ACC-COMMIT-013`; `ACC-VH-006` | `story_state.md`; `commit_and_output.md` |
| `REQ-FR-036` | P0 | 全adopted Evidenceは凍結本文に一度だけ現れる完全一致quoteを持ち、Unicode code-point offset、quote hash、prose hash、Scene／Commit identityで検証できなければならない。 | `ACC-EVID-003..005,009`; `ACC-COMMIT-008` | `evidence_and_updates.md`; `scene_commit_fixture.md` |
| `REQ-FR-037` | P0 | Scene Commitは、全committed-delta changeがafter rootsに現れ、全parent-to-child root changeがcommitted deltaに表現される双方向対応を証明しなければならない。 | `ACC-EVID-010`; `ACC-COMMIT-005..007` | `evidence_and_updates.md`; `commit_and_output.md` |
| `REQ-FR-038` | P0 | Scene adoptionは`COMMIT-01` dry validation、`COMMIT-02` ID allocation／merge、`COMMIT-03` manifests／Validation、`COMMIT-04` final move／HEAD-lastの四Stageで実行しなければならない。 | `ACC-COMMIT-001..014`; `ACC-REC-021`; `ACC-FIX-011` | `commit_and_output.md`; `runtime_and_recovery.md` |
| `REQ-FR-039` | P0 | 各Volume終了後は実際のfinal Scene HEADからcomplete Handoff candidateを生成・Reviewし、次巻またはCompletionへ必要なsafe carry-overを保存しなければならない。 | `ACC-VH-001..003,008` | `commit_and_output.md`; `runtime_records.md` |
| `REQ-FR-040` | P0 | Volume Handoffは独立した`volume_handoff` Commit／Generationとして採用し、Story Stateでは`thread_states[].volume_disposition`以外を変更してはならない。 | `ACC-VH-004..007`; `ACC-RUN-014`; `ACC-REC-022` | `story_state.md`; `runtime_records.md`; `commit_and_output.md` |
| `REQ-FR-041` | P0 | Generation IDは全Commitで進み、Story-clock orderとsuccessful Scene countはScene Commitだけで進むため、Generation番号をScene順として扱ってはならない。 | `ACC-COMMIT-013`; `ACC-VH-006`; `ACC-FIX-002..004` | `ledger_contracts.md`; `runtime_records.md` |
| `REQ-FR-042` | P0 | Completionはfinal Scene Generationではなく、final Volume Handoffが`canon/HEAD`に採用された後だけ開始しなければならない。 | `ACC-VH-008`; `ACC-OUT-001`; `ACC-FIX-004..005` | `commit_and_output.md`; `pipeline_contracts.md` |
| `REQ-FR-043` | P0 | COMP-PREはLLM call前にfinal HEAD、plans、Scenes、Evidence、Story clock、Required Threads／Ending criteria、Handoffs、active work absence、Context capacityを機械検証しなければならない。 | `ACC-OUT-001`; `ACC-CTX-012,015..016` | `review_and_audit.md`; `commit_and_output.md` |
| `REQ-FR-044` | P0 | Completion auditは`complete`、`complete_with_residual_issues`、`incomplete`の一つを返し、最初のstructurally valid attemptを選択してprivate auditへ保存しなければならない。 | `ACC-REV-007..008`; `ACC-OUT-002..004`; `ACC-PERF-003` | `review_and_audit.md`; `commit_and_output.md` |
| `REQ-FR-045` | P0 | Structurally validな`incomplete`は再試行、自動story修正、Gate pass、CURRENT更新の理由にしてはならず、diagnostic artifactsを残してmanual interventionへ停止しなければならない。 | `ACC-REV-008`; `ACC-OUT-012`; `ACC-FIX-009`; `ACC-REC-031` | `SPECIFICATION.md`; `commit_and_output.md` |
| `REQ-FR-046` | P0 | CompletionおよびPublication StageはCanon、Knowledge、Story State、Evidence、plans、Scenes、Handoffs、`canon/HEAD`を変更してはならない。 | `ACC-OUT-001..016`; `ACC-EVID-010`; `ACC-REC-023` | `ledger_contracts.md`; `commit_and_output.md` |
| `REQ-FR-047` | P0 | Runは`running`、resume可能なpause／stop、`failed`、manual intervention、`completed`を機械的に区別し、status、next Stage、stop reasonを整合させなければならない。 | `ACC-RUN-004`; `ACC-REC-027..032`; `ACC-CLI-006` | `runtime_records.md`; `runtime_and_recovery.md` |
| `REQ-FR-048` | P0 | Version 1はlegacy `state.json`、legacy Stage名、legacy ID、legacy raw log、legacy outputを自動migrationまたはauthorityとして利用してはならない。 | `ACC-CFG-010`; `ACC-PKG-005`; `ACC-REC-004..006` | `IMPLEMENTATION_STATUS.md`; `series_engine_design.md` |
| `REQ-FR-049` | P0 | 公開CLI／public APIの結果とexpected errorはredactedで、Run status、completed／next Stage、target、HEAD、CURRENT、safe reasonを返し、private Context／audit bodyを返してはならない。 | `ACC-CLI-006..007`; `ACC-SEC-003..004` | `series_engine_design.md`; `runtime_records.md` |
| `REQ-FR-050` | P0 | Artifactまたはdirectoryの存在だけをadoptionの証拠としてはならず、Storyはvalid `canon/HEAD`、Publicationはvalid `output/CURRENT`からのみadoptedと判定しなければならない。 | `ACC-COMMIT-011..012`; `ACC-VH-007`; `ACC-OUT-014..016`; `ACC-REC-005..006,019..026` | `runtime_and_recovery.md`; `ledger_contracts.md` |

# Part 2: Publication要件

## 11. Publication要件

Reader-facing payload、Validation、Gate、CURRENT adoption。

| Requirement ID | P | Normative requirement | Verification | Primary authority |
|---|---:|---|---|---|
| `REQ-PUB-001` | P0 | OUT-01はpersist-before-useされた一意な`pub-NNNNNN` Publication IDを割り当て、失敗したIDを再利用してはならない。 | `ACC-OUT-002`; `ACC-REC-009`; `ACC-FIX-006` | `commit_and_output.md`; `runtime_records.md` |
| `REQ-PUB-002` | P0 | Default publicationは`manuscript/`、`metadata/`、`reports/`、`publication-validation.json`、`publication-manifest.json`の登録済みlayoutを使用しなければならない。 | `ACC-RUN-016..019`; `ACC-OUT-005..010` | `workspace_layout.md`; `commit_and_output.md` |
| `REQ-PUB-003` | P0 | 全巻／巻別manuscriptのVolume、Chapter、Scene順は採用plansから決定し、filesystem列挙順、mtime、最大番号から決定してはならない。 | `ACC-OUT-005`; `ACC-FIX-006..007` | `SPECIFICATION.md`; `commit_and_output.md` |
| `REQ-PUB-004` | P0 | Publication headingは採用plan titleからcodeが決定的に追加し、Scene prose bytesおよびEvidence sourceとして扱ってはならない。 | `ACC-OUT-005`; `ACC-EVID-003..005`; `ACC-SCENE-DATA-007` | `commit_and_output.md`; `scene_artifacts.md` |
| `REQ-PUB-005` | P0 | Reader-facing payloadはpersistent IDs、workspace内部path、candidate／checkpoint／staging path、private Review／Completion、provider／runtime metadata、author truth、credentialを含んではならない。 | `ACC-OUT-006..007`; `ACC-SEC-001,004`; `ACC-PROMPT-007` | `SPECIFICATION.md`; `review_and_audit.md` |
| `REQ-PUB-006` | P0 | Series／Volume metadataはreader／distribution用途に必要なtitle、genre、counts、profile、source Generation、Completion result、relative path／hash／character countを機械的に検証可能な形で含まなければならない。 | `ACC-OUT-005..007`; `ACC-RUN-016..019` | `commit_and_output.md`; `runtime_records.md` |
| `REQ-PUB-007` | P0 | PublicationのCompletion reportはsafe projectionであり、private auditのauthor truth、private Evidence analysis、Review issue textを直接複製してはならない。 | `ACC-OUT-007`; `ACC-SEC-004`; `ACC-CTX-012` | `review_and_audit.md`; `context_contracts.md` |
| `REQ-PUB-008` | P0 | OUT-01／02はpayload filesだけから`payload_set_sha256`を計算し、Validation、Manifest、provisional build manifestをpayload setへ含めてはならない。 | `ACC-REV-011`; `ACC-OUT-008`; `ACC-FIX-006` | `review_and_audit.md`; `commit_and_output.md` |
| `REQ-PUB-009` | P0 | OUT-02は全payloadのpath、role、size、hash、content ruleをValidationし、失敗時はGate／adoptionへ進めてはならない。 | `ACC-OUT-009`; `ACC-REV-011`; `ACC-REC-023` | `commit_and_output.md`; `review_and_audit.md` |
| `REQ-PUB-010` | P0 | Final Publication manifestはpayloadとValidationを`files`へ列挙し、`content_set_sha256`を計算し、自身を列挙またはhashしてはならない。 | `ACC-RUN-016..019`; `ACC-OUT-010`; `ACC-REV-011` | `runtime_records.md`; `commit_and_output.md` |
| `REQ-PUB-011` | P0 | COMP-PUBLISHはCompletionが`complete`または`complete_with_residual_issues`で、全mechanical checkが成功した場合だけGateをpassにしなければならない。 | `ACC-OUT-011`; `ACC-REV-012` | `review_and_audit.md`; `commit_and_output.md` |
| `REQ-PUB-012` | P0 | Completionが`incomplete`またはPublication mechanical validationが失敗した場合、Gateはfailでなければならず、OUT-03へ進めてはならない。 | `ACC-OUT-009,012`; `ACC-FIX-009` | `commit_and_output.md` |
| `REQ-PUB-013` | P0 | Publication Gateはroot-relative references、Manifest／Validation／payload／content hashes、rename-stable `publication_snapshot_sha256`を持ち、staging root pathを保存してはならない。 | `ACC-REV-012`; `ACC-OUT-013`; `ACC-PATH-007` | `review_and_audit.md`; `runtime_records.md` |
| `REQ-PUB-014` | P0 | OUT-03 normal adoptionはfinalized staging rootと同一Gate snapshotを検証し、final Publication directoryへrenameし、final rootで再検証しなければならない。 | `ACC-OUT-014`; `ACC-REC-023`; `ACC-FIX-011` | `commit_and_output.md`; `runtime_and_recovery.md` |
| `REQ-PUB-015` | P0 | Publication rename後かつCURRENT更新前のCrashだけは、元のpassing Gateとexact transaction identityを条件にfinal rootから明示的OUT-03 recoveryを許可しなければならない。 | `ACC-OUT-015`; `ACC-REC-023` | `commit_and_output.md`; `runtime_and_recovery.md` |
| `REQ-PUB-016` | P0 | `output/CURRENT`はPublication adoptionの最後に更新し、valid CURRENTとRun Stateが一致した場合だけRunを`completed`としなければならない。 | `ACC-OUT-016`; `ACC-REC-006,032`; `ACC-FIX-006` | `runtime_records.md`; `runtime_and_recovery.md` |

# Part 3: 運用・Runtime要件

## 12. 運用・Runtime要件

設定、lock、workspace、counter、audit、status、observability。

| Requirement ID | P | Normative requirement | Verification | Primary authority |
|---|---:|---|---|---|
| `REQ-OPS-001` | P0 | Effective configは全defaultとoverrideをmaterializeしたcomplete redacted objectでなければならず、実行時に未materialize defaultへ依存してはならない。 | `ACC-CFG-001`; `ACC-RUN-001` | `configuration_contracts.md` |
| `REQ-OPS-002` | P0 | Credential値をEffective configへ保存してはならず、保存できるのは登録されたcredential environment-variable名だけでなければならない。 | `ACC-CFG-002`; `ACC-SEC-001` | `configuration_contracts.md`; `review_and_audit.md` |
| `REQ-OPS-003` | P0 | LLM operation設定は登録済み10 operation keyを正確に持ち、Stageごとの未知または欠落keyをstartup時に拒否しなければならない。 | `ACC-CFG-003`; `ACC-PROMPT-001` | `configuration_contracts.md`; `prompt_template_design.md` |
| `REQ-OPS-004` | P0 | Provider timeoutはconnect、first event、idle、total callを区別し、各値の階層と上限を検証しなければならない。 | `ACC-CFG-006`; `ACC-PERF-001` | `configuration_contracts.md`; `series_engine_design.md` |
| `REQ-OPS-005` | P0 | Transport retryとresponse-structure retryは登録されたerror分類とbounded exponential backoff／jitterに従わなければならない。 | `ACC-CFG-007..008`; `ACC-PERF-001` | `configuration_contracts.md`; `pipeline_contracts.md` |
| `REQ-OPS-006` | P0 | RuntimeはCall、token、cost、active elapsed、retry、revision、Completion attempt、successful Scene countを永続的に計数し、次call前にbudgetを検査しなければならない。 | `ACC-CFG-009`; `ACC-REC-007..010,028`; `ACC-PERF-001` | `configuration_contracts.md`; `runtime_records.md` |
| `REQ-OPS-007` | P0 | Publishing profileはplatform、format、volume range、access policy、local resolution、reader question、auto-publish=falseを完全にmaterializeしなければならない。 | `ACC-CFG-011`; `ACC-OUT-005..010` | `configuration_contracts.md`; `SPECIFICATION.md` |
| `REQ-OPS-008` | P0 | Audit retention、compression、redaction、最大容量、warning thresholdを設定可能にし、必要なactive／adopted referencesをretentionで削除してはならない。 | `ACC-CFG-012`; `ACC-SEC-006`; `ACC-PERF-005` | `configuration_contracts.md`; `review_and_audit.md` |
| `REQ-OPS-009` | P0 | 一つのworkspaceは一つのexclusive mutating writerだけを許可し、unsupported lock／filesystem semanticsを明示的に拒否しなければならない。 | `ACC-REC-001..003`; `ACC-CLI-003` | `runtime_and_recovery.md`; `series_engine_design.md` |
| `REQ-OPS-010` | P0 | WorkspaceはRun manifest、Run State、Counters、Effective configの四Runtime rootを正確なpathとSchemaで持たなければならない。 | `ACC-RUN-001`; `ACC-REC-004` | `runtime_records.md`; `workspace_layout.md` |
| `REQ-OPS-011` | P0 | Mutable Runtime rootはcomplete-file canonical bytesとしてatomic replacementし、field patchまたはin-place editを使用してはならない。 | `ACC-RUN-002..003`; `ACC-CORE-001..002`; `ACC-FIX-011` | `runtime_records.md`; `series_engine_design.md` |
| `REQ-OPS-012` | P0 | Artifact classは`candidate`、`checkpoint`、`staged_internal`、`staged_internal_validation`、`adopted`、`audit`だけを使用し、複合／legacy classを使用してはならない。 | `ACC-RUN-005` | `runtime_records.md`; `workspace_layout.md` |
| `REQ-OPS-013` | P0 | 全code-owned ID counterはpersist-before-use、単調増加、非再利用でなければならず、失敗により生じたgapを保持しなければならない。 | `ACC-COMMIT-003..004`; `ACC-REC-007..009` | `runtime_records.md`; `runtime_and_recovery.md` |
| `REQ-OPS-014` | P0 | 各provider HTTP attemptは一意なCall ID、Stage、target、role、attempt identity、Context／prompt／Schema／config identity、timing、usage、outcomeを持つimmutable auditを作らなければならない。 | `ACC-REV-009..010`; `ACC-PROMPT-008`; `ACC-REC-010,013` | `review_and_audit.md`; `prompt_template_design.md` |
| `REQ-OPS-015` | P0 | 各code Stageはsource authority、input Run-state revision、durable outputs、pointer changes、result／errorを持つimmutable operation auditを作らなければならない。 | `ACC-REV-009..010`; `ACC-REC-026`; `ACC-FIX-011` | `series_engine_design.md`; `review_and_audit.md` |
| `REQ-OPS-016` | P0 | 全workspace pathは`workspace_layout.md`のcanonical treeとroleに従い、同一semantic artifactを複数のauthority pathへ保存してはならない。 | `ACC-PATH-001..007`; `ACC-RUN-001..019` | `workspace_layout.md` |
| `REQ-OPS-017` | P0 | Run Stateは各complete replacementで`state_revision`を正確に一つ増加させ、active target、Candidate、Checkpoint、HEAD、CURRENT、statusを整合させなければならない。 | `ACC-RUN-002..004,009`; `ACC-REC-014,026,032` | `runtime_records.md` |
| `REQ-OPS-018` | P0 | Run status、last completed Stage、next Stage、target、stop reasonはcanonical transition graphと一致し、unknown transitionを保存してはならない。 | `ACC-RUN-004`; `ACC-CLI-005..006`; `ACC-REC-027..032` | `pipeline_contracts.md`; `runtime_records.md` |
| `REQ-OPS-019` | P0 | 通常logとprogressはRun ID、Stage、target、status、HEAD、CURRENT、Call ID、duration、safe errorを構造化して示し、resume authorityとして使用してはならない。 | `ACC-SEC-002..003`; `ACC-CLI-007`; `ACC-PERF-006` | `series_engine_design.md`; `review_and_audit.md` |
| `REQ-OPS-020` | P0 | Read-only inspectionはRun State、HEAD、CURRENT、adopted plans／Scenes／Handoffs、audits、Completion、Publication Validation／Manifest、quarantine理由を変更せず確認可能でなければならない。 | `ACC-REC-004..006,024..026`; `ACC-RUN-011..019` | `SPECIFICATION.md`; `workspace_layout.md` |

# Part 4: Recovery要件

## 13. Recovery要件

Crash後のauthority選択、resume、quarantine、manual intervention。

| Requirement ID | P | Normative requirement | Verification | Primary authority |
|---|---:|---|---|---|
| `REQ-REC-001` | P0 | Startupはlock、filesystem security、Runtime roots、HEAD、CURRENT、Run-state comparison、selected Checkpoint、selected Candidate、referenced transaction、orphan分類の順で検証しなければならない。 | `ACC-REC-001..006`; `ACC-PATH-001..007` | `runtime_and_recovery.md` |
| `REQ-REC-002` | P0 | Valid HEAD／CURRENTはRun Stateより強いadoption authorityであり、Run Stateが遅れている場合はprovider callまたはID allocationを繰り返さずreconcileしなければならない。 | `ACC-COMMIT-012`; `ACC-OUT-016`; `ACC-REC-014,026,032` | `runtime_and_recovery.md`; `ledger_contracts.md` |
| `REQ-REC-003` | P0 | Candidate fileだけが存在しmanifestがない場合、candidateを採用またはresumeせずquarantineして再生成しなければならない。 | `ACC-REC-011` | `runtime_and_recovery.md` |
| `REQ-REC-004` | P0 | Candidate manifestだけが存在しcandidateがない場合、manifestからcandidateを合成せずquarantineして再生成しなければならない。 | `ACC-REC-012` | `runtime_and_recovery.md` |
| `REQ-REC-005` | P0 | Raw successful LLM auditだけが存在する場合、responseをCandidateへ昇格せず、使用量とCall IDを保持して新しいCall IDでprovider operationを再実行しなければならない。 | `ACC-REC-010,013` | `runtime_and_recovery.md`; `review_and_audit.md` |
| `REQ-REC-006` | P0 | Valid selected Candidate manifestがdurableでRun Stateが遅れている場合、completed provider callを繰り返さずmanifestのexact next Stageへreconcileしなければならない。 | `ACC-REC-014` | `runtime_and_recovery.md`; `runtime_records.md` |
| `REQ-REC-007` | P0 | Unreferenced Reviewをactive authorityへ昇格してはならず、referenced valid ReviewだけはReview callを繰り返さず正しいRevision／adoption routeへ利用しなければならない。 | `ACC-REC-015..016` | `runtime_and_recovery.md`; `review_and_audit.md` |
| `REQ-REC-008` | P0 | Partial next candidate versionまたはmissing Context snapshotは既存versionを上書き・推測せず、invalid historyとしてquarantine／regenerateしなければならない。 | `ACC-REC-017..018` | `runtime_and_recovery.md` |
| `REQ-REC-009` | P0 | Checkpoint recoveryはRun Stateが選ぶexact Sceneとmanifest phaseだけを信頼し、unreferenced later-phase fileをphase昇格に利用してはならない。 | `ACC-PIPE-SCENE-011`; `ACC-REC-021` | `runtime_and_recovery.md`; `scene_generation.md` |
| `REQ-REC-010` | P0 | Scene candidate／checkpointのsource Generationがcurrent HEADと異なる場合、rebaseせず全Scene chainを無効化し、既にadoptedでなければSC-01から再生成しなければならない。 | `ACC-PIPE-SCENE-012`; `ACC-REC-021` | `scene_generation.md`; `runtime_and_recovery.md` |
| `REQ-REC-011` | P0 | Genesisの各failpointは、HEAD変更前をunadopted、HEAD変更後をadoptedとして一意に分類しなければならない。 | `ACC-PIPE-INIT-007`; `ACC-REC-019`; `ACC-FIX-011` | `runtime_and_recovery.md`; `input_and_initial.md` |
| `REQ-REC-012` | P0 | Plan adoptionの各failpointは、ready candidate、staging、final plan、Run Stateのdurabilityから再実行／reconcile／mechanical conflictを一意に決めなければならない。 | `ACC-PIPE-PLAN-006`; `ACC-REC-020`; `ACC-FIX-011` | `runtime_and_recovery.md`; `planning.md` |
| `REQ-REC-013` | P0 | Scene Commitの各failpointは、allocation、merge、COMMIT_PREPARED、final Generation／Scene、HEAD、Run StateのdurabilityからID再利用なしで一意に復旧しなければならない。 | `ACC-COMMIT-003..012`; `ACC-REC-021`; `ACC-FIX-011` | `runtime_and_recovery.md`; `commit_and_output.md` |
| `REQ-REC-014` | P0 | Handoff transactionの各failpointは、Handoff／Generation／HEAD／Run Stateのdurabilityから一意に復旧し、HEAD前のfinal-looking Handoffを採用してはならない。 | `ACC-VH-004..008`; `ACC-REC-022`; `ACC-FIX-011` | `runtime_and_recovery.md` |
| `REQ-REC-015` | P0 | Publication transactionの各failpointはpayload、Validation、Manifest、Gate、staging／final root、CURRENT、Run Stateからnormal resume、explicit recovery、reconcile、manual interventionを一意に決めなければならない。 | `ACC-OUT-008..016`; `ACC-REC-023`; `ACC-FIX-011` | `runtime_and_recovery.md`; `commit_and_output.md` |
| `REQ-REC-016` | P0 | Orphan分類はvalid HEAD、CURRENT、selected Candidate、selected Checkpoint、referenced transactionからのreachabilityを証明した後だけ行わなければならない。 | `ACC-REC-024`; `ACC-SEC-006` | `runtime_and_recovery.md`; `workspace_layout.md` |
| `REQ-REC-017` | P0 | Quarantineはimmutable recovery auditを伴い、通常startupで自動promotionまたはadoption sourceとして利用してはならない。 | `ACC-REC-025`; `ACC-REC-026` | `runtime_and_recovery.md` |
| `REQ-REC-018` | P0 | 同じdurable stateに対するstartup recoveryはidempotentで、追加Call ID、persistent ID、usage、candidate version、residual issue、quarantine copy、pointer変更を作ってはならない。 | `ACC-REC-026` | `runtime_and_recovery.md` |
| `REQ-REC-019` | P0 | User stop、budget stop、pause、recoverable failedはregistered durable boundaryで保存し、resume compatibility検査後にだけrunningへ戻さなければならない。 | `ACC-REC-027..030`; `ACC-CLI-006` | `runtime_and_recovery.md`; `series_engine_design.md` |
| `REQ-REC-020` | P0 | Invalid HEAD／CURRENT、counter regression、conflicting immutable artifacts、unsupported migration、ambiguous Publication roots、valid Completion incompleteは自動推測せずmanual interventionまたはterminal stateへ移行しなければならない。 | `ACC-REC-005..008,023,031..032`; `ACC-FIX-009` | `runtime_and_recovery.md`; `IMPLEMENTATION_STATUS.md` |

# Part 5: Security／Privacy要件

## 14. Security／Privacy要件

Credential、秘密投影、prompt injection、path boundary。

| Requirement ID | P | Normative requirement | Verification | Primary authority |
|---|---:|---|---|---|
| `REQ-SEC-001` | P0 | Credential値はworkspace内のconfig、Context、prompt、candidate、audit、log、publication、errorへ一切永続化してはならない。 | `ACC-CFG-002`; `ACC-SEC-001` | `configuration_contracts.md`; `review_and_audit.md` |
| `REQ-SEC-002` | P0 | Authorization、cookie、provider secret header、および登録済みsecret patternはLLM auditと通常logでredactしなければならない。 | `ACC-SEC-002`; `ACC-REV-010` | `review_and_audit.md`; `series_engine_design.md` |
| `REQ-SEC-003` | P0 | Expected errorとCLI出力はcredential、private body、unnecessary absolute path、Python tracebackを公開せず、safe error codeとmessageを返さなければならない。 | `ACC-SEC-003`; `ACC-CLI-006..007` | `series_engine_design.md` |
| `REQ-SEC-004` | P0 | Private Author artifact、private Review、Handoff、Completion audit、Context snapshotをreader-facing Publicationへ複製してはならない。 | `ACC-SEC-004`; `ACC-OUT-006..007` | `context_contracts.md`; `commit_and_output.md` |
| `REQ-SEC-005` | P0 | Writer provider requestはThread author truth／resolution condition、Knowledge author truth、Ending source text、非POV private Stateの登録sentinelを含んではならない。 | `ACC-CTX-006..008`; `ACC-SEC-005`; `ACC-PROMPT-007` | `context_contracts.md`; `prompt_template_design.md` |
| `REQ-SEC-006` | P0 | Continuity provider requestはWriter-safe dataだけを使用し、author truth、future private plan、private Ending／Knowledge contentを含んではならない。 | `ACC-CTX-009`; `ACC-PIPE-SCENE-007`; `ACC-PROMPT-007` | `context_contracts.md`; `scene_generation.md` |
| `REQ-SEC-007` | P0 | Private Review extensionはcontradiction検出に必要な最小secretだけを持ち、writer-safe Revisionへsecret answerを直接転載してはならない。 | `ACC-CTX-010`; `ACC-REV-002..003`; `ACC-PROMPT-007` | `context_contracts.md`; `review_and_audit.md` |
| `REQ-SEC-008` | P0 | Brief、prose、notes、Review text内の命令風文字列はuntrusted dataとしてdelimiter内へ固定し、Stage、Schema、response format、tool／retrieval behaviorを変更してはならない。 | `ACC-PROMPT-004,007`; `ACC-SEC-004..005` | `prompt_template_design.md` |
| `REQ-SEC-009` | P0 | 全managed pathはworkspace-relative POSIX、canonical case、fixed-width coordinatesでなければならず、traversal、absolute path、unknown normalizationを拒否しなければならない。 | `ACC-PATH-001..004,006` | `workspace_layout.md`; `series_engine_design.md` |
| `REQ-SEC-010` | P0 | Symlink、junction、mountまたはexternal referenceによりworkspace root外へ到達するread／writeを拒否しなければならない。 | `ACC-PATH-005`; `ACC-SEC-007` | `workspace_layout.md`; `runtime_and_recovery.md` |
| `REQ-SEC-011` | P0 | Storycraftはprovider call以外のWeb、filesystem retrieval、外部tool、別conversation memoryをLLMへ要求または暗黙利用してはならない。 | `ACC-PROMPT-007`; `ACC-SEC-001..005` | `prompt_template_design.md`; `SPECIFICATION.md` |
| `REQ-SEC-012` | P0 | Publication内部pathはroot-relativeで自身のroot内だけへ解決し、staging prefix、workspace-private path、external symlinkを含んではならない。 | `ACC-PATH-007`; `ACC-RUN-019`; `ACC-SEC-007` | `runtime_records.md`; `workspace_layout.md` |

# Part 6: 非機能要件

## 15. 非機能要件

Canonical bytes、determinism、bounded behavior、packaging、testability。

| Requirement ID | P | Normative requirement | Verification | Primary authority |
|---|---:|---|---|---|
| `REQ-NFR-001` | P0 | 全persisted JSONはUTF-8、NFC、deterministic key order、contract-normalized array order、finite strict numbers、compact bytes、exact final-LF policyでcanonicalizeされなければならない。 | `ACC-CORE-001,004`; `ACC-FIX-007` | `implementation_acceptance.md`; `series_engine_design.md` |
| `REQ-NFR-002` | P0 | 全SHA-256は定義されたcanonical bytesに対して計算し、pretty display、filesystem metadata、非canonical parser representationへ依存してはならない。 | `ACC-CORE-002`; `ACC-FIX-006..007` | `implementation_acceptance.md`; `runtime_records.md` |
| `REQ-NFR-003` | P0 | Prose、pointer、JSONLを含むtext artifactはNFC、LF、BOM／control rejection、exact final-LFなど専用canonical text contractへ従わなければならない。 | `ACC-CORE-005`; `ACC-SCENE-DATA-005..006` | `implementation_acceptance.md`; `scene_artifacts.md` |
| `REQ-NFR-004` | P0 | 全structured rootとunion branchはunknown field、missing required field、wrong discriminator、invalid enum、boolean-as-integerを拒否しなければならない。 | `ACC-CORE-003..004`; `ACC-PROMPT-004`; 各data acceptance group | `implementation_acceptance.md`; field-level contracts |
| `REQ-NFR-005` | P0 | Context snapshotはtimestamp-free、hash-named、source-ref complete、self-hashなしのdeterministic artifactで、同じauthority inputから同じbytesを生成しなければならない。 | `ACC-CTX-001..005`; `ACC-FIX-007` | `context_contracts.md` |
| `REQ-NFR-006` | P0 | 全LLM callはrendered system／user、attached Schema、provider framing overheadを含む最終request全体のtoken preflightをCall ID allocation前に実行しなければならない。 | `ACC-CTX-013..016`; `ACC-PERF-004` | `context_contracts.md`; `prompt_template_design.md` |
| `REQ-NFR-007` | P0 | Retry、Review、Revision、Completion attemptはすべて設定上限内で停止し、Review-until-passまたはCompletion-until-complete loopを実装してはならない。 | `ACC-PERF-001..003`; `ACC-FIX-008..010` | `pipeline_contracts.md`; `configuration_contracts.md` |
| `REQ-NFR-008` | P0 | Context constructionはcurrent Stageに必要なselected recordsだけを読み込み、whole-series mutable objectまたはquadratic full-root scanを前提としてはならない。 | `ACC-PERF-004`; `ACC-CTX-013..015` | `context_contracts.md`; `series_engine_design.md` |
| `REQ-NFR-009` | P0 | Streaming response、audit保存、retentionはboundedで、unbounded in-memory response accumulationまたは無制限audit growthを許可してはならない。 | `ACC-PERF-005`; `ACC-CFG-012` | `configuration_contracts.md`; `series_engine_design.md` |
| `REQ-NFR-010` | P0 | Startupはpointer-selected authorityを先に検証し、candidate／audit historyを必要に応じてlazyに扱い、全file contentのmtime scanへ依存してはならない。 | `ACC-PERF-006`; `ACC-REC-004,024` | `runtime_and_recovery.md`; `series_engine_design.md` |
| `REQ-NFR-011` | P0 | Mandatory automated suiteはreal network、real credential、external database／object store、特定home directoryを必要としてはならない。 | `ACC-PKG-001..004`; `ACC-FIX-001..011`; acceptance philosophy | `implementation_acceptance.md` |
| `REQ-NFR-012` | P0 | Timeout、backoff、elapsed-time、safe-stop試験はfake wall／monotonic clockとfake sleeperを使用し、mandatory testで実時間待機してはならない。 | `ACC-PERF-001`; mandatory deterministic doubles | `implementation_acceptance.md`; `series_engine_design.md` |
| `REQ-NFR-013` | P0 | Prompt／Schema／registry assetはinstalled packageの一つのpackage-data rootからloadし、repository source tree、cwd、user homeへfallbackしてはならない。 | `ACC-PKG-003..004`; `ACC-PROMPT-001..003` | `prompt_template_design.md` |
| `REQ-NFR-014` | P0 | Release artifactはsource tree外でwheel build／isolated install／CLI smoke／prompt and Schema loadを成功しなければならない。 | `ACC-PKG-001..004`; `ACC-CLI-001` | `implementation_acceptance.md`; `prompt_template_design.md` |
| `REQ-NFR-015` | P0 | 最低Python version、package version、workspace／state／code compatibilityはpackage metadataとRun manifestで明示し、unsupported runtimeを拒否しなければならない。 | `ACC-PKG-005..006`; `ACC-CFG-010` | `configuration_contracts.md`; `runtime_records.md` |
| `REQ-NFR-016` | P0 | Prompt、Schema、renderer、immutable config、workspace／state versionの非互換変更はactive candidateを自動migrationせずresume前に停止しなければならない。 | `ACC-CFG-010`; `ACC-PKG-005`; `ACC-PROMPT-003` | `configuration_contracts.md`; `prompt_template_design.md` |
| `REQ-NFR-017` | P0 | Productionとtestsは同じserializer、hash、path validator、Schema、transition matrix、ID allocator、Context builder、manifest reader、recovery classifierを使用しなければならない。 | `ACC-CORE-001..005`; acceptance philosophy 1.6; 全ACC group | `implementation_acceptance.md`; `series_engine_design.md` |
| `REQ-NFR-018` | P0 | Release suiteはsuccess、residual issue、incomplete Completion、structural retry、全登録failpoint、security mutation、Publication reproducibilityをdeterministic fixtureで証明しなければならない。 | `ACC-FIX-001..011`; Release gates 46..54; `ACC-SEC-001..007` | `implementation_acceptance.md`; example fixtures |

# Part 7: Traceability and governance

## 16. Requirement inventory

| Area | first ID | last ID | count |
|---|---|---|---:|
| `FR` | `REQ-FR-001` | `REQ-FR-050` | 50 |
| `PUB` | `REQ-PUB-001` | `REQ-PUB-016` | 16 |
| `OPS` | `REQ-OPS-001` | `REQ-OPS-020` | 20 |
| `REC` | `REQ-REC-001` | `REQ-REC-020` | 20 |
| `SEC` | `REQ-SEC-001` | `REQ-SEC-012` | 12 |
| `NFR` | `REQ-NFR-001` | `REQ-NFR-018` | 18 |
| **total** |  |  | **136** |

## 17. Requirement-to-acceptance trace rule

Release evidence must make the following query possible for every Requirement ID:

```text
Requirement ID
→ design authority section
→ Acceptance ID
→ automated test node
→ result
→ fixture
→ code/runtime version
```

A Requirement is not passed when:

```text
only documentation exists
a legacy test passes
a similar field exists
a happy-path command returns zero
a manually inspected prose sample looks acceptable
```

All referenced Acceptance IDs must pass through the canonical commands in `implementation_acceptance.md`.

## 18. Requirement-to-status separation

`IMPLEMENTATION_STATUS.md` owns:

```text
VERIFIED_LEGACY
PARTIAL_FOUNDATION
SPEC_ONLY
BLOCKED_UNVERIFIED
DEPRECATED
ACCEPTED_V1
```

Requirements do not embed current status.

Status may move to`ACCEPTED_V1` only when:

```text
production implementation exists
mapped Acceptance IDs pass
negative/crash/security cases pass where applicable
canonical commands pass
release trace report is complete
```

## 19. Change control

A Requirement change requires:

1. preserving or retiring the existing Requirement ID;
2. updating `SPECIFICATION.md` when user-visible behavior changes;
3. updating the owning design contract;
4. updating exact Acceptance IDs;
5. updating fixtures when canonical bytes／hashes／paths change;
6. updating `IMPLEMENTATION_STATUS.md` without overstating completion;
7. recording compatibility impact for prompt／Schema／workspace／state／config;
8. rerunning all affected release gates.

Breaking changes must not reuse the same prompt bundle、Schema bundle、workspace version、state version、or immutable config identity.

## 20. Requirement mutation policy

Forbidden requirement handling:

```text
weaken a MUST because current code lacks it
mark a Requirement passed from design review alone
replace an exact requirement with “best effort”
silently change an Acceptance range
treat a known mechanical failure as residual semantic issue
use README wording to override a field-level contract
```

Ambiguity is resolved by correcting the documents before implementation proceeds.

## 21. Mechanical acceptance of this document

This Requirements document is valid only when automated documentation checks demonstrate:

```text
all Requirement IDs are unique
each Area starts at 001 and has no gap
FR count = 50
PUB count = 16
OPS count = 20
REC count = 20
SEC count = 12
NFR count = 18
total count = 136
every Requirement has P0, Verification, and authority
every ACC reference uses a registered acceptance prefix
all relative links resolve
no legacy critique／closure／state-v5 artifact is made normative
no Requirement claims current implementation completion
```

---

## 22. Final requirement invariant

The version-1 product is acceptable only when durable validated data can answer:

```text
which run
which exact Stage and target
which source Generation and adopted plans
which Candidate／Checkpoint／transaction is selected
which IDs and usage are consumed
which Generation is HEAD
which Publication is CURRENT
which next Stage is legal
which recovery action follows any registered crash boundary
```

None of these answers may depend on:

```text
mtime
largest unreferenced ID
normal log
raw provider success
one mutable monolithic state
unreferenced staging
```
