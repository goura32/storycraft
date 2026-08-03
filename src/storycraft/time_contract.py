"""Strict UTC RFC 3339 timestamps used by persisted V2 records."""
from __future__ import annotations

from datetime import datetime, timedelta
import re

from .series_contracts import ContractError


_UTC_RFC3339 = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]+)?(?:Z|\+00:00)"
)


def parse_utc_timestamp(value: object, label: str = "timestamp") -> datetime:
    """Parse the closed persisted timestamp form and require UTC explicitly."""
    if not isinstance(value, str) or _UTC_RFC3339.fullmatch(value) is None:
        raise ContractError(f"{label}はUTC RFC3339文字列でなければなりません")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError(f"{label}はUTC RFC3339文字列でなければなりません") from exc
    if parsed.utcoffset() != timedelta(0):
        raise ContractError(f"{label}はUTC RFC3339文字列でなければなりません")
    return parsed
