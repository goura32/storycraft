"""Storycraft Version 1 volume_plan Stage実行。"""
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
    stage="volume_plan",
    artifact_type="volume_plan",
    review_category="volume_plan_quality",
    next_stage="chapter_plan",
)


class VolumePlanStageService:
    """一巻の役割と到達点を生成、Review、採用する。"""

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
        if (
            not isinstance(volume_number, int)
            or isinstance(volume_number, bool)
            or volume_number < 1
        ):
            raise ContractError(
                "volume_planには対象Volume番号が必要です"
            )

        generation_id = state["current_generation_id"]
        if generation_id is None:
            raise ContractError(
                "volume_planにはcurrent Generationが必要です"
            )
        if target.get("basis_generation_id") != generation_id:
            raise ContractError(
                "volume_plan targetのbasis_generation_idが"
                "current Generationと一致しません"
            )
        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "volume_plan targetのseriesがworkspaceと"
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

        if (
            target.get("series_plan_id")
            != series_plan["series_plan_id"]
        ):
            raise ContractError(
                "volume_plan targetのseries_plan_idが"
                "採用済みSeries Planと一致しません"
            )

        current_generation = self._read_generation(
            generation_id
        )
        self._validate_current_generation(
            current_generation,
            generation_id,
            initial_design,
        )
        previous_handoff = self._read_previous_handoff(
            volume_number,
            generation_id,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_volume_plan(
                candidate,
                brief,
                initial_design,
                series_plan,
                volume_number,
                generation_id,
            )

        timestamp = updated_at or utc_now()
        volume_plan_id = f"volume-plan-v{volume_number:02d}"

        return self.runner.run(
            model,
            context={
                "brief": deepcopy(brief),
                "initial_design": deepcopy(initial_design),
                "series_plan": deepcopy(series_plan),
                "current_generation": deepcopy(
                    current_generation
                ),
                "previous_handoff": deepcopy(
                    previous_handoff
                ),
                "target_volume_number": volume_number,
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                initial_design,
                series_plan,
                volume_number,
                generation_id,
                timestamp,
            ),
            next_target={
                "series": state["workspace_id"],
                "series_plan_id": series_plan[
                    "series_plan_id"
                ],
                "volume_plan_id": volume_plan_id,
                "volume_number": volume_number,
                "chapter_number": 1,
                "basis_generation_id": generation_id,
            },
            updated_at=timestamp,
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

    def _read_previous_handoff(
        self,
        volume_number: int,
        generation_id: str,
    ) -> dict[str, Any] | None:
        if volume_number == 1:
            return None

        previous_number = volume_number - 1
        path = (
            self.workspace_root
            / "handoffs"
            / f"handoff-v{previous_number:02d}"
            / "handoff.json"
        )
        if not path.is_file():
            raise ContractError(
                "第二巻以降のvolume_planには"
                "前Volume Handoffが必要です"
            )

        handoff = read_json(path)
        if handoff.get("schema_version") != 1:
            raise ContractError(
                "前Volume Handoffのschema_versionが不正です"
            )
        if handoff.get("handoff_id") != (
            f"handoff-v{previous_number:02d}"
        ):
            raise ContractError(
                "前Volume HandoffのIDが不正です"
            )
        if handoff.get("volume_number") != previous_number:
            raise ContractError(
                "前Volume Handoffの巻番号が不正です"
            )
        if handoff.get("basis_generation_id") != generation_id:
            raise ContractError(
                "前Volume Handoffのbasis_generation_idが"
                "current Generationと一致しません"
            )
        return handoff

    def _adopt(
        self,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_number: int,
        basis_generation_id: str,
        created_at: str,
    ) -> None:
        """Review済みCandidateをimmutable Volume Planへ採用する。"""
        ContractValidator._validate_volume_plan(
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_number,
            basis_generation_id,
        )

        volume_plan_id = f"volume-plan-v{volume_number:02d}"
        adopted = {
            "schema_version": 1,
            "volume_plan_id": volume_plan_id,
            "volume_number": volume_number,
            "version": 1,
            "status": "accepted",
            "basis_generation_id": basis_generation_id,
            "series_plan_id": series_plan["series_plan_id"],
            "parent_plan_id": None,
            **deepcopy(candidate),
            "created_at": created_at,
        }

        ContractValidator._validate_volume_plan(
            adopted,
            brief,
            initial_design,
            series_plan,
            volume_number,
            basis_generation_id,
            adopted=True,
        )

        version_root = (
            self.workspace_root
            / "design/volume-plans"
            / f"v{volume_number:02d}-v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "volume-plan.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みVolume Planを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".volume-plan-",
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
            ContractValidator._validate_volume_plan(
                written,
                brief,
                initial_design,
                series_plan,
                volume_number,
                basis_generation_id,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
