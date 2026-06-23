"""PII / sensitive-data detection tuned for Mexican enterprise documents.

Detects names, emails, phones, RFC, CURP, CLABE/accounts, addresses and
financial/health/secret markers (blueprint section 5).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Mexican-specific identifiers
RFC_RE = re.compile(r"\b([A-ZÑ&]{3,4})\d{6}([A-Z0-9]{3})\b")
CURP_RE = re.compile(r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b")
CLABE_RE = re.compile(r"\b\d{18}\b")                      # CLABE interbancaria
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")           # tarjeta de crédito
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"\b(?:\+?52[\s-]?)?(?:\d[\s-]?){10}\b")
ACCOUNT_RE = re.compile(r"\b(?:cuenta|account|cta)\b[:\s#]*\d{6,}", re.IGNORECASE)

# Keyword markers (lower-cased match)
FINANCIAL_KW = ("estado de cuenta", "saldo", "nómina", "factura", "monto", "transferencia")
HEALTH_KW = ("diagnóstico", "expediente clínico", "historia clínica", "paciente", "padecimiento")
SECRET_KW = ("api_key", "api key", "secret", "password", "contraseña", "private key", "token de acceso")


@dataclass
class PIIResult:
    types: list[str]
    matches: int
    score: float  # 0..1 risk score

    @property
    def has_pii(self) -> bool:
        return self.matches > 0


def _kw_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(text.count(k) for k in keywords)


def detect_pii(*texts: str | None) -> PIIResult:
    """Scan one or more text fragments and return an aggregated PII result."""
    blob = "\n".join(t for t in texts if t)
    upper = blob.upper()
    lower = blob.lower()

    found: dict[str, int] = {}

    def add(kind: str, count: int) -> None:
        if count:
            found[kind] = found.get(kind, 0) + count

    add("rfc", len(RFC_RE.findall(upper)))
    add("curp", len(CURP_RE.findall(upper)))
    add("clabe", len(CLABE_RE.findall(blob)))
    add("card", len([m for m in CARD_RE.findall(blob) if len(re.sub(r"\D", "", m)) >= 13]))
    add("email", len(EMAIL_RE.findall(blob)))
    add("phone", len(PHONE_RE.findall(blob)))
    add("account", len(ACCOUNT_RE.findall(blob)))
    add("financial", _kw_hits(lower, FINANCIAL_KW))
    add("health", _kw_hits(lower, HEALTH_KW))
    add("secret", _kw_hits(lower, SECRET_KW))

    matches = sum(found.values())
    # Weighted score: hard identifiers and secrets dominate the risk.
    weights = {
        "rfc": 0.25, "curp": 0.3, "clabe": 0.3, "card": 0.35, "account": 0.2,
        "secret": 0.4, "health": 0.3, "financial": 0.15, "email": 0.08, "phone": 0.08,
    }
    raw = sum(weights.get(k, 0.1) * min(v, 3) for k, v in found.items())
    score = round(min(1.0, raw), 3)
    return PIIResult(types=sorted(found.keys()), matches=matches, score=score)
