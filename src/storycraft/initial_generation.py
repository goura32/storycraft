"""採用済みInitial DesignとInitial Generationのcode-only契約。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from .series_contracts import ContractError


INTEGRATED_FIELDS = (
    "concept",
    "characters",
    "relationships",
    "world",
    "locations",
    "world_rules",
    "knowledge_facts",
    "character_knowledge",
    "threads",
    "ending",
    "long_term_arcs",
)


def build_accepted_initial_design(
    integrated: dict[str, Any],
    brief: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Review済み統合Candidateへ採用metadataを付与する。"""
    return {
        "schema_version": 1,
        "design_id": "initial-design-0001",
        "version": 1,
        "brief_id": "brief-0001",
        **deepcopy(integrated),
        "created_at": created_at,
    }


def validate_accepted_initial_design(
    value: dict[str, Any],
    integrated: dict[str, Any],
    brief: dict[str, Any],
) -> None:
    """採用済みInitial Designが統合Candidateを保持することを検証する。"""
    if not isinstance(value, dict):
        raise ContractError(
            "採用済みInitial Designはobjectが必要です"
        )

    expected_fields = {
        "schema_version",
        "design_id",
        "version",
        "brief_id",
        "created_at",
        *INTEGRATED_FIELDS,
    }
    if set(value) != expected_fields:
        raise ContractError(
            "採用済みInitial Designのfield構成が不正です"
        )

    if value["schema_version"] != 1:
        raise ContractError(
            "Initial Design.schema_versionは1が必要です"
        )
    if value["design_id"] != "initial-design-0001":
        raise ContractError(
            "Initial Design.design_idが不正です"
        )
    if value["version"] != 1:
        raise ContractError(
            "Initial Design.versionは1が必要です"
        )
    if value["brief_id"] != "brief-0001":
        raise ContractError(
            "Initial Design.brief_idはbrief-0001が必要です"
        )
    _validate_timestamp(
        value["created_at"],
        "Initial Design.created_at",
    )

    adopted_content = {
        field: value[field]
        for field in INTEGRATED_FIELDS
    }
    if adopted_content != integrated:
        raise ContractError(
            "採用済みInitial DesignがReview済み"
            "統合Candidateと一致しません"
        )


