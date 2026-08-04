"""プロンプトテンプレートローダー - Jinja2テンプレートからプロンプトを構築"""

from __future__ import annotations

import json
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from jsonschema import Draft202012Validator

from .series_contracts import ContractError


class PromptTemplate:
    """Jinja template and schema loader constrained to the packaged prompt root."""

    def __init__(self, template_dir: Path):
        self.template_dir = template_dir.expanduser()
        if self.template_dir.is_symlink() or not self.template_dir.is_dir():
            raise ContractError("prompt template rootが通常directoryではありません")
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.policies["json.dumps_function"] = json.dumps
        self.env.policies["json.dumps_kwargs"] = {
            "ensure_ascii": False,
            "sort_keys": True,
            "separators": (",", ":"),
        }
        self._schema_cache: dict[Path, dict[str, object]] = {}

    @staticmethod
    def _component(value: object, label: str) -> str:
        if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
            raise ContractError(f"{label}が不正です")
        return value

    def _asset_path(self, relative: Path, label: str) -> Path:
        """Resolve one prompt asset without lexical or symlink escape."""
        root = self.template_dir.resolve()
        candidate = self.template_dir / relative
        if candidate.is_symlink() or not candidate.is_file():
            raise ContractError(f"{label}が通常fileではありません")
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ContractError(f"{label}がprompt root外を参照します") from exc
        if resolved.is_symlink() or not resolved.is_file():
            raise ContractError(f"{label}が通常fileではありません")
        return resolved

    def load_schema_object(self, category: str, stage: str) -> dict[str, object]:
        """Schema fileをJSON objectとして読み込む。"""
        category = self._component(category, "schema category")
        stage = self._component(stage, "schema stage")
        if category == "critique":
            relative = Path("schemas") / "critique.json"
        else:
            if category not in {"generate", "revise", "revision", "fix"}:
                raise ContractError(f"schema categoryが不正です: {category}")
            relative = Path("schemas") / f"{stage}.json"

        cache_key = self._asset_path(relative, "schema")
        cached = self._schema_cache.get(cache_key)
        if cached is not None:
            return cached

        with cache_key.open(encoding="utf-8") as file:
            schema = json.load(file)
        if not isinstance(schema, dict):
            raise ValueError(f"Schema rootはobjectでなければなりません: {cache_key}")
        Draft202012Validator.check_schema(schema)
        self._schema_cache[cache_key] = schema
        return schema

    def load_schema(self, category: str, stage: str) -> str:
        """Schema fileを整形済みJSON文字列で返す。"""
        schema = self.load_schema_object(category, stage)
        return json.dumps(schema, ensure_ascii=False, indent=2)

    def render_system(self, response_mode: str = "json") -> str:
        """応答形式に対応するシステムプロンプトを描画する。単一の共通ファイルを使用。"""
        if response_mode not in {"json", "prose"}:
            raise ValueError(f"未知のresponse modeです: {response_mode}")
        self._asset_path(Path("system") / "common.j2", "system prompt")
        return self.env.get_template("system/common.j2").render(response_mode=response_mode)

    def render_user(self, kind: str, template_stage: str, **kwargs) -> str:
        """ユーザープロンプトをテンプレート名とレンダリング値から構築する。"""
        kind = self._component(kind, "prompt kind")
        template_stage = self._component(template_stage, "prompt stage")
        relative = Path("user") / template_stage / f"{kind}_{template_stage}.j2"
        self._asset_path(relative, "user prompt")
        template = self.env.get_template(relative.as_posix())
        return template.render(**kwargs)

    def load_schema_text(self, category: str, stage: str) -> str:
        return self.load_schema(category, stage)


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
