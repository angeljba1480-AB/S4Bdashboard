"""Provider resilience (blueprint §12: "si un proveedor falla, el router usa
fallback permitido o informa bloqueo seguro").

Fallback never weakens privacy: a request routed LOCAL can only fall back to
LOCAL; a PREMIUM request may fall back to more-private routes (open/vpc/local).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings
from ..models import ModelRoute
from .adapters import ModelResponse, get_adapter

# Lower rank = more private. Fallback may only move to an equal-or-lower rank.
_PRIVACY_RANK = {
    ModelRoute.LOCAL: 0,
    ModelRoute.VPC: 1,
    ModelRoute.OPEN: 2,
    ModelRoute.PREMIUM: 3,
}


@dataclass
class GenerationResult:
    response: ModelResponse
    route: ModelRoute
    fell_back: bool
    error: str = ""


def generate_with_fallback(
    primary: ModelRoute, system: str, prompt: str, context: list[str]
) -> GenerationResult:
    """Try the primary route, then privacy-safe fallbacks in configured order."""
    chosen_rank = _PRIVACY_RANK.get(primary, 0)
    candidates = [primary] + [
        r for name in settings.fallback_routes
        if (r := _route_from_name(name)) and r != primary and _PRIVACY_RANK.get(r, 99) <= chosen_rank
    ]

    last_err = ""
    for i, route in enumerate(candidates):
        try:
            adapter = get_adapter(route)
            resp = adapter.generate(system, prompt, context)
            return GenerationResult(response=resp, route=route, fell_back=i > 0, error=last_err)
        except Exception as exc:  # provider failure -> try next private-safe route
            last_err = f"{route.value}: {exc}"
            continue

    # Everything failed -> safe block (never silently leak or hang).
    return GenerationResult(
        response=ModelResponse(content="", model="—", provider="none"),
        route=ModelRoute.BLOCKED, fell_back=True, error=last_err or "todos los proveedores fallaron",
    )


def _route_from_name(name: str) -> ModelRoute | None:
    try:
        return ModelRoute(name)
    except ValueError:
        return None
