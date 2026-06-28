"""Tablero Financiero (pilot): overview, clientes y preguntar (RAG)."""
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


def test_overview_consolidado_and_entity(client):
    h = _auth(client)
    cons = client.get("/finance/overview?entity=CONS", headers=h).json()
    assert cons["entity"] == "CONS"
    assert cons["kpis"]["revenue"] > 5e8  # S4B + S4C
    assert len(cons["monthly"]) == 12 and cons["segments"] and cons["alerts"]
    s4b = client.get("/finance/overview?entity=S4B", headers=h).json()
    assert s4b["kpis"]["revenue"] == 467909597
    # entidad inválida cae a CONS
    assert client.get("/finance/overview?entity=ZZZ", headers=h).json()["entity"] == "CONS"


def test_clients_filtered_by_entity(client):
    h = _auth(client)
    allc = client.get("/finance/clients?entity=CONS", headers=h).json()
    assert allc and allc[0]["revenue"] >= allc[-1]["revenue"]  # ordenado desc
    s4c = client.get("/finance/clients?entity=S4C", headers=h).json()
    assert s4c and all(c["entity"] == "S4C" for c in s4c)


def test_ask_grounded(client, monkeypatch):
    h = _auth(client)
    captured = {}
    import app.routers.finance as fin

    class _Resp:
        content = "El EBITDA consolidado es $93.2M (18.5%)."

    class _Gen:
        response = _Resp()
        class route:  # noqa: N801
            value = "open"

    def fake_gen(route, system, prompt, context):
        captured["prompt"] = prompt
        return _Gen()

    monkeypatch.setattr(fin, "generate_with_fallback", fake_gen, raising=False)
    # también parchamos el import dentro de la función
    import app.ai.resilience as res
    monkeypatch.setattr(res, "generate_with_fallback", fake_gen, raising=False)

    r = client.post("/finance/ask", headers=h, json={"question": "¿Cuál es el EBITDA?", "entity": "CONS"}).json()
    assert "answer" in r and r["entity"] == "CONS"
    # el contexto incluyó cifras reales (anti-alucinación)
    assert "Ingresos" in captured.get("prompt", "") and "EBITDA" in captured.get("prompt", "")
