"""Storycraft Version 1 initial_threads Stage実行。"""
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
    stage="initial_threads",
    artifact_type="threads",
    review_category="thread_quality",
    next_stage="initial_ending",
)


class InitialThreadsStageService:
    """シリーズ全体で追跡する主要Threadを確定する。"""

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

        ContractValidator._validate_initial_threads_prerequisites(
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_initial_threads(
                candidate,
                brief,
                concept,
                characters,
                relationships,
                world,
                knowledge,
            )

        state = self.runner.state_store.load()

        return self.runner.run(
            model,
            context={
                "concept": deepcopy(concept),
                "characters": deepcopy(characters),
                "relationships": deepcopy(relationships),
                "world": deepcopy(world),
                "knowledge": deepcopy(knowledge),
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
    ) -> None:
        """Threadへ決定的IDを付与して採用する。"""
        ContractValidator._validate_initial_threads(
            candidate,
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
        )

        adopted = {
            "threads": [
                {
                    "thread_id": f"thread-{index:04d}",
                    **deepcopy(record),
                }
                for index, record in enumerate(
                    candidate["threads"],
                    1,
                )
            ]
        }

        ContractValidator._validate_initial_threads(
            adopted,
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
            adopted=True,
        )

        version_root = (
            self.workspace_root / "design/initial/v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "threads.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みInitial Threadsを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".threads-",
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
            ContractValidator._validate_initial_threads(
                written,
                brief,
                concept,
                characters,
                relationships,
                world,
                knowledge,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
