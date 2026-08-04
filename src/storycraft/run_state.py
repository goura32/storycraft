"""閉じたrun-state保存形式と工程横断の不変条件を検証する。"""
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .artifact_registry import artifact_directory, artifact_spec
from .filesystem_security import assert_no_symlink_path
from .series_contracts import ContractError
from .time_contract import parse_utc_timestamp


RUNNING_STAGES = frozenset({
    "request_intake", "initial_design", "series_plan", "volume_plan", "chapter_plan",
    "scene_plan", "scene_card", "scene_prose", "scene_continuity", "scene_commit",
    "volume_publication",
})
_STAGE_TARGET_FIELDS: dict[str, frozenset[str]] = {
    "request_intake": frozenset(), "initial_design": frozenset(),
    "series_plan": frozenset(), "volume_plan": frozenset({"volume_number"}),
    "chapter_plan": frozenset({"volume_number", "chapter_number"}),
    "scene_plan": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "scene_card": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "scene_prose": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "scene_continuity": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "scene_commit": frozenset({"volume_number", "chapter_number", "scene_number"}),
    "volume_publication": frozenset({"volume_number"}),
}
_REQUIRED_FIELDS = frozenset({
    "schema_version", "workspace_id", "status", "last_error", "current_stage",
    "current_target", "current_selection_id", "pending_commit", "published_volumes",
    "created_at", "updated_at",
})
_ERROR_CODES = frozenset({
    "invalid_response_limit", "technical_retry_exhausted", "internal_error",
    "authority_inconsistency", "publication_invalid",
})
_CONTENT_KINDS = frozenset({
    "request", "initial-design", "series-plan", "volume-plan", "chapter-plan",
    "scene-plan", "scene-card", "scene-prose", "continuity-update",
})
_TARGET_KIND_CONTENT = "content_artifact"
_TARGET_KIND_FOR_ARTIFACT = {
    "adoption": "adoption_record",
    "selection": "selection_snapshot",
    "scene-commit": "scene_commit_record",
    "volume-publication": "publication_directory",
}
_TARGET_KINDS = frozenset({_TARGET_KIND_CONTENT, *_TARGET_KIND_FOR_ARTIFACT.values()})
_CONTENT_ARTIFACT_KINDS = frozenset({
    "request", "initial-design", "generation", "series-plan", "volume-plan", "chapter-plan",
    "scene-plan", "scene-card", "scene-prose", "continuity-update", "scene",
})
_TARGET_FIELDS = frozenset({"artifact_id", "target_kind", "artifact_kind", "staging_path", "final_path", "status"})


def target_artifact_kind(target: dict[str, Any]) -> str:
    """Return the registry kind represented by a closed pending target."""
    target_kind = target.get("target_kind")
    if target_kind == _TARGET_KIND_CONTENT:
        artifact_kind = target.get("artifact_kind")
        if not isinstance(artifact_kind, str):
            raise ContractError("content targetにはartifact_kindが必要です")
        return artifact_kind
    for artifact_kind, expected_target_kind in _TARGET_KIND_FOR_ARTIFACT.items():
        if target_kind == expected_target_kind:
            return artifact_kind
    raise ContractError("pending target_kindが不正です")


def make_pending_target(artifact_id: str, artifact_kind: str, staging_path: str, final_path: str) -> dict[str, Any]:
    """Build a manifest target with separate role and content namespaces."""
    target_kind = _TARGET_KIND_FOR_ARTIFACT.get(artifact_kind, _TARGET_KIND_CONTENT)
    return {
        "artifact_id": artifact_id,
        "target_kind": target_kind,
        "artifact_kind": artifact_kind if target_kind == _TARGET_KIND_CONTENT else None,
        "staging_path": staging_path,
        "final_path": final_path,
        "status": "pending",
    }


