# Storycraft

Storycraftは、BriefまたはKeywordsから、日本語の長編シリーズを段階的に設計・執筆・確認し、読者向け原稿へまとめるローカル実行型の制作支援ツールです。

Version 1は、単一利用者・単一writer・ローカルfilesystemを前提とします。

---

## 1. できること

Storycraftは、次の制作工程を一つのworkflowとして扱います。

```text
BriefまたはKeywords
↓
Initial Design
↓
Series Plan
↓
Volume Plan
↓
Chapter Plan
↓
Scene Plan
↓
Scene Card
↓
Scene本文
↓
継続性更新
↓
Volume Handoff
↓
Completion
↓
Publication
```

主な特徴:

- 4〜10巻の日本語長編シリーズ
- BriefまたはKeywordsから開始
- Series／Volume／Chapter／Scene単位の計画
- Sceneごとの本文生成
- ReviewとRevision
- 本文根拠に基づく継続性更新
- Crash後の再開
- 完結判定
- 読者向けPublicationの決定的な組立
- ローカルworkspaceでの保存
- Providerごとのmodel設定
- Call数、token、費用、時間のBudget制御

---

## 2. 対象

Storycraft Version 1は、次の利用を想定しています。

```text
個人で長編シリーズを作りたい
巻をまたぐ人物・関係・謎を追跡したい
Sceneごとに生成結果を確認したい
途中停止後に安全に再開したい
内部資料と読者向け原稿を分離したい
```

---

## 3. Version 1の範囲

### 対応

```text
日本語
4〜10巻
単一workspace
単一writer
ローカルfilesystem
外部LLM Provider
Brief入力
Keywords入力
run
resume
step
Markdown Publication
```

### 対象外

```text
複数writerの同時編集
分散実行
remote workspace
共同編集
自動Web検索
別会話memoryの自動取得
Gitを正本にする運用
Publication時の本文再生成
```

---

## 4. 入力

新規作品は、次のどちらか一方から開始します。

### Brief

作品の主要条件をまとめた入力です。

例:

```json
{
  "title": "潮騒の記憶",
  "genre": [
    "ミステリ",
    "ヒューマンドラマ"
  ],
  "premise": "記憶の一部を失った主人公が、海辺の町で姉と灯台火災の真相を追う。",
  "required_elements": [
    "海辺の町",
    "失われた記憶",
    "姉妹",
    "灯台"
  ],
  "avoid": [
    "露悪的な残虐描写"
  ],
  "ending_preference": "救いのある結末",
  "volume_count": 4,
  "language": "ja"
}
```

厳密なfieldとSchemaはproduction assetで定義します。

---

### Keywords

短い条件からBriefを生成する入力です。

例:

```json
{
  "keywords": [
    "海辺の町",
    "失われた記憶",
    "姉妹",
    "静かな恐怖",
    "灯台"
  ],
  "avoid": [
    "露悪的な残虐描写"
  ],
  "ending_preference": "救いのある結末",
  "volume_hint": 4,
  "language": "ja"
}
```

Keywordsから生成したBriefは、必須Keyword、avoid、Ending希望、巻数希望を保持します。

---

## 5. 基本command

Storycraftの公開CLIは、次の三つを中心とします。

```text
run
resume
step
```

### `run`

新しいworkspaceで作品制作を開始します。

既存workspaceを確認なしで上書きしません。

---

### `resume`

途中停止したworkspaceを再開します。

元のBriefまたはKeywordsを再入力する必要はありません。

---

### `step`

現在の意味的Stageを一つだけ完了して終了します。

Reviewと必要なRevisionは、同じStage内で処理します。

---

## 6. CLIの確認

実際に利用可能なoptionは、installed packageのhelpで確認します。

```bash
storycraft --help
storycraft run --help
storycraft resume --help
storycraft step --help
```

Package名、entry point、install commandは、repositoryのpackage metadataと実装状況を確認して更新してください。

現在の確認状況は次を参照します。

