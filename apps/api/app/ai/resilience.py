"""Provider resilience (blueprint §12: "si un proveedor falla, el router usa
fallback permitido o informa bloqueo seguro").

Fallback never weakens privacy: a request routed LOCAL can only fall back to
LOCAL; a PREMIUM request may fall back to more-private routes (open/vpc/local).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import settings
from ..models import ModelRoute
from .adapters import MockAdapter, ModelResponse, get_adapter

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


def _real_routes() -> list[ModelRoute]:
    """Routes that have a real (non-MOCK) provider configured, most→least private."""
    order = [ModelRoute.LOCAL, ModelRoute.VPC, ModelRoute.OPEN, ModelRoute.PREMIUM]
    return [r for r in order if not isinstance(get_adapter(r), MockAdapter)]


def generate_with_fallback(
    primary: ModelRoute, system: str, prompt: str, context: list[str]
) -> GenerationResult:
    """Try the primary route, then privacy-safe fallbacks in configured order.

    Order of attempts:
      1. Real (non-MOCK) providers on the primary route and equal/more-private
         routes — never weakening privacy.
      2. (opt-in) If no private real provider exists and ALLOW_CLOUD_FALLBACK is
         set, climb to the best available real provider (open/premium) instead of
         returning the offline MOCK. This is the only step that can move to a
         less-private route, and it is disabled by default.
      3. Offline-safe MOCK on the primary route (deterministic, grounded).
    """
    chosen_rank = _PRIVACY_RANK.get(primary, 0)
    safe = [primary]
    for name in settings.fallback_routes:
        r = _route_from_name(name)
        if r and r not in safe and _PRIVACY_RANK.get(r, 99) <= chosen_rank:
            safe.append(r)

    last_err = ""

    def _try(route: ModelRoute) -> ModelResponse | None:
        nonlocal last_err
        try:
            return get_adapter(route).generate(system, prompt, context)
        except Exception as exc:  # provider failure -> try next route
            last_err = f"{route.value}: {exc}"
            return None

    # 1) Real, privacy-safe providers first (don't settle for MOCK yet).
    for route in safe:
        if isinstance(get_adapter(route), MockAdapter):
            continue
        if (resp := _try(route)) is not None:
            return GenerationResult(resp, route, fell_back=route != primary, error=last_err)

    # 2) Opt-in: climb to a real cloud provider when no private one is available.
    if settings.allow_cloud_fallback:
        for route in _real_routes():
            if route in safe:
                continue
            if (resp := _try(route)) is not None:
                return GenerationResult(resp, route, fell_back=True, error=last_err)

    # 3) Offline-safe: MOCK on a privacy-safe route (primary first, then more
    #    private), preserving the privacy-safe fallback when no real provider works.
    for route in safe:
        if (resp := _try(route)) is not None:
            return GenerationResult(resp, route, fell_back=route != primary, error=last_err)

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
