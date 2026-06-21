"""SSO / OIDC authorization-code flow (blueprint §4: Auth = Keycloak/Auth0/
Clerk/Entra). Optional and pluggable — enabled via SSO_ENABLED + OIDC_* config.

When disabled, the platform uses password login. When enabled, users are
auto-provisioned into a tenant derived from their email domain on first login.
"""
from __future__ import annotations

from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import create_access_token
from ..config import settings
from ..db import get_session
from ..models import AuditEvent, Role, Tenant, User

router = APIRouter(prefix="/auth/sso", tags=["auth"])


def _discovery() -> dict:
    url = f"{settings.oidc_issuer.rstrip('/')}/.well-known/openid-configuration"
    return httpx.get(url, timeout=15).raise_for_status().json()


@router.get("/config")
def sso_config() -> dict:
    """Lets the frontend decide whether to show the SSO button."""
    if not settings.sso_enabled:
        return {"enabled": False}
    params = urlencode({
        "client_id": settings.oidc_client_id,
        "redirect_uri": settings.oidc_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
    })
    try:
        authorize = _discovery()["authorization_endpoint"]
    except Exception:
        return {"enabled": False, "error": "OIDC discovery failed"}
    return {"enabled": True, "authorize_url": f"{authorize}?{params}"}


class CallbackBody(BaseModel):
    code: str


@router.post("/callback")
def sso_callback(body: CallbackBody, session: Session = Depends(get_session)) -> dict:
    if not settings.sso_enabled:
        raise HTTPException(status_code=400, detail="SSO no habilitado")

    conf = _discovery()
    token_resp = httpx.post(conf["token_endpoint"], data={
        "grant_type": "authorization_code",
        "code": body.code,
        "redirect_uri": settings.oidc_redirect_uri,
        "client_id": settings.oidc_client_id,
        "client_secret": settings.oidc_client_secret,
    }, timeout=15)
    token_resp.raise_for_status()
    access = token_resp.json().get("access_token")

    userinfo = httpx.get(conf["userinfo_endpoint"],
                         headers={"Authorization": f"Bearer {access}"}, timeout=15)
    userinfo.raise_for_status()
    info = userinfo.json()
    email = info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="El IdP no devolvió email")

    user = _provision(session, email, info.get("name") or email)
    session.add(AuditEvent(tenant_id=user.tenant_id, user_id=user.id, event_type="login",
                           object_type="user", object_id=user.id, reason="login SSO/OIDC"))
    session.commit()
    return {"access_token": create_access_token(user), "token_type": "bearer"}


def _provision(session: Session, email: str, name: str) -> User:
    """Find or create the user (and a tenant from the email domain)."""
    user = session.exec(select(User).where(User.email == email)).first()
    if user:
        return user
    domain = email.split("@")[-1]
    tenant = session.exec(select(Tenant).where(Tenant.name == domain)).first()
    if not tenant:
        tenant = Tenant(name=domain)
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
    user = User(tenant_id=tenant.id, email=email, name=name,
                role=Role(settings.oidc_default_role), status="active")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
