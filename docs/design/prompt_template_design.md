# プロンプトテンプレートファイル化 設計書

## 概要

各ステージのプロンプトを外部テンプレートファイルとして管理し、実行時にプレースホルダーを置換してLLMへ送信するプロンプトを構築する。

## 設計目標

1. **プロンプトの可視化・編集容易化** - Pythonコードから分離し、テンプレートファイルとして管理
2. **スキーマの明示的管理** - 出力JSONスキーマをテンプレート内で宣言的に記述
3. **デバッグ容易化** - 送信プロンプトの完全版をログ/ファイルとして確認可能

## プロンプト構成の分類

| 種別 | 共有範囲 | ファイル数 | 説明 |
|------|----------|------------|------|
| **システムプロンプト** | 全ステージ・全用途共通 | 1つ | 役割定義・基本指示・言語規約 |
| **生成用ユーザープロンプト** | ステージごと | 10個 | ステージ固有の入力データ・指示 |
| **批評用ユーザープロンプト** | ステージごと | 10個 | ステージ固有の文脈・批評観点 |
| **修正用ユーザープロンプト** | ステージごと | 10個 | ステージ固有の修正指示 |

## スキーマ構成

| スキーマ | 共有範囲 | ファイル数 | 説明 |
|----------|----------|------------|------|
| **生成出力スキーマ** | ステージごと | 10個 | 各ステージの生成時出力構造 |
| **批評出力スキーマ** | 全ステージ共通 | 1つ | 統一された批評結果構造 |
| **修正出力スキーマ** | 生成と同一 | （別ファイル不要） | 生成スキーマと同一内容（`schemas/generate/` を再利用） |

## ディレクトリ構造

```
storycraft/
├── templates/
│   ├── prompts/
│   │   ├── system/
│   │   │   └── common.j2              # システムプロンプト（全共通・1つ）
│   │   ├── user/
│   │   │   ├── generate_plan.j2
│   │   │   ├── generate_characters.j2
│   │   │   ├── generate_world.j2
│   │   │   ├── generate_timeline.j2
│   │   │   ├── generate_threads.j2
│   │   │   ├── generate_volume_chapters.j2
│   │   │   ├── generate_scene_cards.j2
│   │   │   ├── generate_scene_write.j2
│   │   │   ├── generate_volume_summary.j2
│   │   │   └── generate_closure_check.j2
│   │   │   ├── critique_plan.j2
│   │   │   ├── critique_characters.j2
│   │   │   ├── critique_world.j2
│   │   │   ├── critique_timeline.j2
│   │   │   ├── critique_threads.j2
│   │   │   ├── critique_volume_chapters.j2
│   │   │   ├── critique_scene_cards.j2
│   │   │   ├── critique_scene_write.j2
│   │   │   ├── critique_volume_summary.j2
│   │   │   └── critique_closure_check.j2
│   │   │   ├── fix_plan.j2
│   │   │   ├── fix_characters.j2
│   │   │   ├── fix_world.j2
│   │   │   ├── fix_timeline.j2
│   │   │   ├── fix_threads.j2
│   │   │   ├── fix_volume_chapters.j2
│   │   │   ├── fix_scene_cards.j2
│   │   │   ├── fix_scene_write.j2
│   │   │   ├── fix_volume_summary.j2
│   │   │   └── fix_closure_check.j2
│   │   ├── schemas/
│   │   │   ├── generate/
│   │   │   │   ├── plan.json
│   │   │   │   ├── characters.json
│   │   │   │   ├── world.json
│   │   │   │   ├── timeline.json
│   │   │   │   ├── threads.json
│   │   │   │   ├── volume_chapters.json
│   │   │   │   ├── scene_cards.json
│   │   │   │   ├── scene_write.json
│   │   │   │   ├── volume_summary.json
│   │   │   │   └── closure_check.json
│   │   │   └── critique.json          # 批評出力スキーマ（共通・1個）
│   │   # 修正スキーマは生成スキーマと同一のため別ファイル不要
│   │   # （schemas/generate/ を再利用）
```

