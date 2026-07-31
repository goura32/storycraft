"""採用済みScene CommitとScene Generationのcode-only契約。"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .series_contracts import ContractError


_STATE_TARGET_SOURCES = {
    "character_state": "characters",
    "relationship_state": "relationships",
    "thread_state": "threads",
    "inventory_state": "inventory",
    "commitment_state": "commitments",
}


def state_target_record(
    state: dict[str, Any], target_type: str, target_id: str
) -> dict[str, Any]:
    """Scene Cardで許可された現在状態の対象を決定的に解決する。"""
    if target_type == "timeline_state":
        if target_id != "timeline":
            raise ContractError("timeline_stateのtarget_idはtimelineが必要です")
        record = state.get("timeline")
    else:
        source_name = _STATE_TARGET_SOURCES.get(target_type)
        if source_name is None:
            raise ContractError("unknown state target_type")
        source = state.get(source_name)
        record = source.get(target_id) if isinstance(source, dict) else None
    if not isinstance(record, dict):
        raise ContractError("current Stateの対象が存在しません")
    return record


def build_scene_commit_candidate(
    scene_prose: dict[str, Any],
    scene_card: dict[str, Any],
    continuity_update: dict[str, Any],
    basis_generation: dict[str, Any],
    volume_number: int,
    chapter_number: int,
    scene_number: int,
    timestamp: str,
) -> dict[str, Any]:
    """Scene Commit候補を決定的に構築する。"""
    # Combine scene data into a commit candidate
    return {
        "schema_version": 1,
        "scene_commit_id": f"scene-commit-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001",
        "version": 1,
        "brief_id": "brief-000001",
        "scene_id": f"scene-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001",
        "scene_card_id": scene_card.get("scene_card_id", f"scene-card-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001"),
        "scene_prose_id": scene_prose.get("scene_prose_id", f"scene-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001"),
        "continuity_update_id": continuity_update.get("continuity_update_id", f"continuity-v{volume_number:02d}-c{chapter_number:02d}-s{scene_number:02d}-000001"),
        "basis_generation_id": basis_generation.get("generation_id", "gen-000001"),
        "volume_number": volume_number,
        "chapter_number": chapter_number,
        "scene_number": scene_number,
        "created_at": timestamp,
        # Copy the actual content
        "scene_prose": deepcopy(scene_prose.get("content", "")),
        "scene_card": deepcopy(scene_card),
        "continuity_update": deepcopy(continuity_update),
    }


def validate_scene_commit_candidate(
    candidate: dict[str, Any],
    brief: dict[str, Any],
    initial_design: dict[str, Any],
    series_plan: dict[str, Any],
    volume_plan: dict[str, Any],
    chapter_plan: dict[str, Any],
    scene_plan: dict[str, Any],
    scene_card: dict[str, Any],
    scene_prose: dict[str, Any],
    continuity_update: dict[str, Any],
    current_generation: dict[str, Any],
    volume_number: int,
    chapter_number: int,
    scene_number: int,
) -> None:
    """Scene Commit候補を検証する。"""
    if not isinstance(candidate, dict):
        raise ContractError("Scene Commit CandidateはJSON objectでなければなりません")
    
    # Verify all required fields
    required = [
        "schema_version", "scene_commit_id", "version", "brief_id",
        "scene_id", "scene_card_id", "scene_prose_id", "continuity_update_id",
        "basis_generation_id", "volume_number", "chapter_number", "scene_number",
        "created_at", "scene_prose", "scene_card", "continuity_update"
    ]
    for field in required:
        if field not in candidate:
            raise ContractError(f"Scene Commit Candidateに必須フィールドがありません: {field}")
    
    if candidate["schema_version"] != 1:
        raise ContractError("Scene Commit Candidateのschema_versionは1でなければなりません")
    
    if candidate["volume_number"] != volume_number:
        raise ContractError("Scene Commitの巻番号が一致しません")
    if candidate["chapter_number"] != chapter_number:
        raise ContractError("Scene Commitの章番号が一致しません")
    if candidate["scene_number"] != scene_number:
        raise ContractError("Scene Commitの場面番号が一致しません")


def build_accepted_scene_commit(
    candidate: dict[str, Any],
    brief: dict[str, Any],
    initial_design: dict[str, Any],
    series_plan: dict[str, Any],
    volume_plan: dict[str, Any],
    chapter_plan: dict[str, Any],
    scene_plan: dict[str, Any],
    scene_card: dict[str, Any],
    scene_prose: dict[str, Any],
    continuity_update: dict[str, Any],
    current_generation: dict[str, Any],
    volume_number: int,
    chapter_number: int,
    scene_number: int,
    timestamp: str,
) -> dict[str, Any]:
    """採用済みScene Commitを構築する。"""
    # Extract the next generation from current
    next_gen_num = int(current_generation["generation_id"].split("-")[1]) + 1
    next_gen_id = f"gen-{next_gen_num:06d}"
    
    # Build the new generation
    new_generation = {
        "schema_version": 1,
        "generation_id": next_gen_id,
        "basis_generation_id": current_generation["generation_id"],
        "created_at": timestamp,
        "scenes": current_generation.get("scenes", []) + [
            {
                "scene_id": candidate["scene_id"],
                "scene_commit_id": candidate["scene_commit_id"],
                "volume_number": volume_number,
                "chapter_number": chapter_number,
                "scene_number": scene_number,
            }
        ],
        "state_schema": current_generation.get("state_schema", {}),
        "state_ids": current_generation.get("state_ids", {}),
        "knowledge_model": current_generation.get("knowledge_model", {}),
        "unresolved_threads": current_generation.get("unresolved_threads", []),
    }
    
    return {
        "scene_commit": {
            "schema_version": 1,
            "scene_commit_id": candidate["scene_commit_id"],
            "version": 1,
            "brief_id": "brief-000001",
            "scene_id": candidate["scene_id"],
            "scene_card_id": candidate["scene_card_id"],
            "scene_prose_id": candidate["scene_prose_id"],
            "continuity_update_id": candidate["continuity_update_id"],
            "basis_generation_id": candidate["basis_generation_id"],
            "volume_number": volume_number,
            "chapter_number": chapter_number,
            "scene_number": scene_number,
            "created_at": timestamp,
            "scene_prose": candidate["scene_prose"],
            "scene_card": candidate["scene_card"],
            "continuity_update": candidate["continuity_update"],
        },
        "generation": new_generation,
    }


def validate_accepted_scene_commit(
    accepted: dict[str, Any],
    candidate: dict[str, Any],
    brief: dict[str, Any],
    initial_design: dict[str, Any],
    series_plan: dict[str, Any],
    volume_plan: dict[str, Any],
    chapter_plan: dict[str, Any],
    scene_plan: dict[str, Any],
    scene_card: dict[str, Any],
    scene_prose: dict[str, Any],
    continuity_update: dict[str, Any],
    current_generation: dict[str, Any],
) -> None:
    """採用済みScene Commitを検証する。"""
    if not isinstance(accepted, dict):
        raise ContractError("採用済みScene CommitはJSON objectでなければなりません")
    
    if "scene_commit" not in accepted or "generation" not in accepted:
        raise ContractError("採用済みScene Commitにscene_commitまたはgenerationがありません")
    
    scene_commit = accepted["scene_commit"]
    generation = accepted["generation"]
    
    # Verify scene_commit matches candidate
    for field in ["scene_commit_id", "scene_id", "scene_card_id", "scene_prose_id", 
                  "continuity_update_id", "basis_generation_id", "volume_number",
                  "chapter_number", "scene_number", "scene_prose", "scene_card", "continuity_update"]:
        if scene_commit.get(field) != candidate.get(field):
            raise ContractError(f"採用済みScene Commitの{field}が候補と一致しません")
    
    # Verify generation
    if generation["basis_generation_id"] != current_generation["generation_id"]:
        raise ContractError("Generationのbasis_generation_idが不正です")
    
    # Verify scene was added
    scenes = generation.get("scenes", [])
    last_scene = scenes[-1] if scenes else None
    if not last_scene or last_scene["scene_commit_id"] != candidate["scene_commit_id"]:
        raise ContractError("GenerationにScene Commitが追加されていません")


def validate_scene_commit_candidate_basic(candidate: dict[str, Any], initial_design: dict[str, Any]) -> None:
    """Scene Commit候補の基本検証（互換性のため）。"""
    validate_scene_commit_candidate(
        candidate, {}, initial_design, {}, {}, {}, {}, {}, {}, {}, {}, 1, 1, 1
    )