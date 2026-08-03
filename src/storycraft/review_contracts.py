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
                    r'\[("([^"\\]|\\.)*")\]',
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
    """JSON path evidence locationsがCandidate内を指すことを検証する。"""
    for issue in critique["issues"]:
        locations = issue.get("evidence_locations", [])
        json_locations = [location for location in locations if isinstance(location, str) and location.startswith("$")]
        for location in json_locations:
            value: Any = candidate
            for token in field_tokens(location):
                if isinstance(value, dict) and isinstance(token, str) and token in value:
                    value = value[token]
                elif isinstance(value, list) and isinstance(token, int) and 0 <= token < len(value):
                    value = value[token]
                else:
                    raise ContractError("批評 issue の evidence_locations が候補を指しません")


def validate_revision_scope(
    candidate: dict[str, Any],
    revised: dict[str, Any],
    critique: dict[str, Any],
) -> None:
    """RevisionがReviewで指摘されたfieldだけを変更したか検証する。

    V1 spec: 修正は生成物全体を置き換えられます。指摘は優先して直すべき問題を示しますが、
    修正可能範囲を制限しません。全体の整合性または品質改善のため、指摘対象外も変更できます。
    ただし、形式、必須項目、識別子、参照、更新可能範囲の契約は必ず守ります。
    """
    # V1では修正範囲を制限しない。ただし、形式・必須項目・識別子・参照・更新可能範囲の契約は必ず守る必要がある。
    # それらは別途 validator で検証されるため、ここでは何もしない。
    return