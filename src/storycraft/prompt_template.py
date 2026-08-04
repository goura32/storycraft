"""プロンプトテンプレートローダー - Jinja2テンプレートからプロンプトを構築"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
from typing import Any
import weakref

from jinja2 import BaseLoader, Environment, StrictUndefined
from jsonschema import Draft202012Validator

from .filesystem_security import (
    _open_directory_chain,
    absolute_without_resolving,
    assert_no_symlink_path,
    directory_identity,
    read_text_at,
)
from .series_contracts import ContractError


class _NoFollowPromptLoader(BaseLoader):
    """Jinja loader that reads the selected asset through a no-follow descriptor."""

    def __init__(self, owner: "PromptTemplate") -> None:
        self.owner = owner

    def get_source(self, environment: Environment, template: str):
        del environment
        relative = Path(template)
        reference = self.owner._asset_references.pop(relative, None)
        if reference is None:
            path = self.owner._asset_path(relative, "template")
            expected_identity = self.owner._asset_identities.get(path)
        else:
            path, expected_identity = reference
        try:
            source = self.owner._read_asset_text(path, expected_identity=expected_identity)
        except OSError as exc:
            raise ContractError("templateを安全に読み込めません") from exc
        return source, str(path), lambda: False


class PromptTemplate:
    """Jinja template and schema loader constrained to the packaged prompt root."""

    def __init__(self, template_dir: Path):
        template_candidate = absolute_without_resolving(template_dir.expanduser())
        expected_root_identity = directory_identity(template_candidate)
        self.template_dir = assert_no_symlink_path(template_candidate, require_directory=True)
        self._root_descriptor = _open_directory_chain(
            self.template_dir,
            expected_identity=expected_root_identity,
        )
        self._root_finalizer = weakref.finalize(self, os.close, self._root_descriptor)
        self.env = Environment(
            loader=_NoFollowPromptLoader(self),
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
        self._asset_identities: dict[Path, tuple[int, int]] = {}
        self._asset_references: dict[Path, tuple[Path, tuple[int, int]]] = {}

    @staticmethod
    def _component(value: object, label: str) -> str:
        if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
            raise ContractError(f"{label}が不正です")
        return value

    def _asset_path(self, relative: Path, label: str) -> Path:
        """Resolve one prompt asset without lexical or symlink escape."""
        root = self.template_dir
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
        file_stat = os.stat(resolved, follow_symlinks=False)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ContractError(f"{label}が通常fileではありません")
        identity = (file_stat.st_dev, file_stat.st_ino)
        self._asset_identities[resolved] = identity
        self._asset_references[Path(relative)] = (resolved, identity)
        return resolved

    def _assert_root_descriptor(self) -> None:
        try:
            path_stat = os.stat(self.template_dir, follow_symlinks=False)
            fd_stat = os.fstat(self._root_descriptor)
        except OSError as exc:
            raise ContractError("prompt rootが利用できません") from exc
        if not stat.S_ISDIR(path_stat.st_mode) or (path_stat.st_dev, path_stat.st_ino) != (fd_stat.st_dev, fd_stat.st_ino):
            raise ContractError("prompt rootが初期化時のdirectoryから置換されています")

    def _read_asset_text(self, path: Path, *, expected_identity: tuple[int, int] | None = None) -> str:
        self._assert_root_descriptor()
        try:
            relative = path.relative_to(self.template_dir)
        except ValueError as exc:
            raise ContractError("prompt assetがroot外を参照します") from exc
        if expected_identity is None:
            expected_identity = self._asset_identities.pop(path, None)
        else:
            self._asset_identities.pop(path, None)
        for key, reference in list(self._asset_references.items()):
            if reference[0] == path:
                self._asset_references.pop(key, None)
        if expected_identity is None:
            raise ContractError("prompt assetの検証済みidentityがありません")
        return read_text_at(self._root_descriptor, relative, expected_identity=expected_identity)

    def close(self) -> None:
        finalizer = getattr(self, "_root_finalizer", None)
        if finalizer is not None and finalizer.alive:
            finalizer()

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
            self._assert_root_descriptor()
            self._asset_identities.pop(cache_key, None)
            return cached

        try:
            schema = json.loads(self._read_asset_text(cache_key))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContractError("schemaを安全に読み込めません") from exc
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
