"""Storycraft Version 1 initial_concept Stage実行。"""
from __future__ import annotations

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
    stage="initial_concept",
    artifact_type="story_concept",
    review_category="concept_quality",
    next_stage="initial_characters",
)


class InitialConceptStageService:
    """Briefから採用済みStory Conceptを確定する。"""

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
        ContractValidator._validate_brief(brief)

        def validate(candidate: object) -> None:
            ContractValidator._validate_initial_concept(
                candidate,
                brief,
            )
            assert isinstance(candidate, dict)

            missing_tone = [
                item
                for item in brief["tone"]
                if item not in candidate["tone"]
            ]
            if missing_tone:
                raise ContractError(
                    "Initial ConceptがBriefのtoneを保持していません: "
                    + ", ".join(missing_tone)
                )

        return self.runner.run(
            model,
            context={"brief": brief},
            validator=validate,
            adopter=self._adopt,
            next_target={
                "series": self.runner.state_store.load()[
                    "workspace_id"
                ],
            },
            updated_at=updated_at,
        )

    def _adopt(self, concept: dict[str, Any]) -> None:
        """ConceptをInitial Design v0001へatomic採用する。"""
        brief = read_json(
            self.workspace_root / "input/brief.json"
        )
        ContractValidator._validate_initial_concept(
            concept,
            brief,
        )

        version_root = (
            self.workspace_root / "design/initial/v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "concept.json"

        if path.exists():
            existing = read_json(path)
            if existing != concept:
                raise ContractError(
                    "採用済みInitial Conceptを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".concept-",
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
                    concept,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            written = read_json(temporary)
            ContractValidator._validate_initial_concept(
                written,
                brief,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
