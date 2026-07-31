"""docs v2 の唯一の工程定義。"""
from __future__ import annotations
from enum import StrEnum

class Stage(StrEnum):
    REQUEST_INTAKE = "request_intake"
    INITIAL_DESIGN = "initial_design"
    SERIES_PLAN = "series_plan"
    VOLUME_PLAN = "volume_plan"
    CHAPTER_PLAN = "chapter_plan"
    SCENE_PLAN = "scene_plan"
    SCENE_CARD = "scene_card"
    SCENE_PROSE = "scene_prose"
    SCENE_CONTINUITY = "scene_continuity"
    SCENE_COMMIT = "scene_commit"
    VOLUME_PUBLICATION = "volume_publication"

STAGES = tuple(stage.value for stage in Stage)
ACTIVE_TEMPLATE_STAGES: tuple[str, ...] = (
    "request_intake",
    "initial_design",
    "series_plan",
    "volume_plan",
    "chapter_plan",
    "scene_plan",
    "scene_card",
    "scene_prose",
    "scene_continuity",
)
INPUT_STAGES: tuple[Stage, ...] = ()
INITIAL_DESIGN_STAGES = (Stage.INITIAL_DESIGN,)
PLANNING_STAGES = (Stage.SERIES_PLAN, Stage.VOLUME_PLAN, Stage.CHAPTER_PLAN, Stage.SCENE_PLAN)
SCENE_STAGES = (Stage.SCENE_CARD, Stage.SCENE_PROSE, Stage.SCENE_CONTINUITY, Stage.SCENE_COMMIT)
FINALIZATION_STAGES = (Stage.VOLUME_PUBLICATION,)
STAGE_GROUPS = (INITIAL_DESIGN_STAGES, PLANNING_STAGES, SCENE_STAGES, FINALIZATION_STAGES)
