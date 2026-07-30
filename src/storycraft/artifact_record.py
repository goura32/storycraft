"""Deterministic V2 artifact record validation before an artifact gains authority."""
from __future__ import annotations

from typing import Any

from .artifact_registry import artifact_spec
from .series_contracts import ContractError


def validate_record(artifact_kind: str, artifact_id: str, record: object) -> dict[str, Any]:
    """Validate the record envelope appropriate for an immutable V2 artifact."""
    artifact_spec(artifact_kind).match_id(artifact_id)
    if not isinstance(record, dict):
        raise ContractError("record.jsonはobjectでなければなりません")
    if artifact_kind == "settings":
        _require(record, {"schema_version", "settings_id", "payload", "created_at"})
        _equal(record, "settings_id", artifact_id)
    elif artifact_kind == "keywords":
        _require(record, {"schema_version", "keywords_id", "keywords", "language", "created_at"})
        _equal(record, "keywords_id", artifact_id)
    elif artifact_kind == "quality-disposition":
        _require(record, {"schema_version", "quality_id", "candidate_id", "adoption_record_id", "review_record_ids", "revision_count", "result", "remaining_major_issues", "notice_type", "created_at"})
        _equal(record, "quality_id", artifact_id)
    elif artifact_kind == "request":
        _require(record, {"schema_version", "request_id", "payload", "created_at"})
        _equal(record, "request_id", artifact_id)
    else:
        _require(record, {"schema_version", "artifact_id", "artifact_kind", "selection_id", "created_at", "content"})
        _equal(record, "artifact_id", artifact_id)
        _equal(record, "artifact_kind", artifact_kind)
    if record.get("schema_version") != 1:
        raise ContractError("record.jsonのschema_versionが不正です")
    return record


def _require(record: dict[str, Any], keys: set[str]) -> None:
    if set(record) != keys:
        raise ContractError("record.jsonのfield構成が不正です")


def _equal(record: dict[str, Any], key: str, expected: str) -> None:
    if record.get(key) != expected:
        raise ContractError(f"record.jsonの{key}が配置IDと一致しません")
