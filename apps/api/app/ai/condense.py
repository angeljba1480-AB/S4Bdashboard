"""Token efficiency: condense large context with the cheap/open model before it
reaches an expensive premium model, and flag answers that look insufficient so
they can be escalated.

Idea (blueprint 'minimizar' aplicado al costo): subir un PDF grande directo a un
modelo premium quema muchos tokens. En su lugar, el modelo barato (NaN/open)
destila el contexto a lo esencial y el premium razona sobre ese extracto chico.
"""
from __future__ import annotations

from .. import runtime_config
from ..models import ModelRoute
from .cost import estimate_tokens
from .resilience import generate_with_fallback

_CONDENSE_SYSTEM = (
    "Condensa el contexto conservando hechos, cifras, nombres, fechas y conclusiones "
    "clave. Sé breve y fiel; no inventes ni opines."
)

# Markers that suggest the cheap model couldn't really answer.
_INSUFFICIENT = (
    "no tengo información", "no se encontr", "no encontré", "no cuento con",
    "no puedo responder", "no hay información", "no dispongo de", "insufficient",
    "i don't have", "no está en las fuentes", "no aparece en",
)


def _chars(context: list[str]) -> int:
    return sum(len(c) for c in context)


def condense(context: list[str], *, route: ModelRoute = ModelRoute.OPEN) -> tuple[list[str], int]:
    """Return (condensed_context, tokens_saved_estimate). No-op if small/disabled."""
    if not runtime_config.condense_enabled() or not context:
        return context, 0
    joined = "\n\n".join(context)
    threshold = runtime_config.condense_threshold_chars()
    if len(joined) <= threshold:
        return context, 0
    before = estimate_tokens(joined)
    # Cap the cheap-side input so the condensation call itself stays cheap.
    capped = joined[: threshold * 6]
    gen = generate_with_fallback(route, _CONDENSE_SYSTEM, "Condensa el siguiente contexto:", [capped])
    if gen.route == ModelRoute.BLOCKED or not gen.response.content:
        return context, 0
    condensed = [gen.response.content]
    saved = max(0, before - estimate_tokens(gen.response.content))
    return condensed, saved


def looks_insufficient(text: str) -> bool:
    """Heuristic: did the cheap model fail to produce a real answer?"""
    t = (text or "").strip().lower()
    if len(t) < 40:
        return True
    return any(m in t for m in _INSUFFICIENT)


def within_budget(*texts: str) -> bool:
    """True if the estimated tokens are under the configured cap (0 = no cap)."""
    cap = runtime_config.max_tokens_per_request()
    if cap <= 0:
        return True
    return estimate_tokens(" ".join(texts)) <= cap