def validate_run_state(state: object) -> dict[str, Any]:
    """保存済みrun-stateが定義済みの閉じた契約と一致することを検証する。"""
    if not isinstance(state, dict):
        raise ContractError("run-stateはオブジェクトでなければなりません")
    _require_exact_fields(state, _REQUIRED_FIELDS, "run-state")
    if state["schema_version"] != 3:
        raise ContractError("run-state.schema_versionは3でなければなりません")
    _require_id(state["workspace_id"], "ws-", "workspace_id")
    _validate_timestamps(state)
    _validate_published_volumes(state["published_volumes"])
    status = state["status"]
    if status == "running":
        if state["last_error"] is not None:
            raise ContractError("runningではlast_errorはnullでなければなりません")
        _validate_current_work(state, allow_null_selection=state["current_stage"] == "request_intake")
    elif status == "blocked":
        _validate_error(state["last_error"])
        _validate_current_work(state, allow_null_selection=True)
    elif status == "completed":
        _validate_completed(state)
    else:
        raise ContractError("run-state.statusはrunning、blocked、completedのいずれかです")
    return state


def _validate_completed(state: dict[str, Any]) -> None:
    for field in ("last_error", "current_stage", "current_target", "pending_commit"):
        if state[field] is not None:
            raise ContractError(f"completedでは{field}はnullでなければなりません")
    _require_id(state["current_selection_id"], "selection-", "current_selection_id")
    if not state["published_volumes"]:
        raise ContractError("completedにはpublished_volumesが必要です")


def _validate_current_work(state: dict[str, Any], *, allow_null_selection: bool) -> None:
    stage = state["current_stage"]
    if stage not in RUNNING_STAGES:
        raise ContractError(f"run-state.current_stageが現行工程ではありません: {stage!r}")
    _validate_target(stage, state["current_target"])
    selection_id = state["current_selection_id"]
    if selection_id is None:
        if not (allow_null_selection and stage == "request_intake"):
            raise ContractError("current_selection_idはrequest_intake以外で必要です")
    else:
        _require_id(selection_id, "selection-", "current_selection_id")
    _validate_pending_commit(
        state["pending_commit"], state["published_volumes"], state["current_selection_id"],
        state["status"], state["current_stage"],
    )


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


def _validate_pending_commit(
    value: object, published_volumes: object, current_selection_id: object,
    status: object, current_stage: object,
) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise ContractError("pending_commitはnullまたはオブジェクトでなければなりません")
    _require_exact_fields(value, {"kind", "staging_path", "input_selection_id", "output_selection_id", "state_update", "targets"}, "pending_commit")
    kind = value["kind"]
    if kind not in {"candidate_adoption", "scene_commit", "volume_publication"}:
        raise ContractError("pending_commit.kindが不正です")
    _validate_staging_root(value["staging_path"])
    targets = _validate_manifest_targets(value["targets"], value["staging_path"])
    input_selection_id = value["input_selection_id"]
    output_selection_id = value["output_selection_id"]
    if kind == "volume_publication":
        _require_id(input_selection_id, "selection-", "pending_commit.input_selection_id")
        if output_selection_id is not None:
            raise ContractError("volume_publicationのoutput_selection_idはnullでなければなりません")
    else:
        _require_id(output_selection_id, "selection-", "pending_commit.output_selection_id")
        if input_selection_id is not None:
            _require_id(input_selection_id, "selection-", "pending_commit.input_selection_id")
        elif not (
            kind == "candidate_adoption"
            and _is_bootstrap_request_adoption(targets)
            and status == "running"
            and current_stage == "request_intake"
            and current_selection_id is None
        ):
            raise ContractError("input_selection_id=nullはbootstrap request adoptionだけに許可されます")
    if input_selection_id is not None and input_selection_id != current_selection_id:
        raise ContractError("pending_commit.input_selection_idはrun-state.current_selection_idと一致しなければなりません")
    _validate_target_set(kind, targets)
    _validate_state_update(kind, value["state_update"], input_selection_id, output_selection_id, targets, published_volumes)


def _validate_staging_root(value: object) -> None:
    _validate_manifest_path(value, "pending_commit.staging_path")
    if not isinstance(value, str) or not value.startswith("runtime/staging/"):
        raise ContractError("pending_commit.staging_pathが不正です")


