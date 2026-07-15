"""進捗ログ。標準出力とファイルの両方へ出す。"""
from __future__ import annotations

import logging
import sys
from pathlib import Path


def get_logger() -> logging.Logger:
    log = logging.getLogger("storycraft")
    if not log.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(h)
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
