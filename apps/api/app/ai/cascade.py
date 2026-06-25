"""Model cascade: draft with the cheap/open model, then refine with a premium
public model (Claude/GPT) for advanced tasks — without breaking privacy.

Escalation rules:
- Start with the cheap/open model (NaN) ALWAYS; premium is only an escalation.
- Escalate when requested (manual "máxima precisión") OR when the cheap answer
  looks insufficient ("en caso de no estar de acuerdo"). A static "advanced" flag
  does NOT force premium by itself — NaN first, premium on demand.
- Only if a premium provider is actually configured (si no, se queda en NaN).
- Never escalate sensitive content (PII / confidential / restricted) WITHOUT
  explicit approval — instead we signal `escalation_pending` so the UI can ask.
- The refine step is grounded in the already-minimized + redacted context.
"""
from __future__ import annotations

from ..models import ModelRoute, Sensitivity
from .adapters import MockAdapter, get_adapter
from .condense import condense, looks_insufficient, within_budget
from .resilience import generate_with_fallback

REFINE_SYSTEM = (
    "Eres un revisor experto. Mejora, verifica y profundiza el borrador, "
    "manteniéndote fiel a los hechos del contexto. No inventes. Responde en español."
)


def premium_available() -> bool:
    return not isinstance(get_adapter(ModelRoute.PREMIUM), MockAdapter)


def is_sensitive(decision) -> bool:
    return (
        bool(getattr(decision, "redacted", False))
        or decision.classification in (Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED)
        or bool(decision.pii_types)
    )


def maybe_refine(
    *, decision, base_content: str, base_route: ModelRoute, instruction: str,
    want_precision: bool = False, advanced: bool = False, approved: bool = False,
    escalate_if_insufficient: bool = False,
) -> dict:
    """Return {content, route, model, escalated, escalation_pending, tokens_saved, over_budget}.

    Escalates to premium when requested, when the task is advanced, or when the
    cheap answer looks insufficient. Before paying premium, the (already redacted)
    context is condensed with the cheap model to cut token cost.
    """
    base = {"content": base_content, "route": base_route.value, "model": None,
            "escalated": False, "escalation_pending": False, "tokens_saved": 0, "over_budget": False}

    # NaN first: premium only on explicit "máxima precisión" or a weak answer.
    # `advanced` (static agent flag) is kept for compatibility but no longer forces
    # escalation by itself — that's what made the chat jump straight to premium.
    insufficient = escalate_if_insufficient and looks_insufficient(base_content)
    if not (want_precision or insufficient):
        return base
    if base_route in (ModelRoute.BLOCKED, ModelRoute.PREMIUM):
        return base  # already premium or blocked — nothing to escalate
    if not premium_available():
        return base
    if is_sensitive(decision) and not approved:
        base["escalation_pending"] = True
        return base

    # Condense the context with the cheap model so premium pays for a small input.
    ctx, saved = condense(list(decision.context or []))
    refine_prompt = (
        f"Instrucción original: {instruction}\n\n"
        f"Borrador a mejorar:\n{base_content}\n\n"
        "Entrega una versión mejorada: más precisa, completa y bien estructurada."
    )
    if not within_budget(refine_prompt, *ctx):
        base["over_budget"] = True
        base["tokens_saved"] = saved
        return base  # over the per-request token cap even after condensing → stay cheap

    gen = generate_with_fallback(ModelRoute.PREMIUM, REFINE_SYSTEM, refine_prompt, ctx)
    if gen.route == ModelRoute.BLOCKED or not gen.response.content:
        return {**base, "tokens_saved": saved}
    return {"content": gen.response.content, "route": gen.route.value, "model": gen.response.model,
            "escalated": True, "escalation_pending": False, "tokens_saved": saved, "over_budget": False}
