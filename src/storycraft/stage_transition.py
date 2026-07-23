"""Storycraft Version 1 のStage遷移契約。"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from typing import Any

from .run_state import validate_run_state
from .series_contracts import ContractError
from .stages import SCENE_STAGES, Stage


ALLOWED_STAGE_TRANSITIONS: Mapping[Stage, frozenset[Stage]] = {
    Stage.INPUT: frozenset({
        Stage.INITIAL_CONCEPT,
    }),
    Stage.INITIAL_CONCEPT: frozenset({
        Stage.INITIAL_CHARACTERS,
    }),
    Stage.INITIAL_CHARACTERS: frozenset({
        Stage.INITIAL_RELATIONSHIPS,
    }),
    Stage.INITIAL_RELATIONSHIPS: frozenset({
        Stage.INITIAL_WORLD,
    }),
    Stage.INITIAL_WORLD: frozenset({
        Stage.INITIAL_KNOWLEDGE,
    }),
    Stage.INITIAL_KNOWLEDGE: frozenset({
        Stage.INITIAL_THREADS,
    }),
    Stage.INITIAL_THREADS: frozenset({
        Stage.INITIAL_ENDING,
    }),
    Stage.INITIAL_ENDING: frozenset({
        Stage.INITIAL_INTEGRATE,
    }),
    Stage.INITIAL_INTEGRATE: frozenset({
        Stage.INITIAL_ACCEPT,
    }),
    Stage.INITIAL_ACCEPT: frozenset({
        Stage.SERIES_PLAN,
    }),
    Stage.SERIES_PLAN: frozenset({
        Stage.VOLUME_PLAN,
    }),
    Stage.VOLUME_PLAN: frozenset({
        Stage.CHAPTER_PLAN,
    }),
    Stage.CHAPTER_PLAN: frozenset({
        Stage.SCENE_PLAN,
    }),
    Stage.SCENE_PLAN: frozenset({
        Stage.SCENE_CARD,
    }),
    Stage.SCENE_CARD: frozenset({
        Stage.SCENE_PROSE,
    }),
    Stage.SCENE_PROSE: frozenset({
        Stage.SCENE_CONTINUITY,
    }),
    Stage.SCENE_CONTINUITY: frozenset({
        Stage.SCENE_COMMIT,
    }),
    Stage.SCENE_COMMIT: frozenset({
        Stage.SCENE_CARD,
        Stage.CHAPTER_PLAN,
        Stage.SCENE_PLAN,
        Stage.VOLUME_HANDOFF,
    }),
    Stage.VOLUME_HANDOFF: frozenset({
        Stage.VOLUME_PLAN,
        Stage.COMPLETION,
    }),
    Stage.COMPLETION: frozenset({
        Stage.PUBLICATION,
    }),
    Stage.PUBLICATION: frozenset(),
}


def allowed_next_stages(stage: str | Stage) -> frozenset[Stage]:
    """指定Stageから許可される次Stageを返す。"""
    normalized = _normalize_stage(stage)
    return ALLOWED_STAGE_TRANSITIONS[normalized]


def validate_stage_transition(
    current_stage: str | Stage,
    next_stage: str | Stage,
) -> tuple[Stage, Stage]:
    """Stage遷移がV1 Pipelineで許可されることを確認する。"""
    current = _normalize_stage(current_stage)
    following = _normalize_stage(next_stage)

    if following not in ALLOWED_STAGE_TRANSITIONS[current]:
        allowed = ", ".join(
            stage.value
            for stage in sorted(
                ALLOWED_STAGE_TRANSITIONS[current],
                key=lambda item: item.value,
            )
        ) or "<terminal>"

        raise ContractError(
            "不正なV1 Stage遷移です: "
            f"{current.value} -> {following.value}; "
            f"allowed={allowed}"
        )

    return current, following


def is_terminal_stage(stage: str | Stage) -> bool:
    """次Stageを持たない正式な終端Stageか。"""
    return not allowed_next_stages(stage)


def _normalize_stage(stage: str | Stage) -> Stage:
    if isinstance(stage, Stage):
        return stage
    try:
        return Stage(stage)
    except (TypeError, ValueError) as exc:
        raise ContractError(
            f"未知のV1 Stageです: {stage!r}"
        ) from exc



_PRESERVE_ACTIVE_SCENE = object()


def advance_run_state(
    state: dict[str, Any],
    *,
    next_stage: str | Stage,
    next_target: dict[str, Any],
    updated_at: str,
    active_scene_id: str | None | object = _PRESERVE_ACTIVE_SCENE,
) -> dict[str, Any]:
    """完了済みStageから次Stageへrun-stateを非破壊更新する。"""
    current_state = validate_run_state(state)

    if current_state["status"] not in {"initializing", "running"}:
        raise ContractError(
            "Stage遷移できるrun statusではありません: "
            f"{current_state['status']!r}"
        )

    if current_state["active_candidate"] is not None:
        raise ContractError(
            "未採用active_candidateがあるため次Stageへ進めません"
        )

    if current_state["pending_commit"] is not None:
        raise ContractError(
            "pending_commitがあるため次Stageへ進めません"
        )

    _, following = validate_stage_transition(
        current_state["current_stage"],
        next_stage,
    )

    if not isinstance(next_target, dict) or not next_target:
        raise ContractError(
            "次Stageのcurrent_targetは空でないオブジェクトが必要です"
        )

    _validate_updated_at_progress(
        current_state["updated_at"],
        updated_at,
    )

    advanced = deepcopy(current_state)
    advanced["status"] = "running"
    advanced["current_stage"] = following.value
    advanced["current_target"] = deepcopy(next_target)
    advanced["active_candidate"] = None
    advanced["pending_commit"] = None
    advanced["stop_reason"] = None
    advanced["last_error"] = None
    advanced["updated_at"] = updated_at

    if following in SCENE_STAGES:
        resolved_scene_id = (
            current_state["active_scene_id"]
            if active_scene_id is _PRESERVE_ACTIVE_SCENE
            else active_scene_id
        )
        if resolved_scene_id is None:
            raise ContractError(
                f"{following.value}へ進むにはactive_scene_idが必要です"
            )
        advanced["active_scene_id"] = resolved_scene_id
    else:
        if (
            active_scene_id is not _PRESERVE_ACTIVE_SCENE
            and active_scene_id is not None
        ):
            raise ContractError(
                "Scene工程以外へactive_scene_idを設定できません"
            )
        advanced["active_scene_id"] = None

    return validate_run_state(advanced)


def _validate_updated_at_progress(
    previous: object,
    following: object,
) -> None:
    previous_time = _parse_transition_timestamp(
        previous,
        "現在のupdated_at",
    )
    following_time = _parse_transition_timestamp(
        following,
        "次のupdated_at",
    )

    if following_time < previous_time:
        raise ContractError(
            "Stage遷移でupdated_atを後退できません"
        )


def _parse_transition_timestamp(
    value: object,
    label: str,
) -> datetime:
    if not isinstance(value, str):
        raise ContractError(
            f"{label}はISO 8601文字列でなければなりません"
        )
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ContractError(
            f"{label}がISO 8601形式ではありません"
        ) from exc
