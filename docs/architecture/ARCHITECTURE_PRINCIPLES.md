# Storycraft 設計原則

この文書は、Storycraft の仕様・設計・実装・試験が従う最上位の設計原則を定める。

以後の文書や実装がこの原則と矛盾する場合は、個別文書を修正する。既存実装や既存文書に合わせて、この原則を弱めてはならない。

---

## 1. 対象

Storycraft は、単一利用者がローカル環境で使う、日本語長編シリーズ生成CLIである。

前提:

```text
一つのworkspace
一つの書き込みprocess
ローカルfilesystem
一つの実行状態
人間が読める成果物
外部の監査主体なし
悪意ある改ざんへの耐性は対象外
```

対象外:

```text
複数writerによる同時編集
分散worker
remote database
object storage
network filesystem
外部署名
改ざん証明
第三者監査
高可用性cluster
```

---

## 2. 最優先事項

設計判断は、次の順で優先する。

```text
1. 実装しやすさ
2. Crash後の理解しやすさ
3. workspaceの人間可読性
4. データ喪失の防止
5. 生成品質
6. 将来拡張性
```

将来の可能性だけを理由に、現在不要な複雑性を導入してはならない。

---

## 3. 単純さを優先する

Storycraft は、必要性を説明できない仕組みを持たない。

次を導入する場合は、文書で明確に説明しなければならない。

```text
何を防ぐのか
失敗時に何をするのか
より単純な方法では代替できないのか
利用者にどのような価値があるのか
```

説明できない場合、その仕組みは削除する。

---

# Part I: 保存と状態

## 4. 単一writer

一つのworkspaceへ書き込めるprocessは常に一つだけとする。

実装は排他lockを取得し、取得できない場合は明確に失敗する。

Lockの目的は同時書き込みの防止であり、分散合意やlock recovery protocolではない。

---

## 5. ローカルfilesystem

Version 1はローカルfilesystemだけを対象とする。

設計は次を前提にしてよい。

```text
同一machine
同一workspace root
通常のatomic file replacement
通常のdirectory rename
一つのprocessが書き込む
```

Network filesystemやremote storageの互換性は保証しない。

---

## 6. 一つの実行状態ファイル

現在の実行位置を表す正本は、一つの実行状態ファイルとする。

推奨path:

```text
runtime/run-state.json
```

実行状態は少なくとも次を持つ。

```text
run_id
status
current_stage
current_target
current_generation
current_publication
active_candidate
active_scene
stop_reason
updated_at
```

現在位置を複数のpointerやManifestへ重複保存しない。

---

## 7. 完全ファイル更新

変更可能なJSONは、部分更新せず完全ファイルとして書き換える。

処理:

```text
一時ファイルへ完全な内容を書く
読み直して検証する
atomic replaceする
```

JSON Patch、追記による状態更新、file内のin-place editを使用しない。

---

## 8. 確定済みdirectoryは上書きしない

次のような確定済み成果物directoryはimmutableとする。

```text
generations/000012/
scenes/v01-c001-s002/
publications/pub-000001/
```

同じIDのdirectoryを上書きしてはならない。

修正が必要な場合は、新しいIDまたは新しいversionを作る。

---

## 9. 一時directoryから確定する

複数ファイルで構成される成果物は、一時directoryで完成させてから最終pathへrenameする。

例:

```text
runtime/staging/scene-v01-c001-s002/
→
scenes/v01-c001-s002/
```

最終directoryが存在することを、確定完了の主要な証拠とする。

---

## 10. Manifest graphを作らない

Version 1では、複数Manifestが互いを参照するgraphを作らない。

原則として不要:

```text
Candidate Manifest
Checkpoint Manifest
Commit Manifest
Generation Manifest
Publication Manifest
Publication Gate
Validation Manifest
```

必要な識別情報は、成果物directory内の単純な`metadata.json`または`commit.json`へまとめる。

---

## 11. Hashは原則使用しない

SHA-256などのhashは、原則として保存契約へ含めない。

削除対象の例:

