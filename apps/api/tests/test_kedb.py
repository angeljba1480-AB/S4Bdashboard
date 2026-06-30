"""KEDB — base de errores conocidos, gateada por perfil de ciberseguridad."""
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


def test_kedb_gated_by_cyber_profile(client):
    h = _auth(client)
    # Sin perfil cyber: deshabilitado y 403 al usarlo.
    assert client.get("/kedb/status", headers=h).json()["enabled"] is False
    assert client.get("/kedb", headers=h).status_code == 403

    # Habilitar perfil de ciberseguridad → módulo disponible.
    client.put("/company/profile", headers=h, json={"industry": "Ciberseguridad / SOC"})
    assert client.get("/kedb/status", headers=h).json()["enabled"] is True
    assert client.get("/kedb", headers=h).status_code == 200


def test_kedb_crud_and_analyze(client):
    h = _auth(client)
    client.put("/company/profile", headers=h, json={"industry": "Ciberseguridad"})  # asegura habilitado
    k = client.post("/kedb", headers=h, json={
        "title": "Falso positivo EDR en actualización", "symptom": "EDR bloquea binario firmado tras parche",
        "cause": "Firma no reconocida por caché del agente", "resolution": "Forzar refresh de reputación / excluir hash",
        "product": "EDR", "severity": "high", "tags": ["edr", "falso-positivo"]}).json()
    assert k["severity"] == "high" and "edr" in k["tags"]

    lst = client.get("/kedb?q=edr", headers=h).json()
    assert any(x["id"] == k["id"] for x in lst)

    # Analizar un síntoma parecido → lo reconoce como error conocido.
    an = client.post("/kedb/analyze", headers=h,
                     json={"symptom": "el EDR bloquea un binario firmado", "product": "EDR"}).json()
    assert an["is_known"] is True and an["matches"]

    assert client.delete(f"/kedb/{k['id']}", headers=h).json()["ok"] is True
