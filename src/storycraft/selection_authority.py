"""Resolve immutable selection slots to verified on-disk V2 records."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping



import jsonschema

from .artifact_record import validate_record
from .artifact_registry import ARTIFACT_SPECS, artifact_directory, validate_artifact_reference
from .prompt_template import get_template_loader
from .selection_snapshot import validate_selection_snapshot
from .series_contracts import ContractError


ContentValidator = Callable[[dict[str, Any], dict[str, dict[str, Any]]], None]

def _validate_request_content(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    fields = {"title", "genre", "premise", "required_elements", "forbidden_elements", "ending_preference", "volume_count", "language"}
    if set(content) != fields or content.get("language") != "ja":
        raise ContractError("request content")
    for key in ("title", "genre", "premise", "ending_preference"):
        if not isinstance(content.get(key), str) or not content[key].strip():
            raise ContractError("request content")
    for key in ("required_elements", "forbidden_elements"):
        item = content.get(key)
        if not isinstance(item, list) or any(not isinstance(x, str) or not x.strip() for x in item) or len(item) != len(set(item)):
            raise ContractError("request content")
    count = content.get("volume_count")
    if not isinstance(count, int) or isinstance(count, bool) or not 4 <= count <= 10:
        raise ContractError("request content")

def _validate_initial_design_content(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    required = {
        "core": str,
        "cast": list,
        "world": str,
        "knowledge_model": dict,
        "unresolved_threads": list,
        "ending_conditions": list,
    }
    if not isinstance(content, dict):
        raise ContractError("initial-design content")
    actual_keys = set(content.keys())
    expected_keys = set(required.keys())
    if actual_keys != expected_keys:
        raise ContractError("initial-design content")
    for key, typ in required.items():
        val = content[key]
        if not isinstance(val, typ):
            raise ContractError("initial-design content")
        if key == "core" or key == "world":
            if not isinstance(val, str) or not val.strip():
                raise ContractError("initial-design content")
        if key == "cast":
            if not isinstance(val, list):
                raise ContractError("initial-design content")
            for item in val:
                if not isinstance(item, dict):
                    raise ContractError("initial-design content")
                if set(item.keys()) != {"name", "role"}:
                    raise ContractError("initial-design content")
                if not isinstance(item.get("name"), str) or not item["name"].strip():
                    raise ContractError("initial-design content")
                if not isinstance(item.get("role"), str) or not item["role"].strip():
                    raise ContractError("initial-design content")
        if key == "knowledge_model":
            if not isinstance(val, dict):
                raise ContractError("initial-design content")
        if key == "unresolved_threads":
            if not isinstance(val, list):
                raise ContractError("initial-design content")
        if key == "ending_conditions":
            if not isinstance(val, list):
                raise ContractError("initial-design content")
            for item in val:
                if not isinstance(item, str) or not item.strip():
                    raise ContractError("initial-design content")

def _require_object(content: dict[str, Any], kind: str) -> dict[str, Any]:
    if not isinstance(content, dict) or not content:
        raise ContractError(f"{kind} content")
    return content


def _require_numbered_list(content: dict[str, Any], kind: str, *fields: str) -> None:
    value = _require_object(content, kind)
    items: object = next((value[field] for field in fields if isinstance(value.get(field), list)), None)
    if not isinstance(items, list) or not items:
        raise ContractError(f"{kind} content")
    if all(isinstance(item, int) and not isinstance(item, bool) and item >= 1 for item in items):
        return
    for item in items:
        if not isinstance(item, dict) or not any(isinstance(item.get(number_field), int) and not isinstance(item[number_field], bool) and item[number_field] >= 1 for number_field in ("volume_number", "chapter_number", "scene_number")):
            raise ContractError(f"{kind} content")


def _reject_unknown(content: dict[str, Any], kind: str, allowed: set[str]) -> None:
    unknown = set(content) - allowed
    if unknown:
        raise ContractError(f"{kind} contentに未知の項目があります: {sorted(unknown)}")


def _validate_schema_when_modern(content: dict[str, Any], kind: str, marker: str) -> None:
    if marker not in content:
        return
    stage = {"series-plan": "series_plan", "volume-plan": "volume_plan", "chapter-plan": "chapter_plan", "scene-plan": "scene_plan", "scene-card": "scene_card"}[kind]
    try:
        jsonschema.Draft202012Validator(get_template_loader().load_schema_object("generate", stage)).validate(content)
    except jsonschema.ValidationError as exc:
        raise ContractError(f"{kind} content schema不正") from exc


def _validate_series_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "series-plan")
    _validate_schema_when_modern(value, "series-plan", "volume_summaries")
    _reject_unknown(value, "series-plan", {"volume_count", "series_objectives", "volume_summaries", "character_arc_map", "relationship_arc_map", "thread_progression", "revelation_schedule", "ending_path", "global_constraints", "title", "volumes", "thread_allocations"})
    if "volume_summaries" not in value and (not isinstance(value.get("thread_allocations"), list)):
        raise ContractError("series-plan content")
    _require_numbered_list(value, "series-plan", "volume_summaries", "volumes")


def _validate_volume_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "volume-plan")
    _validate_schema_when_modern(value, "volume-plan", "chapter_summaries")
    _reject_unknown(value, "volume-plan", {"volume_number", "title", "starting_state_summary", "volume_purpose", "central_conflict", "character_changes", "relationship_changes", "required_revelations", "unresolved_threads", "ending_state_summary", "chapter_summaries", "chapters", "thread_allocations"})
    if "chapter_summaries" not in value and (not isinstance(value.get("thread_allocations"), list)):
        raise ContractError("volume-plan content")
    _require_numbered_list(value, "volume-plan", "chapter_summaries", "chapters")


def _validate_chapter_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "chapter-plan")
    _validate_schema_when_modern(value, "chapter-plan", "scene_summaries")
    _reject_unknown(value, "chapter-plan", {"volume_number", "chapter_number", "title", "chapter_purpose", "starting_conditions", "ending_changes", "scene_summaries", "scenes", "thread_allocations"})
    if "scene_summaries" not in value and (not isinstance(value.get("thread_allocations"), list)):
        raise ContractError("chapter-plan content")
    _require_numbered_list(value, "chapter-plan", "scene_summaries", "scenes")


def _validate_scene_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "scene-plan")
    _reject_unknown(value, "scene-plan", {"purpose", "pov_character_id", "coordinate", "characters", "setting", "conflict", "turning_point", "ending_state", "required_revelations", "allowed_knowledge", "forbidden_knowledge", "allowed_disclosures", "allowed_facts", "allowed_updates", "forbidden_disclosures", "prose_conditions", "planned_fact_changes", "thread_allocations", "scene_goal", "dramatic_question", "emotional_arc", "beats", "disclosures", "revelations", "foreshadowing", "threads", "continuity_requirements", "description", "scene_number"})
    if not isinstance(value.get("purpose"), str) or not value["purpose"].strip():
        raise ContractError("scene-plan content")
    if not any(key in value for key in ("pov_character_id", "coordinate", "characters")):
        raise ContractError("scene-plan content")


def _validate_scene_card(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "scene-card")
    _reject_unknown(value, "scene-card", {"coordinate", "pov_character_id", "pov_character", "location", "time", "characters_present", "goals", "constraints", "allowed_knowledge", "forbidden_knowledge", "allowed_disclosures", "allowed_facts", "allowed_updates", "forbidden_disclosures", "prose_conditions", "planned_fact_changes", "thread_allocations", "beats", "continuity_constraints", "scene_goal", "dramatic_question", "emotional_arc", "disclosures", "revelations", "foreshadowing", "threads", "description", "scene_number", "setting"})
    if not any(key in value for key in ("pov_character_id", "coordinate", "pov_character")):
        raise ContractError("scene-card content")


def _validate_scene_prose(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "scene-prose")
    _reject_unknown(value, "scene-prose", {"text", "coordinate", "scene_id", "word_count", "language"})
    if not isinstance(value.get("text"), str) or not value["text"].strip():
        raise ContractError("scene-prose content")


def _validate_continuity_update(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "continuity-update")
    if not any(key in value for key in ("operations", "changes", "summary")):
        raise ContractError("continuity-update content")


def _validate_generation(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "generation")
    if not any(key in value for key in ("story_facts", "character_states", "character_knowledge", "world_states")):
        raise ContractError("generation content")


def _validate_scene(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "scene")
    if not any(key in value for key in ("scene_prose_id", "coordinate")):
        raise ContractError("scene content")


DEFAULT_CONTENT_VALIDATORS: dict[str, ContentValidator] = {
    "request": _validate_request_content,
    "initial-design": _validate_initial_design_content,
    "series-plan": _validate_series_plan,
    "volume-plan": _validate_volume_plan,
    "chapter-plan": _validate_chapter_plan,
    "scene-plan": _validate_scene_plan,
    "scene-card": _validate_scene_card,
    "scene-prose": _validate_scene_prose,
    "continuity-update": _validate_continuity_update,
    "generation": _validate_generation,
    "scene": _validate_scene,
}


def resolve_selection(
    workspace_root: Path,
    snapshot: object,
    *,
    content_validators: Mapping[str, ContentValidator] | None = None,
) -> dict[str, dict[str, Any]]:
    """Resolve slots and reapply each available kind validator to its input bundle.

    The optional mapping is the integration seam for stage-owned semantic validators;
    this authority layer always verifies the closed envelope and restores the exact
    immutable input selection before invoking one.
    """
    value = validate_selection_snapshot(snapshot)
    validators: dict[str, ContentValidator] = dict(DEFAULT_CONTENT_VALIDATORS)
    if content_validators is not None:
        validators.update(content_validators)
    return _resolve_snapshot(workspace_root.expanduser(), snapshot, validators, set())


def _resolve_snapshot(
    workspace_root: Path,
    snapshot: object,
    validators: Mapping[str, ContentValidator],
    resolving: set[str],
) -> dict[str, dict[str, Any]]:
    value = validate_selection_snapshot(snapshot)
    selection_id = value["selection_id"]
    if selection_id in resolving:
        raise ContractError("selection input chainが循環しています")
    resolving.add(selection_id)
    try:
        resolved: dict[str, dict[str, Any]] = {}
        for slot, artifact_id in value["slots"].items():
            kind = _kind_for(slot, artifact_id)
            validate_artifact_reference(kind, artifact_id, slot)
            record = _read_record(workspace_root, kind, artifact_id)
            record = validate_record(kind, artifact_id, record)
            if "content" in record:
                inputs = _input_bundle(workspace_root, record, validators, resolving)
                validator = validators.get(kind)
                if validator is not None:
                    validator(record["content"], inputs)
            resolved[slot] = record
        return resolved
    finally:
        resolving.remove(selection_id)


def _input_bundle(
    workspace_root: Path,
    record: dict[str, Any],
    validators: Mapping[str, ContentValidator],
    resolving: set[str],
) -> dict[str, dict[str, Any]]:
    input_selection_id = record["input_selection_id"]
    if input_selection_id is None:
        return {}
    assert isinstance(input_selection_id, str)
    snapshot_path = workspace_root / "runtime" / "selections" / input_selection_id / "record.json"
    if snapshot_path.is_symlink() or not snapshot_path.is_file():
        raise ContractError("artifact input_selection_idのselectionがありません")
    try:
        input_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("artifact input selectionを読み込めません") from exc
    if input_snapshot.get("selection_id") != input_selection_id if isinstance(input_snapshot, dict) else True:
        raise ContractError("artifact input selectionのIDが保存先と一致しません")
    return _resolve_snapshot(workspace_root, input_snapshot, validators, resolving)


def _read_record(workspace_root: Path, kind: str, artifact_id: str) -> dict[str, Any]:
    directory = workspace_root / artifact_directory(kind, artifact_id)
    if directory.is_symlink() or not directory.is_dir():
        raise ContractError(f"selectionのrecord directoryが通常directoryではありません: {directory}")
    record_path = directory / "record.json"
    if record_path.is_symlink() or not record_path.is_file():
        raise ContractError("selectionのrecord.jsonが通常ファイルではありません")
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("selectionのrecord.jsonを読み込めません") from exc
    if not isinstance(record, dict):
        raise ContractError("selectionのrecord.jsonはobjectでなければなりません")
    return record


def _kind_for(slot: str, artifact_id: str) -> str:
    if slot.startswith("scene_prose_disposition.") or slot.startswith("continuity_disposition."):
        return "quality-disposition"
    if slot == "prior_volume_plan":
        # Prior volume plan is always an adoption of a volume-plan artifact
        return "volume-plan"
    matches: list[str] = []
    for kind, spec in ARTIFACT_SPECS.items():
        if kind == "quality-disposition":
            continue
        try:
            validate_artifact_reference(kind, artifact_id, slot)
        except ContractError:
            continue
        matches.append(kind)
    if len(matches) != 1:
        raise ContractError("selection slotからartifact kindを一意に解決できません")
    return matches[0]