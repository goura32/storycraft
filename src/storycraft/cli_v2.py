"""docs 契約だけを公開する v2 CLI。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .run_state import RunStateStore
from .series_contracts import ContractError
from .workspace_v2 import create_v2_workspace, validate_v2_workspace
from .workflow_v2 import RunUnavailable, run_v2
from .workspace_lock import WorkspaceLockBusy


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
    return {"kind": pending["kind"], "pending_target_count": sum(target.get("status") == "pending" for target in targets if isinstance(target, dict)), "finalized_target_count": sum(target.get("status") == "finalized" for target in targets if isinstance(target, dict))}


def _common(state: dict[str, Any]) -> dict[str, object]:
    return {"workspace_id": state["workspace_id"], "status": state["status"], "current_stage": state["current_stage"], "current_target": state["current_target"], "current_selection_id": state["current_selection_id"], "stop_reason": state["stop_reason"], "pending_commit": _pending_summary(state["pending_commit"])}


def cmd_init(args: argparse.Namespace) -> dict[str, object]:
    request = _load_object(args.request or args.keywords)
    settings = _load_object(args.config)
    root = Path(args.workspace).expanduser()
    create_v2_workspace(root, workspace_id=args.workspace_id or f"ws-{root.name}", request=request, settings=settings, created_at="2026-07-29T00:00:00Z")
    state = RunStateStore(root).load()
    return {"workspace_id": state["workspace_id"], "status": "created", "run_id": state["run_id"], "current_selection_id": state["current_selection_id"]}


def cmd_status(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.workspace).expanduser()
    state = RunStateStore(root).load()
    return {**_common(state), "runtime_lock": None, "run_state_path": "runtime/run-state.json", "manifest_path": None}


def cmd_validate(args: argparse.Namespace) -> dict[str, object]:
    root = Path(args.workspace).expanduser()
    try:
        validate_v2_workspace(root)
        passed, detail = True, None
    except ContractError as exc:
        passed, detail = False, str(exc)
    state = RunStateStore(root).load_recovery()
    result = {**_common(state), "checks": [{"name": "v2_workspace", "passed": passed}]}
    if detail:
        result["checks"][0]["detail"] = detail  # type: ignore[index]
    if not passed:
        raise ContractError("validation_failed")
    return result


def cmd_run(args: argparse.Namespace) -> dict[str, object]:
    """v2の保存済み確定を優先して収束し、公開工程を決定的に実行する。"""
    return _common(run_v2(Path(args.workspace).expanduser()))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storycraft")
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
    args = _parser().parse_args(argv)
    try:
        if args.command == "init": result = cmd_init(args)
        elif args.command == "status": result = cmd_status(args)
        elif args.command == "validate": result = cmd_validate(args)
        else: result = cmd_run(args)
    except WorkspaceLockBusy as exc:
        print(json.dumps({"ok": False, "code": "locked", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 75
    except RunUnavailable as exc:
        print(json.dumps({"ok": False, "code": "blocked", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 4
    except ContractError as exc:
        print(json.dumps({"ok": False, "code": "invalid_argument", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(f"workspace={result['workspace_id']} status={result['status']} stage={result.get('current_stage')}")
    return 0

def console_main() -> None:
    """console_scripts 用の終了コード伝播境界。"""
    raise SystemExit(main())


if __name__ == "__main__":
    console_main()
