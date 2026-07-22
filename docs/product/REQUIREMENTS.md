# Storycraft 要件

この文書は、Storycraft Version 1が満たすべき製品要件を定める。

最上位の設計原則は[`../architecture/ARCHITECTURE_PRINCIPLES.md`](../architecture/ARCHITECTURE_PRINCIPLES.md)である。

利用者向けの説明は`SPECIFICATION.md`、現行実装の到達状況は`IMPLEMENTATION_STATUS.md`、具体的な試験は`../design/implementation_acceptance.md`へ分離する。

---

## 1. 前提

Storycraft Version 1は次を前提とする。

```text
単一writer
ローカルfilesystem
一つのworkspace
一つの実行状態ファイル
確定済みdirectoryの上書き禁止
一時directoryからのatomic rename
Hashは原則使用しない
外部監査なし
```

---

## 2. 要件表記

要件ID:

```text
REQ-<分類>-<連番>
```

分類:

| 分類 | 意味 |
|---|---|
| `FR` | 機能 |
| `DATA` | データと保存 |
| `OPS` | 運用 |
| `REC` | 再開と復旧 |
| `SEC` | 安全性と秘密情報 |
| `NFR` | 非機能とRelease |

この文書の要件は、明示がない限りすべてVersion 1の必須要件である。

---

## 3. 要件の優先順位

要件数そのものを品質指標にしない。

Releaseに必要な要件はすべて同じ重要度を持つが、実装順は次を優先する。

```text
保存と実行状態
Sceneの正常系
Crash後の再開
秘密情報の分離
CompletionとPublication
最適化と追加機能
```

---

## 4. 設計との関係

要件は「何を満たすか」を定める。

次の詳細は設計文書へ委譲する。

```text
JSON field
path
Stage名
Python module
atomic write手順
provider request形式
```

設計が要件を満たせない場合は、要件を弱めず設計を修正する。

---

# Part 1: 機能要件

## 5. 機能要件

