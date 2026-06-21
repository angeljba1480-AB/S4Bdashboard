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
    tok = client.post("/auth/login", json={"email": "admin@s4b.mx", "password": "demo1234"}).json()["access_token"]
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
