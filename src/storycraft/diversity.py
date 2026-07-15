"""§3.0 過去作品との差別化。

- アーカイブ (archive_dir) から直近 recent_window 作品分の要素を抜粋
- 多様性目標として依頼文へ加える
- アーカイブが空、または作品数が recent_window 未満の場合は注入を省略
- 禁止語リストは入れない (象の問題回避)
"""
from __future__ import annotations

from pathlib import Path


def build_diversity_note(archive_dir: Path, recent_window: int) -> str | None:
    if not archive_dir.exists():
        return None
    files = sorted(
        (p for p in archive_dir.iterdir() if p.is_file() and p.suffix in (".md", ".txt", ".yaml", ".yml", ".json")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    recent = files[:recent_window]
    if not recent:
        return None
    excerpts = []
    for p in recent:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        # 長すぎる場合は先頭だけ
        if len(text) > 1500:
            text = text[:1500] + "…(省略)"
        excerpts.append(f"### {p.stem}\n{text}")
    joined = "\n\n".join(excerpts)
    return (
        "【過去作品との差別化目標】\n"
        "以下は過去作品の役割配置・舞台・骨子の抜粋である。\n"
        "これらと構造が異なる前提・配置を立てること。個別の禁止語リストは与えない。\n\n"
        f"{joined}\n"
    )
