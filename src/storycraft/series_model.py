"""Storycraft V1のOpenAI互換JSON Model実装。"""
from __future__ import annotations

import json
from typing import Any

from .log import logger
from .llm import LLMClient
from .ollama import OllamaResponseFormatError
from .series_contracts import ContractError, LLMCallError
from .prompt_template import get_template_loader
from .stages import ACTIVE_TEMPLATE_STAGES


class OpenAIStoryModel:
    """Jinjaテンプレートと工程別外部スキーマから実送信プロンプトを構築する。"""

    def __init__(self, settings, raw_dir) -> None:
        self.client = LLMClient(settings, raw_dir)
        self._seed_sequence = 0
        self._format_attempt = 1

    def set_log_ref(self, ref: str) -> None:
        """Workflowから受け取る対象座標。prompt本文には含めない。"""
        self._log_ref = ref

    def set_log_quality_pass(self, quality_pass: str = "") -> None:
        """品質ループ回次。LLM通信retryとは別の運用ログ用メタデータ。"""
        self._log_quality_pass = quality_pass

    def set_call_context(
        self,
        *,
        settings_id: str,
        input_refs: list[str],
        target_candidate_id: str | None = None,
    ) -> None:
        """Bind the next V2 operation to immutable workspace provenance."""
        self._call_context = {
            "settings_id": settings_id,
            "input_refs": list(input_refs),
            "target_candidate_id": target_candidate_id,
        }
        self._format_attempt = 1

    def begin_format_attempt(self) -> None:
        """Advance the structural retry axis; transport retries stay unchanged."""
        self._format_attempt = getattr(self, "_format_attempt", 1) + 1

    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        return self._call("generate", stage, self._render("generate", stage, context=context))

    def critique(self, stage: str, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return self._call("critique", stage, self._render("critique", stage, candidate=candidate, context=context))

    def revision(self, stage: str, candidate: dict[str, Any], critique: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        # Keep the legacy method name as an alias to the canonical V2 operation.
        return self.revise(stage, context, candidate, critique)

    # CandidateStage is the public V2 workflow surface.  Keep the older names for
    # V1 callers, but make the V2 protocol explicit rather than asking adapters to
    # probe for legacy methods.
    def review(self, stage: str, context: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        return self._call("review", stage, self._render("review", stage, candidate=candidate, context=context))

    def revise(self, stage: str, context: dict[str, Any], candidate: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
        return self._call("revise", stage, self._render("revise", stage, candidate=candidate, critique=review, context=context))

    def generate_prose(
        self,
        stage: str,
        context: dict[str, Any],
    ) -> str:
        return self._call_text(
            "generate",
            stage,
            self._render("generate", stage, context=context),
            invalid_limit=1,
        )

    def critique_prose(
        self,
        stage: str,
        candidate: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        return self._call(
            "review",
            stage,
            self._render(
                "critique",
                stage,
                candidate=candidate,
                context=context,
            ),
        )

    def revision_prose(
        self,
        stage: str,
        candidate: str,
        critique: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        return self._call_text(
            "revise",
            stage,
            self._render(
                "revise",
                stage,
                candidate=candidate,
                critique=critique,
                context=context,
            ),
            invalid_limit=1,
        )

    @staticmethod
    def _render(kind: str, stage: str, **kwargs: Any) -> str:
        if stage not in ACTIVE_TEMPLATE_STAGES:
            raise ContractError(f"未知の生成工程です: {stage}")
        loader = get_template_loader()
        template_kind = {
            "review": "critique",
            "revise": "fix",
            "revision": "fix",
        }.get(kind, kind)
        schema_kind = "revise" if kind == "revision" else kind
        output_schema = json.dumps(OpenAIStoryModel._response_schema(schema_kind, stage), ensure_ascii=False, indent=2)
        return loader.render_user(template_kind, stage, output_schema=output_schema, **kwargs)

    def render_system(self, response_mode: str = "json") -> str:
        """応答形式に対応するシステムプロンプトを描画する。"""
        loader = get_template_loader()
        return loader.render_system(response_mode=response_mode)

    @staticmethod
    def _response_schema(kind: str, stage: str) -> dict[str, Any]:
        if kind in {"generate", "revise"}:
            payload_schema = get_template_loader().load_schema_object("generate", stage)
            artifact_kind = {
                "request_intake": "request",
                "scene_continuity": "continuity-update",
            }.get(stage, stage.replace("_", "-"))
            return {
                "type": "object", "additionalProperties": False,
                "required": ["schema_version", "artifact_kind", "payload"],
                "properties": {
                    "schema_version": {"const": "candidate-response-v1"},
                    "artifact_kind": {"const": artifact_kind},
                    "payload": payload_schema,
                },
            }
        if kind in {"review", "critique"}:
            return get_template_loader().load_schema_object("critique", stage)
        return get_template_loader().load_schema_object(kind, stage)

    @staticmethod
    def _safe_error_type(error: str) -> str:
        """標準ログには接続先由来のエラー本文を出さない。"""
        raw_type = error.split(":", 1)[0]
        safe_type = "".join(char if char.isalnum() or char in "._-" else "_" for char in raw_type)
        return safe_type[:80] or "unknown"

    @staticmethod
    def _response_format(
        kind: str,
        stage: str,
    ) -> dict[str, Any]:
        """工程に応じたOpenAI互換response formatを返す。"""
        schema = OpenAIStoryModel._response_schema(kind, stage)

        return {
            "type": "json_schema",
            "json_schema": {
                "name": (
                    f"storycraft_{kind}_{stage}"
                ),
                "strict": True,
                "schema": schema,
            },
        }

    def _call(self, kind: str, stage: str, user_prompt: str) -> dict[str, Any]:
        failure_reason = "unknown"
        attempts = max(int(self.client.settings.retry.get("max_attempts", 1)), 1)
        ref = getattr(self, "_log_ref", stage)
        format_attempt = getattr(self, "_format_attempt", 1)
        response_format = self._response_format(
            kind,
            stage,
        )

        for retry_attempt in range(1, attempts + 1):
            # V2 records model discovery and completion as two physical calls.
            # Reserve a distinct monotonic seed for each physical call record.
            llm_settings = getattr(self.client.settings, "llm", {})
            seed_step = 2 if llm_settings.get("v2_openai_ollama", False) else 1
            seed = getattr(self, "_seed_sequence", 0) + 1
            self._seed_sequence = seed + seed_step - 1
            messages = [
                {"role": "system", "content": self.render_system("json")},
                {"role": "user", "content": user_prompt},
                {
                    "__kind": kind, "__phase": stage, "__ref": ref,
                    "__attempt": retry_attempt, "__retry_total": attempts,
                    "__format_attempt": format_attempt,
                    "__quality_pass": getattr(self, "_log_quality_pass", ""),
                    **getattr(self, "_call_context", {}),
                },
            ]
            record = self.client.call_once(
                messages,
                response_format,
                seed,
            )
            self.client.save_raw(record, messages)
            self.last_call_id = getattr(record, "call_id", None)
            if record.error:
                failure_reason = f"transport:{self._safe_error_type(record.error)}"
                logger.error(
                    "LLM通信エラー: stage=%s kind=%s attempt=%s/%s error_type=%s",
                    stage, kind, retry_attempt, attempts, self._safe_error_type(record.error),
                )
                continue
            try:
                value = json.loads(record.content)
            except json.JSONDecodeError as exc:
                # Structural retries belong to the candidate operation, where the
                # immutable invalid_response_limit is available; this is not a
                # transport/technical exhaustion.
                raise ContractError(f"{stage} のLLM応答JSONが不正です") from exc
            if isinstance(value, dict):
                return value
            raise ContractError(f"{stage} のLLM応答はobjectでなければなりません")
        raise LLMCallError(f"{stage} のLLM呼び出しに失敗しました: reason={failure_reason}")

    def _call_text(
        self,
        kind: str,
        stage: str,
        user_prompt: str,
        *,
        invalid_limit: int | None = None,
    ) -> str:
        attempts = max(int(self.client.settings.retry.get("max_attempts", 1)), 1)
        if invalid_limit is None:
            invalid_limit = max(int(self.client.settings.llm.get("invalid_response_limit", 5)), 1)
        elif not isinstance(invalid_limit, int) or isinstance(invalid_limit, bool) or invalid_limit < 1:
            raise ContractError("本文invalid_response_limitが不正です")
        ref = getattr(self, "_log_ref", stage)
        for local_format_attempt in range(1, invalid_limit + 1):
            if local_format_attempt > 1:
                self.begin_format_attempt()
            format_attempt = getattr(self, "_format_attempt", local_format_attempt)
            format_failed = False
            for retry_attempt in range(1, attempts + 1):
                self._seed_sequence = getattr(self, "_seed_sequence", 0) + 1
                seed = self._seed_sequence
                messages = [
                    {"role": "system", "content": self.render_system("prose")},
                    {"role": "user", "content": user_prompt},
                    {
                        "__kind": kind,
                        "__phase": stage,
                        "__ref": ref,
                        "__attempt": retry_attempt,
                        "__retry_total": attempts,
                        "__format_attempt": format_attempt,
                        "__quality_pass": getattr(self, "_log_quality_pass", ""),
                        **getattr(self, "_call_context", {}),
                    },
                ]
                try:
                    record = self.client.call_once(messages, None, seed)
                except OllamaResponseFormatError:
                    format_failed = True
                    break
                self.last_call_id = record.call_id
                self.client.save_raw(record, messages)
                if record.error:
                    logger.error(
                        "LLM通信エラー: stage=%s kind=%s attempt=%s/%s error_type=%s",
                        stage, kind, retry_attempt, attempts, self._safe_error_type(record.error),
                    )
                    continue
                value = record.content.strip()
                if value:
                    return value
                format_failed = True
                logger.error(
                    "LLM本文形式エラー: stage=%s kind=%s attempt=%s/%s reason=empty_text",
                    stage, kind, retry_attempt, attempts,
                )
                break
            if format_failed:
                continue
            raise LLMCallError(
                f"{stage} のLLM本文呼び出しに失敗しました: reason=technical_retry_exhausted"
            )
        raise OllamaResponseFormatError(f"{stage} のLLM本文がinvalid_response_limitまで不正です")
