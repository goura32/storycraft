"""Filesystem boundary checks used before creating or persisting artifacts."""
from __future__ import annotations

import os
from pathlib import Path
import stat
from uuid import uuid4

from .series_contracts import ContractError


def absolute_without_resolving(path: Path) -> Path:
    """Make a lexical absolute path without following symlinks."""
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _directory_fd_anchor(path: Path) -> tuple[int, tuple[str, ...]] | None:
    absolute = absolute_without_resolving(path)
    parts = absolute.parts
    if len(parts) < 5 or parts[:4] != ("/", "proc", "self", "fd"):
        return None
    try:
        descriptor = int(parts[4])
    except ValueError:
        return None
    if descriptor < 0:
        return None
    return descriptor, parts[5:]


def _open_relative_directory(directory_fd: int, parts: tuple[str, ...]) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current_fd = os.dup(directory_fd)
    try:
        for part in parts:
            if part in {"", ".", ".."}:
                raise ContractError("directory fd相対pathが不正です")
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _assert_fd_directory_path(directory_fd: int, parts: tuple[str, ...], *, require_directory: bool) -> None:
    try:
        current_fd = _open_relative_directory(directory_fd, parts)
    except FileNotFoundError as exc:
        if require_directory:
            raise ContractError("directory fd相対pathが存在しません") from exc
        return
    except OSError as exc:
        raise ContractError("directory fd相対pathが通常directoryではありません") from exc
    os.close(current_fd)


def _assert_fd_file_path(directory_fd: int, parts: tuple[str, ...], *, require_file: bool) -> None:
    if not parts:
        raise ContractError("directory fd相対file pathが空です")
    try:
        current_fd = _open_relative_directory(directory_fd, parts[:-1])
    except OSError as exc:
        raise ContractError("directory fd相対fileの親が通常directoryではありません") from exc
    try:
        try:
            leaf_stat = os.stat(parts[-1], dir_fd=current_fd, follow_symlinks=False)
        except FileNotFoundError as exc:
            if require_file:
                raise ContractError("directory fd相対fileが存在しません") from exc
            return
        if stat.S_ISLNK(leaf_stat.st_mode) or not stat.S_ISREG(leaf_stat.st_mode):
            raise ContractError("directory fd相対fileが通常fileではありません")
    finally:
        os.close(current_fd)


def directory_fd_path(directory_fd: int) -> Path:
    """Return a path view anchored to an open directory descriptor (Linux)."""
    return Path(f"/proc/self/fd/{directory_fd}")


def is_directory_fd_path(path: Path) -> bool:
    return _directory_fd_anchor(path) is not None


def assert_no_symlink_path(path: Path, *, require_directory: bool = False) -> Path:
    """Reject symlink components and non-directory existing components.

    Missing trailing components are allowed so callers can safely create them;
    every existing component from the filesystem root through ``path`` is
    inspected with ``lstat`` semantics via ``Path.is_symlink``.
    """
    absolute = absolute_without_resolving(path)
    anchored = _directory_fd_anchor(absolute)
    if anchored is not None:
        descriptor, parts = anchored
        _assert_fd_directory_path(descriptor, parts, require_directory=require_directory)
        return absolute
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
    anchored = _directory_fd_anchor(absolute)
    if anchored is not None:
        descriptor, parts = anchored
        _assert_fd_file_path(descriptor, parts, require_file=require_file)
        return absolute
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


def ensure_directory_chain_nofollow(path: Path) -> Path:
    """Create every component of a directory chain without following symlinks."""
    target = absolute_without_resolving(path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(os.fspath(Path(target.anchor)), flags)
    try:
        for part in target.parts[1:]:
            try:
                os.mkdir(part, 0o755, dir_fd=descriptor)
            except FileExistsError:
                pass
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
    except OSError as exc:
        os.close(descriptor)
        raise ContractError("directory chainを安全に作成できません") from exc
    except Exception:
        os.close(descriptor)
        raise
    os.close(descriptor)
    return assert_no_symlink_path(target, require_directory=True)


def create_unique_directory_at(directory_fd: int, prefix: str) -> str:
    """Create and return a unique child directory relative to ``directory_fd``."""
    for _ in range(128):
        name = f"{prefix}{uuid4().hex}"
        try:
            os.mkdir(name, 0o700, dir_fd=directory_fd)
        except FileExistsError:
            continue
        return name
    raise ContractError("一時directory名を確保できません")


def remove_directory_at(parent_fd: int, name: str) -> None:
    """Remove a directory tree through an already opened parent directory."""
    child_fd = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        for child in os.listdir(child_fd):
            child_stat = os.stat(child, dir_fd=child_fd, follow_symlinks=False)
            if stat.S_ISDIR(child_stat.st_mode) and not stat.S_ISLNK(child_stat.st_mode):
                remove_directory_at(child_fd, child)
            else:
                os.unlink(child, dir_fd=child_fd)
    finally:
        os.close(child_fd)
    os.rmdir(name, dir_fd=parent_fd)


def _open_directory_chain(directory: Path) -> int:
    """Open every directory component without following symlinks."""
    anchored = _directory_fd_anchor(directory)
    if anchored is not None:
        descriptor, parts = anchored
        try:
            return _open_relative_directory(descriptor, parts)
        except OSError as exc:
            raise ContractError("directory fd相対pathが通常directoryではありません") from exc
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


def read_text_at(directory_fd: int, relative: Path, *, encoding: str = "utf-8") -> str:
    """Read a relative regular file through a directory-fd anchored chain."""
    relative = Path(relative)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ContractError("directory fdからの相対pathが不正です")
    parts = relative.parts
    if not parts:
        raise ContractError("directory fdからのleaf pathが空です")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current_fd = os.dup(directory_fd)
    try:
        for part in parts[:-1]:
            next_fd = os.open(part, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        descriptor = os.open(parts[-1], os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=current_fd)
        try:
            with os.fdopen(descriptor, "r", encoding=encoding) as handle:
                descriptor = -1
                return handle.read()
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    finally:
        os.close(current_fd)


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