| 要件ID | 要件 | 主な確認方法 |
|---|---|---|
| `REQ-FR-001` | Storycraftは、一度のBriefまたはKeywords入力から、日本語の長編シリーズを計画・執筆・継続性管理・完結判定・Publication作成まで実行しなければならない。 | 自動全体試験 |
| `REQ-FR-002` | 生成対象は4〜10巻でなければならない。 | 入力・計画試験 |
| `REQ-FR-003` | 公開CLIは`run`、`resume`、`step`を提供しなければならない。 | CLI試験 |
| `REQ-FR-004` | `run`は新規workspaceだけを初期化し、既存workspaceを上書きしてはならない。 | CLI・workspace試験 |
| `REQ-FR-005` | `resume`は既存workspaceの実行状態を読み、再入力なしで再開しなければならない。 | 再開試験 |
| `REQ-FR-006` | `step`は最大一つの意味的Stageを完了して返らなければならない。 | Stage境界試験 |
| `REQ-FR-007` | 開始時の入力はBriefまたはKeywordsの正確に一方でなければならない。 | 入力試験 |
| `REQ-FR-008` | Keywords入力から生成したBriefは、利用者のKeyword、avoid、ending、volume hintを保持しなければならない。 | Brief生成試験 |
| `REQ-FR-009` | 初期設計はConcept、人物、Relationship、World、Thread、Ending、Knowledgeを含まなければならない。 | 初期設計試験 |
| `REQ-FR-010` | Series planは全巻の役割、主人公変化、主要Relationship変化、主要Thread進行、Endingへの到達を定義しなければならない。 | Series plan試験 |
| `REQ-FR-011` | 各Volume planは、その巻開始時の実際のStory状態と前巻Handoffを参照しなければならない。 | Volume plan試験 |
| `REQ-FR-012` | 各Chapter planは、親Volume planと現在のStory状態を参照し、順序付きScene planを持たなければならない。 | Chapter plan試験 |
| `REQ-FR-013` | 採用済みplanは上書きしてはならない。修正が必要な場合は新しいversionを作らなければならない。 | 不変性試験 |
| `REQ-FR-014` | Scene CardはPOV、参加人物、場所、目的、必須beat、開示、禁止開示、許可更新を定義しなければならない。 | Scene Card試験 |
| `REQ-FR-015` | 本文生成へ渡す情報は、Scene執筆に必要な情報だけに限定しなければならない。 | Writer Context試験 |
| `REQ-FR-016` | 本文生成結果は自然な日本語のScene本文だけでなければならない。 | 本文形式試験 |
| `REQ-FR-017` | 本文生成結果にJSON、front matter、heading、箇条書き、表、code fence、内部metadataを含めてはならない。 | 本文形式試験 |
| `REQ-FR-018` | 継続性更新は凍結済み本文に実際に書かれた変化だけを対象にしなければならない。 | 継続性試験 |
| `REQ-FR-019` | 継続性更新はScene Cardで許可された対象だけを変更しなければならない。 | 許可更新試験 |
| `REQ-FR-020` | 通常Sceneは新しいMajor Thread、Ending条件、Temporal ruleを作成してはならない。 | 禁止更新試験 |
| `REQ-FR-021` | Reviewは候補の問題点だけを返し、候補を書き換えてはならない。 | Review試験 |
| `REQ-FR-022` | Revisionは候補全体の置換版を返し、patchやdiffだけを返してはならない。 | Revision試験 |
| `REQ-FR-023` | 通信失敗、応答形式不正、意味的Revisionは別々に扱い、それぞれ上限を持たなければならない。 | Retry試験 |
| `REQ-FR-024` | 一つのSceneでは、Scene Card、本文、継続性更新、Scene確定が完了するまで同じ基準Generationを使用しなければならない。 | Scene一貫性試験 |
| `REQ-FR-025` | Scene確定時は、Scene成果物と新しいGenerationを一時directoryで完成させてから最終directoryへrenameしなければならない。 | Scene確定Crash試験 |
| `REQ-FR-026` | 各Volume終了時に、実際の巻末状態から次巻または完結判定用のHandoffを作成しなければならない。 | Handoff試験 |
| `REQ-FR-027` | Handoffは巻末状態の要約と次巻制約を表し、本文全体を再生成または変更してはならない。 | Handoff試験 |
| `REQ-FR-028` | 完結判定は最終Volume Handoff後に実行しなければならない。 | 完結開始条件試験 |
| `REQ-FR-029` | 完結判定は`complete`、`complete_with_issues`、`incomplete`のいずれかを返さなければならない。 | 完結判定試験 |
| `REQ-FR-030` | 意味的に`incomplete`である結果を、`complete`になるまで再試行してはならない。 | incomplete試験 |
| `REQ-FR-031` | Publicationは採用済みplanとScene本文から、全巻Markdown、巻別Markdown、metadata、完結結果を作成しなければならない。 | Publication試験 |
| `REQ-FR-032` | Publicationを最終directoryへrenameし、実行状態へ反映した後だけrunを`completed`にしなければならない。 | Publication Crash試験 |

# Part 2: データ・保存要件

## 6. データ・保存要件

| 要件ID | 要件 | 主な確認方法 |
|---|---|---|
| `REQ-DATA-001` | 現在の実行位置を表す正本は`runtime/run-state.json`だけでなければならない。 | 実行状態試験 |
| `REQ-DATA-002` | `run-state.json`はrun status、current stage、target、current generation、current publication、active candidate、active sceneを持たなければならない。 | Schema試験 |
| `REQ-DATA-003` | 変更可能なJSONは完全ファイルとしてatomic replacementしなければならない。 | atomic write試験 |
| `REQ-DATA-004` | 確定済みGeneration、Scene、Publication directoryは上書きしてはならない。 | 不変性試験 |
| `REQ-DATA-005` | Generationは`canon.json`、`state.json`、`evidence.json`、`commit.json`を持たなければならない。 | Generation試験 |
| `REQ-DATA-006` | Scene directoryは`scene-card.json`、`prose.md`、`continuity.json`、`commit.json`を持たなければならない。 | Scene artifact試験 |
| `REQ-DATA-007` | Publication directoryは全巻・巻別Markdown、metadata、completion resultを持たなければならない。 | Publication layout試験 |
| `REQ-DATA-008` | Evidenceは少なくともScene ID、本文引用、更新対象、変更内容を持たなければならない。 | Evidence試験 |
| `REQ-DATA-009` | Evidenceの本文引用は採用済みScene本文で確認できなければならない。 | Evidence照合試験 |
| `REQ-DATA-010` | Hashは原則として保存契約へ含めてはならない。 | Schema・文書試験 |
| `REQ-DATA-011` | Manifest graph、Publication Gate、独立HEAD／CURRENT pointerをVersion 1の正本として使用してはならない。 | 構成試験 |
| `REQ-DATA-012` | IDは必要な種類だけを単調増加で管理し、使用前にcounterへ保存し、失敗した番号を再利用してはならない。 | ID試験 |

