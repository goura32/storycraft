"""検証済みstaging directoryのimmutableな確定処理。"""
from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path

from .series_contracts import ContractError


DirectoryValidator = Callable[[Path], None]


def fsync_directory(path: Path) -> None:
    """POSIX環境でdirectory entryを同期する。"""
    if os.name != "posix":
        return
    descriptor = os.open(path, os.O_RDONLY)
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

    try:
        os.rename(staging, final)
        fsync_directory(final_parent)
    except OSError as exc:
        raise ContractError(
            "immutable directoryをfinalizeできません: "
            f"{staging} -> {final}"
        ) from exc

    # ここで失敗してもfinalを削除・巻戻ししない。
    # Recoveryが確定済みdirectoryを再検証して前進する。
    validator(final)
