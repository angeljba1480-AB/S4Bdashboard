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
    # CONS = S4B + S4C (agnóstico al dataset: demo o real inyectado)
    s4b = client.get("/finance/overview?entity=S4B", headers=h).json()
    s4c = client.get("/finance/overview?entity=S4C", headers=h).json()
    assert cons["kpis"]["revenue"] == s4b["kpis"]["revenue"] + s4c["kpis"]["revenue"]
    assert cons["kpis"]["revenue"] > 0
    assert len(cons["monthly"]) == 12 and cons["segments"] and cons["alerts"]
    # entidad inválida cae a CONS
    assert client.get("/finance/overview?entity=ZZZ", headers=h).json()["entity"] == "CONS"


def test_clients_filtered_by_entity(client):
    h = _auth(client)
    allc = client.get("/finance/clients?entity=CONS", headers=h).json()
    assert allc and allc[0]["revenue"] >= allc[-1]["revenue"]  # ordenado desc
    s4c = client.get("/finance/clients?entity=S4C", headers=h).json()
    assert s4c and all(c["entity"] == "S4C" for c in s4c)


def test_projects_and_operations(client):
    h = _auth(client)
    pr = client.get("/finance/projects", headers=h).json()
    assert pr["totals"]["proyectos"] > 0 and pr["trend"] and pr["detail"]
    assert "ebitda_bc" in pr["totals"] and "desviacion" in pr["totals"]  # plan vs real
    ops = client.get("/finance/operations", headers=h).json()
    assert 0 <= ops["utilization"]["utilizacion"] <= 1
    assert ops["cost_per_hour"]["by_role"] and ops["client_scoring"]["clients"]
    # comparativo de costos cableado (RESUMEN_COSTOS): siempre trae costo_bc
    cc = ops["cost_comparison"]
    assert cc["by_month"] and "costo_bc" in cc["available"]
    assert all({"anio", "mes", "costo_bc", "costo_cmi", "costo_timesheet"} <= set(r) for r in cc["by_month"])


def test_map_rows_to_dataset():
    """SELECT/CSV (filas) → bloque de proyectos del tablero, vía mapeo."""
    from app.finance.ingest_tabular import build_projects_from_rows
    rows = [
        {"CLIENTE": "IMSS", "PROY": "SOC", "TIPO": "Gobierno", "ANIO": "2025", "VTA": 1000000, "MGN": 300000, "EB": 200000},
        {"CLIENTE": "ALSEA", "PROY": "Lic", "TIPO": "Privado", "ANIO": "2025", "VTA": 500000, "MGN": 100000, "EB": 80000},
    ]
    mapping = {"cliente": "CLIENTE", "nombre": "PROY", "tipo": "TIPO", "anio": "ANIO",
               "venta": "VTA", "margen": "MGN", "ebitda": "EB"}
    data = build_projects_from_rows(rows, mapping)
    t = data["projects"]["totals"]
    assert t["venta"] == 1500000 and t["proyectos"] == 2
    assert data["projects"]["detail"][0]["cliente"] == "IMSS"  # ordenado por venta
    assert data["gob_ip"]["2025"]["gob"] == 1000000 and data["gob_ip"]["2025"]["ip"] == 500000


def test_dataset_upload_override_and_delete(client):
    import json
    h = _auth(client)
    # estado inicial: sin dataset cargado (demo o entorno)
    st0 = client.get("/finance/dataset/status", headers=h).json()
    # subir un JSON que cambia el nombre de la compañía (se mezcla sobre el base)
    payload = json.dumps({"company": {"name": "ACME Pilot", "legalName": "ACME", "period": "2025", "ceo": "", "cfo": ""}})
    r = client.post("/finance/dataset", headers=h,
                    files=[("files", ("d.json", payload.encode(), "application/json"))])
    assert r.status_code == 201 and r.json()["source"] == "json"
    ov = client.get("/finance/overview?entity=CONS", headers=h).json()
    assert ov["company"]["name"] == "ACME Pilot" and ov["is_demo"] is False
    assert client.get("/finance/dataset/status", headers=h).json()["loaded"] is True
    # borrar → vuelve al base
    assert client.delete("/finance/dataset", headers=h).json()["ok"] is True
    ov2 = client.get("/finance/overview?entity=CONS", headers=h).json()
    assert ov2["company"]["name"] != "ACME Pilot"
    _ = st0


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
