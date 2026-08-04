"""Filesystem boundary checks used before creating or persisting artifacts."""
from __future__ import annotations

import os
from pathlib import Path

from .series_contracts import ContractError


def absolute_without_resolving(path: Path) -> Path:
    """Make a lexical absolute path without following symlinks."""
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def assert_no_symlink_path(path: Path, *, require_directory: bool = False) -> Path:
    """Reject symlink components and non-directory existing components.

    Missing trailing components are allowed so callers can safely create them;
    every existing component from the filesystem root through ``path`` is
    inspected with ``lstat`` semantics via ``Path.is_symlink``.
    """
    absolute = absolute_without_resolving(path)
    current = Path(absolute.anchor)
    parts = absolute.parts[1:]
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ContractError(f"symlink pathは許可されません: {absolute}")
        if current.exists() and not current.is_dir():
            raise ContractError(f"directory pathが通常directoryではありません: {absolute}")
    if require_directory and (not absolute.exists() or not absolute.is_dir() or absolute.is_symlink()):
        raise ContractError(f"pathは通常directoryでなければなりません: {absolute}")
    return absolute


def assert_within(root: Path, child: Path) -> None:
    """Require lexical and resolved containment after symlink checks."""
    root_abs = assert_no_symlink_path(root, require_directory=True)
    child_abs = assert_no_symlink_path(child)
    try:
        child_abs.relative_to(root_abs)
    except ValueError as exc:
        raise ContractError("pathがworkspace root外を参照しています") from exc
    try:
        child_abs.resolve().relative_to(root_abs.resolve())
    except ValueError as exc:
        raise ContractError("resolved pathがworkspace root外を参照しています") from exc
