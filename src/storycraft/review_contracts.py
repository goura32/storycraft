"""Review／Revisionで使用するfield path契約。"""
from __future__ import annotations

import json
import re
from typing import Any

from .series_contracts import ContractError


FieldToken = str | int
FieldPath = tuple[FieldToken, ...]


def field_tokens(field: str) -> FieldPath:
    """Review fieldをCandidate内のpathへ変換する。"""
    if field.startswith("$."):
        field = field[2:]
    elif field == "$":
        return ()

    tokens: list[FieldToken] = []
    position = 0

    while position < len(field):
        if field[position] == "[":
            index_match = re.match(
                r"\[(\d+)\]",
                field[position:],
            )
            if index_match is not None:
                tokens.append(int(index_match.group(1)))
                position += index_match.end()
            else:
                key_match = re.match(
                    r'\[("(?:[^"\\]|\\.)*")\]',
                    field[position:],
                )
                if key_match is None:
                    raise ContractError(
                        "批評 issue の field パスが不正です"
                    )
                try:
                    tokens.append(
                        json.loads(key_match.group(1))
                    )
                except json.JSONDecodeError as exc:
                    raise ContractError(
                        "批評 issue の field パスが不正です"
                    ) from exc
                position += key_match.end()
        else:
            name_match = re.match(
                r"[A-Za-z_][A-Za-z0-9_]*",
                field[position:],
            )
            if name_match is None:
                raise ContractError(
                    "批評 issue の field パスが不正です"
                )
            tokens.append(name_match.group(0))
            position += name_match.end()

        if (
            position < len(field)
            and field[position] == "."
        ):
            position += 1
        elif (
            position < len(field)
            and field[position] != "["
        ):
            raise ContractError(
                "批評 issue の field パスが不正です"
            )

    return tuple(tokens)


def validate_critique_fields(
    critique: dict[str, Any],
    candidate: dict[str, Any],
) -> None:
    """全Review IssueがCandidate内のfieldを指すことを検証する。"""
    for issue in critique["issues"]:
        value: Any = candidate

        for token in field_tokens(issue["field"]):
            if (
                isinstance(value, dict)
                and isinstance(token, str)
                and token in value
            ):
                value = value[token]
            elif (
                isinstance(value, list)
                and isinstance(token, int)
                and 0 <= token < len(value)
            ):
                value = value[token]
            else:
                raise ContractError(
                    "批評 issue の field が候補を指しません"
                )


def validate_revision_scope(
    candidate: dict[str, Any],
    revised: dict[str, Any],
    critique: dict[str, Any],
) -> None:
    """RevisionがReviewで指摘されたfieldだけを変更したか検証する。"""
    allowed = [
        field_tokens(issue["field"])
        for issue in critique["issues"]
    ]

    for path in _changed_paths(candidate, revised):
        if not any(
            path[: len(cited)] == cited
            for cited in allowed
        ):
            raise ContractError(
                "修正版が批評で引用されていないfieldを"
                "変更しています"
            )


def _changed_paths(
    before: Any,
    after: Any,
    prefix: FieldPath = (),
) -> set[FieldPath]:
    """二つのJSON互換値で変更された末端pathを返す。"""
    if type(before) is not type(after):
        return {prefix}

    if isinstance(before, dict):
        paths: set[FieldPath] = set()

        for key in set(before) | set(after):
            child_path = prefix + (key,)

            if key not in before or key not in after:
                paths.add(child_path)
            else:
                paths |= _changed_paths(
                    before[key],
                    after[key],
                    child_path,
                )

        return paths

    if isinstance(before, list):
        if len(before) != len(after):
            return {prefix}

        paths: set[FieldPath] = set()

        for index, (old, new) in enumerate(
            zip(before, after)
        ):
            paths |= _changed_paths(
                old,
                new,
                prefix + (index,),
            )

        return paths

    return {prefix} if before != after else set()
