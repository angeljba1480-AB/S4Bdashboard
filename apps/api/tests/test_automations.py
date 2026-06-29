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
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
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
    # 'mando' es centro de mando: aunque n8n esté simulado, MaestroAI calcula el
    # reporte real y lo entrega (queda como notificación por defecto).
    assert "enviado a" in run["detail"]
    notifs = client.get("/notifications", headers=h).json()
    assert any(n["event_type"] == "automation" for n in notifs)


def test_ingesta_native_indexes_pending_docs(client):
    """La automatización 'ingesta' indexa DENTRO de MaestroAI (sin n8n)."""
    h = _auth(client)
    # Sube un documento (queda indexado al subir) y otro vía API que dejaremos pendiente.
    client.post("/documents/upload", headers=h,
                files=[("file", ("nota.txt", b"contenido de prueba para ingesta", "text/plain"))])
    a = client.post("/automations/from-template", headers=h, json={"template_id": "indexar_nuevos_docs"}).json()
    assert a["action_type"] == "workflow" and a["action_ref"] == "ingesta"

    # Validar: debe mostrar el paso nativo y el de Entrada (opcional).
    v = client.get(f"/automations/{a['id']}/validate", headers=h).json()
    labels = {s["label"] for s in v["steps"]}
    assert "Indexado (nativo)" in labels and "Entrada" in labels and "Salida" in labels

    # Fijar fuente y salida, luego ejecutar: corre nativo (no "workflow … n8n").
    client.post(f"/automations/{a['id']}/source", headers=h, json={"kind": "new_documents"})
    client.post(f"/automations/{a['id']}/delivery", headers=h, json={"channels": ["notify"]})
    run = client.post(f"/automations/{a['id']}/run", headers=h).json()
    assert run["status"] == "completed"
    assert "ingesta" in run["detail"] and "n8n" not in run["detail"]
