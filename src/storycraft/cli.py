"""Storycraft V1のコマンドライン。"""
from __future__ import annotations

import argparse
from collections.abc import Callable
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import time
from typing import Any

import yaml

from .config import Settings
from .log import add_file_handler, logger
from .run_state import RunStateStore
from .series_contracts import ContractError, StoryModel
from .series_model import OpenAIStoryModel
from .v1_workflow import V1WorkflowService
from .workspace import create_workspace


ModelFactory = Callable[[], StoryModel]

ACTIVE_RUN_STATUSES = frozenset({
    "initializing",
    "running",
})

TERMINAL_RUN_STATUSES = frozenset({
    "stopped",
    "blocked",
    "failed",
    "completed",
})

_process_started_at: float | None = None
_process_exit_reason = "normal"


def _flush_logs() -> None:
    """終了直前のログをファイルへ確実に反映する。"""
    for handler in logger.handlers:
        handler.flush()


def _handle_termination_signal(
    signum: int,
    _frame: Any,
) -> None:
    """SIGTERMを無言で終わらせず終了記録を残す。"""
    global _process_exit_reason

    signal_name = signal.Signals(signum).name
    _process_exit_reason = f"signal:{signal_name}"

    logger.warning(
        "終了シグナル受信: %s。終了処理を開始します",
        signal_name,
    )
    _flush_logs()
    raise SystemExit(128 + signum)