```text
本文hash
Context hash
Candidate hash
Review hash
計画hash
Canon root hash
State root hash
開始前確認hash
Publication集合hash
```

Hashを導入できるのは、次の条件をすべて満たす場合だけである。

```text
具体的な用途がある
検出後の動作が決まっている
IDとimmutable directoryでは代替できない
設計を大きく複雑化しない
```

単なる「改ざん検知」は、Version 1の導入理由として認めない。

---

## 12. 外部監査を想定しない

Version 1は、第三者による監査、署名検証、証拠保全を目的としない。

Auditは開発・障害調査・再開判断のために保存する。

AuditをStoryの正本や採用authorityとして使わない。

---

# Part II: 生成物と採用

## 13. Generation

Generationは、一つの採用済みStory状態を表すdirectoryである。

推奨構成:

```text
generations/000012/
  canon.json
  state.json
  evidence.json
  commit.json
```

`commit.json`は少なくとも次を持つ。

```text
generation_id
parent_generation
commit_type
source_artifact
created_at
```

Generationの採用状態は`run-state.json.current_generation`で表す。

---

## 14. HEAD pointerを正本にしない

`canon/HEAD`のようなpointerを設ける場合、それは人間向けの補助表示とする。

正本は`run-state.json.current_generation`である。

Pointerと状態ファイルを二つの独立authorityにしてはならない。

Version 1ではpointer自体を削除してよい。

---

## 15. Scene成果物

採用済みSceneは一つのdirectoryへまとめる。

推奨構成:

```text
scenes/v01-c001-s002/
  scene-card.json
  prose.md
  continuity.json
  commit.json
```

本文、継続性更新、根拠情報は同じScene directoryに属する。

---

## 16. Publication

Publicationはreader-facing成果物をまとめたimmutable directoryである。

推奨構成:

```text
publications/pub-000001/
  series.md
  v01.md
  v02.md
  metadata.json
  completion.json
```

作成手順:

```text
一時directoryへ全ファイルを書く
必要最低限の検証を行う
最終directoryへrenameする
run-state.json.current_publicationを更新する
run statusをcompletedにする
```

---

## 17. CURRENT pointerを正本にしない

`output/CURRENT`を設ける場合、それは補助表示とする。

正本は`run-state.json.current_publication`である。

Version 1ではpointerを削除してよい。

---

## 18. Publication Gateを作らない

外部監査主体が存在しないため、独立したPublication Gateは作らない。

Publication採用前に行う検証は、Publication作成処理の内部手順とする。

最低限確認する内容:

```text
必須ファイルが存在する
Markdownが空でない
JSONが読み込める
Volume／Chapter／Scene順がplanと一致する
Completionが公開可能な状態である
```

---

# Part III: 実行工程

## 19. Stageは意味のある単位に限定する

Stageは、利用者、生成モデル、再開処理にとって意味のある工程だけにする。

次のような内部処理は、原則として独立Stageにしない。

```text
Schema確認
ID割当
file freeze
Manifest作成
Validation作成
directory rename
状態ファイル更新
```

これらは一つのStage内の実装手順とする。

---

## 20. 推奨Stage分類

Version 1の外部的なStageは、概ね次を基準とする。

```text
入力
初期設計
シリーズ計画
巻計画
章計画
Scene Card
本文
継続性更新
Scene確定
巻Handoff
完結判定
Publication
```

ReviewとRevisionは共通処理として扱ってよい。

最終Stage数は、実装可能性と再開単位を見て決める。

Stage数を多くすること自体を品質とみなさない。

---

## 21. Scene中の基準状態を固定する

一つのSceneについて、次の処理が完了するまで基準Generationを変えない。

```text
Scene Card
本文
継続性更新
Scene確定
```

途中で基準Generationが変わった場合は、古いScene処理を再利用せずやり直す。

---

## 22. ReviewとRevisionを分離する

生成候補は、必要に応じてReviewする。

Reviewは問題点を返し、候補自体を書き換えない。

Revisionは候補全体の置換版を返す。

禁止:

