"""Conector SharePoint (Graph delegado) → repositorio + RAG."""
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


def test_sharepoint_crud_and_requires_ms_account(client):
    h = _auth(client)
    s = client.post("/datasources/sharepoint", headers=h, json={
        "name": "Finanzas SP", "site_url": "https://contoso.sharepoint.com/sites/Finanzas",
        "folder": "Proyectos Finanzas", "area": "Finanzas"}).json()
    assert s["site_url"].endswith("/Finanzas") and s["folder"] == "Proyectos Finanzas"
    lst = client.get("/datasources/sharepoint", headers=h).json()
    assert any(x["id"] == s["id"] for x in lst)
    # Sin cuenta Microsoft conectada → test/import devuelven 400 claro (no 500).
    assert client.post(f"/datasources/sharepoint/{s['id']}/test", headers=h).status_code == 400
    assert client.delete(f"/datasources/sharepoint/{s['id']}", headers=h).json()["ok"] is True


def test_sharepoint_site_url_parsing():
    from app.integrations.sharepoint import _children_url
    assert _children_url("SID", "") == "https://graph.microsoft.com/v1.0/sites/SID/drive/root/children"
    assert _children_url("SID", "Proyectos Finanzas").endswith("/root:/Proyectos Finanzas:/children")
