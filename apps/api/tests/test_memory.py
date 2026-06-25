"""Memory + tags: capture, recall (semantic), tag filter, area scope, auto-capture."""
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


def test_create_search_and_tags(client):
    h = _auth(client)
    client.post("/memory", headers=h, json={
        "title": "Propuesta ACME", "content": "Propuesta comercial para ACME sobre CRM, 8 semanas.",
        "tags": ["ventas", "acme"], "source": "manual"})
    client.post("/memory", headers=h, json={
        "title": "Contrato RH", "content": "Contrato laboral confidencial del área de RH.",
        "tags": ["rh"], "source": "manual"})

    # Tag catalog
    tags = client.get("/memory/tags", headers=h).json()
    assert {"ventas", "acme", "rh"} <= set(tags)

    # Filter by tag
    ventas = client.get("/memory?tag=ventas", headers=h).json()
    assert ventas and all("ventas" in m["tags"] for m in ventas)

    # Semantic-ish recall: query about ACME ranks the ACME item first
    found = client.get("/memory?q=propuesta de ACME", headers=h).json()
    assert found and found[0]["title"] == "Propuesta ACME"


def test_delete(client):
    h = _auth(client)
    m = client.post("/memory", headers=h, json={"title": "tmp", "content": "borrar esto"}).json()
    assert client.delete(f"/memory/{m['id']}", headers=h).json()["ok"] is True
    assert all(x["id"] != m["id"] for x in client.get("/memory", headers=h).json())


def test_empty_content_rejected(client):
    h = _auth(client)
    assert client.post("/memory", headers=h, json={"title": "x", "content": "  "}).status_code == 422


def test_recipe_completion_auto_captures(client):
    h = _auth(client)
    start = client.post("/recipes/cotizacion/start", headers=h, json={
        "inputs": {"cliente": "MemoriaCo", "concepto": "servicio", "monto": "1000"}}).json()
    client.post(f"/recipes/runs/{start['id']}/approve", headers=h)
    # The finished run should appear in memory.
    mem = client.get("/memory?q=MemoriaCo", headers=h).json()
    assert any("MemoriaCo" in (m["title"] + m["content"]) for m in mem)


def test_chat_uses_memory_context(client):
    h = _auth(client)
    client.post("/memory", headers=h, json={
        "title": "Dato clave ZQX", "content": "El proyecto ZQX usa el color institucional morado.",
        "tags": ["proyecto"]})
    agent_id = client.get("/agents", headers=h).json()[0]["id"]
    res = client.post("/chat", headers=h, json={
        "agent_id": agent_id, "prompt": "¿qué recuerdas del proyecto ZQX?",
        "use_rag": False, "use_memory": True}).json()
    # Mock adapter echoes retrieved context → memory content should surface.
    assert "ZQX" in res["content"] or "morado" in res["content"].lower()
