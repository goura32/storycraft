"""Storycraft Version 1 workspaceの安全な初期化。"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from jsonschema import Draft202012Validator

from .prompt_template import get_template_loader
from .run_state import RunStateStore, validate_run_state
from .series_contracts import ContractError
from .stages import Stage


REQUIRED_DIRECTORIES = (
    "input",
    "runtime",
    "runtime/staging",
    "runtime/candidates",
    "runtime/calls",
    "runtime/orphans",
    "design",
    "design/initial",
    "design/series-plans",
    "design/volume-plans",
    "design/chapter-plans",
    "design/scene-plans",
    "generations",
    "scenes",
    "handoffs",
    "completion",
    "publications",
    "logs",
)

INITIAL_COUNTERS = {
    "schema_version": 1,
    "next_run": 2,
    "next_generation": 1,
    "next_publication": 1,
    "next_candidate": 1,
    "next_review": 1,
    "next_revision": 1,
    "next_call": 1,
    "next_completion": 1,
    "next_evidence": 1,
    "next_update": 1,
}


def create_workspace(
    workspace_root: Path,
    *,
    workspace_id: str,
    config: dict[str, Any],
    brief: dict[str, Any] | None = None,
    keywords: dict[str, Any] | None = None,
    created_at: str | None = None,
) -> Path:
    """BriefまたはKeywordsの正確に一方からworkspaceを作成する。"""
    if brief is not None and keywords is not None:
        raise ContractError(
            "INPUT_MODE_CONFLICT: BriefとKeywordsを同時に指定できません"
        )
    if brief is None and keywords is None:
        raise ContractError(
            "INPUT_MODE_REQUIRED: BriefまたはKeywordsのどちらか一方が必要です"
        )

    if brief is not None:
        return _create_workspace(
            workspace_root,
            workspace_id=workspace_id,
            input_kind="brief",
            input_payload=brief,
            config=config,
            created_at=created_at,
        )

    assert keywords is not None
    return _create_workspace(
        workspace_root,
        workspace_id=workspace_id,
        input_kind="keywords",
        input_payload=keywords,
        config=config,
        created_at=created_at,
    )


def create_workspace_from_brief(
    workspace_root: Path,
    *,
    workspace_id: str,
    brief: dict[str, Any],
    config: dict[str, Any],
    created_at: str | None = None,
) -> Path:
    """Brief入力からV1 workspaceを作成する。"""
    return create_workspace(
        workspace_root,
        workspace_id=workspace_id,
        brief=brief,
        config=config,
        created_at=created_at,
    )


def create_workspace_from_keywords(
    workspace_root: Path,
    *,
    workspace_id: str,
    keywords: dict[str, Any],
    config: dict[str, Any],
    created_at: str | None = None,
) -> Path:
    """Keywords入力からV1 workspaceを作成する。"""
    return create_workspace(
        workspace_root,
        workspace_id=workspace_id,
        keywords=keywords,
        config=config,
        created_at=created_at,
    )


def _create_workspace(
    workspace_root: Path,
    *,
    workspace_id: str,
    input_kind: str,
    input_payload: dict[str, Any],
    config: dict[str, Any],
    created_at: str | None,
) -> Path:
    root = workspace_root.expanduser()

    if root.exists():
        raise ContractError(
            "workspaceが既に存在します。resumeを使用してください"
        )

    _validate_workspace_destination(root)
    _validate_identifier(workspace_id, "workspace_id", "ws-")

    if input_kind == "brief":
        _validate_brief(input_payload)
    elif input_kind == "keywords":
        _validate_keywords(input_payload)
    else:
        raise ContractError(
            f"未知のinput kindです: {input_kind!r}"
        )

    timestamp = created_at or _utc_now()
    initial_config = _prepare_config(
        config,
        workspace_id=workspace_id,
        created_at=timestamp,
    )
    initial_counters = {
        **INITIAL_COUNTERS,
        "updated_at": timestamp,
    }
    initial_run_state = {
        "schema_version": 1,
        "workspace_id": workspace_id,
        "run_id": "run-000001",
        "status": "initializing",
        "current_stage": Stage.INPUT.value,
        "current_target": {"series": workspace_id},
        "current_generation_id": None,
        "current_publication_id": None,
        "active_candidate": None,
        "active_scene_id": None,
        "pending_commit": None,
        "stop_reason": None,
        "last_error": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    validate_run_state(initial_run_state)

    parent = root.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{root.name}.initializing-",
            dir=parent,
        )
    )

    input_filename = f"{input_kind}.json"

    try:
        _create_directories(staging)
        _write_json(
            staging / "input" / input_filename,
            input_payload,
        )
        _write_json(
            staging / "input/source.json",
            {
                "schema_version": 1,
                "source_type": input_kind,
                "source_path": f"input/{input_filename}",
                "created_at": timestamp,
            },
        )
        _write_json(
            staging / "runtime/config.json",
            initial_config,
        )
        _write_json(
            staging / "runtime/counters.json",
            initial_counters,
        )
        RunStateStore(staging).save(initial_run_state)
        (staging / "runtime/lock").touch(exist_ok=False)

        _validate_created_workspace(
            staging,
            expected_workspace_id=workspace_id,
        )

        staging.rename(root)
        _fsync_directory(parent)
        return root
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def validate_workspace_layout(
    workspace_root: Path,
) -> None:
    """既存V1 workspaceの必須layoutを検証する。"""
    root = workspace_root.expanduser()

    if not root.is_dir():
        raise ContractError(
            "workspace directoryが存在しません"
        )

    for relative in REQUIRED_DIRECTORIES:
        path = root / relative
        if not path.is_dir():
            raise ContractError(
                f"workspace必須directoryがありません: {relative}"
            )

    for relative in (
        "runtime/run-state.json",
        "runtime/config.json",
        "runtime/counters.json",
        "runtime/lock",
        "input/source.json",
    ):
        path = root / relative
        if not path.is_file():
            raise ContractError(
                f"workspace必須fileがありません: {relative}"
            )

    _validate_workspace_input(root)
    _validate_initial_design_artifacts(root)
    _validate_initial_generation_artifacts(root)
    _validate_series_plan_artifacts(root)
    _validate_volume_plan_artifacts(root)
    _validate_chapter_plan_artifacts(root)
    _validate_scene_plan_artifacts(root)

    resolved_root = root.resolve()
    for path in root.rglob("*"):
        if path.is_symlink():
            resolved = path.resolve()
            if not resolved.is_relative_to(resolved_root):
                raise ContractError(
                    f"workspace外を指すsymlinkがあります: {path}"
                )


def _validate_created_workspace(
    workspace_root: Path,
    *,
    expected_workspace_id: str,
) -> None:
    validate_workspace_layout(workspace_root)

    state = RunStateStore(workspace_root).load()
    if state["workspace_id"] != expected_workspace_id:
        raise ContractError(
            "run-stateのworkspace_idが一致しません"
        )

    config = _read_json(
        workspace_root / "runtime/config.json"
    )
    if config.get("workspace_id") != expected_workspace_id:
        raise ContractError(
            "configのworkspace_idが一致しません"
        )

    counters = _read_json(
        workspace_root / "runtime/counters.json"
    )
    _validate_initial_counters(counters)


def _prepare_config(
    config: dict[str, Any],
    *,
    workspace_id: str,
    created_at: str,
) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ContractError(
            "workspace configはオブジェクトでなければなりません"
        )

    prepared = deepcopy(config)
    prepared["schema_version"] = 1
    prepared["workspace_id"] = workspace_id
    prepared.setdefault("config_version", 1)
    prepared.setdefault("language", "ja")
    prepared["created_at"] = created_at

    if prepared["config_version"] != 1:
        raise ContractError(
            "config_versionは1でなければなりません"
        )
    if prepared["language"] != "ja":
        raise ContractError(
            "workspace languageはjaでなければなりません"
        )

    return prepared


def _validate_brief(brief: object) -> None:
    if not isinstance(brief, dict):
        raise ContractError(
            "Briefはオブジェクトでなければなりません"
        )

    schema = get_template_loader().load_schema_object(
        "generate",
        "brief",
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(brief),
        key=lambda item: (
            list(item.absolute_path),
            item.message,
        ),
    )
    if errors:
        first = errors[0]
        path = ".".join(
            str(part) for part in first.absolute_path
        ) or "<root>"
        raise ContractError(
            f"Brief契約違反: {path}: {first.message}"
        )


def _validate_keywords(keywords: object) -> None:
    if not isinstance(keywords, dict):
        raise ContractError(
            "Keywordsはオブジェクトでなければなりません"
        )

    required = {
        "schema_version",
        "source_type",
        "keywords",
        "avoid",
        "ending_preference",
        "volume_hint",
        "language",
    }
    allowed = required | {"notes"}
    missing = required - set(keywords)
    unknown = set(keywords) - allowed

    if missing:
        raise ContractError(
            "Keywords必須field不足: "
            + ", ".join(sorted(missing))
        )
    if unknown:
        raise ContractError(
            "Keywords未知field: "
            + ", ".join(sorted(unknown))
        )
    if keywords["schema_version"] != 1:
        raise ContractError(
            "Keywords.schema_versionは1でなければなりません"
        )
    if keywords["source_type"] != "keywords":
        raise ContractError(
            "Keywords.source_typeはkeywordsでなければなりません"
        )

    _validate_unique_string_list(
        keywords["keywords"],
        "Keywords.keywords",
        allow_empty=False,
    )
    _validate_unique_string_list(
        keywords["avoid"],
        "Keywords.avoid",
        allow_empty=True,
    )

    ending = keywords["ending_preference"]
    if not isinstance(ending, str) or not ending.strip():
        raise ContractError(
            "Keywords.ending_preferenceは空でない文字列が必要です"
        )

    volume_hint = keywords["volume_hint"]
    if (
        not isinstance(volume_hint, int)
        or isinstance(volume_hint, bool)
        or not 4 <= volume_hint <= 10
    ):
        raise ContractError(
            "Keywords.volume_hintは4から10の整数でなければなりません"
        )

    if keywords["language"] != "ja":
        raise ContractError(
            "Keywords.languageはjaでなければなりません"
        )

    notes = keywords.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise ContractError(
            "Keywords.notesは文字列またはnullでなければなりません"
        )


def _validate_unique_string_list(
    value: object,
    field: str,
    *,
    allow_empty: bool,
) -> None:
    if not isinstance(value, list):
        raise ContractError(
            f"{field}は配列でなければなりません"
        )
    if not allow_empty and not value:
        raise ContractError(
            f"{field}は一つ以上必要です"
        )
    if not all(
        isinstance(item, str) and item.strip()
        for item in value
    ):
        raise ContractError(
            f"{field}は空でない文字列だけを含めなければなりません"
        )
    if len(value) != len(set(value)):
        raise ContractError(
            f"{field}に重複を含められません"
        )


def _validate_workspace_input(root: Path) -> None:
    source = _read_json(root / "input/source.json")
    source_type = source.get("source_type")
    source_path = source.get("source_path")

    if source_type not in {"brief", "keywords"}:
        raise ContractError(
            "input/source.jsonのsource_typeが不正です"
        )

    expected_path = f"input/{source_type}.json"
    if source_path != expected_path:
        raise ContractError(
            "input/source.jsonのsource_pathが不正です"
        )

    selected = root / expected_path

    if not selected.is_file():
        raise ContractError(
            f"workspace入力fileがありません: {expected_path}"
        )

    payload = _read_json(selected)
    brief_path = root / "input/brief.json"
    keywords_path = root / "input/keywords.json"

    if source_type == "brief":
        if keywords_path.exists():
            raise ContractError(
                "Brief起点workspaceにkeywords.jsonを置けません"
            )
        _validate_brief(payload)
        return

    _validate_keywords(payload)

    if brief_path.exists():
        adopted_brief = _read_json(brief_path)
        _validate_brief(adopted_brief)
        if adopted_brief.get("source_type") != "keywords":
            raise ContractError(
                "Keywords起点の採用済みBriefはsource_type=keywordsが必要です"
            )
        if (
            adopted_brief.get("source_reference")
            != "input/keywords.json"
        ):
            raise ContractError(
                "Keywords起点の採用済みBriefは元入力を参照しなければなりません"
            )


def _validate_initial_design_artifacts(root: Path) -> None:
    """存在する採用済みInitial Design部品だけを検証する。"""
    version_root = root / "design/initial/v0001"
    if not version_root.exists():
        return
    if not version_root.is_dir():
        raise ContractError(
            "design/initial/v0001はdirectoryでなければなりません"
        )

    concept_path = version_root / "concept.json"
    characters_path = version_root / "characters.json"
    relationships_path = version_root / "relationships.json"
    world_path = version_root / "world.json"
    knowledge_path = version_root / "knowledge.json"
    threads_path = version_root / "threads.json"
    ending_path = version_root / "ending.json"
    integrated_path = version_root / "integrated.json"
    accepted_path = version_root / "initial-design.json"

    if characters_path.exists() and not concept_path.is_file():
        raise ContractError(
            "採用済みCharactersには採用済みConceptが必要です"
        )

    if relationships_path.exists() and not characters_path.is_file():
        raise ContractError(
            "採用済みRelationshipsには"
            "採用済みCharactersが必要です"
        )

    if world_path.exists() and not relationships_path.is_file():
        raise ContractError(
            "採用済みWorldには"
            "採用済みRelationshipsが必要です"
        )

    if knowledge_path.exists() and not world_path.is_file():
        raise ContractError(
            "採用済みKnowledgeには"
            "採用済みWorldが必要です"
        )

    if threads_path.exists() and not knowledge_path.is_file():
        raise ContractError(
            "採用済みThreadsには"
            "採用済みKnowledgeが必要です"
        )

    if ending_path.exists() and not threads_path.is_file():
        raise ContractError(
            "採用済みEndingには"
            "採用済みThreadsが必要です"
        )

    if integrated_path.exists() and not ending_path.is_file():
        raise ContractError(
            "統合Initial Designには"
            "採用済みEndingが必要です"
        )

    if accepted_path.exists() and not integrated_path.is_file():
        raise ContractError(
            "採用済みInitial Designには"
            "統合Initial Designが必要です"
        )

    if concept_path.exists():
        if not concept_path.is_file():
            raise ContractError(
                "採用済みConceptはfileでなければなりません"
            )

        from .series_contracts import ContractValidator

        concept = _read_json(concept_path)
        brief = _read_json(root / "input/brief.json")
        ContractValidator._validate_initial_concept(
            concept,
            brief,
        )

        if characters_path.exists():
            if not characters_path.is_file():
                raise ContractError(
                    "採用済みCharactersはfileでなければなりません"
                )
            characters = _read_json(characters_path)
            ContractValidator._validate_initial_characters(
                characters,
                brief,
                concept,
                adopted=True,
            )

            if relationships_path.exists():
                if not relationships_path.is_file():
                    raise ContractError(
                        "採用済みRelationshipsは"
                        "fileでなければなりません"
                    )
                relationships = _read_json(
                    relationships_path
                )
                ContractValidator._validate_initial_relationships(
                    relationships,
                    concept,
                    characters,
                    adopted=True,
                )

                if world_path.exists():
                    if not world_path.is_file():
                        raise ContractError(
                            "採用済みWorldは"
                            "fileでなければなりません"
                        )
                    world = _read_json(world_path)
                    ContractValidator._validate_initial_world(
                        world,
                        brief,
                        concept,
                        characters,
                        relationships,
                        adopted=True,
                    )

                    if knowledge_path.exists():
                        if not knowledge_path.is_file():
                            raise ContractError(
                                "採用済みKnowledgeは"
                                "fileでなければなりません"
                            )
                        knowledge = _read_json(
                            knowledge_path
                        )
                        ContractValidator._validate_initial_knowledge(
                            knowledge,
                            brief,
                            concept,
                            characters,
                            relationships,
                            world,
                            adopted=True,
                        )

                        if threads_path.exists():
                            if not threads_path.is_file():
                                raise ContractError(
                                    "採用済みThreadsは"
                                    "fileでなければなりません"
                                )
                            threads = _read_json(
                                threads_path
                            )
                            ContractValidator._validate_initial_threads(
                                threads,
                                brief,
                                concept,
                                characters,
                                relationships,
                                world,
                                knowledge,
                                adopted=True,
                            )

                            if ending_path.exists():
                                if not ending_path.is_file():
                                    raise ContractError(
                                        "採用済みEndingは"
                                        "fileでなければなりません"
                                    )
                                ending = _read_json(
                                    ending_path
                                )
                                ContractValidator._validate_initial_ending(
                                    ending,
                                    brief,
                                    concept,
                                    characters,
                                    relationships,
                                    threads,
                                    adopted=True,
                                )

                                if integrated_path.exists():
                                    if not integrated_path.is_file():
                                        raise ContractError(
                                            "統合Initial Designは"
                                            "fileでなければなりません"
                                        )
                                    integrated = _read_json(
                                        integrated_path
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

                                    if accepted_path.exists():
                                        if not accepted_path.is_file():
                                            raise ContractError(
                                                "採用済みInitial Designは"
                                                "fileでなければなりません"
                                            )
                                        from .initial_generation import (
                                            validate_accepted_initial_design,
                                        )

                                        accepted = _read_json(
                                            accepted_path
                                        )
                                        validate_accepted_initial_design(
                                            accepted,
                                            integrated,
                                            brief,
                                        )


def _validate_initial_generation_artifacts(
    root: Path,
) -> None:
    """存在するGenerationとrun-state参照を検証する。"""
    version_root = root / "design/initial/v0001"
    accepted_path = version_root / "initial-design.json"
    state = RunStateStore(root).load()
    current_generation_id = state[
        "current_generation_id"
    ]
    generation_root = root / "generations"

    generation_directories = sorted(
        generation_root.glob("gen-*")
    )

    if not accepted_path.exists():
        if current_generation_id is not None:
            raise ContractError(
                "current_generation_idには採用済み"
                "Initial Designが必要です"
            )
        if generation_directories:
            raise ContractError(
                "Generationには採用済みInitial Designが必要です"
            )
        return

    accepted = _read_json(accepted_path)

    from .initial_generation import (
        validate_initial_generation,
    )

    generation_ids: set[str] = set()
    initial_generation_ids: list[str] = []
    parents: dict[str, str] = {}

    for directory in generation_directories:
        if not directory.is_dir():
            raise ContractError(
                "Generation pathはdirectoryが必要です"
            )

        generation_id = directory.name
        files: dict[str, Any] = {}
        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            file_path = directory / name
            if not file_path.is_file():
                raise ContractError(
                    "Generationの必須fileが"
                    f"ありません: {generation_id}/{name}"
                )
            value = _read_json(file_path)
            if not isinstance(value, dict):
                raise ContractError(
                    "Generation fileはobjectが必要です: "
                    f"{generation_id}/{name}"
                )
            if value.get("schema_version") != 1:
                raise ContractError(
                    "Generation fileのschema_versionは"
                    f"1が必要です: {generation_id}/{name}"
                )
            if value.get("generation_id") != generation_id:
                raise ContractError(
                    "Generation fileのgeneration_idが"
                    f"directory名と一致しません: "
                    f"{generation_id}/{name}"
                )
            files[name] = value

        commit = files["commit.json"]
        created_at = commit.get("created_at")
        if not isinstance(created_at, str):
            raise ContractError(
                "Generation commitにはcreated_atが必要です"
            )
        try:
            parsed = datetime.fromisoformat(
                created_at.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ContractError(
                "Generation commitのcreated_atが不正です"
            ) from exc
        if parsed.tzinfo is None:
            raise ContractError(
                "Generation commitのcreated_atには"
                "timezoneが必要です"
            )

        commit_type = commit.get("commit_type")
        source_type = commit.get("source_artifact_type")
        source_id = commit.get("source_artifact_id")
        changed_targets = commit.get("changed_targets")
        if not isinstance(commit_type, str) or not commit_type:
            raise ContractError(
                "Generation commit_typeが不正です"
            )
        if not isinstance(source_type, str) or not source_type:
            raise ContractError(
                "Generation source_artifact_typeが不正です"
            )
        if not isinstance(source_id, str) or not source_id:
            raise ContractError(
                "Generation source_artifact_idが不正です"
            )
        if (
            not isinstance(changed_targets, list)
            or not changed_targets
            or any(
                not isinstance(target, str) or not target
                for target in changed_targets
            )
        ):
            raise ContractError(
                "Generation changed_targetsが不正です"
            )

        parent_generation_id = commit.get(
            "parent_generation_id"
        )
        if parent_generation_id is None:
            if (
                commit_type != "initial_design"
                or source_type != "initial_design"
                or source_id != accepted["design_id"]
            ):
                raise ContractError(
                    "親を持たないGenerationは"
                    "Initial Design由来でなければなりません"
                )
            validate_initial_generation(files, accepted)
            initial_generation_ids.append(generation_id)
        else:
            if (
                not isinstance(parent_generation_id, str)
                or not parent_generation_id.startswith("gen-")
                or parent_generation_id == generation_id
            ):
                raise ContractError(
                    "Generation parent_generation_idが不正です"
                )
            if commit_type == "initial_design":
                raise ContractError(
                    "後続Generationのcommit_typeを"
                    "initial_designにできません"
                )
            parents[generation_id] = parent_generation_id

        generation_ids.add(generation_id)

    if len(initial_generation_ids) > 1:
        raise ContractError(
            "Initial Generationが複数存在します"
        )
    if generation_ids and not initial_generation_ids:
        raise ContractError(
            "Generation系列にInitial Generationがありません"
        )

    for generation_id, parent_generation_id in parents.items():
        if parent_generation_id not in generation_ids:
            raise ContractError(
                "Generationのparent Generationが"
                f"存在しません: {generation_id}"
            )

    if current_generation_id is None:
        if (
            state["current_stage"] != Stage.INITIAL_ACCEPT.value
            and generation_ids
        ):
            raise ContractError(
                "Generationがある場合は"
                "current_generation_idが必要です"
            )
        return

    if current_generation_id not in generation_ids:
        raise ContractError(
            "current_generation_idが有効な"
            "Generationを参照していません"
        )


def _validate_series_plan_artifacts(
    root: Path,
) -> None:
    """存在する採用済みSeries Planを検証する。"""
    version_root = (
        root / "design/series-plans/series-plan-v0001"
    )
    if not version_root.exists():
        return
    if not version_root.is_dir():
        raise ContractError(
            "Series Plan version pathはdirectoryが必要です"
        )

    plan_path = version_root / "series-plan.json"
    if not plan_path.is_file():
        raise ContractError(
            "Series Plan version directoryに"
            "series-plan.jsonがありません"
        )

    initial_design_path = (
        root / "design/initial/v0001/initial-design.json"
    )
    if not initial_design_path.is_file():
        raise ContractError(
            "採用済みSeries Planには"
            "採用済みInitial Designが必要です"
        )

    plan = _read_json(plan_path)
    initial_design = _read_json(initial_design_path)
    brief = _read_json(root / "input/brief.json")

    basis_generation_id = plan.get(
        "basis_generation_id"
    )
    if not isinstance(basis_generation_id, str):
        raise ContractError(
            "Series Planのbasis_generation_idが不正です"
        )

    generation_root = (
        root / "generations" / basis_generation_id
    )
    if not generation_root.is_dir():
        raise ContractError(
            "Series Planのbasis Generationが存在しません"
        )
    for name in (
        "canon.json",
        "state.json",
        "evidence.json",
        "commit.json",
    ):
        if not (generation_root / name).is_file():
            raise ContractError(
                "Series Planのbasis Generationが"
                f"不完全です: {name}"
            )

    from .series_contracts import ContractValidator

    ContractValidator._validate_series_plan(
        plan,
        brief,
        initial_design,
        basis_generation_id,
        adopted=True,
    )


def _validate_volume_plan_artifacts(
    root: Path,
) -> None:
    """存在する採用済みVolume Planを検証する。"""
    plans_root = root / "design/volume-plans"
    entries = sorted(plans_root.iterdir())
    if not entries:
        return

    series_plan_path = (
        root
        / "design/series-plans"
        / "series-plan-v0001"
        / "series-plan.json"
    )
    initial_design_path = (
        root / "design/initial/v0001/initial-design.json"
    )
    if not series_plan_path.is_file():
        raise ContractError(
            "採用済みVolume Planには"
            "採用済みSeries Planが必要です"
        )
    if not initial_design_path.is_file():
        raise ContractError(
            "採用済みVolume Planには"
            "採用済みInitial Designが必要です"
        )

    brief = _read_json(root / "input/brief.json")
    initial_design = _read_json(initial_design_path)
    series_plan = _read_json(series_plan_path)

    seen_numbers: set[int] = set()
    for directory in entries:
        if not directory.is_dir():
            raise ContractError(
                "Volume Plan version pathは"
                "directoryが必要です"
            )

        plan_path = directory / "volume-plan.json"
        if not plan_path.is_file():
            raise ContractError(
                "Volume Plan version directoryに"
                "volume-plan.jsonがありません"
            )

        plan = _read_json(plan_path)
        volume_number = plan.get("volume_number")
        if (
            not isinstance(volume_number, int)
            or isinstance(volume_number, bool)
            or volume_number < 1
        ):
            raise ContractError(
                "Volume Planのvolume_numberが不正です"
            )

        expected_directory = (
            f"v{volume_number:02d}-v0001"
        )
        if directory.name != expected_directory:
            raise ContractError(
                "Volume Plan directory名が"
                "volume_numberと一致しません"
            )
        if volume_number in seen_numbers:
            raise ContractError(
                "同じVolumeの採用済みPlanが複数あります"
            )
        seen_numbers.add(volume_number)

        basis_generation_id = plan.get(
            "basis_generation_id"
        )
        if not isinstance(basis_generation_id, str):
            raise ContractError(
                "Volume Planのbasis_generation_idが不正です"
            )

        generation_root = (
            root / "generations" / basis_generation_id
        )
        if not generation_root.is_dir():
            raise ContractError(
                "Volume Planのbasis Generationが存在しません"
            )
        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            if not (generation_root / name).is_file():
                raise ContractError(
                    "Volume Planのbasis Generationが"
                    f"不完全です: {name}"
                )

        from .series_contracts import ContractValidator

        ContractValidator._validate_volume_plan(
            plan,
            brief,
            initial_design,
            series_plan,
            volume_number,
            basis_generation_id,
            adopted=True,
        )



def _validate_chapter_plan_artifacts(
    root: Path,
) -> None:
    """存在する採用済みChapter Planを検証する。"""
    plans_root = root / "design/chapter-plans"
    entries = sorted(plans_root.iterdir())
    if not entries:
        return

    series_plan_path = (
        root
        / "design/series-plans"
        / "series-plan-v0001"
        / "series-plan.json"
    )
    initial_design_path = (
        root / "design/initial/v0001/initial-design.json"
    )
    if not series_plan_path.is_file():
        raise ContractError(
            "採用済みChapter Planには"
            "採用済みSeries Planが必要です"
        )
    if not initial_design_path.is_file():
        raise ContractError(
            "採用済みChapter Planには"
            "採用済みInitial Designが必要です"
        )

    brief = _read_json(root / "input/brief.json")
    initial_design = _read_json(initial_design_path)
    series_plan = _read_json(series_plan_path)

    seen_targets: set[tuple[int, int]] = set()
    chapter_numbers_by_volume: dict[int, set[int]] = {}
    revelation_usage: dict[int, int] = {}
    revelation_limits: dict[int, int] = {}

    for directory in entries:
        if not directory.is_dir():
            raise ContractError(
                "Chapter Plan version pathは"
                "directoryが必要です"
            )

        plan_path = directory / "chapter-plan.json"
        if not plan_path.is_file():
            raise ContractError(
                "Chapter Plan version directoryに"
                "chapter-plan.jsonがありません"
            )

        plan = _read_json(plan_path)
        volume_number = plan.get("volume_number")
        chapter_number = plan.get("chapter_number")
        for number, label in (
            (volume_number, "volume_number"),
            (chapter_number, "chapter_number"),
        ):
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
            ):
                raise ContractError(
                    f"Chapter Planの{label}が不正です"
                )

        expected_directory = (
            f"v{volume_number:02d}"
            f"-c{chapter_number:03d}-v0001"
        )
        if directory.name != expected_directory:
            raise ContractError(
                "Chapter Plan directory名が"
                "対象巻章と一致しません"
            )

        target = (volume_number, chapter_number)
        if target in seen_targets:
            raise ContractError(
                "同じChapterの採用済みPlanが複数あります"
            )
        seen_targets.add(target)
        chapter_numbers_by_volume.setdefault(
            volume_number,
            set(),
        ).add(chapter_number)

        volume_plan_path = (
            root
            / "design/volume-plans"
            / f"v{volume_number:02d}-v0001"
            / "volume-plan.json"
        )
        if not volume_plan_path.is_file():
            raise ContractError(
                "採用済みChapter Planには"
                "親Volume Planが必要です"
            )
        volume_plan = _read_json(volume_plan_path)

        basis_generation_id = plan.get(
            "basis_generation_id"
        )
        if not isinstance(basis_generation_id, str):
            raise ContractError(
                "Chapter Planのbasis_generation_idが不正です"
            )

        generation_root = (
            root / "generations" / basis_generation_id
        )
        if not generation_root.is_dir():
            raise ContractError(
                "Chapter Planのbasis Generationが存在しません"
            )
        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            if not (generation_root / name).is_file():
                raise ContractError(
                    "Chapter Planのbasis Generationが"
                    f"不完全です: {name}"
                )

        from .series_contracts import ContractValidator

        ContractValidator._validate_chapter_plan(
            plan,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            volume_number,
            chapter_number,
            basis_generation_id,
            adopted=True,
        )

        revelation_limits[volume_number] = len(
            volume_plan["revelations"]
        )
        revelation_usage[volume_number] = (
            revelation_usage.get(volume_number, 0)
            + len(plan["required_revelations"])
        )

    for volume_number, chapter_numbers in (
        chapter_numbers_by_volume.items()
    ):
        expected = set(
            range(1, max(chapter_numbers) + 1)
        )
        if chapter_numbers != expected:
            raise ContractError(
                "採用済みChapter Planは"
                "第一章から連続して存在しなければなりません"
            )
        if (
            revelation_usage.get(volume_number, 0)
            > revelation_limits[volume_number]
        ):
            raise ContractError(
                "採用済みChapter Plan全体の"
                "required_revelationsがVolume Planの"
                "開示予定を超えています"
            )



def _validate_scene_plan_artifacts(
    root: Path,
) -> None:
    """存在する採用済みScene Planを検証する。"""
    plans_root = root / "design/scene-plans"
    entries = sorted(plans_root.iterdir())
    if not entries:
        return

    initial_design_path = (
        root / "design/initial/v0001/initial-design.json"
    )
    series_plan_path = (
        root
        / "design/series-plans"
        / "series-plan-v0001"
        / "series-plan.json"
    )
    if not initial_design_path.is_file():
        raise ContractError(
            "採用済みScene Planには"
            "採用済みInitial Designが必要です"
        )
    if not series_plan_path.is_file():
        raise ContractError(
            "採用済みScene Planには"
            "採用済みSeries Planが必要です"
        )

    brief = _read_json(root / "input/brief.json")
    initial_design = _read_json(initial_design_path)
    series_plan = _read_json(series_plan_path)

    seen_targets: set[tuple[int, int, int]] = set()
    scene_numbers_by_chapter: dict[
        tuple[int, int],
        set[int],
    ] = {}
    revelation_usage: dict[tuple[int, int], int] = {}
    revelation_limits: dict[tuple[int, int], int] = {}

    for directory in entries:
        if not directory.is_dir():
            raise ContractError(
                "Scene Plan version pathは"
                "directoryが必要です"
            )

        plan_path = directory / "scene-plan.json"
        if not plan_path.is_file():
            raise ContractError(
                "Scene Plan version directoryに"
                "scene-plan.jsonがありません"
            )

        plan = _read_json(plan_path)
        volume_number = plan.get("volume_number")
        chapter_number = plan.get("chapter_number")
        scene_number = plan.get("scene_number")
        for number, label in (
            (volume_number, "volume_number"),
            (chapter_number, "chapter_number"),
            (scene_number, "scene_number"),
        ):
            if (
                not isinstance(number, int)
                or isinstance(number, bool)
                or number < 1
            ):
                raise ContractError(
                    f"Scene Planの{label}が不正です"
                )

        expected_directory = (
            f"v{volume_number:02d}"
            f"-c{chapter_number:03d}"
            f"-s{scene_number:03d}-v0001"
        )
        if directory.name != expected_directory:
            raise ContractError(
                "Scene Plan directory名が対象Sceneと"
                "一致しません"
            )

        target = (
            volume_number,
            chapter_number,
            scene_number,
        )
        if target in seen_targets:
            raise ContractError(
                "同じSceneの採用済みPlanが複数あります"
            )
        seen_targets.add(target)

        chapter_key = (
            volume_number,
            chapter_number,
        )
        scene_numbers_by_chapter.setdefault(
            chapter_key,
            set(),
        ).add(scene_number)

        volume_plan_path = (
            root
            / "design/volume-plans"
            / f"v{volume_number:02d}-v0001"
            / "volume-plan.json"
        )
        chapter_plan_path = (
            root
            / "design/chapter-plans"
            / (
                f"v{volume_number:02d}"
                f"-c{chapter_number:03d}-v0001"
            )
            / "chapter-plan.json"
        )
        if not volume_plan_path.is_file():
            raise ContractError(
                "採用済みScene Planには"
                "親Volume Planが必要です"
            )
        if not chapter_plan_path.is_file():
            raise ContractError(
                "採用済みScene Planには"
                "親Chapter Planが必要です"
            )

        volume_plan = _read_json(volume_plan_path)
        chapter_plan = _read_json(chapter_plan_path)

        basis_generation_id = plan.get(
            "basis_generation_id"
        )
        if not isinstance(basis_generation_id, str):
            raise ContractError(
                "Scene Planのbasis_generation_idが不正です"
            )

        generation_root = (
            root / "generations" / basis_generation_id
        )
        if not generation_root.is_dir():
            raise ContractError(
                "Scene Planのbasis Generationが存在しません"
            )

        current_generation = {}
        for name in (
            "canon.json",
            "state.json",
            "evidence.json",
            "commit.json",
        ):
            generation_path = generation_root / name
            if not generation_path.is_file():
                raise ContractError(
                    "Scene Planのbasis Generationが"
                    f"不完全です: {name}"
                )
            current_generation[name] = _read_json(
                generation_path
            )

        from .series_contracts import ContractValidator

        ContractValidator._validate_scene_plan(
            plan,
            brief,
            initial_design,
            series_plan,
            volume_plan,
            chapter_plan,
            current_generation,
            volume_number,
            chapter_number,
            scene_number,
            basis_generation_id,
            adopted=True,
        )

        revelation_limits[chapter_key] = len(
            chapter_plan["required_revelations"]
        )
        revelation_usage[chapter_key] = (
            revelation_usage.get(chapter_key, 0)
            + len(plan["intended_revelations"])
        )

    for chapter_key, scene_numbers in (
        scene_numbers_by_chapter.items()
    ):
        expected = set(
            range(1, max(scene_numbers) + 1)
        )
        if scene_numbers != expected:
            raise ContractError(
                "採用済みScene Planは第一Sceneから"
                "連続して存在しなければなりません"
            )
        if (
            revelation_usage.get(chapter_key, 0)
            > revelation_limits[chapter_key]
        ):
            raise ContractError(
                "採用済みScene Plan全体の"
                "intended_revelationsがChapter Planの"
                "開示予定を超えています"
            )


def _validate_workspace_destination(root: Path) -> None:
    if not root.name or root.name in {".", ".."}:
        raise ContractError(
            "workspace pathが不正です"
        )
    if "\x00" in str(root):
        raise ContractError(
            "workspace pathにNULを含められません"
        )


def _validate_identifier(
    value: object,
    field: str,
    prefix: str,
) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith(prefix)
        or "/" in value
        or "\\" in value
        or ".." in value
        or "\x00" in value
    ):
        raise ContractError(
            f"{field}が安全な{prefix}識別子ではありません"
        )


def _create_directories(root: Path) -> None:
    for relative in REQUIRED_DIRECTORIES:
        (root / relative).mkdir(
            parents=True,
            exist_ok=False,
        )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(
            f"workspace JSONを読めません: {path.name}"
        ) from exc

    if not isinstance(value, dict):
        raise ContractError(
            f"workspace JSONがオブジェクトではありません: {path.name}"
        )
    return value


def _validate_initial_counters(
    counters: dict[str, Any],
) -> None:
    expected = set(INITIAL_COUNTERS) | {"updated_at"}
    if set(counters) != expected:
        raise ContractError(
            "初期countersのfield構成が不正です"
        )

    for field, value in counters.items():
        if field in {"schema_version", "updated_at"}:
            continue
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise ContractError(
                f"初期counterが不正です: {field}"
            )


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _fsync_directory(path: Path) -> None:
    if os.name != "posix":
        return

    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
