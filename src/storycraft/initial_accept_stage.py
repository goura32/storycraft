"""Storycraft Version 1 initial_accept Stage実行。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .initial_generation import (
    build_accepted_initial_design,
    build_initial_generation,
    validate_accepted_initial_design,
    validate_initial_generation,
)
from .reviewed_candidate_stage import (
    fsync_directory,
    read_json,
    reserve_identifier,
    utc_now,
    write_json_new,
)
from .run_state import RunStateStore, validate_run_state
from .series_contracts import ContractError, ContractValidator
from .stage_transition import advance_run_state
from .workspace import validate_workspace_layout


class InitialAcceptStageService:
    """統合Initial Designを採用しInitial Generationを作る。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        *,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        validate_workspace_layout(self.workspace_root)
        state = self.state_store.load()

        if state["current_stage"] != "initial_accept":
            raise ContractError(
                "現在のrun-stateはinitial_acceptではありません"
            )
        if state["status"] not in {
            "initializing",
            "running",
        }:
            raise ContractError(
                "initial_acceptを実行できる"
                "run statusではありません"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるため"
                "initial_acceptを開始できません"
            )

        timestamp = updated_at or utc_now()
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
        integrated = read_json(
            version_root / "integrated.json"
        )

        ContractValidator._validate_initial_integrate(
            integrated,
            brief,
            concept,
            characters,
            relationships,
            world,
            knowledge,
            threads,
            ending,
        )

        initial_design = self._ensure_initial_design(
            integrated,
            brief,
            timestamp,
        )
        generation_id = self._find_initial_generation(
            initial_design,
        )

        if generation_id is None:
            generation_id = reserve_identifier(
                self.workspace_root,
                "next_generation",
                "gen",
                timestamp,
            )
            self._create_initial_generation(
                initial_design,
                generation_id,
                timestamp,
            )

        generation = self._read_generation(generation_id)
        validate_initial_generation(
            generation,
            initial_design,
        )

        with_generation = deepcopy(state)
        with_generation["current_generation_id"] = (
            generation_id
        )
        validate_run_state(with_generation)

        advanced = advance_run_state(
            with_generation,
            next_stage="series_plan",
            next_target={
                "series": state["workspace_id"],
                "basis_generation_id": generation_id,
            },
            updated_at=timestamp,
        )
        self.state_store.save(advanced)
        validate_workspace_layout(self.workspace_root)
        return advanced

    def _ensure_initial_design(
        self,
        integrated: dict[str, Any],
        brief: dict[str, Any],
        created_at: str,
    ) -> dict[str, Any]:
        path = (
            self.workspace_root
            / "design/initial/v0001/initial-design.json"
        )

        if path.exists():
            existing = read_json(path)
            validate_accepted_initial_design(
                existing,
                integrated,
                brief,
            )
            return existing

        adopted = build_accepted_initial_design(
            integrated,
            brief,
            created_at=created_at,
        )
        validate_accepted_initial_design(
            adopted,
            integrated,
            brief,
        )
        write_json_new(path, adopted)
        fsync_directory(path.parent)
        return adopted

    def _find_initial_generation(
        self,
        initial_design: dict[str, Any],
    ) -> str | None:
        matches: list[str] = []
        root = self.workspace_root / "generations"

        for directory in sorted(root.glob("gen-*")):
            if not directory.is_dir():
                continue
            commit_path = directory / "commit.json"
            if not commit_path.is_file():
                continue
            commit = read_json(commit_path)
            if (
                commit.get("parent_generation_id") is None
                and commit.get("commit_type")
                == "initial_design"
                and commit.get("source_artifact_id")
                == initial_design["design_id"]
            ):
                files = self._read_generation(
                    directory.name
                )
                validate_initial_generation(
                    files,
                    initial_design,
                )
                matches.append(directory.name)

        if len(matches) > 1:
            raise ContractError(
                "Initial Generationが複数存在します"
            )
        return matches[0] if matches else None

    def _create_initial_generation(
        self,
        initial_design: dict[str, Any],
        generation_id: str,
        created_at: str,
    ) -> None:
        generations_root = (
            self.workspace_root / "generations"
        )
        final = generations_root / generation_id

        if final.exists():
            files = self._read_generation(generation_id)
            validate_initial_generation(
                files,
                initial_design,
            )
            return

        staging_parent = (
            self.workspace_root / "runtime/staging"
        )
        staging = Path(
            tempfile.mkdtemp(
                prefix=f"generation-{generation_id}-",
                dir=staging_parent,
            )
        )

        files = build_initial_generation(
            initial_design,
            generation_id=generation_id,
            created_at=created_at,
        )

        try:
            for name, value in files.items():
                write_json_new(staging / name, value)

            written = {
                name: read_json(staging / name)
                for name in files
            }
            validate_initial_generation(
                written,
                initial_design,
            )

            staging.rename(final)
            fsync_directory(generations_root)
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise

    def _read_generation(
        self,
        generation_id: str,
    ) -> dict[str, dict[str, Any]]:
        root = (
            self.workspace_root
            / "generations"
            / generation_id
        )
        if not root.is_dir():
            raise ContractError(
                "Initial Generation directoryがありません"
            )

        return {
            name: read_json(root / name)
            for name in (
                "canon.json",
                "state.json",
                "evidence.json",
                "commit.json",
            )
        }
