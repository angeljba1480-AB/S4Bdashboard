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
    return {
        "entity": e, "company": seed.COMPANY,
        "kpis": {
            "revenue": k["revenue"], "ebitda": k["ebitda"], "neta": k["neta"],
            "margen_bruto": k["margen_bruto"], "margen_ebitda": k["margen_ebitda"],
            "dso": k["dso"], "dpo": k["dpo"], "ccc": k["ccc"], "roe": k["roe"],
            "growth": k["growth"], "cash": k["cash"], "ar": k["ar"],
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
