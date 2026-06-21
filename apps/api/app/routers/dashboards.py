"""/dashboards — build company dashboards (KPIs/charts/tables) bound to live
metrics or manual data, optionally linked to a workflow automation.

Describe what you want to measure -> the platform suggests a widget spec (from a
catalog of available metrics) -> save -> /data resolves real values for render.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AuditEvent, Dashboard, Tenant, User
from .usage import compute_operations

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

# Available platform widgets the builder can wire to real data.
WIDGET_CATALOG: list[dict] = [
    {"key": "cases.total", "type": "kpi", "title": "Casos totales", "tags": ["caso", "proceso", "operación"]},
    {"key": "cases.completed", "type": "kpi", "title": "Casos completados", "tags": ["caso", "completado"]},
    {"key": "searches", "type": "kpi", "title": "Búsquedas / consultas", "tags": ["búsqueda", "consulta", "chat"]},
    {"key": "tokens.total", "type": "kpi", "title": "Tokens usados", "tags": ["token", "consumo", "ia"]},
    {"key": "cost.total", "type": "kpi", "title": "Costo estimado (USD)", "tags": ["costo", "gasto", "presupuesto"]},
    {"key": "apps.deployed", "type": "kpi", "title": "Apps en producción", "tags": ["app", "producción"]},
    {"key": "tokens.by_source", "type": "bar", "title": "Tokens por fuente", "tags": ["token", "consumo"]},
    {"key": "cases.by_recipe", "type": "bar", "title": "Casos por tipo", "tags": ["caso", "tipo", "proceso"]},
    {"key": "cost.by_route", "type": "bar", "title": "Costo por ruta", "tags": ["costo", "ruta", "gasto"]},
    {"key": "recent_cases", "type": "table", "title": "Casos recientes", "tags": ["caso", "reciente", "historial"]},
]


class DashboardIn(BaseModel):
    name: str
    description: str = ""
    spec: list[dict] | None = None
    workflow_id: str = ""


class SuggestIn(BaseModel):
    description: str


def suggest_spec(description: str) -> list[dict]:
    """Pick relevant widgets for a natural-language description (keyword match).

    Robust offline; an LLM can refine later. Always returns a usable dashboard.
    """
    d = (description or "").lower()
    chosen = [w for w in WIDGET_CATALOG if any(t in d for t in w["tags"])]
    if not chosen:  # sensible default: a balanced operations board
        keys = {"cases.total", "searches", "tokens.total", "cost.total", "cases.by_recipe", "recent_cases"}
        chosen = [w for w in WIDGET_CATALOG if w["key"] in keys]
    # de-dup, cap and assign ids
    seen, spec = set(), []
    for i, w in enumerate(chosen):
        if w["key"] in seen:
            continue
        seen.add(w["key"])
        spec.append({"id": f"w{i}", "type": w["type"], "title": w["title"],
                     "source": "platform", "key": w["key"]})
    return spec[:8]


def _dig(data: dict, path: str):
    cur = data
    for part in path.split("."):
        cur = (cur or {}).get(part) if isinstance(cur, dict) else None
    return cur


def resolve_widget(widget: dict, ops: dict) -> dict:
    """Attach live data to a widget for rendering."""
    out = {**widget}
    if widget.get("source") == "manual":
        return out  # data already embedded in config
    key = widget.get("key", "")
    val = _dig(ops, key)
    if widget["type"] == "kpi":
        out["value"] = val if val is not None else 0
    elif widget["type"] == "bar":
        series = val if isinstance(val, dict) else {}
        out["series"] = [{"name": k, "value": v} for k, v in series.items()]
    elif widget["type"] == "table":
        out["rows"] = val if isinstance(val, list) else []
    return out


def _out(d: Dashboard) -> dict:
    return {"id": d.id, "name": d.name, "description": d.description,
            "spec": json.loads(d.spec or "[]"), "workflow_id": d.workflow_id or None}


def _load(session, tenant, user, did) -> Dashboard:
    d = session.get(Dashboard, did)
    if not d or d.tenant_id != tenant.id or d.user_id != user.id:
        raise HTTPException(status_code=404, detail="Tablero no encontrado")
    return d


@router.get("/catalog")
def catalog(_: User = Depends(get_current_user)) -> list[dict]:
    return [{"key": w["key"], "type": w["type"], "title": w["title"]} for w in WIDGET_CATALOG]


@router.post("/suggest")
def suggest(body: SuggestIn, _: User = Depends(get_current_user)) -> dict:
    return {"spec": suggest_spec(body.description)}


@router.get("")
def list_dashboards(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(
        select(Dashboard).where(Dashboard.tenant_id == tenant.id, Dashboard.user_id == user.id)
        .order_by(Dashboard.created_at.desc())
    ).all()
    return [_out(d) for d in rows]


@router.post("", status_code=201)
def create_dashboard(
    body: DashboardIn,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    spec = body.spec if body.spec is not None else suggest_spec(body.description)
    d = Dashboard(tenant_id=tenant.id, user_id=user.id, name=body.name.strip(),
                  description=body.description.strip(), spec=json.dumps(spec),
                  workflow_id=body.workflow_id.strip())
    session.add(d)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="dashboard",
        object_type="dashboard", object_id=d.id, risk_level="low",
        reason=f"tablero creado: {d.name}",
    ))
    session.commit()
    session.refresh(d)
    return _out(d)


@router.put("/{dashboard_id}")
def update_dashboard(
    dashboard_id: str,
    body: DashboardIn,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    d = _load(session, tenant, user, dashboard_id)
    d.name = body.name.strip() or d.name
    d.description = body.description.strip()
    if body.spec is not None:
        d.spec = json.dumps(body.spec)
    d.workflow_id = body.workflow_id.strip()
    d.updated_at = __import__("datetime").datetime.utcnow()
    session.add(d)
    session.commit()
    session.refresh(d)
    return _out(d)


@router.delete("/{dashboard_id}")
def delete_dashboard(
    dashboard_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    d = _load(session, tenant, user, dashboard_id)
    session.delete(d)
    session.commit()
    return {"ok": True}


@router.get("/{dashboard_id}/data")
def dashboard_data(
    dashboard_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    d = _load(session, tenant, user, dashboard_id)
    ops = compute_operations(session, tenant)
    widgets = [resolve_widget(w, ops) for w in json.loads(d.spec or "[]")]
    return {"id": d.id, "name": d.name, "widgets": widgets}
