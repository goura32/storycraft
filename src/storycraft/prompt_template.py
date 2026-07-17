"""プロンプトテンプレートローダー - Jinja2テンプレートからプロンプトを構築"""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class PromptTemplate:
    """プロンプトテンプレートの読み込みとレンダリングを管理"""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # カスタムフィルタ: JSON整形出力
        self.env.filters["tojson"] = lambda v, **kw: json.dumps(v, **kw)

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
        # スキーマは呼び出し側で明示的にロードして渡すこと
        template = self.env.get_template(f"user/{kind}_{stage}.j2")
        return template.render(**kwargs)

    def load_schema_text(self, category: str, stage: str) -> str:
        return self.load_schema(category, stage)


# シングルトンインスタンス
_template_loader: PromptTemplate | None = None


def get_template_loader() -> PromptTemplate:
    """パッケージ同梱テンプレートを優先してシングルトンを取得する。"""
    global _template_loader
    if _template_loader is None:
        packaged = Path(__file__).parent / "templates" / "prompts"
        source_tree = Path(__file__).parent.parent.parent / "templates" / "prompts"
        template_dir = packaged if packaged.exists() else source_tree
        _template_loader = PromptTemplate(template_dir)
    return _template_loader