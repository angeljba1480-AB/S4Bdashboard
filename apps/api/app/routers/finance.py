"""/finance — Tablero Financiero servido por endpoint + preguntar (RAG) + carga self-service.

La data se resuelve por tenant: lo que el cliente sube en la app (cifrado) → dataset
inyectado por entorno → demo. En Paso 1 se sustituye por el conector a la fuente; el
contrato del endpoint no cambia.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session

from ..auth import get_current_tenant, get_current_user, require_roles
from ..db import get_session
from ..finance import seed
from ..models import Role, Tenant, User

router = APIRouter(prefix="/finance", tags=["finance"])

_ENTITIES = {"S4B", "S4C", "CONS"}


def _entity(e: str) -> str:
    e = (e or "CONS").upper()
    return e if e in _ENTITIES else "CONS"


@router.get("/overview")
def overview(entity: str = "CONS", tenant: Tenant = Depends(get_current_tenant),
             _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    ds = seed.for_tenant(session, tenant)
    e = _entity(entity)
    k = ds.entity_kpis(e)
    segs = sorted(ds.segments.get(e, []), key=lambda s: -s["revenue"])
    clientes = ds.top_clients if e == "CONS" else [c for c in ds.top_clients if c["entity"] == e]
    rule40 = k["growth"] + k["margen_ebitda"]
    fy = ds.fy
    return {
        "entity": e, "company": ds.company,
        "kpis": {
            "revenue": k["revenue"], "costos": k["costos"], "ub": k["ub"],
            "ebitda": k["ebitda"], "neta": k["neta"],
            "margen_bruto": k["margen_bruto"], "margen_ebitda": k["margen_ebitda"],
            "margen_neto": k["margen_neto"],
            "dso": k["dso"], "dpo": k["dpo"], "ccc": k["ccc"], "roe": k["roe"],
            "endeudamiento": k["endeudamiento"], "growth": k["growth"],
            "activo": k["activo"], "pasivo": k["pasivo"], "capital": k["capital"],
            "cash": k["cash"], "ar": k["ar"], "ap": k["ap"], "wc": k["wc"],
            "headcount": ds.headcount.get(e, ds.headcount.get("CONS", 0)),
            "rule40": rule40,
            "headcount_s4b": ds.headcount.get("S4B", 0), "headcount_s4c": ds.headcount.get("S4C", 0),
            "revenue_s4b": fy.get("S4B", {}).get("revenue", 0), "revenue_s4c": fy.get("S4C", {}).get("revenue", 0),
            "ebitda_s4b": fy.get("S4B", {}).get("ebitda", 0), "ebitda_s4c": fy.get("S4C", {}).get("ebitda", 0),
        },
        "summary": {
            "caja": k["cash"], "cartera": k["ar"], "capital_trabajo": k["wc"], "rule40": rule40,
            "proyectos_riesgo": 6, "top_clientes": len(clientes), "lineas_servicio": len(segs),
            "linea_principal": segs[0]["name"] if segs else "",
            "alertas_criticas": len([a for a in ds.alerts if a["level"] == "high"]),
        },
        "monthly": ds.monthly.get(e, []),
        "segments": segs,
        "gob_ip": ds.gob_ip,
        "benchmarks": ds.benchmarks,
        "alerts": ds.alerts,
        "source": ("cargado por el cliente" if ds.origin().startswith("tenant")
                   else "demo (sin datos cargados)" if ds.is_demo()
                   else "inyectado (entorno)"),
        "is_demo": ds.is_demo(),
    }


@router.get("/clients")
def clients(entity: str = "CONS", tenant: Tenant = Depends(get_current_tenant),
            _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[dict]:
    ds = seed.for_tenant(session, tenant)
    e = _entity(entity)
    rows = ds.top_clients if e == "CONS" else [c for c in ds.top_clients if c["entity"] == e]
    return sorted(rows, key=lambda c: -c["revenue"])


@router.get("/projects")
def projects(tenant: Tenant = Depends(get_current_tenant),
             _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Portafolio de proyectos: totales, tendencia, mezcla de costo, plan vs real y detalle."""
    return seed.for_tenant(session, tenant).projects()


