"""Stage test用workspace baseline cache。"""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
from threading import RLock
from typing import Any

import storycraft.workspace as workspace_module

from tests.support.validation_controls import (
    defer_workspace_validation,
)


WorkspaceBuilder = Callable[
    [str],
    Path | tuple[Path, Any],
]

_CACHE_DIRECTORY = tempfile.TemporaryDirectory(
    prefix="storycraft-workspace-fixtures-",
)
_CACHE_ROOT = Path(_CACHE_DIRECTORY.name)

_BASELINES: dict[
    str,
    tuple[Path, Any],
] = {}

# Builderが別のcached fixtureを利用する場合があるため、
# 通常のLockではなく再入可能なLockを使う。
_CACHE_LOCK = RLock()


def _remove_build_directory(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _normalize_builder_result(
    built: Path | tuple[Path, Any],
) -> tuple[Path, Any]:
    if isinstance(built, tuple):
        if len(built) != 2:
            raise AssertionError(
                "workspace builderのtupleは"
                "2要素である必要があります"
            )

        baseline, payload = built
    else:
        baseline = built
        payload = None

    if (
        not isinstance(baseline, Path)
        or not baseline.is_dir()
        or baseline.is_symlink()
    ):
        raise AssertionError(
            "workspace builderが有効な"
            "directoryを返しませんでした"
        )

    return baseline, payload


def _build_baseline(
    *,
    key: str,
    builder: WorkspaceBuilder,
) -> tuple[Path, Any]:
    build_parent = _CACHE_ROOT / key

    # 前回のbuilder失敗で残ったdirectoryがあっても、
    # 同じprocess内で再試行できるようにする。
    _remove_build_directory(build_parent)
    build_parent.mkdir(parents=True)

    try:
        # 途中Stageごとの全体検証は省略し、
        # baseline完成後に一度だけ実検証する。
        with defer_workspace_validation():
            built = builder(str(build_parent))

        baseline, payload = _normalize_builder_result(
            built
        )

        resolved_parent = build_parent.resolve()
        resolved_baseline = baseline.resolve()

        try:
            resolved_baseline.relative_to(
                resolved_parent
            )
        except ValueError as exc:
            raise AssertionError(
                "baseline workspaceはcacheの"
                "build directory内に必要です"
            ) from exc

        # 不完全なbaselineをcacheへ登録しないため、
        # 登録直前に本物のvalidatorで検証する。
        workspace_module.validate_workspace_layout(
            baseline
        )

        return baseline, deepcopy(payload)

    except BaseException:
        _remove_build_directory(build_parent)
        raise


def clone_cached_workspace(
    *,
    key: str,
    temporary: str,
    builder: WorkspaceBuilder,
) -> tuple[Path, Any]:
    """検証済みbaselineを一度だけ構築し、独立copyを返す。"""
    if not key:
        raise AssertionError(
            "fixture cache keyが空です"
        )

    with _CACHE_LOCK:
        if key not in _BASELINES:
            _BASELINES[key] = _build_baseline(
                key=key,
                builder=builder,
            )

        baseline, payload = _BASELINES[key]

        destination = (
            Path(temporary) / baseline.name
        )

        if (
            destination.exists()
            or destination.is_symlink()
        ):
            raise AssertionError(
                "fixture workspaceの配置先が"
                f"既に存在します: {destination}"
            )

        shutil.copytree(
            baseline,
            destination,
        )

        return (
            destination,
            deepcopy(payload),
        )
