"""Admin endpoints: tenant settings, users and configured model routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, require_roles
from ..config import settings
from ..db import get_session
from ..models import ModelRoute, Role, Tenant, User

router = APIRouter(prefix="/admin", tags=["admin"])


class TenantSettings(BaseModel):
    allows_external: bool
    allows_vpc: bool
    retention_days: int


@router.get("/users")
def list_users(
    _: User = Depends(require_roles(Role.ADMIN, Role.SECURITY)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[dict]:
    users = session.exec(select(User).where(User.tenant_id == tenant.id)).all()
    return [{"id": u.id, "email": u.email, "name": u.name, "role": u.role.value,
             "mfa_enabled": u.mfa_enabled, "status": u.status} for u in users]


@router.get("/routes")
def model_routes(_: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS))) -> list[dict]:
    """Which model routes are enabled (real provider vs mock fallback)."""
    return [
        {"route": ModelRoute.LOCAL.value, "enabled": settings.local_enabled,
         "model": settings.local_model, "mode": "real" if settings.local_enabled else "mock"},
        {"route": ModelRoute.VPC.value, "enabled": settings.vpc_enabled,
         "model": settings.vpc_model, "mode": "real" if settings.vpc_enabled else "mock"},
        {"route": ModelRoute.OPEN.value, "enabled": settings.open_enabled,
         "model": settings.open_model, "mode": "real" if settings.open_enabled else "mock"},
        {"route": ModelRoute.PREMIUM.value, "enabled": settings.premium_enabled,
         "model": settings.premium_model, "mode": "real" if settings.premium_enabled else "mock"},
    ]


@router.put("/tenant")
def update_tenant(
    body: TenantSettings,
    _: User = Depends(require_roles(Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    tenant.allows_external = body.allows_external
    tenant.allows_vpc = body.allows_vpc
    tenant.retention_days = body.retention_days
    session.add(tenant)
    session.commit()
    return {"ok": True}
