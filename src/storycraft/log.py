"""進捗ログ。公開CLIの標準ストリームには出さず、必要時だけファイルへ出す。"""
from __future__ import annotations

import logging
from pathlib import Path


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


def add_file_handler(log_file: Path) -> None:
    """作業ディレクトリのログファイルへも出力する。"""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
