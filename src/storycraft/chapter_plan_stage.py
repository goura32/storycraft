"""Storycraft Version 1 chapter_plan Stage実行。"""
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
    stage="chapter_plan",
    artifact_type="chapter_plan",
    review_category="chapter_plan_quality",
    next_stage="scene_plan",
)


class ChapterPlanStageService:
    """一章を順序付きSceneへ具体化し、採用する。"""

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
        for number, label in (
            (volume_number, "Volume"),
            (chapter_number, "Chapter"),
        ):
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
            ):
                raise ContractError(
                    f"chapter_planには対象{label}番号が必要です"
                )

        generation_id = state["current_generation_id"]
        if generation_id is None:
            raise ContractError(
                "chapter_planにはcurrent Generationが必要です"
            )
        if target.get("basis_generation_id") != generation_id:
            raise ContractError(
                "chapter_plan targetのbasis_generation_idが"
                "current Generationと一致しません"
            )
        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "chapter_plan targetのseriesがworkspaceと"
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

        if (
            target.get("series_plan_id")
            != series_plan["series_plan_id"]
        ):
            raise ContractError(
                "chapter_plan targetのseries_plan_idが"
                "採用済みSeries Planと一致しません"
            )
        if (
            target.get("volume_plan_id")
            != volume_plan["volume_plan_id"]
        ):
            raise ContractError(
                "chapter_plan targetのvolume_plan_idが"
                "採用済みVolume Planと一致しません"
            )
        if volume_plan.get("volume_number") != volume_number:
            raise ContractError(
                "chapter_plan targetの対象巻が"
                "採用済みVolume Planと一致しません"
            )
        if not any(
            record.get("chapter_number") == chapter_number
            for record in volume_plan.get(
                "chapter_summaries",
                [],
            )
            if isinstance(record, dict)
        ):
            raise ContractError(
                "chapter_plan targetの対象章が"
                "Volume Planに存在しません"
            )

        prior_revelation_count = (
            self._validate_prior_chapter_plans(
                volume_number,
                chapter_number,
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
            ContractValidator._validate_chapter_plan(
                candidate,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                volume_number,
                chapter_number,
                generation_id,
            )
            if not isinstance(candidate, dict):
                raise ContractError(
                    "Chapter Plan Candidateはobjectが必要です"
                )
            if (
                prior_revelation_count
                + len(candidate["required_revelations"])
                > len(volume_plan["revelations"])
            ):
                raise ContractError(
                    "Chapter Planのrequired_revelationsが"
                    "Volume Planの未使用開示枠を超えています"
                )

        timestamp = updated_at or utc_now()
        chapter_plan_id = (
            f"chapter-plan-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
        )

        return self.runner.run(
            model,
            context={
                "brief": deepcopy(brief),
                "initial_design": deepcopy(initial_design),
                "series_plan": deepcopy(series_plan),
                "volume_plan": deepcopy(volume_plan),
                "current_generation": deepcopy(
                    current_generation
                ),
                "target_volume_number": volume_number,
                "target_chapter_number": chapter_number,
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                volume_number,
                chapter_number,
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
                "chapter_plan_id": chapter_plan_id,
                "volume_number": volume_number,
                "chapter_number": chapter_number,
                "scene_number": 1,
                "basis_generation_id": generation_id,
            },
            updated_at=timestamp,
        )

    def _validate_prior_chapter_plans(
        self,
        volume_number: int,
        chapter_number: int,
    ) -> int:
        """対象章より前の採用Planと使用済み開示数を確認する。"""
        revelation_count = 0
        for prior_number in range(1, chapter_number):
            path = (
                self.workspace_root
                / "design/chapter-plans"
                / (
                    f"v{volume_number:02d}"
                    f"-c{prior_number:03d}-v0001"
                )
                / "chapter-plan.json"
            )
            if not path.is_file():
                raise ContractError(
                    "後続Chapter Planには直前までの"
                    "採用済みChapter Planが必要です"
                )
            prior = read_json(path)
            revelations = prior.get(
                "required_revelations"
            )
            if not isinstance(revelations, list):
                raise ContractError(
                    "採用済みChapter Planの"
                    "required_revelationsが不正です"
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
        volume_number: int,
        chapter_number: int,
        basis_generation_id: str,
        created_at: str,
    ) -> None:
        """Review済みCandidateをimmutable Chapter Planへ採用する。"""
        ContractValidator._validate_chapter_plan(
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            volume_number,
            chapter_number,
            basis_generation_id,
        )

        chapter_plan_id = (
            f"chapter-plan-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
        )
        adopted = {
            "schema_version": 1,
            "chapter_plan_id": chapter_plan_id,
            "volume_number": volume_number,
            "chapter_number": chapter_number,
            "version": 1,
            "status": "accepted",
            "basis_generation_id": basis_generation_id,
            "volume_plan_id": volume_plan["volume_plan_id"],
            "parent_plan_id": None,
            **deepcopy(candidate),
            "created_at": created_at,
        }

        ContractValidator._validate_chapter_plan(
            adopted,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            volume_number,
            chapter_number,
            basis_generation_id,
            adopted=True,
        )

        version_root = (
            self.workspace_root
            / "design/chapter-plans"
            / (
                f"v{volume_number:02d}"
                f"-c{chapter_number:03d}-v0001"
            )
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "chapter-plan.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みChapter Planを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".chapter-plan-",
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
            ContractValidator._validate_chapter_plan(
                written,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                volume_number,
                chapter_number,
                basis_generation_id,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
