"""/runbooks — biblioteca de runbooks (automatizaciones multi-paso) por segmento
(PyME/Enterprise) y sector. Instalar un runbook crea un *playbook del agente* que el
agente ejecuta a demanda (lecturas al momento; escrituras con aprobación)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AgentPlaybook, AuditEvent, Tenant, User
from ..runbooks import catalog

router = APIRouter(prefix="/runbooks", tags=["runbooks"])


def _out(rb: dict) -> dict:
    return {"id": rb["id"], "title": rb["title"], "description": rb["description"],
            "segment": rb.get("segment", "ambos"), "sector": rb["sector"],
            "area": rb.get("area", ""), "benefit": rb.get("benefit", ""),
            "icon": rb.get("icon", "workflow"), "steps": rb.get("steps", [])}


@router.get("/facets")
def facets(_: User = Depends(get_current_user)) -> dict:
    return catalog.facets()


@router.get("")
def list_runbooks(segment: str = "", sector: str = "", q: str = "",
                  _: User = Depends(get_current_user)) -> list[dict]:
    return [_out(rb) for rb in catalog.list_runbooks(segment.strip(), sector.strip(), q.strip())]


@router.post("/{rb_id}/install", status_code=201)
def install_runbook(rb_id: str, tenant: Tenant = Depends(get_current_tenant),
                    user: User = Depends(get_current_user),
                    session: Session = Depends(get_session)) -> dict:
    """Instala el runbook como un playbook del agente (re-ejecutable desde *Acciones*)."""
    rb = catalog.get_runbook(rb_id)
    if not rb:
        raise HTTPException(status_code=404, detail="Runbook no encontrado")
    # Evita duplicados por nombre para el mismo usuario.
    existing = session.exec(select(AgentPlaybook).where(
        AgentPlaybook.tenant_id == tenant.id, AgentPlaybook.user_id == user.id,
        AgentPlaybook.name == rb["title"])).first()
    if existing:
        return {"id": existing.id, "name": existing.name, "already_installed": True}
    p = AgentPlaybook(tenant_id=tenant.id, user_id=user.id, name=rb["title"],
                      instruction=catalog.build_instruction(rb), auto_approve=False)
    session.add(p)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="runbook", object_type="agent_playbook",
        object_id=p.id, risk_level="low", reason=f"runbook instalado: {rb['title']}"))
    session.commit(); session.refresh(p)
    return {"id": p.id, "name": p.name, "already_installed": False}
