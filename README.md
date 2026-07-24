# Storycraft

Storycraftは、BriefまたはKeywordsから日本語の長編シリーズを段階的に設計・執筆し、継続性を管理して読者向け原稿へまとめるローカル実行型CLIです。

Version 1は、単一利用者・単一writer・ローカルfilesystemを前提とします。現在はalpha開発中であり、V1契約に対する実装状況は[`docs/product/IMPLEMENTATION_STATUS.md`](docs/product/IMPLEMENTATION_STATUS.md)を正本とします。

## V1の制作フロー

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
Scene Commit
↓
Volume Handoff
↓
Completion
↓
Publication
```

主な目標:

- 4〜10巻の日本語長編シリーズ
- ChapterとSceneを一対象ずつ計画
- Sceneごとの本文生成、Review、Revision
- 本文Evidenceに基づく現在状態と読者開示の更新
- 確定済み成果物を上書きしない保存
- Crash後の決定的な再開
- 採用済みSceneだけからPublicationを構築
- operationごとのProvider／model、timeout、Budget、Audit

## V1の範囲

対応対象:

```text
日本語
単一workspace
単一writer
ローカルfilesystem
外部LLM Provider
Brief入力またはKeywords入力
run / resume / step
Markdown Publication
```

対象外:

```text
複数writerの同時編集
分散実行
remote workspace
自動Web検索
別会話memoryの自動取得
Gitを実行状態の正本にする運用
Publication時の物語本文再生成
```

## 現在の実装状態

V1の個別Stage Serviceは、入力から`scene_continuity`まで段階的に実装されています。一方、公開CLIはまだV1 Workflowへ完全統合されておらず、`scene_commit`、`volume_handoff`、`completion`、`publication`、V1 Crash Recoveryは未実装です。

そのため、READMEに記載したV1フロー全体を現時点のCLIで完走できるとはみなしません。正確な実装済み範囲、試験状況、次の作業順は次を参照してください。

[`docs/product/IMPLEMENTATION_STATUS.md`](docs/product/IMPLEMENTATION_STATUS.md)

## 開発環境

必要条件:

```text
Python 3.11以上
ローカルfilesystem
OpenAI互換APIを利用する場合は対応するendpointとCredential
```

開発用install例:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

CLIの実装済みoptionはhelpで確認します。

```bash
storycraft --help
storycraft run --help
storycraft resume --help
storycraft step --help
```

## 入力

新規作品はBriefまたはKeywordsの正確に一方から開始します。厳密なfieldはproduction Schemaを正本とします。

Brief例:

```json
{
  "title": "潮騒の記憶",
  "genre": ["ミステリ", "ヒューマンドラマ"],
  "premise": "記憶の一部を失った主人公が、海辺の町で姉と灯台火災の真相を追う。",
  "required_elements": ["海辺の町", "失われた記憶", "姉妹", "灯台"],
  "avoid": ["露悪的な残虐描写"],
  "ending_preference": "救いのある結末",
  "volume_count": 4,
  "language": "ja"
}
```

Keywords例:

```json
{
  "keywords": ["海辺の町", "失われた記憶", "姉妹", "静かな恐怖", "灯台"],
  "avoid": ["露悪的な残虐描写"],
  "ending_preference": "救いのある結末",
  "volume_hint": 4,
  "language": "ja"
}
```

## 設計原則

```text
現在のrun位置には一つのAuthorityだけを持つ
情報種別ごとにState Authorityを一意にする
確定済みGeneration、Scene、Publicationはimmutable
変更可能fileは完全な内容でatomic replacementする
複数file成果物はstagingからdirectory単位で確定する
Planと作中で確定した事実を分離する
本文EvidenceなしにStateを更新しない
Character KnowledgeとReader Knowledgeを分離する
通常SceneからCanonを変更しない
Reviewは候補を書き換えず、Revisionは完全置換を返す
Recoveryとcode-only operationでProviderを初期化しない
Publicationで新しい物語本文を生成しない
Hash、Manifest、Gateを根拠なくAuthorityへ追加しない
```

## 文書

文書入口:

[`docs/README.md`](docs/README.md)

| 文書 | 正本とする内容 |
|---|---|
| [`docs/product/SPECIFICATION.md`](docs/product/SPECIFICATION.md) | 利用者向け製品仕様 |
| [`docs/product/REQUIREMENTS.md`](docs/product/REQUIREMENTS.md) | 76件の検証可能要件 |
| [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) | 全体構造と設計原則 |
| [`docs/design/DATA_MODEL.md`](docs/design/DATA_MODEL.md) | StoryデータとAuthority |
| [`docs/design/WORKSPACE_AND_RECOVERY.md`](docs/design/WORKSPACE_AND_RECOVERY.md) | 保存、確定、Crash Recovery |
| [`docs/design/PIPELINE.md`](docs/design/PIPELINE.md) | Stage、Loop、遷移 |
| [`docs/design/LLM_INTEGRATION.md`](docs/design/LLM_INTEGRATION.md) | Context、Prompt、Provider連携 |
| [`docs/testing/ACCEPTANCE.md`](docs/testing/ACCEPTANCE.md) | Release受入試験 |
| [`docs/product/IMPLEMENTATION_STATUS.md`](docs/product/IMPLEMENTATION_STATUS.md) | 現在の実装・試験状況 |

## Test

標準test command:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Wheel smoke:

```bash
bash scripts/wheel_smoke.sh
```

Release判定は[`docs/testing/ACCEPTANCE.md`](docs/testing/ACCEPTANCE.md)の必須suiteに従います。実network、実Credential、長い実時間待機を必須試験へ持ち込みません。

## 文書・実装の変更順

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

> Storycraftは、物語の意味生成をLLMへ任せながら、現在状態、保存、継続性、再開、完結判定、Publicationを明示的な契約と決定的なコードで管理します。
