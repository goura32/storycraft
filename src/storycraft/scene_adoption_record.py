"""Scene Commit再構築用のimmutableなScene採用記録。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from .immutable_directory import (
    finalize_immutable_directory,
)
from .reviewed_candidate_stage import (
    fsync_directory,
    read_json,
    write_json_new,
)
from .series_contracts import ContractError


_RECORD_FILES = {
    "scene-card.json",
    "prose.md",
    "continuity.json",
}


@dataclass(frozen=True)
class SceneAdoptionRecord:
    """Scene Commit入力として採用済みの三成果物。"""

    scene_card: dict[str, Any]
    prose: str
    continuity: dict[str, Any]


def scene_adoption_record_path(
    workspace_root: Path,
    scene_id: str,
) -> Path:
    """Scene IDに対応する採用記録pathを返す。"""
    _validate_scene_id(scene_id)
    return (
        workspace_root.expanduser()
        / "runtime/candidates/scene_continuity"
        / f"adopted-{scene_id}-v0001"
    )


def publish_scene_adoption_record(
    workspace_root: Path,
    *,
    scene_id: str,
    scene_card: dict[str, Any],
    prose: str,
    continuity: dict[str, Any],
) -> Path:
    """採用済みScene入力をimmutable directoryとして保存する。"""
    root = workspace_root.expanduser()
    final = scene_adoption_record_path(root, scene_id)
    parent = final.parent

    record = SceneAdoptionRecord(
        scene_card=deepcopy(scene_card),
        prose=prose,
        continuity=deepcopy(continuity),
    )
    _validate_record(record, scene_id)

    if final.exists() or final.is_symlink():
        existing = load_scene_adoption_record(
            root,
            scene_id,
        )
        if existing != record:
            raise ContractError(
                "既存のScene採用記録が予定内容と"
                "競合しています"
            )
        return final

    if parent.is_symlink() or not parent.is_dir():
        raise ContractError(
            "Scene Continuity Candidate directoryが"
            "存在しません"
        )

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".adopted-{scene_id}-",
            dir=parent,
        )
    )

    try:
        write_json_new(
            staging / "scene-card.json",
            record.scene_card,
        )
        _write_text_new(
            staging / "prose.md",
            record.prose,
        )
        write_json_new(
            staging / "continuity.json",
            record.continuity,
        )
        fsync_directory(staging)

        validator = lambda path: (
            _validate_record_directory(
                path,
                scene_id=scene_id,
                expected=record,
            )
        )

        finalize_immutable_directory(
            staging=staging,
            final=final,
            validator=validator,
        )
        return final
    except Exception:
        # rename後の検証失敗ではfinalを削除しない。
        if staging.exists():
            shutil.rmtree(staging)
        raise


def load_scene_adoption_record(
    workspace_root: Path,
    scene_id: str,
) -> SceneAdoptionRecord:
    """確定済みScene採用記録を読み、検証する。"""
    path = scene_adoption_record_path(
        workspace_root,
        scene_id,
    )
    return _validate_record_directory(
        path,
        scene_id=scene_id,
    )


def _validate_record_directory(
    path: Path,
    *,
    scene_id: str,
    expected: SceneAdoptionRecord | None = None,
) -> SceneAdoptionRecord:
    if path.is_symlink() or not path.is_dir():
        raise ContractError(
            "Scene採用記録directoryが存在しません"
        )

    try:
        names = {
            entry.name
            for entry in path.iterdir()
        }
    except OSError as exc:
        raise ContractError(
            "Scene採用記録directoryを読めません"
        ) from exc

    if names != _RECORD_FILES:
        raise ContractError(
            "Scene採用記録のfile構成が不正です"
        )

    scene_card = read_json(
        path / "scene-card.json"
    )
    continuity = read_json(
        path / "continuity.json"
    )

    prose_path = path / "prose.md"
    if prose_path.is_symlink() or not prose_path.is_file():
        raise ContractError(
            "Scene採用記録のprose.mdが不正です"
        )
    try:
        prose = prose_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContractError(
            "Scene採用記録のprose.mdを読めません"
        ) from exc

    record = SceneAdoptionRecord(
        scene_card=scene_card,
        prose=prose,
        continuity=continuity,
    )
    _validate_record(record, scene_id)

    if expected is not None and record != expected:
        raise ContractError(
            "Scene採用記録が書込み予定内容と"
            "一致しません"
        )

    return record


def _validate_record(
    record: SceneAdoptionRecord,
    scene_id: str,
) -> None:
    _validate_scene_id(scene_id)

    if not isinstance(record.scene_card, dict):
        raise ContractError(
            "Scene採用記録のScene Cardが不正です"
        )
    if not isinstance(record.continuity, dict):
        raise ContractError(
            "Scene採用記録のContinuityが不正です"
        )
    if (
        not isinstance(record.prose, str)
        or not record.prose.strip()
    ):
        raise ContractError(
            "Scene採用記録の本文が空です"
        )

    if record.scene_card.get("scene_id") != scene_id:
        raise ContractError(
            "Scene採用記録のScene Card IDが不正です"
        )
    if record.continuity.get("scene_id") != scene_id:
        raise ContractError(
            "Scene採用記録のContinuity IDが不正です"
        )

    card_basis = record.scene_card.get(
        "basis_generation_id"
    )
    continuity_basis = record.continuity.get(
        "basis_generation_id"
    )
    if (
        not isinstance(card_basis, str)
        or card_basis != continuity_basis
    ):
        raise ContractError(
            "Scene採用記録のbasis Generationが"
            "一致しません"
        )

    if record.continuity.get("prose_version") != 1:
        raise ContractError(
            "Scene採用記録のprose_versionが不正です"
        )
    if record.continuity.get("version") != 1:
        raise ContractError(
            "Scene採用記録のContinuity versionが"
            "不正です"
        )

    result_generation_id = record.continuity.get(
        "result_generation_id"
    )
    if not re.fullmatch(
        r"gen-\d{6}",
        str(result_generation_id),
    ):
        raise ContractError(
            "Scene採用記録のresult Generation IDが"
            "不正です"
        )


def _validate_scene_id(scene_id: object) -> None:
    if not re.fullmatch(
        r"scene-v\d{2}-c\d{3}-s\d{3}",
        str(scene_id),
    ):
        raise ContractError(
            "Scene採用記録のscene_idが不正です"
        )


def _write_text_new(path: Path, value: str) -> None:
    try:
        with path.open(
            "x",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise ContractError(
            "Scene採用記録の本文を書き込めません"
        ) from exc
