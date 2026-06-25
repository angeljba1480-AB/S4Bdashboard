"""Runtime, admin-editable config (token efficiency / budget) with a memory cache.

Values live in the platform_settings table and override the env defaults from
`settings`. The cache is loaded at startup and refreshed on every write, so the
generation path reads them without a DB hit.
"""
from __future__ import annotations

from sqlmodel import Session, select

from .config import settings

# In-memory cache: key -> str value.
_CACHE: dict[str, str] = {}

# Keys + their env fallback.
KEYS = {
    "condense_enabled": lambda: str(settings.condense_enabled).lower(),
    "condense_threshold_chars": lambda: str(settings.condense_threshold_chars),
    "max_tokens_per_request": lambda: str(settings.max_tokens_per_request),
    "tokens_saved_total": lambda: "0",
}


def load(session: Session) -> None:
    from .models import PlatformSetting

    _CACHE.clear()
    for row in session.exec(select(PlatformSetting)).all():
        _CACHE[row.key] = row.value


def _raw(key: str) -> str:
    if key in _CACHE:
        return _CACHE[key]
    fallback = KEYS.get(key)
    return fallback() if fallback else ""


def set_value(session: Session, key: str, value: str) -> None:
    from .models import PlatformSetting

    row = session.get(PlatformSetting, key) or PlatformSetting(key=key)
    row.value = str(value)
    session.add(row)
    session.commit()
    _CACHE[key] = str(value)


# --- typed accessors (used by the generation path) --------------------------
def condense_enabled() -> bool:
    return _raw("condense_enabled").strip().lower() in ("1", "true", "yes", "on")


def condense_threshold_chars() -> int:
    try:
        return int(_raw("condense_threshold_chars"))
    except (ValueError, TypeError):
        return settings.condense_threshold_chars


def max_tokens_per_request() -> int:
    try:
        return int(_raw("max_tokens_per_request"))
    except (ValueError, TypeError):
        return settings.max_tokens_per_request


def tokens_saved_total() -> int:
    try:
        return int(_raw("tokens_saved_total"))
    except (ValueError, TypeError):
        return 0


def add_tokens_saved(session: Session, n: int) -> None:
    """Accumulate the tokens saved by condensation (best-effort)."""
    if n and n > 0:
        set_value(session, "tokens_saved_total", str(tokens_saved_total() + int(n)))
