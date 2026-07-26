"""V1 raw-text Scene本文の生成・Review・Revision基盤。"""
from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .reviewed_candidate_stage import (
    fsync_directory,
    normalize_review,
    read_json,
    reserve_identifier,
    revision_limit_from_config,
    stop_state,
    utc_now,
    write_json_new,
)
from .run_state import RunStateStore, validate_run_state
from .error_sanitizer import safe_exception_message
from .series_contracts import (
    ContractError,
    ContractValidator,
    ProseStoryModel,
)
from .stage_transition import advance_run_state
from .workspace import validate_workspace_layout


ProseValidator = Callable[[object], None]
ProseAdopter = Callable[[str], None]


@dataclass(frozen=True)
class ReviewedProseSpec:
    """raw-text Review対象Stageの固定契約。"""

    stage: str
    artifact_type: str
    review_category: str
    next_stage: str
    model_stage: str


class ReviewedProseStageRunner:
    """本文生成、Review、Revision、採用、遷移を実行する。"""

    def __init__(
        self,
        workspace_root: Path,
        spec: ReviewedProseSpec,
    ) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.spec = spec
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        model: ProseStoryModel | None,
        *,
        context: dict[str, Any],
        review_context: dict[str, Any],
        validator: ProseValidator,
        adopter: ProseAdopter,
        next_target: dict[str, Any],
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace_layout(
                self.workspace_root
            )

        state = self.state_store.load()

        if state["current_stage"] != self.spec.stage:
            raise ContractError(
                "現在のrun-stateは対象Stageではありません: "
                f"expected={self.spec.stage!r}, "
                f"actual={state['current_stage']!r}"
            )
        if state["status"] not in {"initializing", "running"}:
            raise ContractError(
                "Prose Candidate Stageを実行できる"
                "run statusではありません"
            )

        pending = state["pending_commit"]
        if (
            isinstance(pending, dict)
            and pending.get("kind")
            == "candidate_adoption"
        ):
            return self._complete_prose_adoption(
                state,
                validator=validator,
                adopter=adopter,
                next_target=next_target,
                recovering=True,
            )

        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if pending is not None:
            raise ContractError(
                "pending_commitがあるため"
                "Prose Candidate Stageを開始できません"
            )
        if model is None:
            raise ContractError(
                "Prose Candidate生成には"
                "ProseStoryModelが必要です"
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
            generated = model.generate_prose(
                self.spec.model_stage,
                deepcopy(context),
            )
            candidate = (
                generated.strip()
                if isinstance(generated, str)
                else generated
            )
            validator(candidate)
        except Exception as exc:
            blocked = stop_state(
                state,
                status="blocked",
                stop_reason="manual_review_required",
                last_error={
                    "code": (
                        f"{self.spec.stage.upper()}"
                        "_GENERATION_INVALID"
                    ),
                    "message": safe_exception_message(exc),
                },
                updated_at=timestamp,
            )
            self.state_store.save(blocked)
            return blocked

        if not isinstance(candidate, str):
            raise ContractError(
                "検証済みProse Candidateが文字列ではありません"
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
                critique = model.critique_prose(
                    self.spec.model_stage,
                    candidate,
                    deepcopy(review_context),
                )
                ContractValidator._validate_critique(critique)
            except Exception as exc:
                publish_prose_candidate_version(
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
                            f"{self.spec.stage.upper()}"
                            "_REVIEW_INVALID"
                        ),
                        "message": safe_exception_message(exc),
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

            publish_prose_candidate_version(
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

            if accepted:
                active_state["pending_commit"] = {
                    "kind": "candidate_adoption",
                    "target_id": candidate_id,
                    "stage": self.spec.stage,
                    "version": version,
                    "phase": "prepared",
                }

            validate_run_state(active_state)
            self.state_store.save(active_state)
            state = active_state

            if accepted:
                return self._complete_prose_adoption(
                    state,
                    validator=validator,
                    adopter=adopter,
                    next_target=next_target,
                    recovering=False,
                )

            if exhausted:
                blocked = stop_state(
                    state,
                    status="blocked",
                    stop_reason="revision_limit",
                    last_error={
                        "code": (
                            f"{self.spec.stage.upper()}"
                            "_REVISION_LIMIT"
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
                generated_revision = model.revision_prose(
                    self.spec.model_stage,
                    candidate,
                    critique,
                    deepcopy(context),
                )
                revised = (
                    generated_revision.strip()
                    if isinstance(generated_revision, str)
                    else generated_revision
                )
                validator(revised)
            except Exception as exc:
                blocked = stop_state(
                    state,
                    status="blocked",
                    stop_reason="manual_review_required",
                    last_error={
                        "code": (
                            f"{self.spec.stage.upper()}"
                            "_REVISION_INVALID"
                        ),
                        "message": safe_exception_message(exc),
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

            if not isinstance(revised, str):
                raise ContractError(
                    "修正版Prose Candidateが文字列ではありません"
                )

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


    def _complete_prose_adoption(
        self,
        state: dict[str, Any],
        *,
        validator: ProseValidator,
        adopter: ProseAdopter,
        next_target: dict[str, Any],
        recovering: bool,
    ) -> dict[str, Any]:
        """保存済みaccepted ProseをProviderなしで採用する。"""
        active = state["active_candidate"]
        if not isinstance(active, dict):
            raise ContractError(
                "Prose Adoptionには"
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
                "active_candidateが"
                "Prose Stageと一致しません"
            )

        timestamp = state["updated_at"]
        pending = state["pending_commit"]

        if not isinstance(pending, dict):
            raise ContractError(
                "Prose Adoptionには"
                "pending_commit=preparedが必要です"
            )

        prepared = deepcopy(state)

        prose = load_accepted_prose_candidate_version(
            self.workspace_root,
            stage=self.spec.stage,
            candidate_id=candidate_id,
            version=version,
        )
        validator(prose)

        try:
            adopter(prose)
        except Exception as exc:
            if recovering:
                raise ContractError(
                    "Prose Adoption Recoveryは"
                    "manual対応が必要です"
                ) from exc
            raise

        validate_workspace_layout(
            self.workspace_root,
            run_state=prepared,
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
                "Prose Adoption phaseが不正です"
            )

        adopted_state = deepcopy(finalized)
        adopted_state["active_candidate"] = None
        adopted_state["pending_commit"] = None
        validate_run_state(adopted_state)

        advanced = advance_run_state(
            adopted_state,
            next_stage=self.spec.next_stage,
            next_target=deepcopy(next_target),
            updated_at=timestamp,
        )
        self.state_store.save(advanced)
        return advanced


def load_accepted_prose_candidate_version(
    workspace_root: Path,
    *,
    stage: str,
    candidate_id: str,
    version: int,
) -> str:
    """accepted Prose Candidateを採用Authorityとして読む。"""
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
            "Prose Candidate version directoryが"
            "存在しません"
        )

    required = {
        "candidate.json",
        "candidate.md",
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
            "accepted Prose Candidateの"
            "必須fileがありません"
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
        or metadata.get("content_path")
        != "candidate.md"
    ):
        raise ContractError(
            "Prose Candidate metadataが"
            "pendingと一致しません"
        )

    if status.get("status") != "accepted":
        raise ContractError(
            "Prose Candidate statusが"
            "acceptedではありません"
        )

    if (
        review.get("decision") != "accept"
        or review.get("target_id")
        != candidate_id
        or review.get("target_version")
        != version
    ):
        raise ContractError(
            "Prose Candidate Reviewが"
            "採用を示していません"
        )

    try:
        stored = (
            directory / "candidate.md"
        ).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContractError(
            "Prose Candidate本文を"
            "読み込めません"
        ) from exc

    if not stored.endswith("\n"):
        raise ContractError(
            "Prose Candidate本文の"
            "終端改行がありません"
        )

    prose = stored[:-1]
    if not prose:
        raise ContractError(
            "Prose Candidate本文が空です"
        )

    return prose


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


def write_text_new(path: Path, value: str) -> None:
    """新規UTF-8 text fileを書き、内容を同期する。"""
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(value)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
