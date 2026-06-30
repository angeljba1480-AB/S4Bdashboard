"""QA end-to-end de flujos internos (corre en CI): documentos, export,
automatizaciones multi-paso, finanzas self-service y KEDB cross-cliente."""
from __future__ import annotations

import io
import json
import os
import tempfile
import zipfile

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


def test_qa_documentos_varios_tipos(client):
    h = _auth(client)
    import openpyxl
    r = client.post("/documents/upload", headers=h, files={"file": ("nota.txt", b"contrato de prueba", "text/plain")}, data={"area": "Legal"})
    assert r.status_code == 201 and r.json().get("indexed")
    wb = openpyxl.Workbook(); ws = wb.active; ws.append(["Cliente", "Venta"]); ws.append(["IMSS", 1000]); b = io.BytesIO(); wb.save(b)
    assert client.post("/documents/upload", headers=h, files={"file": ("datos.xlsx", b.getvalue(), "application/octet-stream")}).status_code == 201
    zb = io.BytesIO()
    with zipfile.ZipFile(zb, "w") as z:
        z.writestr("a.txt", "alpha"); z.writestr("b.csv", "x,y\n1,2")
    assert client.post("/documents/upload", headers=h, files={"file": ("paq.zip", zb.getvalue(), "application/zip")}).status_code == 201


def test_qa_export_formatos(client):
    h = _auth(client)
    for fmt in ("pdf", "docx", "pptx", "xlsx"):
        r = client.post("/export/report", headers=h, json={"title": "Reporte QA", "content": "Línea 1\nLínea 2", "format": fmt})
        assert r.status_code == 200 and len(r.content) > 200, fmt


def test_qa_pipeline_multipaso(client):
    h = _auth(client)
    a = client.post("/automations", headers=h, json={"name": "QA pipeline", "trigger": "manual", "action_type": "notify"}).json()
    steps = [{"type": "notify", "message": "Cobranza: 3 vencidos."}, {"type": "ai", "prompt": "Redacta recordatorio."}, {"type": "deliver", "channels": ["notify"]}]
    put = client.put(f"/automations/{a['id']}/steps", headers=h, json={"steps": steps}).json()
    assert len(put["config"]["steps"]) == 3
    run = client.post(f"/automations/{a['id']}/run", headers=h).json()
    assert run["status"] == "completed" and "enviado a" in run["detail"]


def test_qa_canvas_validate_y_mando(client):
    h = _auth(client)
    v = client.post("/automations/from-template", headers=h, json={"template_id": "reporte_operacion"}).json()
    val = client.get(f"/automations/{v['id']}/validate", headers=h).json()
    assert val["steps"] and any(s["label"] == "Salida" for s in val["steps"])
    assert "enviado a" in client.post(f"/automations/{v['id']}/run", headers=h).json()["detail"]


def test_qa_finanzas_self_service(client):
    h = _auth(client)
    assert "company" in client.get("/finance/dataset/template", headers=h).json()
    payload = json.dumps({"company": {"name": "ACME QA", "legalName": "ACME", "period": "2025", "ceo": "", "cfo": ""}})
    assert client.post("/finance/dataset", headers=h, files=[("files", ("d.json", payload.encode(), "application/json"))]).status_code == 201
    ov = client.get("/finance/overview?entity=CONS", headers=h).json()
    assert ov["company"]["name"] == "ACME QA" and ov["is_demo"] is False
    assert client.delete("/finance/dataset", headers=h).json()["ok"]


def test_qa_kedb_cross_cliente(client):
    h = _auth(client)
    client.put("/company/profile", headers=h, json={"industry": "Ciberseguridad / SOC"})
    assert client.get("/kedb/status", headers=h).json()["enabled"]
    k = client.post("/kedb", headers=h, json={"title": "Falso positivo EDR", "symptom": "EDR bloquea binario firmado", "resolution": "excluir hash", "product": "EDR", "severity": "high"}).json()
    an = client.post("/kedb/analyze", headers=h, json={"symptom": "el EDR bloquea un binario firmado", "product": "EDR"}).json()
    assert an["is_known"] and an["matches"]
    cand = client.post(f"/kedb/{k['id']}/promote", headers=h).json()
    assert cand["scope"] == "shared"
    assert any(p["id"] == cand["id"] for p in client.get("/kedb/proposals", headers=h).json())
    assert client.post(f"/kedb/proposals/{cand['id']}/approve", headers=h).json()["status"] == "published"
    assert any(x["id"] == cand["id"] and x["scope"] == "shared" for x in client.get("/kedb", headers=h).json())
