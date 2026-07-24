"""Storycraft Version 1 completion Stage実行。"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .immutable_directory import (
    finalize_immutable_directory,
)
from .reviewed_candidate_stage import (
    ReviewedCandidateSpec,
    ReviewedCandidateStageRunner,
    read_json,
    reserve_identifier,
    stop_state,
    utc_now,
    write_json_new,
)
from .run_state import validate_run_state
from .series_contracts import (
    ContractError,
    ContractValidator,
    StoryModel,
)
from .stage_transition import advance_run_state
from .stages import Stage
from .workspace import validate_workspace_layout


_SPEC = ReviewedCandidateSpec(
    stage=Stage.COMPLETION.value,
    artifact_type="completion",
    review_category="completion_quality",
    next_stage=Stage.PUBLICATION.value,
)

_SCENE_FILES = {
    "scene-card.json",
    "prose.md",
    "continuity.json",
    "commit.json",
}

_GENERATION_FILES = (
    "canon.json",
    "state.json",
    "evidence.json",
    "commit.json",
)

_PRECHECK_SUMMARY = {
    "all_volumes_complete": True,
    "all_planned_scenes_committed": True,
    "unfinished_scene_work": False,
}


class CompletionStageService:
    """シリーズ完結状態を評価しCompletion Resultを確定する。"""

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

        if (
            state["current_stage"]
            != Stage.COMPLETION.value
        ):
            raise ContractError(
                "現在のrun-stateはcompletionではありません"
            )
        if state["active_scene_id"] is not None:
            raise ContractError(
                "completionにはactive_scene_idを残せません"
            )

        inputs = self._prepare_inputs(state)
        initial_design = inputs["initial_design"]
        series_plan = inputs["series_plan"]
        handoffs = inputs["handoffs"]
        current_generation = inputs["current_generation"]
        completed_scene_ids = inputs[
            "completed_scene_ids"
        ]

        generation_id = state["current_generation_id"]
        assert isinstance(generation_id, str)

        timestamp = updated_at or utc_now()
        completion_id = reserve_identifier(
            self.workspace_root,
            "next_completion",
            "completion",
            timestamp,
        )

        def validate(candidate: object) -> None:
            ContractValidator._validate_completion(
                candidate,
                current_generation,
                initial_design,
                series_plan,
                handoffs,
                generation_id,
            )

        publication_target = {
            "series": state["workspace_id"],
            "series_plan_id": series_plan[
                "series_plan_id"
            ],
            "completion_id": completion_id,
            "basis_generation_id": generation_id,
        }

        def after_adoption(
            candidate: dict[str, Any],
            adopted_state: dict[str, Any],
            adopted_at: str,
        ) -> dict[str, Any]:
            return self._after_adoption(
                candidate,
                adopted_state,
                completion_id,
                series_plan,
                generation_id,
                adopted_at,
            )

        return self.runner.run(
            model,
            context={
                "initial_design": deepcopy(initial_design),
                "series_plan": deepcopy(series_plan),
                "handoffs": deepcopy(handoffs),
                "current_generation": deepcopy(
                    current_generation
                ),
                "completed_scene_ids": deepcopy(
                    completed_scene_ids
                ),
                "precheck_summary": deepcopy(
                    _PRECHECK_SUMMARY
                ),
            },
            validator=validate,
            adopter=lambda candidate: self._adopt(
                candidate,
                current_generation,
                initial_design,
                series_plan,
                handoffs,
                generation_id,
                completion_id,
                timestamp,
            ),
            next_stage=Stage.PUBLICATION.value,
            next_target=publication_target,
            after_adoption=after_adoption,
            updated_at=timestamp,
        )

    def _prepare_inputs(
        self,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Completion開始条件をcode-onlyで検証する。"""
        target = state["current_target"]

        generation_id = state["current_generation_id"]
        if not isinstance(generation_id, str):
            raise ContractError(
                "completionにはcurrent Generationが必要です"
            )
        if (
            target.get("basis_generation_id")
            != generation_id
        ):
            raise ContractError(
                "completion targetのbasis_generation_idが"
                "current Generationと一致しません"
            )
        if target.get("series") != state["workspace_id"]:
            raise ContractError(
                "completion targetのseriesが"
                "workspaceと一致しません"
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
                "completion targetのseries_plan_idが"
                "採用済みSeries Planと一致しません"
            )

        volume_count = _positive_integer(
            series_plan.get("volume_count"),
            "Series Plan.volume_count",
        )
        if target.get("volume_number") != volume_count:
            raise ContractError(
                "completion targetがSeries Planの"
                "最終Volumeを示していません"
            )

        final_handoff_id = (
            f"handoff-v{volume_count:02d}"
        )
        if (
            target.get("final_handoff_id")
            != final_handoff_id
        ):
            raise ContractError(
                "completion targetのfinal_handoff_idが"
                "最終Volumeと一致しません"
            )

        (
            handoffs,
            completed_scene_ids,
        ) = self._load_completed_series(
            series_plan,
            generation_id,
        )

        current_generation = self._read_generation(
            generation_id
        )
        self._validate_current_generation(
            current_generation,
            generation_id,
            completed_scene_ids,
        )

        return {
            "initial_design": initial_design,
            "series_plan": series_plan,
            "handoffs": handoffs,
            "current_generation": current_generation,
            "completed_scene_ids": completed_scene_ids,
            "precheck_summary": deepcopy(
                _PRECHECK_SUMMARY
            ),
        }

    def _load_completed_series(
        self,
        series_plan: dict[str, Any],
        final_generation_id: str,
    ) -> tuple[
        list[dict[str, Any]],
        list[str],
    ]:
        """全Plan、Scene、Handoffの完了状態を確認する。"""
        volume_count = _positive_integer(
            series_plan.get("volume_count"),
            "Series Plan.volume_count",
        )
        series_plan_id = _required_string(
            series_plan.get("series_plan_id"),
            "Series Plan.series_plan_id",
        )
        expected_parent_generation_id = (
            _required_string(
                series_plan.get("basis_generation_id"),
                "Series Plan.basis_generation_id",
            )
        )

        handoffs: list[dict[str, Any]] = []
        completed_scene_ids: list[str] = []
        expected_handoff_names: set[str] = set()
        expected_scene_ids: set[str] = set()

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
                or volume_plan.get("series_plan_id")
                != series_plan_id
            ):
                raise ContractError(
                    "CompletionのVolume Planが"
                    "Series Planと一致しません"
                )

            chapter_numbers = _ordered_numbers(
                volume_plan.get("chapter_summaries"),
                field="chapter_number",
                label="Volume Plan Chapter",
            )
            expected_chapter_ids: list[str] = []
            volume_scene_ids: list[str] = []

            for chapter_number in chapter_numbers:
                chapter_plan_id = (
                    f"chapter-plan-v{volume_number:02d}"
                    f"-c{chapter_number:03d}"
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

                if (
                    chapter_plan.get("chapter_plan_id")
                    != chapter_plan_id
                    or chapter_plan.get("volume_plan_id")
                    != volume_plan.get("volume_plan_id")
                    or chapter_plan.get("volume_number")
                    != volume_number
                    or chapter_plan.get("chapter_number")
                    != chapter_number
                ):
                    raise ContractError(
                        "CompletionのChapter Planが"
                        "Volume Planと一致しません"
                    )

                expected_chapter_ids.append(
                    f"chapter-v{volume_number:02d}"
                    f"-c{chapter_number:03d}"
                )

                scene_numbers = _ordered_numbers(
                    chapter_plan.get("scene_summaries"),
                    field="scene_number",
                    label="Chapter Plan Scene",
                )

                for scene_number in scene_numbers:
                    scene_id = (
                        f"scene-v{volume_number:02d}"
                        f"-c{chapter_number:03d}"
                        f"-s{scene_number:03d}"
                    )
                    scene_plan_id = (
                        f"scene-plan-v{volume_number:02d}"
                        f"-c{chapter_number:03d}"
                        f"-s{scene_number:03d}"
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
                    if (
                        scene_plan.get("scene_plan_id")
                        != scene_plan_id
                        or scene_plan.get("chapter_plan_id")
                        != chapter_plan_id
                    ):
                        raise ContractError(
                            "CompletionのScene Planが"
                            "Chapter Planと一致しません"
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
                            "Completionには全計画Sceneの"
                            "確定directoryが必要です"
                        )
                    if {
                        entry.name
                        for entry in scene_root.iterdir()
                    } != _SCENE_FILES:
                        raise ContractError(
                            "Completion対象Sceneの"
                            "file構成が不正です"
                        )

                    prose = (
                        scene_root / "prose.md"
                    ).read_text(encoding="utf-8")
                    if not prose.strip():
                        raise ContractError(
                            "Completion対象Sceneの"
                            "prose.mdが空です"
                        )

                    scene_commit = read_json(
                        scene_root / "commit.json"
                    )
                    if (
                        scene_commit.get("scene_id")
                        != scene_id
                        or scene_commit.get(
                            "parent_generation_id"
                        )
                        != expected_parent_generation_id
                    ):
                        raise ContractError(
                            "Completion対象Sceneの"
                            "Generation系列が不正です"
                        )

                    result_generation_id = (
                        _required_string(
                            scene_commit.get(
                                "result_generation_id"
                            ),
                            "Scene Commit."
                            "result_generation_id",
                        )
                    )
                    expected_parent_generation_id = (
                        result_generation_id
                    )

                    expected_scene_ids.add(scene_id)
                    completed_scene_ids.append(scene_id)
                    volume_scene_ids.append(scene_id)

            handoff_id = (
                f"handoff-v{volume_number:02d}"
            )
            handoff = read_json(
                self.workspace_root
                / "handoffs"
                / handoff_id
                / "handoff.json"
            )
            if (
                handoff.get("handoff_id") != handoff_id
                or handoff.get("volume_number")
                != volume_number
                or handoff.get("completed_chapter_ids")
                != expected_chapter_ids
                or handoff.get("completed_scene_ids")
                != volume_scene_ids
                or handoff.get("basis_generation_id")
                != expected_parent_generation_id
            ):
                raise ContractError(
                    "Completion対象Handoffが"
                    "確定済みPlan／Sceneと一致しません"
                )

            expected_handoff_names.add(handoff_id)
            handoffs.append(handoff)

        if (
            expected_parent_generation_id
            != final_generation_id
        ):
            raise ContractError(
                "Completionのcurrent Generationが"
                "最終計画Sceneの結果ではありません"
            )

        actual_scene_ids = {
            entry.name
            for entry in (
                self.workspace_root / "scenes"
            ).iterdir()
            if entry.is_dir() and not entry.is_symlink()
        }
        if actual_scene_ids != expected_scene_ids:
            raise ContractError(
                "Completionの確定Scene集合が"
                "全Planと一致しません"
            )

        actual_handoff_names = {
            entry.name
            for entry in (
                self.workspace_root / "handoffs"
            ).iterdir()
            if entry.is_dir() and not entry.is_symlink()
        }
        if actual_handoff_names != expected_handoff_names:
            raise ContractError(
                "CompletionのHandoff集合が"
                "Series Planと一致しません"
            )

        for entry in (
            self.workspace_root / "runtime/staging"
        ).iterdir():
            if entry.name.startswith(
                ("scene-scene-", "generation-gen-")
            ):
                raise ContractError(
                    "Completion開始時に未完了の"
                    "Scene／Generation stagingがあります"
                )

        return handoffs, completed_scene_ids

    def _read_generation(
        self,
        generation_id: str,
    ) -> dict[str, Any]:
        generation_root = (
            self.workspace_root
            / "generations"
            / generation_id
        )
        if (
            generation_root.is_symlink()
            or not generation_root.is_dir()
        ):
            raise ContractError(
                "Completionの最終Generationが存在しません"
            )

        generation: dict[str, Any] = {}
        for name in _GENERATION_FILES:
            path = generation_root / name
            if not path.is_file():
                raise ContractError(
                    "Completionの最終Generationが"
                    f"不完全です: {name}"
                )
            generation[name] = read_json(path)
        return generation

    @staticmethod
    def _validate_current_generation(
        generation: dict[str, Any],
        generation_id: str,
        completed_scene_ids: list[str],
    ) -> None:
        if not completed_scene_ids:
            raise ContractError(
                "Completionには一つ以上の"
                "確定Sceneが必要です"
            )

        for name in _GENERATION_FILES:
            record = generation.get(name)
            if (
                not isinstance(record, dict)
                or record.get("generation_id")
                != generation_id
            ):
                raise ContractError(
                    "Completionの最終Generationが"
                    f"不正です: {name}"
                )

        commit = generation["commit.json"]
        if (
            commit.get("commit_type") != "scene"
            or commit.get("source_artifact_type")
            != "scene"
            or commit.get("source_artifact_id")
            != completed_scene_ids[-1]
        ):
            raise ContractError(
                "Completionの最終Generationが"
                "最終Scene由来ではありません"
            )

    def _adopt(
        self,
        candidate: dict[str, Any],
        current_generation: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        handoffs: list[dict[str, Any]],
        basis_generation_id: str,
        completion_id: str,
        created_at: str,
    ) -> None:
        """Completion Candidateをimmutable Resultへ採用する。"""
        ContractValidator._validate_completion(
            candidate,
            current_generation,
            initial_design,
            series_plan,
            handoffs,
            basis_generation_id,
        )

        adopted = {
            "schema_version": 1,
            "completion_id": completion_id,
            "basis_generation_id": (
                basis_generation_id
            ),
            "precheck_summary": deepcopy(
                _PRECHECK_SUMMARY
            ),
            **deepcopy(candidate),
            "created_at": created_at,
        }

        ContractValidator._validate_completion(
            adopted,
            current_generation,
            initial_design,
            series_plan,
            handoffs,
            basis_generation_id,
            adopted=True,
        )

        completion_root = (
            self.workspace_root / "completion"
        )
        final = completion_root / completion_id

        def validate_directory(directory: Path) -> None:
            if {
                entry.name
                for entry in directory.iterdir()
            } != {"result.json"}:
                raise ContractError(
                    "Completion directoryの"
                    "file構成が不正です"
                )

            result = read_json(
                directory / "result.json"
            )
            ContractValidator._validate_completion(
                result,
                current_generation,
                initial_design,
                series_plan,
                handoffs,
                basis_generation_id,
                adopted=True,
            )

        if final.exists() or final.is_symlink():
            if final.is_dir() and not final.is_symlink():
                validate_directory(final)
                if (
                    read_json(final / "result.json")
                    == adopted
                ):
                    return
            raise ContractError(
                "採用済みCompletion Resultを"
                "上書きできません"
            )

        staging = Path(
            tempfile.mkdtemp(
                prefix=f".{completion_id}-",
                dir=completion_root,
            )
        )
        try:
            write_json_new(
                staging / "result.json",
                adopted,
            )
            finalize_immutable_directory(
                staging=staging,
                final=final,
                validator=validate_directory,
            )
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise

    @staticmethod
    def _after_adoption(
        candidate: dict[str, Any],
        adopted_state: dict[str, Any],
        completion_id: str,
        series_plan: dict[str, Any],
        basis_generation_id: str,
        updated_at: str,
    ) -> dict[str, Any]:
        """Completion statusに応じてPublicationまたは停止へ進む。"""
        if candidate["status"] == "incomplete":
            return stop_state(
                adopted_state,
                status="blocked",
                stop_reason="completion_incomplete",
                last_error={
                    "code": "COMPLETION_INCOMPLETE",
                    "message": candidate["summary"],
                    "completion_id": completion_id,
                    "issues": deepcopy(
                        candidate["issues"]
                    ),
                },
                updated_at=updated_at,
            )

        advanced = advance_run_state(
            adopted_state,
            next_stage=Stage.PUBLICATION,
            next_target={
                "series": adopted_state[
                    "workspace_id"
                ],
                "series_plan_id": series_plan[
                    "series_plan_id"
                ],
                "completion_id": completion_id,
                "completion_status": candidate[
                    "status"
                ],
                "basis_generation_id": (
                    basis_generation_id
                ),
            },
            updated_at=updated_at,
        )
        return validate_run_state(advanced)


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


def _required_string(
    value: object,
    label: str,
) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(
            f"{label}は空でない文字列が必要です"
        )
    return value


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
