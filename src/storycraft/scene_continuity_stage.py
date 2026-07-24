"""Storycraft Version 1 scene_continuity Stage実行。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from jsonschema import Draft202012Validator

from .initial_generation import validate_initial_generation
from .prompt_template import get_template_loader
from .reviewed_candidate_stage import (
    ReviewedCandidateSpec,
    ReviewedCandidateStageRunner,
    fsync_directory,
    read_json,
    reserve_identifier,
    utc_now,
)
from .scene_prose_stage import SceneProseStageService
from .series_contracts import (
    ContractError,
    ContractValidator,
    StoryModel,
)
from .workspace import validate_workspace_layout


_SPEC = ReviewedCandidateSpec(
    stage="scene_continuity",
    artifact_type="scene_continuity",
    review_category="scene_continuity_accuracy",
    next_stage="scene_commit",
    model_stage="scene_continuity_v1",
)


class SceneContinuityStageService:
    """凍結本文からEvidence付きContinuity Updateを確定する。"""

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

        if state["current_stage"] != "scene_continuity":
            raise ContractError(
                "現在のrun-stateはscene_continuityではありません"
            )
        if state["status"] not in {"initializing", "running"}:
            raise ContractError(
                "scene_continuityを実行できるrun statusではありません"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "未処理のactive_candidateがあります"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるためscene_continuityを"
                "開始できません"
            )

        volume_number = self._positive_number(
            target.get("volume_number"),
            "Volume",
        )
        chapter_number = self._positive_number(
            target.get("chapter_number"),
            "Chapter",
        )
        scene_number = self._positive_number(
            target.get("scene_number"),
            "Scene",
        )

        generation_id = state["current_generation_id"]
        if not isinstance(generation_id, str):
            raise ContractError(
                "scene_continuityにはcurrent Generationが必要です"
            )
        if target.get("basis_generation_id") != generation_id:
            raise ContractError(
                "scene_continuity targetのbasis_generation_idが"
                "current Generationと一致しません"
            )
        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "scene_continuity targetのseriesがworkspaceと"
                "一致しません"
            )
        if target.get("prose_version") != 1:
            raise ContractError(
                "scene_continuityにはprose_version 1が必要です"
            )

        scene_id = (
            f"scene-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )
        if target.get("scene_id") != scene_id:
            raise ContractError(
                "scene_continuity targetのscene_idが対象座標と"
                "一致しません"
            )
        if state["active_scene_id"] != scene_id:
            raise ContractError(
                "scene_continuityのactive_scene_idが"
                "実行対象と一致しません"
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

        staging_root = (
            self.workspace_root
            / "runtime/staging"
            / f"scene-{scene_id}"
        )
        scene_card = read_json(staging_root / "scene-card.json")
        prose_path = staging_root / "prose.md"
        if not prose_path.is_file():
            raise ContractError(
                "scene_continuityには凍結済みprose.mdが必要です"
            )
        prose = prose_path.read_text(encoding="utf-8")
        SceneProseStageService._validate_prose_text(prose)

        expected_targets = {
            "series_plan_id": series_plan["series_plan_id"],
            "volume_plan_id": volume_plan["volume_plan_id"],
            "chapter_plan_id": chapter_plan["chapter_plan_id"],
            "scene_plan_id": scene_plan["scene_plan_id"],
            "scene_card_version": scene_card["version"],
        }
        for field, expected in expected_targets.items():
            if target.get(field) != expected:
                raise ContractError(
                    f"scene_continuity targetの{field}が"
                    "採用済み成果物と一致しません"
                )

        current_generation = self._read_generation(generation_id)
        self._validate_current_generation(
            current_generation,
            generation_id,
            initial_design,
        )
        ContractValidator._validate_scene_card_v1(
            scene_card,
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
            adopted=True,
        )

        context = self._build_context(
            scene_id,
            generation_id,
            prose,
            scene_card,
            current_generation,
        )
        timestamp = updated_at or utc_now()
        result_generation_id = reserve_identifier(
            self.workspace_root,
            "next_generation",
            "gen",
            timestamp,
        )

        validator = lambda candidate: self._validate_candidate(
            candidate,
            prose=prose,
            scene_card=scene_card,
            current_generation=current_generation,
            initial_design=initial_design,
            scene_id=scene_id,
        )

        return self.runner.run(
            model,
            context=context,
            validator=validator,
            adopter=lambda candidate: self._adopt(
                candidate,
                staging_root=staging_root,
                prose=prose,
                scene_card=scene_card,
                current_generation=current_generation,
                initial_design=initial_design,
                scene_id=scene_id,
                basis_generation_id=generation_id,
                result_generation_id=result_generation_id,
                prose_version=target["prose_version"],
                created_at=timestamp,
            ),
            next_target={
                **deepcopy(target),
                "continuity_version": 1,
                "result_generation_id": result_generation_id,
            },
            updated_at=timestamp,
        )

    @staticmethod
    def _positive_number(value: object, label: str) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ContractError(
                f"scene_continuityには対象{label}番号が必要です"
            )
        return value

    def _read_generation(
        self,
        generation_id: str,
    ) -> dict[str, Any]:
        root = self.workspace_root / "generations" / generation_id
        if not root.is_dir():
            raise ContractError(
                "current Generation directoryが存在しません"
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
                    f"current Generation fileが不正です: {name}"
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
        scene_id: str,
        generation_id: str,
        prose: str,
        scene_card: dict[str, Any],
        generation: dict[str, Any],
    ) -> dict[str, Any]:
        state = generation["state.json"]
        relevant_state: list[dict[str, Any]] = []
        target_ids: set[str] = set()

        for allowed in scene_card["allowed_updates"]:
            target_type = allowed["target_type"]
            target_id = allowed["target_id"]
            target_ids.add(target_id)
            record = SceneContinuityStageService._target_record(
                state,
                target_type,
                target_id,
            )
            relevant_state.append({
                "target_type": target_type,
                "target_id": target_id,
                "allowed_fields": deepcopy(
                    allowed["allowed_fields"]
                ),
                "current_value": {
                    field: deepcopy(record[field])
                    for field in allowed["allowed_fields"]
                },
            })

        related_subjects = (
            target_ids
            | set(scene_card["participant_ids"])
            | {scene_card["location_id"]}
            | set(scene_card["allowed_revelations"])
        )
        related_canon = [
            {
                "subject_type": record["subject_type"],
                "subject_id": record["subject_id"],
                "predicate": record["predicate"],
                "value": deepcopy(record["value"]),
                "visibility": record["visibility"],
            }
            for record in generation["canon.json"]["records"]
            if (
                record["subject_id"] in related_subjects
                and (
                    record["visibility"] == "reader_visible"
                    or record["subject_id"]
                    in scene_card["allowed_revelations"]
                )
            )
        ]

        return {
            "scene_id": scene_id,
            "basis_generation_id": generation_id,
            "prose_version": 1,
            "frozen_prose": prose.strip(),
            "allowed_updates": relevant_state,
            "related_canon": related_canon,
        }

    @staticmethod
    def _target_record(
        state: dict[str, Any],
        target_type: str,
        target_id: str,
    ) -> dict[str, Any]:
        if target_type == "timeline_state":
            if target_id != "timeline":
                raise ContractError(
                    "timeline_stateのtarget_idはtimelineが必要です"
                )
            return state["timeline"]

        sources = {
            "character_state": state["characters"],
            "relationship_state": state["relationships"],
            "thread_state": state["threads"],
            "inventory_state": state["inventory"],
            "commitment_state": state["commitments"],
        }
        source = sources.get(target_type)
        if source is None or target_id not in source:
            raise ContractError(
                "Continuityが未知のState targetを参照しています"
            )
        record = source[target_id]
        if not isinstance(record, dict):
            raise ContractError(
                "Continuity targetのcurrent Stateが不正です"
            )
        return record

    @classmethod
    def _validate_candidate(
        cls,
        value: object,
        *,
        prose: str,
        scene_card: dict[str, Any],
        current_generation: dict[str, Any],
        initial_design: dict[str, Any],
        scene_id: str,
    ) -> None:
        if not isinstance(value, dict):
            raise ContractError(
                "Continuity CandidateはJSON objectが必要です"
            )

        schema = get_template_loader().load_schema_object(
            "generate",
            "scene_continuity_v1",
        )
        errors = sorted(
            Draft202012Validator(schema).iter_errors(value),
            key=lambda error: (
                list(error.absolute_path),
                error.message,
            ),
        )
        if errors:
            error = errors[0]
            location = ".".join(
                str(part) for part in error.absolute_path
            ) or "<root>"
            raise ContractError(
                "Continuity契約違反: "
                f"{location}: {error.message}"
            )

        allowed = {
            (
                record["target_type"],
                record["target_id"],
                field,
            )
            for record in scene_card["allowed_updates"]
            for field in record["allowed_fields"]
        }
        state = current_generation["state.json"]
        evidence = value["evidence"]
        used_evidence: set[int] = set()
        seen_operations: set[tuple[str, str, str]] = set()

        for index, operation in enumerate(value["operations"]):
            key = (
                operation["target_type"],
                operation["target_id"],
                operation["field"],
            )
            if key not in allowed:
                raise ContractError(
                    "Continuity operationがallowed_updates外です: "
                    f"operations[{index}]"
                )
            if key in seen_operations:
                raise ContractError(
                    "同じState fieldを複数回更新できません: "
                    f"operations[{index}]"
                )
            seen_operations.add(key)

            record = cls._target_record(
                state,
                operation["target_type"],
                operation["target_id"],
            )
            field = operation["field"]
            current_value = record[field]
            if operation["old_value"] != current_value:
                raise ContractError(
                    "Continuity old_valueがcurrent Generationと"
                    f"一致しません: operations[{index}].old_value"
                )
            if operation["new_value"] == current_value:
                raise ContractError(
                    "Continuityにno-op更新を含められません: "
                    f"operations[{index}].new_value"
                )

            cls._validate_new_value(
                target_type=operation["target_type"],
                field=field,
                old_value=current_value,
                new_value=operation["new_value"],
                scene_id=scene_id,
                initial_design=initial_design,
            )

            for evidence_index in operation["evidence_indices"]:
                if evidence_index >= len(evidence):
                    raise ContractError(
                        "Continuity operationが存在しないEvidenceを"
                        f"参照しています: operations[{index}]"
                    )
                record_evidence = evidence[evidence_index]
                if (
                    record_evidence["target_type"]
                    != operation["target_type"]
                    or record_evidence["target_id"]
                    != operation["target_id"]
                ):
                    raise ContractError(
                        "Continuity Evidenceのtargetがoperationと"
                        f"一致しません: operations[{index}]"
                    )
                used_evidence.add(evidence_index)

        for index, record in enumerate(evidence):
            cls._validate_evidence(
                record,
                prose,
                index,
            )

        if used_evidence != set(range(len(evidence))):
            raise ContractError(
                "未使用のContinuity Evidenceがあります"
            )

    @staticmethod
    def _validate_new_value(
        *,
        target_type: str,
        field: str,
        old_value: Any,
        new_value: Any,
        scene_id: str,
        initial_design: dict[str, Any],
    ) -> None:
        knowledge_ids = {
            record["knowledge_id"]
            for record in initial_design["knowledge_facts"]
        }
        location_ids = {
            record["location_id"]
            for record in initial_design["locations"]
        }

        if target_type == "character_state":
            if field == "current_location_id":
                if new_value not in location_ids:
                    raise ContractError(
                        "Character current_location_idが未知です"
                    )
                return
            if field == "knowledge_states":
                if not isinstance(new_value, dict):
                    raise ContractError(
                        "knowledge_statesはobjectが必要です"
                    )
                if not set(new_value).issubset(knowledge_ids):
                    raise ContractError(
                        "knowledge_statesが未知Knowledgeを"
                        "参照しています"
                    )
                states = {
                    "unknown",
                    "suspects",
                    "believes",
                    "knows",
                    "disbelieves",
                }
                if any(
                    state not in states
                    for state in new_value.values()
                ):
                    raise ContractError(
                        "knowledge_statesの認識状態が不正です"
                    )
                return
            if field in {
                "goals",
                "active_constraints",
                "inventory_item_ids",
            }:
                SceneContinuityStageService._string_list(
                    new_value,
                    f"character_state.{field}",
                )
                return
            if field in {
                "physical_condition",
                "emotional_condition",
                "availability",
                "alive_status",
            }:
                SceneContinuityStageService._nonempty_string(
                    new_value,
                    f"character_state.{field}",
                )
                return

        if target_type == "relationship_state":
            if field in {
                "trust",
                "affection",
                "fear",
                "hostility",
            }:
                if (
                    not isinstance(new_value, int)
                    or isinstance(new_value, bool)
                    or not 0 <= new_value <= 10
                ):
                    raise ContractError(
                        f"relationship_state.{field}は"
                        "0から10の整数が必要です"
                    )
                return
            if field == "last_change_scene_id":
                if new_value != scene_id:
                    raise ContractError(
                        "last_change_scene_idはcurrent Sceneが必要です"
                    )
                return
            if field in {"obligations", "shared_secrets"}:
                SceneContinuityStageService._string_list(
                    new_value,
                    f"relationship_state.{field}",
                )
                return
            if field in {
                "status",
                "public_status",
                "private_status",
            }:
                SceneContinuityStageService._nonempty_string(
                    new_value,
                    f"relationship_state.{field}",
                )
                return

        if target_type == "thread_state":
            if field == "status":
                if new_value not in {
                    "planned",
                    "open",
                    "progressing",
                    "in_progress",
                    "resolved",
                }:
                    raise ContractError(
                        "thread_state.statusが不正です"
                    )
                return
            if field in {
                "latest_development_scene_id",
                "resolution_scene_id",
            }:
                if new_value not in {None, scene_id}:
                    raise ContractError(
                        f"thread_state.{field}はnullまたは"
                        "current Sceneが必要です"
                    )
                return
            if field == "completion_notes":
                if new_value is not None:
                    SceneContinuityStageService._nonempty_string(
                        new_value,
                        "thread_state.completion_notes",
                    )
                return
            if field == "open_questions":
                SceneContinuityStageService._string_list(
                    new_value,
                    "thread_state.open_questions",
                )
                return
            if field == "progress_summary":
                SceneContinuityStageService._nonempty_string(
                    new_value,
                    "thread_state.progress_summary",
                )
                return

        if target_type == "timeline_state":
            if field in {
                "current_story_time",
                "calendar_system",
                "elapsed_time",
            }:
                SceneContinuityStageService._nonempty_string(
                    new_value,
                    f"timeline_state.{field}",
                )
                return
            if field in {
                "known_deadlines",
                "event_order",
                "time_constraints",
            }:
                SceneContinuityStageService._string_list(
                    new_value,
                    f"timeline_state.{field}",
                )
                if field == "event_order":
                    if (
                        not isinstance(old_value, list)
                        or new_value[: len(old_value)] != old_value
                        or new_value[len(old_value):] != [scene_id]
                    ):
                        raise ContractError(
                            "timeline.event_orderはcurrent Sceneを"
                            "末尾へ一度だけ追加しなければなりません"
                        )
                return

        SceneContinuityStageService._same_json_type(
            old_value,
            new_value,
            f"{target_type}.{field}",
        )

    @staticmethod
    def _same_json_type(
        old_value: Any,
        new_value: Any,
        field: str,
    ) -> None:
        if old_value is None:
            if new_value is None:
                raise ContractError(
                    f"{field}は変更後値が必要です"
                )
            return
        if isinstance(old_value, bool):
            valid = isinstance(new_value, bool)
        elif isinstance(old_value, int):
            valid = (
                isinstance(new_value, int)
                and not isinstance(new_value, bool)
            )
        elif isinstance(old_value, float):
            valid = (
                isinstance(new_value, (int, float))
                and not isinstance(new_value, bool)
                and math.isfinite(float(new_value))
            )
        else:
            valid = type(new_value) is type(old_value)
        if not valid:
            raise ContractError(
                f"{field}のnew_value型がcurrent Stateと"
                "一致しません"
            )

    @staticmethod
    def _nonempty_string(value: Any, field: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ContractError(
                f"{field}は空でない文字列が必要です"
            )

    @staticmethod
    def _string_list(value: Any, field: str) -> None:
        if (
            not isinstance(value, list)
            or any(
                not isinstance(item, str) or not item.strip()
                for item in value
            )
            or len(value) != len(set(value))
        ):
            raise ContractError(
                f"{field}は重複のない文字列配列が必要です"
            )

    @staticmethod
    def _validate_evidence(
        evidence: dict[str, Any],
        prose: str,
        index: int,
    ) -> None:
        quote = evidence["quote"]
        starts = [
            match.start()
            for match in re.finditer(
                re.escape(quote),
                prose,
            )
        ]
        occurrence = evidence["occurrence"]
        if occurrence > len(starts):
            raise ContractError(
                "Evidence quoteまたはoccurrenceが本文と"
                f"一致しません: evidence[{index}]"
            )

        start = starts[occurrence - 1]
        end = start + len(quote)
        before = evidence["context_before"]
        after = evidence["context_after"]

        if (
            before
            and before not in prose[max(0, start - 1200):start]
        ):
            raise ContractError(
                "Evidence context_beforeが引用付近にありません: "
                f"evidence[{index}]"
            )
        if (
            after
            and after not in prose[end:end + 1200]
        ):
            raise ContractError(
                "Evidence context_afterが引用付近にありません: "
                f"evidence[{index}]"
            )

    @classmethod
    def _validate_adopted(
        cls,
        value: object,
        *,
        prose: str,
        scene_card: dict[str, Any],
        current_generation: dict[str, Any],
        initial_design: dict[str, Any],
        scene_id: str,
        basis_generation_id: str,
    ) -> None:
        if not isinstance(value, dict):
            raise ContractError(
                "採用済みContinuityはobjectが必要です"
            )

        expected_fields = {
            "schema_version",
            "continuity_id",
            "scene_id",
            "version",
            "basis_generation_id",
            "prose_version",
            "result_generation_id",
            "summary",
            "operations",
            "evidence",
            "unchanged_assertions",
            "created_at",
        }
        if set(value) != expected_fields:
            raise ContractError(
                "採用済みContinuityのfield構成が不正です"
            )
        if value["schema_version"] != 1:
            raise ContractError(
                "Continuity.schema_versionは1が必要です"
            )
        if value["continuity_id"] != (
            f"continuity-{scene_id}-v0001"
        ):
            raise ContractError(
                "Continuity.continuity_idが不正です"
            )
        if value["scene_id"] != scene_id:
            raise ContractError(
                "Continuity.scene_idが不正です"
            )
        if value["version"] != 1:
            raise ContractError(
                "Continuity.versionは1が必要です"
            )
        if value["basis_generation_id"] != basis_generation_id:
            raise ContractError(
                "Continuity basis Generationが不正です"
            )
        if value["prose_version"] != 1:
            raise ContractError(
                "Continuity prose_versionが不正です"
            )
        if not re.fullmatch(
            r"gen-\d{6}",
            value["result_generation_id"],
        ):
            raise ContractError(
                "Continuity result_generation_idが不正です"
            )
        cls._timestamp(value["created_at"])

        evidence_ids: list[str] = []
        candidate_evidence = []
        for record in value["evidence"]:
            if not isinstance(record, dict):
                raise ContractError(
                    "採用済みEvidenceがobjectではありません"
                )
            evidence_id = record.get("evidence_id")
            if not re.fullmatch(
                r"evidence-\d{6}",
                str(evidence_id),
            ):
                raise ContractError(
                    "採用済みEvidence IDが不正です"
                )
            evidence_ids.append(evidence_id)
            candidate_evidence.append({
                key: deepcopy(record[key])
                for key in (
                    "quote",
                    "occurrence",
                    "context_before",
                    "context_after",
                    "target_type",
                    "target_id",
                    "change_summary",
                )
            })
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ContractError(
                "採用済みEvidence IDが重複しています"
            )
        evidence_index = {
            identifier: index
            for index, identifier in enumerate(evidence_ids)
        }

        operation_ids: list[str] = []
        candidate_operations = []
        for record in value["operations"]:
            if not isinstance(record, dict):
                raise ContractError(
                    "採用済みOperationがobjectではありません"
                )
            operation_id = record.get("operation_id")
            if not re.fullmatch(
                r"update-\d{6}",
                str(operation_id),
            ):
                raise ContractError(
                    "採用済みOperation IDが不正です"
                )
            operation_ids.append(operation_id)
            evidence_refs = record.get("evidence_ids")
            if (
                not isinstance(evidence_refs, list)
                or not evidence_refs
                or any(
                    identifier not in evidence_index
                    for identifier in evidence_refs
                )
            ):
                raise ContractError(
                    "採用済みOperationのEvidence参照が不正です"
                )
            candidate_operations.append({
                key: deepcopy(record[key])
                for key in (
                    "target_type",
                    "target_id",
                    "field",
                    "operation",
                    "old_value",
                    "new_value",
                    "reason",
                )
            } | {
                "evidence_indices": [
                    evidence_index[identifier]
                    for identifier in evidence_refs
                ],
            })
        if len(operation_ids) != len(set(operation_ids)):
            raise ContractError(
                "採用済みOperation IDが重複しています"
            )

        cls._validate_candidate(
            {
                "summary": value["summary"],
                "operations": candidate_operations,
                "evidence": candidate_evidence,
                "unchanged_assertions": deepcopy(
                    value["unchanged_assertions"]
                ),
            },
            prose=prose,
            scene_card=scene_card,
            current_generation=current_generation,
            initial_design=initial_design,
            scene_id=scene_id,
        )

    @staticmethod
    def _timestamp(value: object) -> None:
        if not isinstance(value, str):
            raise ContractError(
                "Continuity.created_atは文字列が必要です"
            )
        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ContractError(
                "Continuity.created_atが不正です"
            ) from exc
        if parsed.tzinfo is None:
            raise ContractError(
                "Continuity.created_atにはtimezoneが必要です"
            )

    def _adopt(
        self,
        candidate: dict[str, Any],
        *,
        staging_root: Path,
        prose: str,
        scene_card: dict[str, Any],
        current_generation: dict[str, Any],
        initial_design: dict[str, Any],
        scene_id: str,
        basis_generation_id: str,
        result_generation_id: str,
        prose_version: int,
        created_at: str,
    ) -> None:
        self._validate_candidate(
            candidate,
            prose=prose,
            scene_card=scene_card,
            current_generation=current_generation,
            initial_design=initial_design,
            scene_id=scene_id,
        )

        path = staging_root / "continuity.json"
        if path.exists():
            raise ContractError(
                "採用済みContinuityを上書きできません"
            )

        evidence_ids = [
            reserve_identifier(
                self.workspace_root,
                "next_evidence",
                "evidence",
                created_at,
            )
            for _ in candidate["evidence"]
        ]
        operations = []
        for record in candidate["operations"]:
            operations.append({
                "operation_id": reserve_identifier(
                    self.workspace_root,
                    "next_update",
                    "update",
                    created_at,
                ),
                **{
                    key: deepcopy(record[key])
                    for key in (
                        "target_type",
                        "target_id",
                        "field",
                        "operation",
                        "old_value",
                        "new_value",
                        "reason",
                    )
                },
                "evidence_ids": [
                    evidence_ids[index]
                    for index in record["evidence_indices"]
                ],
            })

        evidence = [
            {
                "evidence_id": evidence_ids[index],
                "scene_id": scene_id,
                **deepcopy(record),
            }
            for index, record in enumerate(candidate["evidence"])
        ]
        adopted = {
            "schema_version": 1,
            "continuity_id": (
                f"continuity-{scene_id}-v0001"
            ),
            "scene_id": scene_id,
            "version": 1,
            "basis_generation_id": basis_generation_id,
            "prose_version": prose_version,
            "result_generation_id": result_generation_id,
            "summary": candidate["summary"],
            "operations": operations,
            "evidence": evidence,
            "unchanged_assertions": deepcopy(
                candidate["unchanged_assertions"]
            ),
            "created_at": created_at,
        }
        self._validate_adopted(
            adopted,
            prose=prose,
            scene_card=scene_card,
            current_generation=current_generation,
            initial_design=initial_design,
            scene_id=scene_id,
            basis_generation_id=basis_generation_id,
        )
        self._write_json_atomic(path, adopted)

    @staticmethod
    def _write_json_atomic(
        path: Path,
        value: dict[str, Any],
    ) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}-",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                json.dump(
                    value,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            read_back = json.loads(
                temporary.read_text(encoding="utf-8")
            )
            if read_back != value:
                raise ContractError(
                    "Continuity書込み後の検証に失敗しました"
                )
            os.replace(temporary, path)
            fsync_directory(path.parent)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
