"""Búsqueda global: cruza documentos, memoria, recetas, etc."""
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


def test_short_query_returns_empty(client):
    r = client.get("/search?q=a", headers=_auth(client)).json()
    assert r["total"] == 0 and r["results"] == []


def test_finds_document(client):
    h = _auth(client)
    client.post("/documents/upload", headers=h, data={
        "text": "El contrato Zephyrine cubre la garantía extendida.",
        "filename": "contrato-zephyrine.txt", "area": "", "category": "contrato"})
    r = client.get("/search?q=Zephyrine", headers=h).json()
    assert r["total"] >= 1
    doc_hits = [x for x in r["results"] if x["type"] == "document"]
    assert any("zephyrine" in (x["title"] + x["snippet"]).lower() for x in doc_hits)
    assert doc_hits[0]["href"] == "/documents"


def test_finds_memory(client):
    h = _auth(client)
    client.post("/memory", headers=h, json={
        "title": "Proveedor Qwilfish", "content": "Qwilfish entrega los martes."})
    r = client.get("/search?q=Qwilfish", headers=h).json()
    assert any(x["type"] == "memory" for x in r["results"])
