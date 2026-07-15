"""Markdown出力。§8 に従う。

output/
  volume-01.md ...
  series.md
各巻に巻題・章題・本文を含める。series.md は全巻を順番に収録。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_scenes(scene_dir: Path, vol: int, ch: int) -> list[dict]:
    d = scene_dir / f"volume-{vol:02d}" / f"chapter-{ch:02d}"
    out = []
    if not d.exists():
        return out
    for p in sorted(d.glob("scene-*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def build_volume_markdown(plan: dict, chapters: list, scene_dir: Path, vol: int) -> str:
    vol_plan = next((v for v in plan.get("volumes", []) if v.get("number") == vol), {})
    lines = [f"# 第{vol}巻 {vol_plan.get('title', '')}", ""]
    for ch in chapters:
        ch_num = ch.get("chapter_number")
        lines.append(f"## 第{ch_num}章 {ch.get('title', '')}")
        lines.append("")
        scenes = _load_scenes(scene_dir, vol, ch_num)
        for sc in scenes:
            content = sc.get("content", "")
            lines.append(content)
            lines.append("")
    return "\n".join(lines)


def build_series_markdown(plan: dict, all_chapters: dict, scene_dir: Path, vol_count: int) -> str:
    parts = ["# シリーズ全体", ""]
    for vol in range(1, vol_count + 1):
        chapters = all_chapters.get(vol, [])
        parts.append(build_volume_markdown(plan, chapters, scene_dir, vol))
        parts.append("")
    return "\n".join(parts)


def write_output(state: Any, out_root: Path) -> None:
    plan = state.load_json("series_plan") or {}
    vol_count = plan.get("volume_count", 0)
    chapters_by_vol: dict[int, list] = {}
    for vol in range(1, vol_count + 1):
        chapters = state.load_json(f"volume_{vol:02d}_chapters")
        chapters_by_vol[vol] = chapters.get("chapters", []) if isinstance(chapters, dict) else []
    out_root.mkdir(parents=True, exist_ok=True)
    for vol in range(1, vol_count + 1):
        md = build_volume_markdown(plan, chapters_by_vol.get(vol, []), state.scene_dir, vol)
        (out_root / f"volume-{vol:02d}.md").write_text(md, encoding="utf-8")
    series = build_series_markdown(plan, chapters_by_vol, state.scene_dir, vol_count)
    (out_root / "series.md").write_text(series, encoding="utf-8")
