"""Storycraft Version 1 のrun-state契約。"""
from __future__ import annotations

from copy import deepcopy

from datetime import datetime
import json
import os
from pathlib import Path
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

CANDIDATE_ADOPTION_PHASES = frozenset({
    "prepared",
    "artifact_finalized",
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

    if kind == "candidate_adoption":
        expected_fields = {
            "kind",
            "target_id",
            "stage",
            "version",
            "phase",
        }
        if set(pending) != expected_fields:
            raise ContractError(
                "candidate_adoption pending_commitの"
                "field構成が不正です"
            )

        stage = pending.get("stage")
        version = pending.get("version")

        if stage != state["current_stage"]:
            raise ContractError(
                "candidate_adoption pending_commit.stageは"
                "current_stageと一致しなければなりません"
            )
        if (
            not target_id.startswith("candidate-")
            or "/" in target_id
            or "\\" in target_id
            or "." in target_id
        ):
            raise ContractError(
                "candidate_adoption target_idが不正です"
            )
        if (
            not isinstance(version, int)
            or isinstance(version, bool)
            or version < 1
        ):
            raise ContractError(
                "candidate_adoption versionは"
                "1以上の整数が必要です"
            )
        if phase not in CANDIDATE_ADOPTION_PHASES:
            raise ContractError(
                "candidate_adoption phaseが不正です: "
                f"{phase!r}"
            )
        if state["status"] != "running":
            raise ContractError(
                "candidate_adoption中のstatusは"
                "runningでなければなりません"
            )

        active = state["active_candidate"]
        if not isinstance(active, dict):
            raise ContractError(
                "candidate_adoptionには"
                "active_candidateが必要です"
            )
        if (
            active.get("kind") != stage
            or active.get("candidate_id") != target_id
            or active.get("version") != version
        ):
            raise ContractError(
                "candidate_adoption pending_commitと"
                "active_candidateが一致しません"
            )
        return

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



def _is_stale_scene_commit_shape(
    state: dict[str, Any],
) -> bool:
    """最終state更新後にpendingだけ残った形か判定する。"""
    pending = state.get("pending_commit")
    if not isinstance(pending, dict):
        return False

    expected_fields = {
        "kind",
        "target_id",
        "expected_generation_id",
        "phase",
    }
    if set(pending) != expected_fields:
        return False

    target_id = pending.get("target_id")
    expected_generation_id = pending.get(
        "expected_generation_id"
    )

    return (
        pending.get("kind") == Stage.SCENE_COMMIT.value
        and pending.get("phase") == "generation_finalized"
        and isinstance(target_id, str)
        and target_id.startswith("scene-v")
        and isinstance(expected_generation_id, str)
        and expected_generation_id.startswith("gen-")
        and state.get("status") == "running"
        and state.get("current_stage") in {
            Stage.SCENE_PLAN.value,
            Stage.CHAPTER_PLAN.value,
            Stage.VOLUME_HANDOFF.value,
        }
        and state.get("current_generation_id")
        == expected_generation_id
        and state.get("active_candidate") is None
        and state.get("active_scene_id") is None
    )


def validate_recovery_run_state(
    state: object,
) -> dict[str, Any]:
    """通常stateまたは限定されたstale pending stateを検証する。"""
    try:
        return validate_run_state(state)
    except ContractError:
        if (
            not isinstance(state, dict)
            or not _is_stale_scene_commit_shape(state)
        ):
            raise

        normalized = deepcopy(state)
        normalized["pending_commit"] = None
        validate_run_state(normalized)
        return state


def is_stale_scene_commit_recovery_state(
    state: object,
) -> bool:
    """検証済みstateがstale Scene Commit pendingか判定する。"""
    try:
        validated = validate_recovery_run_state(state)
    except ContractError:
        return False

    return _is_stale_scene_commit_shape(validated)


class RunStateStore:
    """V1 runtime/run-state.json の原子的な永続化。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.runtime_root = workspace_root / "runtime"
        self.path = self.runtime_root / "run-state.json"

    def exists(self) -> bool:
        return self.path.is_file()

    def _read(self) -> object:
        if not self.exists():
            raise ContractError("V1 run-stateがありません")

        try:
            return json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise ContractError(
                "V1 run-stateがJSONとして読めません"
            ) from exc
        except OSError as exc:
            raise ContractError(
                "V1 run-stateを読み込めません"
            ) from exc

    def load(self) -> dict[str, Any]:
        """通常のrun-stateを厳密に読み込む。"""
        return validate_run_state(self._read())

    def load_recovery(self) -> dict[str, Any]:
        """Recovery開始時に限定特殊状態も含めて読み込む。"""
        return validate_recovery_run_state(
            self._read()
        )

    def save(self, state: dict[str, Any]) -> None:
        validate_run_state(state)
        self.runtime_root.mkdir(parents=True, exist_ok=True)

        temporary = self.path.with_suffix(".json.tmp")

        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(
                    state,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            written = json.loads(
                temporary.read_text(encoding="utf-8")
            )
            validate_run_state(written)

            os.replace(temporary, self.path)
            self._fsync_directory()
        except (OSError, json.JSONDecodeError) as exc:
            temporary.unlink(missing_ok=True)
            raise ContractError(
                "V1 run-stateを原子的に保存できません"
            ) from exc

    def _fsync_directory(self) -> None:
        if os.name != "posix":
            return

        descriptor = os.open(self.runtime_root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
