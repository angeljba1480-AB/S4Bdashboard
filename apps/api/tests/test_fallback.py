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


class _RealAdapter:
    """A non-MOCK adapter standing in for a configured cloud provider."""

    def __init__(self, route):
        self.route = route
        self.model_name = f"real-{route.value}"

    def generate(self, system, prompt, context):
        return ModelResponse(content="contenido real", model=self.model_name, provider="real")


def _adapters_local_mock_open_real(route):
    # LOCAL has no real provider (MOCK); OPEN is a real cloud provider.
    return _RealAdapter(route) if route == ModelRoute.OPEN else MockAdapter(route, route.value)


def test_cloud_fallback_off_keeps_private_route_on_mock(monkeypatch):
    # Default: a private route with only MOCK must NOT climb to the cloud.
    monkeypatch.setattr(resilience, "get_adapter", _adapters_local_mock_open_real)
    monkeypatch.setattr(resilience.settings, "allow_cloud_fallback", False)
    result = resilience.generate_with_fallback(ModelRoute.LOCAL, "sys", "propuesta", ["ctx"])
    assert result.route == ModelRoute.LOCAL
    assert result.response.provider == "mock"


def test_cloud_fallback_on_climbs_to_real_provider(monkeypatch):
    # Opt-in: with no private real provider, climb to the real cloud provider.
    monkeypatch.setattr(resilience, "get_adapter", _adapters_local_mock_open_real)
    monkeypatch.setattr(resilience.settings, "allow_cloud_fallback", True)
    result = resilience.generate_with_fallback(ModelRoute.LOCAL, "sys", "propuesta", ["ctx"])
    assert result.route == ModelRoute.OPEN
    assert result.fell_back is True
    assert result.response.provider == "real"
