"""Storycraft Version 1 scene_commit Stage実行。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import re
import shutil
from typing import Any

from .immutable_directory import (
    finalize_immutable_directory,
)
from .reviewed_candidate_stage import (
    fsync_directory,
    read_json,
    utc_now,
    write_json_new,
)
from .orphan_storage import move_directory_to_orphans
from .run_state import RunStateStore, validate_run_state
from .scene_adoption_record import (
    load_scene_adoption_record,
    restore_scene_staging_from_adoption_record,
)
from .scene_continuity_stage import (
    SceneContinuityStageService,
)
from .scene_generation import (
    build_scene_commit,
    build_scene_generation,
    validate_scene_commit,
    validate_scene_generation,
)
from .scene_prose_stage import SceneProseStageService
from .series_contracts import (
    ContractError,
    ContractValidator,
)
from .stage_transition import advance_run_state
from .stages import Stage
from .workspace import validate_workspace_layout


_GENERATION_FILES = (
    "canon.json",
    "state.json",
    "evidence.json",
    "commit.json",
)


def determine_scene_commit_transition(
    *,
    state: dict[str, Any],
    series_plan: dict[str, Any],
    volume_plan: dict[str, Any],
    chapter_plan: dict[str, Any],
    result_generation_id: str,
) -> tuple[Stage, dict[str, Any]]:
    """採用済みPlanだけからScene Commit後の遷移を決める。"""
    target = state.get("current_target")
    if not isinstance(target, dict):
        raise ContractError(
            "scene_commit current_targetが不正です"
        )

    volume_number = _positive_integer(
        target.get("volume_number"),
        "current_target.volume_number",
    )
    chapter_number = _positive_integer(
        target.get("chapter_number"),
        "current_target.chapter_number",
    )
    scene_number = _positive_integer(
        target.get("scene_number"),
        "current_target.scene_number",
    )

    scene_numbers = _ordered_numbers(
        chapter_plan.get("scene_summaries"),
        field="scene_number",
        label="Chapter Plan Scene",
    )
    chapter_numbers = _ordered_numbers(
        volume_plan.get("chapter_summaries"),
        field="chapter_number",
        label="Volume Plan Chapter",
    )

    if scene_number not in scene_numbers:
        raise ContractError(
            "Scene Commit対象がChapter Planにありません"
        )
    if chapter_number not in chapter_numbers:
        raise ContractError(
            "Scene Commit対象ChapterがVolume Planにありません"
        )

    workspace_id = _required_string(
        state.get("workspace_id"),
        "run-state.workspace_id",
    )
    series_plan_id = _required_string(
        series_plan.get("series_plan_id"),
        "Series Plan.series_plan_id",
    )
    volume_plan_id = _required_string(
        volume_plan.get("volume_plan_id"),
        "Volume Plan.volume_plan_id",
    )
    chapter_plan_id = _required_string(
        chapter_plan.get("chapter_plan_id"),
        "Chapter Plan.chapter_plan_id",
    )
    generation_id = _required_string(
        result_generation_id,
        "result_generation_id",
    )

    if scene_number < scene_numbers[-1]:
        return (
            Stage.SCENE_PLAN,
            {
                "series": workspace_id,
                "series_plan_id": series_plan_id,
                "volume_plan_id": volume_plan_id,
                "chapter_plan_id": chapter_plan_id,
                "volume_number": volume_number,
                "chapter_number": chapter_number,
                "scene_number": scene_number + 1,
                "basis_generation_id": generation_id,
            },
        )

    if chapter_number < chapter_numbers[-1]:
        return (
            Stage.CHAPTER_PLAN,
            {
                "series": workspace_id,
                "series_plan_id": series_plan_id,
                "volume_plan_id": volume_plan_id,
                "volume_number": volume_number,
                "chapter_number": chapter_number + 1,
                "basis_generation_id": generation_id,
            },
        )

    return (
        Stage.VOLUME_HANDOFF,
        {
            "series": workspace_id,
            "series_plan_id": series_plan_id,
            "volume_plan_id": volume_plan_id,
            "volume_number": volume_number,
            "basis_generation_id": generation_id,
        },
    )


class SceneCommitStageService:
    """Sceneと後継Generationをcode-onlyで確定する。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser()
        self.state_store = RunStateStore(self.workspace_root)

    def run(
        self,
        *,
        workspace_already_validated: bool = False,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        if not workspace_already_validated:
            validate_workspace_layout(
                self.workspace_root
            )
        state = self.state_store.load()

        if state["current_stage"] != Stage.SCENE_COMMIT.value:
            raise ContractError(
                "現在のrun-stateはscene_commitではありません"
            )
        if state["status"] != "running":
            raise ContractError(
                "scene_commitを実行できるrun statusではありません"
            )
        if state["active_candidate"] is not None:
            raise ContractError(
                "scene_commitにはactive_candidateを"
                "残せません"
            )
        if state["pending_commit"] is not None:
            raise ContractError(
                "pending_commitはRecoveryで処理する必要があります"
            )

        timestamp = updated_at or utc_now()
        _validate_timestamp_progress(
            state["updated_at"],
            timestamp,
        )

        target = state["current_target"]
        volume_number = _positive_integer(
            target.get("volume_number"),
            "current_target.volume_number",
        )
        chapter_number = _positive_integer(
            target.get("chapter_number"),
            "current_target.chapter_number",
        )
        scene_number = _positive_integer(
            target.get("scene_number"),
            "current_target.scene_number",
        )

        scene_id = (
            f"scene-v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}"
        )
        if state["active_scene_id"] != scene_id:
            raise ContractError(
                "scene_commitのactive_scene_idが"
                "対象Sceneと一致しません"
            )
        if target.get("scene_id") != scene_id:
            raise ContractError(
                "scene_commit targetのscene_idが"
                "対象座標と一致しません"
            )

        self._ensure_scene_staging_available(
            scene_id=scene_id,
            updated_at=timestamp,
        )

        parent_generation_id = state[
            "current_generation_id"
        ]
        if not isinstance(parent_generation_id, str):
            raise ContractError(
                "scene_commitにはcurrent Generationが必要です"
            )
        if (
            target.get("basis_generation_id")
            != parent_generation_id
        ):
            raise ContractError(
                "scene_commit targetのbasis Generationが"
                "current Generationと一致しません"
            )

        result_generation_id = _required_string(
            target.get("result_generation_id"),
            "current_target.result_generation_id",
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
        parent_generation = self._read_generation(
            parent_generation_id
        )

        scene_staging = (
            self.workspace_root
            / "runtime/staging"
            / f"scene-{scene_id}"
        )
        scene_card = read_json(
            scene_staging / "scene-card.json"
        )
        prose_path = scene_staging / "prose.md"
        if not prose_path.is_file():
            raise ContractError(
                "scene_commitには凍結済みprose.mdが必要です"
            )
        try:
            prose = prose_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ContractError(
                "scene_commitのprose.mdを読めません"
            ) from exc
        continuity = read_json(
            scene_staging / "continuity.json"
        )

        expected_target = {
            "series": state["workspace_id"],
            "series_plan_id": series_plan["series_plan_id"],
            "volume_plan_id": volume_plan["volume_plan_id"],
            "chapter_plan_id": chapter_plan["chapter_plan_id"],
            "scene_plan_id": scene_plan["scene_plan_id"],
            "scene_id": scene_id,
            "scene_card_version": scene_card["version"],
            "prose_version": continuity["prose_version"],
            "continuity_version": continuity["version"],
            "volume_number": volume_number,
            "chapter_number": chapter_number,
            "scene_number": scene_number,
            "basis_generation_id": parent_generation_id,
            "result_generation_id": continuity[
                "result_generation_id"
            ],
        }
        for field, expected in expected_target.items():
            if target.get(field) != expected:
                raise ContractError(
                    "scene_commit targetの"
                    f"{field}が採用済み成果物と一致しません"
                )

        ContractValidator._validate_scene_card_v1(
            scene_card,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            parent_generation,
            volume_number,
            chapter_number,
            scene_number,
            parent_generation_id,
            adopted=True,
        )
        SceneProseStageService._validate_prose_text(prose)
        SceneContinuityStageService._validate_adopted(
            continuity,
            prose=prose,
            scene_card=scene_card,
            current_generation=parent_generation,
            initial_design=initial_design,
            scene_id=scene_id,
            basis_generation_id=parent_generation_id,
        )

        self._validate_prior_scene_order(
            volume_number=volume_number,
            chapter_number=chapter_number,
            scene_number=scene_number,
        )

        scene_commit = build_scene_commit(
            scene_card=scene_card,
            continuity=continuity,
        )
        validate_scene_commit(
            scene_commit,
            scene_card=scene_card,
            continuity=continuity,
        )

        self._ensure_scene_commit(
            scene_staging,
            scene_commit,
        )

        generation = build_scene_generation(
            parent_generation=parent_generation,
            continuity=continuity,
            scene_commit=scene_commit,
        )
        validate_scene_generation(
            generation,
            parent_generation=parent_generation,
            continuity=continuity,
            scene_commit=scene_commit,
        )

        generation_staging = (
            self.workspace_root
            / "runtime/staging"
            / f"generation-{result_generation_id}"
        )
        scene_final = (
            self.workspace_root / "scenes" / scene_id
        )
        generation_final = (
            self.workspace_root
            / "generations"
            / result_generation_id
        )

        if scene_final.exists() or scene_final.is_symlink():
            raise ContractError(
                "確定対象Sceneが既に存在します"
            )
        if (
            generation_final.exists()
            or generation_final.is_symlink()
        ):
            raise ContractError(
                "確定対象Generationが既に存在します"
            )

        scene_validator = lambda path: (
            self._validate_scene_directory(
                path,
                brief=brief,
                initial_design=initial_design,
                series_plan=series_plan,
                volume_plan=volume_plan,
                chapter_plan=chapter_plan,
                scene_plan=scene_plan,
                parent_generation=parent_generation,
                scene_card=scene_card,
                continuity=continuity,
                scene_commit=scene_commit,
                prose=prose,
                volume_number=volume_number,
                chapter_number=chapter_number,
                scene_number=scene_number,
                parent_generation_id=(
                    parent_generation_id
                ),
            )
        )
        generation_validator = lambda path: (
            self._validate_generation_directory(
                path,
                parent_generation=parent_generation,
                continuity=continuity,
                scene_commit=scene_commit,
            )
        )

        self._ensure_generation_staging(
            generation_staging,
            generation,
            generation_validator,
        )

        scene_validator(scene_staging)
        generation_validator(generation_staging)

        commit_state = self._save_pending_phase(
            state,
            scene_id=scene_id,
            result_generation_id=result_generation_id,
            phase="prepared",
            updated_at=timestamp,
        )

        finalize_immutable_directory(
            staging=scene_staging,
            final=scene_final,
            validator=scene_validator,
        )
        commit_state = self._save_pending_phase(
            commit_state,
            scene_id=scene_id,
            result_generation_id=result_generation_id,
            phase="scene_finalized",
            updated_at=timestamp,
        )

        finalize_immutable_directory(
            staging=generation_staging,
            final=generation_final,
            validator=generation_validator,
        )
        commit_state = self._save_pending_phase(
            commit_state,
            scene_id=scene_id,
            result_generation_id=result_generation_id,
            phase="generation_finalized",
            updated_at=timestamp,
        )

        next_stage, next_target = (
            determine_scene_commit_transition(
                state=commit_state,
                series_plan=series_plan,
                volume_plan=volume_plan,
                chapter_plan=chapter_plan,
                result_generation_id=result_generation_id,
            )
        )

        ready = deepcopy(commit_state)
        ready["current_generation_id"] = (
            result_generation_id
        )
        ready["pending_commit"] = None
        validate_run_state(ready)

        advanced = advance_run_state(
            ready,
            next_stage=next_stage,
            next_target=next_target,
            updated_at=timestamp,
        )
        self.state_store.save(advanced)

        validate_workspace_layout(self.workspace_root)
        return advanced

    def _ensure_scene_staging_available(
        self,
        *,
        scene_id: str,
        updated_at: str,
    ) -> Path:
        """採用記録と一致するScene stagingを用意する。"""
        final_scene = (
            self.workspace_root / "scenes" / scene_id
        )
        if (
            final_scene.exists()
            or final_scene.is_symlink()
        ):
            raise ContractError(
                "pending_commitがない状態で"
                "確定済みSceneが存在します"
            )

        record = load_scene_adoption_record(
            self.workspace_root,
            scene_id,
        )
        staging = (
            self.workspace_root
            / "runtime/staging"
            / f"scene-{scene_id}"
        )

        if not staging.exists() and not staging.is_symlink():
            return restore_scene_staging_from_adoption_record(
                self.workspace_root,
                scene_id,
            )

        if staging.is_symlink() or not staging.is_dir():
            raise ContractError(
                "Scene stagingが通常directoryでは"
                "ないためmanual対応が必要です"
            )

        try:
            scene_card = read_json(
                staging / "scene-card.json"
            )
            continuity = read_json(
                staging / "continuity.json"
            )
            prose = (
                staging / "prose.md"
            ).read_text(encoding="utf-8")

            if scene_card != record.scene_card:
                raise ContractError(
                    "Scene stagingのScene Cardが"
                    "採用記録と一致しません"
                )
            if prose != record.prose:
                raise ContractError(
                    "Scene stagingの本文が"
                    "採用記録と一致しません"
                )
            if continuity != record.continuity:
                raise ContractError(
                    "Scene stagingのContinuityが"
                    "採用記録と一致しません"
                )

            return staging
        except (
            ContractError,
            OSError,
            UnicodeError,
        ):
            move_directory_to_orphans(
                self.workspace_root,
                staging,
                updated_at=updated_at,
            )
            return restore_scene_staging_from_adoption_record(
                self.workspace_root,
                scene_id,
            )

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
                "current Generation directoryが存在しません"
            )
        return {
            name: read_json(root / name)
            for name in _GENERATION_FILES
        }

    def _ensure_scene_commit(
        self,
        scene_staging: Path,
        scene_commit: dict[str, Any],
    ) -> None:
        path = scene_staging / "commit.json"
        if path.exists():
            existing = read_json(path)
            if existing != scene_commit:
                raise ContractError(
                    "Scene stagingのcommit.jsonが"
                    "予定内容と競合しています"
                )
            return

        write_json_new(path, scene_commit)
        fsync_directory(scene_staging)

    def _ensure_generation_staging(
        self,
        staging: Path,
        generation: dict[str, dict[str, Any]],
        validator: Any,
    ) -> None:
        if staging.exists():
            if not staging.is_dir() or staging.is_symlink():
                raise ContractError(
                    "Generation staging pathが不正です"
                )
            validator(staging)
            return

        staging.mkdir()
        try:
            for name in _GENERATION_FILES:
                write_json_new(
                    staging / name,
                    generation[name],
                )
            fsync_directory(staging)
            validator(staging)
        except Exception:
            if staging.exists():
                shutil.rmtree(staging)
            raise

    def _validate_scene_directory(
        self,
        root: Path,
        *,
        brief: dict[str, Any],
        initial_design: dict[str, Any],
        series_plan: dict[str, Any],
        volume_plan: dict[str, Any],
        chapter_plan: dict[str, Any],
        scene_plan: dict[str, Any],
        parent_generation: dict[str, dict[str, Any]],
        scene_card: dict[str, Any],
        continuity: dict[str, Any],
        scene_commit: dict[str, Any],
        prose: str,
        volume_number: int,
        chapter_number: int,
        scene_number: int,
        parent_generation_id: str,
    ) -> None:
        required = {
            "scene-card.json",
            "prose.md",
            "continuity.json",
            "commit.json",
        }
        names = {entry.name for entry in root.iterdir()}
        if not required.issubset(names):
            raise ContractError(
                "Scene directoryの必須fileが不足しています"
            )
        if names - required - {"metadata.json"}:
            raise ContractError(
                "Scene directoryに未知fileがあります"
            )

        written_card = read_json(root / "scene-card.json")
        written_continuity = read_json(
            root / "continuity.json"
        )
        written_commit = read_json(root / "commit.json")
        try:
            written_prose = (
                root / "prose.md"
            ).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ContractError(
                "Scene directoryのprose.mdを読めません"
            ) from exc

        if written_card != scene_card:
            raise ContractError(
                "Scene directoryのScene Cardが変化しています"
            )
        if written_continuity != continuity:
            raise ContractError(
                "Scene directoryのContinuityが変化しています"
            )
        if written_commit != scene_commit:
            raise ContractError(
                "Scene directoryのCommitが変化しています"
            )
        if written_prose != prose:
            raise ContractError(
                "Scene directoryの本文が変化しています"
            )

        ContractValidator._validate_scene_card_v1(
            written_card,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            scene_plan,
            parent_generation,
            volume_number,
            chapter_number,
            scene_number,
            parent_generation_id,
            adopted=True,
        )
        SceneProseStageService._validate_prose_text(
            written_prose
        )
        SceneContinuityStageService._validate_adopted(
            written_continuity,
            prose=written_prose,
            scene_card=written_card,
            current_generation=parent_generation,
            initial_design=initial_design,
            scene_id=written_card["scene_id"],
            basis_generation_id=parent_generation_id,
        )
        validate_scene_commit(
            written_commit,
            scene_card=written_card,
            continuity=written_continuity,
        )

    def _validate_generation_directory(
        self,
        root: Path,
        *,
        parent_generation: dict[str, dict[str, Any]],
        continuity: dict[str, Any],
        scene_commit: dict[str, Any],
    ) -> None:
        names = {entry.name for entry in root.iterdir()}
        if names != set(_GENERATION_FILES):
            raise ContractError(
                "Scene Generationのfile構成が不正です"
            )

        files = {
            name: read_json(root / name)
            for name in _GENERATION_FILES
        }
        validate_scene_generation(
            files,
            parent_generation=parent_generation,
            continuity=continuity,
            scene_commit=scene_commit,
        )

    def _save_pending_phase(
        self,
        state: dict[str, Any],
        *,
        scene_id: str,
        result_generation_id: str,
        phase: str,
        updated_at: str,
    ) -> dict[str, Any]:
        updated = deepcopy(state)
        updated["pending_commit"] = {
            "kind": Stage.SCENE_COMMIT.value,
            "target_id": scene_id,
            "expected_generation_id": (
                result_generation_id
            ),
            "phase": phase,
        }
        updated["updated_at"] = updated_at
        self.state_store.save(updated)
        return updated

    def _validate_prior_scene_order(
        self,
        *,
        volume_number: int,
        chapter_number: int,
        scene_number: int,
    ) -> None:
        scenes_root = self.workspace_root / "scenes"
        pattern = re.compile(
            r"scene-v(\d{2})-c(\d{3})-s(\d{3})"
        )
        actual: set[int] = set()

        for entry in scenes_root.iterdir():
            match = pattern.fullmatch(entry.name)
            if match is None:
                continue
            if not entry.is_dir() or entry.is_symlink():
                raise ContractError(
                    "Scene final pathはdirectoryが必要です"
                )
            if (
                int(match.group(1)) == volume_number
                and int(match.group(2)) == chapter_number
            ):
                actual.add(int(match.group(3)))

        expected = set(range(1, scene_number))
        if actual != expected:
            raise ContractError(
                "確定済みScene順が対象Sceneと一致しません"
            )


def _ordered_numbers(
    records: object,
    *,
    field: str,
    label: str,
) -> list[int]:
    if not isinstance(records, list) or not records:
        raise ContractError(
            f"{label}一覧が不正です"
        )

    numbers: list[int] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ContractError(
                f"{label}[{index}]が不正です"
            )
        numbers.append(
            _positive_integer(
                record.get(field),
                f"{label}[{index}].{field}",
            )
        )

    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        raise ContractError(
            f"{label}番号が1から連続していません"
        )
    return numbers


def _positive_integer(value: object, field: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ContractError(
            f"{field}は1以上の整数が必要です"
        )
    return value


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(
            f"{field}は空でない文字列が必要です"
        )
    return value


def _validate_timestamp_progress(
    previous: object,
    following: object,
) -> None:
    previous_time = _parse_timestamp(
        previous,
        "現在のupdated_at",
    )
    following_time = _parse_timestamp(
        following,
        "scene_commit updated_at",
    )
    if following_time < previous_time:
        raise ContractError(
            "scene_commitでupdated_atを後退できません"
        )


def _parse_timestamp(
    value: object,
    field: str,
) -> datetime:
    if not isinstance(value, str):
        raise ContractError(
            f"{field}はISO 8601文字列が必要です"
        )
    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ContractError(
            f"{field}がISO 8601形式ではありません"
        ) from exc
    if parsed.tzinfo is None:
        raise ContractError(
            f"{field}にはtimezoneが必要です"
        )
    return parsed
