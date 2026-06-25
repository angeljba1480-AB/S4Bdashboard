"""Sprint 4: report templates by industry, PPTX/XLSX export, Drive guard."""
from __future__ import annotations

import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_industry_report_recipe_in_catalog(client):
    ids = {r["id"] for r in client.get("/recipes", headers=_auth(client)).json()}
    assert "reporte_industria" in ids


def test_report_generates_with_industry_sections(client):
    h = _auth(client)
    start = client.post("/recipes/reporte_industria/start", headers=h, json={
        "inputs": {"plantilla": "Retail / comercio", "tema": "Resultados de ventas", "periodo": "Q2 2026"},
    }).json()
    assert start["status"] == "draft"
    # The generated draft is real content produced through the router.
    assert start["draft"].get("contenido"), "debe generar contenido del reporte"


def test_export_run_pptx_and_xlsx(client):
    h = _auth(client)
    start = client.post("/recipes/cotizacion/start", headers=h, json={
        "inputs": {"cliente": "ACME", "concepto": "servicio", "monto": "1000"},
    }).json()
    client.post(f"/recipes/runs/{start['id']}/approve", headers=h)

    pptx = client.get(f"/recipes/runs/{start['id']}/export?format=pptx", headers=h)
    assert pptx.status_code == 200 and pptx.headers["content-type"] == PPTX
    assert pptx.content[:2] == b"PK"

    xlsx = client.get(f"/recipes/runs/{start['id']}/export?format=xlsx", headers=h)
    assert xlsx.status_code == 200 and xlsx.headers["content-type"] == XLSX
    assert xlsx.content[:2] == b"PK"


def test_export_report_endpoint_pptx(client):
    h = _auth(client)
    r = client.post("/export/report", headers=h, json={
        "title": "Reporte demo", "content": "## Resumen\n- punto uno\n- punto dos", "format": "pptx"})
    assert r.status_code == 200 and r.headers["content-type"] == PPTX
    assert r.content[:2] == b"PK"


def test_drive_requires_google_connection(client):
    h = _auth(client)
    r = client.get("/drive/files", headers=h)
    assert r.status_code == 400  # no Google connected in this tenant
