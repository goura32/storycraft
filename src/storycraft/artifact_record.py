"""Deterministic V2 artifact record-envelope validation."""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from .artifact_registry import artifact_spec
from .series_contracts import ContractError


_CONTENT_KINDS = frozenset({
    "request", "initial-design", "series-plan", "volume-plan", "chapter-plan",
    "scene-plan", "scene-card", "scene-prose", "continuity-update", "generation", "scene",
})
_AUDIT_ID_PATTERNS = {
    "candidate": re.compile(r"candidate-(?P<counter>[0-9]{6})"),
    "review": re.compile(r"review-(?P<counter>[0-9]{6})"),
    "call": re.compile(r"call-(?P<counter>[0-9]{6})"),
}


def validate_record(artifact_kind: str, artifact_id: str, record: object) -> dict[str, Any]:
    """Validate one immutable record's own closed envelope, not its input bundle."""
    artifact_spec(artifact_kind).match_id(artifact_id)
    if not isinstance(record, dict):
        raise ContractError("record.jsonはobjectでなければなりません")
    if artifact_kind in _CONTENT_KINDS:
        _require(record, {"schema_version", "artifact_id", "artifact_kind", "input_selection_id", "created_at", "content"})
        _equal(record, "artifact_id", artifact_id)
        _equal(record, "artifact_kind", artifact_kind)
        input_selection_id = record["input_selection_id"]
        if artifact_kind == "request":
            if input_selection_id is not None and not _selection_id(input_selection_id):
                raise ContractError("record.jsonのinput_selection_idが不正です")
        elif not _selection_id(input_selection_id):
            raise ContractError("record.jsonのinput_selection_idが不正です")
        if not isinstance(record["content"], dict):
            raise ContractError("record.jsonのcontentはobjectでなければなりません")
    elif artifact_kind == "settings":
        _require(record, {"schema_version", "settings_id", "payload", "created_at"})
        _equal(record, "settings_id", artifact_id)
    elif artifact_kind == "keywords":
        _require(record, {"schema_version", "keywords_id", "keywords", "language", "created_at"})
        _equal(record, "keywords_id", artifact_id)
    elif artifact_kind == "quality-disposition":
        _validate_quality_disposition(record, artifact_id)
    elif artifact_kind == "adoption":
        _validate_adoption(record, artifact_id)
    elif artifact_kind == "scene-commit":
        _validate_scene_commit(record, artifact_id)
    else:
        raise ContractError("このartifact_kindのrecord形式は未定義です")
    if record.get("schema_version") != 1:
        raise ContractError("record.jsonのschema_versionが不正です")
    _timestamp(record.get("created_at"))
    return record


def validate_candidate_record(candidate_id: str, record: object) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ContractError("candidate recordはobjectでなければなりません")
    if not _canonical_audit_id("candidate", candidate_id):
        raise ContractError("candidate recordのIDが不正です")
    _require(record, {"schema_version", "candidate_id", "artifact_kind", "input_selection_id", "keywords_id", "settings_id", "payload", "parent_candidate_id", "review_record_id", "call_id", "created_at"})
    _equal(record, "candidate_id", candidate_id)
    artifact_spec(record["artifact_kind"])
    if record["artifact_kind"] not in _CONTENT_KINDS - {"generation", "scene"}:
        raise ContractError("candidate recordのartifact_kindが不正です")
    if not isinstance(record["payload"], dict) or not _prefixed_id(record["settings_id"], "settings-") or not _prefixed_id(record["call_id"], "call-"):
        raise ContractError("candidate recordの参照またはpayloadが不正です")
    selection, keywords = record["input_selection_id"], record["keywords_id"]
    if selection is None:
        if not _prefixed_id(keywords, "keywords-"):
            raise ContractError("selection前candidateのkeywords参照が不正です")
    elif not _selection_id(selection) or keywords is not None:
        raise ContractError("candidate recordのinput selection/keywords参照が不正です")
    parent, review = record["parent_candidate_id"], record["review_record_id"]
    if (parent is None) != (review is None) or (parent is not None and (not _prefixed_id(parent, "candidate-") or not _prefixed_id(review, "review-"))):
        raise ContractError("candidate recordのrevision参照が不正です")
    if record["schema_version"] != 1:
        raise ContractError("candidate recordのschema_versionが不正です")
    _timestamp(record["created_at"])
    return record


def validate_review_record(review_id: str, record: object) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ContractError("review recordはobjectでなければなりません")
    if not _canonical_audit_id("review", review_id):
        raise ContractError("review recordのIDが不正です")
    _require(record, {"schema_version", "review_id", "candidate_id", "response", "call_id", "created_at"})
    _equal(record, "review_id", review_id)
    if not _prefixed_id(record["candidate_id"], "candidate-") or not _prefixed_id(record["call_id"], "call-"):
        raise ContractError("review recordの参照が不正です")
    _validate_review_response(record["response"])
    if record["schema_version"] != 1:
        raise ContractError("review recordのschema_versionが不正です")
    _timestamp(record["created_at"])
    return record