[`docs/product/IMPLEMENTATION_STATUS.md`](docs/product/IMPLEMENTATION_STATUS.md)

---

## 7. 制作flow

### Initial Design

作品全体の作者用設計を作ります。

```text
Concept
Characters
Relationships
World
Locations
World Rules
Knowledge
Threads
Ending
Long-term Arcs
```

個別Candidateをそのまま並べるのではなく、相互矛盾を解消した統合版を採用します。

---

### Plan

将来の執筆方針を段階的に作ります。

```text
Series Plan
Volume Plan
Chapter Plan
Scene Plan
```

Planは予定であり、本文に書かれた事実ではありません。

---

### Scene Card

一つのSceneについて、本文生成に必要な条件を定めます。

```text
POV
参加人物
場所
目的
開始状況
必須beat
Conflict
開示制約
許可する継続性更新
終了時の変化
```

---

### Scene本文

Scene Cardと現在のStory状態に基づき、日本語散文を生成します。

本文には次を含めません。

```text
JSON
内部識別子
Review結果
Prompt
Provider情報
実装用metadata
```

---

### ReviewとRevision

ReviewはCandidateの問題点を返します。

Review自身がCandidateを書き換えることはありません。

Revisionは、修正差分ではなく完全な置換Candidateを返します。

---

### 継続性

継続性更新は、確定対象の本文に実際に書かれた変化だけを反映します。

更新例:

```text
人物の現在位置
人物が知った事実
Relationshipの変化
Threadの進行
所有物
負傷
時間経過
Location状態
```

各更新は、本文中のEvidenceと関連付けます。

Planに書かれているだけの変更は採用しません。

---

### Volume Handoff

各巻の終了時に、実際の巻末状態を次巻へ引き渡します。

```text
主要人物の状態
Relationshipの状態
解決済みThread
未解決Thread
新しい制約
Endingへの進捗
次巻で無視できない結果
```

---

### Completion

全巻と全Sceneの完了後、シリーズがPublication可能かを評価します。

結果:

```text
complete
complete_with_issues
incomplete
```

`incomplete`は正当な結果です。

`complete`になるまで自動的に再試行しません。

---

### Publication

Publicationは、採用済みScene本文を計画順に組み立てます。

Publication作成時に新しい物語本文を生成しません。

含めない情報:

```text
Review
Revision指示
作者用秘密
Provider情報
Usage
内部Context
Recovery情報
```

---

## 8. 再開とCrash Recovery

Storycraftは、途中状態を次の三分類で扱います。

```text
resume:
  確定済み状態から続行

regenerate:
  未採用の途中作業を再生成

manual:
  自動判断せず人間確認
```

不正な現在状態を推測で修復したり、確定済み成果物を黙って削除したりしません。

---

## 9. Workspace

一つのworkspaceは、一つのシリーズを表します。

Workspaceには次が含まれます。

```text
入力
Initial Design
Plan
Scene
Generation
Handoff
Completion
Publication
実行状態
Call記録
```

確定済みのScene、Generation、Publicationは上書きしません。

---

## 10. Providerとmodel

処理ごとにProviderまたはmodelを設定できます。

例:

```text
Scene本文:
  prose向けmodel

Review:
  review向けmodel

継続性:
  structured output向けmodel

Completion:
  reasoning向けmodel
```

Credentialはworkspaceへ保存しません。

---

## 11. Budget

新しいProvider callを開始する前に、設定した利用上限を確認します。

```text
Call数
input token
output token
合計token
推定費用
経過時間
```

上限へ達した場合は、安全な状態で停止します。

---

## 12. 秘密情報

Storycraftは、作者用秘密と本文へ渡してよい情報を分離します。

Scene本文生成へ無条件に渡さない情報:

```text
未公開の真相
作者用Thread回答
Ending全体
将来巻の詳細
非POV人物の非公開内面
```

作品データ内の命令風文章も、実行命令として扱いません。

---

