"""Storycraft Version 1 volume_handoff Stage実行。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
from typing import Any

from .immutable_directory import (
    finalize_immutable_directory,
)
from .reviewed_candidate_stage import (
    ReviewedCandidateSpec,
    ReviewedCandidateStageRunner,
    read_json,
    utc_now,
    write_json_new,
)
from .series_contracts import (
    ContractError,
    ContractValidator,
    StoryModel,
)
from .stages import Stage
from .workspace import validate_workspace_layout


_SPEC = ReviewedCandidateSpec(
    stage=Stage.VOLUME_HANDOFF.value,
    artifact_type="volume_handoff",
    review_category="volume_handoff_quality",
    # 実際の遷移先はVolume番号からrun時に決定する。
    next_stage=Stage.COMPLETION.value,
)


def determine_volume_handoff_transition(
    *,
    state: dict[str, Any],
    series_plan: dict[str, Any],
    volume_number: int,
    basis_generation_id: str,
) -> tuple[Stage, dict[str, Any]]:
    """採用済みSeries PlanからHandoff後の遷移を決める。"""
    workspace_id = _required_string(
        state.get("workspace_id"),
        "run-state.workspace_id",
    )
    series_plan_id = _required_string(
        series_plan.get("series_plan_id"),
        "Series Plan.series_plan_id",
    )
    generation_id = _required_string(
        basis_generation_id,
        "basis_generation_id",
    )

    volume_count = _positive_integer(
        series_plan.get("volume_count"),
        "Series Plan.volume_count",
    )
    if not 1 <= volume_number <= volume_count:
        raise ContractError(
            "Volume Handoff対象巻が"
            "Series Plan範囲外です"
        )

    if volume_number < volume_count:
        return (
            Stage.VOLUME_PLAN,
            {
                "series": workspace_id,
                "series_plan_id": series_plan_id,
                "volume_number": volume_number + 1,
                "basis_generation_id": generation_id,
            },
        )

    return (
        Stage.COMPLETION,
        {
            "series": workspace_id,
            "series_plan_id": series_plan_id,
            "volume_number": volume_number,
            "basis_generation_id": generation_id,
            "final_handoff_id": (
                f"handoff-v{volume_number:02d}"
            ),
        },
    )


class VolumeHandoffStageService:
    """巻末状態をReviewしimmutable Handoffへ採用する。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.runner = ReviewedCandidateStageRunner(
            self.workspace_root,
            _SPEC,
        )

    def run(
        self,
        model: StoryModel,
        *,
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace_layout(
                self.workspace_root
            )

        state = self.runner.state_store.load()

        if (
            state["current_stage"]
            != Stage.VOLUME_HANDOFF.value
        ):
            raise ContractError(
                "現在のrun-stateは"
                "volume_handoffではありません"
            )

        target = state["current_target"]
        volume_number = _positive_integer(
            target.get("volume_number"),
            "current_target.volume_number",
        )

        generation_id = state["current_generation_id"]
        if not isinstance(generation_id, str):
            raise ContractError(
                "volume_handoffには"
                "current Generationが必要です"
            )
        if (
            target.get("basis_generation_id")
            != generation_id
        ):
            raise ContractError(
                "volume_handoff targetの"
                "basis_generation_idが"
                "current Generationと一致しません"
            )
        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "volume_handoff targetのseriesが"
                "workspaceと一致しません"
            )

        series_plan = read_json(
            self.workspace_root
            / "design/series-plans"
            / "series-plan-v0001"
            / "series-plan.json"
        )
        volume_plan = read_json(
            self.workspace_root
            / "design/volume-plans"
            / f"v{volume_number:02d}-v0001"
            / "volume-plan.json"
        )

        if (
            target.get("series_plan_id")
            != series_plan.get("series_plan_id")
        ):
            raise ContractError(
                "volume_handoff targetのseries_plan_idが"
                "採用済みSeries Planと一致しません"
            )
        if (
            target.get("volume_plan_id")
            != volume_plan.get("volume_plan_id")
        ):
            raise ContractError(
                "volume_handoff targetのvolume_plan_idが"
                "採用済みVolume Planと一致しません"
            )
        if (
            volume_plan.get("volume_number")
            != volume_number
        ):
            raise ContractError(
                "volume_handoff対象巻が"
                "Volume Planと一致しません"
            )
        if (
            volume_plan.get("series_plan_id")
            != series_plan.get("series_plan_id")
        ):
            raise ContractError(
                "Volume PlanのSeries Plan参照が"
                "一致しません"
            )

        (
            chapter_plans,
            completed_scenes,
            completed_chapter_ids,
            completed_scene_ids,
        ) = self._load_completed_volume(
            volume_plan,
            volume_number,
        )

        current_generation = self._read_generation(
            generation_id
        )
        self._validate_terminal_generation(
            current_generation,
            generation_id,
            completed_scene_ids,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_volume_handoff(
                candidate,
                current_generation,
                series_plan,
                volume_plan,
                volume_number,
                generation_id,
            )

        timestamp = updated_at or utc_now()
        next_stage, next_target = (
            determine_volume_handoff_transition(
                state=state,
                series_plan=series_plan,
                volume_number=volume_number,
                basis_generation_id=generation_id,
            )
        )

        return self.runner.run(
            model,
            context={
                "series_plan": deepcopy(series_plan),
                "volume_plan": deepcopy(volume_plan),
                "chapter_plans": deepcopy(chapter_plans),
                "completed_scenes": deepcopy(
                    completed_scenes
                ),
                "current_generation": deepcopy(
                    current_generation
                ),
                "target_volume_number": volume_number,
                "is_final_volume": (
                    volume_number
                    == series_plan["volume_count"]
                ),
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                current_generation,
                series_plan,
                volume_plan,
                volume_number,
                generation_id,
                completed_chapter_ids,
                completed_scene_ids,
                timestamp,
            ),
            next_stage=next_stage.value,
            next_target=next_target,
            updated_at=timestamp,
            workspace_already_validated=True,
        )

    def _load_completed_volume(
        self,
        volume_plan: dict[str, Any],
        volume_number: int,
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[str],
        list[str],
    ]:
        """Plan順で全Chapter Planと確定Sceneを読み込む。"""
        chapter_numbers = _ordered_numbers(
            volume_plan.get("chapter_summaries"),
            field="chapter_number",
            label="Volume Plan Chapter",
        )

        chapter_plans: list[dict[str, Any]] = []
        completed_scenes: list[dict[str, Any]] = []
        completed_chapter_ids: list[str] = []
        completed_scene_ids: list[str] = []
        expected_scene_plan_directories: set[str] = set()

        for chapter_number in chapter_numbers:
            chapter_plan_id = (
                f"chapter-plan-v{volume_number:02d}"
                f"-c{chapter_number:03d}"
            )
            chapter_path = (
                self.workspace_root
                / "design/chapter-plans"
                / (
                    f"v{volume_number:02d}"
                    f"-c{chapter_number:03d}-v0001"
                )
                / "chapter-plan.json"
            )
            if not chapter_path.is_file():
                raise ContractError(
                    "Volume Handoffには全Chapterの"
                    "採用済みChapter Planが必要です"
                )

            chapter_plan = read_json(chapter_path)
            if (
                chapter_plan.get("chapter_plan_id")
                != chapter_plan_id
                or chapter_plan.get("volume_number")
                != volume_number
                or chapter_plan.get("chapter_number")
                != chapter_number
                or chapter_plan.get("volume_plan_id")
                != volume_plan.get("volume_plan_id")
            ):
                raise ContractError(
                    "Volume HandoffのChapter Planが"
                    "採用済みVolume Planと一致しません"
                )

            scene_numbers = _ordered_numbers(
                chapter_plan.get("scene_summaries"),
                field="scene_number",
                label="Chapter Plan Scene",
            )

            completed_chapter_ids.append(
                f"chapter-v{volume_number:02d}"
                f"-c{chapter_number:03d}"
            )
            chapter_plans.append(chapter_plan)

            for scene_number in scene_numbers:
                scene_id = (
                    f"scene-v{volume_number:02d}"
                    f"-c{chapter_number:03d}"
                    f"-s{scene_number:03d}"
                )
                scene_plan_id = (
                    f"scene-plan-v{volume_number:02d}"
                    f"-c{chapter_number:03d}"
                    f"-s{scene_number:03d}"
                )
                scene_plan_directory = (
                    f"v{volume_number:02d}"
                    f"-c{chapter_number:03d}"
                    f"-s{scene_number:03d}-v0001"
                )
                expected_scene_plan_directories.add(
                    scene_plan_directory
                )

                scene_plan_path = (
                    self.workspace_root
                    / "design/scene-plans"
                    / scene_plan_directory
                    / "scene-plan.json"
                )
                if not scene_plan_path.is_file():
                    raise ContractError(
                        "Volume Handoffには全Sceneの"
                        "採用済みScene Planが必要です"
                    )
                scene_plan = read_json(scene_plan_path)
                if (
                    scene_plan.get("scene_plan_id")
                    != scene_plan_id
                    or scene_plan.get("chapter_plan_id")
                    != chapter_plan_id
                    or scene_plan.get("volume_number")
                    != volume_number
                    or scene_plan.get("chapter_number")
                    != chapter_number
                    or scene_plan.get("scene_number")
                    != scene_number
                ):
                    raise ContractError(
                        "Volume HandoffのScene Planが"
                        "Chapter Planと一致しません"
                    )

                scene_root = (
                    self.workspace_root / "scenes" / scene_id
                )
                if (
                    scene_root.is_symlink()
                    or not scene_root.is_dir()
                ):
                    raise ContractError(
                        "Volume Handoffには全計画Sceneの"
                        "確定directoryが必要です"
                    )

                expected_files = {
                    "scene-card.json",
                    "prose.md",
                    "continuity.json",
                    "commit.json",
                }
                if {
                    entry.name
                    for entry in scene_root.iterdir()
                } != expected_files:
                    raise ContractError(
                        "確定Scene directoryの"
                        "file構成が不正です"
                    )

                scene_card = read_json(
                    scene_root / "scene-card.json"
                )
                continuity = read_json(
                    scene_root / "continuity.json"
                )
                commit = read_json(
                    scene_root / "commit.json"
                )
                prose = (
                    scene_root / "prose.md"
                ).read_text(encoding="utf-8")

                if not prose.strip():
                    raise ContractError(
                        "確定Sceneのprose.mdが空です"
                    )
                if (
                    scene_card.get("scene_id") != scene_id
                    or scene_card.get("scene_plan_id")
                    != scene_plan_id
                    or continuity.get("scene_id")
                    != scene_id
                    or commit.get("scene_id") != scene_id
                ):
                    raise ContractError(
                        "確定Sceneの参照IDが"
                        "Plan順と一致しません"
                    )
                if (
                    continuity.get("result_generation_id")
                    != commit.get("result_generation_id")
                ):
                    raise ContractError(
                        "確定Sceneのresult Generationが"
                        "一致しません"
                    )

                completed_scene_ids.append(scene_id)
                completed_scenes.append({
                    "scene_id": scene_id,
                    "chapter_id": (
                        f"chapter-v{volume_number:02d}"
                        f"-c{chapter_number:03d}"
                    ),
                    "scene_plan": scene_plan,
                    "scene_card": scene_card,
                    "prose": prose,
                    "continuity": continuity,
                    "commit": commit,
                })

        actual_scene_ids = {
            entry.name
            for entry in (
                self.workspace_root / "scenes"
            ).glob(
                f"scene-v{volume_number:02d}-c*-s*"
            )
            if entry.is_dir() and not entry.is_symlink()
        }
        if actual_scene_ids != set(completed_scene_ids):
            raise ContractError(
                "Volume内の確定Sceneが"
                "採用済みPlan順と一致しません"
            )

        actual_scene_plan_directories = {
            entry.name
            for entry in (
                self.workspace_root
                / "design/scene-plans"
            ).glob(
                f"v{volume_number:02d}-c*-s*-v0001"
            )
            if entry.is_dir() and not entry.is_symlink()
        }
        if (
            actual_scene_plan_directories
            != expected_scene_plan_directories
        ):
            raise ContractError(
                "Volume内のScene Planが"
                "採用済みPlan順と一致しません"
            )

        return (
            chapter_plans,
            completed_scenes,
            completed_chapter_ids,
            completed_scene_ids,
        )

    def _read_generation(
        self,
        generation_id: str,
    ) -> dict[str, Any]:
        root = (
            self.workspace_root
            / "generations"
            / generation_id
        )
        if root.is_symlink() or not root.is_dir():
            raise ContractError(
                "巻末Generation directoryが存在しません"
            )

        generation: dict[str, Any] = {}
        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            path = root / name
            if not path.is_file():
                raise ContractError(
                    "巻末Generationの必須fileが"
                    f"ありません: {name}"
                )
            generation[name] = read_json(path)
        return generation

    @staticmethod
    def _validate_terminal_generation(
        generation: dict[str, Any],
        generation_id: str,
        completed_scene_ids: list[str],
    ) -> None:
        if not completed_scene_ids:
            raise ContractError(
                "Volume Handoffには"
                "一つ以上の確定Sceneが必要です"
            )

        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            record = generation.get(name)
            if (
                not isinstance(record, dict)
                or record.get("generation_id")
                != generation_id
            ):
                raise ContractError(
                    "巻末Generationが不正です: "
                    f"{name}"
                )

        commit = generation["commit.json"]
        if (
            commit.get("commit_type") != "scene"
            or commit.get("source_artifact_type")
            != "scene"
            or commit.get("source_artifact_id")
            != completed_scene_ids[-1]
        ):
            raise ContractError(
                "current Generationが"
                "Volume最終SceneのGenerationではありません"
            )

        evidence = generation["evidence.json"].get(
            "evidence"
        )
        if not isinstance(evidence, list):
            raise ContractError(
                "巻末Generation.evidenceが不正です"
            )
        for record in evidence:
            if (
                not isinstance(record, dict)
                or record.get("scene_id")
                not in completed_scene_ids
            ):
                raise ContractError(
                    "巻末GenerationがVolume外Sceneの"
                    "Evidenceを参照しています"
                )

    def _adopt(
        self,
        candidate: dict[str, Any],
        current_generation: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        volume_number: int,
        basis_generation_id: str,
        completed_chapter_ids: list[str],
        completed_scene_ids: list[str],
        created_at: str,
    ) -> None:
        """Review済みCandidateをimmutable Handoffへ採用する。"""
        ContractValidator._validate_volume_handoff(
            candidate,
            current_generation,
            series_plan,
            volume_plan,
            volume_number,
            basis_generation_id,
        )

        adopted = {
            "schema_version": 1,
            "handoff_id": (
                f"handoff-v{volume_number:02d}"
            ),
            "volume_number": volume_number,
            "basis_generation_id": basis_generation_id,
            "completed_chapter_ids": deepcopy(
                completed_chapter_ids
            ),
            "completed_scene_ids": deepcopy(
                completed_scene_ids
            ),
            **deepcopy(candidate),
            "created_at": created_at,
        }

        def validate_directory(directory: Path) -> None:
            if {
                entry.name for entry in directory.iterdir()
            } != {"handoff.json"}:
                raise ContractError(
                    "Volume Handoff directoryの"
                    "file構成が不正です"
                )

            written = read_json(
                directory / "handoff.json"
            )
            ContractValidator._validate_volume_handoff(
                written,
                current_generation,
                series_plan,
                volume_plan,
                volume_number,
                basis_generation_id,
                adopted=True,
                expected_chapter_ids=(
                    completed_chapter_ids
                ),
                expected_scene_ids=completed_scene_ids,
            )

        handoffs_root = self.workspace_root / "handoffs"
        final = (
            handoffs_root
            / f"handoff-v{volume_number:02d}"
        )

        if final.exists() or final.is_symlink():
            if final.is_dir() and not final.is_symlink():
                validate_directory(final)
                if (
                    read_json(final / "handoff.json")
                    == adopted
                ):
                    return
            raise ContractError(
                "採用済みVolume Handoffを"
                "上書きできません"
            )

        staging = Path(
            tempfile.mkdtemp(
                prefix=(
                    f".handoff-v{volume_number:02d}-"
                ),
                dir=handoffs_root,
            )
        )

        try:
            write_json_new(
                staging / "handoff.json",
                adopted,
            )
            finalize_immutable_directory(
                staging=staging,
                final=final,
                validator=validate_directory,
            )
        except Exception:
            if staging.exists():
                import shutil

                shutil.rmtree(staging)
            raise


def _positive_integer(
    value: object,
    label: str,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ContractError(
            f"{label}は1以上の整数が必要です"
        )
    return value


def _required_string(
    value: object,
    label: str,
) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(
            f"{label}は空でない文字列が必要です"
        )
    return value


def _ordered_numbers(
    records: object,
    *,
    field: str,
    label: str,
) -> list[int]:
    if not isinstance(records, list) or not records:
        raise ContractError(
            f"{label}一覧が必要です"
        )

    numbers: list[int] = []
    for record in records:
        if not isinstance(record, dict):
            raise ContractError(
                f"{label}はobjectが必要です"
            )
        numbers.append(
            _positive_integer(
                record.get(field),
                f"{label}.{field}",
            )
        )

    if numbers != list(range(1, len(numbers) + 1)):
        raise ContractError(
            f"{label}番号は1からの連番が必要です"
        )
    return numbers
