"""Persistence for mailbox OAuth tokens (encrypted at rest) + auto-refresh.

Also stores generic IMAP credentials (provider="imap") in the same table: the
connection blob {host, port, email, password} is encrypted into access_token_enc
and never expires (expires_at == 0).
"""
from __future__ import annotations

import json
import time
from datetime import datetime

from sqlmodel import Session, select

from ..models import OAuthToken, Tenant
from ..security.crypto import decrypt, encrypt
from . import oauth


def _kms(tenant: Tenant) -> str:
    return tenant.kms_key_id


def save_imap(session: Session, tenant: Tenant, user_id: str,
              host: str, port: int, email: str, password: str) -> OAuthToken:
    """Store generic IMAP credentials (encrypted) as a non-expiring connection.

    Keyed by email so a user can connect several IMAP mailboxes; reconnecting the
    same address updates it instead of creating a duplicate.
    """
    row = session.exec(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant.id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == "imap",
            OAuthToken.identifier == email,
        )
    ).first() or OAuthToken(tenant_id=tenant.id, user_id=user_id, provider="imap")
    blob = json.dumps({"host": host, "port": int(port or 993), "email": email, "password": password})
    row.identifier = email
    row.access_token_enc = encrypt(blob, _kms(tenant))
    row.refresh_token_enc = ""
    row.expires_at = 0  # IMAP credentials don't expire
    row.scopes = "imap"
    row.status = "active"
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def save_token(session: Session, tenant: Tenant, user_id: str, provider: str,
               identifier: str, token_resp: dict) -> OAuthToken:
    # Key by (provider, identifier) so a user can connect several accounts of the
    # same provider (e.g. personal + work Google). Reconnecting the same address
    # updates its row; a new address inserts a new one. When the identity couldn't
    # be resolved (identifier empty) fall back to matching the provider alone to
    # avoid orphaning a credential-less row.
    query = select(OAuthToken).where(
        OAuthToken.tenant_id == tenant.id,
        OAuthToken.user_id == user_id,
        OAuthToken.provider == provider,
    )
    if identifier:
        query = query.where(OAuthToken.identifier == identifier)
    row = session.exec(query).first() or OAuthToken(
        tenant_id=tenant.id, user_id=user_id, provider=provider)

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


def get_connection(session: Session, tenant_id: str, user_id: str, conn_id: str) -> OAuthToken | None:
    """Fetch one active connection by its id, scoped to the tenant + user."""
    row = session.get(OAuthToken, conn_id)
    if not row or row.tenant_id != tenant_id or row.user_id != user_id or row.status != "active":
        return None
    return row


def access_token_for(session: Session, tenant: Tenant, row: OAuthToken) -> str | None:
    """Return a usable access token for a specific connection, refreshing if expired."""
    # expires_at == 0 means non-expiring (IMAP credentials blob).
    if row.expires_at == 0 or row.expires_at > time.time():
        return decrypt(row.access_token_enc, _kms(tenant))

    refresh = decrypt(row.refresh_token_enc, _kms(tenant)) if row.refresh_token_enc else ""
    if not refresh:
        return None
    try:
        token_resp = oauth.refresh_access_token(row.provider, refresh)
    except Exception:
        return None
    row = save_token(session, tenant, row.user_id, row.provider, row.identifier, token_resp)
    return decrypt(row.access_token_enc, _kms(tenant))


def get_valid_access_token(session: Session, tenant: Tenant, user_id: str, provider: str) -> str | None:
    """Back-compat: token for the first active connection of a provider."""
    row = session.exec(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant.id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider,
            OAuthToken.status == "active",
        )
    ).first()
    return access_token_for(session, tenant, row) if row else None


def list_connections(session: Session, tenant_id: str, user_id: str) -> list[OAuthToken]:
    return session.exec(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.status == "active",
        )
    ).all()


def resolve_connection(session: Session, tenant_id: str, user_id: str,
                       prefer: str = "") -> OAuthToken | None:
    """Pick a connection for the use case. `prefer` may be a connection id or an
    email address; falls back to the first active connection."""
    conns = list_connections(session, tenant_id, user_id)
    if not conns:
        return None
    if prefer:
        for c in conns:
            if c.id == prefer:
                return c
        for c in conns:
            if c.identifier and c.identifier.lower() == prefer.lower():
                return c
    return conns[0]


def active_provider(session: Session, tenant_id: str, user_id: str, prefer_email: str = "") -> str | None:
    """Pick the user's connected provider, preferring one matching prefer_email."""
    conn = resolve_connection(session, tenant_id, user_id, prefer_email)
    return conn.provider if conn else None


def _revoke_row(row: OAuthToken) -> None:
    row.status = "revoked"
    row.access_token_enc = ""
    row.refresh_token_enc = ""


def revoke(session: Session, tenant_id: str, user_id: str, provider: str) -> bool:
    """Disconnect every active account of a provider (e.g. all Gmail accounts)."""
    rows = session.exec(
        select(OAuthToken).where(
            OAuthToken.tenant_id == tenant_id,
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider,
            OAuthToken.status == "active",
        )
    ).all()
    if not rows:
        return False
    for row in rows:
        _revoke_row(row)
        session.add(row)
    session.commit()
    return True


def revoke_connection(session: Session, tenant_id: str, user_id: str, conn_id: str) -> bool:
    """Disconnect a single account by its connection id."""
    row = get_connection(session, tenant_id, user_id, conn_id)
    if not row:
        return False
    _revoke_row(row)
    session.add(row)
    session.commit()
    return True
