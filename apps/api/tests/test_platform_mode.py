"""Modo demo: la plataforma debe reportar honestamente si la IA es real o simulada."""
from __future__ import annotations

import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_platform_mode_sin_proveedor_es_demo(monkeypatch):
    """Sin proveedores configurados (default de tests): demo_mode=True, ai_live=False."""
    import app.ai.adapters as ad
    monkeypatch.setattr(ad, "_RUNTIME", {}, raising=False)
    m = ad.platform_mode()
    assert m["ai_live"] is False
    assert m["demo_mode"] is True
    assert m["embeddings_semantic"] is False  # embeddings_provider="local" por defecto
    assert m["live_routes"] == []


def test_platform_mode_con_override_es_live(monkeypatch):
    """Con un proveedor real (override de admin) la IA deja de ser demo."""
    import app.ai.adapters as ad
    from app.models import ModelRoute
    monkeypatch.setattr(ad, "_RUNTIME",
                        {ModelRoute.OPEN.value: {"enabled": True, "base_url": "https://api.example/v1",
                                                 "api_key": "k", "model": "m"}}, raising=False)
    m = ad.platform_mode()
    assert m["ai_live"] is True
    assert m["demo_mode"] is False
    assert ModelRoute.OPEN.value in m["live_routes"]


def test_me_expone_modo(monkeypatch):
    with TestClient(app) as c:
        me = c.get("/me", headers=_auth(c)).json()
    # /me expone el modo con tipos correctos. (El valor exacto depende de si hay
    # proveedores configurados; el estado global _RUNTIME puede venir de otros tests,
    # así que aquí solo validamos contrato; el valor lo cubren los tests unitarios.)
    for k in ("demo_mode", "ai_live", "embeddings_semantic"):
        assert k in me and isinstance(me[k], bool)
    # Coherencia interna: demo_mode es lo opuesto de ai_live.
    assert me["demo_mode"] is (not me["ai_live"])
