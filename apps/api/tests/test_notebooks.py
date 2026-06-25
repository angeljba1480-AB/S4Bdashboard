"""Notebooks (NotebookLM-style) + external provider config."""
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


def test_notebook_crud_and_ask(client):
    h = _auth(client)
    doc = client.post("/documents/upload", headers=h, data={
        "filename": "fuente.txt",
        "text": "El proyecto Zeta inicia en marzo y termina en junio. Responsable: el área de operaciones.",
    }).json()

    nb = client.post("/notebooks", headers=h, json={"name": "Proyecto Zeta", "document_ids": [doc["id"]]}).json()
    assert nb["name"] == "Proyecto Zeta" and len(nb["sources"]) == 1

    # Appears in the list
    assert any(x["id"] == nb["id"] for x in client.get("/notebooks", headers=h).json())

    # Ask grounded in the notebook's source
    ans = client.post(f"/notebooks/{nb['id']}/ask", headers=h, json={"question": "¿Cuándo inicia el proyecto Zeta?"}).json()
    assert ans.get("content")
    assert len(ans.get("citations", [])) >= 1

    # Generate an artifact
    art = client.post(f"/notebooks/{nb['id']}/generate/resumen", headers=h).json()
    assert art.get("content")

    # Delete
    assert client.delete(f"/notebooks/{nb['id']}", headers=h).json()["ok"] is True


def test_notebook_without_sources_prompts(client):
    h = _auth(client)
    nb = client.post("/notebooks", headers=h, json={"name": "Vacío", "document_ids": []}).json()
    ans = client.post(f"/notebooks/{nb['id']}/ask", headers=h, json={"question": "hola"}).json()
    assert ans.get("empty") is True


def test_notebook_isolated_per_user(client):
    su = _auth(client)
    nb = client.post("/notebooks", headers=su, json={"name": "Privado", "document_ids": []}).json()
    # A different user can't access it.
    client.post("/admin/users", headers=su, json={"email": "otro@maestroai.mx", "name": "Otro", "role": "user"})
    other = _auth_other(client)
    assert client.get(f"/notebooks/{nb['id']}/ask", headers=other) .status_code in (404, 405)
    assert client.post(f"/notebooks/{nb['id']}/ask", headers=other, json={"question": "x"}).status_code == 404


def _auth_other(client) -> dict:
    tok = client.post("/auth/login", json={"email": "otro@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_external_provider_config(client):
    h = _auth(client)
    before = {p["route"]: p for p in client.get("/admin/providers", headers=h).json()}
    assert "premium" in before and "open" in before

    r = client.put("/admin/providers/premium", headers=h, json={
        "enabled": True, "base_url": "https://api.example.com/v1", "model": "demo-model", "api_key": "sk-secret-123"})
    assert r.json()["enabled"] is True and r.json()["has_key"] is True

    after = {p["route"]: p for p in client.get("/admin/providers", headers=h).json()}
    assert after["premium"]["base_url"] == "https://api.example.com/v1"
    assert after["premium"]["has_key"] is True  # key stored, never returned in plaintext

    assert client.put("/admin/providers/nope", headers=h, json={"enabled": True}).status_code == 400
