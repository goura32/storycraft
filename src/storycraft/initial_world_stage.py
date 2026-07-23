"""Storycraft Version 1 initial_world Stage実行。"""
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
    stage="initial_world",
    artifact_type="world",
    review_category="world_quality",
    next_stage="initial_knowledge",
)


class InitialWorldStageService:
    """Briefと初期人物設計から世界設定を確定する。"""

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

        ContractValidator._validate_initial_world_prerequisites(
            brief,
            concept,
            characters,
            relationships,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_initial_world(
                candidate,
                brief,
                concept,
                characters,
                relationships,
            )

        state = self.runner.state_store.load()

        return self.runner.run(
            model,
            context={
                "brief": deepcopy(brief),
                "concept": deepcopy(concept),
                "characters": deepcopy(characters),
                "relationships": deepcopy(relationships),
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                concept,
                characters,
                relationships,
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
    ) -> None:
        """LocationとRuleへ決定的IDを付与して採用する。"""
        ContractValidator._validate_initial_world(
            candidate,
            brief,
            concept,
            characters,
            relationships,
        )

        location_ids = [
            f"loc-{index:04d}"
            for index in range(
                1,
                len(candidate["locations"]) + 1,
            )
        ]

        adopted_locations: list[dict[str, Any]] = []
        for index, record in enumerate(
            candidate["locations"]
        ):
            copied = deepcopy(record)
            parent_index = copied.pop(
                "parent_location_index"
            )
            copied["location_id"] = location_ids[index]
            copied["parent_location_id"] = (
                None
                if parent_index is None
                else location_ids[parent_index]
            )
            adopted_locations.append(copied)

        adopted = {
            "world": deepcopy(candidate["world"]),
            "locations": adopted_locations,
            "world_rules": [
                {
                    "rule_id": f"rule-{index:04d}",
                    **deepcopy(record),
                }
                for index, record in enumerate(
                    candidate["world_rules"],
                    1,
                )
            ],
        }

        ContractValidator._validate_initial_world(
            adopted,
            brief,
            concept,
            characters,
            relationships,
            adopted=True,
        )

        version_root = (
            self.workspace_root / "design/initial/v0001"
        )
        version_root.mkdir(parents=True, exist_ok=True)
        path = version_root / "world.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みInitial Worldを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".world-",
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
            ContractValidator._validate_initial_world(
                written,
                brief,
                concept,
                characters,
                relationships,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(version_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
