"""Alertas configurables: reglas, disparo (popup) y notificaciones in-app."""
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


def test_event_types_catalog(client):
    keys = {e["key"] for e in client.get("/alerts/event-types", headers=_auth(client)).json()}
    assert {"test", "finetune", "workflow"} <= keys


def test_rule_crud_validation(client):
    h = _auth(client)
    # webhook sin URL → 422
    assert client.post("/alerts/rules", headers=h, json={
        "name": "x", "event_type": "test", "channels": ["webhook"], "webhook_url": ""}).status_code == 422
    # event_type inválido → 422
    assert client.post("/alerts/rules", headers=h, json={
        "name": "x", "event_type": "nope", "channels": ["popup"]}).status_code == 422
    r = client.post("/alerts/rules", headers=h, json={
        "name": "Avísame de fine-tuning", "event_type": "finetune", "channels": ["popup"]}).json()
    assert r["event_type"] == "finetune" and r["channels"] == ["popup"]
    assert any(x["id"] == r["id"] for x in client.get("/alerts/rules", headers=h).json())
    assert client.delete(f"/alerts/rules/{r['id']}", headers=h).json()["ok"] is True


def test_test_alert_creates_popup_notification(client):
    h = _auth(client)
    before = client.get("/notifications/unread-count", headers=h).json()["count"]
    # Sin regla de "test" → no dispara.
    assert client.post("/alerts/test", headers=h).json()["fired"] == 0
    # Con regla popup para "test" → dispara y crea notificación.
    client.post("/alerts/rules", headers=h, json={"name": "Pruebas", "event_type": "test", "channels": ["popup"]})
    assert client.post("/alerts/test", headers=h).json()["fired"] == 1
    after = client.get("/notifications/unread-count", headers=h).json()["count"]
    assert after == before + 1
    # Aparece en la lista de no leídas y se puede marcar leída.
    unread = client.get("/notifications?unread=true", headers=h).json()
    assert unread and unread[0]["title"] == "Alerta de prueba"
    assert client.post(f"/notifications/{unread[0]['id']}/read", headers=h).json()["ok"] is True


def test_mark_all_read(client):
    h = _auth(client)
    client.post("/alerts/test", headers=h)  # genera al menos una (regla creada arriba)
    client.post("/notifications/read-all", headers=h)
    assert client.get("/notifications/unread-count", headers=h).json()["count"] == 0
