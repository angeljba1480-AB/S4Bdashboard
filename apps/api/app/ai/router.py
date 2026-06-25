"""Privacy Model Router (blueprint section 6).

The user never picks a model. Given sensitivity, PII, task and policy, the
router decides: LOCAL, VPC, OPEN, PREMIUM or BLOCKED — and always leaves an
auditable reason. This is the strategic core of the platform.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import Agent, ModelRoute, Sensitivity, Tenant
from ..security.classifier import Classification, classify_data
from ..security.dlp import minimize_context, redact
from ..security.policy import Policy, load_policy, violates_policy


@dataclass
class RouteDecision:
    route: ModelRoute
    classification: Sensitivity
    pii_types: list[str]
    pii_score: float
    reason: str
    audit_required: bool
    redacted: bool
    context: list[str] = field(default_factory=list)
    policy_reasons: list[str] = field(default_factory=list)


def route_request(
    tenant: Tenant,
    agent: Agent | None,
    prompt: str,
    context_chunks: list[str],
    task: str = "chat",
) -> RouteDecision:
    """Implements the decision tree from the blueprint pseudocode."""
    classification: Classification = classify_data(prompt, *context_chunks)
    sensitivity = classification.sensitivity
    pii = classification.pii
    policy: Policy = load_policy(tenant, agent)

    # 1. Hard policy violations -> BLOCK
    decision = violates_policy(policy, sensitivity, pii, task=prompt)
    if decision.blocked:
        return RouteDecision(
            route=ModelRoute.BLOCKED,
            classification=sensitivity,
            pii_types=pii.types,
            pii_score=pii.score,
            reason=f"BLOQUEADO: {decision.reason}",
            audit_required=True,
            redacted=False,
            policy_reasons=classification.reasons,
        )

    # 2. Minimize + redact context before anything leaves the policy boundary.
    minimized = minimize_context(context_chunks)
    needs_redaction = pii.has_pii or sensitivity in (Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED)
    safe_context = [redact(c) for c in minimized] if needs_redaction else minimized

    def build(route: ModelRoute, reason: str) -> RouteDecision:
        return RouteDecision(
            route=route,
            classification=sensitivity,
            pii_types=pii.types,
            pii_score=pii.score,
            reason=reason,
            audit_required=route in (ModelRoute.LOCAL, ModelRoute.VPC) or needs_redaction or route == ModelRoute.BLOCKED,
            redacted=needs_redaction,
            context=safe_context,
            policy_reasons=classification.reasons,
        )

    # 3. RESTRICTED -> always local, never leaves.
    if sensitivity == Sensitivity.RESTRICTED:
        return build(ModelRoute.LOCAL, "Datos RESTRICTED: procesamiento local obligatorio, sin salida externa")

    # 4. CONFIDENTIAL -> VPC if allowed, else local.
    if sensitivity == Sensitivity.CONFIDENTIAL:
        if policy.allows_vpc:
            return build(ModelRoute.VPC, "Datos CONFIDENTIAL: VPC privada con auditoría")
        return build(ModelRoute.LOCAL, "Datos CONFIDENTIAL sin VPC permitida: fallback local")

    # 5. PII present but not high sensitivity -> never to external by default.
    if pii.has_pii and policy.no_external_pii:
        if policy.allows_vpc:
            return build(ModelRoute.VPC, "PII detectado: se mantiene en VPC privada (no externa)")
        return build(ModelRoute.LOCAL, "PII detectado sin VPC: fallback local")

    # 6. INTERNAL / PUBLIC -> always START on the cheap open model (NaN). Premium
    #    is never the base route: it's an on-demand cascade escalation (máxima
    #    precisión / respuesta insuficiente), so non-sensitive work begins on NaN
    #    and only sube a premium si no convence. Esto también evita prometer
    #    "premium" cuando no hay proveedor premium configurado.
    if policy.allows_external:
        return build(ModelRoute.OPEN,
                     "Datos no sensibles: empieza con el modelo abierto (NaN); "
                     "escala a premium solo si pides máxima precisión o la respuesta es insuficiente")

    # 7. External not allowed by policy -> keep private.
    if policy.allows_vpc:
        return build(ModelRoute.VPC, "Política sin salida externa: VPC privada")
    return build(ModelRoute.LOCAL, "Política sin salida externa ni VPC: local")
