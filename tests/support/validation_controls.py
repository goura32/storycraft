"""テスト中の重いworkspace全体検証を一時的に延期する。"""
from __future__ import annotations

from contextlib import contextmanager
import sys
from types import ModuleType
from typing import Iterator

import storycraft.workspace as workspace_module


@contextmanager
def defer_workspace_validation() -> Iterator[None]:
    """storycraft内部の全体検証aliasを一時的に無効化する。

    呼び出し側は、対象処理の完了後に本物の
    validate_workspace_layoutを必ず実行すること。
    """
    original = workspace_module.validate_workspace_layout
    patched: list[tuple[ModuleType, object]] = []

    def deferred(
        *args: object,
        **kwargs: object,
    ) -> None:
        return None

    for name, module in list(sys.modules.items()):
        if (
            module is None
            or not name.startswith("storycraft")
        ):
            continue

        try:
            value = getattr(
                module,
                "validate_workspace_layout",
                None,
            )
        except Exception:
            continue

        if value is original:
            patched.append((module, value))
            setattr(
                module,
                "validate_workspace_layout",
                deferred,
            )

    try:
        yield
    finally:
        for module, value in reversed(patched):
            if (
                getattr(
                    module,
                    "validate_workspace_layout",
                    None,
                )
                is deferred
            ):
                setattr(
                    module,
                    "validate_workspace_layout",
                    value,
                )