## ファイル命名規則

| 種別 | 命名パターン | 例 |
|------|--------------|-----|
| 生成用ユーザープロンプト | `generate_{stage}.j2` | `generate_plan.j2` |
| 批評用ユーザープロンプト | `critique_{stage}.j2` | `critique_plan.j2` |
| 修正用ユーザープロンプト | `fix_{stage}.j2` | `fix_plan.j2` |
| 生成スキーマ | `schemas/generate/{stage}.json` | `schemas/generate/plan.json` |
| 批評スキーマ（共通） | `schemas/critique.json` | （1ファイルのみ） |
| 修正スキーマ | 生成スキーマと同一（別ファイル作成不要） | `schemas/generate/{stage}.json` を参照 |

## テンプレートエンジン

**Jinja2** を採用。理由：
- Python標準的で高機能
- 条件分岐・ループ・フィルタ対応
- インクルード機能でコンポーネント再利用可能
- 既存エコシステムが豊富

## プレースホルダー仕様

### 共通プレースホルダー（全テンプレート共通）

| 変数名 | 型 | 説明 | 例 |
|--------|-----|------|-----|
| `stage_name` | str | ステージ識別子 | `"plan"` |
| `ref` | str | 呼び出し参照ID | `"vol1.ch1.sc1"` |
| `log_prefix` | str | ログプレフィックス | `"巻1/5 章:1/8 場面:1/3"` |
| `improvement_directions` | list[str] | 改善指示リスト | `["地の文を削る", "対話を自然に"]` |
| `json_schema` | str | 出力スキーマ文字列 | 後述 |

### ステージ別プレースホルダー（生成・批評・修正共通）

| ステージ | 変数名 | 型 | 説明 |
|----------|--------|-----|------|
| **plan** | `brief` | dict | 企画全体 |
| | `diversity_note` | str | 多様性注入文 |
| **characters** | `series_plan` | dict | 全巻計画 |
| | `diversity_note` | str | 多様性注入文 |
| **world** | `brief` | dict | 企画 |
| | `series_plan` | dict | 全巻計画 |
| | `characters` | dict | 人物・関係カード |
| **timeline** | `brief` | dict | 企画 |
| | `series_plan` | dict | 全巻計画 |
| **threads** | `brief` | dict | 企画 |
| | `series_plan` | dict | 全巻計画 |
| | `characters` | dict | 人物・関係カード |
| | `world` | dict | 世界台帳 |
| | `timeline` | dict | 時間台帳 |
| **volume_chapters** | `vol_plan` | dict | 対象巻計画 |
| | `brief` | dict | 企画 |
| | `prior_summaries` | list | 前巻要約リスト |
| | `threads` | dict | 伏線台帳 |
| | `is_final` | bool | 最終巻フラグ |
| **scene_cards** | `chapter` | dict | 対象章計画 |
| | `brief` | dict | 企画 |
| | `handoff` | str | 前章引継ぎ要約 |
| | `vol_changes` | str | 巻内変化サマリ |
| | `chapter_threads` | dict | 対象章の伏線 |
| | `is_final_chapter` | bool | 最終章フラグ |
| | `final_condition` | str | 結末条件 |
| **scene_write** | `card` | dict | 場面カード |
| | `context` | dict | 文脈情報（視点、開示範囲、台帳抜粋等） |
| **volume_summary** | `chapters_handoffs` | list | 各章の引継ぎ要約 |
| | `series_plan` | dict | 全巻計画 |
| **closure_check** | `threads` | dict | 伏線台帳 |
| | `scene_updates` | list | 全場面の更新履歴 |
| | `handoffs` | list | 引継ぎ要約リスト |

### 批評・修正用の追加プレースホルダー

| 用途 | 変数名 | 型 | 説明 |
|------|--------|-----|------|
| 批評・修正共通 | `current` | dict | 現在の最良版JSON（草稿） |
| 批評・修正共通 | `card` | dict | 文脈情報（生成時と同等） |
| 修正のみ | `critique_result` | dict | 批評結果（issues, overall_assessment） |

