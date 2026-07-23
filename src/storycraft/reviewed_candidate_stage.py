"""V1 Review／Revision対象Stageの共通Candidate実行基盤。"""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .run_state import RunStateStore, validate_run_state
from .series_contracts import (
    ContractError,
    ContractValidator,
    StoryModel,
)
from .series_workflow import SeriesWorkflow
from .stage_transition import advance_run_state
from .workspace import validate_workspace_layout


CandidateValidator = Callable[[object], None]
CandidateAdopter = Callable[[dict[str, Any]], None]


_PRESERVE_ACTIVE_SCENE = object()


@dataclass(frozen=True)
class ReviewedCandidateSpec:
    """Review対象Stageの固定契約。"""

    stage: str
    artifact_type: str
    review_category: str
    next_stage: str


class ReviewedCandidateStageRunner:
    """生成、Review、Revision、採用、Stage遷移を実行する。"""

    def __init__(
        self,
        workspace_root: Path,
        spec: ReviewedCandidateSpec,
    ) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.spec = spec
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        model: StoryModel,
        *,
        context: dict[str, Any],
        validator: CandidateValidator,
        adopter: CandidateAdopter,
        next_target: dict[str, Any],
        active_scene_id: str | None | object = (
            _PRESERVE_ACTIVE_SCENE
        ),
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        validate_workspace_layout(self.workspace_root)
        state = self.state_store.load()

        if state["current_stage"] != self.spec.stage:
            raise ContractError(
                "現在のrun-stateは対象Stageではありません: "
                f"expected={self.spec.stage!r}, "
                f"actual={state['current_stage']!r}"
            )
        if state["status"] not in {"initializing", "running"}:
            raise ContractError(
                "Candidate Stageを実行できるrun statusではありません"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるためCandidate Stageを開始できません"
            )

        timestamp = updated_at or utc_now()
        config = read_json(
            self.workspace_root / "runtime/config.json"
        )
        revision_limit = revision_limit_from_config(config)

        candidate_id = reserve_identifier(
            self.workspace_root,
            "next_candidate",
            "candidate",
            timestamp,
        )

        try:
            candidate = model.generate(
                self.spec.stage,
                deepcopy(context),
            )
            validator(candidate)
        except Exception as exc:
            blocked = stop_state(
                state,
                status="blocked",
                stop_reason="manual_review_required",
                last_error={
                    "code": (
                        f"{self.spec.stage.upper()}_GENERATION_INVALID"
                    ),
                    "message": str(exc),
                },
                updated_at=timestamp,
            )
            self.state_store.save(blocked)
            return blocked

        if not isinstance(candidate, dict):
            raise ContractError(
                "検証済みCandidateがJSON objectではありません"
            )

        version = 1
        revisions_used = 0
        revision_metadata: dict[str, Any] | None = None

        while True:
            review_id = reserve_identifier(
                self.workspace_root,
                "next_review",
                "review",
                timestamp,
            )

            try:
                critique = model.critique(
                    self.spec.stage,
                    candidate,
                    deepcopy(context),
                )
                ContractValidator._validate_critique(critique)
                SeriesWorkflow._validate_critique_fields(
                    critique,
                    candidate,
                )
            except Exception as exc:
                publish_candidate_version(
                    self.workspace_root,
                    stage=self.spec.stage,
                    artifact_type=self.spec.artifact_type,
                    candidate_id=candidate_id,
                    version=version,
                    candidate=candidate,
                    context=context,
                    review=None,
                    revision=revision_metadata,
                    status="generated",
                    timestamp=timestamp,
                )
                blocked = stop_state(
                    state,
                    status="blocked",
                    stop_reason="manual_review_required",
                    last_error={
                        "code": (
                            f"{self.spec.stage.upper()}_REVIEW_INVALID"
                        ),
                        "message": str(exc),
                    },
                    updated_at=timestamp,
                    active_candidate={
                        "kind": self.spec.stage,
                        "candidate_id": candidate_id,
                        "version": version,
                    },
                )
                self.state_store.save(blocked)
                return blocked

            issues = critique["issues"]
            accepted = not issues
            exhausted = (
                bool(issues)
                and revisions_used >= revision_limit
            )

            if accepted:
                candidate_status = "accepted"
                decision = "accept"
            elif exhausted:
                candidate_status = "rejected"
                decision = "reject"
            else:
                candidate_status = "needs_revision"
                decision = "revise"

            review = normalize_review(
                review_id=review_id,
                target_type=self.spec.stage,
                review_category=self.spec.review_category,
                candidate_id=candidate_id,
                version=version,
                critique=critique,
                decision=decision,
                created_at=timestamp,
            )

            publish_candidate_version(
                self.workspace_root,
                stage=self.spec.stage,
                artifact_type=self.spec.artifact_type,
                candidate_id=candidate_id,
                version=version,
                candidate=candidate,
                context=context,
                review=review,
                revision=revision_metadata,
                status=candidate_status,
                timestamp=timestamp,
            )

            active_state = deepcopy(state)
            active_state["status"] = "running"
            active_state["active_candidate"] = {
                "kind": self.spec.stage,
                "candidate_id": candidate_id,
                "version": version,
            }
            active_state["stop_reason"] = None
            active_state["last_error"] = None
            active_state["updated_at"] = timestamp
            validate_run_state(active_state)
            self.state_store.save(active_state)
            state = active_state

            if accepted:
                adopter(deepcopy(candidate))
                validate_workspace_layout(self.workspace_root)

                adopted_state = deepcopy(state)
                adopted_state["active_candidate"] = None
                validate_run_state(adopted_state)

                transition_kwargs: dict[str, Any] = {}
                if active_scene_id is not _PRESERVE_ACTIVE_SCENE:
                    transition_kwargs["active_scene_id"] = (
                        active_scene_id
                    )

                advanced = advance_run_state(
                    adopted_state,
                    next_stage=self.spec.next_stage,
                    next_target=deepcopy(next_target),
                    updated_at=timestamp,
                    **transition_kwargs,
                )
                self.state_store.save(advanced)
                return advanced

            if exhausted:
                blocked = stop_state(
                    state,
                    status="blocked",
                    stop_reason="revision_limit",
                    last_error={
                        "code": (
                            f"{self.spec.stage.upper()}_REVISION_LIMIT"
                        ),
                        "issues": deepcopy(issues),
                    },
                    updated_at=timestamp,
                    active_candidate={
                        "kind": self.spec.stage,
                        "candidate_id": candidate_id,
                        "version": version,
                    },
                )
                self.state_store.save(blocked)
                return blocked

            revision_id = reserve_identifier(
                self.workspace_root,
                "next_revision",
                "revision",
                timestamp,
            )

            try:
                revised = model.revision(
                    self.spec.stage,
                    candidate,
                    critique,
                    deepcopy(context),
                )
                validator(revised)
                if not isinstance(revised, dict):
                    raise ContractError(
                        "修正版CandidateがJSON objectではありません"
                    )
                SeriesWorkflow._validate_revision_scope(
                    candidate,
                    revised,
                    critique,
                )
            except Exception as exc:
                blocked = stop_state(
                    state,
                    status="blocked",
                    stop_reason="manual_review_required",
                    last_error={
                        "code": (
                            f"{self.spec.stage.upper()}_REVISION_INVALID"
                        ),
                        "message": str(exc),
                    },
                    updated_at=timestamp,
                    active_candidate={
                        "kind": self.spec.stage,
                        "candidate_id": candidate_id,
                        "version": version,
                    },
                )
                self.state_store.save(blocked)
                return blocked

            revision_metadata = {
                "schema_version": 1,
                "revision_id": revision_id,
                "candidate_id": candidate_id,
                "from_version": version,
                "to_version": version + 1,
                "review_id": review_id,
                "created_at": timestamp,
            }
            candidate = revised
            version += 1
            revisions_used += 1


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
    """Legacy critique shapeをV1 Review記録へ正規化する。"""
    issues = []
    for index, issue in enumerate(critique["issues"], 1):
        issues.append({
            "issue_id": f"{review_id}-issue-{index:03d}",
            "category": review_category,
            "severity": issue["severity"],
            "location": issue["field"],
            "description": issue["description"],
            "expected": "指摘された問題が解消されていること",
            "suggestion": issue["suggestion"],
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
    """V1 Revision上限をWorkspace configから取得する。"""
    retry = config.get("retry")
    if not isinstance(retry, dict):
        return 1

    value = retry.get("revision", 1)
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise ContractError(
            "config.retry.revisionは0以上の整数が必要です"
        )
    return value


def stop_state(
    state: dict[str, Any],
    *,
    status: str,
    stop_reason: str,
    last_error: str | dict[str, Any],
    updated_at: str,
    active_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """run-stateを停止状態へ非破壊更新する。"""
    stopped = deepcopy(state)
    stopped["status"] = status
    stopped["stop_reason"] = stop_reason
    stopped["last_error"] = deepcopy(last_error)
    stopped["updated_at"] = updated_at
    if active_candidate is not None:
        stopped["active_candidate"] = deepcopy(
            active_candidate
        )
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


def fsync_directory(path: Path) -> None:
    """POSIX環境でdirectory entryを同期する。"""
    if os.name != "posix":
        return

    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
