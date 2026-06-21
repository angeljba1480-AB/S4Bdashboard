"""Admin endpoints: tenant settings, users and configured model routes."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, require_roles
from ..config import settings
from ..db import get_session
from ..integrations.n8n import resolve_n8n
from ..integrations.n8n_provision import ensure_tenant_workflows, is_available as is_provision_available
from ..models import ModelRoute, Role, Tenant, User
from ..security.crypto import encrypt

router = APIRouter(prefix="/admin", tags=["admin"])


class TenantSettings(BaseModel):
    allows_external: bool
    allows_vpc: bool
    retention_days: int


class N8nSettings(BaseModel):
    webhook_base_url: str = ""
    api_key: str = ""          # write-only; stored encrypted, never returned
    auth_header: str = ""


class BrandSettings(BaseModel):
    brand_name: str = ""
    brand_logo_url: str = ""
    brand_color: str = ""
    brand_tagline: str = ""


@router.get("/branding")
def get_branding(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    return {"brand_name": tenant.brand_name, "brand_logo_url": tenant.brand_logo_url,
            "brand_color": tenant.brand_color, "brand_tagline": tenant.brand_tagline,
            "tenant_name": tenant.name}


@router.put("/branding")
def update_branding(
    body: BrandSettings,
    _: User = Depends(require_roles(Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """White-label the portal for this tenant (name, logo, color, tagline)."""
    color = body.brand_color.strip()
    if color and not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise HTTPException(status_code=422, detail="Color inválido (usa formato #RRGGBB)")
    tenant.brand_name = body.brand_name.strip()
    tenant.brand_logo_url = body.brand_logo_url.strip()
    tenant.brand_color = color
    tenant.brand_tagline = body.brand_tagline.strip()
    session.add(tenant)
    session.commit()
    return {"brand_name": tenant.brand_name, "brand_logo_url": tenant.brand_logo_url,
            "brand_color": tenant.brand_color, "brand_tagline": tenant.brand_tagline}


@router.get("/users")
def list_users(
    _: User = Depends(require_roles(Role.ADMIN, Role.SECURITY)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[dict]:
    users = session.exec(select(User).where(User.tenant_id == tenant.id)).all()
    return [{"id": u.id, "email": u.email, "name": u.name, "role": u.role.value,
             "mfa_enabled": u.mfa_enabled, "status": u.status} for u in users]


class NewUser(BaseModel):
    email: str
    name: str
    role: str = "user"
    password: str = "demo1234"


def _seats_used(session: Session, tenant_id: str) -> int:
    return len(session.exec(
        select(User).where(User.tenant_id == tenant_id, User.status == "active")
    ).all())


@router.post("/users", status_code=201)
def create_user(
    body: NewUser,
    _: User = Depends(require_roles(Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Add a user — enforces the tenant's licensed seats (annual prepaid)."""
    from ..auth import hash_password

    if tenant.subscription_status == "expired":
        raise HTTPException(status_code=402, detail="Suscripción vencida: renueva para agregar usuarios")
    if _seats_used(session, tenant.id) >= tenant.seats_licensed:
        raise HTTPException(status_code=402, detail={
            "message": "No hay asientos disponibles. Amplía tu plan.",
            "seats_licensed": tenant.seats_licensed})
    if session.exec(select(User).where(User.email == body.email)).first():
        raise HTTPException(status_code=409, detail="Ese correo ya existe")
    try:
        role = Role(body.role)
    except ValueError:
        raise HTTPException(status_code=422, detail="Rol inválido")
    u = User(tenant_id=tenant.id, email=body.email.strip(), name=body.name.strip(),
             role=role, password_hash=hash_password(body.password))
    session.add(u)
    session.commit()
    session.refresh(u)
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role.value}


