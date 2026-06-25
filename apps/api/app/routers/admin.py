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
    country: str | None = None


@router.get("/branding")
def get_branding(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
) -> dict:
    return {"brand_name": tenant.brand_name, "brand_logo_url": tenant.brand_logo_url,
            "brand_color": tenant.brand_color, "brand_tagline": tenant.brand_tagline,
            "tenant_name": tenant.name, "country": tenant.country}


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
    if body.country:
        from ..regional.countries import get_country
        tenant.country = get_country(body.country)["code"]
    session.add(tenant)
    session.commit()
    return {"brand_name": tenant.brand_name, "brand_logo_url": tenant.brand_logo_url,
            "brand_color": tenant.brand_color, "brand_tagline": tenant.brand_tagline}


def _user_out(u: User) -> dict:
    return {"id": u.id, "email": u.email, "name": u.name, "role": u.role.value,
            "area": u.area or "", "license": u.license or "basic",
            "mfa_enabled": u.mfa_enabled, "status": u.status}


@router.get("/users")
def list_users(
    _: User = Depends(require_roles(Role.ADMIN, Role.SECURITY)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[dict]:
    users = session.exec(select(User).where(User.tenant_id == tenant.id)).all()
    return [_user_out(u) for u in users]


class NewUser(BaseModel):
    email: str
    name: str
    role: str = "user"
    area: str = ""
    license: str = "basic"
    password: str = "demo1234"


class UpdateUser(BaseModel):
    name: str | None = None
    role: str | None = None
    area: str | None = None
    license: str | None = None
    status: str | None = None


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
    if role == Role.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="El super admin no se crea desde aquí")
    u = User(tenant_id=tenant.id, email=body.email.strip(), name=body.name.strip(),
             role=role, area=body.area.strip(), license=(body.license or "basic").strip(),
             password_hash=hash_password(body.password))
    session.add(u)
    session.commit()
    session.refresh(u)
    return _user_out(u)


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    body: UpdateUser,
    actor: User = Depends(require_roles(Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Edit a user's role, area, license or status (hierarchical permissions)."""
    u = session.get(User, user_id)
    if not u or u.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if body.role is not None:
        try:
            new_role = Role(body.role)
        except ValueError:
            raise HTTPException(status_code=422, detail="Rol inválido")
        # Only a super admin can grant or revoke the super admin role.
        if (new_role == Role.SUPER_ADMIN or u.role == Role.SUPER_ADMIN) and actor.role != Role.SUPER_ADMIN:
            raise HTTPException(status_code=403, detail="Solo un super admin puede gestionar el rol super admin")
        u.role = new_role
    if body.name is not None:
        u.name = body.name.strip()
    if body.area is not None:
        u.area = body.area.strip()
    if body.license is not None:
        u.license = body.license.strip() or "basic"
    if body.status is not None:
        u.status = body.status.strip()
    session.add(u)
    session.commit()
    session.refresh(u)
    return _user_out(u)


@router.get("/tenants")
def list_tenants(
    _: User = Depends(require_roles(Role.SUPER_ADMIN)),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Cross-tenant overview — only the super admin sees every organization."""
    from ..models import Document

    out = []
    for t in session.exec(select(Tenant)).all():
        users = session.exec(select(User).where(User.tenant_id == t.id)).all()
        docs = len(session.exec(select(Document).where(Document.tenant_id == t.id)).all())
        out.append({
            "id": t.id, "name": t.name, "plan": t.plan,
            "subscription_status": t.subscription_status,
            "country": t.country, "seats_licensed": t.seats_licensed,
            "users": len(users), "documents": docs,
        })
    return out


@router.get("/plans")
def list_plans(_: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS, Role.SECURITY))) -> dict:
    """Recommended licensing scheme + indicative pricing (industry-aligned, MXN)."""
    from ..billing.plans import CURRENCY, PLANS
    return {"currency": CURRENCY, "plans": PLANS}


@router.get("/plans/estimate")
def estimate_plan(
    plan: str, seats: int = 1,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
) -> dict:
    from ..billing.plans import estimate
    out = estimate(plan, seats)
    if not out:
        raise HTTPException(status_code=404, detail="Plan sin precio público (cotización a la medida)")
    return out


class ApiKeyIn(BaseModel):
    name: str = "Integración"


@router.get("/api-keys")
def list_api_keys(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[dict]:
    from ..models import ApiKey
    rows = session.exec(select(ApiKey).where(ApiKey.tenant_id == tenant.id)).all()
    return [{"id": k.id, "name": k.name, "prefix": k.key_prefix, "status": k.status,
             "created_at": k.created_at.isoformat()} for k in rows]


@router.post("/api-keys", status_code=201)
def create_api_key(
    body: ApiKeyIn,
    _: User = Depends(require_roles(Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Create an API key for the public /v1 integration API. Full key shown once."""
    from ..auth import generate_api_key
    from ..models import ApiKey
    full, prefix, khash = generate_api_key()
    row = ApiKey(tenant_id=tenant.id, name=body.name.strip() or "Integración",
                 key_prefix=prefix, key_hash=khash, status="active")
    session.add(row)
    session.commit()
    session.refresh(row)
    return {"id": row.id, "name": row.name, "api_key": full,
            "note": "Guarda esta llave ahora; no se vuelve a mostrar."}


@router.post("/api-keys/{key_id}/revoke")
def revoke_api_key(
    key_id: str,
    _: User = Depends(require_roles(Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    from ..models import ApiKey
    k = session.get(ApiKey, key_id)
    if not k or k.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="API key no encontrada")
    k.status = "revoked"
    session.add(k)
    session.commit()
    return {"id": k.id, "status": k.status}


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


class ProviderIn(BaseModel):
    enabled: bool = False
    base_url: str = ""
    model: str = ""
    api_key: str = ""          # write-only; stored encrypted, never returned


_EXTERNAL_ROUTES = ("premium", "open")


@router.get("/providers")
def list_providers(
    _: User = Depends(require_roles(Role.SUPER_ADMIN)),
    session: Session = Depends(get_session),
) -> list[dict]:
    """External model providers (GPT/Claude/Llama…) configurable from the UI."""
    from ..models import ProviderSetting

    rows = {r.route: r for r in session.exec(select(ProviderSetting)).all()}
    out = []
    for route in _EXTERNAL_ROUTES:
        r = rows.get(route)
        out.append({
            "route": route,
            "enabled": bool(r and r.enabled),
            "base_url": (r.base_url if r else ""),
            "model": (r.model if r else ""),
            "has_key": bool(r and r.api_key_enc),
        })
    return out


@router.put("/providers/{route}")
def update_provider(
    route: str,
    body: ProviderIn,
    _: User = Depends(require_roles(Role.SUPER_ADMIN)),
    session: Session = Depends(get_session),
) -> dict:
    """Set an external provider's endpoint/model/key. PII is redacted before any
    external call (privacy router), so keys here only enable that egress."""
    from ..ai.adapters import load_overrides
    from ..models import ProviderSetting

    if route not in _EXTERNAL_ROUTES:
        raise HTTPException(status_code=400, detail="Ruta externa inválida (usa premium u open)")
    row = session.exec(select(ProviderSetting).where(ProviderSetting.route == route)).first()
    if not row:
        row = ProviderSetting(route=route)
    row.enabled = body.enabled
    row.base_url = body.base_url.strip()
    row.model = body.model.strip()
    if body.api_key:
        row.api_key_enc = encrypt(body.api_key, settings.secret_key)
    elif not body.enabled and not body.base_url:
        row.api_key_enc = ""
    session.add(row)
    session.commit()
    load_overrides(session)   # refresh runtime cache immediately
    return {"route": route, "enabled": row.enabled, "has_key": bool(row.api_key_enc)}


class EfficiencyIn(BaseModel):
    condense_enabled: bool | None = None
    condense_threshold_chars: int | None = None
    max_tokens_per_request: int | None = None


@router.get("/efficiency")
def get_efficiency(_: User = Depends(require_roles(Role.SUPER_ADMIN))) -> dict:
    """Token-efficiency controls (condensación + tope de gasto) y ahorro acumulado."""
    from .. import runtime_config
    return {
        "condense_enabled": runtime_config.condense_enabled(),
        "condense_threshold_chars": runtime_config.condense_threshold_chars(),
        "max_tokens_per_request": runtime_config.max_tokens_per_request(),
        "tokens_saved_total": runtime_config.tokens_saved_total(),
    }


@router.put("/efficiency")
def update_efficiency(
    body: EfficiencyIn,
    _: User = Depends(require_roles(Role.SUPER_ADMIN)),
    session: Session = Depends(get_session),
) -> dict:
    from .. import runtime_config
    if body.condense_enabled is not None:
        runtime_config.set_value(session, "condense_enabled", str(body.condense_enabled).lower())
    if body.condense_threshold_chars is not None:
        runtime_config.set_value(session, "condense_threshold_chars", str(max(0, body.condense_threshold_chars)))
    if body.max_tokens_per_request is not None:
        runtime_config.set_value(session, "max_tokens_per_request", str(max(0, body.max_tokens_per_request)))
    return {
        "condense_enabled": runtime_config.condense_enabled(),
        "condense_threshold_chars": runtime_config.condense_threshold_chars(),
        "max_tokens_per_request": runtime_config.max_tokens_per_request(),
        "tokens_saved_total": runtime_config.tokens_saved_total(),
    }


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
