"""Model cascade (draft → refine with premium) + privacy gating."""
from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.ai import cascade  # noqa: E402
from app.models import ModelRoute, Sensitivity  # noqa: E402


def _decision(sensitive: bool):
    return SimpleNamespace(
        redacted=sensitive,
        classification=Sensitivity.CONFIDENTIAL if sensitive else Sensitivity.INTERNAL,
        pii_types=["email"] if sensitive else [],
        context=["contexto seguro"],
    )


def _fake_refined(monkeypatch):
    monkeypatch.setattr(cascade, "premium_available", lambda: True)
    monkeypatch.setattr(cascade, "generate_with_fallback", lambda *a, **k: SimpleNamespace(
        route=ModelRoute.PREMIUM, response=SimpleNamespace(content="REFINADO", model="premium-x")))


def test_not_eligible_returns_base(monkeypatch):
    _fake_refined(monkeypatch)
    out = cascade.maybe_refine(decision=_decision(False), base_content="borrador",
                               base_route=ModelRoute.OPEN, instruction="x")
    assert out["escalated"] is False and out["content"] == "borrador"


def test_non_sensitive_precision_escalates(monkeypatch):
    _fake_refined(monkeypatch)
    out = cascade.maybe_refine(decision=_decision(False), base_content="borrador",
                               base_route=ModelRoute.OPEN, instruction="x", want_precision=True)
    assert out["escalated"] is True and out["content"] == "REFINADO" and out["route"] == "premium"


def test_advanced_alone_does_not_escalate(monkeypatch):
    # NaN primero: la marca 'advanced' por sí sola NO sube a premium; se requiere
    # 'máxima precisión' o que la respuesta sea insuficiente.
    _fake_refined(monkeypatch)
    out = cascade.maybe_refine(decision=_decision(False), base_content="una respuesta amplia y suficiente",
                               base_route=ModelRoute.OPEN, instruction="x", advanced=True)
    assert out["escalated"] is False


def test_insufficient_answer_escalates(monkeypatch):
    # "en caso de no estar de acuerdo": si el borrador barato es pobre, escala.
    _fake_refined(monkeypatch)
    out = cascade.maybe_refine(decision=_decision(False), base_content="no sé",
                               base_route=ModelRoute.OPEN, instruction="x",
                               escalate_if_insufficient=True)
    assert out["escalated"] is True


def test_sensitive_needs_approval(monkeypatch):
    _fake_refined(monkeypatch)
    out = cascade.maybe_refine(decision=_decision(True), base_content="b",
                               base_route=ModelRoute.VPC, instruction="x", want_precision=True)
    assert out["escalated"] is False and out["escalation_pending"] is True


def test_sensitive_with_approval_escalates(monkeypatch):
    _fake_refined(monkeypatch)
    out = cascade.maybe_refine(decision=_decision(True), base_content="b",
                               base_route=ModelRoute.VPC, instruction="x", want_precision=True, approved=True)
    assert out["escalated"] is True


def test_no_premium_no_escalation(monkeypatch):
    monkeypatch.setattr(cascade, "premium_available", lambda: False)
    out = cascade.maybe_refine(decision=_decision(False), base_content="b",
                               base_route=ModelRoute.OPEN, instruction="x", want_precision=True)
    assert out["escalated"] is False and out["escalation_pending"] is False
