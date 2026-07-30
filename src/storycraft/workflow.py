"""v2 run の recovery-first dispatcher。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .publication_recovery import execute_publication_recovery
from .run_state import RunStateStore
from .series_contracts import ContractError
from .volume_publication_stage import VolumePublicationStageService
from .workspace_lock import workspace_lock


class RunUnavailable(ContractError):
    """健全だが未実装の次工程、または停止済み run を示す。"""


def run(workspace_root: Path) -> dict[str, Any]:
    """最初に保存済み確定を収束する。LLMは必要になるまで初期化しない。"""
    root = workspace_root.expanduser()
    with workspace_lock(root):
        store = RunStateStore(root)
        state = store.load()
        if state["status"] == "blocked":
            raise RunUnavailable("blocked workspaceはrunできません")
        if state["status"] == "completed":
            return state
        pending = state["pending_commit"]
        if isinstance(pending, dict):
            if pending.get("kind") != "volume_publication":
                raise RunUnavailable("未移行のpending_commitはrunできません")
            try:
                return execute_publication_recovery(root, state)
            except ContractError as exc:
                blocked = dict(state)
                blocked.update({"status": "blocked", "last_error": {"code": "publication_invalid", "message": str(exc), "evidence_refs": [], "occurred_at": state["updated_at"]}})
                store.save(blocked)
                raise RunUnavailable("publication_invalid") from exc
        if state["current_stage"] == "volume_publication":
            try:
                return VolumePublicationStageService(root).run(updated_at=state["updated_at"])
            except ContractError as exc:
                blocked = dict(state)
                blocked.update({"status": "blocked", "last_error": {"code": "publication_invalid", "message": str(exc), "evidence_refs": [], "occurred_at": state["updated_at"]}})
                store.save(blocked)
                raise RunUnavailable("publication_invalid") from exc

        # ワークスペース検証をLLM初期化前に行う
        from .workspace import validate_workspace
        try:
            validate_workspace(root)
        except ContractError as exc:
            blocked = dict(state)
            blocked.update({"status": "blocked", "last_error": {"code": "workspace_invalid", "message": str(exc), "evidence_refs": [], "occurred_at": state["updated_at"]}})
            store.save(blocked)
            raise RunUnavailable("workspace_invalid") from exc

        # 初期設計以降の工程をディスパッチ
        from .initial_design_stage import InitialDesignStageService
        from .series_plan_stage import SeriesPlanStageService
        from .volume_plan_stage import VolumePlanStageService
        from .chapter_plan_stage import ChapterPlanStageService
        from .scene_plan_stage import ScenePlanStageService
        from .scene_card_stage import SceneCardStageService
        from .scene_prose_stage import SceneProseStageService
        from .scene_continuity_stage import SceneContinuityStageService
        from .scene_commit_stage import SceneCommitStageService
        from .series_model import OpenAIStoryModel
        from .reviewed_candidate_stage import read_json

        # 設定は runtime/settings/settings-000001/record.json の payload に保存されている
        selection_id = state["current_selection_id"]
        selection = read_json(root / "runtime/selections" / selection_id / "record.json")
        settings_id = selection["slots"]["settings"]

        settings_record = read_json(root / "runtime/settings" / settings_id / "record.json")
        payload = settings_record.get("payload", {})

        # Ollama設定をOpenAI互換APIクライアントが期待する形式に変換
        llm_config = {
            "provider": payload.get("provider", "ollama"),
            "base_url": payload.get("endpoint", "http://127.0.0.1:11434"),
            "model": payload.get("model", "qwen3:35b"),
            "thinking": True,
            "stream": True,
            "first_event_timeout_seconds": 3600,
            "idle_timeout_seconds": 600,
            "stream_progress_log_interval_seconds": 60,
        }

        # Settings.llmが期待されるため辞書でラップ
        class SettingsWrapper:
            def __init__(self, llm_dict):
                self.llm = llm_dict

        model = OpenAIStoryModel(SettingsWrapper(llm_config), root / "runtime/raw_logs")

        stage = state["current_stage"]

        if stage == "initial_design":
            service = InitialDesignStageService(root)
            return service.run(model, updated_at=state["updated_at"])
        elif stage == "series_plan":
            service = SeriesPlanStageService(root)
            return service.run(model, updated_at=state["updated_at"])
        elif stage == "volume_plan":
            service = VolumePlanStageService(root)
            return service.run(model, updated_at=state["updated_at"])
        elif stage == "chapter_plan":
            service = ChapterPlanStageService(root)
            return service.run(model, updated_at=state["updated_at"])
        elif stage == "scene_plan":
            service = ScenePlanStageService(root)
            return service.run(model, updated_at=state["updated_at"])
        elif stage == "scene_card":
            service = SceneCardStageService(root)
            return service.run(model, updated_at=state["updated_at"])
        elif stage == "scene_prose":
            service = SceneProseStageService(root)
            return service.run(model, updated_at=state["updated_at"])
        elif stage == "scene_continuity":
            service = SceneContinuityStageService(root)
            return service.run(model, updated_at=state["updated_at"])
        elif stage == "scene_commit":
            service = SceneCommitStageService(root)
            return service.run(updated_at=state["updated_at"])

        raise RunUnavailable(f"このv2工程のdispatcherは未実装です: {stage}")