@router.get("/billing")
def get_billing(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    from .apps import DEPLOY_PRICE_MXN

    used = _seats_used(session, tenant.id)
    return {
        "plan": tenant.plan,
        "subscription_status": tenant.subscription_status,
        "renews_at": tenant.subscription_renews_at or None,
        "setup_fee_paid": tenant.setup_fee_paid,
        "annual_fee_mxn": tenant.annual_fee_mxn,
        "seats_licensed": tenant.seats_licensed,
        "seats_used": used,
        "seats_available": max(0, tenant.seats_licensed - used),
        "prod_deploy_price_mxn": DEPLOY_PRICE_MXN,
    }


class BillingUpdate(BaseModel):
    seats_licensed: int | None = None
    annual_fee_mxn: int | None = None
    subscription_status: str | None = None
    subscription_renews_at: str | None = None
    setup_fee_paid: bool | None = None
    plan: str | None = None


@router.put("/billing")
def update_billing(
    body: BillingUpdate,
    _: User = Depends(require_roles(Role.SUPER_ADMIN, Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Set the tenant's subscription (seats, annual fee, status). In production a
    billing provider/webhook drives this; here it's set explicitly."""
    if body.seats_licensed is not None:
        if body.seats_licensed < _seats_used(session, tenant.id):
            raise HTTPException(status_code=422, detail="No puedes licenciar menos asientos de los usados")
        tenant.seats_licensed = body.seats_licensed
    if body.annual_fee_mxn is not None:
        tenant.annual_fee_mxn = body.annual_fee_mxn
    if body.subscription_status is not None:
        tenant.subscription_status = body.subscription_status
    if body.subscription_renews_at is not None:
        tenant.subscription_renews_at = body.subscription_renews_at
    if body.setup_fee_paid is not None:
        tenant.setup_fee_paid = body.setup_fee_paid
    if body.plan is not None:
        tenant.plan = body.plan
    session.add(tenant)
    session.commit()
    return {"ok": True}


@router.get("/routes")
def model_routes(_: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS))) -> list[dict]:
    """Which model routes are enabled (real provider vs mock fallback)."""
    return [
        {"route": ModelRoute.LOCAL.value, "provider": "Self-hosted (Ollama)", "enabled": settings.local_enabled,
         "model": settings.local_model, "mode": "real" if settings.local_enabled else "mock"},
        {"route": ModelRoute.VPC.value, "provider": "VPC (vLLM/TGI)", "enabled": settings.vpc_enabled,
         "model": settings.vpc_model, "mode": "real" if settings.vpc_enabled else "mock"},
        {"route": ModelRoute.OPEN.value, "provider": settings.open_provider_name, "enabled": settings.open_enabled,
         "model": settings.open_model, "mode": "real" if settings.open_enabled else "mock"},
        {"route": ModelRoute.PREMIUM.value, "provider": "Premium externo", "enabled": settings.premium_enabled,
         "model": settings.premium_model, "mode": "real" if settings.premium_enabled else "mock"},
    ]


@router.get("/security")
def security_status(
    _: User = Depends(require_roles(Role.ADMIN, Role.SECURITY, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    """Surface the enterprise-hardening posture (Fase 5)."""
    return {
        "encryption_at_rest": {"enabled": settings.encryption_enabled, "algo": "AES-256-GCM",
                               "kms_key_version": settings.kms_key_version},
        "vector_store": settings.vector_store,
        "sso": {"enabled": settings.sso_enabled, "issuer": settings.oidc_issuer or None},
        "fallback_order": settings.fallback_routes,
        "workflows": _workflows_status(tenant),
    }


def _workflows_status(tenant: Tenant) -> dict:
    cfg = resolve_n8n(tenant)
    return {"engine": "n8n" if cfg.enabled else "simulado", "source": cfg.source,
            "base_url": cfg.base_url or None}


@router.get("/n8n")
def get_n8n(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    """n8n status. Managed is the zero-config default; BYO is advanced/optional."""
    cfg = resolve_n8n(tenant)
    return {
        "tenant_override": bool(tenant.n8n_webhook_base_url),
        "webhook_base_url": tenant.n8n_webhook_base_url or None,
        "auth_header": tenant.n8n_auth_header or settings.n8n_auth_header,
        "has_api_key": bool(tenant.n8n_api_key_enc),
        "effective_source": cfg.source,
        "managed_available": bool(settings.n8n_enabled and settings.n8n_webhook_base_url),
        "auto_provision": settings.n8n_auto_provision and is_provision_available(),
        "provisioned": tenant.n8n_provisioned,
    }


@router.post("/n8n/provision")
def provision_n8n(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Manually (re)provision this tenant's managed workflows. Usually automatic."""
    from .workflows import CATALOG

    result = ensure_tenant_workflows(tenant, [w["id"] for w in CATALOG])
    if result.get("provisioned"):
        tenant.n8n_provisioned = True
        session.add(tenant)
        session.commit()
    return result


@router.put("/n8n")
def update_n8n(
    body: N8nSettings,
    _: User = Depends(require_roles(Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Set/clear this tenant's own n8n. Empty base_url reverts to global n8n."""
    tenant.n8n_webhook_base_url = body.webhook_base_url.strip()
    tenant.n8n_auth_header = body.auth_header.strip()
    if body.api_key:
        tenant.n8n_api_key_enc = encrypt(body.api_key, tenant.id)
    elif not tenant.n8n_webhook_base_url:
        tenant.n8n_api_key_enc = ""  # cleared override
    session.add(tenant)
    session.commit()
    return _workflows_status(tenant)


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
