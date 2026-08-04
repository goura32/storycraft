"""Deterministic JSON path handling for scene continuity changes."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .series_contracts import ContractError


def path_tokens(target: str, path: object) -> list[str]:
    """Parse canonical JSON Pointer and the legacy dotted root notation."""
    if not isinstance(path, str):
        raise ContractError("continuity_update pathが不正です")
    pointer_prefix = f"/{target}"
    dotted_prefix = f"$.{target}"
    if path == pointer_prefix:
        return [target]
    if path.startswith(pointer_prefix + "/"):
        raw = path[1:].split("/")
        if raw[0] != target:
            raise ContractError("continuity_update pathが不正です")
        tokens: list[str] = []
        for token in raw:
            position = 0
            while position < len(token):
                if token[position] == "~":
                    if position + 1 >= len(token) or token[position + 1] not in {"0", "1"}:
                        raise ContractError("continuity_update pathのJSON Pointer escapeが不正です")
                    position += 2
                else:
                    position += 1
            decoded = token.replace("~1", "/").replace("~0", "~")
            if decoded == "":
                raise ContractError("continuity_update pathが不正です")
            tokens.append(decoded)
        return tokens
    if path == dotted_prefix:
        return [target]
    if path.startswith(dotted_prefix + "."):
        suffix = path[len(dotted_prefix) + 1 :]
        parts = suffix.split(".")
        if not parts or any(not part for part in parts):
            raise ContractError("continuity_update pathが不正です")
        return [target, *parts]
    raise ContractError("continuity_update pathが不正です")


def _list_index(values: list[Any], selector: str, *, allow_append: bool = False) -> int | None:
    if selector == "-":
        return None if allow_append else (_raise_path())
    if selector.isdigit():
        if len(selector) > 1 and selector.startswith("0"):
            raise ContractError("continuity_update pathのarray indexが不正です")
        index = int(selector)
        if 0 <= index < len(values):
            return index
        raise ContractError("continuity_update pathが現在stateにありません")
    for index, item in enumerate(values):
        if isinstance(item, dict):
            for key in ("fact_id", "disclosure_id", "item_id", "id"):
                if item.get(key) == selector:
                    return index
    raise ContractError("continuity_update pathが現在stateにありません")


def _raise_path() -> None:
    raise ContractError("continuity_update pathが現在stateにありません")


def _canonical_id(item: object, selector: str) -> str:
    if isinstance(item, dict):
        for key in ("fact_id", "disclosure_id", "item_id", "id"):
            value = item.get(key)
            if isinstance(value, str) and value:
                return value
    return selector


def resolve_selector(container: object, selector: str, *, allow_append: bool = False) -> tuple[object, str]:
    """Resolve a mapping key, array index, or canonical array ID."""
    if isinstance(container, list):
        index = _list_index(container, selector, allow_append=allow_append)
        if index is None:
            return "-", selector
        return index, _canonical_id(container[index], selector)
    if isinstance(container, dict) and selector in container:
        return selector, selector
    raise ContractError("continuity_update pathが現在stateにありません")


def binding(state: dict[str, Any], target: str, path: object, operation: str) -> tuple[str, str, list[str]]:
    """Return the allowed-update ID and field for a change path."""
    tokens = path_tokens(target, path)
    if target == "timeline_position":
        if tokens != [target]:
            raise ContractError("timeline_positionのpathが不正です")
        return target, "value", tokens
    container = state.get(target)
    if len(tokens) == 1:
        if not isinstance(container, (dict, list)):
            raise ContractError("continuity_update targetが現在stateにありません")
        return target, "item", tokens
    selector = tokens[1]
    resolved, canonical = resolve_selector(
        container,
        selector,
        allow_append=operation == "add" and len(tokens) == 2,
    )
    del resolved
    field = tokens[2] if len(tokens) > 2 else "item"
    return canonical, field, tokens


def _resolve_child(parent: object, token: str, *, final_add: bool = False) -> object:
    if isinstance(parent, list):
        index, _ = resolve_selector(parent, token, allow_append=final_add)
        return index
    if isinstance(parent, dict) and token in parent:
        return token
    raise ContractError("continuity_update pathが現在stateにありません")


def apply_change(state: dict[str, Any], target: str, path: object, operation: str, value: object) -> None:
    """Apply one already contract-checked change in place."""
    tokens = path_tokens(target, path)
    parent: object = state
    for token in tokens[:-1]:
        child = _resolve_child(parent, token)
        if isinstance(parent, list):
            assert isinstance(child, int)
            parent = parent[child]
        else:
            assert isinstance(parent, dict)
            assert isinstance(child, str)
            parent = parent[child]
    key = tokens[-1]
    if isinstance(parent, list):
        if operation == "add" and key == "-":
            parent.append(deepcopy(value))
            return
        resolved, _ = resolve_selector(parent, key)
        assert isinstance(resolved, int)
        if operation == "set":
            parent[resolved] = deepcopy(value)
        elif operation == "remove":
            del parent[resolved]
        elif operation == "add":
            parent.insert(resolved, deepcopy(value))
        else:
            raise ContractError("continuity_update opが不正です")
        return
    if not isinstance(parent, dict):
        raise ContractError("continuity_update pathが現在stateにありません")
    if operation == "set":
        if key not in parent:
            raise ContractError("continuity_update set先がありません")
        parent[key] = deepcopy(value)
    elif operation == "add":
        if key in parent and isinstance(parent[key], list):
            parent[key].append(deepcopy(value))
        elif key not in parent:
            parent[key] = deepcopy(value)
        else:
            raise ContractError("continuity_update add先が不正です")
    elif operation == "remove":
        if key not in parent:
            raise ContractError("continuity_update remove先がありません")
        del parent[key]
    else:
        raise ContractError("continuity_update opが不正です")
