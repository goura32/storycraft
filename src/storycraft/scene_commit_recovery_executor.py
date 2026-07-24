"""Scene CommitをProviderなしで正常完了状態へ復旧する。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .immutable_directory import (
    finalize_immutable_directory,
)
from .orphan_storage import move_directory_to_orphans
from .reviewed_candidate_stage import read_json
from .run_state import RunStateStore, validate_run_state
from .scene_adoption_record import (
    load_scene_adoption_record,
)
from .scene_commit_recovery import (
    DirectoryCondition,
    SceneCommitRecoveryAction,
    SceneCommitRecoveryInspection,
    classify_scene_commit_recovery,
    inspect_scene_commit_recovery,
)
from .scene_commit_stage import (
    SceneCommitStageService,
    determine_scene_commit_transition,
)
from .scene_generation import (
    build_scene_commit,
    build_scene_generation,
    validate_scene_commit,
)
from .series_contracts import ContractError
from .stage_transition import advance_run_state
from .workspace import validate_workspace_layout


DirectoryValidator = Callable[[Path], None]


@dataclass(frozen=True)
class _RecoveryContext:
    root: Path
    state: dict[str, Any]
    service: SceneCommitStageService
    store: RunStateStore
    scene_id: str
    parent_generation_id: str
    expected_generation_id: str
    scene_staging: Path
    generation_staging: Path
    scene_final: Path
    generation_final: Path
    series_plan: dict[str, Any]
    volume_plan: dict[str, Any]
    chapter_plan: dict[str, Any]
    parent_generation: dict[str, dict[str, Any]]
    scene_card: dict[str, Any]
    prose: str
    continuity: dict[str, Any]
    scene_commit: dict[str, Any]
    scene_validator: DirectoryValidator
    generation_validator: DirectoryValidator


def execute_scene_commit_recovery(
    workspace_root: Path,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """pending Scene Commitをforward-onlyに復旧する。"""
    root = workspace_root.expanduser()
    store = RunStateStore(root)
    current = store.load()

    if state is not None and current != state:
        raise ContractError(
            "Scene Commit Recovery開始前にrun-stateが"
            "変更されています"
        )

    inspection = inspect_scene_commit_recovery(
        root,
        current,
    )
    action = classify_scene_commit_recovery(
        inspection.snapshot
    )

    if action is SceneCommitRecoveryAction.MANUAL:
        _raise_manual(inspection)

    context = _load_context(
        root,
        current,
        inspection,
    )
    timestamp = current["updated_at"]

    if action is SceneCommitRecoveryAction.RESTART_COMMIT:
        return _restart_commit(
            context,
            inspection,
            updated_at=timestamp,
        )

    if action is SceneCommitRecoveryAction.FINALIZE_SCENE:
        pending_state = context.service._save_pending_phase(
            current,
            scene_id=context.scene_id,
            result_generation_id=(
                context.expected_generation_id
            ),
            phase="prepared",
            updated_at=timestamp,
        )

        finalize_immutable_directory(
            staging=context.scene_staging,
            final=context.scene_final,
            validator=context.scene_validator,
        )
        pending_state = (
            context.service._save_pending_phase(
                pending_state,
                scene_id=context.scene_id,
                result_generation_id=(
                    context.expected_generation_id
                ),
                phase="scene_finalized",
                updated_at=timestamp,
            )
        )

        finalize_immutable_directory(
            staging=context.generation_staging,
            final=context.generation_final,
            validator=context.generation_validator,
        )
        pending_state = (
            context.service._save_pending_phase(
                pending_state,
                scene_id=context.scene_id,
                result_generation_id=(
                    context.expected_generation_id
                ),
                phase="generation_finalized",
                updated_at=timestamp,
            )
        )
        return _complete_state(
            context,
            pending_state,
            updated_at=timestamp,
        )

    if (
        action
        is SceneCommitRecoveryAction.FINALIZE_GENERATION
    ):
        pending_state = context.service._save_pending_phase(
            current,
            scene_id=context.scene_id,
            result_generation_id=(
                context.expected_generation_id
            ),
            phase="scene_finalized",
            updated_at=timestamp,
        )

        finalize_immutable_directory(
            staging=context.generation_staging,
            final=context.generation_final,
            validator=context.generation_validator,
        )
        pending_state = (
            context.service._save_pending_phase(
                pending_state,
                scene_id=context.scene_id,
                result_generation_id=(
                    context.expected_generation_id
                ),
                phase="generation_finalized",
                updated_at=timestamp,
            )
        )
        return _complete_state(
            context,
            pending_state,
            updated_at=timestamp,
        )

    if (
        action
        is SceneCommitRecoveryAction.REBUILD_GENERATION
    ):
        pending_state = context.service._save_pending_phase(
            current,
            scene_id=context.scene_id,
            result_generation_id=(
                context.expected_generation_id
            ),
            phase="scene_finalized",
            updated_at=timestamp,
        )

        if (
            inspection.snapshot.generation_staging
            is not DirectoryCondition.ABSENT
        ):
            move_directory_to_orphans(
                context.root,
                context.generation_staging,
                updated_at=timestamp,
            )

        generation = build_scene_generation(
            parent_generation=context.parent_generation,
            continuity=context.continuity,
            scene_commit=context.scene_commit,
        )
        context.service._ensure_generation_staging(
            context.generation_staging,
            generation,
            context.generation_validator,
        )

        finalize_immutable_directory(
            staging=context.generation_staging,
            final=context.generation_final,
            validator=context.generation_validator,
        )
        pending_state = (
            context.service._save_pending_phase(
                pending_state,
                scene_id=context.scene_id,
                result_generation_id=(
                    context.expected_generation_id
                ),
                phase="generation_finalized",
                updated_at=timestamp,
            )
        )
        return _complete_state(
            context,
            pending_state,
            updated_at=timestamp,
        )

    if action is SceneCommitRecoveryAction.COMPLETE_STATE:
        pending_state = context.service._save_pending_phase(
            current,
            scene_id=context.scene_id,
            result_generation_id=(
                context.expected_generation_id
            ),
            phase="generation_finalized",
            updated_at=timestamp,
        )
        return _complete_state(
            context,
            pending_state,
            updated_at=timestamp,
        )

    if (
        action
        is SceneCommitRecoveryAction.CLEAR_STALE_PENDING
    ):
        cleared = deepcopy(current)
        cleared["pending_commit"] = None
        context.store.save(cleared)
        return cleared

    raise AssertionError(
        f"未処理のScene Commit Recovery action: {action}"
    )


def _restart_commit(
    context: _RecoveryContext,
    inspection: SceneCommitRecoveryInspection,
    *,
    updated_at: str,
) -> dict[str, Any]:
    """finalがない状態でGeneration stagingを再準備する。"""
    if (
        inspection.snapshot.scene_staging
        is DirectoryCondition.INVALID
    ):
        move_directory_to_orphans(
            context.root,
            context.scene_staging,
            updated_at=updated_at,
        )

    if (
        inspection.snapshot.generation_staging
        is not DirectoryCondition.ABSENT
    ):
        move_directory_to_orphans(
            context.root,
            context.generation_staging,
            updated_at=updated_at,
        )

    restarted = deepcopy(context.state)
    restarted["pending_commit"] = None
    context.store.save(restarted)

    return context.service.run(
        updated_at=updated_at,
    )


def _complete_state(
    context: _RecoveryContext,
    state: dict[str, Any],
    *,
    updated_at: str,
) -> dict[str, Any]:
    """両final確認後に最後のrun-state更新を行う。"""
    next_stage, next_target = (
        determine_scene_commit_transition(
            state=state,
            series_plan=context.series_plan,
            volume_plan=context.volume_plan,
            chapter_plan=context.chapter_plan,
            result_generation_id=(
                context.expected_generation_id
            ),
        )
    )

    ready = deepcopy(state)
    ready["current_generation_id"] = (
        context.expected_generation_id
    )
    ready["pending_commit"] = None
    validate_run_state(ready)

    advanced = advance_run_state(
        ready,
        next_stage=next_stage,
        next_target=next_target,
        updated_at=updated_at,
    )
    context.store.save(advanced)

    validate_workspace_layout(context.root)
    return advanced


def _load_context(
    root: Path,
    state: dict[str, Any],
    inspection: SceneCommitRecoveryInspection,
) -> _RecoveryContext:
    pending = state["pending_commit"]
    assert isinstance(pending, dict)

    target = state["current_target"]
    scene_id = pending["target_id"]
    expected_generation_id = pending[
        "expected_generation_id"
    ]
    parent_generation_id = target[
        "basis_generation_id"
    ]

    volume_number = target["volume_number"]
    chapter_number = target["chapter_number"]
    scene_number = target["scene_number"]

    service = SceneCommitStageService(root)
    store = RunStateStore(root)

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

    scene_staging = (
        root / "runtime/staging" / f"scene-{scene_id}"
    )
    generation_staging = (
        root
        / "runtime/staging"
        / f"generation-{expected_generation_id}"
    )
    scene_final = root / "scenes" / scene_id
    generation_final = (
        root / "generations" / expected_generation_id
    )

    scene_source: Path | None = None
    if (
        inspection.snapshot.scene_final
        is DirectoryCondition.COMPLETE
    ):
        scene_source = scene_final
    elif (
        inspection.snapshot.scene_staging
        is DirectoryCondition.COMPLETE
    ):
        scene_source = scene_staging

    if scene_source is None:
        try:
            adoption = load_scene_adoption_record(
                root,
                scene_id,
            )
        except ContractError:
            _raise_manual(inspection)

        scene_card = deepcopy(adoption.scene_card)
        prose = adoption.prose
        continuity = deepcopy(adoption.continuity)
        scene_commit = build_scene_commit(
            scene_card=scene_card,
            continuity=continuity,
        )
        validate_scene_commit(
            scene_commit,
            scene_card=scene_card,
            continuity=continuity,
        )
    else:
        scene_card = read_json(
            scene_source / "scene-card.json"
        )
        continuity = read_json(
            scene_source / "continuity.json"
        )
        scene_commit = read_json(
            scene_source / "commit.json"
        )
        try:
            prose = (
                scene_source / "prose.md"
            ).read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeError) as exc:
            raise ContractError(
                "Recovery対象Scene本文を読み込めません"
            ) from exc

    def scene_validator(path: Path) -> None:
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
            parent_generation_id=parent_generation_id,
        )

    def generation_validator(path: Path) -> None:
        service._validate_generation_directory(
            path,
            parent_generation=parent_generation,
            continuity=continuity,
            scene_commit=scene_commit,
        )

    return _RecoveryContext(
        root=root,
        state=state,
        service=service,
        store=store,
        scene_id=scene_id,
        parent_generation_id=parent_generation_id,
        expected_generation_id=expected_generation_id,
        scene_staging=scene_staging,
        generation_staging=generation_staging,
        scene_final=scene_final,
        generation_final=generation_final,
        series_plan=series_plan,
        volume_plan=volume_plan,
        chapter_plan=chapter_plan,
        parent_generation=parent_generation,
        scene_card=scene_card,
        prose=prose,
        continuity=continuity,
        scene_commit=scene_commit,
        scene_validator=scene_validator,
        generation_validator=generation_validator,
    )


def _raise_manual(
    inspection: SceneCommitRecoveryInspection,
) -> None:
    details = [
        f"snapshot={inspection.snapshot!r}",
    ]
    for label, error in (
        (
            "scene_staging",
            inspection.scene_staging_error,
        ),
        (
            "generation_staging",
            inspection.generation_staging_error,
        ),
        (
            "scene_final",
            inspection.scene_final_error,
        ),
        (
            "generation_final",
            inspection.generation_final_error,
        ),
    ):
        if error:
            details.append(f"{label}={error}")

    raise ContractError(
        "Scene Commit Recoveryはmanual対応が必要です: "
        + " | ".join(details)
    )
