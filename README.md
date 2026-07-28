# Storycraft

Storycraft は、Brief または Keywords から日本語の長編シリーズを段階的に設計・執筆し、継続性を管理して Markdown 原稿を出力するローカル実行型CLIです。

## V1

- 単一利用者・単一 writer・単一ローカル workspace
- 日本語、4〜10巻
- Brief／Keywords、計画、Scene本文、継続性、巻Handoff、完結判定、Publication
- `run`、`resume`、`step`、`status`、`validate`
- LLM による創作・意味的評価と、コードによる検証・保存・復旧の分離

複数 writer の同時編集、分散実行、remote workspace、自動Web検索、Publication時の本文再生成は V1 の対象外です。

## 使い方

CLI と利用可能な option は、実行環境で確認します。

```bash
storycraft --help
storycraft run --help
storycraft resume --help
storycraft step --help
```

新規作品は Brief または Keywords の一方から開始します。厳密な入力形式と制作・品質・復旧・公開の契約は[仕様書](docs/SPECIFICATION.md)を参照してください。

## 主要原則

- 確定済みの Generation、Scene、Plan、Handoff、Completion、Publication は不変。
- 本文 Evidence のない物語上の事実や現在状態を作らない。
- LLM Candidate は、コード検証、独立 Review、必要時 Revision、再 Review を経て採用する。
- 要約は根拠参照付きの LLM 意味的要約とし、機械的な抜粋・切り詰めを使わない。
- Recovery と公開は決定的に行い、確定済み成果物を上書きしない。
- Budget は新しい LLM Call を止めるが、検証、確定、Recovery、安全停止を妨げない。

## 文書

| 文書 | 内容 |
|---|---|
| [仕様書](docs/SPECIFICATION.md) | V1 の唯一の仕様正本 |
| [実装状況](docs/IMPLEMENTATION_STATUS.md) | 時点付きの実装・検証記録。仕様正本ではない |
| [fixture の説明](tests/fixtures/README.md) | 自動試験用 fixture の構成 |

## 開発者向け検証

```bash
python -m unittest discover -s tests -p "test_*.py"
bash scripts/wheel_smoke.sh
```

> Storycraft は、物語の意味生成を LLM に任せながら、状態、保存、継続性、再開、完結判定、公開を明示的な契約と決定的なコードで管理します。