## スキーマ構成

### 1. 生成出力スキーマ（ステージごと・10個）
`schemas/generate/{stage}.json` - 各ステージの生成時出力構造を定義

### 2. 批評出力スキーマ（全ステージ共通・1個）
`schemas/critique.json` - 統一された批評結果構造

```json
{
  "type": "object",
  "required": ["issues", "overall_assessment"],
  "properties": {
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["severity", "category", "location", "problem", "suggestion"],
        "properties": {
          "severity": {"type": "string", "enum": ["致命的", "重要", "軽微"]},
          "category": {"type": "string", "enum": ["表現", "論理", "用語", "構成", "その他"]},
          "location": {"type": "string"},
          "problem": {"type": "string"},
          "suggestion": {"type": "string"}
        }
      }
    },
    "overall_assessment": {"type": "string"}
  }
}
```

### 修正出力スキーマ
生成スキーマと同一。`schemas/generate/{stage}.json` を再利用（別ファイル作成不要）。

## テンプレートエンジン

**Jinja2** を採用。理由：
- Python標準的で高機能
- 条件分岐・ループ・フィルタ対応
- インクルード機能でコンポーネント再利用可能
- 既存エコシステムが豊富

## テンプレートファイル例

### システムプロンプト（`system/common.j2` - 全共通・1つ）

```jinja
あなたは日本語小説の執筆支援AIです。与えられたタスクに従い、自然な日本語でJSONオブジェクトを返してください。

# 基本方針
- 中国語的な表現や不必要な外来語を避ける
- 自然な日本語で記述する
- 指定されたJSON構造のみを返す（説明文は書かない）

# JSON出力規約
- 必ず有効なJSONオブジェクトのみを返す
- コードブロック（```json ... ```）で囲まない
- キー名・文字列値はダブルクォートで囲む
```

### 生成用ユーザープロンプト例（`user/generate_plan.j2`）

```jinja
次の企画から全巻計画を作ってください。

企画:
{{ brief | tojson(ensure_ascii=False, indent=2) }}

巻数は5巻を第一候補に、4〜10巻から題材と物語の広がりで選んでください。
各巻の章数は6〜10章、各章の場面数は2〜4場面、1場面の本文量は1,800〜2,600字の範囲で、
物語の役割に合わせて選んでください。
各巻は少なくとも18場面を持つようにしてください。
計画はシリーズの方向、各巻の章数、視点規則だけを決め、章内の場面や本文の細部は決めないでください。

{% if diversity_note %}
【過去作品との差別化目標】
{{ diversity_note }}
{% endif %}

返すJSONの構造:
{
  "volume_count": 5,
  "volumes": [{"number":1,"title":"","role":"","character_changes":"","resolves":"","leaves":"","chapter_count":8,"viewpoint_rule":""}],
  "final_resolution": "最終巻で回収する結末",
  "series_viewpoint_rule": "語りの形式、視点変更を許す単位、視点人物候補"
}

【この呼び出し専用JSON Schema】
{{ schema }}

必ずJSONオブジェクトだけを返してください。
```

### 批評用ユーザープロンプト例（`user/critique_plan.j2`）

```jinja
次のJSONオブジェクト（草稿）を批評してください。

草稿:
{{ current | tojson(ensure_ascii=False, indent=2) }}

文脈情報:
{{ card | tojson(ensure_ascii=False, indent=2) }}

改善の方向:
{{ improvement_directions | tojson(ensure_ascii=False, indent=2) }}

以下の観点で自由文フィールドの問題点を列挙してください:
- 日本語として自然か（中国語的表現・不要な外来語の混入・用語の揺れ）
- 情報の正確性・一貫性・具体性
- 論理的整合性・矛盾の有無
- 表現の明確さ・冗長さ

【この呼び出し専用JSON Schema】
{{ schema }}

必ずJSONオブジェクトだけを返してください。
```

### 修正用ユーザープロンプト例（`user/fix_plan.j2`）

