"""Normalization shared by the public input and persisted-request boundaries."""
from __future__ import annotations

import unicodedata
from typing import Any

from .series_contracts import ContractError


_REQUEST_FIELDS = {
    "title", "genre", "premise", "required_elements", "avoid",
    "ending_preference", "volume_count", "language",
}


def normalize_text(value: object, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ContractError(f"{label}は文字列でなければなりません")
    normalized = unicodedata.normalize("NFC", value.strip())
    if not allow_empty and not normalized:
        raise ContractError(f"{label}は空でない文字列が必要です")
    if any(unicodedata.category(char).startswith("C") for char in normalized):
        raise ContractError(f"{label}に制御文字を含めることはできません")
    return normalized


def normalize_request(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _REQUEST_FIELDS:
        raise ContractError("request schemaが不正です")
    normalized: dict[str, Any] = {
        "title": normalize_text(value.get("title"), "request.title"),
        "premise": normalize_text(value.get("premise"), "request.premise"),
        "ending_preference": normalize_text(value.get("ending_preference"), "request.ending_preference"),
        "language": normalize_text(value.get("language"), "request.language"),
    }
    if normalized["language"] != "ja":
        raise ContractError("request.languageが不正です")
    genre = value.get("genre")
    if not isinstance(genre, list) or not genre:
        raise ContractError("request.genreが不正です")
    normalized["genre"] = [normalize_text(item, "request.genre item") for item in genre]
    required_elements = value.get("required_elements")
    avoid = value.get("avoid")
    for field, items in (("required_elements", required_elements), ("avoid", avoid)):
        if not isinstance(items, list):
            raise ContractError(f"request.{field}が不正です")
        normalized[field] = [normalize_text(item, f"request.{field} item") for item in items]
    count = value.get("volume_count")
    if not isinstance(count, int) or isinstance(count, bool) or not 4 <= count <= 10:
        raise ContractError("request.volume_countが不正です")
    normalized["volume_count"] = count
    for field in ("genre", "required_elements", "avoid"):
        items = normalized[field]
        if len(items) != len(set(items)):
            raise ContractError(f"request.{field}に重複があります")
    return normalized


def normalize_settings(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError("settings schemaが不正です")
    normalized = dict(value)
    for field in ("provider", "endpoint", "model"):
        if field in normalized:
            normalized[field] = normalize_text(normalized[field], f"settings.{field}")
    return normalized
