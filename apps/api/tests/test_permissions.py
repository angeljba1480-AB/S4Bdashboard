"""Hierarchical governance: area-scoped visibility + super admin (blueprint §2.1)."""
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


def _login(client, email, password="demo1234") -> dict:
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_seed_admin_promoted_to_super_admin(client):
    """ensure_super_admin() runs on startup and promotes the oldest admin."""
    h = _login(client, "admin@maestroai.mx")
    tenants = client.get("/admin/tenants", headers=h)
    assert tenants.status_code == 200  # only a super admin can list tenants
    assert any(t["name"] == "MaestroAI" for t in tenants.json())


def test_area_scoped_document_visibility(client):
    su = _login(client, "admin@maestroai.mx")
    # A business user confined to "Ventas".
    client.post("/admin/users", headers=su, json={
        "email": "ventas@maestroai.mx", "name": "Vendedor", "role": "user", "area": "Ventas",
    })
    # Documents in three areas.
    for area, fname in [("Ventas", "v.txt"), ("RH", "r.txt"), ("", "general.txt")]:
        client.post("/documents/upload", headers=su, data={
            "filename": fname, "text": f"contenido de {fname}", "area": area})

    seller = _login(client, "ventas@maestroai.mx")
    names = {d["filename"] for d in client.get("/documents", headers=seller).json()}
    assert "v.txt" in names           # own area
    assert "general.txt" in names     # general/unassigned visible to all
    assert "r.txt" not in names       # other area hidden

    # Admin/super admin sees everything.
    all_names = {d["filename"] for d in client.get("/documents", headers=su).json()}
    assert {"v.txt", "r.txt", "general.txt"} <= all_names


def test_only_super_admin_lists_tenants(client):
    seller = _login(client, "ventas@maestroai.mx")
    assert client.get("/admin/tenants", headers=seller).status_code == 403


def test_plain_admin_cannot_grant_super_admin(client):
    su = _login(client, "admin@maestroai.mx")
    client.post("/admin/users", headers=su, json={
        "email": "admin2@maestroai.mx", "name": "Admin Dos", "role": "admin"}).json()
    target = client.post("/admin/users", headers=su, json={
        "email": "target@maestroai.mx", "name": "Objetivo", "role": "user"}).json()

    ha = _login(client, "admin2@maestroai.mx")
    # A plain admin can re-tag area/license...
    ok = client.patch(f"/admin/users/{target['id']}", headers=ha, json={"area": "Finanzas", "license": "pro"})
    assert ok.status_code == 200 and ok.json()["area"] == "Finanzas"
    # ...but cannot grant super admin.
    denied = client.patch(f"/admin/users/{target['id']}", headers=ha, json={"role": "super_admin"})
    assert denied.status_code == 403
