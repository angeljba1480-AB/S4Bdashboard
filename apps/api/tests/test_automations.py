"""Automations tests (templates, create, toggle, run dispatch)."""
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


def test_templates_available(client):
    h = _auth(client)
    t = client.get("/automations/templates", headers=h).json()
    ids = {x["id"] for x in t}
    assert {"resumen_diario", "cobranza_semanal", "alerta_doc_sensible"} <= ids


def test_create_from_template_and_run_recipe(client):
    h = _auth(client)
    a = client.post("/automations/from-template", headers=h, json={"template_id": "redes_semanal"}).json()
    assert a["action_type"] == "recipe"
    assert a["enabled"] is True

    run = client.post(f"/automations/{a['id']}/run", headers=h).json()
    assert run["status"] == "completed"
    assert run["last_run"]


def test_run_notify_and_toggle(client):
    h = _auth(client)
    a = client.post("/automations/from-template", headers=h, json={"template_id": "alerta_doc_sensible"}).json()
    run = client.post(f"/automations/{a['id']}/run", headers=h).json()
    assert run["status"] == "completed"
    assert "documento" in run["detail"].lower()

    toggled = client.post(f"/automations/{a['id']}/toggle", headers=h).json()
    assert toggled["enabled"] is False


def test_workflow_automation_runs_simulated(client):
    h = _auth(client)
    a = client.post("/automations/from-template", headers=h, json={"template_id": "reporte_operacion"}).json()
    run = client.post(f"/automations/{a['id']}/run", headers=h).json()
    # n8n disabled in tests -> simulated, but the action dispatches successfully
    assert run["status"] in ("simulated", "completed")
    assert "workflow" in run["detail"]
