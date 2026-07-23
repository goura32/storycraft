"""Storycraft Version 1 initial_relationships Stage実行。"""
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
    stage="initial_relationships",
    artifact_type="relationships",
    review_category="relationship_quality",
    next_stage="initial_world",
)


class InitialRelationshipsStageService:
    """ConceptとCharactersから主要人物関係を確定する。"""

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
        characters = read_json(
            self.workspace_root
            / "design/initial/v0001/characters.json"
        )

        ContractValidator._validate_initial_concept(
            concept,
            brief,
        )
        ContractValidator._validate_initial_characters(
            characters,
            brief,
            concept,
            adopted=True,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_initial_relationships(
                candidate,
                concept,
                characters,
            )

        state = self.runner.state_store.load()

        return self.runner.run(
            model,
            context={
                "concept": deepcopy(concept),
                "characters": deepcopy(characters),
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                concept,
                characters,
            ),
            next_target={
                "series": state["workspace_id"],
            },
            updated_at=updated_at,
        )

    def _adopt(
        self,
        candidate: dict[str, Any],
        concept: dict[str, Any],
        characters: dict[str, Any],
    ) -> None:
        """Relationshipへ決定的IDを付与して採用する。"""
        ContractValidator._validate_initial_relationships(
            candidate,
            concept,
            characters,
        )

        adopted = {
            "relationships": [
                {
                    "relationship_id": f"rel-{index:04d}",
                    **deepcopy(record),
                }
                for index, record in enumerate(
                    candidate["relationships"],
                    1,
                )
            ]
        }

        ContractValidator._validate_initial_relationships(
            adopted,
            concept,
            characters,
            adopted=True,
        )

        version_root = (
            self.workspace_root / "design/initial/v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "relationships.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みInitial Relationshipsを"
                    "上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".relationships-",
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
            ContractValidator._validate_initial_relationships(
                written,
                concept,
                characters,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
