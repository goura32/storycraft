"""Storycraft Version 1 の工程定義。"""
from __future__ import annotations

from enum import StrEnum


class Stage(StrEnum):
    """Version 1で使用する正規工程名。"""

    INPUT = "input"

    INITIAL_CONCEPT = "initial_concept"
    INITIAL_CHARACTERS = "initial_characters"
    INITIAL_RELATIONSHIPS = "initial_relationships"
    INITIAL_WORLD = "initial_world"
    INITIAL_KNOWLEDGE = "initial_knowledge"
    INITIAL_THREADS = "initial_threads"
    INITIAL_ENDING = "initial_ending"
    INITIAL_INTEGRATE = "initial_integrate"
    INITIAL_ACCEPT = "initial_accept"

    SERIES_PLAN = "series_plan"
    VOLUME_PLAN = "volume_plan"
    CHAPTER_PLAN = "chapter_plan"
    SCENE_PLAN = "scene_plan"

    SCENE_CARD = "scene_card"
    SCENE_PROSE = "scene_prose"
    SCENE_CONTINUITY = "scene_continuity"
    SCENE_COMMIT = "scene_commit"

    VOLUME_HANDOFF = "volume_handoff"
    COMPLETION = "completion"
    PUBLICATION = "publication"


# OpenAIStoryModelが描画できるVersion 1の全Template工程。
#
# briefはStage enum上ではinputに属するが、Keywords入力から
# Briefを生成・批評・修正する際のmodel stageとして使用する。
V1_TEMPLATE_STAGES = (
    "brief",
    Stage.INITIAL_CONCEPT.value,
    Stage.INITIAL_CHARACTERS.value,
    Stage.INITIAL_RELATIONSHIPS.value,
    Stage.INITIAL_WORLD.value,
    Stage.INITIAL_KNOWLEDGE.value,
    Stage.INITIAL_THREADS.value,
    Stage.INITIAL_ENDING.value,
    Stage.INITIAL_INTEGRATE.value,
    Stage.SERIES_PLAN.value,
    Stage.VOLUME_PLAN.value,
    Stage.CHAPTER_PLAN.value,
    Stage.SCENE_PLAN.value,
    "scene_card_v1",
    "scene_prose_v1",
    "scene_continuity_v1",
    Stage.VOLUME_HANDOFF.value,
    Stage.COMPLETION.value,
)

ACTIVE_TEMPLATE_STAGES = V1_TEMPLATE_STAGES


INPUT_STAGES = (
    Stage.INPUT,
)

INITIAL_DESIGN_STAGES = (
    Stage.INITIAL_CONCEPT,
    Stage.INITIAL_CHARACTERS,
    Stage.INITIAL_RELATIONSHIPS,
    Stage.INITIAL_WORLD,
    Stage.INITIAL_KNOWLEDGE,
    Stage.INITIAL_THREADS,
    Stage.INITIAL_ENDING,
    Stage.INITIAL_INTEGRATE,
    Stage.INITIAL_ACCEPT,
)

PLANNING_STAGES = (
    Stage.SERIES_PLAN,
    Stage.VOLUME_PLAN,
    Stage.CHAPTER_PLAN,
    Stage.SCENE_PLAN,
)

SCENE_STAGES = (
    Stage.SCENE_CARD,
    Stage.SCENE_PROSE,
    Stage.SCENE_CONTINUITY,
    Stage.SCENE_COMMIT,
)

FINALIZATION_STAGES = (
    Stage.VOLUME_HANDOFF,
    Stage.COMPLETION,
    Stage.PUBLICATION,
)

STAGE_GROUPS = (
    INPUT_STAGES,
    INITIAL_DESIGN_STAGES,
    PLANNING_STAGES,
    SCENE_STAGES,
    FINALIZATION_STAGES,
)

STAGES = tuple(
    stage.value
    for group in STAGE_GROUPS
    for stage in group
)
