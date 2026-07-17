"""公開シリーズ生成サービス。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .series_contracts import ContractError, RunResult, StoryModel
from .series_store import StateStore
from .series_workflow import SeriesWorkflow


class SeriesService(SeriesWorkflow):
    """ワークスペースをロックしてシリーズ工程を公開操作として実行する。"""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.store = StateStore(workspace)

    def run(self, brief: dict[str, Any] | None, model: StoryModel, *, keywords: list[str] | None = None, stop_after_scene: str | None = None) -> RunResult:
        with self.store.lock():
            if self.store.exists():
                raise ContractError("この作業場所には保存済みシリーズがあります。resume を使ってください")
            state = self._new_state(brief, keywords=keywords)
            self.store.save(state)
            return self._advance(state, model, stop_after_scene=stop_after_scene)

    def resume(self, model: StoryModel) -> RunResult:
        with self.store.lock():
            return self._advance(self.store.load(), model)

    def step(self, model: StoryModel, brief: dict[str, Any] | None = None, *, keywords: list[str] | None = None) -> RunResult:
        with self.store.lock():
            if not self.store.exists():
                if (brief is None) == (keywords is None):
                    raise ContractError("初回の step には企画またはkeywordsのどちらか一方が必要です")
                state = self._new_state(brief, keywords=keywords)
                self.store.save(state)
            else:
                state = self.store.load()
            if state["completed"]:
                return self._result(state, self._volume_paths())
            self._run_one(state, model)
            self.store.save(state)
            return self._result(state)
