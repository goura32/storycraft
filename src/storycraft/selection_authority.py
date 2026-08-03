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
    fields = {"title", "genre", "premise", "required_elements", "avoid", "ending_preference", "volume_count", "language"}
    if set(content) != fields or content.get("language") != "ja":
        raise ContractError("request content")
    for key in ("title", "premise", "ending_preference"):
        if not isinstance(content.get(key), str) or not content[key].strip():
            raise ContractError("request content")
    # genre: array of strings
    genre = content.get("genre")
    if not isinstance(genre, list) or not genre or any(not isinstance(x, str) or not x.strip() for x in genre) or len(genre) != len(set(genre)):
        raise ContractError("request content")
    for key in ("required_elements", "avoid"):
        item = content.get(key)
        if not isinstance(item, list) or any(not isinstance(x, str) or not x.strip() for x in item) or len(item) != len(set(item)):
            raise ContractError("request content")
    count = content.get("volume_count")
    if not isinstance(count, int) or isinstance(count, bool) or not 4 <= count <= 10:
        raise ContractError("request content")

def _validate_initial_design_content(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    if not isinstance(content, dict):
        raise ContractError("initial-design content")
    try:
        jsonschema.Draft202012Validator(
            get_template_loader().load_schema_object("generate", "initial_design")
        ).validate(content)
    except jsonschema.ValidationError as exc:
        raise ContractError("initial-design content schema不正") from exc
    cast = content["cast"]
    cast_names = [item["name"] for item in cast]
    thread_names = [item["name"] for item in content["unresolved_threads"]]
    if len(cast_names) != len(set(cast_names)) or len(thread_names) != len(set(thread_names)):
        raise ContractError("initial-design contentの名称が重複しています")
    character_knows = content["knowledge_model"]["character_knows"]
    if set(character_knows) != set(cast_names):
        raise ContractError("initial-design contentの人物知識主体がcastと一致しません")
    required_threads = {item["name"] for item in content["unresolved_threads"] if item["required_for_ending"]}
    condition_threads = {item["thread_name"] for item in content["ending_conditions"]}
    if condition_threads != required_threads:
        raise ContractError("initial-design contentの結末条件が未解決事項と一致しません")


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


def _validate_schema(content: dict[str, Any], kind: str) -> None:
    stage = {"series-plan": "series_plan", "volume-plan": "volume_plan", "chapter-plan": "chapter_plan", "scene-plan": "scene_plan", "scene-card": "scene_card"}[kind]
    try:
        jsonschema.Draft202012Validator(get_template_loader().load_schema_object("generate", stage)).validate(content)
    except jsonschema.ValidationError as exc:
        raise ContractError(f"{kind} content schema不正") from exc


def _validate_series_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    value = _require_object(content, "series-plan")
    _validate_schema(value, "series-plan")
    _reject_unknown(value, "series-plan", {"volume_count", "series_objectives", "volume_summaries", "character_arc_map", "relationship_arc_map", "thread_progression", "revelation_schedule", "ending_path", "global_constraints"})
    summaries = value.get("volume_summaries")
    if not isinstance(summaries, list) or not summaries:
        raise ContractError("series-plan volume_summaries")
    count = value.get("volume_count")
    numbers = [item.get("volume_number") if isinstance(item, dict) else None for item in summaries]
    if not isinstance(count, int) or isinstance(count, bool) or not 4 <= count <= 10 or len(summaries) != count or numbers != list(range(1, count + 1)):
        raise ContractError("series-plan volume_countとvolume_summariesの対応が不正です")
    request = inputs.get("request", {}).get("content") if isinstance(inputs.get("request"), dict) else None
    if request is not None and (not isinstance(request, dict) or request.get("volume_count") != count):
        raise ContractError("series-plan volume_countがrequestと一致しません")


def _validate_volume_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "volume-plan")
    _validate_schema(value, "volume-plan")
    _reject_unknown(value, "volume-plan", {"title", "starting_state_summary", "volume_purpose", "central_conflict", "character_changes", "relationship_changes", "thread_goals", "revelations", "chapter_summaries", "required_end_state", "handoff_expectations"})
    summaries = value.get("chapter_summaries")
    numbers = [item.get("chapter_number") if isinstance(item, dict) else None for item in summaries] if isinstance(summaries, list) else []
    if not summaries or numbers != list(range(1, len(summaries) + 1)):
        raise ContractError("volume-plan chapter_summariesの番号が不正です")


def _validate_chapter_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "chapter-plan")
    _validate_schema(value, "chapter-plan")
    _reject_unknown(value, "chapter-plan", {"title", "chapter_purpose", "starting_conditions", "ending_changes", "scene_summaries", "required_revelations", "constraints"})
    summaries = value.get("scene_summaries")
    numbers = [item.get("scene_number") if isinstance(item, dict) else None for item in summaries] if isinstance(summaries, list) else []
    if not summaries or numbers != list(range(1, len(summaries) + 1)):
        raise ContractError("chapter-plan scene_summariesの番号が不正です")


def _validate_scene_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "scene-plan")
    _validate_schema(value, "scene-plan")


def _validate_scene_card(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    value = _require_object(content, "scene-card")
    _validate_schema(value, "scene-card")
    scene_plan = inputs.get("scene_plan")
    plan_content = scene_plan.get("content") if isinstance(scene_plan, dict) else None
    if isinstance(plan_content, dict):
        for field in ("pov_character_id", "participant_ids", "location_id"):
            if value.get(field) != plan_content.get(field):
                raise ContractError(f"scene-card {field}がscene-planと一致しません")


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
    _reject_unknown(value, "generation", {"story_facts", "character_knowledge", "reader_disclosures", "unresolved_thread_states", "timeline_position"})
    if not isinstance(value.get("story_facts"), list) or not value["story_facts"]:
        raise ContractError("generation story_facts")
    if not isinstance(value.get("character_knowledge"), dict):
        raise ContractError("generation character_knowledge")
    if not isinstance(value.get("reader_disclosures"), list):
        raise ContractError("generation reader_disclosures")
    if not isinstance(value.get("unresolved_thread_states"), dict):
        raise ContractError("generation unresolved_thread_states")
    timeline_position = value.get("timeline_position")
    if not isinstance(timeline_position, int) or isinstance(timeline_position, bool) or timeline_position < 0:
        raise ContractError("generation timeline_position")


def _validate_scene(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    value = _require_object(content, "scene")
    required = {"coordinate", "scene_prose_id", "continuity_update_id", "current_state_id", "scene_card_id", "quality_disposition_id"}
    if set(value) != required:
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
        validate_artifact_reference("quality-disposition", artifact_id, slot)
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