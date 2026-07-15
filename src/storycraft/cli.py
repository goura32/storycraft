"""コマンドライン。§10 に従う。

run    : 一括実行（続きからでも開始。完了済みステージはスキップ）
resume : 保存状態から続きを実行（--out のみ、--brief は不要）
step   : 未完了の最初のステージを1つ実行 / --stage で指定ステージを強制1実行
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Settings
from .ids import IDSequencer
from .log import add_file_handler, logger
from .llm import LLMClient
from .pipeline import Pipeline, STAGES
from .state import State


def _build(brief_path: str | None, out: str | None, config_path: str | None):
    settings = Settings.load(config_path)
    out_root = settings.resolve_output_dir(out)
    out_root.mkdir(parents=True, exist_ok=True)
    state = State.load(out_root / "state")
    add_file_handler(out_root / "state" / "log" / "run.log")
    llm = LLMClient(settings, state.raw_dir)
    seq = IDSequencer(state.root)
    pipe = Pipeline(settings, state, llm, seq)
    if brief_path:
        p = Path(brief_path)
        if not p.exists():
            logger.error("企画ファイルが見つかりません: %s", brief_path)
            sys.exit(1)
        import json
        state.data["brief"] = json.loads(p.read_text(encoding="utf-8"))
        state.save()
    return settings, out_root, state, pipe


def _next_stage(state: State) -> str | None:
    for st in STAGES:
        if not state.is_stage_done(st):
            return st
    return None


def cmd_run(args) -> None:
    settings, out_root, state, pipe = _build(args.brief, args.out, args.config)
    _run_full(pipe, state, out_root, args)


def cmd_resume(args) -> None:
    settings, out_root, state, pipe = _build(None, args.out, args.config)
    if not state.data.get("brief") and "brief" not in state.data:
        # brief が無い場合は state.json から復元を試みる
        pass
    _run_full(pipe, state, out_root, args)


def _run_full(pipe: Pipeline, state: State, out_root: Path, args) -> None:
    # 巻ループの再開地点を決定
    plan = state.load_json("series_plan")
    vol_count = plan.get("volume_count", 0) if plan else 0
    start_vol = 1
    if vol_count:
        for v in range(1, vol_count + 1):
            if not state.is_stage_done(f"volplan-{v}"):
                start_vol = v
                break

    # グローバルステージ
    for st in ("plan", "characters", "world", "timeline", "threads"):
        if not state.is_stage_done(st):
            if not getattr(pipe, f"stage_{st}")():
                logger.error("ステージ %s が失敗しました。停止。", st)
                return
            state.set_stage_done(st)

    if not vol_count:
        logger.error("全巻計画が未作成です。")
        return

    for vol in range(start_vol, vol_count + 1):
        if not state.is_stage_done(f"volplan-{vol}"):
            if not pipe.stage_volume_plan(vol):
                logger.error("巻計画 %d が失敗しました。", vol)
                return
            state.set_stage_done(f"volplan-{vol}")
        chapters = state.load_json(f"volume_{vol:02d}_chapters")
        for ch in chapters.get("chapters", []):
            ch_num = ch.get("chapter_number")
            if not state.is_stage_done(f"cards-{vol}.{ch_num}"):
                if not pipe.stage_scene_cards(vol, ch_num):
                    logger.error("場面カード vol%d ch%d が失敗しました。", vol, ch_num)
                    return
                state.set_stage_done(f"cards-{vol}.{ch_num}")
            if not state.is_stage_done(f"scenes-{vol}.{ch_num}"):
                if not pipe.stage_scenes(vol, ch_num):
                    logger.error("場面生成 vol%d ch%d が失敗しました。停止。", vol, ch_num)
                    return
                state.set_stage_done(f"scenes-{vol}.{ch_num}")
        if not state.is_stage_done(f"volsum-{vol}"):
            if not pipe.stage_volume_summary(vol):
                logger.error("巻要約 %d が失敗しました。", vol)
                return
            state.set_stage_done(f"volsum-{vol}")

    if not state.is_stage_done("closure"):
        if not pipe.stage_closure_check():
            logger.error("完結前確認が失敗: %s", state.data.get("stop_reason"))
            return
        state.set_stage_done("closure")

    if not state.is_stage_done("output"):
        pipe.stage_output(out_root)
        state.set_stage_done("output")
    logger.info("完了しました。出力: %s", out_root)


def cmd_step(args) -> None:
    settings, out_root, state, pipe = _build(args.brief, args.out, args.config)
    target = args.stage
    if target:
        # 指定ステージを強制1実行
        if target == "scenes" and (args.chapter or args.chapter_range):
            _run_scenes_forced(pipe, state, args)
        else:
            ok = _run_single_stage(pipe, state, target)
            if not ok:
                logger.error("ステージ %s が失敗しました。", target)
                return
        state.set_stage_done(target)
        logger.info("ステージ %s を実行しました。", target)
        return

    nxt = _next_stage(state)
    if not nxt:
        logger.info("すべてのステージが完了しています。")
        return
    ok = _run_single_stage(pipe, state, nxt)
    if not ok:
        logger.error("ステージ %s が失敗しました。", nxt)
        return
    state.set_stage_done(nxt)
    logger.info("ステージ %s を実行しました。次は %s", nxt, _next_stage(state))


def _run_scenes_forced(pipe, state, args) -> None:
    vol = args.chapter or 1
    chapters = state.load_json(f"volume_{vol:02d}_chapters")
    ch_nums = [c["chapter_number"] for c in chapters.get("chapters", [])]
    if not ch_nums:
        logger.error("巻 %d の章がありません。", vol)
        return
    ch = ch_nums[0]
    rng = None
    if args.chapter_range:
        lo, hi = (int(x) for x in args.chapter_range.split("-"))
        rng = (lo, hi)
    pipe.stage_scenes(vol, ch, rng)


def _run_single_stage(pipe: Pipeline, state: State, target: str) -> bool:
    if target in ("plan", "characters", "world", "timeline", "threads"):
        return getattr(pipe, f"stage_{target}")()
    if target == "output":
        return pipe.stage_output(state.root.parent)
    if target == "closure":
        return pipe.stage_closure_check()
    if target.startswith("volplan-"):
        vol = int(target.split("-")[1])
        return pipe.stage_volume_plan(vol)
    if target.startswith("cards-"):
        _, rest = target.split("-", 1)
        vol, ch = rest.split(".")
        return pipe.stage_scene_cards(int(vol), int(ch))
    if target.startswith("scenes-"):
        _, rest = target.split("-", 1)
        vol, ch = rest.split(".")
        return pipe.stage_scenes(int(vol), int(ch))
    if target.startswith("volsum-"):
        vol = int(target.split("-")[1])
        return pipe.stage_volume_summary(vol)
    logger.warning("未知のステージ: %s", target)
    return False


def main() -> None:
    ap = argparse.ArgumentParser(prog="storycraft", description="LLM小説シリーズ生成")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="一括実行")
    p_run.add_argument("--brief", required=True, help="初回企画JSON")
    p_run.add_argument("--out", default=None, help="作業ディレクトリ")
    p_run.add_argument("--config", default=None, help="config.yaml")
    p_run.set_defaults(func=cmd_run)

    p_res = sub.add_parser("resume", help="続きから再開")
    p_res.add_argument("--out", required=True, help="作業ディレクトリ")
    p_res.add_argument("--config", default=None, help="config.yaml")
    p_res.set_defaults(func=cmd_resume)

    p_step = sub.add_parser("step", help="1ステージ確認実行")
    p_step.add_argument("--out", required=True, help="作業ディレクトリ")
    p_step.add_argument("--brief", default=None, help="初回企画JSON（初回のみ）")
    p_step.add_argument("--config", default=None, help="config.yaml")
    p_step.add_argument("--stage", default=None, help="強制実行するステージ名")
    p_step.add_argument("--chapter", type=int, default=None, help="対象巻 (scenes用)")
    p_step.add_argument("--chapter-range", default=None, help="場面範囲 M-N (scenes用)")
    p_step.set_defaults(func=cmd_step)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
