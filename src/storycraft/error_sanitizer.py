"""永続化・表示前の例外文字列とcredentialの安全化。"""
from __future__ import annotations

import re


_CONTROL_RE = re.compile(r"[\r\n\t]+")
_SPACES_RE = re.compile(r"\s+")

_URL_USERINFO_RE = re.compile(
    r"(?i)\b([a-z][a-z0-9+.-]*://)"
    r"([^/\s@]+)@"
)

_QUERY_SECRET_RE = re.compile(
    r"(?i)([?&](?:"
    r"api[_-]?key|"
    r"access[_-]?token|"
    r"refresh[_-]?token|"
    r"token|secret|key"
    r")=)([^&#\s]+)"
)

_AUTHORIZATION_RE = re.compile(
    r"(?i)\b("
    r"authorization|proxy-authorization"
    r")\s*[:=]\s*[^,;]+"
)

_NAMED_SECRET_RE = re.compile(
    r"(?i)\b("
    r"x-api-key|"
    r"api[_-]?key|"
    r"access[_-]?token|"
    r"refresh[_-]?token|"
    r"client[_-]?secret|"
    r"token|secret"
    r")\s*[:=]\s*[^,;]+"
)

_BEARER_RE = re.compile(
    r"(?i)\bbearer\s+[^,;]+"
)

_OPENAI_KEY_RE = re.compile(
    r"\bsk-[A-Za-z0-9_-]{8,}\b"
)

_SENSITIVE_LITERAL_RE = re.compile(
    r"(?i)\b(?:"
    r"secret[-_]?token|"
    r"private[-_]?key|"
    r"api[-_]?secret"
    r")(?:\\n|\s+)?[^,;]*"
)


def sanitize_text(
    value: object,
    *,
    max_length: int = 1000,
) -> str:
    """秘密値とlog injection用制御文字を除去する。"""
    text = str(value)
    text = _CONTROL_RE.sub(" ", text)
    text = _SPACES_RE.sub(" ", text).strip()

    text = _URL_USERINFO_RE.sub(
        r"\1[REDACTED]@",
        text,
    )
    text = _QUERY_SECRET_RE.sub(
        r"\1[REDACTED]",
        text,
    )
    text = _AUTHORIZATION_RE.sub(
        r"\1: [REDACTED]",
        text,
    )
    text = _NAMED_SECRET_RE.sub(
        r"\1: [REDACTED]",
        text,
    )
    text = _BEARER_RE.sub(
        "Bearer [REDACTED]",
        text,
    )
    text = _OPENAI_KEY_RE.sub(
        "[REDACTED]",
        text,
    )
    text = _SENSITIVE_LITERAL_RE.sub(
        "[REDACTED]",
        text,
    )

    if max_length < 1:
        return ""

    if len(text) > max_length:
        return text[: max_length - 1] + "…"

    return text


def safe_exception_message(
    error: BaseException,
) -> str:
    """例外型を残し、本文だけを安全化する。"""
    error_type = type(error).__name__
    message = sanitize_text(str(error))

    if not message:
        return error_type

    return f"{error_type}: {message}"