def build_initial_generation(
    initial_design: dict[str, Any],
    *,
    generation_id: str,
    created_at: str,
) -> dict[str, dict[str, Any]]:
    """Initial Designから決定的なInitial Generationを構築する。"""
    knowledge_by_character: dict[str, dict[str, str]] = {
        record["character_id"]: {}
        for record in initial_design["characters"]
    }
    for record in initial_design["character_knowledge"]:
        knowledge_by_character.setdefault(
            record["character_id"],
            {},
        )[record["knowledge_id"]] = record["state"]

    root_location_ids = [
        record["location_id"]
        for record in initial_design["locations"]
        if record["parent_location_id"] is None
    ]
    if not root_location_ids:
        raise ContractError(
            "Initial Generationには最上位Locationが必要です"
        )
    default_location_id = root_location_ids[0]

    character_states = {
        record["character_id"]: {
            "current_location_id": default_location_id,
            "physical_condition": "healthy",
            "emotional_condition": record["initial_state"][
                "emotion"
            ],
            "goals": [
                record["initial_state"]["recent_goal"]
            ],
            "active_constraints": [],
            "inventory_item_ids": [],
            "knowledge_states": deepcopy(
                knowledge_by_character.get(
                    record["character_id"],
                    {},
                )
            ),
            "availability": "available",
            "alive_status": "alive",
        }
        for record in initial_design["characters"]
    }

    relationship_states = {
        record["relationship_id"]: {
            "status": record["initial_state"]["status"],
            "trust": record["initial_state"]["trust"],
            "affection": record["initial_state"][
                "affection"
            ],
            "fear": record["initial_state"].get("fear", 0),
            "hostility": record["initial_state"][
                "hostility"
            ],
            "obligations": [],
            "shared_secrets": [],
            "public_status": record["public_description"],
            "private_status": record["private_truth"],
            "last_change_scene_id": None,
        }
        for record in initial_design["relationships"]
    }

    thread_states = {
        record["thread_id"]: {
            "status": record["initial_status"],
            "progress_summary": (
                f"{record['title']}はInitial Designの"
                "開始状態にある。"
            ),
            "open_questions": (
                [record["question"]]
                if record["initial_status"] != "resolved"
                else []
            ),
            "latest_development_scene_id": None,
            "resolution_scene_id": None,
            "completion_notes": None,
        }
        for record in initial_design["threads"]
    }

    canon_records: list[dict[str, Any]] = []

    def append_canon(
        *,
        subject_type: str,
        subject_id: str,
        predicate: str,
        value: dict[str, Any],
        visibility: str,
        notes: str | None,
    ) -> None:
        canon_records.append({
            "canon_id": (
                f"canon-{len(canon_records) + 1:06d}"
            ),
            "subject_type": subject_type,
            "subject_id": subject_id,
            "predicate": predicate,
            "value": deepcopy(value),
            "visibility": visibility,
            "source_scene_id": None,
            "introduced_generation_id": generation_id,
            "status": "active",
            "notes": notes,
        })

    for record in initial_design["characters"]:
        append_canon(
            subject_type="character",
            subject_id=record["character_id"],
            predicate="initial_state",
            value=deepcopy(record["initial_state"]),
            visibility="writer_private",
            notes=record["name"],
        )

    for record in initial_design["relationships"]:
        append_canon(
            subject_type="relationship",
            subject_id=record["relationship_id"],
            predicate="participants",
            value={
                "character_ids": deepcopy(
                    record["participant_ids"]
                ),
            },
            visibility="reader_visible",
            notes=record["public_description"],
        )

    for record in initial_design["locations"]:
        if record["parent_location_id"] is None:
            continue
        append_canon(
            subject_type="location",
            subject_id=record["location_id"],
            predicate="located_in",
            value={
                "location_id": record[
                    "parent_location_id"
                ],
            },
            visibility="reader_visible",
            notes=None,
        )

    for record in initial_design["world_rules"]:
        append_canon(
            subject_type="world_rule",
            subject_id=record["rule_id"],
            predicate="description",
            value={
                "description": record["description"],
                "scope": record["scope"],
                "exceptions": deepcopy(
                    record["exceptions"]
                ),
                "change_policy": record["change_policy"],
            },
            visibility=record["reader_visibility"],
            notes=record["name"],
        )

    for record in initial_design["knowledge_facts"]:
        if record["truth_status"] != "true":
            continue
        append_canon(
            subject_type="knowledge",
            subject_id=record["knowledge_id"],
            predicate="statement",
            value={
                "statement": record["statement"],
                "truth_status": record["truth_status"],
            },
            visibility=record["reader_visibility"],
            notes=record["private_notes"],
        )

    return {
        "canon.json": {
            "schema_version": 1,
            "generation_id": generation_id,
            "records": canon_records,
        },
        "state.json": {
            "schema_version": 1,
            "generation_id": generation_id,
            "characters": character_states,
            "relationships": relationship_states,
            "threads": thread_states,
            "timeline": {
                "current_story_time": "シリーズ開始時点",
                "calendar_system": "未設定",
                "elapsed_time": "0",
                "known_deadlines": [],
                "event_order": [],
                "time_constraints": [],
            },
            "inventory": {},
            "commitments": {},
        },
        "evidence.json": {
            "schema_version": 1,
            "generation_id": generation_id,
            "evidence": [],
        },
        "commit.json": {
            "schema_version": 1,
            "generation_id": generation_id,
            "parent_generation_id": None,
            "commit_type": "initial_design",
            "source_artifact_type": "initial_design",
            "source_artifact_id": initial_design["design_id"],
            "summary": (
                "Initial Designから初期Story状態を作成。"
            ),
            "changed_targets": [
                "canon",
                "state",
            ],
            "created_at": created_at,
        },
    }


def validate_initial_generation(
    files: dict[str, dict[str, Any]],
    initial_design: dict[str, Any],
) -> None:
    """Initial Generationの4ファイルを決定的構築結果へ照合する。"""
    expected_names = {
        "canon.json",
        "state.json",
        "evidence.json",
        "commit.json",
    }
    if set(files) != expected_names:
        raise ContractError(
            "Initial Generationのfile構成が不正です"
        )

    for name, value in files.items():
        if not isinstance(value, dict):
            raise ContractError(
                f"Initial Generationの{name}はobjectが必要です"
            )

    commit = files["commit.json"]
    generation_id = commit.get("generation_id")
    if (
        not isinstance(generation_id, str)
        or not generation_id.startswith("gen-")
    ):
        raise ContractError(
            "Initial Generation IDが不正です"
        )

    created_at = commit.get("created_at")
    _validate_timestamp(
        created_at,
        "Initial Generation.created_at",
    )

    expected = build_initial_generation(
        initial_design,
        generation_id=generation_id,
        created_at=created_at,
    )
    if files != expected:
        raise ContractError(
            "Initial Generationが採用済み"
            "Initial Designからの決定的構築結果と一致しません"
        )


def _validate_timestamp(value: object, field: str) -> None:
    if not isinstance(value, str):
        raise ContractError(
            f"{field}はISO 8601文字列が必要です"
        )
    try:
        datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ContractError(
            f"{field}がISO 8601形式ではありません"
        ) from exc
