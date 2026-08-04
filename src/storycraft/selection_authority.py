"""Resolve immutable selection slots to verified on-disk V2 records."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping



import jsonschema

from .artifact_record import validate_record
from .artifact_registry import ARTIFACT_SPECS, artifact_directory, artifact_spec, validate_artifact_reference
from .input_normalization import normalize_request
from .prompt_template import get_template_loader
from .selection_snapshot import validate_selection_snapshot
from .series_contracts import ContractError


ContentValidator = Callable[[dict[str, Any], dict[str, Any]], None]

def _validate_request_content(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    del inputs
    try:
        normalized = normalize_request(content)
    except ContractError as exc:
        raise ContractError("request content") from exc
    if normalized != content:
        raise ContractError("request contentはNFC正規化・前後空白除去済みでなければなりません")

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
    initial_design = _record_content(inputs.get("initial_design"))
    if initial_design is not None:
        threads = initial_design.get("unresolved_threads")
        progression = value.get("thread_progression")
        thread_names = {
            item.get("name") for item in threads
            if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"]
        } if isinstance(threads, list) else set()
        if not thread_names or not isinstance(progression, dict) or set(progression) != thread_names:
            raise ContractError("series-planのthread_progressionがinitial-designのunresolved_threadsと一致しません")


def _validate_volume_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    value = _require_object(content, "volume-plan")
    _validate_schema(value, "volume-plan")
    _reject_unknown(value, "volume-plan", {"title", "starting_state_summary", "volume_purpose", "central_conflict", "character_changes", "relationship_changes", "thread_goals", "revelations", "chapter_summaries", "required_end_state", "handoff_expectations"})
    summaries = value.get("chapter_summaries")
    numbers = [item.get("chapter_number") if isinstance(item, dict) else None for item in summaries] if isinstance(summaries, list) else []
    if not summaries or numbers != list(range(1, len(summaries) + 1)):
        raise ContractError("volume-plan chapter_summariesの番号が不正です")
    slot = _current_slot(inputs)
    match = re.fullmatch(r"volume_plan\.v(\d+)", slot)
    if match is None:
        raise ContractError("volume-planのselection slot座標が不正です")
    volume = int(match.group(1))
    series_plan = _record_content(_record_for_prefix(inputs, "series_plan"))
    if not isinstance(series_plan, dict):
        if inputs.get("__strict_parent__"):
            raise ContractError("volume-planの親series-planが候補入力selectionにありません")
        return
    volume_summaries = series_plan.get("volume_summaries")
    parent = next((item for item in volume_summaries if isinstance(item, dict) and item.get("volume_number") == volume), None) if isinstance(volume_summaries, list) else None
    if not isinstance(parent, dict):
        raise ContractError("volume-planの対象巻がseries-planにありません")
    _validate_volume_thread_goals(value, series_plan, volume)

    settings = inputs.get("settings", {})
    settings_payload = settings.get("payload") if isinstance(settings, dict) else None
    chapter_range = settings_payload.get("chapter_per_volume_range") if isinstance(settings_payload, dict) else None
    if isinstance(chapter_range, list) and len(chapter_range) == 2 and not (chapter_range[0] <= len(summaries) <= chapter_range[1]):
        raise ContractError("volume-planの章数がsettings.chapter_per_volume_range外です")


def _validate_chapter_plan(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    value = _require_object(content, "chapter-plan")
    _validate_schema(value, "chapter-plan")
    _reject_unknown(value, "chapter-plan", {"title", "chapter_purpose", "starting_conditions", "ending_changes", "scene_summaries", "required_revelations", "constraints"})
    summaries = value.get("scene_summaries")
    numbers = [item.get("scene_number") if isinstance(item, dict) else None for item in summaries] if isinstance(summaries, list) else []
    if not summaries or numbers != list(range(1, len(summaries) + 1)):
        raise ContractError("chapter-plan scene_summariesの番号が不正です")
    slot = _current_slot(inputs)
    match = re.fullmatch(r"chapter_plan\.v(\d+)\.c(\d+)", slot)
    if match is None:
        raise ContractError("chapter-planのselection slot座標が不正です")
    volume, chapter = (int(item) for item in match.groups())
    volume_plan = _record_content(_record_for_prefix(inputs, f"volume_plan.v{volume:02d}"))
    if not isinstance(volume_plan, dict):
        if inputs.get("__strict_parent__"):
            raise ContractError("chapter-planの親volume-planが候補入力selectionにありません")
        return
    chapter_summaries = volume_plan.get("chapter_summaries")
    parent = next((item for item in chapter_summaries if isinstance(item, dict) and item.get("chapter_number") == chapter), None) if isinstance(chapter_summaries, list) else None
    if not isinstance(parent, dict) or not isinstance(parent.get("purpose"), str):
        raise ContractError("chapter-planの対象章がvolume-planにありません")

    settings = inputs.get("settings", {})
    settings_payload = settings.get("payload") if isinstance(settings, dict) else None
    scene_range = settings_payload.get("chapter_scene_range") if isinstance(settings_payload, dict) else None
    if isinstance(scene_range, list) and len(scene_range) == 2 and not (scene_range[0] <= len(summaries) <= scene_range[1]):
        raise ContractError("chapter-planのscene数がsettings.chapter_scene_range外です")


def _record_for_prefix(inputs: dict[str, Any], prefix: str) -> dict[str, Any] | None:
    """Return the one coordinate-bound parent record for a slot namespace."""
    exact = inputs.get(prefix)
    if isinstance(exact, dict):
        return exact
    matches = [
        record for slot, record in inputs.items()
        if isinstance(slot, str) and slot.startswith(prefix + ".") and isinstance(record, dict)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _record_content(record: dict[str, Any] | None) -> dict[str, Any] | None:
    value = record.get("content") if isinstance(record, dict) else None
    return value if isinstance(value, dict) else None


def _canonical_thread_names(initial_design: dict[str, Any]) -> set[str]:
    threads = initial_design.get("unresolved_threads")
    if not isinstance(threads, list) or not threads:
        raise ContractError("initial-designのcanonical thread_nameが不正です")
    names: set[str] = set()
    for thread in threads:
        if not isinstance(thread, dict) or not isinstance(thread.get("name"), str) or not thread["name"]:
            raise ContractError("initial-designのcanonical thread_nameが不正です")
        names.add(thread["name"])
    if len(names) != len(threads):
        raise ContractError("initial-designのcanonical thread_nameが不正です")
    return names


def _validate_generation_thread_names(
    thread_states: dict[str, Any], initial_design: dict[str, Any],
) -> None:
    if set(thread_states) != _canonical_thread_names(initial_design):
        raise ContractError("generationのunresolved_thread_statesがinitial-designのcanonical thread_nameと一致しません")


def _validate_volume_thread_goals(
    volume_plan: dict[str, Any], series_plan: dict[str, Any], volume: int,
) -> None:
    progression = series_plan.get("thread_progression")
    goals = volume_plan.get("thread_goals")
    if not isinstance(progression, dict) or not isinstance(goals, dict):
        raise ContractError("volume-planのthread_goalsまたはseries-planのthread_progressionが不正です")
    expected = {
        name
        for name, volumes in progression.items()
        if isinstance(name, str) and name and isinstance(volumes, list) and volume in volumes
    }
    if set(goals) != expected:
        raise ContractError("volume-planのthread_goalsがseries-planのcanonical thread_name割当と一致しません")


def _validate_thread_lineage(resolved: dict[str, dict[str, Any]]) -> None:
    initial_design = _record_content(resolved.get("initial_design"))
    current_state = _record_content(resolved.get("current_state"))
    if isinstance(initial_design, dict) and isinstance(current_state, dict):
        thread_states = current_state.get("unresolved_thread_states")
        if isinstance(thread_states, dict):
            _validate_generation_thread_names(thread_states, initial_design)

    series_plan = _record_content(resolved.get("series_plan"))
    if not isinstance(series_plan, dict):
        return
    if isinstance(initial_design, dict):
        progression = series_plan.get("thread_progression")
        if not isinstance(progression, dict) or set(progression) != _canonical_thread_names(initial_design):
            raise ContractError("series-planのthread_progressionがinitial-designのcanonical thread_nameと一致しません")
    for slot, record in resolved.items():
        match = re.fullmatch(r"volume_plan\.v(\d+)", slot)
        if match is None:
            continue
        volume_plan = _record_content(record)
        if isinstance(volume_plan, dict):
            _validate_volume_thread_goals(volume_plan, series_plan, int(match.group(1)))


def _current_slot(inputs: dict[str, Any]) -> str:
    slot = inputs.get("__current_slot__")
    if not isinstance(slot, str) or not slot:
        raise ContractError("候補のselection slot束縛がありません")
    return slot


def _scene_coordinate_from_slot(slot: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(?:scene_plan|scene_card)\.v(\d+)\.c(\d+)\.s(\d+)", slot)
    if match is None:
        raise ContractError("scene候補のselection slot座標が不正です")
    return tuple(int(value) for value in match.groups())  # type: ignore[return-value]


def _validate_scene_plan(content: dict[str, Any], inputs: dict[str, Any]) -> None:
    value = _require_object(content, "scene-plan")
    _validate_schema(value, "scene-plan")
    volume, chapter, scene = _scene_coordinate_from_slot(_current_slot(inputs))
    chapter_plan = _record_content(_record_for_prefix(inputs, f"chapter_plan.v{volume:02d}.c{chapter:02d}"))
    volume_plan = _record_content(_record_for_prefix(inputs, f"volume_plan.v{volume:02d}"))
    series_plan = _record_content(_record_for_prefix(inputs, "series_plan"))
    if not isinstance(chapter_plan, dict) or not isinstance(volume_plan, dict) or not isinstance(series_plan, dict):
        raise ContractError("scene-planの親計画が入力selectionにありません")

    summaries = chapter_plan.get("scene_summaries")
    target_summary = next(
        (item for item in summaries if isinstance(item, dict) and item.get("scene_number") == scene),
        None,
    ) if isinstance(summaries, list) else None
    if not isinstance(target_summary, dict) or not isinstance(target_summary.get("purpose"), str):
        raise ContractError("scene-planの対象sceneがchapter-planにありません")
    if not isinstance(value.get("purpose"), str) or target_summary["purpose"] not in value["purpose"]:
        raise ContractError("scene-planのpurposeが親chapter-planと一致しません")

    volume_summaries = series_plan.get("volume_summaries")
    if not isinstance(volume_summaries, list) or not any(
        isinstance(item, dict) and item.get("volume_number") == volume for item in volume_summaries
    ):
        raise ContractError("scene-planの巻座標がseries-planにありません")
    chapter_summaries = volume_plan.get("chapter_summaries")
    if not isinstance(chapter_summaries, list) or not any(
        isinstance(item, dict) and item.get("chapter_number") == chapter for item in chapter_summaries
    ):
        raise ContractError("scene-planの章座標がvolume-planにありません")

    parent_changes = chapter_plan.get("ending_changes", [])
    if not isinstance(parent_changes, list) or not set(value.get("intended_changes", [])).issubset(parent_changes):
        raise ContractError("scene-planのintended_changesが親chapter-planの範囲外です")
    parent_revelations = chapter_plan.get("required_revelations", [])
    if not isinstance(parent_revelations, list) or not set(value.get("intended_revelations", [])).issubset(parent_revelations):
        raise ContractError("scene-planのintended_revelationsが親chapter-planの範囲外です")


def _validate_scene_card(content: dict[str, Any], inputs: dict[str, Any]) -> None:
    value = _require_object(content, "scene-card")
    _validate_schema(value, "scene-card")
    volume, chapter, scene = _scene_coordinate_from_slot(_current_slot(inputs))
    plan_content = _record_content(_record_for_prefix(inputs, f"scene_plan.v{volume:02d}.c{chapter:02d}.s{scene:02d}"))
    if not isinstance(plan_content, dict):
        raise ContractError("scene-cardの親scene-planが入力selectionにありません")
    current_state = _record_content(inputs.get("current_state"))
    thread_states = current_state.get("unresolved_thread_states") if isinstance(current_state, dict) else None
    if isinstance(thread_states, dict):
        for update in value.get("allowed_updates", []):
            if (
                isinstance(update, dict)
                and update.get("target_type") == "unresolved_thread_states"
                and update.get("target_id") not in thread_states
            ):
                raise ContractError("scene-cardのallowed_updatesがcanonical thread_name外です")
    for field in ("pov_character_id", "participant_ids", "location_id"):
        if value.get(field) != plan_content.get(field):
            raise ContractError(f"scene-cardの{field}がscene-planと一致しません")
    plan_purpose = plan_content.get("purpose")
    if not isinstance(value.get("purpose"), str) or not isinstance(plan_purpose, str) or plan_purpose not in value["purpose"]:
        raise ContractError("scene-cardのpurposeがscene-planと一致しません")
    plan_beats = set(plan_content.get("intended_beats", []))
    plan_changes = set(plan_content.get("intended_changes", []))
    if any(not isinstance(beat, dict) or beat.get("description") not in plan_beats for beat in value.get("required_beats", [])):
        raise ContractError("scene-cardのrequired_beatsがscene-planのintended_beats外です")
    if any(target not in plan_changes for target in value.get("ending_state_targets", [])):
        raise ContractError("scene-cardのending_state_targetsがscene-planのintended_changes外です")
    plan_revelations = set(plan_content.get("intended_revelations", []))
    allowed = set(value.get("allowed_revelations", []))
    required = set(value.get("required_revelations", []))
    forbidden = set(value.get("forbidden_revelations", []))
    if not allowed.issubset(plan_revelations) or not required.issubset(allowed) or (allowed | required) & forbidden:
        raise ContractError("scene-cardの開示制約がscene-planの範囲外です")


def _validate_scene_prose(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    value = _require_object(content, "scene-prose")
    if set(value) != {"text", "coordinate"}:
        raise ContractError("scene-prose contentに未知または不足する項目があります")
    slot = _current_slot(inputs)
    match = re.fullmatch(r"scene_prose\.v(\d+)\.c(\d+)\.s(\d+)", slot)
    if match is None:
        raise ContractError("scene-proseのselection slot座標が不正です")
    expected = {"volume_number": int(match.group(1)), "chapter_number": int(match.group(2)), "scene_number": int(match.group(3))}
    if value.get("coordinate") != expected:
        raise ContractError("scene-proseの座標がselection slotと一致しません")
    if not isinstance(value.get("text"), str) or not value["text"].strip():
        raise ContractError("scene-prose content")


def _validate_continuity_update(content: dict[str, Any], inputs: dict[str, Any]) -> None:
    slot = _current_slot(inputs)
    match = re.fullmatch(r"continuity_update\.v(\d+)\.c(\d+)\.s(\d+)", slot)
    if match is None:
        raise ContractError("continuity-updateのselection slot座標が不正です")
    target = {"volume_number": int(match.group(1)), "chapter_number": int(match.group(2)), "scene_number": int(match.group(3))}
    from .scene_continuity_stage import SceneContinuityStageService
    SceneContinuityStageService._validate_content(content, target, inputs)


def _validate_generation(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    value = _require_object(content, "generation")
    _reject_unknown(value, "generation", {"story_facts", "character_knowledge", "reader_disclosures", "unresolved_thread_states", "timeline_position"})
    if not isinstance(value.get("story_facts"), list) or not value["story_facts"]:
        raise ContractError("generation story_facts")
    if not isinstance(value.get("character_knowledge"), dict):
        raise ContractError("generation character_knowledge")
    if not isinstance(value.get("reader_disclosures"), list):
        raise ContractError("generation reader_disclosures")
    thread_states = value.get("unresolved_thread_states")
    if not isinstance(thread_states, dict):
        raise ContractError("generation unresolved_thread_states")
    initial_design = _record_content(inputs.get("initial_design"))
    if isinstance(initial_design, dict):
        _validate_generation_thread_names(thread_states, initial_design)
    for thread_name, thread_state in thread_states.items():
        if not isinstance(thread_name, str) or not thread_name or not isinstance(thread_state, dict) or set(thread_state) != {"status"} or thread_state.get("status") not in {"open", "progressed", "resolved"}:
            raise ContractError("generation unresolved_thread_statesの状態が不正です")
    timeline_position = value.get("timeline_position")
    if not isinstance(timeline_position, int) or isinstance(timeline_position, bool) or timeline_position < 0:
        raise ContractError("generation timeline_position")


def _validate_scene(content: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> None:
    value = _require_object(content, "scene")
    required = {"coordinate", "scene_prose_id", "continuity_update_id", "current_state_id", "scene_card_id", "quality_disposition_id"}
    if set(value) != required:
        raise ContractError("scene content")
    coordinate = value["coordinate"]
    if not isinstance(coordinate, dict) or set(coordinate) != {"volume_number", "chapter_number", "scene_number"} or any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in coordinate.values()):
        raise ContractError("scene coordinate")
    for kind, field in (("scene-prose", "scene_prose_id"), ("continuity-update", "continuity_update_id"), ("scene-card", "scene_card_id")):
        try:
            match = artifact_spec(kind).match_id(value[field])
        except ContractError as exc:
            raise ContractError("scene参照ID") from exc
        if {"volume_number": int(match.group("volume")), "chapter_number": int(match.group("chapter")), "scene_number": int(match.group("scene"))} != coordinate:
            raise ContractError("scene参照座標")
    try:
        artifact_spec("generation").match_id(value["current_state_id"])
        artifact_spec("quality-disposition").match_id(value["quality_disposition_id"])
    except ContractError as exc:
        raise ContractError("scene参照ID") from exc


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
    record_paths: Mapping[tuple[str, str], Path] | None = None,
    resolution_cache: dict[str, dict[str, dict[str, Any]]] | None = None,
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
    root = workspace_root.expanduser()
    cache = resolution_cache if resolution_cache is not None else {}
    resolved = _resolve_snapshot(root, snapshot, validators, set(), record_paths, cache)
    _validate_thread_lineage(resolved)
    _validate_quality_slot_lineage(root, value, resolved, record_paths)
    return resolved


def _validate_quality_slot_lineage(
    workspace_root: Path,
    snapshot: dict[str, Any],
    resolved: dict[str, dict[str, Any]],
    record_paths: Mapping[tuple[str, str], Path] | None,
) -> None:
    """Bind prose/continuity quality slots to their adoption and content IDs."""
    selection_id = snapshot["selection_id"]
    for quality_slot, quality in resolved.items():
        match = re.fullmatch(r"(scene_prose|continuity)_disposition\.(v\d{2}\.c\d{2}\.s\d{2})", quality_slot)
        if match is None:
            continue
        stem, coordinate = match.groups()
        adoption_slot = f"{stem}_adoption.{coordinate}"
        content_slot = f"{stem if stem == 'scene_prose' else 'continuity_update'}.{coordinate}"
        adoption = resolved.get(adoption_slot)
        content = resolved.get(content_slot)
        if not isinstance(adoption, dict) or not isinstance(content, dict):
            raise ContractError(f"{quality_slot}のadoption/content lineageがありません")
        if adoption.get("source_kind") != "candidate" or not _selection_is_ancestor(
            workspace_root, snapshot, adoption.get("output_selection_id"), record_paths
        ):
            raise ContractError(f"{quality_slot}のadoption selection lineageが不正です")
        if adoption.get("quality_id") != quality.get("quality_id"):
            raise ContractError(f"{quality_slot}のquality IDがadoptionと一致しません")
        content_id = content.get("artifact_id")
        output_ids = adoption.get("output_content_artifact_ids")
        if not isinstance(content_id, str) or not isinstance(output_ids, list) or output_ids != [content_id]:
            raise ContractError(f"{quality_slot}のadoption content lineageが不正です")


def _selection_is_ancestor(
    workspace_root: Path,
    snapshot: dict[str, Any],
    ancestor_id: object,
    record_paths: Mapping[tuple[str, str], Path] | None,
) -> bool:
    if not isinstance(ancestor_id, str):
        return False
    current: object = snapshot
    seen: set[str] = set()
    while isinstance(current, dict):
        value = validate_selection_snapshot(current)
        selection_id = value["selection_id"]
        if selection_id == ancestor_id:
            return True
        if selection_id in seen:
            return False
        seen.add(selection_id)
        parent_id = value["input_selection_id"]
        if parent_id is None:
            return False
        current = _read_record(workspace_root, "selection", parent_id, record_paths)
    return False


def _resolve_snapshot(
    workspace_root: Path,
    snapshot: object,
    validators: Mapping[str, ContentValidator],
    resolving: set[str],
    record_paths: Mapping[tuple[str, str], Path] | None = None,
    cache: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> dict[str, dict[str, Any]]:
    value = validate_selection_snapshot(snapshot)
    selection_id = value["selection_id"]
    if cache is not None and selection_id in cache:
        return cache[selection_id]
    if selection_id in resolving:
        raise ContractError("selection input chainが循環しています")
    resolving.add(selection_id)
    try:
        resolved: dict[str, dict[str, Any]] = {}
        for slot, artifact_id in value["slots"].items():
            kind = _kind_for(slot, artifact_id)
            validate_artifact_reference(kind, artifact_id, slot)
            record = _read_record(workspace_root, kind, artifact_id, record_paths)
            record = validate_record(kind, artifact_id, record)
            if "content" in record:
                inputs = _input_bundle(workspace_root, record, validators, resolving, record_paths, cache)
                validation_inputs: dict[str, Any] = dict(inputs)
                validation_inputs["__current_slot__"] = slot
                validator = validators.get(kind)
                if validator is not None:
                    validator(record["content"], validation_inputs)
            resolved[slot] = record
        if cache is not None:
            cache[selection_id] = resolved
        return resolved
    finally:
        resolving.remove(selection_id)


def _input_bundle(
    workspace_root: Path,
    record: dict[str, Any],
    validators: Mapping[str, ContentValidator],
    resolving: set[str],
    record_paths: Mapping[tuple[str, str], Path] | None = None,
    cache: dict[str, dict[str, dict[str, Any]]] | None = None,
) -> dict[str, dict[str, Any]]:
    input_selection_id = record["input_selection_id"]
    if input_selection_id is None:
        return {}
    assert isinstance(input_selection_id, str)
    if record_paths is not None and ("selection", input_selection_id) in record_paths:
        snapshot_path = record_paths[("selection", input_selection_id)]
    else:
        snapshot_path = workspace_root / "runtime" / "selections" / input_selection_id
    snapshot_path = snapshot_path / "record.json"
    if snapshot_path.is_symlink() or not snapshot_path.is_file():
        raise ContractError("artifact input_selection_idのselectionがありません")
    try:
        input_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("artifact input selectionを読み込めません") from exc
    if input_snapshot.get("selection_id") != input_selection_id if isinstance(input_snapshot, dict) else True:
        raise ContractError("artifact input selectionのIDが保存先と一致しません")
    return _resolve_snapshot(workspace_root, input_snapshot, validators, resolving, record_paths, cache)


def _read_record(
    workspace_root: Path,
    kind: str,
    artifact_id: str,
    record_paths: Mapping[tuple[str, str], Path] | None = None,
) -> dict[str, Any]:
    directory = (
        record_paths[(kind, artifact_id)]
        if record_paths is not None and (kind, artifact_id) in record_paths
        else workspace_root / artifact_directory(kind, artifact_id)
    )
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