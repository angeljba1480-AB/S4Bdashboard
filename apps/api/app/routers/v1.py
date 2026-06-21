"""Public integration API (/v1) — system-to-system, authenticated by API key.

Lets external systems (CRM/ERP/delivery/etc.) call MaestroAI: run a use case,
query the trámites KB, or push an event that triggers automations.
Auth: header X-API-Key.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ..auth import get_tenant_by_api_key
from ..db import get_session
from ..models import AuditEvent, Tenant

router = APIRouter(prefix="/v1", tags=["public-api"])


class RunCaseIn(BaseModel):
    inputs: dict = {}


class EventIn(BaseModel):
    event: str
    payload: dict = {}


@router.get("/ping")
def ping(tenant: Tenant = Depends(get_tenant_by_api_key)) -> dict:
    return {"ok": True, "tenant": tenant.name, "country": tenant.country}


@router.post("/cases/{recipe_id}/run")
def run_case(
    recipe_id: str,
    body: RunCaseIn,
    tenant: Tenant = Depends(get_tenant_by_api_key),
    session: Session = Depends(get_session),
) -> dict:
    """Run a use case from an external system (returns the AI-generated draft)."""
    from ..recipes.catalog import prefill, validate_inputs
    from .recipes import _resolve
    recipe = _resolve(session, tenant.id, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Caso de uso no encontrado")
    missing = validate_inputs(recipe, body.inputs)
    if missing:
        raise HTTPException(status_code=422, detail=f"Faltan datos: {', '.join(missing)}")
    draft = prefill(recipe, session, tenant, body.inputs)
    session.add(AuditEvent(
        tenant_id=tenant.id, event_type="api_case", object_type="recipe", object_id=recipe_id,
        risk_level="low", reason=f"caso ejecutado vía API: {recipe['name']}"))
    session.commit()
    return {"recipe": recipe["name"], "draft": draft}


@router.get("/tramites")
def tramites(
    q: str | None = None, region: str | None = None, municipio: str | None = None,
    tenant: Tenant = Depends(get_tenant_by_api_key),
    session: Session = Depends(get_session),
) -> list[dict]:
    from .tramites import layered_search
    return layered_search(session, tenant, q, region, municipio, tenant.country)


@router.post("/events")
def ingest_event(
    body: EventIn,
    tenant: Tenant = Depends(get_tenant_by_api_key),
    session: Session = Depends(get_session),
) -> dict:
    """Ingest an external event (e.g. from a CRM) and trigger matching automations."""
    from .automations import dispatch_event
    ran = dispatch_event(session, tenant, body.event, body.payload)
    return {"event": body.event, "automations_triggered": ran}
