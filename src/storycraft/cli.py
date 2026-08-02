"""docs 契約だけを公開する v2 CLI。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

from .run_state import RunStateStore
from .series_contracts import ContractError
from .workspace import create_workspace, validate_workspace
from .workflow import RunUnavailable, run
from .workspace_lock import WorkspaceLockBusy


class ValidationFailed(ContractError):
    pass


class CliArgumentError(ContractError):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise CliArgumentError(message)


def _load_object(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("入力JSONを読めません") from exc
    if not isinstance(value, dict):
        raise ContractError("入力JSONはobjectでなければなりません")
    return value


def _pending_summary(pending: object) -> dict[str, object] | None:
    if pending is None:
        return None
    if not isinstance(pending, dict):
        raise ContractError("pending_commitが不正です")
    targets = pending.get("targets")
    if not isinstance(targets, list):
        raise ContractError("pending_commit targetsが不正です")
    return {
        "kind": pending["kind"],
        "pending_target_count": sum(t.get("status") == "pending" for t in targets if isinstance(t, dict)),
        "finalized_target_count": sum(t.get("status") == "finalized" for t in targets if isinstance(t, dict)),
    }


def _common(state: dict[str, Any]) -> dict[str, object]:
    completed = state["status"] == "completed"
    return {
        "workspace_id": state["workspace_id"],
        "status": state["status"],
        "current_stage": state["current_stage"],
        "current_target": None if completed else state["current_target"],
        "current_selection_id": state["current_selection_id"],
        "last_error": state["last_error"],
        "pending_commit": None if completed else _pending_summary(state["pending_commit"]),
    }


def cmd_init(args: argparse.Namespace) -> dict[str, object]:
    request = _load_object(args.request) if args.request else None
    keywords = _load_object(args.keywords) if args.keywords else None
    settings = _load_object(args.config)
    root = Path(args.workspace).expanduser()
    create_workspace(
        root,
        workspace_id=args.workspace_id or f"ws-{root.name}",
        request=request,
        keywords=keywords,
        settings=settings,
        created_at="2026-07-29T00:00:00Z",
    )
    state = RunStateStore(root).load()
    # V1 spec: init returns workspace_id, status=created, current_selection_id (no run_id)
    return {
        "workspace_id": state["workspace_id"],
        "status": "created",
        "current_selection_id": state["current_selection_id"],
    }


def cmd_status(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.workspace).expanduser()
    state = RunStateStore(root).load()
    return _common(state)


def cmd_validate(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.workspace).expanduser()
    state = RunStateStore(root).load()
    try:
        validate_workspace(root)
        passed = True
        detail = None
    except ContractError as exc:
        passed = False
        detail = str(exc)
    # validate_workspace は保存済み正本を包括検証する。成功時は契約上の5観点を
    # passed として公開し、失敗時は共通の validation_failed エラーを返す。
    checks = [
        {"name": "schema", "passed": passed},
        {"name": "id", "passed": passed},
        {"name": "reference", "passed": passed},
        {"name": "range", "passed": passed},
        {"name": "evidence", "passed": passed},
    ]
    if detail:
        checks[0]["detail"] = detail  # 最初の項目に詳細を入れる
    if not passed:
        raise ValidationFailed("validation_failed")
    return {**_common(state), "checks": checks}


def cmd_run(args: argparse.Namespace) -> dict[str, object]:
    """v2の保存済み確定を優先して収束し、公開工程を決定的に実行する。"""
    root = Path(args.workspace).expanduser()
    return _common(run(root))


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="storycraft")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--workspace", required=True)
    init.add_argument("--config", required=True)
    init.add_argument("--workspace-id")
    source = init.add_mutually_exclusive_group(required=True)
    source.add_argument("--request")
    source.add_argument("--keywords")
    init.add_argument("--json", action="store_true")
    for name in ("status", "validate", "run"):
        command = commands.add_parser(name)
        command.add_argument("--workspace", required=True)
        command.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.command == "init":
            result = cmd_init(args)
        elif args.command == "status":
            result = cmd_status(args)
        elif args.command == "validate":
            result = cmd_validate(args)
        else:
            result = cmd_run(args)
    except WorkspaceLockBusy as exc:
        _emit_error("lock_unavailable", str(exc))
        return 75
    except RunUnavailable as exc:
        code = str(exc) if str(exc) in _ERROR_CODES else "blocked"
        _emit_error(code, str(exc))
        return 4
    except ValidationFailed as exc:
        _emit_error("validation_failed", str(exc))
        return 5
    except ContractError as exc:
        _emit_error("invalid_argument", str(exc))
        return 2
    except Exception as exc:
        _emit_error("internal_error", str(exc))
        return 70
    if args.json:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        if args.command == "init":
            print(f"workspace created: {args.workspace}")
        else:
            print(f"workspace: {args.workspace} / status: {result['status']} / stage: {result.get('current_stage')} / target: {result.get('current_target')} / selection: {result.get('current_selection_id')}")
    return 0


_ERROR_CODES = {
    "invalid_argument", "blocked", "validation_failed", "internal_error",
    "lock_unavailable", "invalid_response_limit", "technical_retry_exhausted",
    "authority_inconsistency", "publication_invalid",
}


def _emit_error(code: str, message: str) -> None:
    print(json.dumps({"ok": False, "code": code, "message": message}, ensure_ascii=False, separators=(",", ":")), file=sys.stderr)


def console_main() -> None:
    """console_scripts 用の終了コード伝播境界。"""
    raise SystemExit(main())


if __name__ == "__main__":
    console_main()