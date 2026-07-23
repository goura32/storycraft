"""Storycraft Version 1 のinput Stage実行。"""
from __future__ import annotations

from copy import deepcopy
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


class InputStageService:
    """Brief採用またはKeywordsからのBrief生成を完了する。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        model: StoryModel | None = None,
        *,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        validate_workspace_layout(self.workspace_root)
        state = self.state_store.load()

        if state["current_stage"] != "input":
            raise ContractError(
                "現在のrun-stateはinput Stageではありません"
            )
        if state["status"] not in {"initializing", "running"}:
            raise ContractError(
                "input Stageを実行できるrun statusではありません"
            )

        timestamp = updated_at or _utc_now()
        source = _read_json(
            self.workspace_root / "input/source.json"
        )
        source_type = source["source_type"]

        if source_type == "brief":
            brief = _read_json(
                self.workspace_root / "input/brief.json"
            )
            ContractValidator._validate_brief(brief)
            advanced = advance_run_state(
                state,
                next_stage="initial_concept",
                next_target={
                    "series": state["workspace_id"],
                },
                updated_at=timestamp,
            )
            self.state_store.save(advanced)
            return advanced

        if source_type != "keywords":
            raise ContractError(
                f"未知のinput source_typeです: {source_type!r}"
            )
        if model is None:
            raise ContractError(
                "Keywords入力の処理にはStoryModelが必要です"
            )

        keywords = _read_json(
            self.workspace_root / "input/keywords.json"
        )
        config = _read_json(
            self.workspace_root / "runtime/config.json"
        )
        revision_limit = _revision_limit(config)

        candidate_id = _reserve_identifier(
            self.workspace_root,
            "next_candidate",
            "candidate",
            timestamp,
        )
        context = {"keywords": deepcopy(keywords)}

        try:
            candidate = model.generate("brief", context)
            _validate_generated_brief(candidate, keywords)
        except Exception as exc:
            blocked = _stop_state(
                state,
                status="blocked",
                stop_reason="manual_review_required",
                last_error={
                    "code": "BRIEF_GENERATION_INVALID",
                    "message": str(exc),
                },
                updated_at=timestamp,
            )
            self.state_store.save(blocked)
            return blocked

        version = 1
        revisions_used = 0
        revision_metadata: dict[str, Any] | None = None

        while True:
            review_id = _reserve_identifier(
                self.workspace_root,
                "next_review",
                "review",
                timestamp,
            )

            try:
                critique = model.critique(
                    "brief",
                    candidate,
                    context,
                )
                ContractValidator._validate_critique(critique)
                SeriesWorkflow._validate_critique_fields(
                    critique,
                    candidate,
                )
            except Exception as exc:
                blocked = _stop_state(
                    state,
                    status="blocked",
                    stop_reason="manual_review_required",
                    last_error={
                        "code": "BRIEF_REVIEW_INVALID",
                        "message": str(exc),
                    },
                    updated_at=timestamp,
                    active_candidate={
                        "kind": "input",
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
            candidate_status = (
                "accepted"
                if accepted
                else "rejected"
                if exhausted
                else "needs_revision"
            )
            review = _normalize_review(
                review_id=review_id,
                candidate_id=candidate_id,
                version=version,
                critique=critique,
                decision=(
                    "accept"
                    if accepted
                    else "reject"
                    if exhausted
                    else "revise"
                ),
                created_at=timestamp,
            )

            _publish_candidate_version(
                self.workspace_root,
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
                "kind": "input",
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
                _adopt_generated_brief(
                    self.workspace_root,
                    candidate,
                )
                validate_workspace_layout(self.workspace_root)

                adopted_state = deepcopy(state)
                adopted_state["active_candidate"] = None
                validate_run_state(adopted_state)

                advanced = advance_run_state(
                    adopted_state,
                    next_stage="initial_concept",
                    next_target={
                        "series": state["workspace_id"],
                    },
                    updated_at=timestamp,
                )
                self.state_store.save(advanced)
                return advanced

            if exhausted:
                blocked = _stop_state(
                    state,
                    status="blocked",
                    stop_reason="revision_limit",
                    last_error={
                        "code": "BRIEF_REVISION_LIMIT",
                        "issues": deepcopy(issues),
                    },
                    updated_at=timestamp,
                    active_candidate={
                        "kind": "input",
                        "candidate_id": candidate_id,
                        "version": version,
                    },
                )
                self.state_store.save(blocked)
                return blocked

            revision_id = _reserve_identifier(
                self.workspace_root,
                "next_revision",
                "revision",
                timestamp,
            )
            try:
                revised = model.revision(
                    "brief",
                    candidate,
                    critique,
                    context,
                )
                _validate_generated_brief(
                    revised,
                    keywords,
                )
                SeriesWorkflow._validate_revision_scope(
                    candidate,
                    revised,
                    critique,
                )
            except Exception as exc:
                blocked = _stop_state(
                    state,
                    status="blocked",
                    stop_reason="manual_review_required",
                    last_error={
                        "code": "BRIEF_REVISION_INVALID",
                        "message": str(exc),
                    },
                    updated_at=timestamp,
                    active_candidate={
                        "kind": "input",
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


def _validate_generated_brief(
    candidate: object,
    keywords: dict[str, Any],
) -> None:
    ContractValidator._validate_brief(candidate)
    assert isinstance(candidate, dict)

    if candidate.get("source_type") != "keywords":
        raise ContractError(
            "Keywords生成Briefはsource_type=keywordsが必要です"
        )
    if (
        candidate.get("source_reference")
        != "input/keywords.json"
    ):
        raise ContractError(
            "Keywords生成Briefは元Keywordsを参照しなければなりません"
        )
    if candidate.get("language") != keywords["language"]:
        raise ContractError(
            "Keywords生成Briefがlanguageを保持していません"
        )
    if candidate.get("volume_count") != keywords["volume_hint"]:
        raise ContractError(
            "Keywords生成Briefが巻数希望を保持していません"
        )

    brief_avoid = candidate.get("avoid")
    if not isinstance(brief_avoid, list):
        raise ContractError(
            "Keywords生成Briefのavoidが不正です"
        )
    missing_avoid = [
        item
        for item in keywords["avoid"]
        if item not in brief_avoid
    ]
    if missing_avoid:
        raise ContractError(
            "Keywords生成Briefがavoidを保持していません: "
            + ", ".join(missing_avoid)
        )


def _normalize_review(
    *,
    review_id: str,
    candidate_id: str,
    version: int,
    critique: dict[str, Any],
    decision: str,
    created_at: str,
) -> dict[str, Any]:
    issues = []
    for index, issue in enumerate(
        critique["issues"],
        1,
    ):
        issues.append({
            "issue_id": (
                f"{review_id}-issue-{index:03d}"
            ),
            "category": "brief_quality",
            "severity": issue["severity"],
            "location": issue["field"],
            "description": issue["description"],
            "expected": "指摘された問題が解消されていること",
            "suggestion": issue["suggestion"],
        })

    return {
        "schema_version": 1,
        "review_id": review_id,
        "target_type": "brief",
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


def _publish_candidate_version(
    workspace_root: Path,
    *,
    candidate_id: str,
    version: int,
    candidate: dict[str, Any],
    context: dict[str, Any],
    review: dict[str, Any],
    revision: dict[str, Any] | None,
    status: str,
    timestamp: str,
) -> None:
    candidate_root = (
        workspace_root
        / "runtime/candidates/input"
        / candidate_id
    )
    candidate_root.mkdir(
        parents=True,
        exist_ok=True,
    )
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
        _write_json_new(
            staging / "candidate.json",
            {
                "schema_version": 1,
                "candidate_id": candidate_id,
                "kind": "input",
                "artifact_type": "brief",
                "version": version,
                "content": candidate,
                "created_at": timestamp,
            },
        )
        _write_json_new(
            staging / "context.json",
            context,
        )
        _write_json_new(
            staging / "review.json",
            review,
        )
        if revision is not None:
            _write_json_new(
                staging / "revision.json",
                revision,
            )
        _write_json_new(
            staging / "status.json",
            {
                "schema_version": 1,
                "status": status,
                "updated_at": timestamp,
            },
        )

        final.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        staging.rename(final)
        _fsync_directory(candidate_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _adopt_generated_brief(
    workspace_root: Path,
    brief: dict[str, Any],
) -> None:
    path = workspace_root / "input/brief.json"
    if path.exists():
        existing = _read_json(path)
        if existing != brief:
            raise ContractError(
                "採用済みBriefを上書きできません"
            )
        return

    temporary = path.with_suffix(".json.tmp")
    try:
        with temporary.open(
            "x",
            encoding="utf-8",
        ) as handle:
            json.dump(
                brief,
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        written = _read_json(temporary)
        _validate_generated_brief(
            written,
            _read_json(
                workspace_root / "input/keywords.json"
            ),
        )
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _reserve_identifier(
    workspace_root: Path,
    counter_field: str,
    prefix: str,
    updated_at: str,
) -> str:
    path = workspace_root / "runtime/counters.json"
    counters = _read_json(path)
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
    _replace_json(path, updated)
    return f"{prefix}-{number:06d}"


def _revision_limit(config: dict[str, Any]) -> int:
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


def _stop_state(
    state: dict[str, Any],
    *,
    status: str,
    stop_reason: str,
    last_error: str | dict[str, Any],
    updated_at: str,
    active_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
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


def _replace_json(
    path: Path,
    value: object,
) -> None:
    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )
    try:
        with temporary.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                value,
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        json.loads(
            temporary.read_text(encoding="utf-8")
        )
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _write_json_new(
    path: Path,
    value: object,
) -> None:
    with path.open(
        "x",
        encoding="utf-8",
    ) as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _read_json(path: Path) -> dict[str, Any]:
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


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _fsync_directory(path: Path) -> None:
    if os.name != "posix":
        return

    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
