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


@dataclass(frozen=True)
class SceneCommitRecoveryInspection:
    """Scene Commit Recoveryのfilesystem観測結果。"""

    snapshot: SceneCommitRecoverySnapshot
    scene_staging_error: str | None = None
    generation_staging_error: str | None = None
    scene_final_error: str | None = None
    generation_final_error: str | None = None


@dataclass(frozen=True)
class _ScenePayload:
    scene_card: dict[str, object]
    prose: str
    continuity: dict[str, object]
    scene_commit: dict[str, object]


def inspect_scene_commit_recovery(
    workspace_root: "Path",
    state: dict[str, "Any"],
) -> SceneCommitRecoveryInspection:
    """pending Scene Commitの実filesystem状態を検査する。"""
    from copy import deepcopy
    from pathlib import Path
    from typing import Any

    from .reviewed_candidate_stage import read_json
    from .run_state import validate_run_state
    from .scene_commit_stage import (
        SceneCommitStageService,
        determine_scene_commit_transition,
    )
    from .series_contracts import ContractError
    from .stages import Stage

    root = Path(workspace_root).expanduser()
    current = validate_run_state(state)

    pending = current["pending_commit"]
    if (
        not isinstance(pending, dict)
        or pending.get("kind") != Stage.SCENE_COMMIT.value
    ):
        raise ContractError(
            "Scene Commit Recoveryにはscene_commitの"
            "pending_commitが必要です"
        )

    target = current["current_target"]
    scene_id = pending["target_id"]
    expected_generation_id = pending[
        "expected_generation_id"
    ]
    parent_generation_id = target.get(
        "basis_generation_id"
    )

    if not isinstance(parent_generation_id, str):
        raise ContractError(
            "Scene Commit Recoveryの親Generation IDが"
            "不正です"
        )
    if target.get("result_generation_id") != (
        expected_generation_id
    ):
        raise ContractError(
            "pending expected Generationとcurrent_targetが"
            "一致しません"
        )
    if current["active_scene_id"] != scene_id:
        raise ContractError(
            "pending Sceneとactive_scene_idが一致しません"
        )

    volume_number = _inspection_positive_integer(
        target.get("volume_number"),
        "current_target.volume_number",
    )
    chapter_number = _inspection_positive_integer(
        target.get("chapter_number"),
        "current_target.chapter_number",
    )
    scene_number = _inspection_positive_integer(
        target.get("scene_number"),
        "current_target.scene_number",
    )

    expected_scene_id = (
        f"scene-v{volume_number:02d}"
        f"-c{chapter_number:03d}"
        f"-s{scene_number:03d}"
    )
    if scene_id != expected_scene_id:
        raise ContractError(
            "pending Scene IDがcurrent_target座標と"
            "一致しません"
        )

    service = SceneCommitStageService(root)

    brief = read_json(root / "input/brief.json")
    initial_design = read_json(
        root / "design/initial/v0001/initial-design.json"
    )
    series_plan = read_json(
        root
        / "design/series-plans"
        / "series-plan-v0001"
        / "series-plan.json"
    )
    volume_plan = read_json(
        root
        / "design/volume-plans"
        / f"v{volume_number:02d}-v0001"
        / "volume-plan.json"
    )
    chapter_plan = read_json(
        root
        / "design/chapter-plans"
        / (
            f"v{volume_number:02d}"
            f"-c{chapter_number:03d}-v0001"
        )
        / "chapter-plan.json"
    )
    scene_plan = read_json(
        root
        / "design/scene-plans"
        / (
            f"v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}-v0001"
        )
        / "scene-plan.json"
    )
    parent_generation = service._read_generation(
        parent_generation_id
    )

    scene_staging_path = (
        root / "runtime/staging" / f"scene-{scene_id}"
    )
    generation_staging_path = (
        root
        / "runtime/staging"
        / f"generation-{expected_generation_id}"
    )
    scene_final_path = root / "scenes" / scene_id
    generation_final_path = (
        root / "generations" / expected_generation_id
    )

    def inspect_scene(
        path: Path,
    ) -> tuple[
        DirectoryCondition,
        _ScenePayload | None,
        str | None,
    ]:
        if not path.exists() and not path.is_symlink():
            return DirectoryCondition.ABSENT, None, None
        if path.is_symlink() or not path.is_dir():
            return (
                DirectoryCondition.INVALID,
                None,
                "Scene pathは通常directoryではありません",
            )

        try:
            scene_card = read_json(path / "scene-card.json")
            continuity = read_json(
                path / "continuity.json"
            )
            scene_commit = read_json(path / "commit.json")
            prose = (path / "prose.md").read_text(
                encoding="utf-8"
            )

            service._validate_scene_directory(
                path,
                brief=brief,
                initial_design=initial_design,
                series_plan=series_plan,
                volume_plan=volume_plan,
                chapter_plan=chapter_plan,
                scene_plan=scene_plan,
                parent_generation=parent_generation,
                scene_card=scene_card,
                continuity=continuity,
                scene_commit=scene_commit,
                prose=prose,
                volume_number=volume_number,
                chapter_number=chapter_number,
                scene_number=scene_number,
                parent_generation_id=(
                    parent_generation_id
                ),
            )

            if (
                scene_commit["result_generation_id"]
                != expected_generation_id
            ):
                raise ContractError(
                    "Scene Commit result Generationが"
                    "pending予定IDと一致しません"
                )

            return (
                DirectoryCondition.COMPLETE,
                _ScenePayload(
                    scene_card=scene_card,
                    prose=prose,
                    continuity=continuity,
                    scene_commit=scene_commit,
                ),
                None,
            )
        except (
            ContractError,
            OSError,
            UnicodeError,
            KeyError,
            TypeError,
        ) as exc:
            return (
                DirectoryCondition.INVALID,
                None,
                str(exc),
            )

    (
        scene_final_condition,
        scene_final_payload,
        scene_final_error,
    ) = inspect_scene(scene_final_path)

    (
        scene_staging_condition,
        scene_staging_payload,
        scene_staging_error,
    ) = inspect_scene(scene_staging_path)

    canonical_scene = (
        scene_final_payload
        if scene_final_condition
        is DirectoryCondition.COMPLETE
        else scene_staging_payload
    )

    def inspect_generation(
        path: Path,
    ) -> tuple[DirectoryCondition, str | None]:
        if not path.exists() and not path.is_symlink():
            return DirectoryCondition.ABSENT, None
        if path.is_symlink() or not path.is_dir():
            return (
                DirectoryCondition.INVALID,
                "Generation pathは通常directoryではありません",
            )
        if canonical_scene is None:
            return (
                DirectoryCondition.INVALID,
                "Generation検証に必要な完全なSceneがありません",
            )

        try:
            service._validate_generation_directory(
                path,
                parent_generation=parent_generation,
                continuity=canonical_scene.continuity,
                scene_commit=canonical_scene.scene_commit,
            )
            return DirectoryCondition.COMPLETE, None
        except (
            ContractError,
            OSError,
            KeyError,
            TypeError,
        ) as exc:
            return DirectoryCondition.INVALID, str(exc)

    (
        generation_final_condition,
        generation_final_error,
    ) = inspect_generation(generation_final_path)

    (
        generation_staging_condition,
        generation_staging_error,
    ) = inspect_generation(generation_staging_path)

    current_generation_id = current[
        "current_generation_id"
    ]
    if current_generation_id == parent_generation_id:
        relation = CurrentGenerationRelation.PARENT
    elif current_generation_id == expected_generation_id:
        relation = CurrentGenerationRelation.EXPECTED
    else:
        relation = CurrentGenerationRelation.OTHER

    final_state_matches = False
    if (
        relation is CurrentGenerationRelation.EXPECTED
        and scene_final_condition
        is DirectoryCondition.COMPLETE
        and generation_final_condition
        is DirectoryCondition.COMPLETE
    ):
        try:
            next_stage, next_target = (
                determine_scene_commit_transition(
                    state=current,
                    series_plan=series_plan,
                    volume_plan=volume_plan,
                    chapter_plan=chapter_plan,
                    result_generation_id=(
                        expected_generation_id
                    ),
                )
            )

            expected_state = deepcopy(current)
            expected_state["status"] = "running"
            expected_state["current_stage"] = (
                next_stage.value
            )
            expected_state["current_target"] = next_target
            expected_state["current_generation_id"] = (
                expected_generation_id
            )
            expected_state["active_candidate"] = None
            expected_state["active_scene_id"] = None
            expected_state["pending_commit"] = None
            expected_state["stop_reason"] = None
            expected_state["last_error"] = None

            observed_without_pending = deepcopy(current)
            observed_without_pending["pending_commit"] = None

            final_state_matches = (
                observed_without_pending == expected_state
            )
        except ContractError:
            final_state_matches = False

    snapshot = SceneCommitRecoverySnapshot(
        phase=pending["phase"],
        current_generation_relation=relation,
        scene_staging=scene_staging_condition,
        generation_staging=generation_staging_condition,
        scene_final=scene_final_condition,
        generation_final=generation_final_condition,
        final_state_matches=final_state_matches,
    )

    return SceneCommitRecoveryInspection(
        snapshot=snapshot,
        scene_staging_error=scene_staging_error,
        generation_staging_error=generation_staging_error,
        scene_final_error=scene_final_error,
        generation_final_error=generation_final_error,
    )


def _inspection_positive_integer(
    value: object,
    field: str,
) -> int:
    from .series_contracts import ContractError

    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ContractError(
            f"{field}は1以上の整数が必要です"
        )
    return value
