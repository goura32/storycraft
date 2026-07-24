"""Scene Commit Recoveryの副作用なし状態分類。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DirectoryCondition(StrEnum):
    """Recovery対象directoryの観測状態。"""

    ABSENT = "absent"
    COMPLETE = "complete"
    INVALID = "invalid"


class CurrentGenerationRelation(StrEnum):
    """current Generationとpending予定IDとの関係。"""

    PARENT = "parent"
    EXPECTED = "expected"
    OTHER = "other"


class SceneCommitRecoveryAction(StrEnum):
    """Scene Commit Recoveryが次に行う処理。"""

    FINALIZE_SCENE = "finalize_scene"
    RESTART_COMMIT = "restart_commit"
    FINALIZE_GENERATION = "finalize_generation"
    REBUILD_GENERATION = "rebuild_generation"
    COMPLETE_STATE = "complete_state"
    CLEAR_STALE_PENDING = "clear_stale_pending"
    MANUAL = "manual"


@dataclass(frozen=True)
class SceneCommitRecoverySnapshot:
    """Scene Commit Recovery判定に必要な観測結果。"""

    phase: str
    current_generation_relation: CurrentGenerationRelation
    scene_staging: DirectoryCondition
    generation_staging: DirectoryCondition
    scene_final: DirectoryCondition
    generation_final: DirectoryCondition
    final_state_matches: bool = False


def classify_scene_commit_recovery(
    snapshot: SceneCommitRecoverySnapshot,
) -> SceneCommitRecoveryAction:
    """観測状態をforward-onlyなRecovery actionへ分類する。"""
    if snapshot.phase not in {
        "prepared",
        "scene_finalized",
        "generation_finalized",
    }:
        return SceneCommitRecoveryAction.MANUAL

    # 確定pathが存在するのに契約検証を通らない場合は、
    # 削除・置換・後退を行わない。
    if (
        snapshot.scene_final
        is DirectoryCondition.INVALID
        or snapshot.generation_final
        is DirectoryCondition.INVALID
    ):
        return SceneCommitRecoveryAction.MANUAL

    # GenerationをSceneより先に採用する正常経路はない。
    if (
        snapshot.generation_final
        is DirectoryCondition.COMPLETE
        and snapshot.scene_final
        is not DirectoryCondition.COMPLETE
    ):
        return SceneCommitRecoveryAction.MANUAL

    relation = snapshot.current_generation_relation

    if relation is CurrentGenerationRelation.OTHER:
        return SceneCommitRecoveryAction.MANUAL

    if relation is CurrentGenerationRelation.EXPECTED:
        if (
            snapshot.scene_final
            is DirectoryCondition.COMPLETE
            and snapshot.generation_final
            is DirectoryCondition.COMPLETE
            and snapshot.final_state_matches
        ):
            return (
                SceneCommitRecoveryAction.CLEAR_STALE_PENDING
            )
        return SceneCommitRecoveryAction.MANUAL

    # ここからはcurrent Generationが親Generationの状態。
    if (
        snapshot.scene_final
        is DirectoryCondition.COMPLETE
        and snapshot.generation_final
        is DirectoryCondition.COMPLETE
    ):
        return SceneCommitRecoveryAction.COMPLETE_STATE

    if (
        snapshot.scene_final
        is DirectoryCondition.COMPLETE
        and snapshot.generation_final
        is DirectoryCondition.ABSENT
    ):
        if (
            snapshot.generation_staging
            is DirectoryCondition.COMPLETE
        ):
            return (
                SceneCommitRecoveryAction.FINALIZE_GENERATION
            )
        return SceneCommitRecoveryAction.REBUILD_GENERATION

    if (
        snapshot.scene_final
        is DirectoryCondition.ABSENT
        and snapshot.generation_final
        is DirectoryCondition.ABSENT
    ):
        if (
            snapshot.scene_staging
            is DirectoryCondition.COMPLETE
            and snapshot.generation_staging
            is DirectoryCondition.COMPLETE
        ):
            return SceneCommitRecoveryAction.FINALIZE_SCENE
        return SceneCommitRecoveryAction.RESTART_COMMIT

    return SceneCommitRecoveryAction.MANUAL
