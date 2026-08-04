"""Recovery-first workflow dispatcher.

The dispatcher is deliberately the only owner of process-wide sequencing: static
workspace validation, generic pending-commit convergence, then the current stage.
Stage services remain the owners of their immutable artifacts and manifests.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .commit_recovery import recover_pending_commit
from .artifact_registry import artifact_spec
from .error_sanitizer import safe_exception_message, sanitize_text
from .filesystem_security import read_text_nofollow
from .ollama import OllamaResponseFormatError
from .run_state import RunStateStore
from .series_contracts import ContractError, LLMCallError
from .workspace import validate_workspace
from .workspace_lock import workspace_lock


class RunUnavailable(ContractError):
    """A run was blocked and is therefore unavailable to the public CLI."""


StageHandler = Callable[[Path, dict[str, Any], Any | None], dict[str, Any]]
HandlerSpec = tuple[bool, StageHandler]


def _default_model_factory(root: Path, state: dict[str, Any]) -> Any:
    """Construct the provider only for an actually runnable LLM stage."""
    selection_id = state["current_selection_id"]
    try:
        if state.get("current_stage") == "request_intake" and selection_id is None:
            settings_directories = [
                path for path in (root / "runtime/settings").iterdir()
                if path.is_dir() and not path.is_symlink()
            ]
            if len(settings_directories) != 1:
                raise ContractError("request_intakeには一つだけのsettingsが必要です")
            settings_id = settings_directories[0].name
        elif isinstance(selection_id, str):
            selection = json.loads(
                read_text_nofollow(root / "runtime/selections" / selection_id / "record.json")
            )
            settings_id = selection["slots"]["settings"]
        else:
            raise ContractError("LLM stageにはcurrent selectionが必要です")
        payload = json.loads(
            read_text_nofollow(root / "runtime/settings" / settings_id / "record.json")
        )["payload"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ContractError("current selectionのsettingsを読めません") from exc
    if not isinstance(payload, dict):
        raise ContractError("settings payloadが不正です")
    from .series_model import OpenAIStoryModel

    try:
        return OpenAIStoryModel(_model_settings_from_payload(payload, settings_id), root / "runtime/raw_logs", workspace_root=root)
    except ContractError as exc:
        # The canonical settings payload has already passed static workspace validation.  A failure
        # while constructing the provider is therefore a transport failure,
        # not an authority inconsistency in the immutable workspace.
        raise LLMCallError("LLM provider initialization failed") from exc


def _model_settings_from_payload(payload: dict[str, Any], settings_id: str) -> Any:
    """Adapt immutable settings at the provider boundary."""
    artifact_spec("settings").match_id(settings_id)
    class ProviderRuntimeConfiguration:
        def __init__(self, llm: dict[str, Any], retry: dict[str, Any], settings_id: str) -> None:
            self.llm = llm
            self.retry = retry
            self.settings_id = settings_id

    try:
        return ProviderRuntimeConfiguration(
            {
                "provider": payload["provider"],
                "base_url": payload["endpoint"],
                "model": payload["model"],
                "thinking": True,
                "stream": False,
                "first_event_timeout_seconds": 3600,
                "idle_timeout_seconds": 600,
                "stream_progress_log_interval_seconds": 60,
                "invalid_response_limit": payload["invalid_response_limit"],
                "request_options": payload.get("request_options"),
                "ollama_http_boundary": True,
            },
            {"max_attempts": payload["technical_retry_limit"]},
            settings_id,
        )
    except KeyError as exc:
        raise ContractError("settings payloadにprovider設定がありません") from exc


def _request_intake(root: Path, state: dict[str, Any], model: Any | None) -> dict[str, Any]:
    from .request_intake_stage import create_request_intake_stage_service

    return create_request_intake_stage_service(root).run(
        model, workspace_already_validated=True, updated_at=state["updated_at"],
    )


def _planning_handler(module: str, factory: str) -> StageHandler:
    """Adapt a selection-based planning service without alternate dispatch."""
    def handler(root: Path, state: dict[str, Any], model: Any | None) -> dict[str, Any]:
        imported = __import__(f"storycraft.{module}", fromlist=[factory])
        return getattr(imported, factory)(root).run(
            model, workspace_already_validated=True, updated_at=state["updated_at"],
        )
    return handler


def _initial_design(root: Path, state: dict[str, Any], model: Any | None) -> dict[str, Any]:
    from .initial_design_stage import create_initial_design_stage_service

    return create_initial_design_stage_service(root).run(
        model, workspace_already_validated=True, updated_at=state["updated_at"],
    )


def _scene_commit(root: Path, state: dict[str, Any], model: Any | None) -> dict[str, Any]:
    from .scene_commit_stage import create_scene_commit_stage_service

    return create_scene_commit_stage_service(root).run(
        model, workspace_already_validated=True, updated_at=state["updated_at"],
    )


def _volume_publication(root: Path, state: dict[str, Any], model: Any | None) -> dict[str, Any]:
    from .volume_publication_stage import create_volume_publication_stage_service

    return create_volume_publication_stage_service(root).run(
        model, workspace_already_validated=True, updated_at=state["updated_at"],
    )


def _unavailable(stage: str) -> StageHandler:
    def handler(root: Path, state: dict[str, Any], model: Any | None) -> dict[str, Any]:
        del root, state, model
        raise ContractError(f"current handler is not available for {stage}")
    return handler


def _default_handlers() -> dict[str, HandlerSpec]:
    # Do not route immutable state through active-candidate services.  Every stage
    # must consume its declared selection inputs or fail closed.
    return {
        "request_intake": (True, _request_intake),
        "initial_design": (True, _initial_design),
        "series_plan": (True, _planning_handler("series_plan_stage", "create_series_plan_stage_service")),
        "volume_plan": (True, _planning_handler("volume_plan_stage", "create_volume_plan_stage_service")),
        "chapter_plan": (True, _planning_handler("chapter_plan_stage", "create_chapter_plan_stage_service")),
        "scene_plan": (True, _planning_handler("scene_plan_stage", "create_scene_plan_stage_service")),
        "scene_card": (True, _planning_handler("scene_card_stage", "create_scene_card_stage_service")),
        "scene_prose": (True, _planning_handler("scene_prose_stage", "create_scene_prose_stage_service")),
        "scene_continuity": (True, _planning_handler("scene_continuity_stage", "create_scene_continuity_stage_service")),
        "scene_commit": (False, _scene_commit),
        "volume_publication": (False, _volume_publication),
    }


def _block(store: RunStateStore, state: dict[str, Any], code: str, message: str) -> None:
    blocked = dict(state)
    blocked.update({
        "status": "blocked",
        "last_error": {
            "code": code,
            "message": sanitize_text(message),
            "evidence_refs": [],
            "occurred_at": state["updated_at"],
        },
    })
    store.save(blocked)


def _stage_error_code(stage: object, error: BaseException) -> str:
    from .candidate_stage import InvalidResponseLimitError

    if isinstance(error, InvalidResponseLimitError):
        return "invalid_response_limit"
    if isinstance(error, OllamaResponseFormatError):
        return "invalid_response_limit"
    if isinstance(error, LLMCallError):
        return "technical_retry_exhausted"
    if stage == "volume_publication" and isinstance(error, ContractError):
        return "publication_invalid"
    if isinstance(error, ContractError):
        return "authority_inconsistency"
    return "internal_error"


def run(
    workspace_root: Path,
    *,
    handlers: Mapping[str, HandlerSpec] | None = None,
    model_factory: Callable[[Path, dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Run stages until the run completes or an error is persisted as blocked.

    Static validation and generic recovery always precede model construction.  The
    optional injected dependencies keep dispatcher tests provider-free and permit
    stage adapters to be introduced without creating a second state format.
    """
    root = workspace_root.expanduser()
    selected_handlers = dict(_default_handlers() if handlers is None else handlers)
    create_model = model_factory or _default_model_factory
    with workspace_lock(root):
        store = RunStateStore(root)
        state = store.load()
        if state["status"] == "blocked":
            raise RunUnavailable("blocked")
        try:
            validate_workspace(root)
        except ContractError as exc:
            if state["status"] == "completed":
                raise RunUnavailable("authority_inconsistency") from exc
            code = _stage_error_code(state.get("current_stage"), exc)
            _block(store, state, code, safe_exception_message(exc))
            raise RunUnavailable(code) from exc
        if state["status"] == "completed":
            return state

        while True:
            if state["status"] == "completed":
                return state
            if state["status"] == "blocked":
                raise RunUnavailable("blocked")
            if state["pending_commit"] is not None:
                pending_kind = state["pending_commit"].get("kind") if isinstance(state["pending_commit"], dict) else None
                try:
                    state = recover_pending_commit(root)
                except Exception as exc:
                    code = _stage_error_code(pending_kind, exc)
                    _block(store, state, code, safe_exception_message(exc))
                    raise RunUnavailable(code) from exc
                if state["status"] == "completed":
                    return state
                continue

            stage = state["current_stage"]
            specification = selected_handlers.get(stage) if isinstance(stage, str) else None
            if specification is None:
                _block(store, state, "authority_inconsistency", f"current handler is not available for {stage}")
                raise RunUnavailable("authority_inconsistency")
            needs_model, handler = specification
            try:
                model = create_model(root, state) if needs_model else None
                result = handler(root, state, model)
            except Exception as exc:
                code = _stage_error_code(stage, exc)
                _block(store, state, code, safe_exception_message(exc))
                raise RunUnavailable(code) from exc
            if not isinstance(result, dict):
                _block(store, state, "internal_error", "stage handler did not return run-state")
                raise RunUnavailable("internal_error")
            if result["status"] == "completed":
                return result
            if result == state:
                _block(store, state, "internal_error", "stage handler made no run-state progress")
                raise RunUnavailable("internal_error")
            state = result
