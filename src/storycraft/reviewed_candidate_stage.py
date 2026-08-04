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
from .error_sanitizer import safe_exception_message
from .series_contracts import (
    ContractError,
    ContractValidator,
    StoryModel,
)
from .review_contracts import (
    validate_critique_fields,
    validate_revision_scope,
)
from .stage_transition import advance_run_state
from .workspace import validate_workspace


CandidateValidator = Callable[[object], None]
CandidateAdopter = Callable[[dict[str, Any]], None]
CandidateAfterAdoption = Callable[
    [
        dict[str, Any],
        dict[str, Any],
        str,
    ],
    dict[str, Any],
]


_PRESERVE_ACTIVE_SCENE = object()


@dataclass(frozen=True)
class ReviewedCandidateSpec:
    """Review対象Stageの固定契約。"""

    stage: str
    artifact_type: str
    review_category: str
    next_stage: str
    model_stage: str | None = None


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

    def _selected_quality_config(self, state: dict[str, Any]) -> dict[str, Any]:
        """可変 runtime/config.json を読まず、選択済み settings から品質値を得る。"""
        selection_id = state["current_selection_id"]
        if not isinstance(selection_id, str):
            raise ContractError("Candidate工程にはsettingsを持つselectionが必要です")
        selection = read_json(
            self.workspace_root / "runtime/selections" / selection_id / "record.json"
        )
        slots = selection.get("slots")
        if not isinstance(slots, dict) or not isinstance(slots.get("settings"), str):
            raise ContractError("selectionにsettings slotがありません")
        record = read_json(
            self.workspace_root
            / "runtime/settings"
            / slots["settings"]
            / "record.json"
        )
        payload = record.get("payload")
        if not isinstance(payload, dict):
            raise ContractError("settings record payloadが不正です")
        return {
            "quality": {
                "max_critique_passes": payload.get("quality_revision_limit"),
                "invalid_response_limit": payload.get("invalid_response_limit"),
            }
        }

    def run(
        self,
        model: StoryModel | None,
        *,
        context: dict[str, Any],
        validator: CandidateValidator,
        adopter: CandidateAdopter,
        next_target: dict[str, Any],
        next_stage: str | None = None,
        after_adoption: CandidateAfterAdoption | None = None,
        adoption_metadata: dict[str, Any] | None = None,
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            from .workspace import validate_workspace
            validate_workspace(
                self.workspace_root
            )

        state = self.state_store.load()

        if state["current_stage"] != self.spec.stage:
            raise ContractError(
                "現在のrun-stateは対象Stageではありません: "
                f"expected={self.spec.stage!r}, "
                f"actual={state['current_stage']!r}"
            )

        pending = state["pending_commit"]
        if (
            isinstance(pending, dict)
            and pending.get("kind")
            == "candidate_adoption"
        ):
            return self._complete_candidate_adoption(
                state,
                validator=validator,
                adopter=adopter,
                next_target=next_target,
                next_stage=next_stage,
                after_adoption=after_adoption,
                adoption_metadata=adoption_metadata,
                recovering=True,
            )

        if pending is not None:
            raise ContractError(
                "pending_commitがあるためCandidate Stageを開始できません"
            )
        if model is None:
            raise ContractError(
                "Candidate生成にはStoryModelが必要です"
            )

        timestamp = updated_at or utc_now()
        model_stage = self.spec.model_stage or self.spec.stage
        config = self._selected_quality_config(state)
        revision_limit = revision_limit_from_config(config)
        quality = config["quality"]
        invalid_response_limit = quality["invalid_response_limit"]

        candidate_id = reserve_identifier(
            self.workspace_root,
            "next_candidate",
            "candidate",
            timestamp,
        )

        try:
            candidate = model.generate(
                model_stage,
                deepcopy(context),
            )
            validator(candidate)
        except Exception as exc:
            blocked = stop_state(
                state,
                status="blocked",
                last_error={
                    "code": (
                        f"{self.spec.stage.upper()}_GENERATION_INVALID"
                    ),
                    "message": safe_exception_message(exc),
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
                    model_stage,
                    candidate,
                    deepcopy(context),
                )
                ContractValidator._validate_critique(critique)
                validate_critique_fields(
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
                last_error={
                    "code": (
                        f"{self.spec.stage.upper()}_REVIEW_INVALID"
                    ),
                    "message": safe_exception_message(exc),
                },
                updated_at=timestamp,
            )
            self.state_store.save(blocked)
            return blocked

            issues = critique["issues"]
            accepted = not issues
            exhausted = bool(issues) and revisions_used >= revision_limit

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
            active_state["last_error"] = None
            active_state["updated_at"] = timestamp

            if accepted:
                pending_adoption = {
                    "kind": "candidate_adoption",
                    "target_id": candidate_id,
                    "stage": self.spec.stage,
                    "version": version,
                    "phase": "prepared",
                }
                if adoption_metadata is not None:
                    pending_adoption["reserved"] = (
                        deepcopy(adoption_metadata)
                    )
                active_state["pending_commit"] = (
                    pending_adoption
                )

            validate_run_state(active_state)
            self.state_store.save(active_state)
            state = active_state

            if accepted:
                return self._complete_candidate_adoption(
                    state,
                    validator=validator,
                    adopter=adopter,
                    next_target=next_target,
                    next_stage=next_stage,
                    after_adoption=after_adoption,
                    active_scene_id=active_scene_id,
                    adoption_metadata=adoption_metadata,
                    recovering=False,
                )

            if exhausted:
                blocked = stop_state(
                    state,
                    status="blocked",
                    last_error={
                        "code": (
                            f"{self.spec.stage.upper()}_REVISION_LIMIT"
                        ),
                        "issues": deepcopy(issues),
                    },
                    updated_at=timestamp,
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
                    model_stage,
                    candidate,
                    critique,
                    deepcopy(context),
                )
                validator(revised)
                if not isinstance(revised, dict):
                    raise ContractError(
                        "修正版CandidateがJSON objectではありません"
                    )
                validate_revision_scope(
                    candidate,
                    revised,
                    critique,
                )
            except Exception as exc:
                blocked = stop_state(
                    state,
                    status="blocked",
                    last_error={
                        "code": (
                            f"{self.spec.stage.upper()}_REVISION_INVALID"
                        ),
                        "message": safe_exception_message(exc),
                    },
                    updated_at=timestamp,
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


    def _complete_candidate_adoption(
        self,
        state: dict[str, Any],
        *,
        validator: CandidateValidator,
        adopter: CandidateAdopter,
        next_target: dict[str, Any],
        next_stage: str | None,
        after_adoption: CandidateAfterAdoption | None,
        adoption_metadata: dict[str, Any] | None,
        recovering: bool,
    ) -> dict[str, Any]:
        """保存済みaccepted CandidateをProviderなしで採用する。"""
        active = state["active_candidate"]
        if not isinstance(active, dict):
            raise ContractError(
                "Candidate Adoptionには"
                "active_candidateが必要です"
            )

        candidate_id = active.get("candidate_id")
        version = active.get("version")

        if (
            active.get("kind") != self.spec.stage
            or not isinstance(candidate_id, str)
            or not isinstance(version, int)
            or isinstance(version, bool)
            or version < 1
        ):
            raise ContractError(
                "active_candidateが対象Stageと一致しません"
            )

        timestamp = state["updated_at"]
        pending = state["pending_commit"]

        if not isinstance(pending, dict):
            raise ContractError(
                "Candidate Adoptionには"
                "pending_commit=preparedが必要です"
            )

        if adoption_metadata is None:
            if "reserved" in pending:
                raise ContractError(
                    "Candidate Adoptionの予約metadataが"
                    "呼出し内容と一致しません"
                )
        elif (
            pending.get("reserved")
            != adoption_metadata
        ):
            raise ContractError(
                "Candidate Adoptionの予約metadataが"
                "pending_commitと一致しません"
            )

        prepared = deepcopy(state)

        candidate = load_accepted_candidate_version(
            self.workspace_root,
            stage=self.spec.stage,
            candidate_id=candidate_id,
            version=version,
        )
        validator(candidate)

        try:
            adopter(deepcopy(candidate))
        except Exception as exc:
            if recovering:
                raise ContractError(
                    "Candidate Adoption Recoveryは"
                    "manual対応が必要です"
                ) from exc
            raise

        from .workspace import validate_workspace
        validate_workspace(
            self.workspace_root
        )

        phase = prepared["pending_commit"]["phase"]

        if phase == "prepared":
            finalized = deepcopy(prepared)
            finalized["pending_commit"]["phase"] = (
                "artifact_finalized"
            )
            validate_run_state(finalized)
            self.state_store.save(finalized)
        elif phase == "artifact_finalized":
            finalized = prepared
        else:
            raise ContractError(
                "Candidate Adoption phaseが不正です"
            )

        adopted_state = deepcopy(finalized)
        adopted_state["active_candidate"] = None
        adopted_state["pending_commit"] = None
        validate_run_state(adopted_state)

        if after_adoption is not None:
            completed = after_adoption(
                deepcopy(candidate),
                deepcopy(adopted_state),
                timestamp,
            )
            validate_run_state(completed)
            self.state_store.save(completed)
            return completed

        transition_kwargs: dict[str, Any] = {}

        advanced = advance_run_state(
            adopted_state,
            next_stage=(
                next_stage or self.spec.next_stage
            ),
            next_target=deepcopy(next_target),
            updated_at=timestamp,
        )
        self.state_store.save(advanced)
        return advanced


def load_accepted_candidate_version(
    workspace_root: Path,
    *,
    stage: str,
    candidate_id: str,
    version: int,
) -> dict[str, Any]:
    """accepted Candidate versionを採用Authorityとして読む。"""
    directory = (
        workspace_root
        / "runtime/candidates"
        / stage
        / candidate_id
        / f"v{version:04d}"
    )

    if (
        directory.is_symlink()
        or not directory.is_dir()
    ):
        raise ContractError(
            "Candidate version directoryが存在しません"
        )

    required = {
        "candidate.json",
        "context.json",
        "review.json",
        "status.json",
    }
    names = {
        entry.name
        for entry in directory.iterdir()
    }

    if not required.issubset(names):
        raise ContractError(
            "accepted Candidateの必須fileがありません"
        )

    metadata = read_json(
        directory / "candidate.json"
    )
    review = read_json(
        directory / "review.json"
    )
    status = read_json(
        directory / "status.json"
    )

    if (
        metadata.get("schema_version") != 1
        or metadata.get("candidate_id")
        != candidate_id
        or metadata.get("kind") != stage
        or metadata.get("version") != version
    ):
        raise ContractError(
            "Candidate metadataがpendingと一致しません"
        )

    candidate = metadata.get("content")
    if not isinstance(candidate, dict):
        raise ContractError(
            "Candidate contentはobjectが必要です"
        )

    if status.get("status") != "accepted":
        raise ContractError(
            "Candidate statusがacceptedではありません"
        )

    if (
        review.get("decision") != "accept"
        or review.get("target_id")
        != candidate_id
        or review.get("target_version")
        != version
    ):
        raise ContractError(
            "Candidate Reviewが採用を示していません"
        )

    return deepcopy(candidate)


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
        or value < 1
    ):
        raise ContractError(
            "config.quality.max_critique_passesは"
            "1以上の整数が必要です"
        )

    return value


def stop_state(
    state: dict[str, Any],
    *,
    status: str,
    last_error: str | dict[str, Any],
    updated_at: str,
    active_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """run-stateを停止状態へ非破壊更新する（v3ではstop_reasonは保存しない）。"""
    stopped = deepcopy(state)
    stopped["status"] = status
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