def validate_call_record(call_id: str, record: object) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ContractError("call recordはobjectでなければなりません")
    if not _canonical_audit_id("call", call_id):
        raise ContractError("call recordのIDが不正です")
    _require(record, {"schema_version", "call_id", "operation", "role", "target_candidate_id", "input_refs", "technical_attempt", "format_attempt", "seed", "endpoint", "model", "settings_id", "request", "response", "transport", "validation"})
    _equal(record, "call_id", call_id)
    if record["schema_version"] != 1 or record["operation"] not in {"model_capability", "generate", "review", "revise"} or not isinstance(record["role"], str) or not record["role"]:
        raise ContractError("call recordの基本項目が不正です")
    target = record["target_candidate_id"]
    if record["operation"] in {"review", "revise"}:
        if not _prefixed_id(target, "candidate-"):
            raise ContractError("call recordのtarget_candidate_idが不正です")
    elif target is not None:
        raise ContractError("call recordのtarget_candidate_idが不正です")
    refs = record["input_refs"]
    if not isinstance(refs, list) or len(refs) != len(set(refs)) or not all(isinstance(item, str) and item for item in refs):
        raise ContractError("call recordのinput_refsが不正です")
    for field in ("technical_attempt", "format_attempt", "seed"):
        if not isinstance(record[field], int) or isinstance(record[field], bool) or record[field] < 1:
            raise ContractError(f"call recordの{field}が不正です")
    if not isinstance(record["endpoint"], str) or not record["endpoint"] or not isinstance(record["model"], str) or not record["model"] or not _prefixed_id(record["settings_id"], "settings-"):
        raise ContractError("call recordのsettings参照または接続情報が不正です")
    if record["transport"] not in {"success", "failure"} or record["request"] is not None and not isinstance(record["request"], str) or record["response"] is not None and not isinstance(record["response"], str):
        raise ContractError("call recordのtransportが不正です")
    validation = record["validation"]
    if not isinstance(validation, dict) or set(validation) != {"result", "checks", "failure_code"} or not isinstance(validation["checks"], list):
        raise ContractError("call recordのvalidationが不正です")
    result, failure = validation["result"], validation["failure_code"]
    if result == "valid" and failure is None and record["transport"] == "success" and record["response"] is not None:
        return record
    if result == "invalid" and failure in {"json_parse", "schema_invalid", "reference_invalid", "evidence_invalid", "range_invalid"} and record["transport"] == "success" and record["response"] is not None:
        return record
    if result == "not_applicable" and failure is None and record["transport"] == "failure" and record["response"] is None:
        return record
    raise ContractError("call recordのvalidation/transport相関が不正です")


def _validate_review_response(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"schema_version", "decision", "issues"} or value.get("schema_version") != "review-response-v1" or value.get("decision") not in {"pass", "issues"} or not isinstance(value.get("issues"), list) or (value["decision"] == "pass") != (not value["issues"]):
        raise ContractError("review responseが不正です")
    for issue in value["issues"]:
        if not isinstance(issue, dict) or set(issue) != {"severity", "evidence_locations", "explanation"} or issue.get("severity") not in {"critical", "notice"} or not isinstance(issue.get("evidence_locations"), list) or not isinstance(issue.get("explanation"), str) or not issue["explanation"]:
            raise ContractError("review responseのissueが不正です")


def _require(record: dict[str, Any], keys: set[str]) -> None:
    if set(record) != keys:
        raise ContractError("record.jsonのfield構成が不正です")


def _equal(record: dict[str, Any], key: str, expected: str) -> None:
    if record.get(key) != expected:
        raise ContractError(f"record.jsonの{key}が配置IDと一致しません")


def _validate_quality_disposition(record: dict[str, Any], artifact_id: str) -> None:
    required = {"schema_version", "quality_id", "candidate_id", "review_record_ids", "revision_count", "result", "remaining_major_issues", "created_at"}
    notice = record.get("notice_type")
    if set(record) != required and set(record) != required | {"notice_type"}:
        raise ContractError("record.jsonのfield構成が不正です")
    _equal(record, "quality_id", artifact_id)
    if not _prefixed_id(record["candidate_id"], "candidate-"):
        raise ContractError("quality-dispositionのcandidate_idが不正です")
    review_ids = record["review_record_ids"]
    if not isinstance(review_ids, list) or not review_ids or len(review_ids) != len(set(review_ids)) or not all(_prefixed_id(value, "review-") for value in review_ids):
        raise ContractError("quality-dispositionのreview_record_idsが不正です")
    revision_count = record["revision_count"]
    if not isinstance(revision_count, int) or isinstance(revision_count, bool) or revision_count < 0:
        raise ContractError("quality-dispositionのrevision_countが不正です")
    if record["result"] not in {"accepted", "accepted_with_notice"}:
        raise ContractError("quality-dispositionのresultが不正です")
    issues = record["remaining_major_issues"]
    if not isinstance(issues, list):
        raise ContractError("quality-dispositionのremaining_major_issuesが不正です")
    if record["result"] == "accepted":
        if issues or "notice_type" in record:
            raise ContractError("quality-dispositionのnotice_typeが不正です")
    elif notice != "編集":
        raise ContractError("quality-dispositionのnotice_typeが不正です")


