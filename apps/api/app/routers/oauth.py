"""/oauth — connect a user's mailbox/calendar (Microsoft Outlook / Google).

Authorization-code flow. The browser callback carries a signed `state` (not a
JWT), so we can tie it back to the requesting user without a session cookie.
Tokens are stored encrypted (see token_store) and used by the
'Resumen de correo y agenda' use case.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from ..auth import get_current_tenant, get_current_user
from ..config import settings
from ..db import get_session
from ..integrations import oauth, token_store
from ..models import AuditEvent, Tenant, User

router = APIRouter(prefix="/oauth", tags=["oauth"])


def _identity(provider: str, access_token: str) -> str:
    """Best-effort fetch of the connected account's email address."""
    try:
        if provider == "microsoft":
            r = httpx.get("https://graph.microsoft.com/v1.0/me",
                          headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
            d = r.json()
            return d.get("mail") or d.get("userPrincipalName") or ""
        r = httpx.get("https://www.googleapis.com/oauth2/v2/userinfo",
                      headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        return r.json().get("email", "")
    except Exception:
        return ""


@router.get("/providers")
def providers(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    connected = {c.provider: c.identifier for c in token_store.list_connections(session, tenant.id, user.id)}
    return {
        "providers": [
            {**p, "configured": oauth.is_enabled(p["provider"]),
             "connected": p["provider"] in connected,
             "identifier": connected.get(p["provider"], "")}
            for p in oauth.enabled_providers()
        ]
    }


@router.get("/{provider}/authorize")
def authorize(
    provider: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
) -> dict:
    if not oauth.is_enabled(provider):
        raise HTTPException(status_code=400,
                            detail=f"La conexión con {provider} no está configurada. Pídele al admin que la habilite.")
    state = oauth.sign_state(user.id, tenant.id, provider)
    return {"authorize_url": oauth.build_authorize_url(provider, state)}


@router.get("/{provider}/callback")
def callback(
    provider: str,
    code: str = "",
    state: str = "",
    error: str = "",
    session: Session = Depends(get_session),
):
    base = settings.app_public_url.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(f"{base}/integrations?connected=error")
    claims = oauth.verify_state(state)
    if not claims or claims.get("prov") != provider:
        return RedirectResponse(f"{base}/integrations?connected=error")

    tenant = session.get(Tenant, claims["tid"])
    user = session.get(User, claims["uid"])
    if not tenant or not user:
        return RedirectResponse(f"{base}/integrations?connected=error")

    try:
        token_resp = oauth.exchange_code(provider, code)
    except Exception:
        return RedirectResponse(f"{base}/integrations?connected=error")

    identifier = _identity(provider, token_resp.get("access_token", ""))
    token_store.save_token(session, tenant, user.id, provider, identifier, token_resp)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="connection",
        object_type="oauth_token", object_id=provider, risk_level="med",
        reason=f"correo conectado vía {provider} ({identifier})",
    ))
    session.commit()
    return RedirectResponse(f"{base}/integrations?connected={provider}")


@router.delete("/{provider}")
def disconnect(
    provider: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    ok = token_store.revoke(session, tenant.id, user.id, provider)
    if ok:
        session.add(AuditEvent(
            tenant_id=tenant.id, user_id=user.id, event_type="connection",
            object_type="oauth_token", object_id=provider, risk_level="low",
            reason=f"correo desconectado: {provider}",
        ))
        session.commit()
    return {"ok": ok}
