# Storycraft

Storycraft は、作品の依頼文またはキーワードから、日本語の長編シリーズを段階的に設計・執筆し、整合性を保った Markdown 形式の原稿を出力するローカル実行型のコマンドラインツールです。

## V1 の範囲

- 利用者は一人、執筆者は一人、作業場所は一つ
- 日本語で 4〜10 巻の作品を作る
- 依頼文またはキーワード、計画、場面本文、継続性、巻単位の公開用原稿を扱う
- 新規作業場所の初期化 `init`、実行 `run`、状態表示 `status`、検証 `validate` を使う
- 創作や意味の評価は大規模言語モデル（LLM）、形式・保存・復旧は決定的なコードが担当する

複数人の同時編集、分散実行、外部の作業場所、自動ウェブ検索、公開時の本文再生成は V1 の対象外です。

## 必要環境

- Python 3.14+
- Ollama（ローカル LLM サーバー、デフォルト `http://ws1.local:11434/v1`）
- 依存パッケージは `uv` で管理

## インストールと実行

```bash
# 依存インストール
uv sync

# ヘルプ表示
uv run python -m storycraft.cli --help
uv run python -m storycraft.cli init --help
uv run python -m storycraft.cli run --help
uv run python -m storycraft.cli status --help
uv run python -m storycraft.cli validate --help
```

## 基本的な使い方

### 1. 依頼文から始める場合

```bash
# 設定ファイル作成
cat > config.json <<'EOF'
{
  "llm": {
    "provider": "ollama",
    "base_url": "http://ws1.local:11434/v1",
    "model": "qwen3:35b-a3b",
    "first_event_timeout_seconds": 3600,
    "idle_timeout_seconds": 600
  },
  "quality": {
    "max_critique_passes": 1
  }
}
EOF

# 依頼文作成
cat > request.json <<'EOF'
{
  "title": "霧の街の図書館",
  "genre": "現代ファンタジー",
  "premise": "霧に包まれた街の古い図書館で、司書が消えた本の謎を追う",
  "required_elements": ["図書館", "霧", "消えた本", "司書"],
  "forbidden_elements": ["異世界転生", "チート能力", "ハーレム"],
  "ending_preference": "謎が解けて街の霧が晴れ、図書館が再生する",
  "volume_count": 4,
  "language": "ja"
}
EOF

# 作業場所初期化
uv run python -m storycraft.cli init \
  --workspace ./my-novel \
  --request request.json \
  --config config.json \
  --json
```

### 2. キーワードから始める場合

```bash
cat > keywords.json <<'EOF'
{
  "keywords": ["霧", "図書館", "司書", "消えた本", "謎解き"],
  "language": "ja"
}
EOF

uv run python -m storycraft.cli init \
  --workspace ./my-novel \
  --keywords keywords.json \
  --config config.json \
  --json
```

### 3. 実行・状態確認・検証

```bash
# 実行（完了または停止まで）
uv run python -m storycraft.cli run --workspace ./my-novel --json

# 状態表示
uv run python -m storycraft.cli status --workspace ./my-novel --json

# 検証
uv run python -m storycraft.cli validate --workspace ./my-novel --json
```

## 終了コード

| コード | 意味 |
|-------|------|
| 0 | 正常完了（`run`）、正常取得（`status`/`validate`） |
| 2 | 引数・作業場所・設定不正（`init`） |
| 4 | 停止中（`blocked`）または実行不能 |
| 5 | 検証不合格（`validate`） |
| 70 | 内部エラー |
| 75 | ロック取得不能 |

`--json` 指定時、成功時は JSON 1行、エラー時は stderr に `{"ok":false,"code":"...","message":"..."}` を出力します。

## 主な原則

- 確定した作品の状態、場面、計画、公開用原稿は書き換えない
- 本文中の根拠がない物語上の事実や現在状態は作らない
- LLM が作った候補は、コードによる検証と独立した確認を経て採用する
- 必要な根拠は採用済み正本を明示参照して渡し、機械的な抜粋・切り詰めや引継ぎ要約を使わない
- 復旧と公開は決定的に行い、確定済み成果物を上書きしない
- 読者向けの公開単位は巻だけであり、最終巻の公開でシリーズ制作も完了する
- ローカル LLM 専用のため、トークン量や費用による予算管理は行わない

## 文書

| 文書 | 内容 |
|------|------|
| [仕様書](docs/SPECIFICATION.md) | V1 の唯一の仕様正本 |
| [実装状況](docs/IMPLEMENTATION_STATUS.md) | 時点付きの実装・検証記録。仕様正本ではない |
| [設計書](docs/design/README.md) | 実装設計ドキュメント群の索引 |
| [テスト用資料](tests/fixtures/README.md) | 自動試験で使う資料の構成 |

## 開発者向け検証

```bash
# 全テスト実行
uv run python -m unittest discover -s tests -p "test_*.py"

# 個別実行
uv run python -m unittest tests.test_cli
```

## 構成

```
src/storycraft/           # 実装コード
├── cli.py                # CLI エントリーポイント
├── workflow.py           # 実行ディスパッチャ
├── workspace.py          # 作業場所初期化・検証
├── run_state.py          # 実行状態 v3
├── volume_publication_stage.py  # 巻公開
├── reviewed_candidate_stage.py  # 汎用候補生成/確認/修正
├── reviewed_prose_stage.py      # 本文生成/確認/修正
├── scene_prose_stage.py         # 場面本文
├── scene_continuity_stage.py    # 継続性更新
├── series_contracts.py          # 検証器
├── series_model.py              # LLMモデル
├── ollama.py                    # Ollama境界
├── prompt_template.py           # プロンプトテンプレート
├── config.py                    # 設定
└── ...

templates/prompts/
├── system/                      # システムプロンプト
├── schemas/                     # JSONスキーマ
└── user/                        # ユーザープロンプト (generate/critique/revision × 15ステージ)

docs/
├── SPECIFICATION.md             # 仕様正本
├── IMPLEMENTATION_STATUS.md     # 実装状況
└── design/                      # 設計書群

tests/                          # 66テスト
```

> Storycraft は物語の意味生成を LLM に任せながら、状態、保存、継続性、再開、巻公開、最終巻公開による制作完了を明示的な契約と決定的なコードで管理します。