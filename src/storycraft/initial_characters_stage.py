"""Storycraft Version 1 initial_characters Stage実行。"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .reviewed_candidate_stage import (
    ReviewedCandidateSpec,
    ReviewedCandidateStageRunner,
    fsync_directory,
    read_json,
)
from .series_contracts import (
    ContractError,
    ContractValidator,
    StoryModel,
)


_SPEC = ReviewedCandidateSpec(
    stage="initial_characters",
    artifact_type="characters",
    review_category="character_quality",
    next_stage="initial_relationships",
)


class InitialCharactersStageService:
    """BriefとConceptから主要人物設計を確定する。"""

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
        brief = read_json(
            self.workspace_root / "input/brief.json"
        )
        concept = read_json(
            self.workspace_root
            / "design/initial/v0001/concept.json"
        )

        ContractValidator._validate_brief(brief)
        ContractValidator._validate_initial_concept(
            concept,
            brief,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_initial_characters(
                candidate,
                brief,
                concept,
            )

        state = self.runner.state_store.load()

        return self.runner.run(
            model,
            context={
                "brief": deepcopy(brief),
                "concept": deepcopy(concept),
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                concept,
            ),
            next_target={
                "series": state["workspace_id"],
            },
            updated_at=updated_at,
        )

    def _adopt(
        self,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        concept: dict[str, Any],
    ) -> None:
        """人物へ決定的IDを付与しInitial Designへ採用する。"""
        ContractValidator._validate_initial_characters(
            candidate,
            brief,
            concept,
        )

        adopted = {
            "characters": [
                {
                    "character_id": f"char-{index:04d}",
                    **deepcopy(record),
                }
                for index, record in enumerate(
                    candidate["characters"],
                    1,
                )
            ]
        }

        ContractValidator._validate_initial_characters(
            adopted,
            brief,
            concept,
            adopted=True,
        )

        version_root = (
            self.workspace_root / "design/initial/v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "characters.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みInitial Charactersを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".characters-",
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
            ContractValidator._validate_initial_characters(
                written,
                brief,
                concept,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
