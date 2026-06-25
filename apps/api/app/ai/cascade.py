"""Model cascade: draft with the cheap/open model, then refine with a premium
public model (Claude/GPT) for advanced tasks — without breaking privacy.

Escalation rules:
- Only when requested (manual "máxima precisión") OR the task is marked advanced.
- Only if a premium provider is actually configured.
- Never escalate sensitive content (PII / confidential / restricted) WITHOUT
  explicit approval — instead we signal `escalation_pending` so the UI can ask.
- The refine step is grounded in the already-minimized + redacted context.
"""
from __future__ import annotations

from ..models import ModelRoute, Sensitivity
from .adapters import MockAdapter, get_adapter
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
) -> dict:
    """Return {content, route, model, escalated, escalation_pending}."""
    base = {"content": base_content, "route": base_route.value, "model": None,
            "escalated": False, "escalation_pending": False}

    if not (want_precision or advanced):
        return base
    if base_route in (ModelRoute.BLOCKED, ModelRoute.PREMIUM):
        return base  # already premium or blocked — nothing to escalate
    if not premium_available():
        return base
    if is_sensitive(decision) and not approved:
        base["escalation_pending"] = True
        return base

    refine_prompt = (
        f"Instrucción original: {instruction}\n\n"
        f"Borrador a mejorar:\n{base_content}\n\n"
        "Entrega una versión mejorada: más precisa, completa y bien estructurada."
    )
    gen = generate_with_fallback(ModelRoute.PREMIUM, REFINE_SYSTEM, refine_prompt, decision.context)
    if gen.route == ModelRoute.BLOCKED or not gen.response.content:
        return base
    return {"content": gen.response.content, "route": gen.route.value,
            "model": gen.response.model, "escalated": True, "escalation_pending": False}