def _validate_manifest_targets(value: object, staging_root: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ContractError("pending_commit.targetsは空でない配列でなければなりません")
    assert isinstance(staging_root, str)
    targets: list[dict[str, Any]] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for target in value:
        if not isinstance(target, dict):
            raise ContractError("pending_commit.targetsの要素が不正です")
        _require_exact_fields(target, _TARGET_FIELDS, "pending_commit.targets要素")
        _validate_manifest_path(target["staging_path"], "pending_commit.targets.staging_path")
        _validate_manifest_path(target["final_path"], "pending_commit.targets.final_path")
        if not target["staging_path"].startswith(staging_root + "/"):
            raise ContractError("pending_commit.targets.staging_pathはmanifest staging配下でなければなりません")
        if target["status"] not in {"pending", "finalized"}:
            raise ContractError("pending_commit.targets.statusが不正です")
        target_kind = target["target_kind"]
        artifact_kind = target["artifact_kind"]
        if target_kind not in _TARGET_KINDS:
            raise ContractError("pending_commit.targets.target_kindが不正です")
        if target_kind == _TARGET_KIND_CONTENT:
            if artifact_kind not in _CONTENT_ARTIFACT_KINDS:
                raise ContractError("content targetのartifact_kindが不正です")
        elif artifact_kind is not None or target_artifact_kind(target) not in _TARGET_KIND_FOR_ARTIFACT:
            raise ContractError("non-content targetのartifact_kindが不正です")
        artifact_id = target["artifact_id"]
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in ids:
            raise ContractError("pending_commit.targets.artifact_idが不正です")
        if target["final_path"] in paths:
            raise ContractError("pending_commit.targets.final_pathが重複しています")
        _validate_canonical_target(target)
        ids.add(artifact_id)
        paths.add(target["final_path"])
        targets.append(target)
    return targets


def _validate_target_set(kind: str, targets: list[dict[str, Any]]) -> None:
    kinds = [target_artifact_kind(target) for target in targets]
    if kind == "candidate_adoption":
        expected = {"adoption", "selection"}
        content = [item for item in kinds if item in _CONTENT_KINDS]
        generations = [item for item in kinds if item == "generation"]
        valid_content = (
            len(content) == 1 and not generations
            or content == ["initial-design"] and len(generations) == 1
        )
        if set(kinds) - _CONTENT_KINDS - expected - {"generation"} or not valid_content or kinds.count("adoption") != 1 or kinds.count("selection") != 1:
            raise ContractError("candidate_adoptionのtargetsが不正です")
    elif kind == "scene_commit":
        if set(kinds) != {"scene", "generation", "scene-commit", "selection"} or len(targets) != 4:
            raise ContractError("scene_commitのtargetsが不正です")
    elif kinds != ["volume-publication"]:
        raise ContractError("volume_publicationのtargetsが不正です")


def _is_bootstrap_request_adoption(targets: list[dict[str, Any]]) -> bool:
    return any(target_artifact_kind(target) == "request" for target in targets)


def _validate_state_update(
    kind: str, value: object, input_selection_id: object, output_selection_id: object,
    targets: list[dict[str, Any]], published_volumes: object,
) -> None:
    if not isinstance(value, dict):
        raise ContractError("pending_commit.state_updateはオブジェクトでなければなりません")
    fields = {"current_selection_id", "current_stage", "current_target"}
    completes = kind == "volume_publication" and value.get("status") == "completed"
    if kind == "volume_publication":
        fields.add("published_volumes")
    if completes:
        fields.update({"status", "last_error"})
    _require_exact_fields(value, fields, "pending_commit.state_update")
    expected_selection = input_selection_id if kind == "volume_publication" else output_selection_id
    if value["current_selection_id"] != expected_selection:
        raise ContractError("pending_commit.state_update.current_selection_idが不正です")
    if kind != "volume_publication" and not any(
        target_artifact_kind(target) == "selection" and target["artifact_id"] == output_selection_id
        for target in targets
    ):
        raise ContractError("pending_commit.output_selection_idは後続selection targetと一致しなければなりません")
    stage = value["current_stage"]
    if completes:
        if value["last_error"] is not None or stage is not None or value["current_target"] is not None:
            raise ContractError("最終volume_publicationのstate_updateが不正です")
    else:
        if stage not in RUNNING_STAGES:
            raise ContractError("pending_commit.state_update.current_stageが不正です")
        _validate_target(stage, value["current_target"])
    if kind == "volume_publication":
        _validate_published_volumes(value["published_volumes"])
        publication = next(target for target in targets if target_artifact_kind(target) == "volume-publication")
        entries = value["published_volumes"]
        if not entries:
            raise ContractError("volume_publication.state_update.published_volumesが不正です")
        if not isinstance(published_volumes, list) or entries != [*published_volumes, entries[-1]]:
            raise ContractError("volume_publication.state_update.published_volumesは既存値末尾への一件追加でなければなりません")
        if not entries or entries[-1]["publication_id"] != publication["artifact_id"]:
            raise ContractError("volume_publication.state_update.published_volumesが不正です")


def _validate_canonical_target(target: dict[str, Any]) -> None:
    artifact_id, kind, final_path = target["artifact_id"], target_artifact_kind(target), target["final_path"]
    try:
        artifact_spec(kind).match_id(artifact_id)
        expected_path = artifact_directory(kind, artifact_id).as_posix()
    except ContractError as exc:
        raise ContractError("pending_commit.targetsのartifact ID、kind、final_pathが正本配置と一致しません") from exc
    if final_path != expected_path:
        raise ContractError("pending_commit.targetsのartifact ID、kind、final_pathが正本配置と一致しません")


def _validate_manifest_path(value: object, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label}が不正です")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value or value.startswith("./"):
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
        try:
            match = artifact_spec("volume-publication").match_id(entry["publication_id"])
        except ContractError as exc:
            raise ContractError("published_volumes.publication_idが正規IDではありません") from exc
        if int(match.group("volume")) != expected:
            raise ContractError("published_volumes.publication_idの巻番号が不正です")


def _validate_timestamps(state: dict[str, Any]) -> None:
    created = _parse_timestamp(state["created_at"], "created_at")
    updated = _parse_timestamp(state["updated_at"], "updated_at")
    if updated < created:
        raise ContractError("run-state.updated_atはcreated_atより前にできません")


def _parse_timestamp(value: object, field: str) -> datetime:
    return parse_utc_timestamp(value, field)


def _require_exact_fields(value: dict[str, Any], fields: set[str] | frozenset[str], label: str) -> None:
    if set(value) != set(fields):
        raise ContractError(f"{label}のfield構成が不正です")


def _require_id(value: object, prefix: str, label: str) -> None:
    if prefix == "selection-":
        try:
            artifact_spec("selection").match_id(value)
        except ContractError as exc:
            raise ContractError(f"{label}が不正です") from exc
        return
    if prefix == "ws-":
        if not isinstance(value, str) or re.fullmatch(r"ws-[A-Za-z0-9_-]+", value) is None:
            raise ContractError(f"{label}が不正です")
        return
    if not isinstance(value, str) or not value.startswith(prefix) or len(value) == len(prefix) or "/" in value or "\\" in value:
        raise ContractError(f"{label}が不正です")


def validate_recovery_run_state(state: object) -> dict[str, Any]:
    return validate_run_state(state)


def is_stale_scene_commit_recovery_state(state: object) -> bool:
    return False


class RunStateStore:
    """runtime/run-state.json を原子的に永続化する。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.runtime_root = self.workspace_root / "runtime"
        self.path = self.runtime_root / "run-state.json"

    def exists(self) -> bool:
        return self.path.is_file() and not self.path.is_symlink()

    def _read(self) -> object:
        assert_no_symlink_path(self.runtime_root, require_directory=True)
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
        assert_no_symlink_path(self.runtime_root)
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        assert_no_symlink_path(self.runtime_root, require_directory=True)
        if self.path.is_symlink():
            raise ContractError("run-stateはsymlinkであってはなりません")
        temporary = self.path.with_suffix(".json.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as handle:
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
