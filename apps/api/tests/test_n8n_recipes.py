"""Recetas n8n a la medida: CRUD, ejecución (simulada) e integración con el agente."""
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


def test_recipe_crud_and_run(client):
    h = _auth(client)
    r = client.post("/workflows/recipes", headers=h, json={
        "name": "ERP clientes", "category": "db", "webhook_path": "erp-clientes",
        "description": "Consulta saldo en el ERP", "params": ["cliente_id"]}).json()
    assert r["id"] and r["category"] == "db" and r["params"] == ["cliente_id"]

    assert any(x["id"] == r["id"] for x in client.get("/workflows/recipes", headers=h).json())

    # Editar.
    upd = client.patch(f"/workflows/recipes/{r['id']}", headers=h, json={
        "name": "ERP clientes v2", "category": "db", "webhook_path": "erp-clientes",
        "params": ["cliente_id"], "enabled": True}).json()
    assert upd["name"] == "ERP clientes v2"

    # Ejecutar (sin n8n configurado → simulado).
    run = client.post(f"/workflows/recipes/{r['id']}/run", headers=h, json={"payload": {"cliente_id": "123"}}).json()
    assert run["status"] in ("simulated", "completed", "failed") and run["recipe"].startswith("ERP")

    assert client.delete(f"/workflows/recipes/{r['id']}", headers=h).json()["ok"] is True


def test_recipe_requires_webhook(client):
    h = _auth(client)
    assert client.post("/workflows/recipes", headers=h, json={"name": "x", "webhook_path": ""}).status_code == 422


def test_recipe_available_to_agent(client):
    h = _auth(client)
    rid = client.post("/workflows/recipes", headers=h, json={
        "name": "Cotizador SOAP", "category": "soap", "webhook_path": "cotizador"}).json()["id"]

    class _Conn:
        provider = "google"
    from app.integrations import token_store
    orig = token_store.list_connections
    token_store.list_connections = lambda *a, **k: [_Conn()]
    try:
        # dry-run para inspeccionar el plan sin ejecutar; la receta es una herramienta.
        from app.ai import agent_planner
        # Forzamos heurística (sin modelo real): no matchea SOAP, pero la receta debe
        # estar disponible como workflow para el planner por tools.
        tools, name_map = agent_planner.build_tools([], [{"id": rid, "name": "Cotizador SOAP", "steps": "soap"}])
        names = [t["function"]["name"] for t in tools]
        assert any(name_map[n] == f"workflow:{rid}" for n in names)
    finally:
        token_store.list_connections = orig
        client.delete(f"/workflows/recipes/{rid}", headers=h)