@router.get("/operations")
def operations(tenant: Tenant = Depends(get_current_tenant),
               _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Utilización, costo por hora, evaluación de clientes y comparativo de costos."""
    ds = seed.for_tenant(session, tenant)
    return {
        "utilization": ds.utilization(),
        "cost_per_hour": ds.cost_per_hour(),
        "client_scoring": ds.client_scoring(),
        "cost_comparison": ds.cost_comparison(),
        "is_demo": ds.is_demo(),
    }


# ---------------------------------------------------------------------------
# Carga self-service del dataset (JSON o Excel/zip) — Paso 2 dentro de MaestroAI
# ---------------------------------------------------------------------------
@router.get("/dataset/status")
def dataset_status(tenant: Tenant = Depends(get_current_tenant),
                   _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    from ..finance import store
    st = store.status(session, tenant)
    st["origin"] = seed.for_tenant(session, tenant).origin() or "demo"
    return st


@router.post("/dataset", status_code=201)
async def upload_dataset(files: list[UploadFile] = File(...),
                         tenant: Tenant = Depends(get_current_tenant),
                         user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                         session: Session = Depends(get_session)) -> dict:
    """Sube el dataset curado (.json) o los Excel/zip; se transforma y guarda cifrado."""
    from ..finance import store
    from ..finance.ingest_excel import build_dataset_from_files
    payload: list[tuple[str, bytes]] = []
    for f in files:
        raw = await f.read()
        if raw:
            payload.append((f.filename or "archivo", raw))
    if not payload:
        raise HTTPException(status_code=422, detail="No se recibió ningún archivo.")
    try:
        data = build_dataset_from_files(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    has_json = any(n.lower().endswith(".json") for n, _ in payload)
    has_xlsx = any(n.lower().endswith((".xlsx", ".zip")) for n, _ in payload)
    src = "excel+json" if has_json and has_xlsx else "json" if has_json else "excel"
    fname = ", ".join(n for n, _ in payload)
    store.save_dataset(session, tenant, data, source=src, filename=fname, user_id=user.id)
    return {"ok": True, "source": src, "filename": fname,
            "partial_entities": bool(data.get("partial_entities")),
            "proyectos": data.get("projects", {}).get("totals", {}).get("proyectos", 0)}


@router.delete("/dataset")
def delete_dataset(tenant: Tenant = Depends(get_current_tenant),
                   _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                   session: Session = Depends(get_session)) -> dict:
    """Borra el dataset del tenant y vuelve al inyectado por entorno / demo."""
    from ..finance import store
    return {"ok": store.delete_dataset(session, tenant)}


class AskIn(BaseModel):
    question: str
    entity: str = "CONS"


def _context(ds: "seed.Dataset", entity: str) -> str:
    """Texto compacto con las cifras para fundamentar la respuesta (anti-alucinación)."""
    k = ds.entity_kpis(entity)
    m = lambda n: f"${n/1_000_000:.1f}M"
    lines = [f"Entidad: {entity} ({ds.company.get('legalName', '')}), periodo {ds.company.get('period', '')}.",
             f"Ingresos {m(k['revenue'])}, EBITDA {m(k['ebitda'])} ({k['margen_ebitda']*100:.1f}%), "
             f"Utilidad neta {m(k['neta'])}, Margen bruto {k['margen_bruto']*100:.1f}%.",
             f"Crecimiento YoY {k['growth']*100:.1f}%. DSO {k['dso']}d, DPO {k['dpo']}d, CCC {k['ccc']}d, ROE {k['roe']*100:.1f}%.",
             f"Caja {m(k['cash'])}, Cuentas por cobrar {m(k['ar'])}.",
             "Líneas de servicio: " + "; ".join(f"{s['name']} {m(s['revenue'])} (margen {s['margin']*100:.0f}%)"
                                                 for s in ds.segments.get(entity, []))]
    gi = ds.gob_ip
    yr = max(gi) if gi else None
    if yr:
        lines.append(f"Gobierno vs IP {yr}: Gobierno {m(gi[yr]['gob'])}, IP {m(gi[yr]['ip'])}.")
    if ds.alerts:
        lines.append("Alertas: " + " | ".join(a["msg"] for a in ds.alerts))
    pr = ds.projects()
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
                f"{k2.replace('_', '/')} {m(v)}" for k2, v in cm.items() if v))
        top = pr.get("detail", [])[:8]
        if top:
            lines.append("Proyectos principales: " + "; ".join(
                f"{p['cliente']} {m(p['venta'])} (margen {p['pct_margen']*100:.0f}%, desv EBITDA {m(p.get('desviacion', 0))})"
                for p in top))
    u = ds.utilization()
    if u.get("utilizacion"):
        lines.append(
            f"Utilización {u.get('year', '')}: {u['utilizacion']*100:.0f}% "
            f"({u.get('horas_reales', 0):,} horas reales de {u.get('horas_capacidad', 0):,} de capacidad, "
            f"{u.get('empleados', 0)} personas).")
    sc = ds.client_scoring()
    if sc.get("clients"):
        top_sc = sorted(sc["clients"], key=lambda c: -c.get("score", 0))[:5]
        lines.append("Evaluación de clientes (score, tier): " + "; ".join(
            f"{c['name']} {c.get('score')} {c.get('tier', '')}" for c in top_sc))
    cc = ds.cost_comparison()
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
        _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Pregunta sobre las cifras del tablero (RAG sobre los datos del tenant)."""
    from ..ai.resilience import generate_with_fallback
    from ..ai.router import route_request
    ds = seed.for_tenant(session, tenant)
    e = _entity(body.entity)
    ctx = _context(ds, e)
    system = ("Eres analista financiero. Responde en español, claro y conciso, USANDO SOLO las "
              "cifras provistas; si no está en los datos, dilo. No inventes números.")
    prompt = f"Datos del tablero ({e}):\n{ctx}\n\nPregunta: {body.question.strip()}"
    try:
        decision = route_request(tenant, None, prompt, [ctx], task="recipe")
        gen = generate_with_fallback(decision.route, system, prompt, decision.context or [ctx])
        return {"answer": gen.response.content, "entity": e, "route": gen.route.value}
    except Exception as exc:  # pragma: no cover - depende del proveedor
        return {"answer": f"No se pudo generar la respuesta: {exc}", "entity": e, "route": ""}