## 13. Output

正式Publicationは、読者向けMarkdownとして構成します。

例:

```text
publications/
└── pub-000001/
    ├── series.md
    ├── v01.md
    ├── v02.md
    ├── metadata.json
    └── completion.json
```

具体的なworkspace構成は次を参照します。

[`docs/design/WORKSPACE_AND_RECOVERY.md`](docs/design/WORKSPACE_AND_RECOVERY.md)

---

## 14. Documentation

文書入口:

[`docs/README.md`](docs/README.md)

主な文書:

| 文書 | 内容 |
|---|---|
| [`docs/product/SPECIFICATION.md`](docs/product/SPECIFICATION.md) | 利用者向け製品仕様 |
| [`docs/product/REQUIREMENTS.md`](docs/product/REQUIREMENTS.md) | 検証可能な要件 |
| [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) | 全体アーキテクチャ |
| [`docs/design/DATA_MODEL.md`](docs/design/DATA_MODEL.md) | Storyデータ |
| [`docs/design/WORKSPACE_AND_RECOVERY.md`](docs/design/WORKSPACE_AND_RECOVERY.md) | 保存とRecovery |
| [`docs/design/PIPELINE.md`](docs/design/PIPELINE.md) | StageとLoop |
| [`docs/design/LLM_INTEGRATION.md`](docs/design/LLM_INTEGRATION.md) | LLM連携 |
| [`docs/testing/ACCEPTANCE.md`](docs/testing/ACCEPTANCE.md) | 受入試験 |
| [`docs/product/IMPLEMENTATION_STATUS.md`](docs/product/IMPLEMENTATION_STATUS.md) | 現在の実装状況 |

---

## 15. Test fixture

実際の試験入力は次へ置きます。

```text
tests/fixtures/
```

Fixtureには、Brief、Plan、Scene、Generation、Completion、Publication、Crash状態、Provider応答、秘密情報試験を含みます。

Markdown文書へ巨大なJSON exampleを複製しません。

---

## 16. 開発原則

```text
一つのwriter
一つの現在状態Authority
確定済み成果物はimmutable
変更可能fileは完全更新
複数file成果物はstagingから確定
Planと事実を分離
本文根拠なしにStateを更新しない
ReviewとRevisionを分離
Publicationで本文を再生成しない
Hash、Manifest、Gateを根拠なく追加しない
```

---

## 17. Current status

文書構成の簡素化と正本文書の再作成は進行中です。

Production code、新しい受入試験、package smoke、旧設計削除の確認状況は次を参照してください。

[`docs/product/IMPLEMENTATION_STATUS.md`](docs/product/IMPLEMENTATION_STATUS.md)

現時点では、実装確認の証拠が揃っていない項目を「実装済み」とは記載していません。

---

## 18. Repository移行

旧文書は、新しい正本文書へ内容と参照を移した後に削除します。

主な統合:

```text
Engine設計:
  ARCHITECTURE.md
  PIPELINE.md

Workspace・Recovery:
  WORKSPACE_AND_RECOVERY.md

Data contract:
  DATA_MODEL.md

Context・Prompt・Provider:
  LLM_INTEGRATION.md

Acceptance:
  docs/testing/ACCEPTANCE.md

Markdown example:
  tests/fixtures/
```

---

## 19. Contributing

変更時は、次の順序を基本とします。

```text
製品仕様
↓
要件
↓
アーキテクチャ
↓
対応する詳細設計
↓
受入試験
↓
production code
↓
自動試験
↓
実装状況
↓
README
```

詳細:

[`docs/README.md`](docs/README.md)

---

## 20. License

Licenseはrepositoryの正式なLicense fileを参照してください。

License fileが未配置の場合は、配布前に明示する必要があります。

---

## 21. 最終原則

> Storycraftは、物語の意味生成をLLMへ任せながら、現在状態、保存、継続性、再開、完結判定、Publicationを明示的な契約と決定的なコードで管理します。
