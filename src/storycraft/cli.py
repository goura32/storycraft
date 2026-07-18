"""次世代Storycraftのコマンドライン。"""
from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path
from typing import Any

import yaml

from .config import Settings
from .series_engine import ContractError, SeriesService
from .series_model import OpenAIStoryModel
from .log import logger, add_file_handler


_process_started_at: float | None = None
_process_exit_reason = "normal"


def _flush_logs() -> None:
    """終了直前のログをファイルへ確実に反映する。"""
    for handler in logger.handlers:
        handler.flush()


def _handle_termination_signal(signum: int, _frame: Any) -> None:
    """SIGTERMを無言で終わらせず、finally経由で終了記録を残す。"""
    global _process_exit_reason
    signal_name = signal.Signals(signum).name
    _process_exit_reason = f"signal:{signal_name}"
    logger.warning("終了シグナル受信: %s。終了処理を開始します", signal_name)
    _flush_logs()
    raise SystemExit(128 + signum)


def _load_brief(path: str) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise ContractError(f"企画ファイルが見つかりません: {source}")
    text = source.read_text(encoding="utf-8")
    value = json.loads(text) if source.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ContractError("企画ファイルはJSONまたはYAMLのオブジェクトでなければなりません")
    return value


def _setup_logging(workspace: Path) -> None:
    """ワークスペースにログファイルハンドラを追加する。"""
    log_path = workspace / "storycraft.log"
    add_file_handler(log_path)
    logger.info(f"ログ出力先: {log_path}")
    logger.info("プロセス監視開始: pid=%s workspace=%s", os.getpid(), workspace)


def _service_and_model(args) -> tuple[SeriesService, OpenAIStoryModel]:
    settings = Settings.load(args.config)
    workspace = settings.resolve_output_dir(args.out)
    _setup_logging(workspace)
    logger.info(f"モデル: {settings.llm.get('model', 'unknown')}")
    service = SeriesService(workspace)
    return service, OpenAIStoryModel(settings, workspace / "raw")


def _report(result) -> None:
    if result.completed:
        print(f"完了: {result.series_path}")
    else:
        print("保存しました。resume または step で続行できます。")


def cmd_run(args) -> None:
    service, model = _service_and_model(args)
    _report(service.run(_load_brief(args.brief) if args.brief else None, model, keywords=args.keywords))


def cmd_resume(args) -> None:
    service, model = _service_and_model(args)
    _report(service.resume(model))


def cmd_step(args) -> None:
    service, model = _service_and_model(args)
    brief = _load_brief(args.brief) if args.brief else None
    _report(service.step(model, brief, keywords=args.keywords))


def main() -> None:
    parser = argparse.ArgumentParser(prog="storycraft", description="日本語小説シリーズ生成")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name, handler, accepts_initial_input in (
        ("run", cmd_run, True),
        ("resume", cmd_resume, False),
        ("step", cmd_step, True),
    ):
        command = subcommands.add_parser(name)
        command.add_argument("--out", required=True, help="対象シリーズの作業場所")
        command.add_argument("--config", default=None, help="設定YAML")
        if accepts_initial_input:
            initial = command.add_mutually_exclusive_group(required=name == "run")
            initial.add_argument("--brief", help="人が作成した初回企画JSONまたはYAML")
            initial.add_argument("--keywords", action="append", help="brief生成に渡す自由なキーワード。複数回指定できる")
        command.set_defaults(handler=handler)
    args = parser.parse_args()
    global _process_started_at, _process_exit_reason
    _process_started_at = time.monotonic()
    _process_exit_reason = "normal"
    signal.signal(signal.SIGTERM, _handle_termination_signal)
    exit_code = 0
    try:
        args.handler(args)
    except KeyboardInterrupt:
        _process_exit_reason = "keyboard_interrupt"
        exit_code = 130
        logger.warning("ユーザー中断を受信しました")
        raise
    except ContractError as error:
        _process_exit_reason = "contract_error"
        exit_code = 2
        logger.error("契約エラーにより終了します: %s", error)
        parser.error(str(error))
    except SystemExit as error:
        exit_code = int(error.code) if isinstance(error.code, int) else 1
        if _process_exit_reason == "normal":
            _process_exit_reason = "system_exit"
        raise
    except BaseException as error:  # noqa: BLE001
        _process_exit_reason = f"unhandled:{type(error).__name__}"
        exit_code = 1
        logger.exception("未処理例外により終了します")
        raise
    finally:
        elapsed = time.monotonic() - _process_started_at
        logger.info(
            "プロセス終了: command=%s reason=%s exit_code=%s elapsed=%.2fs",
            args.command, _process_exit_reason, exit_code, elapsed,
        )
        _flush_logs()


if __name__ == "__main__":
    main()
