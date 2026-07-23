"""Storycraft Version 1 のrun-state契約。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .series_contracts import ContractError
from .stages import SCENE_STAGES, STAGES, Stage


RUN_STATUSES = frozenset({
    "initializing",
    "running",
    "stopping",
    "stopped",
    "blocked",
    "failed",
    "completed",
})

STOPPED_STATUSES = frozenset({
    "stopped",
    "blocked",
    "failed",
})

SCENE_COMMIT_PHASES = frozenset({
    "prepared",
    "scene_finalized",
    "generation_finalized",
})

PUBLICATION_COMMIT_PHASES = frozenset({
    "prepared",
    "publication_finalized",
})

REQUIRED_FIELDS = frozenset({
    "schema_version",
    "workspace_id",
    "run_id",
    "status",
    "current_stage",
    "current_target",
    "current_generation_id",
    "current_publication_id",
    "active_candidate",
    "active_scene_id",
    "pending_commit",
    "stop_reason",
    "last_error",
    "created_at",
    "updated_at",
})


def validate_run_state(state: object) -> dict[str, Any]:
    """V1 run-stateの構造とcross-field不変条件を検証する。"""
    if not isinstance(state, dict):
        raise ContractError("run-stateはオブジェクトでなければなりません")

    keys = set(state)
    missing = REQUIRED_FIELDS - keys
    unknown = keys - REQUIRED_FIELDS
    if missing:
        raise ContractError(
            "run-state必須field不足: " + ", ".join(sorted(missing))
        )
    if unknown:
        raise ContractError(
            "run-state未知field: " + ", ".join(sorted(unknown))
        )

    if state["schema_version"] != 1:
        raise ContractError("run-state.schema_versionは1でなければなりません")

    _require_identifier(state, "workspace_id", "ws-")
    _require_identifier(state, "run_id", "run-")

    status = state["status"]
    if status not in RUN_STATUSES:
        raise ContractError(f"run-state.statusが不正です: {status!r}")

    current_stage = state["current_stage"]
    if current_stage not in STAGES:
        raise ContractError(
            f"run-state.current_stageがV1工程ではありません: {current_stage!r}"
        )

    target = state["current_target"]
    if not isinstance(target, dict) or not target:
        raise ContractError(
            "run-state.current_targetは空でないオブジェクトでなければなりません"
        )

    _require_optional_identifier(
        state,
        "current_generation_id",
        "gen-",
    )
    _require_optional_identifier(
        state,
        "current_publication_id",
        "pub-",
    )
    _require_optional_identifier(
        state,
        "active_scene_id",
        "scene-v",
    )

    _validate_candidate(state["active_candidate"])
    _validate_stop_fields(state)
    _validate_scene_fields(state)
    _validate_pending_commit(state)
    _validate_completed_state(state)
    _validate_timestamps(state)

    return state


def _require_identifier(
    state: dict[str, Any],
    field: str,
    prefix: str,
) -> None:
    value = state[field]
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ContractError(
            f"run-state.{field}は{prefix}で始まる識別子でなければなりません"
        )


def _require_optional_identifier(
    state: dict[str, Any],
    field: str,
    prefix: str,
) -> None:
    value = state[field]
    if value is None:
        return
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ContractError(
            f"run-state.{field}はnullまたは{prefix}で始まる識別子でなければなりません"
        )


def _validate_candidate(candidate: object) -> None:
    if candidate is None:
        return
    if not isinstance(candidate, dict):
        raise ContractError(
            "run-state.active_candidateはnullまたはオブジェクトでなければなりません"
        )
    if set(candidate) != {"kind", "candidate_id", "version"}:
        raise ContractError(
            "run-state.active_candidateのfield構成が不正です"
        )
    if candidate["kind"] not in STAGES:
        raise ContractError(
            "run-state.active_candidate.kindがV1工程ではありません"
        )
    candidate_id = candidate["candidate_id"]
    if (
        not isinstance(candidate_id, str)
        or not candidate_id.startswith("candidate-")
    ):
        raise ContractError(
            "run-state.active_candidate.candidate_idが不正です"
        )
    version = candidate["version"]
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ContractError(
            "run-state.active_candidate.versionは1以上の整数でなければなりません"
        )


def _validate_stop_fields(state: dict[str, Any]) -> None:
    status = state["status"]
    stop_reason = state["stop_reason"]

    if status in {"running", "initializing", "completed"}:
        if stop_reason is not None:
            raise ContractError(
                f"status={status}ではstop_reasonはnullでなければなりません"
            )
    elif status in STOPPED_STATUSES:
        if not isinstance(stop_reason, str) or not stop_reason:
            raise ContractError(
                f"status={status}ではstop_reasonが必要です"
            )

    last_error = state["last_error"]
    if last_error is not None and not isinstance(last_error, (str, dict)):
        raise ContractError(
            "run-state.last_errorはnull、文字列、またはオブジェクトでなければなりません"
        )


def _validate_scene_fields(state: dict[str, Any]) -> None:
    scene_id = state["active_scene_id"]
    if scene_id is None:
        return

    if state["current_stage"] not in {
        stage.value for stage in SCENE_STAGES
    }:
        raise ContractError(
            "active_scene_idがある場合、current_stageはScene工程でなければなりません"
        )

    target = state["current_target"]
    for field in (
        "volume_number",
        "chapter_number",
        "scene_number",
    ):
        value = target.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ContractError(
                f"active_scene_idがある場合、current_target.{field}は1以上の整数が必要です"
            )


def _validate_pending_commit(state: dict[str, Any]) -> None:
    pending = state["pending_commit"]
    if pending is None:
        return
    if not isinstance(pending, dict):
        raise ContractError(
            "run-state.pending_commitはnullまたはオブジェクトでなければなりません"
        )

    kind = pending.get("kind")
    target_id = pending.get("target_id")
    phase = pending.get("phase")

    if not isinstance(target_id, str) or not target_id:
        raise ContractError(
            "run-state.pending_commit.target_idが必要です"
        )

    if kind == Stage.SCENE_COMMIT.value:
        if set(pending) != {
            "kind",
            "target_id",
            "expected_generation_id",
            "phase",
        }:
            raise ContractError(
                "scene_commit pending_commitのfield構成が不正です"
            )
        if state["current_stage"] != Stage.SCENE_COMMIT.value:
            raise ContractError(
                "scene_commit pending_commitではcurrent_stageもscene_commitでなければなりません"
            )
        if target_id != state["active_scene_id"]:
            raise ContractError(
                "scene_commit pending_commit.target_idはactive_scene_idと一致しなければなりません"
            )
        generation_id = pending["expected_generation_id"]
        if (
            not isinstance(generation_id, str)
            or not generation_id.startswith("gen-")
        ):
            raise ContractError(
                "scene_commit expected_generation_idが不正です"
            )
        if phase not in SCENE_COMMIT_PHASES:
            raise ContractError(
                f"scene_commit pending_commit.phaseが不正です: {phase!r}"
            )
        return

    if kind == Stage.PUBLICATION.value:
        if set(pending) != {"kind", "target_id", "phase"}:
            raise ContractError(
                "publication pending_commitのfield構成が不正です"
            )
        if state["current_stage"] != Stage.PUBLICATION.value:
            raise ContractError(
                "publication pending_commitではcurrent_stageもpublicationでなければなりません"
            )
        if target_id != state["current_target"].get("publication_id"):
            raise ContractError(
                "publication pending_commit.target_idはcurrent_target.publication_idと一致しなければなりません"
            )
        if phase not in PUBLICATION_COMMIT_PHASES:
            raise ContractError(
                f"publication pending_commit.phaseが不正です: {phase!r}"
            )
        return

    raise ContractError(
        f"run-state.pending_commit.kindが不正です: {kind!r}"
    )


def _validate_completed_state(state: dict[str, Any]) -> None:
    if state["status"] != "completed":
        return

    if state["current_stage"] != Stage.PUBLICATION.value:
        raise ContractError(
            "completed runのcurrent_stageはpublicationでなければなりません"
        )
    if state["current_publication_id"] is None:
        raise ContractError(
            "completed runにはcurrent_publication_idが必要です"
        )
    if state["active_candidate"] is not None:
        raise ContractError(
            "completed runのactive_candidateはnullでなければなりません"
        )
    if state["active_scene_id"] is not None:
        raise ContractError(
            "completed runのactive_scene_idはnullでなければなりません"
        )
    if state["pending_commit"] is not None:
        raise ContractError(
            "completed runのpending_commitはnullでなければなりません"
        )


def _validate_timestamps(state: dict[str, Any]) -> None:
    created = _parse_timestamp(state["created_at"], "created_at")
    updated = _parse_timestamp(state["updated_at"], "updated_at")
    if updated < created:
        raise ContractError(
            "run-state.updated_atはcreated_atより前であってはなりません"
        )


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError(
            f"run-state.{field}はISO 8601文字列でなければなりません"
        )
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(
            f"run-state.{field}がISO 8601形式ではありません"
        ) from exc
