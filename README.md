# Storycraft

briefまたはkeywordsを起点に、個人出版向けの日本語小説シリーズを最後まで書き切るCLIです。

次期仕様の大きな流れは、**シリーズ初期設計 → 初期bundle採用 → 巻・章・場面の反復 → 本文・差分・Canon更新を含む場面採用 → 巻handoff → 完結監査 → Markdown出力**です。後続巻は初期Canonではなく、更新済みの現在Canon・現在Stateを参照します。レビューは品質改善に利用しますが、完結監査はrevisionではなく独立した監査attemptです。

> 現行実装との差分は[実装状況](docs/product/IMPLEMENTATION_STATUS.md)を参照してください。

## 文書

| 文書 | 内容 |
|---|---|
| [要件](docs/product/REQUIREMENTS.md) | 利用者向けの不変の約束 |
| [製品仕様](docs/product/SPECIFICATION.md) | 次期製品契約の正本 |
| [実装状況](docs/product/IMPLEMENTATION_STATUS.md) | 現行実装との差分 |
| [エンジン設計](docs/design/series_engine_design.md) | 採用、保存、ID、検証の設計 |
| [生成フロー](docs/design/series_engine_flow.md) | LLM呼び出しと反復の順番 |
| [template設計](docs/design/prompt_template_design.md) | 将来のtemplate責務 |

## 現行CLI

```bash
PYTHONPATH=src .venv/bin/python -m storycraft.cli --help
storycraft run --out ./my-series --brief ./brief.yaml
storycraft run --out ./my-series --keywords '海洋幻想譚'
storycraft resume --out ./my-series
```

現行CLI・template・Schemaは次期仕様に未対応の部分があるため、詳細は実装状況を参照してください。
