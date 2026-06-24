"""Persistence for mailbox OAuth tokens (encrypted at rest) + auto-refresh."""
from __future__ import annotations

import time
from datetime import datetime

from sqlmodel import Session, select

from ..models import OAuthToken, Tenant
from ..security.crypto import decrypt, encrypt
from . import oauth


def _kms(tenant: Tenant) -> str:
    return tenant.kms_key_id


def save_token(session: Session, tenant: Tenant, user_id: str, provider: str,
               identifier: str, token_resp: dict) -> OAuthToken:
    row = session.exec(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant.id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider,
        )
    ).first() or OAuthToken(tenant_id=tenant.id, user_id=user_id, provider=provider)

    access = token_resp.get("access_token", "")
    refresh = token_resp.get("refresh_token", "")
    expires_in = int(token_resp.get("expires_in", 3600) or 3600)
    row.identifier = identifier or row.identifier
    row.access_token_enc = encrypt(access, _kms(tenant))
    if refresh:  # providers may omit refresh_token on re-consent; keep the old one
        row.refresh_token_enc = encrypt(refresh, _kms(tenant))
    row.expires_at = time.time() + expires_in - 60  # refresh a bit early
    row.scopes = token_resp.get("scope", "")
    row.status = "active"
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_valid_access_token(session: Session, tenant: Tenant, user_id: str, provider: str) -> str | None:
    """Return a usable access token, refreshing it if expired. None if not connected."""
    row = session.exec(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant.id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider,
            OAuthToken.status == "active",
        )
    ).first()
    if not row:
        return None
    if row.expires_at and row.expires_at > time.time():
        return decrypt(row.access_token_enc, _kms(tenant))

    refresh = decrypt(row.refresh_token_enc, _kms(tenant)) if row.refresh_token_enc else ""
    if not refresh:
        return None
    try:
        token_resp = oauth.refresh_access_token(provider, refresh)
    except Exception:
        return None
    row = save_token(session, tenant, user_id, provider, row.identifier, token_resp)
    return decrypt(row.access_token_enc, _kms(tenant))


def list_connections(session: Session, tenant_id: str, user_id: str) -> list[OAuthToken]:
    return session.exec(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.status == "active",
        )
    ).all()


def active_provider(session: Session, tenant_id: str, user_id: str, prefer_email: str = "") -> str | None:
    """Pick the user's connected provider, preferring one matching prefer_email."""
    conns = list_connections(session, tenant_id, user_id)
    if not conns:
        return None
    if prefer_email:
        for c in conns:
            if c.identifier and c.identifier.lower() == prefer_email.lower():
                return c.provider
    return conns[0].provider


def revoke(session: Session, tenant_id: str, user_id: str, provider: str) -> bool:
    row = session.exec(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider,
        )
    ).first()
    if not row:
        return False
    row.status = "revoked"
    row.access_token_enc = ""
    row.refresh_token_enc = ""
    session.add(row)
    session.commit()
    return True
