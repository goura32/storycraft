"""統合テスト: run メインループを LLM stub で走らせ、全ステージを通して出力まで到達することを確認。

実LLM呼び出しをしない。Pipeline._ask を stub し、各ステージキーに対して
妥当な JSON フィクスチャを返す。これで _run_full の巻ループ起動〜output までの
オーケストレーションが from-scratch で閉じることを証明する。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# テスト対象を import する前に stub を当てるため、ここでパッチを仕込む
FIX = {
    "plan": {
        "volume_count": 2,
        "volumes": [
            {"number": 1, "title": "霧の端点の灯", "premise": "灯台守の娘の物語",
             "main_threads": ["thread-01"], "arc": "喪失と再構築"},
            {"number": 2, "title": "霧晴れの灯", "premise": "真実の受容",
             "main_threads": ["thread-01"], "arc": "再構築と平和"},
        ],
    },
    "characters": {
        "characters": [
            {"name": "アヤ", "role": "主人公", "traits": ["慎重"], "goal": "父の真実を知る",
             "conflict": "記憶の欠落", "relationships": []}
        ],
        "relationships": [],
    },
    "world": {
        "entities": [
            {"name": "灯台", "kind": "場所", "description": "島の灯台"}
        ],
    },
    "timeline": {
        "events": [
            {"name": "祭礼", "description": "島の年中行事"}
        ],
    },
    "threads": {
        "threads": [
            {"id": "thread-01", "name": "父の真実", "kind": "長期",
             "setup_location": "灯台", "resolution_location": "灯台", "status": "未回収"}
        ],
    },
    "volplan": {
        "chapters": [
            {"chapter_number": 1, "title": "白煙と灯台の影", "summary": "朝の点灯",
             "key_events": [], "characters_present": ["char-01"], "pov": "char-01",
             "ending_hook": ""}
        ],
    },
    "cards": {
        "scene_cards": [
            {
                "scene_number": 1,
                "viewpoint_character": "アヤ",
                "start_time": "time-01",
                "end_time": "time-01",
                "location_id": "entity-01",
                "entity_ids": ["entity-01"],
                "purpose": "朝の点灯",
                "opening": "螺旋階段を上がる",
                "required_events": [],
                "characters": ["アヤ"],
                "thread_actions": [{"id": "thread-01", "action": "導入"}],
                "reader_disclosure": "父の手順表の存在",
                "presentation_rules": ["過去の記憶は触れない"],
                "end_change": "点灯完了",
            }
        ],
    },
    "scenes": {
        "scene_number": 1, "title": "朝の点灯", "pov": "char-01",
        "time_ref": "time-01", "location_ref": "entity-01",
        "characters_present": ["char-01"],
        "handoff_summary": "朝の点灯で父の手順表を提示。",
        "thread_updates": [],
        "character_updates": [],
        "relationship_updates": [],
        "entity_updates": [],
        "timeline_updates": [],
        "content": "潮の香りが床板の間から染み込み、灯台のレンズが回転し始める低鳴りだけが発信する朝だった。娘は鉄製の手桶を両手で抱え、螺旋階段を上がった。足音が乾いた金属に響き、層状に残る煤の粉が舞う。予備タンクの栓を外すと、錆びたネジが軋んで緩む。粘性の高い灯油が注ぎ込まれる音だけを確認する。",
    },
    "volsum": {
        "handoff": "第1章では灯台の朝の点灯を描き、父の残した手順表を提示した。",
    },
    "closure": {
        "results": [
            {"thread_id": "thread-01", "status": "回収", "scene": "scenes-1.1.sc1"}
        ],
    },
}


def _fake_ask(self, kind, phase, ref, sys_p, user_p, schema, validator=None, allowed_ids=None, max_attempts=None, log_prefix=None):
    # 実際の _ask(self, kind, phase, ref, sys_p, user_p, schema, validator=None, allowed_ids=None, max_attempts=None)
    # ref は unit 名: "series" / "all" / "chapters" / "cards" / "sc1" / "summary" / "check"
    if ref == "series":
        return FIX["plan"]
    if ref == "all":
        # characters / world / timeline / threads は kind で区別
        return FIX.get(kind)
    if ref == "chapters":
        # 巻計画
        return FIX["volplan"]
    if ref == "cards":
        # 場面カード
        return FIX["cards"]
    if ref == "sc1" or ref.startswith("sc1."):
        # 場面生成 (改善パスも "sc1.p1" 等)
        return FIX["scenes"]
    if ref == "summary":
        return FIX["volsum"]
    if ref == "check":
        return FIX["closure"]
    raise AssertionError(f"no fixture for kind={kind!r} phase={phase!r} ref={ref!r}")


def main() -> int:
    from storycraft import pipeline
    from storycraft.cli import main as cli_main
    from storycraft.state import State

    pipeline.Pipeline._ask = _fake_ask  # type: ignore[assignment]

    tmp = Path(tempfile.mkdtemp(prefix="sc_run_"))
    out = tmp / "out"
    brief = tmp / "brief.json"
    brief.write_text(json.dumps({
        "genre": "ファンタジー", "target_audience": "成人女性",
        "tone": "叙情的", "themes": ["記憶"], "setting": "霧の島",
        "logline": "灯台守の娘", "must_include": ["灯台"], "must_avoid": ["銃"],
        "length_target": "1巻", "ending": "娘が選ぶ",
    }, ensure_ascii=False), encoding="utf-8")

    sys.argv = ["storycraft", "run", "--brief", str(brief), "--out", str(out)]
    try:
        cli_main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(f"FAIL: cli exited {e.code}")
            return 1

    # 検証
    state = State.load(out / "state")
    required_done = ["plan", "characters", "world", "timeline", "threads",
                     "volplan-1", "cards-1.1", "scenes-1.1", "volsum-1",
                     "volplan-2", "cards-2.1", "scenes-2.1", "volsum-2",
                     "closure", "output"]
    missing = [s for s in required_done if not state.is_stage_done(s)]
    if missing:
        print(f"FAIL: 未完了ステージ: {missing}")
        print("stages_done:", state.data.get("stages_done"))
        return 1

    vol_md = out / "volume-01.md"
    vol2_md = out / "volume-02.md"
    series_md = out / "series.md"
    if not vol_md.exists() or not vol2_md.exists() or not series_md.exists():
        print(f"FAIL: 出力なし vol1={vol_md.exists()} vol2={vol2_md.exists()} series={series_md.exists()}")
        return 1

    content = vol_md.read_text(encoding="utf-8")
    content2 = vol2_md.read_text(encoding="utf-8")
    if "潮の香り" not in content or "潮の香り" not in content2:
        print("FAIL: 場面本文が Markdown に含まれない")
        return 1

    print("PASS: run メインループが from-scratch で全ステージを通し、Markdown を出力しました。")
    print(f"  output: {out}")
    print(f"  volume-01.md size: {vol_md.stat().st_size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