```jinja
次のJSONオブジェクト（草稿）を、批評結果に従って修正してください。

草稿:
{{ current | tojson(ensure_ascii=False, indent=2) }}

批評結果:
{{ critique_result | tojson(ensure_ascii=False, indent=2) }}

文脈情報:
{{ card | tojson(ensure_ascii=False, indent=2) }}

改善の方向:
{{ improvement_directions | tojson(ensure_ascii=False, indent=2) }}

草稿を床として、計測可能な軸で悪化しない範囲で修正してください。
全フィールドのJSON構造はそのまま維持してください。
批評で指摘された問題点を優先的に解決し、構造項目（ID・enum・必須項目・キー構造）は絶対に変更しないでください。
返すJSONは草稿と同じ構造で返してください。

【この呼び出し専用JSON Schema】
{{ schema }}

必ずJSONオブジェクトだけを返してください。
```

## スキーマファイル例

### 生成出力スキーマ（`schemas/generate/plan.json`）
```json
{
  "type": "object",
  "required": ["volume_count", "volumes", "final_resolution", "series_viewpoint_rule"],
  "properties": {
    "volume_count": {"type": "integer", "minimum": 4, "maximum": 10},
    "volumes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["number", "title", "role", "character_changes", "resolves", "leaves", "chapter_count", "viewpoint_rule"],
        "properties": {
          "number": {"type": "integer"},
          "title": {"type": "string"},
          "role": {"type": "string"},
          "character_changes": {"type": "string"},
          "resolves": {"type": "string"},
          "leaves": {"type": "string"},
          "chapter_count": {"type": "integer", "minimum": 6, "maximum": 10},
          "viewpoint_rule": {"type": "string"}
        }
      }
    },
    "final_resolution": {"type": "string"},
    "series_viewpoint_rule": {"type": "string"}
  }
}
```

### 批評出力スキーマ（`schemas/critique.json` - 共通）
```json
{
  "type": "object",
  "required": ["issues", "overall_assessment"],
  "properties": {
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["severity", "category", "location", "problem", "suggestion"],
        "properties": {
          "severity": {"type": "string", "enum": ["致命的", "重要", "軽微"]},
          "category": {"type": "string", "enum": ["表現", "論理", "用語", "構成", "その他"]},
          "location": {"type": "string"},
          "problem": {"type": "string"},
          "suggestion": {"type": "string"}
        }
      }
    },
    "overall_assessment": {"type": "string"}
  }
}
```

### 修正出力スキーマ
生成スキーマと同一。`schemas/generate/{stage}.json` を再利用（別ファイル作成不要）。

## テンプレートエンジン

**Jinja2** を採用。理由：
- Python標準的で高機能
- 条件分岐・ループ・フィルタ対応
- インクルード機能でコンポーネント再利用可能
- 既存エコシステムが豊富

## 実装構成

### テンプレートローダー (`prompt_template.py`)

```python
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import json

class PromptTemplate:
    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters['tojson'] = lambda v, **kw: json.dumps(v, ensure_ascii=False, **kw)
    
    def load_schema(self, category: str, stage: str) -> str:
        """スキーマファイルを読み込み、整形済み文字列で返す"""
        if category == "fix":
            # 修正スキーマ＝生成スキーマ
            schema_path = self.template_dir / "schemas" / "generate" / f"{stage}.json"
        elif category == "critique":
            schema_path = self.template_dir / "schemas" / "critique.json"
        else:
            schema_path = self.template_dir / "schemas" / category / f"{stage}.json"
        with schema_path.open(encoding="utf-8") as f:
            schema = json.load(f)
        return json.dumps(schema, ensure_ascii=False, indent=2)
    
    def render_system(self) -> str:
        """システムプロンプト（共通・1つ）"""
        template = self.env.get_template("system/common.j2")
        return template.render()
    
    def render_user(self, kind: str, stage: str, **kwargs) -> str:
        """ユーザープロンプト（kind: generate/critique/fix, stage: plan/characters等）"""
        # スキーマ自動埋め込み
        if kind == "fix":
            schema = self.load_schema("generate", stage)
        elif kind == "critique":
            schema = self.load_schema("critique", "")
        else:
            schema = self.load_schema("generate", stage)
        kwargs.setdefault('schema', schema)
        template = self.env.get_template(f"user/{kind}_{stage}.j2")
        return template.render(**kwargs)
    
    def load_schema_text(self, category: str, stage: str) -> str:
        return self.load_schema(category, stage)
```

