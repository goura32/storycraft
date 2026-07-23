"""Storycraft Version 1 series_plan Stage実行。"""
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
    stage="series_plan",
    artifact_type="series_plan",
    review_category="series_plan_quality",
    next_stage="volume_plan",
)


class SeriesPlanStageService:
    """全Volumeを通したシリーズ構造を生成、Review、採用する。"""

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

        generation_id = state["current_generation_id"]
        if generation_id is None:
            raise ContractError(
                "series_planにはcurrent Generationが必要です"
            )

        brief = read_json(
            self.workspace_root / "input/brief.json"
        )
        initial_design = read_json(
            self.workspace_root
            / "design/initial/v0001/initial-design.json"
        )
        initial_generation = self._read_generation(
            generation_id
        )
        validate_initial_generation(
            initial_generation,
            initial_design,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_series_plan(
                candidate,
                brief,
                initial_design,
                generation_id,
            )

        timestamp = updated_at or utc_now()

        return self.runner.run(
            model,
            context={
                "brief": deepcopy(brief),
                "initial_design": deepcopy(initial_design),
                "initial_generation": deepcopy(
                    initial_generation
                ),
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                initial_design,
                generation_id,
                timestamp,
            ),
            next_target={
                "series": state["workspace_id"],
                "series_plan_id": "series-plan-0001",
                "volume_number": 1,
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

    def _adopt(
        self,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        basis_generation_id: str,
        created_at: str,
    ) -> None:
        """Review済みCandidateをimmutable Series Planへ採用する。"""
        ContractValidator._validate_series_plan(
            candidate,
            brief,
            initial_design,
            basis_generation_id,
        )

        adopted = {
            "schema_version": 1,
            "series_plan_id": "series-plan-0001",
            "version": 1,
            "status": "accepted",
            "basis_generation_id": basis_generation_id,
            "parent_plan_id": None,
            **deepcopy(candidate),
            "created_at": created_at,
        }

        ContractValidator._validate_series_plan(
            adopted,
            brief,
            initial_design,
            basis_generation_id,
            adopted=True,
        )

        version_root = (
            self.workspace_root
            / "design/series-plans/series-plan-v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "series-plan.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みSeries Planを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".series-plan-",
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
            ContractValidator._validate_series_plan(
                written,
                brief,
                initial_design,
                basis_generation_id,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
