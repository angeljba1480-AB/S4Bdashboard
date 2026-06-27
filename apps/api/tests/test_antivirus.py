"""Antivirus en la ingesta: bloquea EICAR y archivos enormes; deja pasar limpios."""
from __future__ import annotations

import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.security.antivirus import EICAR, scan  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_scan_clean():
    r = scan(b"contenido normal de la empresa", "doc.txt")
    assert r.ok is True


def test_scan_eicar():
    r = scan(EICAR, "virus.txt")
    assert r.ok is False and r.engine == "eicar" and "EICAR" in r.threat


def test_scan_oversize(monkeypatch):
    from app import config
    monkeypatch.setattr(config.settings, "max_upload_mb", 0.000001, raising=False)
    r = scan(b"x" * 5000, "grande.bin")
    assert r.ok is False and r.engine == "size"


def test_upload_blocks_eicar(client):
    h = _auth(client)
    r = client.post("/documents/upload", headers=h,
                    files={"file": ("virus.txt", EICAR, "text/plain")})
    assert r.status_code == 422 and "rechazado" in r.json()["detail"].lower()


def test_upload_allows_clean_file(client):
    h = _auth(client)
    r = client.post("/documents/upload", headers=h,
                    files={"file": ("limpio.txt", b"Reporte mensual de ventas.", "text/plain")},
                    data={"area": "Ventas"})
    assert r.status_code == 201 and r.json()["filename"] == "limpio.txt"
