"""Storycraft Version 1 initial_knowledge Stage実行。"""
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
    stage="initial_knowledge",
    artifact_type="knowledge",
    review_category="knowledge_quality",
    next_stage="initial_threads",
)


class InitialKnowledgeStageService:
    """世界のFactと人物ごとの開始時Knowledgeを確定する。"""

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

        ContractValidator._validate_initial_knowledge_prerequisites(
            brief,
            concept,
            characters,
            relationships,
            world,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_initial_knowledge(
                candidate,
                brief,
                concept,
                characters,
                relationships,
                world,
            )

        state = self.runner.state_store.load()

        return self.runner.run(
            model,
            context={
                "concept": deepcopy(concept),
                "characters": deepcopy(characters),
                "relationships": deepcopy(relationships),
                "world": deepcopy(world),
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                concept,
                characters,
                relationships,
                world,
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
    ) -> None:
        """Factへ決定的IDを付与して採用する。"""
        ContractValidator._validate_initial_knowledge(
            candidate,
            brief,
            concept,
            characters,
            relationships,
            world,
        )

        knowledge_ids = [
            f"know-{index:04d}"
            for index in range(
                1,
                len(candidate["knowledge_facts"]) + 1,
            )
        ]

        adopted = {
            "knowledge_facts": [
                {
                    "knowledge_id": knowledge_ids[index],
                    **deepcopy(record),
                }
                for index, record in enumerate(
                    candidate["knowledge_facts"]
                )
            ],
            "character_knowledge": [
                {
                    "character_id": record["character_id"],
                    "knowledge_id": knowledge_ids[
                        record["knowledge_index"]
                    ],
                    "state": record["state"],
                }
                for record in candidate[
                    "character_knowledge"
                ]
            ],
        }

        ContractValidator._validate_initial_knowledge(
            adopted,
            brief,
            concept,
            characters,
            relationships,
            world,
            adopted=True,
        )

        version_root = (
            self.workspace_root / "design/initial/v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "knowledge.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みInitial Knowledgeを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".knowledge-",
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
            ContractValidator._validate_initial_knowledge(
                written,
                brief,
                concept,
                characters,
                relationships,
                world,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
