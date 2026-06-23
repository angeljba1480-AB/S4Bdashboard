"""Data sensitivity classifier (blueprint section 5).

Maps content -> PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED. The class drives
the model route and permissions. Heuristic + PII-driven; designed to be
replaceable by an ML classifier behind the same interface.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..models import Sensitivity
from .pii import PIIResult, detect_pii

RESTRICTED_KW = (
    "restringido", "restricted", "clasificado", "alto secreto",
    "private key", "llave privada", "credencial", "ciberseguridad ofensiva",
)
CONFIDENTIAL_KW = (
    "confidencial", "confidential", "contrato", "nda", "acuerdo de confidencialidad",
    "propiedad intelectual", "estados financieros", "due diligence", "salarial",
)
INTERNAL_KW = (
    "interno", "internal", "borrador", "uso interno", "memo", "minuta",
)
PUBLIC_KW = (
    "público", "public", "comunicado", "press release", "marketing", "blog",
)


@dataclass
class Classification:
    sensitivity: Sensitivity
    pii: PIIResult
    reasons: list[str]


def _kw(text: str, words: tuple[str, ...]) -> list[str]:
    return [w for w in words if w in text]


def classify_data(*texts: str | None) -> Classification:
    blob = "\n".join(t for t in texts if t)
    lower = blob.lower()
    pii = detect_pii(blob)
    reasons: list[str] = []

    level = Sensitivity.INTERNAL  # safe default: never assume PUBLIC

    # Keyword signals (most-sensitive wins)
    if (hits := _kw(lower, RESTRICTED_KW)):
        level = Sensitivity.RESTRICTED
        reasons.append(f"keywords restringidas: {', '.join(hits)}")
    elif (hits := _kw(lower, CONFIDENTIAL_KW)):
        level = Sensitivity.CONFIDENTIAL
        reasons.append(f"keywords confidenciales: {', '.join(hits)}")
    elif (hits := _kw(lower, PUBLIC_KW)) and not _kw(lower, INTERNAL_KW):
        level = Sensitivity.PUBLIC
        reasons.append(f"keywords públicas: {', '.join(hits)}")
    elif (hits := _kw(lower, INTERNAL_KW)):
        level = Sensitivity.INTERNAL
        reasons.append(f"keywords internas: {', '.join(hits)}")

    # PII can only escalate, never downgrade.
    order = [Sensitivity.PUBLIC, Sensitivity.INTERNAL, Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED]
    if pii.has_pii:
        if any(t in pii.types for t in ("curp", "clabe", "card", "secret", "health")):
            pii_level = Sensitivity.RESTRICTED
            reasons.append(f"PII crítico detectado: {', '.join(pii.types)}")
        elif pii.score >= 0.2:
            pii_level = Sensitivity.CONFIDENTIAL
            reasons.append(f"PII detectado (score {pii.score}): {', '.join(pii.types)}")
        else:
            pii_level = Sensitivity.INTERNAL
            reasons.append(f"PII leve: {', '.join(pii.types)}")
        if order.index(pii_level) > order.index(level):
            level = pii_level

    if not reasons:
        reasons.append("sin señales fuertes; default INTERNAL")

    return Classification(sensitivity=level, pii=pii, reasons=reasons)
