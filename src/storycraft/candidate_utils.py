"""V2 共通ユーティリティ - Candidate/Review/Revision 処理で使う補助関数。

これらは `reviewed_candidate_stage.py` と `reviewed_prose_stage.py` の
レガシー Runner クラスから分離したもので、V2 ワークフローでも使用可能。
"""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .run_state import validate_run_state
from .series_contracts import ContractError


def fsync_directory(path: Path) -> None:
    """POSIX環境でdirectory entryを同期する。"""
    if os.name != "posix":
        return

    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def normalize_review(
    *,
    review_id: str,
    target_type: str,
    review_category: str,
    candidate_id: str,
    version: int,
    critique: dict[str, Any],
    decision: str,
    created_at: str,
) -> dict[str, Any]:
    """Model critiqueをV1 Review記録へ正規化する。"""
    issues = []
    for index, issue in enumerate(critique["issues"], 1):
        issues.append({
            "issue_id": f"{review_id}-issue-{index:03d}",
            "category": review_category,
            "severity": issue["severity"],
            "evidence_locations": issue["evidence_locations"],
            "explanation": issue["explanation"],
        })

    return {
        "schema_version": 1,
        "review_id": review_id,
        "target_type": target_type,
        "target_id": candidate_id,
        "target_version": version,
        "decision": decision,
        "issues": issues,
        "summary": (
            "問題なし。採用可能。"
            if decision == "accept"
            else f"{len(issues)}件の問題があります。"
        ),
        "created_at": created_at,
    }


def publish_candidate_version(
    workspace_root: Path,
    *,
    stage: str,
    artifact_type: str,
    candidate_id: str,
    version: int,
    candidate: dict[str, Any],
    context: dict[str, Any],
    review: dict[str, Any] | None,
    revision: dict[str, Any] | None,
    status: str,
    timestamp: str,
) -> None:
    """完全なCandidate version directoryをatomicに公開する。"""
    candidate_root = (
        workspace_root
        / "runtime/candidates"
        / stage
        / candidate_id
    )
    candidate_root.mkdir(parents=True, exist_ok=True)
    final = candidate_root / f"v{version:04d}"

    if final.exists():
        raise ContractError(
            "同じCandidate versionを上書きできません"
        )

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".v{version:04d}-",
            dir=candidate_root,
        )
    )

    try:
        write_json_new(
            staging / "candidate.json",
            {
                "schema_version": 1,
                "candidate_id": candidate_id,
                "kind": stage,
                "artifact_type": artifact_type,
                "version": version,
                "content": candidate,
                "created_at": timestamp,
            },
        )
        write_json_new(
            staging / "context.json",
            context,
        )
        if review is not None:
            write_json_new(
                staging / "review.json",
                review,
            )
        if revision is not None:
            write_json_new(
                staging / "revision.json",
                revision,
            )

        staging.rename(final)
        fsync_directory(candidate_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def publish_prose_candidate_version(
    workspace_root: Path,
    *,
    stage: str,
    artifact_type: str,
    candidate_id: str,
    version: int,
    candidate: str,
    context: dict[str, Any],
    review: dict[str, Any] | None,
    revision: dict[str, Any] | None,
    status: str,
    timestamp: str,
) -> None:
    """完全なProse Candidate directoryをatomic公開する。"""
    candidate_root = (
        workspace_root
        / "runtime/candidates"
        / stage
        / candidate_id
    )
    candidate_root.mkdir(parents=True, exist_ok=True)
    final = candidate_root / f"v{version:04d}"

    if final.exists():
        raise ContractError(
            "同じCandidate versionを上書きできません"
        )

    staging = Path(
        tempfile.mkdtemp(
            prefix=f".v{version:04d}-",
            dir=candidate_root,
        )
    )

    try:
        write_json_new(
            staging / "candidate.json",
            {
                "schema_version": 1,
                "candidate_id": candidate_id,
                "kind": stage,
                "artifact_type": artifact_type,
                "version": version,
                "content_path": "candidate.md",
                "created_at": timestamp,
            },
        )
        write_text_new(staging / "candidate.md", candidate)
        write_json_new(staging / "context.json", context)
        if review is not None:
            write_json_new(staging / "review.json", review)
        if revision is not None:
            write_json_new(staging / "revision.json", revision)
        write_json_new(
            staging / "status.json",
            {
                "schema_version": 1,
                "status": status,
                "updated_at": timestamp,
            },
        )

        staging.rename(final)
        fsync_directory(candidate_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def reserve_identifier(
    workspace_root: Path,
    counter_field: str,
    prefix: str,
    updated_at: str,
) -> str:
    """Workspace counterをatomic更新して識別子を予約する。"""
    path = workspace_root / "runtime/counters.json"
    counters = read_json(path)
    number = counters.get(counter_field)

    if (
        not isinstance(number, int)
        or isinstance(number, bool)
        or number < 1
    ):
        raise ContractError(
            f"counterが不正です: {counter_field}"
        )

    updated = deepcopy(counters)
    updated[counter_field] = number + 1
    updated["updated_at"] = updated_at
    replace_json(path, updated)
    return f"{prefix}-{number:06d}"


def revision_limit_from_config(config: dict[str, Any]) -> int:
    """V1 Revision上限をWorkspace quality設定から取得する。"""
    quality = config.get("quality")
    if not isinstance(quality, dict):
        return 1

    value = quality.get(
        "max_critique_passes",
        1,
    )
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise ContractError(
            "config.quality.max_critique_passesは"
            "0以上の整数が必要です"
        )

    return value


def stop_state(
    state: dict[str, Any],
    *,
    status: str,
    last_error: str | dict[str, Any],
    updated_at: str,
) -> dict[str, Any]:
    """run-stateを停止状態へ非破壊更新する（v3ではstop_reasonは保存しない）。"""
    stopped = deepcopy(state)
    stopped["status"] = status
    stopped["last_error"] = deepcopy(last_error)
    stopped["updated_at"] = updated_at
    return validate_run_state(stopped)


def replace_json(path: Path, value: object) -> None:
    """既存JSON fileを同directory内temp経由でatomic置換する。"""
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(
                value,
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, path)
        fsync_directory(path.parent)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def write_json_new(path: Path, value: object) -> None:
    """新規JSON fileを書き、file内容を同期する。"""
    with path.open("x", encoding="utf-8") as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_text_new(path: Path, text: str) -> None:
    """新規text fileを書き、file内容を同期する。"""
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def read_json(path: Path) -> dict[str, Any]:
    """JSON object fileを読み込む。"""
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(
            f"JSONを読み込めません: {path}"
        ) from exc

    if not isinstance(value, dict):
        raise ContractError(
            f"JSON objectではありません: {path}"
        )
    return value


def utc_now() -> str:
    """秒精度のUTC timestampを返す。"""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )