"""次世代実行系のOpenAI互換JSONモデル。"""
from __future__ import annotations

import json
from typing import Any

from .log import logger
from .llm import LLMClient
from .series_contracts import ContractError, LLMCallError
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
        if kind == "critique":
            return loader.render_user(kind, stage, stage=stage, output_schema=output_schema, **kwargs)
        return loader.render_user(kind, stage, stage=stage, output_schema=output_schema, **kwargs)

    @staticmethod
    def _safe_error_type(error: str) -> str:
        """標準ログには接続先由来のエラー本文を出さない。"""
        raw_type = error.split(":", 1)[0]
        safe_type = "".join(char if char.isalnum() or char in "._-" else "_" for char in raw_type)
        return safe_type[:80] or "unknown"

    def _call(self, kind: str, stage: str, user_prompt: str) -> dict[str, Any]:
        failure_reason = "unknown"
        attempts = max(int(self.client.settings.retry.get("max_attempts", 1)), 1)
        for retry_attempt in range(1, attempts + 1):
            self.attempt += 1
            messages = [
                {"role": "system", "content": get_template_loader().render_system()},
                {"role": "user", "content": user_prompt},
                {"__kind": kind, "__phase": stage, "__ref": stage, "__attempt": self.attempt},
            ]
            record = self.client.call_once(messages, {"type": "json_object"}, self.attempt)
            self.client.save_raw(record, messages)
            if record.error:
                failure_reason = f"transport:{self._safe_error_type(record.error)}"
                logger.error(
                    "LLM通信エラー: stage=%s kind=%s attempt=%s/%s global_attempt=%s error_type=%s",
                    stage, kind, retry_attempt, attempts, self.attempt, self._safe_error_type(record.error),
                )
                continue
            try:
                value = json.loads(record.content)
            except json.JSONDecodeError as exc:
                failure_reason = "json_decode_error"
                logger.error(
                    "LLM JSONパースエラー: stage=%s kind=%s attempt=%s/%s global_attempt=%s error=%s",
                    stage, kind, retry_attempt, attempts, self.attempt, exc,
                )
                continue
            if isinstance(value, dict):
                return value
            failure_reason = "json_non_object"
            logger.error(
                "LLM JSON形式エラー: stage=%s kind=%s attempt=%s/%s global_attempt=%s actual=%s",
                stage, kind, retry_attempt, attempts, self.attempt, type(value).__name__,
            )
        raise LLMCallError(f"{stage} のLLM呼び出しに失敗しました: reason={failure_reason}")
