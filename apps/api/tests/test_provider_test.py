"""Verificación del modelo premium/open: /admin/providers/{route}/test hace una
llamada real mínima al proveedor configurado (o reporta MOCK si no hay)."""
from __future__ import annotations

import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_unconfigured_premium_reports_mock(client):
    h = _auth(client)
    # BD/cache compartidos entre módulos: deja premium sin proveedor real primero.
    client.put("/admin/providers/premium", headers=h, json={
        "enabled": False, "base_url": "", "model": "", "api_key": ""})
    r = client.post("/admin/providers/premium/test", headers=h).json()
    assert r["ok"] is False and r["mode"] == "mock"


def test_invalid_route_rejected(client):
    h = _auth(client)
    assert client.post("/admin/providers/nope/test", headers=h).status_code == 400


def test_configured_premium_calls_model(client, monkeypatch):
    h = _auth(client)
    # Configura un proveedor premium real (endpoint compatible OpenAI).
    client.put("/admin/providers/premium", headers=h, json={
        "enabled": True, "base_url": "https://api.example.com/v1",
        "model": "gpt-test", "api_key": "sk-test"})

    # Evita la red: el adapter devuelve una respuesta simulada.
    from app.ai import adapters
    from app.ai.adapters import ModelResponse

    def fake_generate(self, system, prompt, context):
        return ModelResponse(content="OK", model=self.model_name, provider=self.base_url)

    monkeypatch.setattr(adapters.OpenAICompatAdapter, "generate", fake_generate)

    r = client.post("/admin/providers/premium/test", headers=h).json()
    assert r["ok"] is True and r["mode"] == "real"
    assert r["model"] == "gpt-test" and r["sample"] == "OK" and "latency_ms" in r


def test_provider_error_is_reported(client, monkeypatch):
    h = _auth(client)
    client.put("/admin/providers/premium", headers=h, json={
        "enabled": True, "base_url": "https://api.example.com/v1",
        "model": "gpt-test", "api_key": "sk-test"})

    from app.ai import adapters

    def boom(self, system, prompt, context):
        raise RuntimeError("401 Unauthorized")

    monkeypatch.setattr(adapters.OpenAICompatAdapter, "generate", boom)

    r = client.post("/admin/providers/premium/test", headers=h).json()
    assert r["ok"] is False and r["mode"] == "real" and "401" in r["detail"]
