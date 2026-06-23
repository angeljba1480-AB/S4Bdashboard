"""Fase 5 enterprise-hardening tests: encryption at rest, export, SIEM, SSO."""
from __future__ import annotations

import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.main import app  # noqa: E402
from app.models import Document  # noqa: E402
from app.security.crypto import is_encrypted  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_documents_encrypted_at_rest(client):
    from app.db import engine

    with Session(engine) as s:
        docs = s.exec(select(Document)).all()
        assert docs, "seed should create documents"
        assert all(is_encrypted(d.text) for d in docs), "document text must be ciphertext at rest"


def test_rag_returns_decrypted_citations(client):
    h = _auth(client)
    agent_id = client.get("/agents", headers=h).json()[0]["id"]
    r = client.post("/chat", headers=h, json={"agent_id": agent_id,
                                              "prompt": "política de seguridad interna"}).json()
    if r["citations"]:
        assert all("enc:" not in c["text"] for c in r["citations"]), "citations must be decrypted"


def test_export_pdf_and_md(client):
    h = _auth(client)
    pdf = client.post("/export/report", headers=h, json={"title": "SOW", "content": "Alcance del proyecto", "format": "pdf"})
    assert pdf.status_code == 200
    assert pdf.content[:4] == b"%PDF"

    md = client.post("/export/report", headers=h, json={"title": "SOW", "content": "Alcance", "format": "md"})
    assert md.status_code == 200
    assert "# SOW" in md.text


def test_audit_siem_export(client):
    h = _auth(client)
    r = client.get("/audit/export", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-ndjson")


def test_security_status(client):
    h = _auth(client)
    s = client.get("/admin/security", headers=h).json()
    assert s["encryption_at_rest"]["enabled"] is True
    assert s["encryption_at_rest"]["algo"] == "AES-256-GCM"
    assert "fallback_order" in s


def test_sso_disabled_by_default(client):
    assert client.get("/auth/sso/config").json()["enabled"] is False
