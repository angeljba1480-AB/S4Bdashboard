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


def _xlsx_bytes(rows_by_sheet: dict[str, list[list]]) -> bytes:
    import io
    import openpyxl
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet, rows in rows_by_sheet.items():
        ws = wb.create_sheet(sheet)
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _nomina_xlsx() -> bytes:
    """Export sintético estilo 'Lista de Raya' (sin datos reales): 2025 completo
    (12 meses) y 2026 parcial (ene-feb)."""
    hdr = ["Código", "Empleado", "*TOTAL* *PERCEPCIONES*", "*TOTAL* *OBLIGACIONES*"]
    sheet_2025 = [
        [None, "Periodo 1 al 24 Quincenal del 01/01/2025 al 31/12/2025"],
        [],
        hdr,
        ["00001", "PEREZ LOPEZ JUAN", 120000, 24000],
        ["00002", "GOMEZ DIAZ ANA", 96000, 19200],
        ["Total Gral.", "", 216000, 43200],
    ]
    sheet_2026 = [
        [None, "Periodo 1 al 4 Quincenal del 01/01/2026 al 28/02/2026"],
        [],
        hdr,
        ["00001", "PEREZ LOPEZ JUAN", 22000, 4400],
        ["00002", "GOMEZ DIAZ ANA", 17000, 3400],
    ]
    return _xlsx_bytes({"2025": sheet_2025, "2026": sheet_2026})


def _timesheet_xlsx() -> bytes:
    """Reporte de horas sintético — el nombre del archivo NO contiene 'timesheet' a
    propósito, para probar que se detecta por columnas."""
    hdr = ["Fecha Dia", "Empleado", "Supervisor", "Proyecto", "Tarea", "Descripción", "Total de Horas"]
    rows = [hdr]
    for fecha, horas_juan, horas_ana, proyecto in [
        ("15/12/2025", 80, 70, "Cliente A - Soporte"),
        ("20/12/2025", 40, 50, "Cliente B - SOC"),
        ("10/01/2026", 80, 80, "Cliente A - Soporte"),
        ("15/02/2026", 80, 80, "Cliente B - SOC"),
    ]:
        rows.append([fecha, "Juan Perez Lopez", "Jefe", proyecto, "Tarea", "Nota", horas_juan])
        rows.append([fecha, "Ana Gomez Diaz", "Jefe", proyecto, "Tarea", "Nota", horas_ana])
    return _xlsx_bytes({"Worksheet": rows})


def test_nomina_timesheet_cost_comparison():
    """Nómina (costo_cmi) × Timesheet (costo_timesheet), sin Resumen ni Concentrado."""
    from app.finance.ingest_excel import build_dataset_from_files
    files = [("nomina.xlsx", _nomina_xlsx()), ("reporte_colaborador.xlsx", _timesheet_xlsx())]
    out = build_dataset_from_files(files)

    cc = out["cost_comparison"]
    assert set(cc["available"]) == {"costo_cmi", "costo_timesheet"}
    assert cc["pending"] == ["costo_bc"]
    by_key = {(r["anio"], r["mes"]): r for r in cc["by_month"]}
    assert len(by_key) == 12 + 2  # 2025 completo + 2026 ene-feb

    # costo_cmi: 2025 = (216000+43200)/12 por mes; 2026 = (39000+7800)/2 por mes
    assert by_key[("2025", "ENE")]["costo_cmi"] == round((216000 + 43200) / 12)
    assert by_key[("2025", "ENE")]["costo_timesheet"] is None  # sin horas ese mes
    assert by_key[("2026", "ENE")]["costo_cmi"] == round((39000 + 7800) / 2)

    # costo_timesheet solo en los meses con horas reales (dic-2025, ene/feb-2026)
    assert by_key[("2025", "DIC")]["costo_timesheet"] is not None
    assert by_key[("2026", "ENE")]["costo_timesheet"] is not None
    assert by_key[("2026", "FEB")]["costo_timesheet"] is not None
    # mismo orden de magnitud que costo_cmi del mismo periodo (no una mezcla de
    # "costo del año completo" contra "horas de un mes")
    dic = by_key[("2025", "DIC")]
    assert 0.3 < dic["costo_timesheet"] / dic["costo_cmi"] < 3

    # utilization se detecta por columnas aunque el archivo no se llame "timesheet*"
    util = out["utilization"]
    assert util["empleados"] == 2
    assert util["horas_reales"] > 0
    assert any(p["nombre"].startswith("Cliente") for p in util["by_project"])
    assert out["partial_entities"] is True
    assert "Nómina/Timesheet" in out["company"]["period"]


def test_nomina_solo_sin_timesheet():
    """Solo Nómina (sin Resumen/Concentrado/Timesheet) ya no debe fallar (antes
    build_dataset_from_files exigía 'Resumen por proyecto')."""
    from app.finance.ingest_excel import build_dataset_from_files
    out = build_dataset_from_files([("nomina.xlsx", _nomina_xlsx())])
    cc = out["cost_comparison"]
    assert cc["available"] == ["costo_cmi"]
    assert set(cc["pending"]) == {"costo_bc", "costo_timesheet"}
    assert "utilization" not in out or out["utilization"] == _dataset_demo_utilization()


def _dataset_demo_utilization():
    from app.finance import dataset as _ds
    return _ds.load().get("utilization", {})


def test_upload_real_excel_endpoint(client):
    """Sube Nómina + Timesheet vía /finance/dataset y verifica /finance/operations."""
    h = _auth(client)
    files = [("files", ("nomina.xlsx", _nomina_xlsx(),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("files", ("reporte_colaborador.xlsx", _timesheet_xlsx(),
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]
    r = client.post("/finance/dataset", headers=h, files=files)
    assert r.status_code == 201 and r.json()["source"] == "excel"
    ops = client.get("/finance/operations", headers=h).json()
    cc = ops["cost_comparison"]
    assert set(cc["available"]) == {"costo_cmi", "costo_timesheet"}
    assert ops["utilization"]["empleados"] == 2
    assert client.delete("/finance/dataset", headers=h).json()["ok"]


def test_dataset_template_download(client):
    h = _auth(client)
    r = client.get("/finance/dataset/template", headers=h)
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")
    body = r.json()
    assert "_instrucciones" in body and "company" in body and "monthly" in body
    assert "_is_demo" not in body


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
