"""WhatsApp vía CallMeBot: configuración y envío (mockeado)."""
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


def test_config_validation_and_send(client, monkeypatch):
    h = _auth(client)
    # sin configurar → no se puede enviar
    assert client.post("/whatsapp/send", headers=h, json={"text": "hola"}).status_code == 400
    # número sin formato internacional → 422
    assert client.post("/whatsapp/config", headers=h, json={"phone": "5512345678", "apikey": "k"}).status_code == 422
    # configurar correctamente
    r = client.post("/whatsapp/config", headers=h, json={"phone": "+5215512345678", "apikey": "abc123"}).json()
    assert r["configured"] is True and r["phone"] == "+5215512345678"
    # la apikey no se devuelve en config
    assert "apikey" not in client.get("/whatsapp/config", headers=h).json()

    sent = {}
    from app.integrations import whatsapp as wa
    monkeypatch.setattr(wa, "send_callmebot", lambda phone, apikey, text: (sent.update(phone=phone, apikey=apikey, text=text) or (True, "ok")))
    out = client.post("/whatsapp/send", headers=h, json={"text": "Resumen del día"}).json()
    assert out["ok"] is True
    assert sent["phone"] == "+5215512345678" and sent["apikey"] == "abc123" and "Resumen" in sent["text"]


def test_alert_whatsapp_channel_uses_callmebot(client, monkeypatch):
    h = _auth(client)
    client.post("/whatsapp/config", headers=h, json={"phone": "+5215599999999", "apikey": "zzz"})
    sent = {}
    from app.integrations import whatsapp as wa
    monkeypatch.setattr(wa, "send_callmebot", lambda phone, apikey, text: (sent.update(text=text) or (True, "ok")))
    # regla de alerta con canal whatsapp, sin webhook_url (CallMeBot la cubre)
    rule = client.post("/alerts/rules", headers=h, json={
        "name": "WA prueba", "event_type": "test", "channels": ["whatsapp"]})
    assert rule.status_code == 201, rule.text
    fired = client.post("/alerts/test", headers=h).json()["fired"]
    assert fired >= 1
    assert "Alerta de prueba" in sent.get("text", "")
    # limpia la regla para no afectar otras pruebas que comparten el DB en CI
    client.delete(f"/alerts/rules/{rule.json()['id']}", headers=h)
