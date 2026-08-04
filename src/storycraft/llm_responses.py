"""Closed-schema validation for CandidateResponse and ReviewResponse."""
from __future__ import annotations
from typing import Any
from .artifact_registry import artifact_spec
from .series_contracts import ContractError

def candidate_response(value: object, expected_kind: str) -> dict[str, Any]:
    artifact_spec(expected_kind)
    if not isinstance(value, dict) or set(value) != {"schema_version", "artifact_kind", "payload"}:
        raise ContractError("CandidateResponseのfield構成が不正です")
    if value["schema_version"] != "candidate-response-v1" or value["artifact_kind"] != expected_kind or not isinstance(value["payload"], dict):
        raise ContractError("CandidateResponseが期待種別と一致しません")
    return value

def review_response(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "decision", "issues"}:
        raise ContractError("ReviewResponseのfield構成が不正です")
    if value["schema_version"] != "review-response-v1" or value["decision"] not in {"pass", "issues"} or not isinstance(value["issues"], list):
        raise ContractError("ReviewResponseが不正です")
    if (value["decision"] == "pass") != (not value["issues"]):
        raise ContractError("ReviewResponseのdecisionとissuesが一致しません")
    return value
