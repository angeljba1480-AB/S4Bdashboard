"""Mapea filas tabulares (resultado de un SELECT del conector legado, o un CSV) al
dataset del Tablero Financiero — el **Paso 1 (BD en vivo)** reutilizando el conector
de sistemas legados (`/datasources`) + el transformador que ya existe.

- ``build_projects_from_rows(rows, mapping)``: aplica el mapeo columna→campo y arma el
  bloque ``projects`` (totales, tendencia, mezcla Gob/IP, clientes, detalle), sobre el
  dataset base (como el ingest de Excel).
- ``propose_mapping(...)``: un **agente** propone qué columna corresponde a cada campo
  (cliente/venta/costos/…) a partir de los nombres de columna y una muestra (+ pista ER).
  El usuario lo confirma antes de aplicar.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy

from . import dataset as _dataset
from .ingest_excel import _agg_clients, _num

# Campos destino del bloque de proyectos. Mínimos para cerrar: cliente + venta.
TARGET_FIELDS = ["cliente", "nombre", "tipo", "anio", "venta", "costos",
                 "margen", "ebitda", "ebitda_bc"]


def _tipo(v) -> str:
    s = str(v or "").strip().upper()
    return "Gobierno" if s.startswith("GOB") else "Privado"


def build_projects_from_rows(rows: list[dict], mapping: dict) -> dict:
    """``rows`` = lista de dicts (columna→valor); ``mapping`` = {campo_destino: columna}."""
    def g(row, field):
        col = mapping.get(field)
        return row.get(col) if col else None

    if not mapping.get("cliente") or not mapping.get("venta"):
        raise ValueError("El mapeo debe incluir al menos 'cliente' y 'venta'.")

    by_year: dict[str, dict] = {}
    projects_by_year: dict[str, list] = {}
    for r in rows:
        venta = _num(g(r, "venta"))
        if venta <= 0:
            continue
        yr = str(g(r, "anio") or "actual").split(".")[0].strip() or "actual"
        gob = _tipo(g(r, "tipo")) == "Gobierno"
        margen = _num(g(r, "margen")); ebitda = _num(g(r, "ebitda")); ebitda_bc = _num(g(r, "ebitda_bc"))
        costos = _num(g(r, "costos")) or (venta - margen if margen else 0)
        a = by_year.setdefault(yr, dict(venta=0, costos=0, margen=0, ebitda=0, ebitda_bc=0,
                                        gob=0, ip=0, proyectos=0))
        a["venta"] += venta; a["costos"] += costos; a["margen"] += margen
        a["ebitda"] += ebitda; a["ebitda_bc"] += ebitda_bc; a["proyectos"] += 1
        a["gob" if gob else "ip"] += venta
        projects_by_year.setdefault(yr, []).append(dict(
            cliente=str(g(r, "cliente") or "").strip(),
            nombre=str(g(r, "nombre") or "").strip()[:60],
            tipo="Gobierno" if gob else "Privado",
            venta=round(venta), costos=round(costos), margen=round(margen),
            pct_margen=round(margen / venta, 3) if venta else 0,
            ebitda=round(ebitda), ebitda_bc=round(ebitda_bc),
            desviacion=round(ebitda - ebitda_bc)))
    if not by_year:
        raise ValueError("Ninguna fila tenía 'venta' > 0 con el mapeo dado.")

    latest = max(by_year, key=lambda y: by_year[y]["venta"])
    a = by_year[latest]
    trend = {y: dict(venta=round(v["venta"]), gob=round(v["gob"]), ip=round(v["ip"]),
                     ebitda=round(v["ebitda"]), ebitda_bc=round(v["ebitda_bc"]),
                     margen=round(v["margen"]), proyectos=v["proyectos"],
                     desviacion=round(v["ebitda"] - v["ebitda_bc"]))
             for y, v in by_year.items()}

    out = deepcopy(_dataset.load())
    out.pop("_origin", None); out.pop("_is_demo", None)
    out["projects"] = dict(
        source="Cargado desde BD (conector legado · SELECT)",
        totals=dict(venta=round(a["venta"]), costos=round(a["costos"]), margen=round(a["margen"]),
                    ebitda=round(a["ebitda"]), ebitda_bc=round(a["ebitda_bc"]),
                    pct_margen=round(a["margen"] / a["venta"], 3) if a["venta"] else 0,
                    pct_ebitda=round(a["ebitda"] / a["venta"], 3) if a["venta"] else 0,
                    desviacion=round(a["ebitda"] - a["ebitda_bc"]), proyectos=a["proyectos"]),
        trend=trend,
        cost_mix=(out.get("projects") or {}).get("cost_mix", {}),
        clients=_agg_clients(projects_by_year[latest])[:20],
        detail=sorted(projects_by_year[latest], key=lambda x: -x["venta"])[:30])
    out["gob_ip"] = {y: dict(gob=trend[y]["gob"], ip=trend[y]["ip"]) for y in trend}
    out["company"] = {**out.get("company", {}), "period": f"BD en vivo · cierre {latest}"}
    out["partial_entities"] = True
    out["_source_files"] = "datasource:sql"
    return out


def propose_mapping(tenant, columns: list[str], sample_rows: list[dict], er_hint: str = "") -> dict:
    """Un agente propone {campo_destino: columna} a partir de columnas + muestra (+ ER)."""
    from ..ai.resilience import generate_with_fallback
    from ..ai.router import route_request

    system = ("Eres un asistente de integración de datos. Mapea columnas de una tabla SQL a los "
              "campos del Tablero Financiero. Responde SOLO un objeto JSON {campo: columna} usando "
              "EXACTAMENTE los nombres de columna provistos; omite los campos sin correspondencia. "
              "Campos válidos: " + ", ".join(TARGET_FIELDS) + ".")
    prompt = (f"Columnas disponibles: {columns}\n"
              f"Muestra de filas: {json.dumps(sample_rows[:3], ensure_ascii=False, default=str)}\n"
              + (f"Pista (modelo entidad-relación): {er_hint}\n" if er_hint else "")
              + "Devuelve el mapeo JSON (campo del tablero → columna SQL).")
    try:
        decision = route_request(tenant, None, prompt, [], task="recipe")
        gen = generate_with_fallback(decision.route, system, prompt, decision.context or [])
        m = re.search(r"\{.*\}", gen.response.content or "", re.S)
        proposed = json.loads(m.group(0)) if m else {}
    except Exception:
        proposed = {}
    # Solo conserva campos válidos cuyo valor sea una columna real.
    cols = set(columns)
    return {k: v for k, v in proposed.items() if k in TARGET_FIELDS and v in cols}
