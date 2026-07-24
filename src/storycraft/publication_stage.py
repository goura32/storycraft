"""Storycraft Version 1 publication Stage実行。"""
from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import shutil
from typing import Any

from .immutable_directory import (
    finalize_immutable_directory,
)
from .publication_builder import (
    build_publication_files,
    validate_publication_directory,
)
from .reviewed_candidate_stage import (
    fsync_directory,
    read_json,
    reserve_identifier,
    utc_now,
    write_json_new,
)
from .run_state import RunStateStore, validate_run_state
from .series_contracts import ContractError
from .stages import Stage
from .workspace import validate_workspace_layout


class PublicationStageService:
    """採用済みScene本文からPublicationを決定的に確定する。"""

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

        if (
            state["current_stage"]
            != Stage.PUBLICATION.value
        ):
            raise ContractError(
                "現在のrun-stateはpublicationではありません"
            )
        if state["status"] not in {
            "initializing",
            "running",
        }:
            raise ContractError(
                "publicationを実行できる"
                "run statusではありません"
            )
        if state["current_publication_id"] is not None:
            raise ContractError(
                "Publicationは既に確定しています"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "publication開始時に"
                "active_candidateを残せません"
            )
        if state["active_scene_id"] is not None:
            raise ContractError(
                "publication開始時に"
                "active_scene_idを残せません"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitがあるため"
                "Publication Stageを再実行できません"
            )

        timestamp = updated_at or utc_now()
        inputs = self._prepare_inputs(state)

        publication_id = reserve_identifier(
            self.workspace_root,
            "next_publication",
            "pub",
            timestamp,
        )

        files = build_publication_files(
            publication_id=publication_id,
            title=inputs["title"],
            language=inputs["language"],
            basis_generation_id=inputs[
                "basis_generation_id"
            ],
            completion=inputs["completion"],
            volumes=inputs["volumes"],
            created_at=timestamp,
        )

        staging = (
            self.workspace_root
            / "runtime/staging"
            / f"publication-{publication_id}"
        )
        final = (
            self.workspace_root
            / "publications"
            / publication_id
        )

        if staging.exists() or staging.is_symlink():
            raise ContractError(
                "Publication stagingが既に存在します"
            )
        if final.exists() or final.is_symlink():
            raise ContractError(
                "確定済みPublicationを上書きできません"
            )

        staging.mkdir()

        try:
            self._write_publication_files(
                staging,
                files,
            )
            validate_publication_directory(
                staging,
                expected_files=files,
            )
        except Exception:
            if staging.exists() and not staging.is_symlink():
                shutil.rmtree(staging)
            raise

        prepared = deepcopy(state)
        prepared["status"] = "running"
        prepared["current_target"] = {
            **deepcopy(state["current_target"]),
            "publication_id": publication_id,
        }
        prepared["pending_commit"] = {
            "kind": Stage.PUBLICATION.value,
            "target_id": publication_id,
            "phase": "prepared",
        }
        prepared["stop_reason"] = None
        prepared["last_error"] = None
        prepared["updated_at"] = timestamp
        validate_run_state(prepared)
        self.state_store.save(prepared)

        finalize_immutable_directory(
            staging=staging,
            final=final,
            validator=lambda directory: (
                validate_publication_directory(
                    directory,
                    expected_files=files,
                )
            ),
        )

        finalized = deepcopy(prepared)
        finalized["pending_commit"] = {
            "kind": Stage.PUBLICATION.value,
            "target_id": publication_id,
            "phase": "publication_finalized",
        }
        validate_run_state(finalized)
        self.state_store.save(finalized)

        completed = deepcopy(finalized)
        completed["status"] = "completed"
        completed["current_publication_id"] = (
            publication_id
        )
        completed["active_candidate"] = None
        completed["active_scene_id"] = None
        completed["pending_commit"] = None
        completed["stop_reason"] = None
        completed["last_error"] = None
        completed["updated_at"] = timestamp
        validate_run_state(completed)
        self.state_store.save(completed)

        validate_workspace_layout(self.workspace_root)
        return completed

    def _prepare_inputs(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Publication入力をPlan順でcode-only収集する。"""
        target = state["current_target"]

        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "publication targetのseriesが"
                "workspaceと一致しません"
            )

        generation_id = state["current_generation_id"]
        if not isinstance(generation_id, str):
            raise ContractError(
                "publicationにはcurrent Generationが必要です"
            )
        if (
            target.get("basis_generation_id")
            != generation_id
        ):
            raise ContractError(
                "publication targetのbasis Generationが"
                "current Generationと一致しません"
            )

        completion_id = target.get("completion_id")
        if (
            not isinstance(completion_id, str)
            or not completion_id.startswith(
                "completion-"
            )
        ):
            raise ContractError(
                "publication targetのcompletion_idが不正です"
            )

        completion_path = (
            self.workspace_root
            / "completion"
            / completion_id
            / "result.json"
        )
        completion = read_json(completion_path)

        if (
            completion.get("completion_id")
            != completion_id
        ):
            raise ContractError(
                "Publication Completion IDが"
                "targetと一致しません"
            )
        if (
            completion.get("basis_generation_id")
            != generation_id
        ):
            raise ContractError(
                "Publication Completionのbasis Generationが"
                "current Generationと一致しません"
            )
        if completion.get("status") not in {
            "complete",
            "complete_with_issues",
        }:
            raise ContractError(
                "Publicationには公開可能Completionが必要です"
            )
        if (
            target.get("completion_status")
            != completion["status"]
        ):
            raise ContractError(
                "publication targetのcompletion_statusが"
                "Completion Resultと一致しません"
            )

        config = read_json(
            self.workspace_root / "runtime/config.json"
        )
        language = config.get("language")
        if not isinstance(language, str) or not language:
            raise ContractError(
                "Publication languageが不正です"
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

        if (
            target.get("series_plan_id")
            != series_plan.get("series_plan_id")
        ):
            raise ContractError(
                "publication targetのseries_plan_idが"
                "採用済みSeries Planと一致しません"
            )

        title = _resolve_series_title(
            brief,
            initial_design,
            series_plan,
        )
        volumes = self._load_volumes(series_plan)

        return {
            "title": title,
            "language": language,
            "basis_generation_id": generation_id,
            "completion": completion,
            "volumes": volumes,
        }

    def _load_volumes(
        self,
        series_plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        volume_count = _positive_integer(
            series_plan.get("volume_count"),
            "Series Plan.volume_count",
        )
        volumes: list[dict[str, Any]] = []

        for volume_number in range(
            1,
            volume_count + 1,
        ):
            volume_plan = read_json(
                self.workspace_root
                / "design/volume-plans"
                / f"v{volume_number:02d}-v0001"
                / "volume-plan.json"
            )

            if (
                volume_plan.get("volume_number")
                != volume_number
            ):
                raise ContractError(
                    "Publication Volume Plan番号が不正です"
                )

            volume_title = _required_text(
                volume_plan.get("title"),
                "Volume Plan.title",
            )
            chapter_numbers = _ordered_numbers(
                volume_plan.get("chapter_summaries"),
                field="chapter_number",
                label="Volume Plan Chapter",
            )
            chapters: list[dict[str, Any]] = []

            for chapter_number in chapter_numbers:
                chapter_plan = read_json(
                    self.workspace_root
                    / "design/chapter-plans"
                    / (
                        f"v{volume_number:02d}"
                        f"-c{chapter_number:03d}-v0001"
                    )
                    / "chapter-plan.json"
                )

                if (
                    chapter_plan.get("volume_number")
                    != volume_number
                    or chapter_plan.get(
                        "chapter_number"
                    )
                    != chapter_number
                    or chapter_plan.get(
                        "volume_plan_id"
                    )
                    != volume_plan.get(
                        "volume_plan_id"
                    )
                ):
                    raise ContractError(
                        "Publication Chapter Planが"
                        "Volume Planと一致しません"
                    )

                chapter_title = _required_text(
                    chapter_plan.get("title"),
                    "Chapter Plan.title",
                )
                scene_numbers = _ordered_numbers(
                    chapter_plan.get("scene_summaries"),
                    field="scene_number",
                    label="Chapter Plan Scene",
                )
                scenes: list[dict[str, Any]] = []

                for scene_number in scene_numbers:
                    scene_id = (
                        f"scene-v{volume_number:02d}"
                        f"-c{chapter_number:03d}"
                        f"-s{scene_number:03d}"
                    )
                    scene_root = (
                        self.workspace_root
                        / "scenes"
                        / scene_id
                    )

                    if (
                        scene_root.is_symlink()
                        or not scene_root.is_dir()
                    ):
                        raise ContractError(
                            "Publication対象Sceneが"
                            "確定されていません"
                        )

                    prose_path = scene_root / "prose.md"
                    try:
                        prose = prose_path.read_text(
                            encoding="utf-8"
                        )
                    except OSError as exc:
                        raise ContractError(
                            "Publication対象Scene本文を"
                            "読み込めません"
                        ) from exc

                    if not prose.strip():
                        raise ContractError(
                            "Publication対象Scene本文が空です"
                        )

                    commit = read_json(
                        scene_root / "commit.json"
                    )
                    if commit.get("scene_id") != scene_id:
                        raise ContractError(
                            "Publication Scene Commitが"
                            "Scene IDと一致しません"
                        )

                    scenes.append({
                        "scene_number": scene_number,
                        "prose": prose.strip(),
                    })

                chapters.append({
                    "chapter_number": chapter_number,
                    "title": chapter_title,
                    "scenes": scenes,
                })

            volumes.append({
                "volume_number": volume_number,
                "title": volume_title,
                "chapters": chapters,
            })

        return volumes

    @staticmethod
    def _write_publication_files(
        staging: Path,
        files: dict[str, dict[str, Any] | str],
    ) -> None:
        for name, value in files.items():
            path = staging / name

            if isinstance(value, dict):
                write_json_new(path, value)
                continue

            if not isinstance(value, str):
                raise ContractError(
                    "Publication file内容が不正です"
                )

            try:
                with path.open(
                    "x",
                    encoding="utf-8",
                ) as handle:
                    handle.write(value)
                    handle.flush()
                    os.fsync(handle.fileno())
            except OSError as exc:
                raise ContractError(
                    f"Publication本文を書き込めません: {name}"
                ) from exc

        fsync_directory(staging)


def _resolve_series_title(
    brief: dict[str, Any],
    initial_design: dict[str, Any],
    series_plan: dict[str, Any],
) -> str:
    concept = initial_design.get("concept")
    if not isinstance(concept, dict):
        concept = {}

    candidates = (
        series_plan.get("title"),
        series_plan.get("series_title"),
        concept.get("title"),
        concept.get("working_title"),
        concept.get("provisional_title"),
        initial_design.get("title"),
        brief.get("title"),
        brief.get("working_title"),
        brief.get("provisional_title"),
    )

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    raise ContractError(
        "Publicationのシリーズ題名を解決できません"
    )


def _ordered_numbers(
    records: object,
    *,
    field: str,
    label: str,
) -> list[int]:
    if not isinstance(records, list) or not records:
        raise ContractError(
            f"{label}一覧が必要です"
        )

    numbers: list[int] = []

    for record in records:
        if not isinstance(record, dict):
            raise ContractError(
                f"{label}はobjectが必要です"
            )
        numbers.append(
            _positive_integer(
                record.get(field),
                f"{label}.{field}",
            )
        )

    if numbers != list(range(1, len(numbers) + 1)):
        raise ContractError(
            f"{label}番号は1からの連番が必要です"
        )

    return numbers


def _positive_integer(
    value: object,
    label: str,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ContractError(
            f"{label}は1以上の整数が必要です"
        )
    return value


def _required_text(
    value: object,
    label: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(
            f"{label}は空でない文字列が必要です"
        )
    return value.strip()
