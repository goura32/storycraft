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
    other_name = (
        "keywords.json"
        if source_type == "brief"
        else "brief.json"
    )
    other = root / "input" / other_name

    if not selected.is_file():
        raise ContractError(
            f"workspace入力fileがありません: {expected_path}"
        )
    if other.exists():
        raise ContractError(
            "workspaceにはBriefとKeywordsの両方を保存できません"
        )

    payload = _read_json(selected)
    if source_type == "brief":
        _validate_brief(payload)
    else:
        _validate_keywords(payload)


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
