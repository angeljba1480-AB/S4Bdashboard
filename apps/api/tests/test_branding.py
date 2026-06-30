"""White-label branding tests."""
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


def test_set_branding_reflects_in_me(client):
    h = _auth(client)
    put = client.put("/admin/branding", headers=h, json={
        "brand_name": "Acme AI", "brand_color": "#0ea5e9",
        "brand_logo_url": "https://cdn.acme.mx/logo.png", "brand_tagline": "IA privada de Acme",
    })
    assert put.status_code == 200
    me = client.get("/me", headers=h).json()
    assert me["brand_name"] == "Acme AI"
    assert me["brand_color"] == "#0ea5e9"
    assert me["brand_tagline"] == "IA privada de Acme"


def test_invalid_color_rejected(client):
    h = _auth(client)
    r = client.put("/admin/branding", headers=h, json={"brand_color": "azul"})
    assert r.status_code == 422


def test_custom_domain_normalized_and_validated(client):
    h = _auth(client)
    # acepta con/sin protocolo y normaliza
    ok = client.put("/admin/branding", headers=h, json={
        "brand_name": "Acme AI", "custom_domain": "https://Plataforma.Acme.com/"})
    assert ok.status_code == 200 and ok.json()["custom_domain"] == "plataforma.acme.com"
    got = client.get("/admin/branding", headers=h).json()
    assert got["custom_domain"] == "plataforma.acme.com"
    # dominio inválido se rechaza
    bad = client.put("/admin/branding", headers=h, json={"custom_domain": "no-es-dominio"})
    assert bad.status_code == 422


def test_email_footer_uses_tenant_brand():
    from app.branding import email_footer, with_signature
    from app.models import Tenant
    t = Tenant(name="Acme", brand_name="Acme AI", brand_tagline="IA privada", custom_domain="plataforma.acme.com")
    foot = email_footer(t)
    assert "Acme AI" in foot and "IA privada" in foot and "plataforma.acme.com" in foot
    assert with_signature(t, "Cuerpo").startswith("Cuerpo")
    # sin marca → sin firma (no estampa MaestroAI en correos del cliente)
    assert email_footer(Tenant(name="X")) == ""
    assert with_signature(Tenant(name="X"), "Cuerpo") == "Cuerpo"
