"""Storycraft Version 1 scene_plan Stage実行。"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .initial_generation import validate_initial_generation
from .reviewed_candidate_stage import (
    ReviewedCandidateSpec,
    ReviewedCandidateStageRunner,
    fsync_directory,
    read_json,
    utc_now,
)
from .series_contracts import (
    ContractError,
    ContractValidator,
    StoryModel,
)
from .workspace import validate_workspace_layout


_SPEC = ReviewedCandidateSpec(
    stage="scene_plan",
    artifact_type="scene_plan",
    review_category="scene_plan_quality",
    next_stage="scene_card",
)


class ScenePlanStageService:
    """一Sceneの予定を生成、Review、採用する。"""

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
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        validate_workspace_layout(self.workspace_root)
        state = self.runner.state_store.load()
        target = state["current_target"]

        volume_number = target.get("volume_number")
        chapter_number = target.get("chapter_number")
        scene_number = target.get("scene_number")
        for number, label in (
            (volume_number, "Volume"),
            (chapter_number, "Chapter"),
            (scene_number, "Scene"),
        ):
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
            ):
                raise ContractError(
                    f"scene_planには対象{label}番号が必要です"
                )

        generation_id = state["current_generation_id"]
        if generation_id is None:
            raise ContractError(
                "scene_planにはcurrent Generationが必要です"
            )
        if target.get("basis_generation_id") != generation_id:
            raise ContractError(
                "scene_plan targetのbasis_generation_idが"
                "current Generationと一致しません"
            )
        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "scene_plan targetのseriesがworkspaceと"
                "一致しません"
            )

        brief = read_json(
            self.workspace_root / "input/brief.json"
        )
        initial_design = read_json(
            self.workspace_root
            / "design/initial/v0001/initial-design.json"
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
        chapter_plan = read_json(
            self.workspace_root
            / "design/chapter-plans"
            / (
                f"v{volume_number:02d}"
                f"-c{chapter_number:03d}-v0001"
            )
            / "chapter-plan.json"
        )

        expected_targets = {
            "series_plan_id": series_plan["series_plan_id"],
            "volume_plan_id": volume_plan["volume_plan_id"],
            "chapter_plan_id": chapter_plan["chapter_plan_id"],
        }
        for field, expected in expected_targets.items():
            if target.get(field) != expected:
                raise ContractError(
                    f"scene_plan targetの{field}が"
                    "採用済みPlanと一致しません"
                )

        if volume_plan.get("volume_number") != volume_number:
            raise ContractError(
                "scene_plan targetの対象巻が"
                "Volume Planと一致しません"
            )
        if (
            chapter_plan.get("volume_number") != volume_number
            or chapter_plan.get("chapter_number")
            != chapter_number
        ):
            raise ContractError(
                "scene_plan targetの対象巻章が"
                "Chapter Planと一致しません"
            )
        if not any(
            record.get("scene_number") == scene_number
            for record in chapter_plan.get(
                "scene_summaries",
                [],
            )
            if isinstance(record, dict)
        ):
            raise ContractError(
                "scene_plan targetの対象Sceneが"
                "Chapter Planに存在しません"
            )

        prior_revelation_count = (
            self._validate_prior_scene_plans(
                volume_number,
                chapter_number,
                scene_number,
            )
        )

        current_generation = self._read_generation(
            generation_id
        )
        self._validate_current_generation(
            current_generation,
            generation_id,
            initial_design,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_scene_plan(
                candidate,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                chapter_plan,
                current_generation,
                volume_number,
                chapter_number,
                scene_number,
                generation_id,
            )
            if not isinstance(candidate, dict):
                raise ContractError(
                    "Scene Plan Candidateはobjectが必要です"
                )
            if (
                prior_revelation_count
                + len(candidate["intended_revelations"])
                > len(chapter_plan["required_revelations"])
            ):
                raise ContractError(
                    "Scene Planのintended_revelationsが"
                    "Chapter Planの未使用開示枠を超えています"
                )

        timestamp = updated_at or utc_now()
        scene_plan_id = (
            f"scene-plan-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )
        scene_id = (
            f"scene-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )

        return self.runner.run(
            model,
            context={
                "brief": deepcopy(brief),
                "initial_design": deepcopy(initial_design),
                "series_plan": deepcopy(series_plan),
                "volume_plan": deepcopy(volume_plan),
                "chapter_plan": deepcopy(chapter_plan),
                "current_generation": deepcopy(
                    current_generation
                ),
                "target_volume_number": volume_number,
                "target_chapter_number": chapter_number,
                "target_scene_number": scene_number,
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                chapter_plan,
                current_generation,
                volume_number,
                chapter_number,
                scene_number,
                generation_id,
                timestamp,
            ),
            next_target={
                "series": state["workspace_id"],
                "series_plan_id": series_plan[
                    "series_plan_id"
                ],
                "volume_plan_id": volume_plan[
                    "volume_plan_id"
                ],
                "chapter_plan_id": chapter_plan[
                    "chapter_plan_id"
                ],
                "scene_plan_id": scene_plan_id,
                "volume_number": volume_number,
                "chapter_number": chapter_number,
                "scene_number": scene_number,
                "basis_generation_id": generation_id,
            },
            active_scene_id=scene_id,
            updated_at=timestamp,
        )

    def _validate_prior_scene_plans(
        self,
        volume_number: int,
        chapter_number: int,
        scene_number: int,
    ) -> int:
        """対象Sceneより前の採用Planと使用済み開示数を確認する。"""
        revelation_count = 0
        for prior_number in range(1, scene_number):
            path = (
                self.workspace_root
                / "design/scene-plans"
                / (
                    f"v{volume_number:02d}"
                    f"-c{chapter_number:03d}"
                    f"-s{prior_number:03d}-v0001"
                )
                / "scene-plan.json"
            )
            if not path.is_file():
                raise ContractError(
                    "後続Scene Planには直前までの"
                    "採用済みScene Planが必要です"
                )
            prior = read_json(path)
            revelations = prior.get(
                "intended_revelations"
            )
            if not isinstance(revelations, list):
                raise ContractError(
                    "採用済みScene Planの"
                    "intended_revelationsが不正です"
                )
            revelation_count += len(revelations)
        return revelation_count

    def _read_generation(
        self,
        generation_id: str,
    ) -> dict[str, Any]:
        root = (
            self.workspace_root
            / "generations"
            / generation_id
        )
        if not root.is_dir():
            raise ContractError(
                "current Generation directoryが存在しません"
            )

        files: dict[str, Any] = {}
        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            path = root / name
            if not path.is_file():
                raise ContractError(
                    "current Generationの必須fileが"
                    f"ありません: {name}"
                )
            files[name] = read_json(path)
        return files

    @staticmethod
    def _validate_current_generation(
        generation: dict[str, Any],
        generation_id: str,
        initial_design: dict[str, Any],
    ) -> None:
        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            value = generation.get(name)
            if not isinstance(value, dict):
                raise ContractError(
                    "current Generation fileが不正です: "
                    f"{name}"
                )
            if value.get("generation_id") != generation_id:
                raise ContractError(
                    "current Generationのgeneration_idが"
                    f"一致しません: {name}"
                )

        commit = generation["commit.json"]
        if commit.get("commit_type") == "initial_design":
            validate_initial_generation(
                generation,
                initial_design,
            )

    def _adopt(
        self,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        chapter_plan: dict[str, Any],
        current_generation: dict[str, Any],
        volume_number: int,
        chapter_number: int,
        scene_number: int,
        basis_generation_id: str,
        created_at: str,
    ) -> None:
        """Review済みCandidateをimmutable Scene Planへ採用する。"""
        ContractValidator._validate_scene_plan(
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            basis_generation_id,
        )

        scene_plan_id = (
            f"scene-plan-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )
        adopted = {
            "schema_version": 1,
            "scene_plan_id": scene_plan_id,
            "volume_number": volume_number,
            "chapter_number": chapter_number,
            "scene_number": scene_number,
            "version": 1,
            "status": "accepted",
            "basis_generation_id": basis_generation_id,
            "chapter_plan_id": chapter_plan[
                "chapter_plan_id"
            ],
            "parent_plan_id": None,
            **deepcopy(candidate),
            "created_at": created_at,
        }

        ContractValidator._validate_scene_plan(
            adopted,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            basis_generation_id,
            adopted=True,
        )

        version_root = (
            self.workspace_root
            / "design/scene-plans"
            / (
                f"v{volume_number:02d}"
                f"-c{chapter_number:03d}"
                f"-s{scene_number:03d}-v0001"
            )
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "scene-plan.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みScene Planを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".scene-plan-",
            suffix=".json.tmp",
            dir=version_root,
        )
        temporary = Path(temporary_name)

        try:
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    adopted,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            written = read_json(temporary)
            ContractValidator._validate_scene_plan(
                written,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                chapter_plan,
                current_generation,
                volume_number,
                chapter_number,
                scene_number,
                basis_generation_id,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
