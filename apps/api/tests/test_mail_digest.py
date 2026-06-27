"""Resumen de correo automatizado: config, preview (clasifica) y entrega."""
from __future__ import annotations

import os
import tempfile
import time

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
    # Limpia las conexiones OAuth creadas (el DB se comparte entre archivos en CI).
    from sqlmodel import Session, select
    from app.db import engine
    from app.models import OAuthToken
    with Session(engine) as s:
        for t in s.exec(select(OAuthToken).where(OAuthToken.identifier == "user@empresa.mx")).all():
            s.delete(t)
        s.commit()


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _connect_mailbox(client, h):
    """Crea una conexión OAuth activa para el usuario (para resolve_connection)."""
    from sqlmodel import Session
    from app.db import engine
    from app.models import OAuthToken, Tenant
    from app.security.crypto import encrypt
    me = client.get("/me", headers=h).json()
    with Session(engine) as s:
        tenant = s.get(Tenant, me["tenant_id"])
        s.add(OAuthToken(tenant_id=me["tenant_id"], user_id=me["id"], provider="google",
                         identifier="user@empresa.mx",
                         access_token_enc=encrypt("fake", tenant.kms_key_id),
                         expires_at=time.time() + 3600, status="active"))
        s.commit()


def test_config_defaults_and_update(client):
    h = _auth(client)
    c = client.get("/mail-digest/config", headers=h).json()
    assert c["schedule"] == "daily" and c["channels"] == ["popup"]
    # schedule inválido → 422
    assert client.put("/mail-digest/config", headers=h, json={"schedule": "hourly"}).status_code == 422
    upd = client.put("/mail-digest/config", headers=h, json={
        "enabled": True, "schedule": "weekdays", "channels": ["popup", "whatsapp"],
        "language": "bilingue", "notes": "Somos una pyme de servicios", "pending_days": 3}).json()
    assert upd["enabled"] and upd["schedule"] == "weekdays" and upd["language"] == "bilingue"
    assert set(upd["channels"]) == {"popup", "whatsapp"} and upd["pending_days"] == 3


def test_preview_classifies_and_learns(client, monkeypatch):
    h = _auth(client)
    _connect_mailbox(client, h)
    from app.integrations import mailbox
    monkeypatch.setattr(mailbox, "fetch", lambda provider, token: {"messages": [
        {"from": "Maestra Ana <ana@cooper.edu>", "subject": "Junta", "preview": "Favor de confirmar", "unread": True},
        {"from": "promos@tienda.com", "subject": "50% OFF", "preview": "Oferta", "unread": True},
    ], "events": []})
    import app.mailsummary as ms
    monkeypatch.setattr(ms, "_classify", lambda tenant, prompt: {
        "items": [{"categoria": "Escuela", "prioridad": "alta", "remitente": "Maestra Ana <ana@cooper.edu>",
                   "asunto_breve": "Junta", "resumen": "Confirmar asistencia", "accion": "Responder",
                   "fecha_limite": "", "pendiente": True}],
        "num_descartados": 1})
    r = client.post("/mail-digest/preview", headers=h).json()
    assert r["ok"] is True
    assert "Escuela" in r["text"] and "Pendientes" in r["text"] and "propaganda" in r["text"].lower()
    # aprendió el remitente
    from sqlmodel import Session, select
    from app.db import engine
    from app.models import MailDigestConfig
    with Session(engine) as s:
        cfg = s.exec(select(MailDigestConfig)).first()
        assert "ana@cooper.edu" in (cfg.sender_profile or "")


def test_run_now_delivers_popup(client, monkeypatch):
    h = _auth(client)
    client.put("/mail-digest/config", headers=h, json={"enabled": True, "channels": ["popup"]})
    from app.integrations import mailbox
    monkeypatch.setattr(mailbox, "fetch", lambda provider, token: {"messages": [
        {"from": "Banco <no-reply@banco.com>", "subject": "Estado de cuenta", "preview": "Disponible", "unread": True}],
        "events": []})
    import app.mailsummary as ms
    monkeypatch.setattr(ms, "_classify", lambda tenant, prompt: {
        "items": [{"categoria": "Finanzas", "prioridad": "media", "remitente": "Banco <no-reply@banco.com>",
                   "asunto_breve": "Estado de cuenta", "resumen": "Disponible", "accion": "", "fecha_limite": "",
                   "pendiente": False}], "num_descartados": 0})
    before = client.get("/notifications/unread-count", headers=h).json()["count"]
    out = client.post("/mail-digest/run-now", headers=h).json()
    assert out["ok"] is True and out["sent"].get("popup") is True
    after = client.get("/notifications/unread-count", headers=h).json()["count"]
    assert after == before + 1