# Part 3: 運用要件

## 7. 運用要件

| 要件ID | 要件 | 主な確認方法 |
|---|---|---|
| `REQ-OPS-001` | 一つのworkspaceへ同時に書き込めるprocessは一つだけでなければならない。 | lock競合試験 |
| `REQ-OPS-002` | Version 1はローカルfilesystemだけを対象としなければならない。 | 環境・文書試験 |
| `REQ-OPS-003` | 設定は完全な一つの設定objectとしてmaterializeしなければならない。 | 設定試験 |
| `REQ-OPS-004` | Credential値は設定fileへ保存せず、環境変数など外部sourceから取得しなければならない。 | Credential試験 |
| `REQ-OPS-005` | Provider callはconnect、first response、idle、total timeoutを設定できなければならない。 | timeout試験 |
| `REQ-OPS-006` | Call数、token、cost、経過時間の予算を設定し、次のprovider call前に確認しなければならない。 | budget試験 |
| `REQ-OPS-007` | 各provider callはStage、target、provider、model、時刻、usage、resultまたはerrorをAuditへ記録しなければならない。 | Audit試験 |
| `REQ-OPS-008` | Auditは調査用であり、CandidateやStory状態の正本として使用してはならない。 | Recovery試験 |
| `REQ-OPS-009` | 進捗表示はrun-stateと採用済みplanから計算しなければならない。 | 進捗試験 |
| `REQ-OPS-010` | 利用者による停止は、安全な保存境界で実行状態へ反映しなければならない。 | 停止試験 |
| `REQ-OPS-011` | 途中成果物は`runtime/staging/`へ置き、確定後に最終directoryへrenameしなければならない。 | staging試験 |
| `REQ-OPS-012` | 不完全な一時成果物は必要に応じて`runtime/orphans/`へ移動できるが、自動採用してはならない。 | orphan試験 |

# Part 4: 再開・復旧要件

## 8. 再開・復旧要件

| 要件ID | 要件 | 主な確認方法 |
|---|---|---|
| `REQ-REC-001` | 起動時はlock、実行状態、現在Generation、現在Publication、active workの順に確認しなければならない。 | 起動試験 |
| `REQ-REC-002` | 実行状態が読め、必要な確定済み入力が存在する場合は現在Stageから再開しなければならない。 | resume試験 |
| `REQ-REC-003` | 不完全な候補、一時directory、Context、Reviewだけが存在する場合は推測採用せず再生成しなければならない。 | 再生成試験 |
| `REQ-REC-004` | 最終directoryへのrename後、実行状態更新前にCrashした場合は、そのdirectoryが予定された唯一の成果物であり必須fileが読めるときだけ実行状態を更新して再開しなければならない。 | rename後Crash試験 |
| `REQ-REC-005` | `run-state.json`が読めない場合は自動修復してはならない。 | 破損状態試験 |
| `REQ-REC-006` | 実行状態が指す確定済みdirectoryが存在しない場合は人間対応としなければならない。 | 欠落成果物試験 |
| `REQ-REC-007` | 同じIDの確定済みdirectoryが競合する場合は人間対応としなければならない。 | 競合試験 |
| `REQ-REC-008` | Counterが既存IDより小さい場合は自動的に巻き戻しや再採番をしてはならない。 | counter試験 |
| `REQ-REC-009` | 完結判定が`incomplete`の場合はPublicationを採用せず人間対応としなければならない。 | incomplete試験 |
| `REQ-REC-010` | 同じdurable stateに対するRecoveryを繰り返しても、新しいCall ID、Generation、Publication、usageを不必要に作ってはならない。 | 冪等性試験 |

# Part 5: 安全性・秘密情報要件

## 9. 安全性・秘密情報要件

