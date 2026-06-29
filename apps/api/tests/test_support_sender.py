"""Remitente de soporte por tenant (marca blanca de correo)."""
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


def test_support_sender_get_set_validate(client):
    h = _auth(client)
    # estado inicial: sin remitente, sin conexiones en el test
    st = client.get("/company/support-sender", headers=h).json()
    assert st["account_id"] == "" and "connections" in st
    # guardar alias sin cuenta (válido: usa la del usuario)
    r = client.put("/company/support-sender", headers=h,
                   json={"account_id": "", "from_addr": "soporte@empresa.mx", "from_name": "Soporte Empresa"})
    assert r.status_code == 200 and r.json()["from_addr"] == "soporte@empresa.mx"
    # un account_id inexistente es rechazado
    bad = client.put("/company/support-sender", headers=h,
                     json={"account_id": "oauth_inexistente", "from_addr": "", "from_name": ""})
    assert bad.status_code == 422
    # persiste
    assert client.get("/company/support-sender", headers=h).json()["from_name"] == "Soporte Empresa"
