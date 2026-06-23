"""Token and cost estimation per message / route (blueprint: cost meter)."""
from __future__ import annotations

from ..models import ModelRoute

# Indicative USD per 1K tokens (input+output blended) per route.
_COST_PER_1K = {
    ModelRoute.LOCAL: 0.0,
    ModelRoute.VPC: 0.0004,
    ModelRoute.OPEN: 0.0008,
    ModelRoute.PREMIUM: 0.005,
    ModelRoute.BLOCKED: 0.0,
}


def estimate_tokens(text: str) -> int:
    """Rough heuristic: ~4 chars per token."""
    return max(1, len(text) // 4)


def estimate_cost(route: ModelRoute, tokens: int) -> float:
    return round(_COST_PER_1K.get(route, 0.0) * (tokens / 1000), 6)
