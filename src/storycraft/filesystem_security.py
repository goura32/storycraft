"""Filesystem boundary checks used before creating or persisting artifacts."""
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

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


def assert_no_symlink_file_path(path: Path, *, require_file: bool = False) -> Path:
    """Reject symlink components for a file path and validate its leaf type."""
    absolute = absolute_without_resolving(path)
    assert_no_symlink_path(absolute.parent, require_directory=True)
    if absolute.is_symlink():
        raise ContractError(f"symlink fileは許可されません: {absolute}")
    if absolute.exists() and not absolute.is_file():
        raise ContractError(f"file pathが通常fileではありません: {absolute}")
    if require_file and not absolute.is_file():
        raise ContractError(f"pathは通常fileでなければなりません: {absolute}")
    return absolute


def ensure_directory_nofollow(path: Path, *, exist_ok: bool = True) -> Path:
    target = Path(path).absolute()
    assert_no_symlink_path(target.parent, require_directory=True)
    directory_fd = _open_directory_chain(target.parent)
    try:
        try:
            os.mkdir(target.name, 0o755, dir_fd=directory_fd)
        except FileExistsError:
            if not exist_ok:
                raise
            assert_no_symlink_path(target, require_directory=True)
    finally:
        os.close(directory_fd)
    return assert_no_symlink_path(target, require_directory=True)


def _open_directory_chain(directory: Path) -> int:
    """Open every directory component without following symlinks."""
    absolute = absolute_without_resolving(directory)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(os.fspath(Path(absolute.anchor)), flags)
    try:
        for part in absolute.parts[1:]:
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def atomic_write_text(path: Path, content: str) -> None:
    """Publish one file with fsync and a directory-handle anchored rename."""
    target = assert_no_symlink_file_path(path)
    directory_fd = _open_directory_chain(target.parent)
    temporary_name = f".{target.name}.{uuid4().hex}.tmp"
    temporary_fd: int | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        temporary_fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        with os.fdopen(temporary_fd, "w", encoding="utf-8") as handle:
            temporary_fd = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(temporary_name, target.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        os.fsync(directory_fd)
    except Exception:
        if temporary_fd is not None:
            os.close(temporary_fd)
        try:
            os.unlink(temporary_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(directory_fd)


def open_nofollow(path: Path, flags: int, mode: int = 0o600) -> int:
    """Open a leaf relative to an already verified no-symlink directory chain."""
    target = assert_no_symlink_file_path(path)
    directory_fd = _open_directory_chain(target.parent)
    try:
        return os.open(
            target.name,
            flags | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            mode,
            dir_fd=directory_fd,
        )
    finally:
        os.close(directory_fd)


def read_text_nofollow(path: Path, *, encoding: str = "utf-8") -> str:
    """Read one regular file through a no-follow descriptor."""
    descriptor = open_nofollow(path, os.O_RDONLY)
    try:
        with os.fdopen(descriptor, "r", encoding=encoding) as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def unlink_nofollow(path: Path, *, missing_ok: bool = False) -> None:
    """Remove one leaf through a no-follow directory descriptor."""
    target = assert_no_symlink_file_path(path)
    directory_fd = _open_directory_chain(target.parent)
    try:
        try:
            os.unlink(target.name, dir_fd=directory_fd)
        except FileNotFoundError:
            if not missing_ok:
                raise
    finally:
        os.close(directory_fd)


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
