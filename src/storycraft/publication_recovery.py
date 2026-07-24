"""PublicationをProviderなしでforward-onlyに復旧する。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .immutable_directory import (
    finalize_immutable_directory,
)
from .publication_builder import (
    build_publication_files,
    validate_publication_directory,
)
from .publication_stage import PublicationStageService
from .run_state import RunStateStore, validate_run_state
from .series_contracts import ContractError
from .stages import Stage
from .workspace import validate_workspace_layout


class PublicationDirectoryCondition(StrEnum):
    """Publication directoryの観測状態。"""

    ABSENT = "absent"
    COMPLETE = "complete"
    INVALID = "invalid"


class PublicationRecoveryAction(StrEnum):
    """Publication Recoveryが次に行う処理。"""

    FINALIZE_PUBLICATION = "finalize_publication"
    COMPLETE_STATE = "complete_state"
    MANUAL = "manual"


@dataclass(frozen=True)
class PublicationRecoverySnapshot:
    """Publication Recovery分類用の観測結果。"""

    phase: str
    staging: PublicationDirectoryCondition
    final: PublicationDirectoryCondition


@dataclass(frozen=True)
class PublicationRecoveryInspection:
    """Publication Recoveryのfilesystem観測結果。"""

    snapshot: PublicationRecoverySnapshot
    publication_id: str
    staging: Path
    final: Path
    expected_files: dict[
        str,
        dict[str, Any] | str,
    ]
    staging_error: str | None = None
    final_error: str | None = None


def classify_publication_recovery(
    snapshot: PublicationRecoverySnapshot,
) -> PublicationRecoveryAction:
    """観測状態をforward-onlyな処理へ分類する。"""
    if snapshot.phase not in {
        "prepared",
        "publication_finalized",
    }:
        return PublicationRecoveryAction.MANUAL

    if (
        snapshot.staging
        is PublicationDirectoryCondition.INVALID
        or snapshot.final
        is PublicationDirectoryCondition.INVALID
    ):
        return PublicationRecoveryAction.MANUAL

    # 同一IDのstagingとfinalが同時に存在する状態は、
    # 自動削除や自動選択をせず人間判断とする。
    if (
        snapshot.staging
        is PublicationDirectoryCondition.COMPLETE
        and snapshot.final
        is PublicationDirectoryCondition.COMPLETE
    ):
        return PublicationRecoveryAction.MANUAL

    if snapshot.phase == "prepared":
        if (
            snapshot.staging
            is PublicationDirectoryCondition.COMPLETE
            and snapshot.final
            is PublicationDirectoryCondition.ABSENT
        ):
            return (
                PublicationRecoveryAction.FINALIZE_PUBLICATION
            )

        if (
            snapshot.staging
            is PublicationDirectoryCondition.ABSENT
            and snapshot.final
            is PublicationDirectoryCondition.COMPLETE
        ):
            return PublicationRecoveryAction.COMPLETE_STATE

        return PublicationRecoveryAction.MANUAL

    # publication_finalizedでは、finalが完全かつ
    # stagingが消えている状態だけを前進させる。
    if (
        snapshot.staging
        is PublicationDirectoryCondition.ABSENT
        and snapshot.final
        is PublicationDirectoryCondition.COMPLETE
    ):
        return PublicationRecoveryAction.COMPLETE_STATE

    return PublicationRecoveryAction.MANUAL


def inspect_publication_recovery(
    workspace_root: Path,
    state: dict[str, Any],
) -> PublicationRecoveryInspection:
    """pending Publicationのfilesystem状態を検査する。"""
    root = workspace_root.expanduser()
    current = validate_run_state(state)

    pending = current["pending_commit"]
    if (
        not isinstance(pending, dict)
        or pending.get("kind")
        != Stage.PUBLICATION.value
    ):
        raise ContractError(
            "Publication Recoveryにはpublicationの"
            "pending_commitが必要です"
        )

    if (
        current["current_stage"]
        != Stage.PUBLICATION.value
    ):
        raise ContractError(
            "Publication Recoveryのcurrent_stageが"
            "publicationではありません"
        )

    if current["current_publication_id"] is not None:
        raise ContractError(
            "pending Publication中に"
            "current_publication_idを設定できません"
        )

    publication_id = pending.get("target_id")
    if (
        not isinstance(publication_id, str)
        or not publication_id.startswith("pub-")
    ):
        raise ContractError(
            "Publication Recoveryの"
            "publication IDが不正です"
        )

    target = current["current_target"]
    if target.get("publication_id") != publication_id:
        raise ContractError(
            "pending Publication IDと"
            "current_targetが一致しません"
        )

    service = PublicationStageService(root)

    try:
        inputs = service._prepare_inputs(current)
        expected_files = build_publication_files(
            publication_id=publication_id,
            title=inputs["title"],
            language=inputs["language"],
            basis_generation_id=inputs[
                "basis_generation_id"
            ],
            completion=inputs["completion"],
            volumes=inputs["volumes"],
            created_at=current["updated_at"],
        )
    except (
        ContractError,
        OSError,
        UnicodeError,
        KeyError,
        TypeError,
    ) as exc:
        raise ContractError(
            "Publication Recoveryはmanual対応が必要です: "
            f"決定的Publicationを再構築できません: {exc}"
        ) from exc

    staging = (
        root
        / "runtime/staging"
        / f"publication-{publication_id}"
    )
    final = root / "publications" / publication_id

    staging_condition, staging_error = (
        _inspect_publication_directory(
            staging,
            expected_files,
        )
    )
    final_condition, final_error = (
        _inspect_publication_directory(
            final,
            expected_files,
        )
    )

    return PublicationRecoveryInspection(
        snapshot=PublicationRecoverySnapshot(
            phase=pending["phase"],
            staging=staging_condition,
            final=final_condition,
        ),
        publication_id=publication_id,
        staging=staging,
        final=final,
        expected_files=expected_files,
        staging_error=staging_error,
        final_error=final_error,
    )


def execute_publication_recovery(
    workspace_root: Path,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """pending Publicationをforward-onlyに復旧する。"""
    root = workspace_root.expanduser()
    store = RunStateStore(root)
    current = store.load_recovery()

    if state is not None and current != state:
        raise ContractError(
            "Publication Recovery開始前に"
            "run-stateが変更されています"
        )

    inspection = inspect_publication_recovery(
        root,
        current,
    )
    action = classify_publication_recovery(
        inspection.snapshot
    )

    if action is PublicationRecoveryAction.MANUAL:
        _raise_manual(inspection)

    timestamp = current["updated_at"]
    pending_state = current

    if (
        action
        is PublicationRecoveryAction.FINALIZE_PUBLICATION
    ):
        finalize_immutable_directory(
            staging=inspection.staging,
            final=inspection.final,
            validator=lambda directory: (
                validate_publication_directory(
                    directory,
                    expected_files=(
                        inspection.expected_files
                    ),
                )
            ),
        )

        pending_state = _save_pending_phase(
            store,
            current,
            publication_id=inspection.publication_id,
            phase="publication_finalized",
        )

    elif action is PublicationRecoveryAction.COMPLETE_STATE:
        # rename直後にCrashした場合はphaseがpreparedのまま
        # finalだけが存在する。実在する完全な成果物まで
        # phaseを前進させてから最終stateを確定する。
        if (
            inspection.snapshot.phase
            == "prepared"
        ):
            pending_state = _save_pending_phase(
                store,
                current,
                publication_id=inspection.publication_id,
                phase="publication_finalized",
            )

    else:
        raise AssertionError(
            "未処理のPublication Recovery action: "
            f"{action}"
        )

    validate_publication_directory(
        inspection.final,
        expected_files=inspection.expected_files,
    )

    completed = _complete_publication_state(
        pending_state,
        publication_id=inspection.publication_id,
        updated_at=timestamp,
    )
    store.save(completed)

    validate_workspace_layout(root)
    return completed


def _inspect_publication_directory(
    path: Path,
    expected_files: dict[
        str,
        dict[str, Any] | str,
    ],
) -> tuple[
    PublicationDirectoryCondition,
    str | None,
]:
    if not path.exists() and not path.is_symlink():
        return PublicationDirectoryCondition.ABSENT, None

    if path.is_symlink() or not path.is_dir():
        return (
            PublicationDirectoryCondition.INVALID,
            "Publication pathは通常directoryではありません",
        )

    try:
        validate_publication_directory(
            path,
            expected_files=expected_files,
        )
        return (
            PublicationDirectoryCondition.COMPLETE,
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
            PublicationDirectoryCondition.INVALID,
            str(exc),
        )


def _save_pending_phase(
    store: RunStateStore,
    state: dict[str, Any],
    *,
    publication_id: str,
    phase: str,
) -> dict[str, Any]:
    pending = deepcopy(state)
    pending["pending_commit"] = {
        "kind": Stage.PUBLICATION.value,
        "target_id": publication_id,
        "phase": phase,
    }
    validate_run_state(pending)
    store.save(pending)
    return pending


def _complete_publication_state(
    state: dict[str, Any],
    *,
    publication_id: str,
    updated_at: str,
) -> dict[str, Any]:
    completed = deepcopy(state)
    completed["status"] = "completed"
    completed["current_stage"] = (
        Stage.PUBLICATION.value
    )
    completed["current_publication_id"] = (
        publication_id
    )
    completed["active_candidate"] = None
    completed["active_scene_id"] = None
    completed["pending_commit"] = None
    completed["stop_reason"] = None
    completed["last_error"] = None
    completed["updated_at"] = updated_at
    return validate_run_state(completed)


def _raise_manual(
    inspection: PublicationRecoveryInspection,
) -> None:
    details = [
        f"snapshot={inspection.snapshot!r}",
    ]

    if inspection.staging_error:
        details.append(
            f"staging={inspection.staging_error}"
        )
    if inspection.final_error:
        details.append(
            f"final={inspection.final_error}"
        )

    raise ContractError(
        "Publication Recoveryはmanual対応が必要です: "
        + " | ".join(details)
    )