```text
Reviewが採用を決める
Reviewが次Stageを決める
Revisionが差分だけ返す
機械的に壊れた候補を意味的Issueとして採用する
```

---

## 23. Retryを分類する

次を別々に扱う。

```text
通信失敗
応答形式不正
意味的Revision
```

それぞれに上限を設ける。

無制限に成功まで繰り返してはならない。

---

# Part IV: Contextと秘密情報

## 24. Contextは一時的な入力である

Contextは、生成モデルへ渡すために組み立てる一時的な入力である。

原則として、hash名ファイルや恒久的な参照graphを作らない。

保存する場合は、Candidate directoryまたはAudit内に単純な`context.json`として置く。

---

## 25. Writerへ秘密情報を渡さない

本文生成へは、必要なdramatic情報だけを渡す。

除外する情報:

```text
未公開の真相
Threadの作者用回答
Endingの内部設計
非POV人物の非公開内面
将来Sceneの詳細
継続性更新の内部処理
```

この境界はhashやManifestより優先して守る。

---

## 26. Contextは人間が読めること

Contextや保存成果物は、開発者が通常のeditorで読めるJSON／Markdownにする。

不要なwrapper、暗号的識別子、重複metadataを増やさない。

---

# Part V: Evidenceと継続性

## 27. Evidenceの目的

Evidenceの目的は、継続性更新の根拠となる本文箇所を人間が確認できるようにすることである。

改ざん証明や法的証拠を目的としない。

---

## 28. Evidenceの最小形式

推奨形式:

```json
{
  "scene_id": "v01-c001-s002",
  "quote": "澪は灯台の鍵を凪へ渡した。",
  "target": "character:澪.inventory",
  "change": "鍵を所持していない"
}
```

必要な場合だけ次を追加する。

```text
出現順
文字offset
前後の短い文脈
```

Quote hashやprose hashは不要である。

---

## 29. 本文を上書きしない

採用済みScene本文を上書きしないことで、Evidenceと本文の関係を維持する。

本文を修正する場合は、新しいScene versionまたは新しいGenerationとして扱う。

---

# Part VI: 完結判定

## 30. 完結前確認

完結判定の前に、コードで次を確認する。

```text
全Volumeが完了している
全計画Sceneが確定している
Required Threadが存在する
Ending条件が存在する
未完了のScene処理がない
```

この確認結果を独立fileとして保存する必要はない。

必要なら完結結果へ含める。

---

## 31. 完結判定

完結判定は、最終Story状態と計画をもとに一度評価する。

結果:

```text
complete
complete_with_issues
incomplete
```

構造不正な応答だけ再試行してよい。

意味的に`incomplete`であることを理由に、`complete`になるまで再試行してはならない。

---

## 32. 完結結果

推奨path:

```text
completion/result.json
```

推奨内容:

```text
status
summary
thread_checks
ending_checks
issues
created_at
```

開始前確認、Context hash、attempt hash、accepted audit graphは持たない。

---

# Part VII: Crashと再開

## 33. Recovery分類を単純にする

Crash後の処理は、原則として次の三つに分類する。

```text
再開
再生成
人間対応
```

必要に応じて、不完全な一時directoryを`runtime/orphans/`へ移動してよい。

---

## 34. 再開

次の場合は再開する。

```text
run-state.jsonが読める
現在Stageが分かる
必要な確定済み入力が存在する
途中成果物が完全である
```

---

## 35. 再生成

次の場合は再生成する。

```text
一時directoryが不完全
候補fileが不完全
Reviewだけ存在する
Contextだけ存在する
Stage出力が読めない
```

不完全成果物を推測して採用しない。

---

## 36. 人間対応

次の場合は自動修復しない。

```text
run-state.jsonが読めない
run-stateが指す確定済みdirectoryがない
同じIDの最終directoryが競合している
counterが既存IDより小さい
完結判定がincomplete
```

---

## 37. Rename後のCrash

最終directoryへのrename後、実行状態更新前にCrashした場合は、次を確認する。

