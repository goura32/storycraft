"""Minimal V2 Ollama boundary; no stage or workspace mutation occurs here."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any, Optional

from .series_contracts import ContractError


class OllamaTechnicalError(ContractError):
    pass


def _fetch_model_info(endpoint: str, model: str) -> dict[str, Any]:
    """GET /v1/models/{model} でモデル情報を取得し、最大コンテキストを抽出する。"""
    url = endpoint.rstrip("/") + f"/v1/models/{model}"
    try:
        with urlopen(Request(url, method="GET"), timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
        raise OllamaTechnicalError("Ollamaモデル情報取得に失敗しました") from exc
    if not isinstance(data, dict):
        raise ContractError("Ollamaモデル情報が不正です")
    return data


def _resolve_num_ctx(model_info: dict[str, Any], request_options: Optional[dict[str, Any]]) -> int:
    """max_input_chars は不要。モデル情報から最大コンテキストを取得し、num_ctx を決定する。"""
    # request_options に num_ctx が指定されていればそれを優先
    if request_options and isinstance(request_options.get("num_ctx"), int):
        return request_options["num_ctx"]
    # モデル情報から context_length または max_context を取得
    context_length = model_info.get("context_length") or model_info.get("max_context")
    if isinstance(context_length, int) and context_length > 0:
        return context_length
    # デフォルト値（Ollamaの既定値 2048 相当を採用）
    return 2048


def generate(
    endpoint: str,
    model: str,
    prompt: str,
    schema: dict[str, Any],
    *,
    request_options: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Ollama に構造化出力で生成を依頼する。
    - think: true を常に有効化
    - options.num_ctx はモデル情報または request_options から決定
    - 未指定の request_options は送らない（Ollama既定値を使用）
    """
    # モデル情報を取得して num_ctx を決定
    model_info = _fetch_model_info(endpoint, model)
    num_ctx = _resolve_num_ctx(model_info, request_options)

    # options を構築（num_ctx のみ明示指定、他は送らない）
    options = {"num_ctx": num_ctx}
    if request_options:
        # num_ctx 以外の request_options も転送（ただし None は除外）
        for key, value in request_options.items():
            if key != "num_ctx" and value is not None:
                options[key] = value

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "storycraft_response", "strict": True, "schema": schema}},
        "think": True,
        "stream": False,
        "options": options,
    }, ensure_ascii=False).encode()

    request = Request(
        endpoint.rstrip("/") + "/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
    except (HTTPError, URLError, OSError) as exc:
        raise OllamaTechnicalError("Ollama呼出しに失敗しました") from exc
    try:
        envelope = json.loads(raw.decode("utf-8"))
        value = json.loads(envelope["choices"][0]["message"]["content"])
    except (UnicodeDecodeError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ContractError("Ollama応答JSONが不正です") from exc
    if not isinstance(value, dict):
        raise ContractError("Ollama応答はobjectでなければなりません")
    return value