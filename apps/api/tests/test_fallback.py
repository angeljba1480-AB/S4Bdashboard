"""Provider resilience tests: privacy-safe fallback chain."""
from __future__ import annotations

import app.ai.resilience as resilience
from app.ai.adapters import MockAdapter, ModelResponse
from app.models import ModelRoute


class _FailingAdapter:
    def __init__(self, route):
        self.route = route
        self.model_name = f"broken-{route.value}"

    def generate(self, system, prompt, context):
        raise RuntimeError("provider down")


def test_fallback_to_more_private_route(monkeypatch):
    # premium fails -> should fall back to a privacy-safe route (open/vpc/local).
    def fake_get_adapter(route):
        if route == ModelRoute.PREMIUM:
            return _FailingAdapter(route)
        return MockAdapter(route, route.value)

    monkeypatch.setattr(resilience, "get_adapter", fake_get_adapter)
    result = resilience.generate_with_fallback(ModelRoute.PREMIUM, "sys", "hola", [])
    assert result.fell_back is True
    assert result.route in (ModelRoute.VPC, ModelRoute.OPEN, ModelRoute.LOCAL)
    assert isinstance(result.response, ModelResponse)


def test_local_never_falls_back_to_external(monkeypatch):
    # If LOCAL fails, fallback must NOT escalate to a less private route.
    monkeypatch.setattr(resilience, "get_adapter", lambda route: _FailingAdapter(route))
    result = resilience.generate_with_fallback(ModelRoute.LOCAL, "sys", "hola", [])
    # All candidates are local-rank; everything failed -> safe block, not external.
    assert result.route == ModelRoute.BLOCKED
    assert result.error


def test_no_fallback_when_primary_ok(monkeypatch):
    monkeypatch.setattr(resilience, "get_adapter", lambda route: MockAdapter(route, route.value))
    result = resilience.generate_with_fallback(ModelRoute.OPEN, "sys", "hola", [])
    assert result.fell_back is False
    assert result.route == ModelRoute.OPEN
