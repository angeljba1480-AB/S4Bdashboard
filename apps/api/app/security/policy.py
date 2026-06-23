"""Policy engine (blueprint sections 5 & 6).

Holds the per-tenant/agent privacy policy and decides whether a request
violates it. Decoupled from the router so policies can later be data-driven
(YAML / DB) without touching routing logic.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Agent, Sensitivity, Tenant
from .pii import PIIResult


@dataclass
class Policy:
    allows_external: bool
    allows_vpc: bool
    no_external_pii: bool = True   # PII never leaves to external providers by default
    privacy_mode: str = "auto"     # auto | local_only | no_external


def load_policy(tenant: Tenant, agent: Agent | None = None) -> Policy:
    mode = agent.privacy_mode if agent else "auto"
    allows_external = tenant.allows_external and mode not in ("local_only", "no_external")
    allows_vpc = tenant.allows_vpc and mode != "local_only"
    return Policy(
        allows_external=allows_external,
        allows_vpc=allows_vpc,
        no_external_pii=True,
        privacy_mode=mode,
    )


@dataclass
class PolicyDecision:
    blocked: bool
    reason: str = ""


def violates_policy(
    policy: Policy,
    classification: Sensitivity,
    pii: PIIResult,
    task: str = "",
) -> PolicyDecision:
    """Return a block decision when the request cannot be processed safely."""
    # Detect prompt-injection / exfiltration attempts in the task itself.
    lowered = task.lower()
    exfil_markers = ("ignora", "ignore previous", "exfiltra", "envía todos los documentos",
                     "reveal system prompt", "muestra el system prompt", "disable policy")
    if any(m in lowered for m in exfil_markers):
        return PolicyDecision(blocked=True, reason="Posible prompt injection / exfiltración")

    # RESTRICTED / CONFIDENTIAL / PII are never blocked here — the router keeps
    # them local or in VPC downstream. Only hard violations (above) block.
    return PolicyDecision(blocked=False)
