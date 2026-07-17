"""次世代実行系のOpenAI互換JSONモデル。"""
from __future__ import annotations

import json
from typing import Any

from .llm import LLMClient
from .nextgen import ContractError
from .prompt_template import get_template_loader


_TEMPLATE_STAGE = {
    "plan": "plan",
    "scene_card": "scene_cards",
    "scene": "scene_write",
    "closure": "closure_check",
}


class OpenAIStoryModel:
    """Jinjaテンプレートから実送信プロンプトを構築する次世代モデル。"""

    def __init__(self, settings, raw_dir) -> None:
        self.client = LLMClient(settings, raw_dir)
        self.attempt = 0

    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        return self._call("generate", stage, self._render("generate", stage, **context))

    def critique(self, stage: str, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return self._call("critique", stage, self._render("critique", stage, candidate=candidate, context=context))

    def revise(
        self,
        stage: str,
        candidate: dict[str, Any],
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._call(
            "revise",
            stage,
            self._render("fix", stage, candidate=candidate, critique=critique, context=context),
        )

    @staticmethod
    def _render(kind: str, stage: str, **kwargs: Any) -> str:
        try:
            template_stage = _TEMPLATE_STAGE[stage]
        except KeyError as exc:
            raise ContractError(f"未知の生成工程です: {stage}") from exc
        return get_template_loader().render_user(kind, template_stage, **kwargs)

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
