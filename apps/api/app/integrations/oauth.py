"""OAuth2 (authorization code) for mailbox/calendar providers.

Microsoft (Outlook/Graph) and Google (Gmail/Calendar). Self-contained: builds
authorize URLs, exchanges/refreshes tokens, and signs the `state` parameter so
the callback (which carries no JWT) can be tied back to the requesting user.
"""
from __future__ import annotations

import time
from urllib.parse import urlencode

import httpx
import jwt

from ..config import settings

ALGORITHM = "HS256"


def _providers() -> dict[str, dict]:
    return {
        "microsoft": {
            "enabled": settings.microsoft_oauth_enabled,
            "client_id": settings.microsoft_client_id,
            "client_secret": settings.microsoft_client_secret,
            "redirect_uri": settings.microsoft_redirect_uri,
            "scopes": settings.microsoft_scopes,
            "authorize_url": f"https://login.microsoftonline.com/{settings.microsoft_tenant}/oauth2/v2.0/authorize",
            "token_url": f"https://login.microsoftonline.com/{settings.microsoft_tenant}/oauth2/v2.0/token",
            "label": "Outlook",
        },
        "google": {
            "enabled": settings.google_oauth_enabled,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "scopes": settings.google_scopes,
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "label": "Gmail",
        },
    }


def provider_config(provider: str) -> dict | None:
    return _providers().get(provider)


def enabled_providers() -> list[dict]:
    return [{"provider": k, "label": v["label"], "enabled": v["enabled"]}
            for k, v in _providers().items()]


def is_enabled(provider: str) -> bool:
    cfg = provider_config(provider)
    return bool(cfg and cfg["enabled"] and cfg["client_id"] and cfg["redirect_uri"])


# --- state signing ----------------------------------------------------------
def sign_state(user_id: str, tenant_id: str, provider: str) -> str:
    payload = {"uid": user_id, "tid": tenant_id, "prov": provider,
               "exp": int(time.time()) + 600}  # 10 min to complete the flow
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def verify_state(state: str) -> dict | None:
    try:
        return jwt.decode(state, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


# --- flow -------------------------------------------------------------------
def build_authorize_url(provider: str, state: str) -> str:
    cfg = provider_config(provider)
    if not cfg:
        raise ValueError(f"proveedor desconocido: {provider}")
    # Force the account chooser so the user can connect a *different* account of
    # the same provider (e.g. personal + work). Google accepts space-delimited
    # prompt values; Microsoft takes a single one.
    prompt = "select_account consent" if provider == "google" else "select_account"
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": cfg["scopes"],
        "state": state,
        "access_type": "offline",      # Google: request a refresh token
        "prompt": prompt,
    }
    return f"{cfg['authorize_url']}?{urlencode(params)}"


def exchange_code(provider: str, code: str) -> dict:
    cfg = provider_config(provider)
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg["redirect_uri"],
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
    }
    resp = httpx.post(cfg["token_url"], data=data, timeout=20)
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(provider: str, refresh_token: str) -> dict:
    cfg = provider_config(provider)
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
    }
    resp = httpx.post(cfg["token_url"], data=data, timeout=20)
    resp.raise_for_status()
    return resp.json()
