"""Storycraft Version 1 scene_card Stage実行。"""
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
    stage="scene_card",
    artifact_type="scene_card",
    review_category="scene_card_quality",
    next_stage="scene_prose",
    model_stage="scene_card_v1",
)


class SceneCardStageService:
    """一Sceneの本文生成用詳細設計を確定する。"""

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
        chapter_number = target.get("chapter_number")
        scene_number = target.get("scene_number")
        for number, label in (
            (volume_number, "Volume"),
            (chapter_number, "Chapter"),
            (scene_number, "Scene"),
        ):
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
            ):
                raise ContractError(
                    f"scene_cardには対象{label}番号が必要です"
                )

        generation_id = state["current_generation_id"]
        if generation_id is None:
            raise ContractError(
                "scene_cardにはcurrent Generationが必要です"
            )
        if target.get("basis_generation_id") != generation_id:
            raise ContractError(
                "scene_card targetのbasis_generation_idが"
                "current Generationと一致しません"
            )
        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "scene_card targetのseriesがworkspaceと"
                "一致しません"
            )

        scene_id = (
            f"scene-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )
        if state["active_scene_id"] != scene_id:
            raise ContractError(
                "scene_cardのactive_scene_idが実行対象と"
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
        volume_plan = read_json(
            self.workspace_root
            / "design/volume-plans"
            / f"v{volume_number:02d}-v0001"
            / "volume-plan.json"
        )
        chapter_plan = read_json(
            self.workspace_root
            / "design/chapter-plans"
            / (
                f"v{volume_number:02d}"
                f"-c{chapter_number:03d}-v0001"
            )
            / "chapter-plan.json"
        )
        scene_plan = read_json(
            self.workspace_root
            / "design/scene-plans"
            / (
                f"v{volume_number:02d}"
                f"-c{chapter_number:03d}"
                f"-s{scene_number:03d}-v0001"
            )
            / "scene-plan.json"
        )

        expected_targets = {
            "series_plan_id": series_plan["series_plan_id"],
            "volume_plan_id": volume_plan["volume_plan_id"],
            "chapter_plan_id": chapter_plan["chapter_plan_id"],
            "scene_plan_id": scene_plan["scene_plan_id"],
        }
        for field, expected in expected_targets.items():
            if target.get(field) != expected:
                raise ContractError(
                    f"scene_card targetの{field}が"
                    "採用済みPlanと一致しません"
                )

        if (
            scene_plan.get("volume_number") != volume_number
            or scene_plan.get("chapter_number")
            != chapter_number
            or scene_plan.get("scene_number") != scene_number
        ):
            raise ContractError(
                "scene_card targetの対象座標が"
                "Scene Planと一致しません"
            )
        if scene_plan.get("basis_generation_id") != generation_id:
            raise ContractError(
                "Scene Planのbasis_generation_idが"
                "current Generationと一致しません"
            )

        current_generation = self._read_generation(
            generation_id
        )
        self._validate_current_generation(
            current_generation,
            generation_id,
            initial_design,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_scene_card_v1(
                candidate,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                chapter_plan,
                scene_plan,
                current_generation,
                volume_number,
                chapter_number,
                scene_number,
                generation_id,
            )

        timestamp = updated_at or utc_now()
        context = self._build_context(
            brief,
            initial_design,
            volume_plan,
            chapter_plan,
            scene_plan,
            current_generation,
            scene_id,
        )

        return self.runner.run(
            model,
            context=context,
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                chapter_plan,
                scene_plan,
                current_generation,
                volume_number,
                chapter_number,
                scene_number,
                generation_id,
                timestamp,
            ),
            next_target={
                "series": state["workspace_id"],
                "series_plan_id": series_plan[
                    "series_plan_id"
                ],
                "volume_plan_id": volume_plan[
                    "volume_plan_id"
                ],
                "chapter_plan_id": chapter_plan[
                    "chapter_plan_id"
                ],
                "scene_plan_id": scene_plan[
                    "scene_plan_id"
                ],
                "scene_id": scene_id,
                "scene_card_version": 1,
                "volume_number": volume_number,
                "chapter_number": chapter_number,
                "scene_number": scene_number,
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

        if (
            generation["commit.json"].get("commit_type")
            == "initial_design"
        ):
            validate_initial_generation(
                generation,
                initial_design,
            )

    @staticmethod
    def _build_context(
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        volume_plan: dict[str, Any],
        chapter_plan: dict[str, Any],
        scene_plan: dict[str, Any],
        generation: dict[str, Any],
        scene_id: str,
    ) -> dict[str, Any]:
        participants = set(scene_plan["participant_ids"])
        location_id = scene_plan["location_id"]
        state = generation["state.json"]

        def references_participant(record: object) -> bool:
            if not isinstance(record, dict):
                return False
            return any(
                value in participants
                for value in record.values()
                if isinstance(value, str)
            )

        character_designs = [
            deepcopy(record)
            for record in initial_design["characters"]
            if record["character_id"] in participants
        ]
        location_designs = [
            deepcopy(record)
            for record in initial_design["locations"]
            if record["location_id"] == location_id
        ]
        relationship_designs = [
            deepcopy(record)
            for record in initial_design["relationships"]
            if references_participant(record)
        ]

        current_state = {
            "generation_id": generation["state.json"][
                "generation_id"
            ],
            "characters": {
                identifier: deepcopy(value)
                for identifier, value
                in state["characters"].items()
                if identifier in participants
            },
            "relationships": {
                identifier: deepcopy(value)
                for identifier, value
                in state["relationships"].items()
                if any(
                    record.get("relationship_id")
                    == identifier
                    for record in relationship_designs
                )
            },
            "threads": deepcopy(state["threads"]),
            "timeline": deepcopy(state["timeline"]),
            "inventory": {
                identifier: deepcopy(value)
                for identifier, value
                in state["inventory"].items()
                if (
                    value.get("holder_character_id")
                    in participants
                    or value.get("owner_character_id")
                    in participants
                    or value.get("location_id") == location_id
                )
            },
            "commitments": {
                identifier: deepcopy(value)
                for identifier, value
                in state["commitments"].items()
                if references_participant(value)
            },
        }

        return {
            "scene_id": scene_id,
            "brief_constraints": {
                field: deepcopy(brief.get(field))
                for field in (
                    "genre",
                    "tone",
                    "audience",
                    "must_include",
                    "must_avoid",
                )
                if field in brief
            },
            "volume_plan": deepcopy(volume_plan),
            "chapter_plan": deepcopy(chapter_plan),
            "scene_plan": deepcopy(scene_plan),
            "relevant_design": {
                "characters": character_designs,
                "relationships": relationship_designs,
                "locations": location_designs,
                "knowledge_facts": deepcopy(
                    initial_design["knowledge_facts"]
                ),
                "threads": deepcopy(
                    initial_design["threads"]
                ),
                "world_rules": deepcopy(
                    initial_design["world_rules"]
                ),
            },
            "current_state": current_state,
        }

    def _adopt(
        self,
        candidate: dict[str, Any],
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        chapter_plan: dict[str, Any],
        scene_plan: dict[str, Any],
        current_generation: dict[str, Any],
        volume_number: int,
        chapter_number: int,
        scene_number: int,
        basis_generation_id: str,
        created_at: str,
    ) -> None:
        """Review済みCardをactive Scene stagingへ保存する。"""
        ContractValidator._validate_scene_card_v1(
            candidate,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            basis_generation_id,
        )

        scene_id = (
            f"scene-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )
        adopted = {
            "schema_version": 1,
            "scene_id": scene_id,
            "version": 1,
            "basis_generation_id": basis_generation_id,
            "scene_plan_id": scene_plan["scene_plan_id"],
            **deepcopy(candidate),
            "created_at": created_at,
        }

        ContractValidator._validate_scene_card_v1(
            adopted,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            basis_generation_id,
            adopted=True,
        )

        staging_root = (
            self.workspace_root
            / "runtime/staging"
            / f"scene-{scene_id}"
        )
        staging_root.mkdir(parents=True, exist_ok=True)
        path = staging_root / "scene-card.json"

        if path.exists():
            existing = read_json(path)
            if existing != adopted:
                raise ContractError(
                    "採用済みScene Cardを上書きできません"
                )
            return

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".scene-card-",
            suffix=".json.tmp",
            dir=staging_root,
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
            ContractValidator._validate_scene_card_v1(
                written,
                brief,
                initial_design,
                series_plan,
                volume_plan,
                chapter_plan,
                scene_plan,
                current_generation,
                volume_number,
                chapter_number,
                scene_number,
                basis_generation_id,
                adopted=True,
            )
            os.replace(temporary, path)
            fsync_directory(staging_root)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
