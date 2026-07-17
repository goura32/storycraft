"""次世代実行系のOpenAI互換JSONモデル。"""
from __future__ import annotations

import json
from typing import Any

from .llm import LLMClient
from .series_engine import ContractError
from .prompt_template import get_template_loader


_STAGES = {
    "brief", "characters", "relationships", "world", "timeline", "threads", "volume_map",
    "volume_chapters", "scene_card", "scene", "continuity", "volume_summary", "closure",
}


class OpenAIStoryModel:
    """Jinjaテンプレートと工程別外部スキーマから実送信プロンプトを構築する。"""

    def __init__(self, settings, raw_dir) -> None:
        self.client = LLMClient(settings, raw_dir)
        self.attempt = 0

    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        return self._call("generate", stage, self._render("generate", stage, context=context))

    def critique(self, stage: str, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return self._call("critique", stage, self._render("critique", stage, candidate=candidate, context=context))

    def revision(self, stage: str, candidate: dict[str, Any], critique: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return self._call("revision", stage, self._render("revision", stage, candidate=candidate, critique=critique, context=context))

    @staticmethod
    def _render(kind: str, stage: str, **kwargs: Any) -> str:
        if stage not in _STAGES:
            raise ContractError(f"未知の生成工程です: {stage}")
        loader = get_template_loader()
        output_schema = loader.load_schema_text(kind, stage)
        if kind == "generate":
            return loader.render_user("generate", stage, stage=stage, output_schema=output_schema, **kwargs)
        candidate_schema = loader.load_schema_text("generate", stage)
        return loader.render_user(kind, stage, stage=stage, output_schema=output_schema, candidate_schema=candidate_schema, **kwargs)

    def _call(self, kind: str, stage: str, user_prompt: str) -> dict[str, Any]:
        last_error = ""
        attempts = int(self.client.settings.retry.get("max_attempts", 1))
        for _ in range(max(attempts, 1)):
            self.attempt += 1
            messages = [
                {"role": "system", "content": get_template_loader().render_system()},
                {"role": "user", "content": user_prompt},
                {"__kind": kind, "__phase": stage, "__ref": stage, "__attempt": self.attempt},
            ]
            record = self.client.call_once(messages, {"type": "json_object"}, self.attempt)
            self.client.save_raw(record, messages)
            if record.error:
                last_error = record.error
                continue
            try:
                value = json.loads(record.content)
            except json.JSONDecodeError:
                last_error = "JSONを返しませんでした"
                continue
            if isinstance(value, dict):
                return value
            last_error = "JSONオブジェクトを返しませんでした"
        raise ContractError(f"{stage} の生成に失敗しました: {last_error}")