| 要件ID | 要件 | 主な確認方法 |
|---|---|---|
| `REQ-SEC-001` | Credential、Authorization header、cookie、secret tokenをworkspace、Audit、Log、Publicationへ保存してはならない。 | 秘密情報試験 |
| `REQ-SEC-002` | 本文生成へ未公開の真相、作者用Thread回答、Ending内部設計、非POV人物の非公開内面を渡してはならない。 | Writer秘密除外試験 |
| `REQ-SEC-003` | 継続性更新へ将来の未公開計画や作者用の秘密情報を渡してはならない。 | Continuity秘密除外試験 |
| `REQ-SEC-004` | Brief、本文、Review内の命令風文字列を、Stageや出力形式を変更する命令として扱ってはならない。 | Prompt injection試験 |
| `REQ-SEC-005` | Publicationへprivate Review、private Completion notes、Context、provider metadataを含めてはならない。 | Publication privacy試験 |
| `REQ-SEC-006` | 全workspace pathはworkspace root内に限定し、absolute path、`..` traversal、symlink escapeを拒否しなければならない。 | Path security試験 |
| `REQ-SEC-007` | Storycraftはprovider call以外のWeb検索、外部file retrieval、別会話memoryを自動利用してはならない。 | 外部取得禁止試験 |
| `REQ-SEC-008` | Expected errorは秘密情報や不要なtracebackを利用者へ表示してはならない。 | error redaction試験 |

# Part 6: 非機能・Release要件

## 10. 非機能・Release要件

| 要件ID | 要件 | 主な確認方法 |
|---|---|---|
| `REQ-NFR-001` | Workspaceは通常のfile browserとeditorで理解できるJSON、Markdown、directory名を使用しなければならない。 | 可読性レビュー |
| `REQ-NFR-002` | JSONはUTF-8、NFC、LF、有限数、未知field拒否の共通規則へ従わなければならない。 | 共通Schema試験 |
| `REQ-NFR-003` | 採用済み本文とPublicationの組み立ては、同じ入力から決定的に再生成できなければならない。 | 再現性試験 |
| `REQ-NFR-004` | ContextはStageに必要な情報だけを読み込み、シリーズ全体の巨大なmutable objectを前提としてはならない。 | Context性能試験 |
| `REQ-NFR-005` | 全provider callは最終requestのtoken量をCall開始前に確認しなければならない。 | token試験 |
| `REQ-NFR-006` | Mandatory testはreal network、real credential、real waitingを必要としてはならない。 | test環境試験 |
| `REQ-NFR-007` | PromptとSchemaはinstalled package内の一つのasset rootから読み込み、source-tree fallbackを使用してはならない。 | wheel試験 |
| `REQ-NFR-008` | Release前に正常系、Review／Revision、通信失敗、形式不正、Scene Crash、Publication Crash、秘密除外、incomplete、lock競合を自動試験しなければならない。 | release suite |

# Part 7: 管理

## 11. 要件数

| 分類 | 範囲 | 件数 |
|---|---|---:|
| `FR` | `REQ-FR-001`〜`REQ-FR-032` | 32 |
| `DATA` | `REQ-DATA-001`〜`REQ-DATA-012` | 12 |
| `OPS` | `REQ-OPS-001`〜`REQ-OPS-012` | 12 |
| `REC` | `REQ-REC-001`〜`REQ-REC-010` | 10 |
| `SEC` | `REQ-SEC-001`〜`REQ-SEC-008` | 8 |
| `NFR` | `REQ-NFR-001`〜`REQ-NFR-008` | 8 |
| **合計** |  | **82** |

## 12. 実装状況との分離

この文書へ実装済み／未実装の状態を書かない。

実装状況は`IMPLEMENTATION_STATUS.md`へ記録する。

次だけでは要件を満たしたことにならない。

```text
設計書に記載した
似たfieldがある
legacy testが通る
happy pathだけ動く
手動確認で問題がなかった
```

要件を満たしたと判断するには、production codeと対応する自動試験が必要である。

## 13. 変更管理

要件を変更する場合:

1. 利用者向け意味が変わる場合は`SPECIFICATION.md`も修正する。
2. 最上位原則と矛盾しないことを確認する。
3. 対応する設計文書を修正する。
4. 自動試験を修正する。
5. `IMPLEMENTATION_STATUS.md`を更新する。
6. READMEの説明を最後に更新する。

既存実装に合わせて必須要件を弱めてはならない。

## 14. この文書の受入条件

この文書は次を満たさなければならない。

```text
要件IDが一意
各分類に欠番がない
合計82件
すべて日本語で理解できる
Hash、Manifest、Gateを不要な必須要件として再導入していない
単一writer・ローカルfilesystem前提と一致する
実装状況を誇張していない
最上位設計原則へのlinkが解決する
```

---

## 15. 最終原則

要件の追加・変更時は、次を確認する。

```text
単一writerでも必要か
ローカルfilesystemでも必要か
run-state.jsonで代替できないか
immutable directoryで代替できないか
atomic renameで代替できないか
利用者価値を説明できるか
```

説明できない要件は追加しない。
