"""Espacios (proyectos del cliente): crear, listar, abrir, borrar."""
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


def test_space_crud_and_modules(client):
    h = _auth(client)
    # nombre obligatorio
    assert client.post("/spaces", headers=h, json={"name": ""}).status_code == 422
    s = client.post("/spaces", headers=h, json={
        "name": "Finanzas S4B", "client": "Silent4Business", "description": "Pilot tablero"}).json()
    assert s["name"] == "Finanzas S4B"
    # trae el módulo Tablero Financiero dentro del espacio
    assert any(m["key"] == "finance" and m["href"] == "/tablero-financiero" for m in s["modules"])
    # aparece al listar y al abrir
    assert any(x["id"] == s["id"] for x in client.get("/spaces", headers=h).json())
    assert client.get(f"/spaces/{s['id']}", headers=h).json()["id"] == s["id"]
    # borrar
    assert client.delete(f"/spaces/{s['id']}", headers=h).json()["ok"] is True
    assert client.get(f"/spaces/{s['id']}", headers=h).status_code == 404
