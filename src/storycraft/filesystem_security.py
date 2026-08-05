"""Filesystem boundary checks used before creating or persisting artifacts."""
from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
import stat
from uuid import uuid4
import weakref

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
            expected = os.stat(part, dir_fd=current_fd, follow_symlinks=False)
            if stat.S_ISLNK(expected.st_mode) or not stat.S_ISDIR(expected.st_mode):
                raise ContractError("directory fd相対pathが通常directoryではありません")
            next_fd = os.open(part, flags, dir_fd=current_fd)
            actual = os.fstat(next_fd)
            if (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
                os.close(next_fd)
                raise ContractError("directory fd相対pathがopen前に置換されました")
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


_PosixPath = type(Path())


class _OwnedDirectoryPath(_PosixPath):
    """A ``Path`` view that keeps its directory descriptor alive.

    A plain ``/proc/self/fd/N`` path is only safe while the descriptor remains
    open.  Workspace creation transfers ownership of the final directory FD to
    the returned path so a caller cannot accidentally continue through a
    replaced lexical parent.  Descendant paths retain the owner object.
    """

    def __new__(cls, value: str, descriptor: int):
        self = super().__new__(cls, value)
        setattr(self, "_anchor_descriptor", descriptor)
        setattr(self, "_anchor_finalizer", weakref.finalize(self, os.close, descriptor))
        return self

    def _make_child(self, args):
        child = super()._make_child(args)  # type: ignore[attr-defined]
        setattr(child, "_anchor_owner", self)
        return child

    def close(self) -> None:
        finalizer = getattr(self, "_anchor_finalizer", None)
        if finalizer is not None and finalizer.alive:
            finalizer()


def owned_directory_fd_path(directory_fd: int) -> Path:
    """Return an FD-backed path whose descriptor is closed on final release."""
    return _OwnedDirectoryPath(f"/proc/self/fd/{directory_fd}", directory_fd)


def assert_directory_fd_identity(path: Path, descriptor: int) -> None:
    """Fail closed when ``path`` no longer names the opened directory."""
    anchored = _directory_fd_anchor(path)
    target_identity: tuple[int, int]
    try:
        if anchored is None:
            path_stat = os.stat(path, follow_symlinks=False)
            if not stat.S_ISDIR(path_stat.st_mode):
                raise ContractError("pathは通常directoryでなければなりません")
            target_identity = (path_stat.st_dev, path_stat.st_ino)
        else:
            probe = _open_relative_directory(anchored[0], anchored[1])
            try:
                probe_stat = os.fstat(probe)
                if not stat.S_ISDIR(probe_stat.st_mode):
                    raise ContractError("directory fd相対pathが通常directoryではありません")
                target_identity = (probe_stat.st_dev, probe_stat.st_ino)
            finally:
                os.close(probe)
        fd_stat = os.fstat(descriptor)
    except OSError as exc:
        raise ContractError("directory identityを検証できません") from exc
    if target_identity != (fd_stat.st_dev, fd_stat.st_ino):
        raise ContractError("directoryが検証後に置換されました")


def directory_identity(path: Path, *, missing_ok: bool = False) -> tuple[int, int] | None:
    """Capture identity from the directory FD that was actually opened.

    Do not perform a pathname validation followed by a separate pathname
    ``stat`` here.  That sequence lets a replacement win between the two
    operations.  The no-follow directory chain opens and verifies every
    component relative to its already-open parent before returning the final
    descriptor.
    """
    absolute = absolute_without_resolving(path)
    descriptor: int | None = None
    try:
        descriptor = _open_directory_chain(absolute)
        descriptor_stat = os.fstat(descriptor)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise ContractError("directoryが存在しません")
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if stat.S_ISLNK(descriptor_stat.st_mode) or not stat.S_ISDIR(descriptor_stat.st_mode):
        raise ContractError("pathは通常directoryでなければなりません")
    return descriptor_stat.st_dev, descriptor_stat.st_ino


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


def ensure_directory_chain_nofollow_fd(path: Path) -> tuple[Path, int]:
    """Create a directory chain and retain the identity-checked final FD."""
    target = absolute_without_resolving(path)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(os.fspath(Path(target.anchor)), flags)
    try:
        for part in target.parts[1:]:
            expected = None
            try:
                expected = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
                if stat.S_ISLNK(expected.st_mode) or not stat.S_ISDIR(expected.st_mode):
                    raise ContractError("directory chainに通常directoryでないentryがあります")
            except FileNotFoundError:
                try:
                    os.mkdir(part, 0o755, dir_fd=descriptor)
                except FileExistsError as exc:
                    raise ContractError("directory chainがopen前に競合しました") from exc
                expected = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            actual = os.fstat(next_descriptor)
            if expected is None or (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
                os.close(next_descriptor)
                raise ContractError("directory chainがopen前に置換されました")
            os.close(descriptor)
            descriptor = next_descriptor
    except OSError as exc:
        os.close(descriptor)
        raise ContractError("directory chainを安全に作成できません") from exc
    except Exception:
        os.close(descriptor)
        raise
    return target, descriptor


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


def ensure_directory_at(
    directory_fd: int,
    parts: tuple[str, ...],
    *,
    exist_ok: bool = True,
    reject_existing_final: bool = False,
) -> int:
    """Create/open a relative directory chain while retaining its final FD."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current_fd = os.dup(directory_fd)
    try:
        for index, part in enumerate(parts):
            if part in {"", ".", ".."}:
                raise ContractError("directory相対pathが不正です")
            expected = None
            try:
                expected = os.stat(part, dir_fd=current_fd, follow_symlinks=False)
                if stat.S_ISLNK(expected.st_mode) or not stat.S_ISDIR(expected.st_mode):
                    raise ContractError("directory相対pathに通常directoryでないentryがあります")
            except FileNotFoundError:
                if not exist_ok:
                    raise
                try:
                    os.mkdir(part, 0o755, dir_fd=current_fd)
                except FileExistsError as exc:
                    raise ContractError("directory相対pathがopen前に競合しました") from exc
                expected = os.stat(part, dir_fd=current_fd, follow_symlinks=False)
            else:
                if not exist_ok:
                    raise FileExistsError(part)
                if reject_existing_final and index == len(parts) - 1:
                    raise ContractError("directory相対pathが作成前に競合しました")
            next_fd = os.open(part, flags, dir_fd=current_fd)
            actual = os.fstat(next_fd)
            if expected is None or (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
                os.close(next_fd)
                raise ContractError("directory相対pathがopen前に置換されました")
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def directory_entry_identity(directory_fd: int, name: str, *, require_directory: bool = True) -> tuple[int, int]:
    """Read one no-follow directory entry identity from an already-held FD."""
    try:
        entry = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError as exc:
        raise ContractError(f"directory entryを検証できません: {name}") from exc
    if stat.S_ISLNK(entry.st_mode) or (require_directory and not stat.S_ISDIR(entry.st_mode)):
        raise ContractError(f"directory entryが通常directoryではありません: {name}")
    return entry.st_dev, entry.st_ino


def open_directory_at(
    directory_fd: int,
    parts: tuple[str, ...],
    *,
    expected_identity: tuple[int, int] | None = None,
) -> int:
    """Open an existing relative directory chain with stat/open identity checks."""
    descriptor = _open_relative_directory(directory_fd, parts)
    if expected_identity is not None:
        try:
            descriptor_stat = os.fstat(descriptor)
            if expected_identity != (descriptor_stat.st_dev, descriptor_stat.st_ino):
                raise ContractError("directory fdが検査後に置換されました")
        except Exception:
            os.close(descriptor)
            raise
    return descriptor


def _workspace_relative_parts(root: Path, child: Path) -> tuple[str, ...]:
    root_anchor = _directory_fd_anchor(root)
    child_anchor = _directory_fd_anchor(child)
    if root_anchor is not None and child_anchor is not None and root_anchor[0] == child_anchor[0]:
        prefix = root_anchor[1]
        if child_anchor[1][:len(prefix)] != prefix:
            raise ContractError("workspace childがroot外を参照しています")
        return child_anchor[1][len(prefix):]
    try:
        return absolute_without_resolving(child).relative_to(absolute_without_resolving(root)).parts
    except ValueError as exc:
        raise ContractError("workspace childがroot外を参照しています") from exc


def open_workspace_directory(
    root: Path,
    child: Path,
    *,
    create: bool = True,
    expected_root_identity: tuple[int, int] | None = None,
    expected_child_identity: tuple[int, int] | None = None,
) -> tuple[int, int]:
    """Open workspace root and child directory FDs before pathname races occur."""
    root_abs = absolute_without_resolving(root)
    child_abs = absolute_without_resolving(child)
    assert_within(root_abs, child_abs)
    if expected_root_identity is None:
        expected_root_identity = directory_identity(root_abs)
    if expected_child_identity is None:
        expected_child_identity = directory_identity(child_abs, missing_ok=create)
    root_abs = assert_no_symlink_path(root_abs, require_directory=True)
    root_fd = _open_directory_chain(root_abs, expected_identity=expected_root_identity)
    try:
        relative_parts = _workspace_relative_parts(root_abs, child_abs)
        child_fd = ensure_directory_at(
            root_fd,
            relative_parts,
            exist_ok=create,
            reject_existing_final=create and expected_child_identity is None,
        )
        child_stat = os.fstat(child_fd)
        if expected_child_identity is not None and expected_child_identity != (child_stat.st_dev, child_stat.st_ino):
            os.close(child_fd)
            raise ContractError("workspace childがopen前に置換されました")
        return root_fd, child_fd
    except Exception:
        os.close(root_fd)
        raise


def rename_noreplace_at(src_dir_fd: int, src_name: str, dst_dir_fd: int, dst_name: str) -> None:
    """Atomically publish a directory without replacing an existing target."""
    if os.name != "posix":
        raise ContractError("rename without replaceはこのOSで利用できません")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (AttributeError, OSError) as exc:
        raise ContractError("rename without replaceを利用できません") from exc
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        src_dir_fd,
        os.fsencode(src_name),
        dst_dir_fd,
        os.fsencode(dst_name),
        1,  # Linux RENAME_NOREPLACE
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise ContractError("workspace targetが既に存在します")
    raise OSError(error_number, os.strerror(error_number))


def _open_cleanup_directory(parent_fd: int) -> tuple[str, int, tuple[int, int]]:
    """Create a private per-operation directory used to quarantine one entry."""
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    for _ in range(16):
        cleanup_name = f".storycraft-cleanup-{uuid4().hex}"
        try:
            os.mkdir(cleanup_name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            continue
        cleanup_fd: int | None = None
        try:
            cleanup_fd = os.open(cleanup_name, flags, dir_fd=parent_fd)
            cleanup_stat = os.fstat(cleanup_fd)
            if not stat.S_ISDIR(cleanup_stat.st_mode):
                raise ContractError("cleanup directoryが通常directoryではありません")
            return cleanup_name, cleanup_fd, (cleanup_stat.st_dev, cleanup_stat.st_ino)
        except Exception:
            if cleanup_fd is not None:
                try:
                    os.close(cleanup_fd)
                except OSError:
                    pass
            # 作成直後のentryをpathnameで回収すると、差替え後の競合者を
            # 消す可能性がある。未処理entryは診断対象として残す。
            raise
    raise ContractError("cleanup directory名を確保できません")


def _close_cleanup_directory(parent_fd: int, cleanup_name: str, cleanup_fd: int, cleanup_identity: tuple[int, int]) -> None:
    """Remove an empty private cleanup directory, otherwise leave evidence intact.

    We intentionally do NOT rmdir by pathname because of TOCTOU: an attacker
    could swap the directory between stat and rmdir. Leaving the uniquely-named
    cleanup directory as evidence is safer than potentially deleting a competitor's
    directory. The cleanup directory name uses uuid4 making collision negligible.
    """
    try:
        if os.listdir(cleanup_fd):
            return
        # Verify identity via the held fd (no pathname lookup)
        current_stat = os.fstat(cleanup_fd)
        if not stat.S_ISDIR(current_stat.st_mode) or (current_stat.st_dev, current_stat.st_ino) != cleanup_identity:
            return
        # Intentionally NOT calling os.rmdir(cleanup_name, dir_fd=parent_fd) here.
        # A stale private directory is safer than deleting a directory that another
        # writer put at this name.
    except OSError:
        # Cleanup itself is fail-closed.
        return


def _restore_quarantined_entry(
    cleanup_fd: int,
    slot_name: str,
    parent_fd: int,
    original_name: str,
) -> None:
    """Restore a quarantined competitor without replacing a new entry."""
    try:
        rename_noreplace_at(cleanup_fd, slot_name, parent_fd, original_name)
    except (ContractError, OSError):
        # If the original name is occupied, retain both entries and let the
        # read-only validator diagnose the incomplete/tampered state.
        return


def unlink_if_identity_at(directory_fd: int, name: str, expected_identity: tuple[int, int]) -> bool:
    """Remove one owned regular file without deleting a swapped competitor.

    A pathname ``stat`` followed by ``unlink`` is not an ownership test: the
    name can be replaced in between.  Move the current entry, without replace,
    into a private directory first.  If the moved inode is not ours, restore it
    without replace and leave it alone.  Only the verified owner is removed,
    and a failed quarantine cleanup is intentionally left for validation.
    """
    try:
        initial = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError:
        return False
    if not stat.S_ISREG(initial.st_mode) or (initial.st_dev, initial.st_ino) != expected_identity:
        return False

    cleanup_name, cleanup_fd, cleanup_identity = _open_cleanup_directory(directory_fd)
    slot_name = f"entry-{uuid4().hex}"
    moved = False
    owner_removed = False
    try:
        # stat直後: rename前にregular-file/directory競合差替えを検知
        try:
            pre_rename = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError:
            return False
        if not stat.S_ISREG(pre_rename.st_mode) or (pre_rename.st_dev, pre_rename.st_ino) != expected_identity:
            return False
        try:
            rename_noreplace_at(directory_fd, name, cleanup_fd, slot_name)
            moved = True
        except (ContractError, OSError):
            return False
        try:
            descriptor = os.open(
                slot_name,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=cleanup_fd,
            )
        except OSError:
            return False
        try:
            moved_stat = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        moved_identity = (moved_stat.st_dev, moved_stat.st_ino)
        if not stat.S_ISREG(moved_stat.st_mode) or moved_identity != expected_identity:
            return False
        try:
            os.unlink(slot_name, dir_fd=cleanup_fd)
        except OSError:
            return False
        owner_removed = True
        return True
    finally:
        try:
            if moved and not owner_removed:
                _restore_quarantined_entry(cleanup_fd, slot_name, directory_fd, name)
        finally:
            try:
                _close_cleanup_directory(directory_fd, cleanup_name, cleanup_fd, cleanup_identity)
            finally:
                os.close(cleanup_fd)


def remove_empty_directory_if_identity_at(directory_fd: int, name: str, expected_identity: tuple[int, int]) -> bool:
    """Remove one owned empty directory without deleting a swapped directory."""
    try:
        initial = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError:
        return False
    if not stat.S_ISDIR(initial.st_mode) or (initial.st_dev, initial.st_ino) != expected_identity:
        return False

    cleanup_name, cleanup_fd, cleanup_identity = _open_cleanup_directory(directory_fd)
    slot_name = f"directory-{uuid4().hex}"
    moved = False
    owner_removed = False
    try:
        # stat直後: rename前にregular-file/directory競合差替えを検知
        try:
            pre_rename = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError:
            return False
        if not stat.S_ISDIR(pre_rename.st_mode) or (pre_rename.st_dev, pre_rename.st_ino) != expected_identity:
            return False
        try:
            rename_noreplace_at(directory_fd, name, cleanup_fd, slot_name)
            moved = True
        except (ContractError, OSError):
            return False
        try:
            descriptor = os.open(
                slot_name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=cleanup_fd,
            )
        except OSError:
            return False
        try:
            moved_stat = os.fstat(descriptor)
            is_empty = not os.listdir(descriptor)
        finally:
            os.close(descriptor)
        moved_identity = (moved_stat.st_dev, moved_stat.st_ino)
        if not stat.S_ISDIR(moved_stat.st_mode) or moved_identity != expected_identity or not is_empty:
            return False
        try:
            os.rmdir(slot_name, dir_fd=cleanup_fd)
        except OSError:
            return False
        owner_removed = True
        return True
    finally:
        try:
            if moved and not owner_removed:
                _restore_quarantined_entry(cleanup_fd, slot_name, directory_fd, name)
        finally:
            try:
                _close_cleanup_directory(directory_fd, cleanup_name, cleanup_fd, cleanup_identity)
            finally:
                os.close(cleanup_fd)


def _open_directory_chain(
    directory: Path,
    *,
    expected_identity: tuple[int, int] | None = None,
) -> int:
    """Open every directory component without following symlinks."""
    anchored = _directory_fd_anchor(directory)
    if anchored is not None:
        descriptor, parts = anchored
        try:
            opened = _open_relative_directory(descriptor, parts)
            if expected_identity is not None:
                opened_stat = os.fstat(opened)
                if expected_identity != (opened_stat.st_dev, opened_stat.st_ino):
                    os.close(opened)
                    raise ContractError("directoryがopen前に置換されました")
            return opened
        except OSError as exc:
            raise ContractError("directory fd相対pathが通常directoryではありません") from exc
    absolute = absolute_without_resolving(directory)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(os.fspath(Path(absolute.anchor)), flags)
    try:
        for part in absolute.parts[1:]:
            expected = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISLNK(expected.st_mode) or not stat.S_ISDIR(expected.st_mode):
                raise ContractError("directory pathに通常directoryでないentryがあります")
            next_descriptor = os.open(part, flags, dir_fd=descriptor)
            actual = os.fstat(next_descriptor)
            if (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
                os.close(next_descriptor)
                raise ContractError("directoryがopen中に置換されました")
            os.close(descriptor)
            descriptor = next_descriptor
        if expected_identity is not None:
            opened_stat = os.fstat(descriptor)
            if expected_identity != (opened_stat.st_dev, opened_stat.st_ino):
                raise ContractError("directoryがopen前に置換されました")
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def atomic_write_text(path: Path, content: str) -> None:
    """Publish one file with fsync and a directory-handle anchored rename."""
    target = assert_no_symlink_file_path(path)
    directory_fd = _open_directory_chain(target.parent, expected_identity=directory_identity(target.parent))
    temporary_name = f".{target.name}.{uuid4().hex}.tmp"
    temporary_fd: int | None = None
    temporary_identity: tuple[int, int] | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        temporary_fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        temporary_stat = os.fstat(temporary_fd)
        if not stat.S_ISREG(temporary_stat.st_mode):
            raise ContractError("atomic公開temporaryが通常fileではありません")
        temporary_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
        with os.fdopen(temporary_fd, "w", encoding="utf-8") as handle:
            temporary_fd = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        # rename前にtemporary identityを再確認（competitor差替え防止）
        check_fd = os.open(temporary_name, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
        try:
            current_stat = os.fstat(check_fd)
            if not stat.S_ISREG(current_stat.st_mode) or (current_stat.st_dev, current_stat.st_ino) != temporary_identity:
                raise ContractError("atomic公開temporaryがrename前に置換されました")
        finally:
            os.close(check_fd)
        os.rename(temporary_name, target.name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
        # rename後に公開されたtargetのidentityを再確認（post-rename TOCTOU防止）
        target_fd = os.open(target.name, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
        try:
            target_stat = os.fstat(target_fd)
            if not stat.S_ISREG(target_stat.st_mode) or (target_stat.st_dev, target_stat.st_ino) != temporary_identity:
                # 公開済みcorrupted fileをbest-effortでunlink
                try:
                    unlink_if_identity_at(directory_fd, target.name, temporary_identity)
                except Exception:
                    pass
                raise ContractError("atomic公開targetがrename後に置換されました")
        finally:
            os.close(target_fd)
        os.fsync(directory_fd)
    except Exception:
        if temporary_fd is not None:
            os.close(temporary_fd)
        if temporary_identity is not None:
            unlink_if_identity_at(directory_fd, temporary_name, temporary_identity)
        raise
    finally:
        os.close(directory_fd)


def atomic_write_text_noreplace(path: Path, content: str) -> tuple[int, int]:
    """Publish one file atomically without replacing a competitor."""
    target = assert_no_symlink_file_path(path)
    directory_fd = _open_directory_chain(
        target.parent,
        expected_identity=directory_identity(target.parent),
    )
    temporary_name = f".{target.name}.{uuid4().hex}.tmp"
    temporary_fd: int | None = None
    published = False
    published_identity: tuple[int, int] | None = None
    temporary_identity: tuple[int, int] | None = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        temporary_fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        temporary_stat = os.fstat(temporary_fd)
        if not stat.S_ISREG(temporary_stat.st_mode):
            raise ContractError("atomic公開temporaryが通常fileではありません")
        temporary_identity = (temporary_stat.st_dev, temporary_stat.st_ino)
        with os.fdopen(temporary_fd, "w", encoding="utf-8") as handle:
            temporary_fd = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        rename_noreplace_at(directory_fd, temporary_name, directory_fd, target.name)
        published_identity = temporary_identity
        published = True
        assert published_identity is not None
        assert_file_identity_at(directory_fd, target.name, published_identity)
        os.fsync(directory_fd)
        return published_identity
    except Exception as exc:
        if published:
            setattr(exc, "_storycraft_published_target", True)
            setattr(exc, "_storycraft_published_identity", published_identity)
            # 公開済みfileのidentity検証失敗時はbest-effortでunlink（corrupted内容除去）
            if published_identity is not None:
                try:
                    unlink_if_identity_at(directory_fd, target.name, published_identity)
                except Exception:
                    pass
        if temporary_fd is not None:
            os.close(temporary_fd)
        if temporary_identity is not None:
            unlink_if_identity_at(directory_fd, temporary_name, temporary_identity)
        raise
    finally:
        os.close(directory_fd)


def assert_file_identity_at(directory_fd: int, name: str, expected_identity: tuple[int, int]) -> None:
    """Fail closed when a published regular file leaf changed after publication."""
    try:
        target_stat = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError as exc:
        raise ContractError("公開後のfile identityを検証できません") from exc
    if not stat.S_ISREG(target_stat.st_mode) or (target_stat.st_dev, target_stat.st_ino) != expected_identity:
        raise ContractError("公開後のfileが置換されました")


def open_nofollow(path: Path, flags: int, mode: int = 0o600) -> int:
    """Open a leaf relative to an already verified no-symlink directory chain."""
    target = assert_no_symlink_file_path(path)
    directory_fd = _open_directory_chain(target.parent, expected_identity=directory_identity(target.parent))
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
    descriptor = open_nofollow(path, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ContractError("pathは通常fileでなければなりません")
        with os.fdopen(descriptor, "r", encoding=encoding) as handle:
            descriptor = -1
            return handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def read_text_at(
    directory_fd: int,
    relative: Path,
    *,
    encoding: str = "utf-8",
    expected_identity: tuple[int, int] | None = None,
) -> str:
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
        descriptor = os.open(
            parts[-1],
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0),
            dir_fd=current_fd,
        )
        try:
            leaf_stat = os.fstat(descriptor)
            if not stat.S_ISREG(leaf_stat.st_mode):
                raise ContractError("directory fdから読むleafは通常fileでなければなりません")
            if expected_identity is not None and expected_identity != (leaf_stat.st_dev, leaf_stat.st_ino):
                raise ContractError("prompt assetが検査後に置換されました")
            with os.fdopen(descriptor, "r", encoding=encoding) as handle:
                descriptor = -1
                return handle.read()
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    finally:
        os.close(current_fd)


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
