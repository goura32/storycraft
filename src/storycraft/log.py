"""進捗ログ。公開CLIの標準ストリームには出さず、必要時だけファイルへ出す。"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import stat

from .filesystem_security import assert_no_symlink_file_path, assert_no_symlink_path, directory_identity, open_workspace_directory
from .series_contracts import ContractError


def get_logger() -> logging.Logger:
    log = logging.getLogger("storycraft")
    if not log.handlers:
        # stdout/stderr are a machine-readable public CLI protocol.  Keep the
        # default logger silent; callers that need diagnostics opt into an
        # explicit workspace file handler below.
        log.addHandler(logging.NullHandler())
        log.setLevel(logging.INFO)
        log.propagate = False
    return log


logger = get_logger()


def add_file_handler(log_file: Path, *, workspace_root: Path) -> None:
    """作業workspace内のログファイルへnofollowで出力する。"""
    root = assert_no_symlink_path(workspace_root, require_directory=True)
    path = Path(log_file).absolute()
    root_descriptor, parent_descriptor = open_workspace_directory(
        root,
        path.parent,
        create=True,
        expected_root_identity=directory_identity(root),
        expected_child_identity=directory_identity(path.parent, missing_ok=True),
    )
    try:
        assert_no_symlink_file_path(path)
        descriptor = os.open(
            path.name,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_APPEND
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0),
            0o600,
            dir_fd=parent_descriptor,
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ContractError("log fileは通常fileでなければなりません")
        except Exception:
            os.close(descriptor)
            raise
    finally:
        os.close(parent_descriptor)
        os.close(root_descriptor)
    stream = os.fdopen(descriptor, "a", encoding="utf-8")
    fh = logging.StreamHandler(stream)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