def _load_object(
    path: str,
    *,
    label: str,
) -> dict[str, Any]:
    source = Path(path).expanduser()

    if not source.is_file():
        raise ContractError(
            f"{label}ファイルが見つかりません: {source}"
        )

    try:
        text = source.read_text(encoding="utf-8")
        value = (
            json.loads(text)
            if source.suffix.lower() == ".json"
            else yaml.safe_load(text)
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ContractError(
            f"{label}ファイルを読み込めません: {source}"
        ) from exc
    except yaml.YAMLError as exc:
        raise ContractError(
            f"{label} YAMLを解析できません: {source}"
        ) from exc

    if not isinstance(value, dict):
        raise ContractError(
            f"{label}ファイルはJSONまたはYAMLの"
            "オブジェクトでなければなりません"
        )

    return value


def _load_brief(path: str) -> dict[str, Any]:
    return _load_object(path, label="企画")


def _load_keywords_file(
    path: str,
) -> dict[str, Any]:
    return _load_object(path, label="Keywords")


def _setup_logging(workspace: Path) -> None:
    """V1 workspaceのlogs directoryへ出力する。"""
    log_path = workspace / "logs/storycraft.log"

    add_file_handler(log_path)

    logger.info("ログ出力先: %s", log_path)
    logger.info(
        "プロセス監視開始: pid=%s workspace=%s",
        os.getpid(),
        workspace,
    )


def _workspace_config(
    settings: Settings,
) -> dict[str, Any]:
    """外部SettingsをV1 workspace configへ写像する。"""
    return {
        "language": "ja",
        "llm": deepcopy(settings.llm),
        "retry": deepcopy(settings.retry),
        "quality": deepcopy(settings.quality),
        "diversity": deepcopy(settings.diversity),
    }


def _default_workspace_id(
    workspace: Path,
) -> str:
    """出力pathから安全で安定したworkspace IDを作る。"""
    normalized = re.sub(
        r"[^a-z0-9_-]+",
        "-",
        workspace.name.lower(),
    ).strip("-_")

    readable = normalized[:48] or "workspace"

    digest = hashlib.sha256(
        str(workspace.absolute()).encode("utf-8")
    ).hexdigest()[:8]

    return f"ws-{readable}-{digest}"


def _keywords_payload(
    args: argparse.Namespace,
) -> dict[str, Any]:
    if args.keywords_file:
        return _load_keywords_file(
            args.keywords_file
        )

    values = [
        value.strip()
        for value in (args.keywords or [])
        if (
            isinstance(value, str)
            and value.strip()
        )
    ]
    avoid = [
        value.strip()
        for value in (args.avoid or [])
        if (
            isinstance(value, str)
            and value.strip()
        )
    ]

    payload: dict[str, Any] = {
        "schema_version": 1,
        "source_type": "keywords",
        "keywords": values,
        "avoid": avoid,
        "ending_preference": (
            args.ending_preference
        ),
        "volume_hint": args.volume_hint,
        "language": "ja",
    }

    if args.notes is not None:
        payload["notes"] = args.notes

    return payload


def _workspace_kind(
    workspace: Path,
) -> str:
    """pathをV1、旧形式、混在、未知へ分類する。"""
    if (
        not workspace.exists()
        and not workspace.is_symlink()
    ):
        return "absent"

    if (
        workspace.is_symlink()
        or not workspace.is_dir()
    ):
        return "invalid"

    v1 = (
        workspace / "runtime/run-state.json"
    ).is_file()
    legacy = (
        workspace / "state.json"
    ).exists()

    if v1 and legacy:
        return "mixed"
    if v1:
        return "v1"
    if legacy:
        return "legacy"

    return "unknown"


def _require_new_workspace(
    workspace: Path,
) -> None:
    kind = _workspace_kind(workspace)

    if kind == "absent":
        return

    if kind == "mixed":
        raise ContractError(
            "旧state.jsonとV1 runtime/run-state.jsonが"
            "混在しています"
        )

    if kind == "legacy":
        raise ContractError(
            "旧形式workspaceには"
            "V1 runを実行できません"
        )

    if kind == "v1":
        raise ContractError(
            "V1 workspaceが既に存在します。"
            "resumeまたはstepを使用してください"
        )

    if kind == "invalid":
        raise ContractError(
            "workspace出力先は"
            "通常directory pathが必要です"
        )

    raise ContractError(
        "既存directoryはV1 workspaceではありません"
    )


def _require_existing_v1_workspace(
    workspace: Path,
) -> None:
    kind = _workspace_kind(workspace)

    if kind == "v1":
        return

    if kind == "mixed":
        raise ContractError(
            "旧state.jsonとV1 runtime/run-state.jsonが"
            "混在しています"
        )

    if kind == "legacy":
        raise ContractError(
            "旧形式workspaceは"
            "V1 CLIで再開できません"
        )

    if kind == "absent":
        raise ContractError(
            "V1 workspaceが存在しません。"
            "runを使用してください"
        )

    if kind == "invalid":
        raise ContractError(
            "workspace pathは"
            "通常directoryが必要です"
        )

    raise ContractError(
        "指定directoryはV1 workspaceではありません"
    )


def _make_model_factory(
    settings: Settings,
    workspace: Path,
) -> ModelFactory:
    """Provider Modelを必要になるまで生成しない。"""
    return lambda: OpenAIStoryModel(
        settings,
        workspace / "runtime/calls",
    )


def _workflow(
    settings: Settings,
    workspace: Path,
) -> V1WorkflowService:
    return V1WorkflowService(
        workspace,
        model_factory=_make_model_factory(
            settings,
            workspace,
        ),
    )


def _run_until_terminal(
    workflow: V1WorkflowService,
    workspace: Path,
) -> dict[str, Any]:
    """run-stateが停止するまでV1 Stageを反復する。"""
    state = RunStateStore(
        workspace
    ).load_recovery()

    while (
        state["status"]
        in ACTIVE_RUN_STATUSES
    ):
        previous = deepcopy(state)
        state = workflow.step()

        if state == previous:
            raise ContractError(
                "V1 Workflowがrun-stateを"
                "前進させませんでした"
            )

    return state


def _report(
    state: dict[str, Any],
    workspace: Path,
) -> None:
    status = state["status"]

    if status == "completed":
        publication_id = state[
            "current_publication_id"
        ]

        if not isinstance(
            publication_id,
            str,
        ):
            raise ContractError(
                "completed runに"
                "Publication IDがありません"
            )

        print(
            "完了: "
            + str(
                workspace
                / "publications"
                / publication_id
            )
        )
        return

    if status in TERMINAL_RUN_STATUSES:
        print(
            "停止: "
            f"status={status} "
            f"reason={state['stop_reason']}"
        )
        return

    print(
        "保存しました: "
        f"status={status} "
        f"stage={state['current_stage']}"
    )


def cmd_run(
    args: argparse.Namespace,
) -> None:
    settings = Settings.load(args.config)
    workspace = settings.resolve_output_dir(
        args.out
    ).expanduser()

    _require_new_workspace(workspace)

    brief = None
    keywords = None

    if args.brief:
        brief = _load_brief(args.brief)
    else:
        keywords = _keywords_payload(args)

    create_workspace(
        workspace,
        workspace_id=(
            args.workspace_id
            or _default_workspace_id(workspace)
        ),
        config=_workspace_config(settings),
        brief=brief,
        keywords=keywords,
    )

    _setup_logging(workspace)

    logger.info(
        "LLM設定: provider=%s model=%s",
        settings.llm.get(
            "provider",
            "ollama",
        ),
        settings.llm.get(
            "model",
            "unknown",
        ),
    )

    state = _run_until_terminal(
        _workflow(settings, workspace),
        workspace,
    )
    _report(state, workspace)


def cmd_resume(
    args: argparse.Namespace,
) -> None:
    settings = Settings.load(args.config)
    workspace = settings.resolve_output_dir(
        args.out
    ).expanduser()

    _require_existing_v1_workspace(
        workspace
    )
    _setup_logging(workspace)

    logger.info(
        "LLM設定: provider=%s model=%s",
        settings.llm.get(
            "provider",
            "ollama",
        ),
        settings.llm.get(
            "model",
            "unknown",
        ),
    )

    state = _run_until_terminal(
        _workflow(settings, workspace),
        workspace,
    )
    _report(state, workspace)


def cmd_step(
    args: argparse.Namespace,
) -> None:
    settings = Settings.load(args.config)
    workspace = settings.resolve_output_dir(
        args.out
    ).expanduser()

    _require_existing_v1_workspace(
        workspace
    )
    _setup_logging(workspace)

    logger.info(
        "LLM設定: provider=%s model=%s",
        settings.llm.get(
            "provider",
            "ollama",
        ),
        settings.llm.get(
            "model",
            "unknown",
        ),
    )

    state = _workflow(
        settings,
        workspace,
    ).step()

    _report(state, workspace)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="storycraft",
        description="日本語小説シリーズ生成",
    )
    subcommands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run = subcommands.add_parser("run")
    run.add_argument(
        "--out",
        required=True,
        help="新規V1 workspace",
    )
    run.add_argument(
        "--config",
        default=None,
        help="設定YAML",
    )
    run.add_argument(
        "--workspace-id",
        default=None,
        help="ws-で始まるworkspace ID",
    )

    initial = (
        run.add_mutually_exclusive_group(
            required=True
        )
    )
    initial.add_argument(
        "--brief",
        help="人が作成した初回企画JSONまたはYAML",
    )
    initial.add_argument(
        "--keywords-file",
        help="V1 Keywords JSONまたはYAML",
    )
    initial.add_argument(
        "--keywords",
        action="append",
        help=(
            "Brief生成用keyword。"
            "複数回指定可能"
        ),
    )

    run.add_argument(
        "--avoid",
        action="append",
        default=[],
        help="避ける要素。複数回指定可能",
    )
    run.add_argument(
        "--ending-preference",
        default="救いのある結末",
        help="結末の希望",
    )
    run.add_argument(
        "--volume-hint",
        type=int,
        default=4,
        help="希望巻数。4から10",
    )
    run.add_argument(
        "--notes",
        default=None,
        help="任意の補足",
    )
    run.set_defaults(handler=cmd_run)

    for name, handler in (
        ("resume", cmd_resume),
        ("step", cmd_step),
    ):
        command = subcommands.add_parser(name)
        command.add_argument(
            "--out",
            required=True,
            help="既存V1 workspace",
        )
        command.add_argument(
            "--config",
            default=None,
            help="設定YAML",
        )
        command.set_defaults(
            handler=handler
        )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    global _process_started_at
    global _process_exit_reason

    _process_started_at = time.monotonic()
    _process_exit_reason = "normal"

    signal.signal(
        signal.SIGTERM,
        _handle_termination_signal,
    )

    exit_code = 0

    try:
        args.handler(args)
    except KeyboardInterrupt:
        _process_exit_reason = (
            "keyboard_interrupt"
        )
        exit_code = 130
        logger.warning(
            "ユーザー中断を受信しました"
        )
        raise
    except ContractError as error:
        _process_exit_reason = (
            "contract_error"
        )
        exit_code = 2
        logger.error(
            "契約エラーにより終了します: %s",
            error,
        )
        parser.error(str(error))
    except SystemExit as error:
        exit_code = (
            int(error.code)
            if isinstance(error.code, int)
            else 1
        )
        if _process_exit_reason == "normal":
            _process_exit_reason = (
                "system_exit"
            )
        raise
    except BaseException as error:  # noqa: BLE001
        _process_exit_reason = (
            f"unhandled:{type(error).__name__}"
        )
        exit_code = 1
        logger.exception(
            "未処理例外により終了します"
        )
        raise
    finally:
        elapsed = (
            time.monotonic()
            - _process_started_at
        )

        logger.info(
            "プロセス終了: command=%s "
            "reason=%s exit_code=%s "
            "elapsed=%.2fs",
            args.command,
            _process_exit_reason,
            exit_code,
            elapsed,
        )
        _flush_logs()


if __name__ == "__main__":
    main()
