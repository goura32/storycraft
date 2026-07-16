"""次世代実行系のOpenAI互換JSONモデル。"""
from __future__ import annotations

import json
from typing import Any

from .llm import LLMClient
from .nextgen import ContractError


class OpenAIStoryModel:
    """既存の接続設定を使い、次世代の工程契約だけをLLMへ渡す。"""

    def __init__(self, settings, raw_dir) -> None:
        self.client = LLMClient(settings, raw_dir)
        self.attempt = 0

    def generate(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        instruction = {
            "plan": "全巻計画を作る。volumes は巻番号、巻題、chapters、巻ごとの変化、最終巻以外の未解決の問いを持つ。",
            "scene_card": "一つの場面カードを作る。scene_id を変えず、visible_thread_ids と allowed_update_ids は提示されたIDだけを使う。",
            "scene": "場面本文、引継ぎ要約、状態更新を作る。状態更新は場面カードが許可したIDだけを使う。",
            "closure": "主要な問いが全て回収済みかと、結末が到達したかを判定する。",
        }.get(stage)
        if instruction is None:
            raise ContractError(f"未知の生成工程です: {stage}")
        return self._call("generate", stage, instruction, context)

    def critique(self, stage: str, candidate: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return self._call(
            "critique",
            stage,
            "候補が入力契約、場面カード、台帳状態、結末条件を守るか批評する。issues は問題の配列にする。",
            {"candidate": candidate, "context": context},
        )

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
            "批評を反映して候補を修正する。元の必須情報とIDを失わず、修正版JSONだけを返す。",
            {"candidate": candidate, "critique": critique, "context": context},
        )

    def _call(self, kind: str, stage: str, instruction: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error = ""
        attempts = int(self.client.settings.retry.get("max_attempts", 1))
        for _ in range(max(attempts, 1)):
            self.attempt += 1
            messages = [
                {"role": "system", "content": "あなたはStorycraftの小説生成工程です。JSONオブジェクトだけを返してください。"},
                {
                    "role": "user",
                    "content": f"{instruction}\n\n入力:\n{json.dumps(payload, ensure_ascii=False)}",
                },
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
