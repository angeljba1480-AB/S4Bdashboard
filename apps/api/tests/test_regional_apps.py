"""Regional catalog + App Studio (pay-to-prod) tests."""
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


# --- regional ---------------------------------------------------------------
def test_regional_ejes_and_filter(client):
    h = _auth(client)
    ejes = client.get("/regional/ejes", headers=h).json()
    assert any(e["id"] == "economia" for e in ejes)
    assert all("count" in e for e in ejes)

    eco = client.get("/regional/procedures?eje=economia", headers=h).json()
    assert eco and all(p["eje"] == "economia" for p in eco)


def test_procedure_to_proposal_feeds_curation(client):
    h = _auth(client)
    proc = client.get("/regional/procedures", headers=h).json()[0]
    prop = client.post(f"/regional/procedures/{proc['id']}/propose", headers=h).json()
    assert prop["status"] == "proposed"
    titles = [p["title"] for p in client.get("/recipes/proposals", headers=h).json()]
    assert proc["title"] in titles


# --- app studio (pay-to-prod) ----------------------------------------------
def test_app_build_then_paywalled_deploy(client):
    h = _auth(client)
    appp = client.post("/apps", headers=h, json={
        "name": "Citas Barbería", "description": "agenda de citas con recordatorios por WhatsApp",
    }).json()
    assert appp["status"] == "built"
    assert appp["paid"] is False

    # deploy without paying -> 402 with checkout
    blocked = client.post(f"/apps/{appp['id']}/deploy", headers=h)
    assert blocked.status_code == 402
    detail = blocked.json()["detail"]
    assert detail["checkout"]["amount"] > 0

    # confirm payment (stub) then deploy succeeds
    client.post(f"/apps/{appp['id']}/checkout", headers=h)
    deployed = client.post(f"/apps/{appp['id']}/deploy", headers=h).json()
    assert deployed["status"] == "deployed"
    assert deployed["deploy_url"]


def test_app_requires_name(client):
    h = _auth(client)
    assert client.post("/apps", headers=h, json={"name": "", "description": "x"}).status_code == 422