```text
対象Stageがそのdirectoryを作る予定だった
同じIDの候補が一つだけ存在する
directory内の必須ファイルが読める
```

条件を満たす場合は`run-state.json`を更新して再開する。

複雑なGateやManifest graphは使用しない。

---

# Part VIII: IDとAudit

## 38. IDは単調増加させる

次のIDは、必要に応じて`runtime/counters.json`で管理する。

```text
Generation ID
Publication ID
永続Story record ID
LLM Call ID
```

IDは使用前にcounterへ保存する。

失敗により番号が欠けても再利用しない。

---

## 39. Auditは調査用である

Auditは、開発・障害調査・利用量確認のために保存する。

代表的な内容:

```text
Stage
target
provider
model
request時刻
response時刻
usage
result
error
```

AuditからCandidateやStory状態を復元しない。

---

## 40. Credentialを保存しない

Credential値、Authorization header、cookie、secret tokenを次へ保存してはならない。

```text
設定
Context
Prompt
Candidate
Audit
Log
Publication
Error message
```

---

# Part IX: 文書と実装

## 41. 日本語を基本言語とする

仕様書、設計書、README、例、コメントは日本語を基本とする。

次は英語表記を許可する。

```text
Python識別子
CLI command
path
JSON field
Stage ID
enum
外部library／provider名
```

不必要に英語用語を増やさない。

---

## 42. 人間が追えるworkspace

Workspaceは、特殊toolがなくても通常のfile browserとeditorで理解できなければならない。

設計は、次を一目で確認できることを目指す。

```text
現在どこまで進んでいるか
最新の採用済みGeneration
各Sceneの本文
現在のStory State
完結判定
最新Publication
```

---

## 43. Testはproductionと同じ処理を使う

Test専用の別serializer、別path規則、別recovery規則を作らない。

ただし、fake clock、fake provider、temporary filesystemなどのdependency injectionは使用する。

---

## 44. 必要な試験だけを持つ

試験数を品質指標にしない。

最低限、次を検証する。

```text
正常な全体実行
Review／Revision
通信失敗
応答形式不正
Scene途中Crash
Scene確定後Crash
Publication rename後Crash
秘密情報の除外
完結判定incomplete
lock競合
```

Manifest片側、hash mismatch、署名不整合など、削除した機能の試験は削除する。

---

## 45. 将来拡張

将来、複数writer、remote storage、外部監査が必要になった場合は、新しいmajor versionの設計課題として扱う。

Version 1へ先回りして組み込まない。

---

# Part X: 設計判断チェックリスト

## 46. 新しい仕組みを追加する前の確認

次の質問すべてに答える。

```text
利用者のどの問題を解決するか
単一writerでも必要か
ローカルfilesystemでも必要か
実行状態ファイルでは代替できないか
immutable directoryでは代替できないか
atomic renameでは代替できないか
障害時の処理が明確か
文書量と実装量に見合うか
```

一つでも説明できない場合は、追加を見送る。

---

## 47. Hash導入チェック

Hashを追加する場合は、次を文書へ記載する。

```text
対象データ
検出する具体的な問題
検出時の処理
ID／path／immutable directoryでは不足する理由
保存期間
利用する処理
```

「念のため」「改ざん検知のため」だけでは導入しない。

---

## 48. Authority追加チェック

新しいpointer、Manifest、Gate、indexを追加する場合は、次を明確にする。

```text
正本か補助情報か
既存の正本と矛盾した場合どちらを優先するか
Crash後にどう再構築するか
削除できない理由
```

複数の正本を作らない。

---

## 49. 最終原則

Storycraft Version 1は、次の原則へ従う。

```text
Single Writer
Local Filesystem
One Run State
Immutable Final Directories
Atomic Replacement
Atomic Rename
Readable Workspace
Minimal Metadata
Hash Only with a Concrete Use
No Manifest Graph
No External Gate
Simple Recovery
Simple Before Clever
```

任意の設計判断がこの原則より複雑な仕組みを必要とする場合、その必要性を具体的に証明しなければならない。