### 既存 `prompts.py` のリファクタリング

```python
# prompts.py (新)
from .prompt_template import PromptTemplate

_template_loader = None

def get_template_loader() -> PromptTemplate:
    global _template_loader
    if _template_loader is None:
        template_dir = Path(__file__).parent.parent / "templates" / "prompts"
        _template_loader = PromptTemplate(template_dir)
    return _template_loader

def plan_series(brief: dict, diversity_note: str | None) -> tuple[str, str, dict, str]:
    loader = get_template_loader()
    div = diversity_note or ""
    sys_p = loader.render_system()
    user_p = loader.render_user("generate", "plan", brief=brief, diversity_note=div)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema("generate", "plan")

def critique_plan(current: dict, card: dict, directions: list) -> tuple[str, str, dict, str]:
    loader = get_template_loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("critique", "plan", current=current, card=card, improvement_directions=directions)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema("critique", "")

def fix_plan(current: dict, critique_result: dict, card: dict, directions: list) -> tuple[str, str, dict, str]:
    loader = get_template_loader()
    sys_p = loader.render_system()
    user_p = loader.render_user("fix", "plan", current=current, critique_result=critique_result, card=card, improvement_directions=directions)
    return sys_p, user_p, RESPONSE_FORMAT, loader.load_schema("generate", "plan")

# 他ステージも同様に実装...
```

## 移行手順

1. **テンプレートディレクトリ作成** - `templates/prompts/` 以下に構造作成
2. **既存プロンプト抽出** - `prompts.py` から各ステージのシステム/ユーザープロンプトを `.j2` ファイル化
3. **スキーマファイル作成** - `schemas/generate/`, `schemas/critique.json` 配下に配置
4. **ローダー実装** - `prompt_template.py` 新規作成
5. **`prompts.py` 書き換え** - テンプレートローダー使用に変更
5. **動作確認** - 統合テスト・実LLMテストで検証

## 想定されるメリット

| 観点 | 現状 | テンプレート化後 |
|------|------|------------------|
| プロンプト編集 | Pythonコード修正必須 | テンプレートファイル編集のみ |
| スキーマ管理 | 文字列でハードコード | JSONファイルで管理・検証可能 |
| 共通部品（システムプロンプト等） | 各関数に分散 | 1ファイルで一元管理 |
| 批評スキーマ | 場面用のみ・ハードコード | 共通スキーマファイルで管理 |
| 修正スキーマ | 生成と別管理 | 生成スキーマを再利用 |
| プロンプト確認 | ログから推測 | 完全な送信プロンプトをファイルで確認可能 |
| A/Bテスト | コード修正必要 | テンプレート差し替えで即座に切替可能 |

## リスクと対策

| リスク | 対策 |
|--------|------|
| Jinja2依存追加 | 依存は軽量、標準的 |
| テンプレート記述ミス | 起動時バリデーション、単体テストで検知 |
| プレースホルダー漏れ | 必須変数チェック機能をローダーに実装 |
| パフォーマンス | テンプレートキャッシュで初回のみオーバーヘッド |

## スケジュール目安

| フェーズ | 作業 | 目安 |
|----------|------|------|
| 1 | ディレクトリ作成・既存プロンプト抽出 | 1日 |
| 2 | テンプレート・スキーマファイル作成（全ステージ分） | 1-2日 |
| 3 | ローダー実装・`prompts.py` 書き換え | 1日 |
| 4 | テスト・動作確認 | 1日 |
| **合計** | | **4-5日** |

---

以上