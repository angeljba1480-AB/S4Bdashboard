"""Conector SFTP (solo lectura) → import al RAG. Se mockea la red (sin paramiko)."""
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


def _create(client, h) -> str:
    return client.post("/datasources/sftp", headers=h, json={
        "name": "ERP exports", "host": "sftp.acme.mx", "username": "svc",
        "auth_type": "password", "secret": "s3cr3t", "remote_path": "/out/reportes"}).json()["id"]


def test_create_requires_fields(client):
    h = _auth(client)
    assert client.post("/datasources/sftp", headers=h, json={
        "name": "x", "host": "", "username": "u", "secret": "p", "remote_path": "/p"}).status_code == 422
    assert client.post("/datasources/sftp", headers=h, json={
        "name": "x", "host": "h", "username": "u", "secret": "", "remote_path": "/p"}).status_code == 422


def test_test_lists_files(client, monkeypatch):
    h = _auth(client)
    sid = _create(client, h)
    from app.integrations import sftp as sftp_conn
    monkeypatch.setattr(sftp_conn, "list_files",
                        lambda *a, **k: [{"name": "rep1.csv", "size": 120}, {"name": "rep2.txt", "size": 80}])
    r = client.post(f"/datasources/sftp/{sid}/test", headers=h).json()
    assert r["ok"] is True and r["count"] == 2


def test_import_creates_documents(client, monkeypatch):
    h = _auth(client)
    sid = _create(client, h)
    from app.integrations import sftp as sftp_conn
    monkeypatch.setattr(sftp_conn, "fetch", lambda *a, **k: [
        ("clientes.csv", b"id,nombre\n1,ACME\n2,Globex\n"),
        ("nota.txt", b"Resumen mensual de operaciones."),
    ])
    r = client.post(f"/datasources/sftp/{sid}/import", headers=h).json()
    assert r["imported"] == 2 and len(r["documents"]) == 2

    # Aparecen como documentos del tenant.
    docs = client.get("/documents", headers=h).json()
    assert any("clientes" in d["filename"] for d in docs)


def test_reveal_and_delete(client):
    h = _auth(client)
    sid = _create(client, h)
    rev = client.get(f"/datasources/sftp/{sid}/reveal", headers=h).json()
    assert rev["secret"] == "s3cr3t" and rev["username"] == "svc"
    assert client.delete(f"/datasources/sftp/{sid}", headers=h).json()["ok"] is True
    assert not any(s["id"] == sid for s in client.get("/datasources/sftp", headers=h).json())
