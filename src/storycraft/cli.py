"""次世代Storycraftのコマンドライン。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from .config import Settings
from .series_engine import ContractError, SeriesService
from .series_model import OpenAIStoryModel


def _load_brief(path: str) -> dict[str, Any]:
    source = Path(path)
    if not source.exists():
        raise ContractError(f"企画ファイルが見つかりません: {source}")
    text = source.read_text(encoding="utf-8")
    value = json.loads(text) if source.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ContractError("企画ファイルはJSONまたはYAMLのオブジェクトでなければなりません")
    return value


def _service_and_model(args) -> tuple[SeriesService, OpenAIStoryModel]:
    settings = Settings.load(args.config)
    workspace = settings.resolve_output_dir(args.out)
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
    try:
        args.handler(args)
    except ContractError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
