"""Biblioteca de runbooks: listado, facetas y instalación como playbook."""
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


def test_facets_have_sectors_and_segments(client):
    f = client.get("/runbooks/facets", headers=_auth(client)).json()
    sectors = {s["key"] for s in f["sectors"]}
    assert {"servicios", "manufactura", "retail", "logistica"} <= sectors
    assert {s["key"] for s in f["segments"]} == {"pyme", "enterprise"}
    assert f["total"] >= 10


def test_list_and_filter(client):
    h = _auth(client)
    allrb = client.get("/runbooks", headers=h).json()
    assert len(allrb) >= 10
    # filtro por sector manufactura
    manuf = client.get("/runbooks?sector=manufactura", headers=h).json()
    assert manuf and all(r["sector"] == "manufactura" for r in manuf)
    # filtro por segmento enterprise incluye los marcados "ambos"
    ent = client.get("/runbooks?segment=enterprise", headers=h).json()
    assert ent and all(r["segment"] in ("enterprise", "ambos") for r in ent)
    # búsqueda por texto
    found = client.get("/runbooks?q=OEE", headers=h).json()
    assert any("oee" in (r["title"] + r["description"]).lower() for r in found)


def test_install_creates_playbook_idempotent(client):
    h = _auth(client)
    r1 = client.post("/runbooks/triage_tickets/install", headers=h).json()
    assert r1["already_installed"] is False and r1["id"]
    # aparece como playbook del agente
    pbs = client.get("/actions/playbooks", headers=h).json()
    assert any(p["id"] == r1["id"] and p["name"] for p in pbs)
    # instalar de nuevo no duplica
    r2 = client.post("/runbooks/triage_tickets/install", headers=h).json()
    assert r2["already_installed"] is True and r2["id"] == r1["id"]


def test_install_unknown_404(client):
    assert client.post("/runbooks/nope/install", headers=_auth(client)).status_code == 404
