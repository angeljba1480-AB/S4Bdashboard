"""/finance — Tablero Financiero (pilot) servido por endpoint + preguntar (RAG).

La data sale de la semilla curada (`app.finance.seed`). En Paso 1 se sustituye por el
conector a la BD/origen; el contrato del endpoint no cambia.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import get_current_tenant, get_current_user
from ..finance import seed
from ..models import Tenant, User

router = APIRouter(prefix="/finance", tags=["finance"])

_ENTITIES = {"S4B", "S4C", "CONS"}


def _entity(e: str) -> str:
    e = (e or "CONS").upper()
    return e if e in _ENTITIES else "CONS"


@router.get("/overview")
def overview(entity: str = "CONS", _: User = Depends(get_current_user)) -> dict:
    e = _entity(entity)
    k = seed.entity_kpis(e)
    segs = sorted(seed.SEGMENTS[e], key=lambda s: -s["revenue"])
    clientes = seed.TOP_CLIENTS if e == "CONS" else [c for c in seed.TOP_CLIENTS if c["entity"] == e]
    rule40 = k["growth"] + k["margen_ebitda"]
    return {
        "entity": e, "company": seed.COMPANY,
        "kpis": {
            "revenue": k["revenue"], "costos": k["costos"], "ub": k["ub"],
            "ebitda": k["ebitda"], "neta": k["neta"],
            "margen_bruto": k["margen_bruto"], "margen_ebitda": k["margen_ebitda"],
            "margen_neto": k["margen_neto"],
            "dso": k["dso"], "dpo": k["dpo"], "ccc": k["ccc"], "roe": k["roe"],
            "endeudamiento": k["endeudamiento"], "growth": k["growth"],
            "activo": k["activo"], "pasivo": k["pasivo"], "capital": k["capital"],
            "cash": k["cash"], "ar": k["ar"], "ap": k["ap"], "wc": k["wc"],
            "headcount": seed.HEADCOUNT.get(e, seed.HEADCOUNT["CONS"]),
            "rule40": rule40,
            "headcount_s4b": seed.HEADCOUNT["S4B"], "headcount_s4c": seed.HEADCOUNT["S4C"],
            "revenue_s4b": seed.FY["S4B"]["revenue"], "revenue_s4c": seed.FY["S4C"]["revenue"],
            "ebitda_s4b": seed.FY["S4B"]["ebitda"], "ebitda_s4c": seed.FY["S4C"]["ebitda"],
        },
        "summary": {
            "caja": k["cash"], "cartera": k["ar"], "capital_trabajo": k["wc"], "rule40": rule40,
            "proyectos_riesgo": 6, "top_clientes": len(clientes), "lineas_servicio": len(segs),
            "linea_principal": segs[0]["name"] if segs else "",
            "alertas_criticas": len([a for a in seed.ALERTS if a["level"] == "high"]),
        },
        "monthly": seed.MONTHLY[e],
        "segments": sorted(seed.SEGMENTS[e], key=lambda s: -s["revenue"]),
        "gob_ip": seed.GOB_IP,
        "benchmarks": seed.BENCHMARKS,
        "alerts": seed.ALERTS,
        "source": "curado (pilot) · cierre 2025 CONTPAQi",
    }


@router.get("/clients")
def clients(entity: str = "CONS", _: User = Depends(get_current_user)) -> list[dict]:
    e = _entity(entity)
    rows = seed.TOP_CLIENTS if e == "CONS" else [c for c in seed.TOP_CLIENTS if c["entity"] == e]
    return sorted(rows, key=lambda c: -c["revenue"])


@router.get("/projects")
def projects(_: User = Depends(get_current_user)) -> dict:
    """Portafolio de proyectos (Resumen por proyecto): totales, tendencia, mezcla de
    costo, plan vs real (EBITDA presupuesto BC vs real) y detalle.

    Paso 1: este dataset lo entrega el conector a la BD; el contrato no cambia.
    """
    return seed.projects()


@router.get("/operations")
def operations(_: User = Depends(get_current_user)) -> dict:
    """Datos operativos derivados de los documentos del cliente:
    utilización (timesheet vs capacidad), costo por hora por rol (Concentrado BC)
    y evaluación/score de clientes (modelo ponderado del equipo).
    """
    return {
        "utilization": seed.utilization(),
        "cost_per_hour": seed.cost_per_hour(),
        "client_scoring": seed.client_scoring(),
        "cost_comparison": seed.cost_comparison(),
        "is_demo": seed.is_demo(),
    }


class AskIn(BaseModel):
    question: str
    entity: str = "CONS"


def _context(entity: str) -> str:
    """Texto compacto con las cifras para fundamentar la respuesta (anti-alucinación)."""
    k = seed.entity_kpis(entity)
    m = lambda n: f"${n/1_000_000:.1f}M"
    lines = [f"Entidad: {entity} ({seed.COMPANY['legalName']}), periodo {seed.COMPANY['period']}.",
             f"Ingresos {m(k['revenue'])}, EBITDA {m(k['ebitda'])} ({k['margen_ebitda']*100:.1f}%), "
             f"Utilidad neta {m(k['neta'])}, Margen bruto {k['margen_bruto']*100:.1f}%.",
             f"Crecimiento YoY {k['growth']*100:.1f}%. DSO {k['dso']}d, DPO {k['dpo']}d, CCC {k['ccc']}d, ROE {k['roe']*100:.1f}%.",
             f"Caja {m(k['cash'])}, Cuentas por cobrar {m(k['ar'])}.",
             "Líneas de servicio: " + "; ".join(f"{s['name']} {m(s['revenue'])} (margen {s['margin']*100:.0f}%)"
                                                 for s in seed.SEGMENTS[entity]),
             "Gobierno vs IP 2025: Gobierno " + m(seed.GOB_IP['2025']['gob']) + ", IP " + m(seed.GOB_IP['2025']['ip']) + ".",
             "Alertas: " + " | ".join(a["msg"] for a in seed.ALERTS)]
    pr = seed.projects()
    if pr.get("totals"):
        t = pr["totals"]
        lines.append(
            f"Portafolio de proyectos ({pr.get('source', '')}): {t.get('proyectos')} proyectos, "
            f"venta {m(t.get('venta', 0))}, margen {m(t.get('margen', 0))} ({t.get('pct_margen', 0)*100:.1f}%), "
            f"EBITDA real {m(t.get('ebitda', 0))} vs EBITDA presupuesto (BC) {m(t.get('ebitda_bc', 0))} "
            f"→ desviación {m(t.get('desviacion', 0))}.")
        cm = pr.get("cost_mix") or {}
        if cm:
            lines.append("Estructura de costo: " + "; ".join(
                f"{k.replace('_', '/')} {m(v)}" for k, v in cm.items() if v))
        top = pr.get("detail", [])[:8]
        if top:
            lines.append("Proyectos principales: " + "; ".join(
                f"{p['cliente']} {m(p['venta'])} (margen {p['pct_margen']*100:.0f}%, desv EBITDA {m(p.get('desviacion', 0))})"
                for p in top))
    u = seed.utilization()
    if u.get("utilizacion"):
        lines.append(
            f"Utilización {u.get('year', '')}: {u['utilizacion']*100:.0f}% "
            f"({u.get('horas_reales', 0):,} horas reales de {u.get('horas_capacidad', 0):,} de capacidad, "
            f"{u.get('empleados', 0)} personas).")
    sc = seed.client_scoring()
    if sc.get("clients"):
        top_sc = sorted(sc["clients"], key=lambda c: -c.get("score", 0))[:5]
        lines.append("Evaluación de clientes (score, tier): " + "; ".join(
            f"{c['name']} {c.get('score')} {c.get('tier', '')}" for c in top_sc))
    cc = seed.cost_comparison()
    if cc.get("by_month"):
        bc = sum(r.get("costo_bc") or 0 for r in cc["by_month"])
        cmi = sum(r.get("costo_cmi") or 0 for r in cc["by_month"])
        if cmi:
            lines.append(f"Comparativo de costos (RESUMEN_COSTOS): costo BC (presupuesto) {m(bc)}, "
                         f"costo CMI (nómina) {m(cmi)}.")
        else:
            lines.append(f"Comparativo de costos: costo BC (presupuesto) {m(bc)}. "
                         "costo_cmi y costo_timesheet pendientes (requieren tabla Nómina).")
    return "\n".join(lines)


@router.post("/ask")
def ask(body: AskIn, tenant: Tenant = Depends(get_current_tenant),
        _: User = Depends(get_current_user)) -> dict:
    """Pregunta sobre las cifras del tablero (RAG sobre los datos curados)."""
    from ..ai.resilience import generate_with_fallback
    from ..ai.router import route_request
    e = _entity(body.entity)
    ctx = _context(e)
    system = ("Eres analista financiero. Responde en español, claro y conciso, USANDO SOLO las "
              "cifras provistas; si no está en los datos, dilo. No inventes números.")
    prompt = f"Datos del tablero ({e}):\n{ctx}\n\nPregunta: {body.question.strip()}"
    try:
        decision = route_request(tenant, None, prompt, [ctx], task="recipe")
        gen = generate_with_fallback(decision.route, system, prompt, decision.context or [ctx])
        return {"answer": gen.response.content, "entity": e, "route": gen.route.value}
    except Exception as exc:  # pragma: no cover - depende del proveedor
        return {"answer": f"No se pudo generar la respuesta: {exc}", "entity": e, "route": ""}
