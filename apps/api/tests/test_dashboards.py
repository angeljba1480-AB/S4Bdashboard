"""Dashboard builder tests."""
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


def test_suggest_matches_description(client):
    h = _auth(client)
    spec = client.post("/dashboards/suggest", headers=h, json={"description": "quiero ver costos y gastos"}).json()["spec"]
    keys = {w["key"] for w in spec}
    assert "cost.total" in keys


def test_create_and_resolve_data(client):
    h = _auth(client)
    # generate a case so KPIs have data
    start = client.post("/recipes/cotizacion/start", headers=h, json={
        "inputs": {"cliente": "Z", "concepto": "x", "monto": "1"}}).json()
    client.post(f"/recipes/runs/{start['id']}/approve", headers=h)

    dash = client.post("/dashboards", headers=h, json={
        "name": "Operación comercial", "description": "casos, tokens y costo"}).json()
    assert dash["spec"], "debe generar widgets"

    data = client.get(f"/dashboards/{dash['id']}/data", headers=h).json()
    kpis = [w for w in data["widgets"] if w["type"] == "kpi"]
    assert kpis and all("value" in w for w in kpis)
    bars = [w for w in data["widgets"] if w["type"] == "bar"]
    assert all("series" in w for w in bars)


def test_company_data_widget_resolves(client):
    h = _auth(client)
    client.post("/documents/upload", headers=h, data={
        "filename": "contrato_demo.txt", "text": "Contrato de servicios confidencial."})
    dash = client.post("/dashboards", headers=h, json={
        "name": "Documentos", "description": "documentos y archivos de la empresa"}).json()
    data = client.get(f"/dashboards/{dash['id']}/data", headers=h).json()
    doc_kpi = next((w for w in data["widgets"] if w["id"] and w.get("value") is not None and "Documentos" in w["title"]), None)
    assert doc_kpi is not None and doc_kpi["value"] >= 1


def test_update_and_delete(client):
    h = _auth(client)
    dash = client.post("/dashboards", headers=h, json={"name": "Tmp", "description": "casos"}).json()
    upd = client.put(f"/dashboards/{dash['id']}", headers=h, json={
        "name": "Tmp 2", "description": "casos", "spec": [{"id": "w0", "type": "kpi", "title": "Casos", "source": "platform", "key": "cases.total"}]}).json()
    assert upd["name"] == "Tmp 2"
    assert client.delete(f"/dashboards/{dash['id']}", headers=h).status_code == 200
    assert client.get(f"/dashboards/{dash['id']}/data", headers=h).status_code == 404
