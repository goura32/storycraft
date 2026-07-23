"""Storycraft Version 1 のStage遷移契約。"""
from __future__ import annotations

from collections.abc import Mapping

from .series_contracts import ContractError
from .stages import Stage


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
