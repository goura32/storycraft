"""Deterministic derivation of immutable Storycraft work state."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .continuity_paths import apply_change, binding
from .series_contracts import ContractError


_STATE_FIELDS = frozenset({
    "story_facts", "character_knowledge", "reader_disclosures",
    "unresolved_thread_states", "timeline_position",
})


def build_initial_state(content: dict[str, Any]) -> dict[str, Any]:
    """Construct the first generation content from adopted initial design content."""
    core = content["core"]
    world = content["world"]
    facts: list[dict[str, Any]] = [
        {"fact_id": "fact-000001", "scope": "core", "value": deepcopy(core)},
        {"fact_id": "fact-000002", "scope": "world", "value": deepcopy(world)},
    ]
    cast = content["cast"]
    knowledge_model = content.get("knowledge_model")
    character_knows = knowledge_model.get("character_knows", {}) if isinstance(knowledge_model, dict) else {}
    character_knowledge: dict[str, Any] = {}
    for index, person in enumerate(cast, start=1):
        character_id = f"char-{index:06d}"
        name = person.get("name") if isinstance(person, dict) else None
        public_knowledge = character_knows.get(name, []) if isinstance(character_knows, dict) else []
        if not isinstance(public_knowledge, list):
            public_knowledge = []
        character_knowledge[character_id] = deepcopy(public_knowledge)
        facts.append({
            "fact_id": f"fact-{index + 2:06d}",
            "scope": "character",
            "subject_id": character_id,
            "value": deepcopy(person),
        })

    thread_states: dict[str, Any] = {}
    for thread in content["unresolved_threads"]:
        if not isinstance(thread, dict) or not isinstance(thread.get("name"), str):
            raise ContractError("unresolved_threadのnameが不正です")
        thread_states[thread["name"]] = {"status": "open"}
    return {
        "story_facts": facts,
        "character_knowledge": character_knowledge,
        "reader_disclosures": [],
        "unresolved_thread_states": thread_states,
        "timeline_position": 0,
    }


def apply_continuity_state(old_state: object, continuity: object) -> dict[str, Any]:
    """Apply one validated continuity update deterministically to a generation."""
    if not isinstance(old_state, dict) or set(old_state) != _STATE_FIELDS:
        raise ContractError("current_state contentが不正です")
    if not isinstance(old_state["story_facts"], list) or not isinstance(old_state["character_knowledge"], dict) or not isinstance(old_state["reader_disclosures"], list):
        raise ContractError("current_stateのcollectionが不正です")
    thread_states = old_state.get("unresolved_thread_states")
    if not isinstance(thread_states, dict) or any(
        not isinstance(state, dict) or set(state) != {"status"} or state.get("status") not in {"open", "progressed", "resolved"}
        for state in thread_states.values()
    ):
        raise ContractError("current_state unresolved_thread_statesが不正です")
    canonical_thread_names = set(thread_states)
    if not isinstance(continuity, dict) or not isinstance(continuity.get("changes"), list):
        raise ContractError("continuity_update contentが不正です")
    result = deepcopy(old_state)
    for change in continuity["changes"]:
        if not isinstance(change, dict) or set(change) != {"op", "target", "path", "value", "evidence_locations"}:
            raise ContractError("continuity_update changeが不正です")
        target, path, operation = change["target"], change["path"], change["op"]
        if target not in _STATE_FIELDS or not isinstance(path, str) or operation not in {"set", "add", "remove"}:
            raise ContractError("continuity_update changeが不正です")
        if not isinstance(change["evidence_locations"], list) or not change["evidence_locations"] or any(not isinstance(item, str) or not item for item in change["evidence_locations"]):
            raise ContractError("continuity_update evidence_locationsが不正です")
        if target == "timeline_position":
            value = change["value"]
            if operation != "set" or path != "/timeline_position" or not isinstance(value, int) or isinstance(value, bool) or value < result["timeline_position"]:
                raise ContractError("timeline_positionは非負整数のsetによる単調増加だけを許可します")
        target_id, field, _tokens = binding(result, target, path, operation)
        if target == "unresolved_thread_states" and (
            operation != "set"
            or target_id not in canonical_thread_names
            or field != "status"
            or change["value"] not in {"open", "progressed", "resolved"}
        ):
            raise ContractError("continuity_updateのthread targetがcanonical state外です")
        apply_change(result, target, path, operation, change["value"])
    if set(result) != _STATE_FIELDS:
        raise ContractError("continuity_update適用後のcurrent_stateが不正です")
    if set(result["unresolved_thread_states"]) != canonical_thread_names:
        raise ContractError("continuity_updateでcanonical thread_nameを追加・削除できません")
    return result
