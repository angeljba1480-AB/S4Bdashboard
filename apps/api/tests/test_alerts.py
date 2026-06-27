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


def test_event_types_include_new(client):
    keys = {e["key"] for e in client.get("/alerts/event-types", headers=_auth(client)).json()}
    assert {"antivirus", "ingest", "webhook", "threshold", "digest"} <= keys


def test_scheduled_digest_rule(client):
    h = _auth(client)
    # schedule inválido → 422
    assert client.post("/alerts/rules", headers=h, json={
        "name": "x", "event_type": "digest", "channels": ["popup"], "schedule": "hourly"}).status_code == 422
    # regla programada diaria
    r = client.post("/alerts/rules", headers=h, json={
        "name": "Resumen diario", "event_type": "digest", "channels": ["popup"], "schedule": "daily"}).json()
    assert r["schedule"] == "daily"
    # run-digests entrega al menos este digest y sella last_digest_at
    out = client.post("/alerts/run-digests?frequency=daily", headers=h).json()
    assert out["frequency"] == "daily" and out["sent"] >= 1
    rules = {x["id"]: x for x in client.get("/alerts/rules", headers=h).json()}
    assert rules[r["id"]]["last_digest_at"]


def test_threshold_get_set(client):
    h = _auth(client)
    assert client.get("/alerts/threshold", headers=h).json()["spend_threshold_usd"] == 0.0
    client.post("/alerts/threshold", headers=h, json={"spend_threshold_usd": 0.001})
    assert client.get("/alerts/threshold", headers=h).json()["spend_threshold_usd"] == 0.001
    # restablecer para no afectar otras corridas
    client.post("/alerts/threshold", headers=h, json={"spend_threshold_usd": 0})


def test_run_checks_fires_on_spend(client):
    from sqlmodel import Session, select

    from app import alerts as ae
    from app.db import engine
    from app.models import AlertRule, AuditEvent, Tenant, User

    with Session(engine) as s:
        tenant = s.exec(select(Tenant)).first()
        user = s.exec(select(User).where(User.tenant_id == tenant.id)).first()
        s.add(AuditEvent(tenant_id=tenant.id, event_type="chat", cost_estimate=5.0))
        s.add(AlertRule(tenant_id=tenant.id, user_id=user.id, name="Gasto",
                        event_type="threshold", channels='["popup"]'))
        s.commit()
        # umbral 0 → no evalúa; umbral 1.0 con gasto 5.0 → dispara
        assert ae.run_checks(s, tenant.id, 0) == 0
        assert ae.run_checks(s, tenant.id, 1.0) == 1
