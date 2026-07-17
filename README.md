# Storycraft

利用者が手入力したbrief、または自由なkeywordsからLLMが生成したbriefを起点に、個人出版向けの日本語小説シリーズを最後まで書き切るCLIです。

Storycraftは、人物・関係・世界・時系列・主要項目のCanonを先に確定し、その既存IDを巻別の `volume_map` へ配分してから、章、場面カード、本文、継続性更新の順で進めます。保存済みの正本状態から中断再開でき、検証済みの巻別・全巻Markdownだけを公開します。

## 文書

| 文書 | 内容 |
|---|---|
| [要件](docs/product/REQUIREMENTS.md) | 製品として変えてはいけない約束 |
| [製品仕様](docs/product/SPECIFICATION.md) | 利用者から見える入出力・生成・再開・出力の契約 |
| [現行実装の位置付け](docs/product/IMPLEMENTATION_STATUS.md) | 現行実装の成熟度と仕様との関係 |
| [シリーズエンジン設計方針](docs/design/series_engine_design.md) | 正本状態、採用、停止、再開、永続化の設計契約 |
| [シリーズ生成フロー設計](docs/design/series_engine_flow.md) | 工程ごとの正本、LLM責務、変更権限 |
| [プロンプトテンプレートと出力契約](docs/design/prompt_template_design.md) | 実送信テンプレート、外部schema、決定的検証 |

## インストール

Python 3.11以上が必要です。

```bash
python -m pip install .
```

開発環境では、リポジトリ直下から次のように実行できます。

```bash
PYTHONPATH=src .venv/bin/python -m storycraft.cli --help
```

## 最短実行

初回briefは、人がYAML/JSONで渡すか、自由なkeywordsからLLMに生成させます。keywordsはジャンル、巻数、雰囲気、題材、人物像などを任意に混在できます。生成briefは内容を採点せず、手入力briefと同じ必須項目・型・範囲だけを検証します。

手入力briefの必須項目は `title`、`genre`、`protagonist`、`key_people`、`want`、`avoid`、`ending` です。

```yaml
# brief.yaml
title: 仮題
genre: 現代ファンタジー
protagonist: 主人公
key_people: 重要人物
want: 主人公に起きてほしいこと
avoid: 避けたい展開
ending: 最後にどう終えたいか
volumes: 4
```

```bash
# 手入力brief
storycraft run --out ./my-series --brief ./brief.yaml

# keywordsを複数指定してbriefをLLM生成
storycraft run --out ./my-series \
  --keywords '海洋幻想譚' \
  --keywords '4巻、静かな希望のある結末' \
  --keywords '霧の島と灯台'
```

`run` は、未保存の作業場所でbriefから出力まで連続実行します。keywords指定時は、最初の保存可能な単位としてbriefだけを生成・構造検証して採用します。実LLMの接続先・model・timeoutは設定YAMLまたは環境変数で指定できます。

## 操作

| コマンド | 用途 | 初回入力 |
|---|---|---|
| `storycraft run --out DIR (--brief FILE \| --keywords TEXT ...)` | 新規シリーズを連続実行 | `brief` または1件以上の `keywords` のどちらか一方が必須 |
| `storycraft resume --out DIR` | 保存済みシリーズの未完了単位を連続実行 | 不要 |
| `storycraft step --out DIR [--brief FILE \| --keywords TEXT ...]` | 次の保存可能な単位だけ実行 | 初回だけ、どちらか一方を指定 |

共通で `--config FILE` に設定YAMLを渡せます。`resume` は初回入力を受け付けず、保存済みbriefは置き換えません。完了済みシリーズへの `step` は出力を作り直さず、保存済みの完成結果を返します。

同じ `--out` への同時操作は拒否されます。別の実行が終了してから `resume` または `step` を実行してください。

## 作業場所と成果物

`--out ./my-series` の場合、作業場所には次が作られます。

```text
my-series/
  state.json        # 再開に使う正本状態
  raw/              # LLM要求・応答の監査記録
  output/
    volume-01.md    # 第1巻（無料導入巻）
    volume-02.md    # 第2巻以降（販売対象巻）
    ...
    series.md       # 全巻を順に連結した原稿
```

`state.json` は一時ファイルへの書込み、ファイル同期、原子的置換、directory同期の順で永続化します。出力もstagingで検証してから `output/` を置換します。本文の空白、計画済み場面の欠落、重複本文、未回収の主要項目、結末根拠の不足があれば完成出力は公開されません。

## 設定

設定YAMLは既定値を部分上書きします。

```yaml
llm:
  base_url: http://localhost:11434/v1
  model: your-model
  thinking: true
  stream: true
  first_event_timeout_seconds: 3600
  idle_timeout_seconds: 600
retry:
  max_attempts: 4
quality:
  max_improvement_passes: 1
```

以下の環境変数でもLLM接続を上書きできます。

| 環境変数 | 対応する設定 |
|---|---|
| `STORYCRAFT_LLM_BASE_URL` | `llm.base_url` |
| `STORYCRAFT_LLM_MODEL` | `llm.model` |
| `STORYCRAFT_LLM_IDLE_TIMEOUT` | `llm.idle_timeout_seconds` |
| `STORYCRAFT_LLM_FIRST_TIMEOUT` | `llm.first_event_timeout_seconds` |

## 開発時の検証

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m compileall -q src tests
git diff --check
bash scripts/wheel_smoke.sh
```

実LLMによる作品内容・販売原稿としての品質は、別途の実行監査が終わるまで主張しません。
