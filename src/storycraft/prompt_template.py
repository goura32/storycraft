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
        # Jinja標準tojsonのシリアライズ設定はここで一元管理する。
        self.env.policies["json.dumps_function"] = json.dumps
        self.env.policies["json.dumps_kwargs"] = {
            "ensure_ascii": False,
            "sort_keys": True,
            "separators": (",", ":"),
        }
        # Schemaは読み取り専用として共有する。
        # 呼び出し側で変更してはならない。
        self._schema_cache: dict[
            Path,
            dict[str, object],
        ] = {}

    def load_schema_object(
        self,
        category: str,
        stage: str,
    ) -> dict[str, object]:
        """Schema fileをJSON objectとして読み込む。"""
        if category == "critique":
            # 確認用スキーマは共通（critique.json）を使用
            schema_path = self.template_dir / "schemas" / "critique.json"
        else:
            # GenerateとRevisionはStage別Schemaを共有する。
            schema_path = (
                self.template_dir
                / "schemas"
                / f"{stage}.json"
            )

        cache_key = schema_path.resolve()
        cached = self._schema_cache.get(cache_key)

        if cached is not None:
            return cached

        with cache_key.open(encoding="utf-8") as file:
            schema = json.load(file)

        if not isinstance(schema, dict):
            raise ValueError(
                f"Schema rootはobjectでなければなりません: "
                f"{cache_key}"
            )

        self._schema_cache[cache_key] = schema
        return schema

    def load_schema(self, category: str, stage: str) -> str:
        """Schema fileを整形済みJSON文字列で返す。"""
        schema = self.load_schema_object(category, stage)
        return json.dumps(schema, ensure_ascii=False, indent=2)

    def render_system(
        self,
        response_mode: str = "json",
    ) -> str:
        """応答形式に対応するシステムプロンプトを描画する。単一の共通ファイルを使用。"""
        if response_mode not in {"json", "prose"}:
            raise ValueError(
                f"未知のresponse modeです: {response_mode}"
            )
        return self.env.get_template("system/common.j2").render(response_mode=response_mode)

    def render_user(self, kind: str, template_stage: str, **kwargs) -> str:
        """ユーザープロンプトをテンプレート名とレンダリング値から構築する。"""
        template = self.env.get_template(f"user/{template_stage}/{kind}_{template_stage}.j2")
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
