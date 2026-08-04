"""検証済みstaging directoryのimmutableな確定処理。"""
from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path

from .filesystem_security import _open_directory_chain, assert_no_symlink_path
from .series_contracts import ContractError


DirectoryValidator = Callable[[Path], None]


def fsync_directory(path: Path) -> None:
    """POSIX環境でdirectory entryを同期する。"""
    if os.name != "posix":
        return
    descriptor = _open_directory_chain(path)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def finalize_immutable_directory(
    *,
    staging: Path,
    final: Path,
    validator: DirectoryValidator,
) -> None:
    """staging directoryを検証してatomic renameで確定する。"""
    staging = staging.expanduser()
    final = final.expanduser()

    if staging == final:
        raise ContractError(
            "staging directoryとfinal directoryは"
            "異なる必要があります"
        )

    if staging.is_symlink() or not staging.is_dir():
        raise ContractError(
            f"staging directoryが存在しません: {staging}"
        )

    if final.exists() or final.is_symlink():
        raise ContractError(
            f"immutable final directoryは既に存在します: {final}"
        )

    final_parent = final.parent
    if final_parent.is_symlink() or not final_parent.is_dir():
        raise ContractError(
            "final directoryの親directoryが存在しません: "
            f"{final_parent}"
        )

    validator(staging)

    if final.exists() or final.is_symlink():
        raise ContractError(
            f"immutable final directoryは既に存在します: {final}"
        )

    try:
        staging_device = staging.stat(follow_symlinks=False).st_dev
        final_device = final_parent.stat(follow_symlinks=False).st_dev
    except OSError as exc:
        raise ContractError(
            "immutable directoryのfilesystemを確認できません"
        ) from exc

    if staging_device != final_device:
        raise ContractError(
            "stagingとfinalは同一filesystem上に存在する必要があります"
        )

    assert_no_symlink_path(staging.parent, require_directory=True)
    assert_no_symlink_path(final_parent, require_directory=True)
    staging_parent_fd = _open_directory_chain(staging.parent)
    final_parent_fd = _open_directory_chain(final_parent)
    try:
        os.rename(staging.name, final.name, src_dir_fd=staging_parent_fd, dst_dir_fd=final_parent_fd)
        os.fsync(final_parent_fd)
    except OSError as exc:
        raise ContractError(
            "immutable directoryをfinalizeできません: "
            f"{staging} -> {final}"
        ) from exc
    finally:
        os.close(staging_parent_fd)
        os.close(final_parent_fd)

    # ここで失敗してもfinalを削除・巻戻ししない。
    # Recoveryが確定済みdirectoryを再検証して前進する。
    validator(final)
