"""/company — the company configuration ("onboarding") workflow.

An Admin Empresa fills in the business context once (identity, areas/org chart,
tech stack, tone). Everyone can read it so use cases pre-fill with the right
areas/responsibles and the AI personalizes every deliverable.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from ..auth import get_current_tenant, get_current_user, require_roles
from ..company_profile import get_or_create, to_dict
from ..db import get_session
from ..models import AuditEvent, Role, Tenant, User

router = APIRouter(prefix="/company", tags=["company"])


class Area(BaseModel):
    name: str = ""
    responsible: str = ""
    email: str = ""


class ProfileUpdate(BaseModel):
    industry: str = ""
    company_size: str = ""
    org_type: str = "privada"       # privada | gobierno
    gov_tramites: bool | None = None  # IP opta por trámites/licitaciones de gobierno
    description: str = ""
    audience: str = ""
    value_prop: str = ""
    goals: str = ""
    tone: str = ""
    website: str = ""
    areas: list[Area] = []
    tech_stack: list[str] = []
    completed: bool | None = None


@router.get("/profile")
def get_profile(
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    profile = get_or_create(session, tenant.id)
    return {**to_dict(profile), "company_name": tenant.brand_name or tenant.name}


@router.put("/profile")
def update_profile(
    body: ProfileUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    session: Session = Depends(get_session),
) -> dict:
    profile = get_or_create(session, tenant.id)
    profile.industry = body.industry.strip()
    profile.company_size = body.company_size.strip()
    profile.org_type = "gobierno" if body.org_type.strip().lower() == "gobierno" else "privada"
    if body.gov_tramites is not None:
        profile.gov_tramites = "1" if body.gov_tramites else ""
    profile.description = body.description.strip()
    profile.audience = body.audience.strip()
    profile.value_prop = body.value_prop.strip()
    profile.goals = body.goals.strip()
    profile.tone = body.tone.strip()
    profile.website = body.website.strip()
    profile.areas = json.dumps([
        {"name": a.name.strip(), "responsible": a.responsible.strip(), "email": a.email.strip()}
        for a in body.areas if a.name.strip()
    ])
    profile.tech_stack = json.dumps([t.strip() for t in body.tech_stack if t.strip()])
    if body.completed is not None:
        profile.completed = body.completed
    from datetime import datetime
    profile.updated_at = datetime.utcnow()
    session.add(profile)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="company_profile",
        object_type="company_profile", object_id=profile.id, risk_level="low",
        reason="configuración de empresa actualizada",
    ))
    session.commit()
    session.refresh(profile)
    return {**to_dict(profile), "company_name": tenant.brand_name or tenant.name}


class SupportSenderUpdate(BaseModel):
    account_id: str = ""    # OAuthToken.id del buzón de soporte ("" = usar cuenta del usuario)
    from_addr: str = ""     # alias "From" opcional
    from_name: str = ""     # nombre para mostrar


@router.get("/support-sender")
def get_support_sender(
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Remitente de soporte del tenant + buzones disponibles para elegir."""
    from ..integrations import token_store
    conns = [{"id": c.id, "provider": c.provider, "email": c.identifier}
             for c in token_store.list_tenant_connections(session, tenant.id)]
    return {
        "account_id": tenant.support_account_id or "",
        "from_addr": tenant.support_from or "",
        "from_name": tenant.support_from_name or "",
        "connections": conns,
    }


@router.put("/support-sender")
def update_support_sender(
    body: SupportSenderUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    session: Session = Depends(get_session),
) -> dict:
    """Fija el buzón desde el que salen los correos de las automatizaciones."""
    from datetime import datetime

    from ..integrations import token_store
    acc = body.account_id.strip()
    if acc:  # validar que el buzón exista y sea del tenant
        ids = {c.id for c in token_store.list_tenant_connections(session, tenant.id)}
        if acc not in ids:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail="El buzón seleccionado no está conectado en este tenant.")
    tenant.support_account_id = acc
    tenant.support_from = body.from_addr.strip()
    tenant.support_from_name = body.from_name.strip()
    session.add(tenant)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="company_config",
        object_type="support_sender", object_id=acc or "(usuario)", risk_level="low",
        reason="remitente de soporte actualizado",
    ))
    session.commit()
    session.refresh(tenant)
    return {"account_id": tenant.support_account_id, "from_addr": tenant.support_from,
            "from_name": tenant.support_from_name}
