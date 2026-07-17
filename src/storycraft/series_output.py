"""完成したシリーズ原稿の検証と原子的出力。"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from .series_contracts import ContractError


class OutputWriter:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    @staticmethod
    def _scene_id(volume: int, chapter: int, scene: int) -> str:
        return f"v{volume:02d}-c{chapter:02d}-s{scene:02d}"

    def validate_manuscript_state(self, state: dict[str, Any]) -> None:
        expected: set[str] = set()
        for volume_number in range(1, len(state["plan"]["volumes"]) + 1):
            chapters = state["chapters"].get(str(volume_number))
            if not isinstance(chapters, list) or not chapters:
                raise ContractError("必要な章がありません")
            for chapter in chapters:
                for scene_number in range(1, chapter["scene_count"] + 1):
                    expected.add(self._scene_id(volume_number, chapter["number"], scene_number))
        scenes = state["scenes"]
        actual = {scene.get("scene_id") for scene in scenes if isinstance(scene, dict)}
        if actual != expected:
            raise ContractError("必要な場面が欠落または不正です")
        contents = [scene.get("content") for scene in scenes]
        if not all(isinstance(content, str) and content.strip() for content in contents):
            raise ContractError("空本文があります")
        if len(contents) != len(set(contents)):
            raise ContractError("場面本文が重複しています")

    def write(self, state: dict[str, Any]) -> list[Path]:
        self.validate_manuscript_state(state)
        self.workspace.mkdir(parents=True, exist_ok=True)
        output = self.workspace / "output"
        staging = Path(tempfile.mkdtemp(prefix=".output-", dir=self.workspace))
        paths: list[Path] = []
        try:
            for volume_number, volume in enumerate(state["plan"]["volumes"], 1):
                chapters = {chapter["number"]: chapter["title"] for chapter in state["chapters"][str(volume_number)]}
                scenes = [scene for scene in state["scenes"] if scene["volume"] == volume_number]
                lines = [f"# 第{volume_number}巻 {volume['title']}", "<!-- 無料導入巻 -->" if volume_number == 1 else "<!-- 販売対象巻 -->", ""]
                current = None
                for scene in scenes:
                    if current != scene["chapter"]:
                        current = scene["chapter"]
                        lines.extend([f"## 第{current}章 {chapters[current]}", ""])
                    lines.extend([scene["content"], ""])
                path = staging / f"volume-{volume_number:02d}.md"
                path.write_text("\n".join(lines), encoding="utf-8")
                paths.append(path)
            series = staging / "series.md"
            series.write_text("\n\n".join(path.read_text(encoding="utf-8") for path in paths), encoding="utf-8")
            self.validate_output(paths, series)
            backup = self.workspace / ".output-previous"
            if backup.exists():
                shutil.rmtree(backup)
            if output.exists():
                output.replace(backup)
            staging.replace(output)
            if backup.exists():
                shutil.rmtree(backup)
            return [output / path.name for path in paths]
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise

    @staticmethod
    def validate_output(paths: list[Path], series: Path) -> None:
        bodies = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if "## 第" not in text:
                raise ContractError(f"必要な章がない出力です: {path.name}")
            body = "\n".join(line for line in text.splitlines() if not line.startswith("#") and not line.startswith("<!--")).strip()
            if not body:
                raise ContractError(f"空本文の出力です: {path.name}")
            bodies.append(body)
        if len(bodies) != len(set(bodies)):
            raise ContractError("巻本文が重複しています")
        if not series.exists() or not series.read_text(encoding="utf-8").strip():
            raise ContractError("全巻Markdownがありません")
