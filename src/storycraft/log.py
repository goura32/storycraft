"""進捗ログ。公開CLIの標準ストリームには出さず、必要時だけファイルへ出す。"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .filesystem_security import assert_no_symlink_path, assert_within, ensure_directory_nofollow, open_nofollow


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
    assert_within(root, path)
    ensure_directory_nofollow(path.parent)
    descriptor = open_nofollow(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    stream = os.fdopen(descriptor, "a", encoding="utf-8")
    fh = logging.StreamHandler(stream)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
