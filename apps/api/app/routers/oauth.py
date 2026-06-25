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
from pydantic import BaseModel
from sqlmodel import Session

from ..auth import get_current_tenant, get_current_user
from ..config import settings
from ..db import get_session
from ..integrations import mailbox, oauth, token_store
from ..models import AuditEvent, Tenant, User

router = APIRouter(prefix="/oauth", tags=["oauth"])


class ImapConnect(BaseModel):
    host: str
    port: int = 993
    email: str
    password: str


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
    labels = {p["provider"]: p["label"] for p in oauth.enabled_providers()}
    labels["imap"] = "IMAP"
    # Connectable provider types (a user may connect several accounts of each).
    out = [{**p, "kind": "oauth", "configured": oauth.is_enabled(p["provider"])}
           for p in oauth.enabled_providers()]
    # Generic IMAP catch-all — always available (user provides credentials).
    out.append({"provider": "imap", "label": "Otro correo (IMAP)", "kind": "imap",
                "enabled": True, "configured": True})
    # Every connected account (one row per account, multiple per provider allowed).
    connections = [
        {"id": c.id, "provider": c.provider,
         "label": labels.get(c.provider, c.provider), "identifier": c.identifier}
        for c in token_store.list_connections(session, tenant.id, user.id)
    ]
    return {"providers": out, "connections": connections}


@router.post("/imap")
def connect_imap(
    body: ImapConnect,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Connect any mailbox via IMAP (Yahoo, iCloud, Zoho, hosting, corporate…)."""
    if not (body.host and body.email and body.password):
        raise HTTPException(status_code=422, detail="Faltan servidor, correo o contraseña")
    try:
        mailbox.imap_test(body.host.strip(), body.port, body.email.strip(), body.password)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=("No se pudo conectar. Verifica servidor/puerto y usa una "
                    "contraseña de aplicación si tu proveedor la exige."))
    token_store.save_imap(session, tenant, user.id, body.host.strip(), body.port,
                          body.email.strip(), body.password)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="connection",
        object_type="oauth_token", object_id="imap", risk_level="med",
        reason=f"correo conectado vía IMAP ({body.email.strip()})",
    ))
    session.commit()
    return {"ok": True, "identifier": body.email.strip()}


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


@router.delete("/connection/{conn_id}")
def disconnect_connection(
    conn_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Disconnect a single connected account by its id."""
    ok = token_store.revoke_connection(session, tenant.id, user.id, conn_id)
    if ok:
        session.add(AuditEvent(
            tenant_id=tenant.id, user_id=user.id, event_type="connection",
            object_type="oauth_token", object_id=conn_id, risk_level="low",
            reason=f"cuenta de correo desconectada: {conn_id}",
        ))
        session.commit()
    return {"ok": ok}


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
