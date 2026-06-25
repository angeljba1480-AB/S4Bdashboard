"""Integration API: API keys, public /v1, connectors, events, run-due."""
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


def test_api_key_lifecycle_and_v1_access(client):
    h = _auth(client)
    created = client.post("/admin/api-keys", headers=h, json={"name": "CRM Acme"}).json()
    assert created["api_key"].startswith("mai_")
    key = created["api_key"]

    # use the key on the public API
    ping = client.get("/v1/ping", headers={"X-API-Key": key})
    assert ping.status_code == 200 and ping.json()["ok"] is True

    # bad key rejected
    assert client.get("/v1/ping", headers={"X-API-Key": "nope"}).status_code == 401

    # listed (masked) + revoke disables access
    keys = client.get("/admin/api-keys", headers=h).json()
    assert any(k["prefix"] == created["api_key"][:10] for k in keys)
    client.post(f"/admin/api-keys/{created['id']}/revoke", headers=h)
    assert client.get("/v1/ping", headers={"X-API-Key": key}).status_code == 401


def test_v1_run_case_and_tramites(client):
    h = _auth(client)
    key = client.post("/admin/api-keys", headers=h, json={"name": "ERP"}).json()["api_key"]
    hk = {"X-API-Key": key}
    run = client.post("/v1/cases/cotizacion/run", headers=hk, json={
        "inputs": {"cliente": "Externo", "concepto": "servicio", "monto": "10"}})
    assert run.status_code == 200 and run.json()["draft"]["plan"]
    tr = client.get("/v1/tramites?q=rfc", headers=hk).json()
    assert isinstance(tr, list)


def test_connector_crud(client):
    h = _auth(client)
    c = client.post("/integrations/connectors", headers=h, json={
        "kind": "delivery", "name": "Rappi", "base_url": "https://example.test/webhook", "token": "secret"}).json()
    assert c["kind"] == "delivery" and c["has_token"] is True
    lst = client.get("/integrations/connectors", headers=h).json()
    assert any(x["id"] == c["id"] for x in lst)
    assert client.delete(f"/integrations/connectors/{c['id']}", headers=h).json()["ok"] is True


def test_event_triggers_automation_via_v1(client):
    h = _auth(client)
    # an event automation that just notifies
    client.post("/automations/from-template", headers=h, json={"template_id": "alerta_doc_sensible"})
    key = client.post("/admin/api-keys", headers=h, json={"name": "evt"}).json()["api_key"]
    res = client.post("/v1/events", headers={"X-API-Key": key},
                      json={"event": "document_uploaded", "payload": {"filename": "x.pdf"}}).json()
    assert res["automations_triggered"] >= 1


def test_document_upload_fires_event(client):
    h = _auth(client)
    client.post("/automations/from-template", headers=h, json={"template_id": "alerta_doc_sensible"})
    # limit alto: el endpoint topa en 100 por defecto y la BD de pruebas es compartida.
    before = len(client.get("/audit?limit=500", headers=h).json())
    client.post("/documents/upload", headers=h, data={"filename": "evt.txt", "text": "Documento con RFC BBM930101XYZ"})
    after = client.get("/audit?limit=500", headers=h).json()
    assert len(after) > before
    assert any(e["event_type"] == "automation" for e in after)


def test_run_due_scheduled(client):
    h = _auth(client)
    client.post("/automations/from-template", headers=h, json={"template_id": "reporte_operacion"})  # daily
    res = client.post("/automations/run-due?frequency=daily", headers=h).json()
    assert res["ran"] >= 1


def test_connector_templates(client):
    h = _auth(client)
    t = client.get("/integrations/connector-templates", headers=h).json()
    ids = {x["id"] for x in t}
    assert {"hubspot", "salesforce", "shopify", "rappi"} <= ids
    assert all("payload_example" in x for x in t)


def test_signed_inbound_webhook(client):
    import hashlib
    import hmac
    h = _auth(client)
    client.post("/automations/from-template", headers=h, json={"template_id": "alerta_doc_sensible"})
    wh = client.post("/integrations/webhooks", headers=h, json={
        "name": "CRM events", "default_event": "document_uploaded"}).json()
    secret = wh["secret"]
    body = b'{"event":"document_uploaded","payload":{"from":"crm"}}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    # valid signature -> dispatched
    ok = client.post(wh["url"], content=body, headers={"X-Signature": sig})
    assert ok.status_code == 200 and ok.json()["automations_triggered"] >= 1

    # bad signature -> rejected
    bad = client.post(wh["url"], content=body, headers={"X-Signature": "deadbeef"})
    assert bad.status_code == 401
