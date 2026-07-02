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


# --- app studio: publicación honesta ---------------------------------------
def test_app_deploy_sin_pago_es_simulado(client):
    """Sin pasarela (por defecto): publicar NO cobra ni despliega real → simulado."""
    h = _auth(client)
    appp = client.post("/apps", headers=h, json={
        "name": "Citas Barbería", "description": "agenda de citas con recordatorios por WhatsApp",
    }).json()
    assert appp["status"] == "built"
    assert appp["paid"] is False

    out = client.post(f"/apps/{appp['id']}/deploy", headers=h)
    assert out.status_code == 200
    j = out.json()
    assert j["status"] == "simulado" and j["simulated"] is True
    assert not j["deploy_url"]  # no se fabrica una URL muerta
    assert "simulad" in (j["note"] or "").lower()

    # el checkout no cobra: responde 409 (pagos no habilitados)
    ck = client.post(f"/apps/{appp['id']}/checkout", headers=h)
    assert ck.status_code == 409


def test_app_deploy_con_pasarela_es_paywalled(client, monkeypatch):
    """Con PAYMENTS_ENABLED sí es pay-to-prod: 402 → checkout → deployed."""
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "payments_enabled", True)
    h = _auth(client)
    appp = client.post("/apps", headers=h, json={
        "name": "Citas 2", "description": "agenda con recordatorios",
    }).json()
    blocked = client.post(f"/apps/{appp['id']}/deploy", headers=h)
    assert blocked.status_code == 402
    assert blocked.json()["detail"]["checkout"]["amount"] > 0
    client.post(f"/apps/{appp['id']}/checkout", headers=h)
    deployed = client.post(f"/apps/{appp['id']}/deploy", headers=h).json()
    assert deployed["status"] == "deployed" and deployed["deploy_url"]


def test_app_requires_name(client):
    h = _auth(client)
    assert client.post("/apps", headers=h, json={"name": "", "description": "x"}).status_code == 422
