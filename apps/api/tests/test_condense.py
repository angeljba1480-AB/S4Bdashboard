"""Token efficiency: condensation, budget cap, insufficient-answer escalation."""
from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.ai import cascade, condense  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import ModelRoute, Sensitivity  # noqa: E402


def test_looks_insufficient():
    assert condense.looks_insufficient("no sé") is True
    assert condense.looks_insufficient("No tengo información sobre eso en las fuentes.") is True
    assert condense.looks_insufficient("La política de respaldo es diaria y se conserva 30 días, con cifrado AES-256.") is False


def test_within_budget(monkeypatch):
    monkeypatch.setattr(settings, "max_tokens_per_request", 0)
    assert condense.within_budget("lo que sea " * 1000) is True   # 0 = sin tope
    monkeypatch.setattr(settings, "max_tokens_per_request", 5)
    assert condense.within_budget("una frase larga que excede el tope") is False


def test_condense_noop_when_small(monkeypatch):
    monkeypatch.setattr(settings, "condense_threshold_chars", 6000)
    ctx, saved = condense.condense(["texto corto"])
    assert ctx == ["texto corto"] and saved == 0


def test_condense_large_context(monkeypatch):
    monkeypatch.setattr(settings, "condense_enabled", True)
    monkeypatch.setattr(settings, "condense_threshold_chars", 20)
    monkeypatch.setattr(condense, "generate_with_fallback", lambda *a, **k: SimpleNamespace(
        route=ModelRoute.OPEN, response=SimpleNamespace(content="extracto breve", model="open-x")))
    big = ["x" * 500, "y" * 500]
    ctx, saved = condense.condense(big)
    assert ctx == ["extracto breve"] and saved > 0


def test_maybe_refine_escalates_on_insufficient(monkeypatch):
    monkeypatch.setattr(cascade, "premium_available", lambda: True)
    monkeypatch.setattr(cascade, "generate_with_fallback", lambda *a, **k: SimpleNamespace(
        route=ModelRoute.PREMIUM, response=SimpleNamespace(content="RESPUESTA PREMIUM", model="premium-x")))
    decision = SimpleNamespace(redacted=False, classification=Sensitivity.INTERNAL, pii_types=[], context=["ctx"])
    out = cascade.maybe_refine(decision=decision, base_content="no sé",
                               base_route=ModelRoute.OPEN, instruction="x", escalate_if_insufficient=True)
    assert out["escalated"] is True and out["content"] == "RESPUESTA PREMIUM"


def test_budget_blocks_escalation(monkeypatch):
    monkeypatch.setattr(cascade, "premium_available", lambda: True)
    monkeypatch.setattr(settings, "max_tokens_per_request", 1)  # imposible de cumplir
    decision = SimpleNamespace(redacted=False, classification=Sensitivity.INTERNAL, pii_types=[], context=["contexto"])
    out = cascade.maybe_refine(decision=decision, base_content="borrador",
                               base_route=ModelRoute.OPEN, instruction="instrucción larga", want_precision=True)
    assert out["escalated"] is False and out["over_budget"] is True