def _prefixed_id(value: object, prefix: str) -> bool:
    return isinstance(value, str) and value.startswith(prefix) and len(value) > len(prefix)


def _canonical_audit_id(kind: str, value: object) -> bool:
    match = _AUDIT_ID_PATTERNS[kind].fullmatch(value) if isinstance(value, str) else None
    return match is not None and int(match["counter"]) >= 1


def _validate_scene_commit(record: dict[str, Any], artifact_id: str) -> None:
    """Validate scene-commit record against closed schema."""
    # Validate wrapper fields
    wrapper_required = {"schema_version", "artifact_id", "artifact_kind", "input_selection_id", "created_at", "content"}
    if set(record) != wrapper_required:
        raise ContractError("scene_commit recordが不正です")
    _equal(record, "artifact_id", artifact_id)
    _equal(record, "artifact_kind", "scene-commit")
    # Validate content
    content = record["content"]
    content_required = {
        "scene_commit_id",
        "scene_id",
        "scene_card_id",
        "scene_prose_id",
        "continuity_update_id",
        "current_state_id",
        "quality_disposition_id",
        "volume_number",
        "chapter_number",
        "scene_number",
        "created_at",
    }
    if set(content) != content_required:
        raise ContractError("scene_commit recordのcontentが不正です")
    _equal(content, "scene_commit_id", artifact_id)
    commit = artifact_spec("scene-commit").match_id(artifact_id)
    coordinate = {
        "volume": content["volume_number"],
        "chapter": content["chapter_number"],
        "scene": content["scene_number"],
    }
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in coordinate.values()):
        raise ContractError("scene_commit recordが不正です")
    if {name: int(commit.group(name)) for name in coordinate} != coordinate:
        raise ContractError("scene_commit recordの座標がIDと一致しません")
    for kind, field in (
        ("scene", "scene_id"),
        ("scene-card", "scene_card_id"),
        ("scene-prose", "scene_prose_id"),
        ("continuity-update", "continuity_update_id"),
    ):
        match = artifact_spec(kind).match_id(content[field])
        if {name: int(match.group(name)) for name in coordinate} != coordinate:
            raise ContractError("scene_commit recordの参照座標が一致しません")
    artifact_spec("generation").match_id(content["current_state_id"])
    artifact_spec("quality-disposition").match_id(content["quality_disposition_id"])
    _timestamp(content["created_at"])


def _validate_adoption(record: dict[str, Any], artifact_id: str) -> None:
    fields = {"schema_version", "adoption_id", "source_kind", "candidate_id", "quality_id", "output_content_artifact_ids", "output_selection_id", "input_selection_id", "created_at"}
    _require(record, fields)
    _equal(record, "adoption_id", artifact_id)
    if record["source_kind"] not in {"candidate", "direct_request"}:
        raise ContractError("adoption recordが不正です")
    if not isinstance(record["output_content_artifact_ids"], list) or not record["output_content_artifact_ids"] or not all(isinstance(value, str) and value for value in record["output_content_artifact_ids"]):
        raise ContractError("adoption recordが不正です")
    if not _selection_id(record["output_selection_id"]):
        raise ContractError("adoption recordのoutput_selection_idが不正です")
    if record["input_selection_id"] is not None and not _selection_id(record["input_selection_id"]):
        raise ContractError("adoption recordのinput_selection_idが不正です")
    if record["source_kind"] == "candidate":
        if not _prefixed_id(record["candidate_id"], "candidate-") or not _prefixed_id(record["quality_id"], "quality-"):
            raise ContractError("adoption recordのcandidate/quality参照が不正です")
    elif record["candidate_id"] is not None or record["quality_id"] is not None:
        raise ContractError("direct_request adoption recordが不正です")


def _selection_id(value: object) -> bool:
    return isinstance(value, str) and value.startswith("selection-") and len(value) > len("selection-")


def _timestamp(value: object) -> None:
    if not isinstance(value, str):
        raise ContractError("record.jsonのcreated_atが不正です")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("record.jsonのcreated_atが不正です") from exc
