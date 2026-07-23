"""Storycraft Version 1 initial_integrate Stage実行。"""
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
    stage="initial_integrate",
    artifact_type="initial_design",
    review_category="initial_design_consistency",
    next_stage="initial_accept",
)


class InitialIntegrateStageService:
    """採用済み初期設計部品を一つの整合したCandidateへ統合する。"""

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
        version_root = (
            self.workspace_root / "design/initial/v0001"
        )
        brief = read_json(
            self.workspace_root / "input/brief.json"
        )
        concept = read_json(version_root / "concept.json")
        characters = read_json(
            version_root / "characters.json"
        )
        relationships = read_json(
            version_root / "relationships.json"
        )
        world = read_json(version_root / "world.json")
        knowledge = read_json(
            version_root / "knowledge.json"
        )
        threads = read_json(version_root / "threads.json")
        ending = read_json(version_root / "ending.json")

        ContractValidator._validate_initial_integrate_prerequisites(
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
            threads,
            ending,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_initial_integrate(
                candidate,
                brief,
                concept,
                characters,
                relationships,
                world,
                knowledge,
                threads,
                ending,
            )

        state = self.runner.state_store.load()

        return self.runner.run(
            model,
            context={
                "brief": deepcopy(brief),
                "concept": deepcopy(concept),
                "characters": deepcopy(characters),
                "relationships": deepcopy(relationships),
                "world": deepcopy(world),
                "knowledge": deepcopy(knowledge),
                "threads": deepcopy(threads),
                "ending": deepcopy(ending),
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                concept,
                characters,
                relationships,
                world,
                knowledge,
                threads,
                ending,
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
        characters: dict[str, Any],
        relationships: dict[str, Any],
        world: dict[str, Any],
        knowledge: dict[str, Any],
        threads: dict[str, Any],
        ending: dict[str, Any],
    ) -> None:
        """Review済み統合Candidateを後続accept用に確定する。"""
        ContractValidator._validate_initial_integrate(
            candidate,
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
            threads,
            ending,
        )

        adopted = deepcopy(candidate)
        version_root = (
            self.workspace_root / "design/initial/v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "integrated.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "Review済み統合Initial Designを"
                    "上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".integrated-",
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
            ContractValidator._validate_initial_integrate(
                written,
                brief,
                concept,
                characters,
                relationships,
                world,
                knowledge,
                threads,
                ending,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
