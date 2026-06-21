"""DLP: context minimization and PII redaction (blueprint section 5)."""
from __future__ import annotations

from .pii import (
    ACCOUNT_RE,
    CARD_RE,
    CLABE_RE,
    CURP_RE,
    EMAIL_RE,
    PHONE_RE,
    RFC_RE,
)

_REDACTIONS = [
    (CURP_RE, "[CURP]"),
    (RFC_RE, "[RFC]"),
    (CLABE_RE, "[CLABE]"),
    (CARD_RE, "[TARJETA]"),
    (EMAIL_RE, "[EMAIL]"),
    (PHONE_RE, "[TEL]"),
    (ACCOUNT_RE, "[CUENTA]"),
]


def redact(text: str) -> str:
    """Replace detected identifiers with reversible-looking tokens."""
    out = text
    for pattern, token in _REDACTIONS:
        out = pattern.sub(token, out)
    return out


def minimize_context(chunks: list[str], max_chars: int = 6000) -> list[str]:
    """Send only what is necessary — never whole documents unless authorized."""
    selected: list[str] = []
    budget = max_chars
    for c in chunks:
        if budget <= 0:
            break
        snippet = c[:budget]
        selected.append(snippet)
        budget -= len(snippet)
    return selected
