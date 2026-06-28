"""Datos curados (pilot) del Tablero Financiero — cierre 2025, fuente CONTPAQi.

Números reales ya curados por el equipo de finanzas (de los archivos subidos). Esta
semilla se reemplaza por el conector a la fuente en Paso 1; el tablero no cambia.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def projects() -> dict:
    """Dataset real derivado del zip 'Resumen por proyecto' (101 proyectos 2025).

    En Paso 1 esto lo entrega el conector a la BD; el contrato no cambia.
    """
    try:
        return json.loads((_DATA_DIR / "projects_2025.json").read_text(encoding="utf-8"))
    except FileNotFoundError:  # pragma: no cover - el archivo viaja con el repo
        return {"source": "", "totals": {}, "trend": {}, "clients": [], "projects": []}

COMPANY = {
    "name": "Silent4Business", "legalName": "Silent4Business + Silent4Cloud",
    "period": "2025 cierre · CONTPAQi", "ceo": "Ángel Beltrán", "cfo": "Lourdes Abadía",
}

# P&L + balance por entidad (2025)
FY = {
    "S4B": {"revenue": 467909597, "costos": 297605953, "ub": 170303644, "ebitda": 90090808,
            "neta": 67789285, "activo": 366322060, "capital": 190643105, "pasivo": 175678955,
            "cash": 149034288, "ar": 65954203, "ap": 120381270, "wc": 86759321,
            "margen_bruto": 0.364, "margen_ebitda": 0.193, "margen_neto": 0.145,
            "dso": 51, "dpo": 148, "ccc": -97, "roe": 0.356, "endeudamiento": 0.480},
    "S4C": {"revenue": 35098004, "costos": 22114839, "ub": 12983165, "ebitda": 3141696,
            "neta": 1515178, "activo": 31966356, "capital": 4085557, "pasivo": 27880799,
            "cash": 3469106, "ar": 22735040, "ap": 3121929, "wc": 3772889,
            "margen_bruto": 0.370, "margen_ebitda": 0.090, "margen_neto": 0.043,
            "dso": 236, "dpo": 52, "ccc": 184, "roe": 0.371, "endeudamiento": 0.872},
}
# Headcount real (grupo): 80 S4B + 46 S4C + 14 otra = 140
HEADCOUNT = {"S4B": 80, "S4C": 46, "CONS": 140}
FY_2024 = {"S4B": {"revenue": 312888833, "ebitda": 61750000},
           "S4C": {"revenue": 18590989, "ebitda": 965549}}


def _cons(a: dict, b: dict) -> dict:
    r = {k: a[k] + b[k] for k in ("revenue", "costos", "ub", "ebitda", "neta", "activo",
                                  "capital", "pasivo", "cash", "ar", "ap", "wc")}
    r["margen_bruto"] = r["ub"] / r["revenue"]
    r["margen_ebitda"] = r["ebitda"] / r["revenue"]
    r["margen_neto"] = r["neta"] / r["revenue"]
    r["dso"] = round(r["ar"] / r["revenue"] * 365)
    r["dpo"] = round(r["ap"] / r["costos"] * 365)
    r["ccc"] = r["dso"] - r["dpo"]
    r["roe"] = r["neta"] / r["capital"]
    r["endeudamiento"] = r["pasivo"] / r["activo"]
    return r


FY["CONS"] = _cons(FY["S4B"], FY["S4C"])
FY_2024["CONS"] = {"revenue": FY_2024["S4B"]["revenue"] + FY_2024["S4C"]["revenue"],
                   "ebitda": FY_2024["S4B"]["ebitda"] + FY_2024["S4C"]["ebitda"]}

# Evolución mensual (millones MXN)
MONTHLY = {
    "S4B": [{"mes": "Ene", "ingresos": 25.6, "ebitda": 3.4}, {"mes": "Feb", "ingresos": 30.1, "ebitda": 4.6},
            {"mes": "Mar", "ingresos": 33.4, "ebitda": 5.4}, {"mes": "Abr", "ingresos": 36.2, "ebitda": 6.0},
            {"mes": "May", "ingresos": 38.7, "ebitda": 6.7}, {"mes": "Jun", "ingresos": 41.7, "ebitda": 7.3},
            {"mes": "Jul", "ingresos": 40.4, "ebitda": 6.9}, {"mes": "Ago", "ingresos": 42.6, "ebitda": 7.5},
            {"mes": "Sep", "ingresos": 44.7, "ebitda": 8.0}, {"mes": "Oct", "ingresos": 45.0, "ebitda": 8.2},
            {"mes": "Nov", "ingresos": 44.7, "ebitda": 8.1}, {"mes": "Dic", "ingresos": 45.5, "ebitda": 8.8}],
    "S4C": [{"mes": "Ene", "ingresos": 1.8, "ebitda": 0.10}, {"mes": "Feb", "ingresos": 2.0, "ebitda": 0.12},
            {"mes": "Mar", "ingresos": 2.4, "ebitda": 0.18}, {"mes": "Abr", "ingresos": 2.8, "ebitda": 0.21},
            {"mes": "May", "ingresos": 3.0, "ebitda": 0.25}, {"mes": "Jun", "ingresos": 3.2, "ebitda": 0.28},
            {"mes": "Jul", "ingresos": 3.0, "ebitda": 0.27}, {"mes": "Ago", "ingresos": 3.1, "ebitda": 0.28},
            {"mes": "Sep", "ingresos": 3.3, "ebitda": 0.30}, {"mes": "Oct", "ingresos": 3.2, "ebitda": 0.29},
            {"mes": "Nov", "ingresos": 3.0, "ebitda": 0.27}, {"mes": "Dic", "ingresos": 4.3, "ebitda": 0.59}],
}
MONTHLY["CONS"] = [{"mes": a["mes"], "ingresos": round(a["ingresos"] + b["ingresos"], 1),
                    "ebitda": round(a["ebitda"] + b["ebitda"], 2)}
                   for a, b in zip(MONTHLY["S4B"], MONTHLY["S4C"])]

# Líneas de servicio (revenue MXN, margen)
SEGMENTS = {
    "S4B": [{"name": "SOC-NOC Administrado", "revenue": 182315538, "margin": 0.45, "tipo": "Recurrente"},
            {"name": "Infraestructura", "revenue": 206921772, "margin": 0.08, "tipo": "Infraestructura"},
            {"name": "Ciberseguridad", "revenue": 39618544, "margin": 0.35, "tipo": "Proyecto"},
            {"name": "Consultoría TI", "revenue": 39090983, "margin": 0.30, "tipo": "Proyecto"},
            {"name": "Innovación", "revenue": 79526, "margin": 0.25, "tipo": "Proyecto"}],
    "S4C": [{"name": "SOC-NOC Administrado", "revenue": 4680340, "margin": 0.45, "tipo": "Recurrente"},
            {"name": "Infraestructura", "revenue": 14101094, "margin": 0.08, "tipo": "Infraestructura"},
            {"name": "Ciberseguridad", "revenue": 4584329, "margin": 0.35, "tipo": "Proyecto"},
            {"name": "Consultoría TI", "revenue": 13359309, "margin": 0.30, "tipo": "Proyecto"}],
}
SEGMENTS["CONS"] = SEGMENTS["S4B"]  # vista consolidada usa la mezcla principal (pilot)

# Gobierno vs IP por año (consolidado)
GOB_IP = {"2023": {"gob": 138255598, "ip": 42422472},
          "2024": {"gob": 243339105, "ip": 86576464},
          "2025": {"gob": 290862274, "ip": 171542502}}

BENCHMARKS = [
    {"metric": "Crecimiento YoY", "s4b": 0.518, "industry": 0.135, "topQ": 0.240, "format": "pct", "higherBetter": True},
    {"metric": "Margen bruto", "s4b": 0.365, "industry": 0.555, "topQ": 0.620, "format": "pct", "higherBetter": True},
    {"metric": "Margen EBITDA", "s4b": 0.185, "industry": 0.180, "topQ": 0.270, "format": "pct", "higherBetter": True},
    {"metric": "Regla del 40", "s4b": 0.703, "industry": 0.315, "topQ": 0.500, "format": "pct", "higherBetter": True},
    {"metric": "DSO (días)", "s4b": 64, "industry": 62, "topQ": 45, "format": "days", "higherBetter": False},
    {"metric": "Cash Conversion Cycle", "s4b": -81, "industry": 30, "topQ": -10, "format": "days", "higherBetter": False},
    {"metric": "% Ingresos recurrentes", "s4b": 0.39, "industry": 0.55, "topQ": 0.75, "format": "pct", "higherBetter": True},
]

ALERTS = [
    {"level": "high", "area": "Concentración", "msg": "Infraestructura 44% del top-line consolidado; comprador descontaría por menor margen estructural.", "impact": 100000000},
    {"level": "high", "area": "Cartera S4C", "msg": "DSO de S4C en 236 días — capital de trabajo amarrado.", "impact": 22735040},
    {"level": "med", "area": "Margen bruto", "msg": "Margen bruto 36.4% bajo el benchmark MSP (45-60%) por el mix con Infraestructura.", "impact": 50000000},
    {"level": "med", "area": "Recurrencia", "msg": "% ingresos recurrentes 39% bajo el benchmark (55-75%) — afecta múltiplo en M&A.", "impact": None},
    {"level": "low", "area": "Eliminaciones", "msg": "Eliminaciones intercompany S4B↔S4C aún no formales en consolidado.", "impact": None},
]

# Top clientes (curado; subset de campos)
TOP_CLIENTS = [
    {"name": "Cámara de Senadores", "sector": "Gobierno", "entity": "S4B", "revenue": 118454384, "margin": 0.20, "status": "green"},
    {"name": "OperBes (IMSS)", "sector": "IP", "entity": "S4B", "revenue": 86747057, "margin": 0.28, "status": "green"},
    {"name": "H. Cámara de Diputados", "sector": "Gobierno", "entity": "S4B", "revenue": 95845789, "margin": 0.20, "status": "amber"},
    {"name": "IFT", "sector": "Gobierno", "entity": "S4B", "revenue": 4723369, "margin": 0.20, "status": "green"},
    {"name": "PEMEX", "sector": "Gobierno", "entity": "S4B", "revenue": 21458522, "margin": 0.20, "status": "green"},
    {"name": "N Digital Evolution", "sector": "IP", "entity": "S4B", "revenue": 52000000, "margin": 0.28, "status": "amber"},
    {"name": "Banjército", "sector": "Gobierno", "entity": "S4B", "revenue": 10790908, "margin": 0.20, "status": "green"},
    {"name": "Banco Ve por Más", "sector": "IP", "entity": "S4B", "revenue": 6040570, "margin": 0.28, "status": "green"},
    {"name": "Banobras", "sector": "Gobierno", "entity": "S4B", "revenue": 15000832, "margin": 0.20, "status": "amber"},
    {"name": "CFE", "sector": "Gobierno", "entity": "S4B", "revenue": 12245542, "margin": 0.20, "status": "amber"},
    {"name": "Grupo Modelo", "sector": "IP", "entity": "S4C", "revenue": 49000, "margin": 0.28, "status": "green"},
    {"name": "ABC Medical Center", "sector": "IP", "entity": "S4C", "revenue": 3215747, "margin": 0.28, "status": "green"},
]


def entity_kpis(entity: str) -> dict:
    d = FY.get(entity, FY["CONS"])
    prev = FY_2024.get(entity, FY_2024["CONS"])
    growth = (d["revenue"] / prev["revenue"] - 1) if prev.get("revenue") else 0.0
    return {**d, "growth": growth}
