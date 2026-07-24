"""Scene Commitと後継Generationの決定的構築。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from typing import Any

from .series_contracts import ContractError


_GENERATION_FILES = {
    "canon.json",
    "state.json",
    "evidence.json",
    "commit.json",
}

_SCENE_COMMIT_FIELDS = {
    "schema_version",
    "scene_id",
    "scene_version",
    "parent_generation_id",
    "result_generation_id",
    "scene_card_version",
    "continuity_update_id",
    "committed_at",
    "commit_summary",
}

_STATE_SOURCES = {
    "character_state": "characters",
    "relationship_state": "relationships",
    "thread_state": "threads",
    "inventory_state": "inventory",
    "commitment_state": "commitments",
}


def state_target_record(
    state: dict[str, Any],
    target_type: str,
    target_id: str,
) -> dict[str, Any]:
    """Continuity targetに対応するState recordを返す。"""
    if not isinstance(state, dict):
        raise ContractError(
            "Generation Stateはobjectが必要です"
        )

    if target_type == "timeline_state":
        if target_id != "timeline":
            raise ContractError(
                "timeline_stateのtarget_idはtimelineが必要です"
            )
        record = state.get("timeline")
        if not isinstance(record, dict):
            raise ContractError(
                "Generation timeline Stateが不正です"
            )
        return record

    source_name = _STATE_SOURCES.get(target_type)
    if source_name is None:
        raise ContractError(
            "Continuity target_typeが不正です"
        )

    source = state.get(source_name)
    if (
        not isinstance(source, dict)
        or target_id not in source
    ):
        raise ContractError(
            "Continuityが未知のState targetを参照しています"
        )

    record = source[target_id]
    if not isinstance(record, dict):
        raise ContractError(
            "Continuity targetのcurrent Stateが不正です"
        )
    return record


def apply_continuity_operations(
    parent_state: dict[str, Any],
    continuity: dict[str, Any],
) -> dict[str, Any]:
    """Continuityのset OperationをStateコピーへ適用する。"""
    if not isinstance(continuity, dict):
        raise ContractError(
            "Continuityはobjectが必要です"
        )

    operations = continuity.get("operations")
    if not isinstance(operations, list):
        raise ContractError(
            "Continuity.operationsは配列が必要です"
        )

    result = deepcopy(parent_state)
    seen: set[tuple[str, str, str]] = set()

    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise ContractError(
                f"Continuity operationが不正です: {index}"
            )

        target_type = _required_string(
            operation.get("target_type"),
            f"operations[{index}].target_type",
        )
        target_id = _required_string(
            operation.get("target_id"),
            f"operations[{index}].target_id",
        )
        field = _required_string(
            operation.get("field"),
            f"operations[{index}].field",
        )

        if operation.get("operation") != "set":
            raise ContractError(
                "Scene Generationではset Operationだけを"
                f"適用できます: operations[{index}]"
            )

        key = (target_type, target_id, field)
        if key in seen:
            raise ContractError(
                "同じState fieldを複数回更新できません"
            )
        seen.add(key)

        record = state_target_record(
            result,
            target_type,
            target_id,
        )
        if field not in record:
            raise ContractError(
                "Continuityが存在しないState fieldを"
                f"参照しています: operations[{index}].field"
            )

        current = record[field]
        if operation.get("old_value") != current:
            raise ContractError(
                "Continuity old_valueが親Generationと"
                f"一致しません: operations[{index}]"
            )

        new_value = operation.get("new_value")
        if new_value == current:
            raise ContractError(
                "Continuityにno-op更新を含められません"
            )

        record[field] = deepcopy(new_value)

    return result


def build_scene_commit(
    *,
    scene_card: dict[str, Any],
    continuity: dict[str, Any],
) -> dict[str, Any]:
    """Scene CardとContinuityからScene Commitを構築する。"""
    if not isinstance(scene_card, dict):
        raise ContractError(
            "Scene Cardはobjectが必要です"
        )
    if not isinstance(continuity, dict):
        raise ContractError(
            "Continuityはobjectが必要です"
        )

    scene_id = _required_string(
        scene_card.get("scene_id"),
        "Scene Card.scene_id",
    )
    if continuity.get("scene_id") != scene_id:
        raise ContractError(
            "Scene CardとContinuityのscene_idが一致しません"
        )

    parent_generation_id = _required_generation_id(
        scene_card.get("basis_generation_id"),
        "Scene Card.basis_generation_id",
    )
    if (
        continuity.get("basis_generation_id")
        != parent_generation_id
    ):
        raise ContractError(
            "Scene CardとContinuityのbasis Generationが"
            "一致しません"
        )

    result_generation_id = _required_generation_id(
        continuity.get("result_generation_id"),
        "Continuity.result_generation_id",
    )
    _validate_generation_order(
        parent_generation_id,
        result_generation_id,
    )

    scene_version = _positive_integer(
        scene_card.get("version"),
        "Scene Card.version",
    )
    continuity_id = _required_string(
        continuity.get("continuity_id"),
        "Continuity.continuity_id",
    )
    committed_at = _required_timestamp(
        continuity.get("created_at"),
        "Continuity.created_at",
    )
    summary = _required_string(
        continuity.get("summary"),
        "Continuity.summary",
    )

    return {
        "schema_version": 1,
        "scene_id": scene_id,
        "scene_version": scene_version,
        "parent_generation_id": parent_generation_id,
        "result_generation_id": result_generation_id,
        "scene_card_version": scene_version,
        "continuity_update_id": continuity_id,
        "committed_at": committed_at,
        "commit_summary": summary,
    }


def validate_scene_commit(
    value: dict[str, Any],
    *,
    scene_card: dict[str, Any],
    continuity: dict[str, Any],
) -> None:
    """Scene Commitを決定的構築結果へ照合する。"""
    if not isinstance(value, dict):
        raise ContractError(
            "Scene Commitはobjectが必要です"
        )
    if set(value) != _SCENE_COMMIT_FIELDS:
        raise ContractError(
            "Scene Commitのfield構成が不正です"
        )

    expected = build_scene_commit(
        scene_card=scene_card,
        continuity=continuity,
    )
    if value != expected:
        raise ContractError(
            "Scene CommitがScene成果物からの"
            "決定的構築結果と一致しません"
        )


def build_scene_generation(
    *,
    parent_generation: dict[str, dict[str, Any]],
    continuity: dict[str, Any],
    scene_commit: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """親GenerationとContinuityから後継Generationを構築する。"""
    parent_id = _validate_generation_container(
        parent_generation,
    )
    _validate_scene_commit_shape(scene_commit)
    _validate_continuity_links(continuity)

    if scene_commit["parent_generation_id"] != parent_id:
        raise ContractError(
            "Scene Commitのparent Generationが"
            "入力Generationと一致しません"
        )

    result_id = _required_generation_id(
        scene_commit["result_generation_id"],
        "Scene Commit.result_generation_id",
    )
    if continuity.get("result_generation_id") != result_id:
        raise ContractError(
            "Scene CommitとContinuityのresult Generationが"
            "一致しません"
        )
    if continuity.get("basis_generation_id") != parent_id:
        raise ContractError(
            "Continuityのbasis Generationが"
            "親Generationと一致しません"
        )
    if continuity.get("scene_id") != scene_commit["scene_id"]:
        raise ContractError(
            "ContinuityとScene Commitのscene_idが"
            "一致しません"
        )

    _validate_generation_order(parent_id, result_id)

    canon = deepcopy(parent_generation["canon.json"])
    canon["generation_id"] = result_id

    state = apply_continuity_operations(
        parent_generation["state.json"],
        continuity,
    )
    state["generation_id"] = result_id

    evidence = deepcopy(
        parent_generation["evidence.json"]
    )
    parent_evidence = evidence.get("evidence")
    if not isinstance(parent_evidence, list):
        raise ContractError(
            "親Generationのevidence配列が不正です"
        )

    new_evidence = deepcopy(continuity["evidence"])
    existing_ids = {
        record.get("evidence_id")
        for record in parent_evidence
        if isinstance(record, dict)
    }
    added_ids = {
        record.get("evidence_id")
        for record in new_evidence
        if isinstance(record, dict)
    }

    if (
        len(added_ids) != len(new_evidence)
        or None in added_ids
        or existing_ids & added_ids
    ):
        raise ContractError(
            "Generationへ追加するEvidence IDが"
            "重複または不正です"
        )

    evidence["generation_id"] = result_id
    evidence["evidence"] = (
        parent_evidence + new_evidence
    )

    changed_targets = [
        (
            f"{operation['target_id']}."
            f"{operation['field']}"
        )
        for operation in continuity["operations"]
    ]

    commit = {
        "schema_version": 1,
        "generation_id": result_id,
        "parent_generation_id": parent_id,
        "commit_type": "scene",
        "source_artifact_type": "scene",
        "source_artifact_id": scene_commit["scene_id"],
        "summary": scene_commit["commit_summary"],
        "changed_targets": changed_targets,
        "created_at": scene_commit["committed_at"],
    }

    return {
        "canon.json": canon,
        "state.json": state,
        "evidence.json": evidence,
        "commit.json": commit,
    }


def validate_scene_generation(
    files: dict[str, dict[str, Any]],
    *,
    parent_generation: dict[str, dict[str, Any]],
    continuity: dict[str, Any],
    scene_commit: dict[str, Any],
) -> None:
    """後継Generationを決定的構築結果へ照合する。"""
    _validate_generation_container(files)

    expected = build_scene_generation(
        parent_generation=parent_generation,
        continuity=continuity,
        scene_commit=scene_commit,
    )
    if files != expected:
        raise ContractError(
            "Scene Generationが親Generationと"
            "Continuityからの決定的構築結果と一致しません"
        )


def _validate_generation_container(
    files: dict[str, dict[str, Any]],
) -> str:
    if not isinstance(files, dict):
        raise ContractError(
            "Generationはfile mapが必要です"
        )
    if set(files) != _GENERATION_FILES:
        raise ContractError(
            "Generationのfile構成が不正です"
        )

    generation_ids: set[str] = set()
    for name in sorted(_GENERATION_FILES):
        value = files[name]
        if not isinstance(value, dict):
            raise ContractError(
                f"Generationの{name}はobjectが必要です"
            )
        generation_ids.add(
            _required_generation_id(
                value.get("generation_id"),
                f"Generation {name}.generation_id",
            )
        )

    if len(generation_ids) != 1:
        raise ContractError(
            "Generation file間でgeneration_idが"
            "一致しません"
        )
    return next(iter(generation_ids))


def _validate_scene_commit_shape(
    value: dict[str, Any],
) -> None:
    if not isinstance(value, dict):
        raise ContractError(
            "Scene Commitはobjectが必要です"
        )
    if set(value) != _SCENE_COMMIT_FIELDS:
        raise ContractError(
            "Scene Commitのfield構成が不正です"
        )
    if value["schema_version"] != 1:
        raise ContractError(
            "Scene Commit.schema_versionは1が必要です"
        )

    _required_string(value["scene_id"], "Scene Commit.scene_id")
    _positive_integer(
        value["scene_version"],
        "Scene Commit.scene_version",
    )
    _positive_integer(
        value["scene_card_version"],
        "Scene Commit.scene_card_version",
    )
    if value["scene_version"] != value["scene_card_version"]:
        raise ContractError(
            "Scene versionとScene Card versionが"
            "一致しません"
        )

    parent_id = _required_generation_id(
        value["parent_generation_id"],
        "Scene Commit.parent_generation_id",
    )
    result_id = _required_generation_id(
        value["result_generation_id"],
        "Scene Commit.result_generation_id",
    )
    _validate_generation_order(parent_id, result_id)

    _required_string(
        value["continuity_update_id"],
        "Scene Commit.continuity_update_id",
    )
    _required_timestamp(
        value["committed_at"],
        "Scene Commit.committed_at",
    )
    _required_string(
        value["commit_summary"],
        "Scene Commit.commit_summary",
    )


def _validate_continuity_links(
    continuity: dict[str, Any],
) -> None:
    if not isinstance(continuity, dict):
        raise ContractError(
            "Continuityはobjectが必要です"
        )

    operations = continuity.get("operations")
    evidence = continuity.get("evidence")
    if not isinstance(operations, list):
        raise ContractError(
            "Continuity.operationsは配列が必要です"
        )
    if not isinstance(evidence, list):
        raise ContractError(
            "Continuity.evidenceは配列が必要です"
        )

    evidence_ids: list[str] = []
    for index, record in enumerate(evidence):
        if not isinstance(record, dict):
            raise ContractError(
                f"Continuity Evidenceが不正です: {index}"
            )
        evidence_ids.append(
            _required_string(
                record.get("evidence_id"),
                f"evidence[{index}].evidence_id",
            )
        )

    if len(evidence_ids) != len(set(evidence_ids)):
        raise ContractError(
            "Continuity Evidence IDが重複しています"
        )

    known = set(evidence_ids)
    used: set[str] = set()
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise ContractError(
                f"Continuity operationが不正です: {index}"
            )
        references = operation.get("evidence_ids")
        if (
            not isinstance(references, list)
            or not references
            or any(
                not isinstance(identifier, str)
                or identifier not in known
                for identifier in references
            )
        ):
            raise ContractError(
                "Continuity operationのEvidence参照が"
                f"不正です: operations[{index}]"
            )
        used.update(references)

    if used != known:
        raise ContractError(
            "未使用のContinuity Evidenceがあります"
        )


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(
            f"{field}は空でない文字列が必要です"
        )
    return value


def _positive_integer(value: object, field: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ContractError(
            f"{field}は1以上の整数が必要です"
        )
    return value


def _required_generation_id(
    value: object,
    field: str,
) -> str:
    identifier = _required_string(value, field)
    if re.fullmatch(r"gen-\d{6}", identifier) is None:
        raise ContractError(
            f"{field}が不正です"
        )
    return identifier


def _validate_generation_order(
    parent_id: str,
    result_id: str,
) -> None:
    parent_number = int(parent_id.removeprefix("gen-"))
    result_number = int(result_id.removeprefix("gen-"))
    if result_number <= parent_number:
        raise ContractError(
            "result Generation IDは親Generationより"
            "後でなければなりません"
        )


def _required_timestamp(
    value: object,
    field: str,
) -> str:
    timestamp = _required_string(value, field)
    try:
        parsed = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ContractError(
            f"{field}がISO 8601形式ではありません"
        ) from exc
    if parsed.tzinfo is None:
        raise ContractError(
            f"{field}にはtimezoneが必要です"
        )
    return timestamp
