"""run-state v3 の形と工程横断の不変条件を検証する。"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .series_contracts import ContractError


RUNNING_STAGES = frozenset({
    "request_intake",
    "initial_design",
    "series_plan",
    "volume_plan",
    "chapter_plan",
    "scene_plan",
    "scene_card",
    "scene_prose",
    "scene_continuity",
    "scene_commit",
    "volume_publication",
})


_STAGE_TARGET_FIELDS: dict[str, frozenset[str]] = {
    "request_intake": frozenset(),
    "initial_design": frozenset(),
    "series_plan": frozenset(),
    "volume_plan": frozenset({"volume_number"}),
    "chapter_plan": frozenset({"volume_number", "chapter_number"}),
    "scene_plan": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "scene_card": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "scene_prose": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "scene_continuity": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "scene_commit": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "volume_publication": frozenset({"volume_number"}),
}

# V1 (schema_version 3) required fields: note that run_id and stop_reason are removed.
_REQUIRED_FIELDS = frozenset({
    "schema_version",
    "workspace_id",
    "status",
    "last_error",
    "current_stage",
    "current_target",
    "current_selection_id",
    "active_candidate",
    "active_scene_id",
    "pending_commit",
    "published_volumes",
    "created_at",
    "updated_at",
})
_ERROR_CODES = frozenset({
    "invalid_response_limit",
    "technical_retry_exhausted",
    "internal_error",
    "authority_inconsistency",
    "publication_invalid",
    "workspace_invalid",
})


def validate_run_state(state: object) -> dict[str, Any]:
    """run-state v3 の形と工程横断の不変条件を検証する。"""
    if not isinstance(state, dict):
        raise ContractError("run-stateはオブジェクトでなければなりません")
    # Required fields must be present; extra fields are allowed.
    missing = _REQUIRED_FIELDS - set(state.keys())
    if missing:
        raise ContractError(f"run-stateに必須フィールドがありません: {missing}")
    if state["schema_version"] != 3:
        raise ContractError("run-state.schema_versionは3でなければなりません")
    _require_id(state["workspace_id"], "ws-", "workspace_id")
    # run_id is not required in v3
    _validate_timestamps(state)
    _validate_published_volumes(state["published_volumes"])

    status = state["status"]
    if status == "running":
        _validate_running(state)
    elif status == "blocked":
        _validate_blocked(state)
    elif status == "completed":
        _validate_completed(state)
    else:
        raise ContractError("run-state.statusはrunning、blocked、completedのいずれかです")
    return state


def _validate_running(state: dict[str, Any]) -> None:
    # runningではlast_errorはnullでなければならない（stop_reasonは存在しない）
    if state["last_error"] is not None:
        raise ContractError("runningではlast_errorはnullでなければなりません")
    _validate_current_work(state, allow_null_selection=state["current_stage"] == "request_intake")


def _validate_blocked(state: dict[str, Any]) -> None:
    # blockedではlast_errorが必要で、そのcodeがエラーコードのいずれかであること
    _validate_error(state["last_error"])
    _validate_current_work(state, allow_null_selection=True)


def _validate_completed(state: dict[str, Any]) -> None:
    # completedでは以下のフィールドはnullでなければならない
    for field in ("last_error", "current_stage", "current_target", "active_candidate", "active_scene_id", "pending_commit"):
        if state[field] is not None:
            raise ContractError(f"completedでは{field}はnullでなければなりません")
    _require_id(state["current_selection_id"], "selection-", "current_selection_id")
    if not state["published_volumes"]:
        raise ContractError("completedにはpublished_volumesが必要です")


def _validate_current_work(state: dict[str, Any], *, allow_null_selection: bool) -> None:
    stage = state["current_stage"]
    if stage not in RUNNING_STAGES:
        raise ContractError(f"run-state.current_stageがV3工程ではありません: {stage!r}")
    target = state["current_target"]
    _validate_target(stage, target)
    selection_id = state["current_selection_id"]
    if selection_id is None:
        if not (allow_null_selection and stage == "request_intake"):
            raise ContractError("current_selection_idはrequest_intake以外で必要です")
    else:
        _require_id(selection_id, "selection-", "current_selection_id")
    _validate_active_candidate(state["active_candidate"])
    _validate_optional_id(state["active_scene_id"], "scene-", "active_scene_id")
    _validate_pending_commit(state["pending_commit"])


def _validate_target(stage: str, target: object) -> None:
    if not isinstance(target, dict):
        raise ContractError("run-state.current_targetはオブジェクトでなければなりません")
    expected = _STAGE_TARGET_FIELDS[stage]
    if set(target) != expected:
        raise ContractError(f"run-state.current_targetが{stage}の座標と一致しません")
    for field in expected:
        value = target[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ContractError(f"run-state.current_target.{field}は1以上の整数でなければなりません")


def _validate_active_candidate(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ContractError("active_candidateはnullまたはオブジェクトでなければなりません")
    _require_exact_fields(value, {"candidate_id", "stage", "version", "input_selection_id", "review_record_id"}, "active_candidate")
    _require_id(value["candidate_id"], "candidate-", "active_candidate.candidate_id")
    if value["stage"] not in RUNNING_STAGES - {"volume_publication"}:
        raise ContractError("active_candidate.stageが不正です")
    if not isinstance(value["version"], int) or isinstance(value["version"], bool) or value["version"] < 1:
        raise ContractError("active_candidate.versionは1以上の整数でなければなりません")
    _require_id(value["input_selection_id"], "selection-", "active_candidate.input_selection_id")
    if value["review_record_id"] is not None:
        _require_id(value["review_record_id"], "review-", "active_candidate.review_record_id")


def _validate_pending_commit(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ContractError("pending_commitはnullまたはオブジェクトでなければなりません")
    _require_exact_fields(value, {"kind", "staging_path", "input_selection_id", "output_selection_id", "state_update", "targets"}, "pending_commit")
    if value["kind"] not in {"candidate_adoption", "scene_commit", "volume_publication"}:
        raise ContractError("pending_commit.kindが不正です")
    if not isinstance(value["staging_path"], str) or not value["staging_path"].startswith("runtime/staging/"):
        raise ContractError("pending_commit.staging_pathが不正です")
    _require_id(value["input_selection_id"], "selection-", "pending_commit.input_selection_id")
    if value["output_selection_id"] is not None:
        _require_id(value["output_selection_id"], "selection-", "pending_commit.output_selection_id")
    if not isinstance(value["state_update"], dict):
        raise ContractError("pending_commit.state_updateはオブジェクトでなければなりません")
    targets = value["targets"]
    if not isinstance(targets, list) or not targets:
        raise ContractError("pending_commit.targetsは空でない配列でなければなりません")
    for target in targets:
        if not isinstance(target, dict):
            raise ContractError("pending_commit.targetsの要素が不正です")
        _require_exact_fields(target, {"artifact_id", "artifact_kind", "staging_path", "final_path", "sha256", "status"}, "pending_commit.targets要素")
        if not isinstance(target["artifact_id"], str) or not target["artifact_id"]:
            raise ContractError("pending_commit.targets.artifact_idが不正です")
        if not isinstance(target["artifact_kind"], str) or not target["artifact_kind"]:
            raise ContractError("pending_commit.targets.artifact_kindが不正です")
        _validate_manifest_path(target["staging_path"], "pending_commit.targets.staging_path")
        _validate_manifest_path(target["final_path"], "pending_commit.targets.final_path")
        if not isinstance(target["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", target["sha256"]) is None:
            raise ContractError("pending_commit.targets.sha256が不正です")
        if target["status"] not in {"pending", "finalized"}:
            raise ContractError("pending_commit.targets.statusが不正です")


def _validate_manifest_path(value: object, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label}が不正です")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ContractError(f"{label}はworkspace内の正規相対pathでなければなりません")


def _validate_error(value: object) -> None:
    if not isinstance(value, dict):
        raise ContractError("blockedではlast_errorが必要です")
    _require_exact_fields(value, {"code", "message", "evidence_refs", "occurred_at"}, "last_error")
    if value["code"] not in _ERROR_CODES:
        raise ContractError("last_error.codeが不正です")
    if not isinstance(value["message"], str) or not value["message"]:
        raise ContractError("last_error.messageが不正です")
    if not isinstance(value["evidence_refs"], list) or not all(isinstance(item, str) and item for item in value["evidence_refs"]):
        raise ContractError("last_error.evidence_refsが不正です")
    _parse_timestamp(value["occurred_at"], "last_error.occurred_at")


def _validate_published_volumes(value: object) -> None:
    if not isinstance(value, list):
        raise ContractError("published_volumesは配列でなければなりません")
    for expected, entry in enumerate(value, 1):
        if not isinstance(entry, dict) or set(entry) != {"volume_number", "publication_id"}:
            raise ContractError("published_volumesの要素が不正です")
        if entry["volume_number"] != expected:
            raise ContractError("published_volumesは第一巻から欠番なく並ぶ必要があります")
        _require_id(entry["publication_id"], f"volume-pub-v{expected:02d}-", "published_volumes.publication_id")


def _validate_timestamps(state: dict[str, Any]) -> None:
    created = _parse_timestamp(state["created_at"], "created_at")
    updated = _parse_timestamp(state["updated_at"], "updated_at")
    if updated < created:
        raise ContractError("run-state.updated_atはcreated_atより前にできません")


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ContractError(f"{field}はISO 8601文字列でなければなりません")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{field}がISO 8601形式ではありません") from exc


def _require_exact_fields(value: dict[str, Any], fields: set[str] | frozenset[str], label: str) -> None:
    if set(value) != set(fields):
        raise ContractError(f"{label}のfield構成が不正です")


def _require_id(value: object, prefix: str, label: str) -> None:
    if not isinstance(value, str) or not value.startswith(prefix) or len(value) == len(prefix):
        raise ContractError(f"{label}が不正です")


def _validate_optional_id(value: object, prefix: str, label: str) -> None:
    if value is not None:
        _require_id(value, prefix, label)


# v3 は manifest 自体で正常な中断を表現する。旧特殊状態は受け付けない。
def validate_recovery_run_state(state: object) -> dict[str, Any]:
    return validate_run_state(state)


def is_stale_scene_commit_recovery_state(state: object) -> bool:
    return False


class RunStateStore:
    """runtime/run-state.json の原子的な v3 永続化。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.runtime_root = self.workspace_root / "runtime"
        self.path = self.runtime_root / "run-state.json"

    def exists(self) -> bool:
        return self.path.is_file()

    def _read(self) -> object:
        if not self.exists():
            raise ContractError("run-stateがありません")
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContractError("run-stateがJSONとして読めません") from exc
        except OSError as exc:
            raise ContractError("run-stateを読み込めません") from exc

    def load(self) -> dict[str, Any]:
        return validate_run_state(self._read())

    def load_recovery(self) -> dict[str, Any]:
        return validate_run_state(self._read())

    def save(self, state: dict[str, Any]) -> None:
        validate_run_state(state)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            validate_run_state(json.loads(temporary.read_text(encoding="utf-8")))
            os.replace(temporary, self.path)
            if os.name == "posix":
                descriptor = os.open(self.runtime_root, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        except (OSError, json.JSONDecodeError) as exc:
            temporary.unlink(missing_ok=True)
            raise ContractError("run-stateを原子的に保存できません") from exc