"""/integrations — outbound connectors to enterprise systems (CRM/ERP/delivery).

MaestroAI pushes data to a configured endpoint (webhook/REST). Connectors are
used by automations (action_type "connector") and can be tested directly.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, require_roles
from ..db import get_session
from ..models import AuditEvent, Connector, Role, Tenant, User, WebhookEndpoint
from ..security.crypto import decrypt, encrypt

router = APIRouter(prefix="/integrations", tags=["integrations"])

KINDS = ["crm", "erp", "delivery", "custom"]

# Ready-made connector templates with the payload shape each system expects.
CONNECTOR_TEMPLATES: list[dict] = [
    {"id": "hubspot", "kind": "crm", "name": "HubSpot", "auth_header": "Authorization",
     "base_url": "https://api.hubapi.com/crm/v3/objects/contacts",
     "auth_hint": "Bearer <private app token>",
     "payload_example": {"properties": {"email": "cliente@correo.com", "firstname": "Ana", "phone": "55..."}}},
    {"id": "salesforce", "kind": "crm", "name": "Salesforce", "auth_header": "Authorization",
     "base_url": "https://<instance>.salesforce.com/services/data/v60.0/sobjects/Lead",
     "auth_hint": "Bearer <OAuth access token>",
     "payload_example": {"LastName": "Pérez", "Company": "ACME", "Email": "ana@acme.com"}},
    {"id": "shopify", "kind": "erp", "name": "Shopify", "auth_header": "X-Shopify-Access-Token",
     "base_url": "https://<shop>.myshopify.com/admin/api/2024-01/orders.json",
     "auth_hint": "<Admin API access token>",
     "payload_example": {"order": {"line_items": [{"title": "Producto", "quantity": 1, "price": "100.00"}]}}},
    {"id": "rappi", "kind": "delivery", "name": "Rappi", "auth_header": "Authorization",
     "base_url": "https://services.rappi.com/api/...",
     "auth_hint": "Bearer <token>",
     "payload_example": {"order_id": "123", "store_id": "...", "items": [{"sku": "A1", "qty": 2}]}},
    {"id": "webhook", "kind": "custom", "name": "Webhook genérico", "auth_header": "Authorization",
     "base_url": "https://tu-sistema.com/webhook",
     "auth_hint": "Bearer <token> (opcional)",
     "payload_example": {"event": "maestroai", "data": {}}},
]


@router.get("/connector-templates")
def connector_templates(_: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS))) -> list[dict]:
    return CONNECTOR_TEMPLATES


class ConnectorIn(BaseModel):
    kind: str = "crm"
    name: str
    base_url: str
    auth_header: str = "Authorization"
    token: str = ""


def _example_for(kind: str) -> dict:
    """A ready-made example (base_url + auth hint + payload) for this kind."""
    for t in CONNECTOR_TEMPLATES:
        if t["kind"] == kind:
            return {"base_url": t["base_url"], "auth_header": t["auth_header"],
                    "auth_hint": t["auth_hint"], "payload_example": t["payload_example"]}
    return {}


def _out(c: Connector) -> dict:
    return {"id": c.id, "kind": c.kind, "name": c.name, "base_url": c.base_url,
            "auth_header": c.auth_header, "has_token": bool(c.token_enc), "enabled": c.enabled,
            "example": _example_for(c.kind)}


def _normalize_url(url: str) -> str:
    """Acepta URLs sin protocolo (p. ej. pegadas de n8n) y antepone https://.
    Evita el error 'Request URL is missing an http://' de httpx."""
    url = (url or "").strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def send_to_connector(session: Session, tenant: Tenant, connector_id: str, payload: dict) -> tuple[str, str]:
    """POST a payload to a tenant connector. Returns (status, detail)."""
    cnx = session.get(Connector, connector_id)
    if not cnx or cnx.tenant_id != tenant.id:
        return "failed", "conector no encontrado"
    if not cnx.enabled or not cnx.base_url:
        return "failed", "conector deshabilitado o sin URL"
    import httpx
    headers = {}
    if cnx.token_enc:
        headers[cnx.auth_header] = decrypt(cnx.token_enc, tenant.id)
    try:  # pragma: no cover - network
        r = httpx.post(_normalize_url(cnx.base_url), json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        return "completed", f"{cnx.kind}:{cnx.name} → {r.status_code}"
    except Exception as exc:  # pragma: no cover - network
        return "failed", f"{cnx.kind} error: {exc}"


@router.get("/connectors")
def list_connectors(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(select(Connector).where(Connector.tenant_id == tenant.id)).all()
    return [_out(c) for c in rows]


@router.post("/connectors", status_code=201)
def create_connector(
    body: ConnectorIn,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    if body.kind not in KINDS:
        raise HTTPException(status_code=422, detail=f"kind inválido (usa {KINDS})")
    if not body.name.strip() or not body.base_url.strip():
        raise HTTPException(status_code=422, detail="Nombre y base_url son obligatorios")
    c = Connector(tenant_id=tenant.id, kind=body.kind, name=body.name.strip(),
                  base_url=_normalize_url(body.base_url), auth_header=body.auth_header.strip() or "Authorization",
                  token_enc=encrypt(body.token, tenant.id) if body.token else "")
    session.add(c)
    session.commit()
    session.refresh(c)
    return _out(c)


@router.post("/connectors/{connector_id}/test")
def test_connector(
    connector_id: str,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    status, detail = send_to_connector(session, tenant, connector_id, {"test": True, "from": "MaestroAI"})
    return {"status": status, "detail": detail}


@router.get("/connectors/{connector_id}/reveal")
def reveal_connector(
    connector_id: str,
    user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Revela el secreto (token) configurado — para el 'ojito' de info sensible.
    Solo ADMIN/DEVOPS y queda auditado."""
    c = session.get(Connector, connector_id)
    if not c or c.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Conector no encontrado")
    token = decrypt(c.token_enc, tenant.id) if c.token_enc else ""
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="reveal", object_type="connector",
        object_id=c.id, risk_level="med", reason=f"reveló el secreto del conector '{c.name}'",
    ))
    session.commit()
    return {"auth_header": c.auth_header, "token": token}


@router.delete("/connectors/{connector_id}")
def delete_connector(
    connector_id: str,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    c = session.get(Connector, connector_id)
    if not c or c.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Conector no encontrado")
    session.delete(c)
    session.commit()
    return {"ok": True}


# --- Inbound signed webhooks (HMAC) ----------------------------------------
class WebhookIn(BaseModel):
    name: str = "Webhook entrante"
    default_event: str = "webhook"


@router.get("/webhooks")
def list_webhooks(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(select(WebhookEndpoint).where(WebhookEndpoint.tenant_id == tenant.id)).all()
    return [{"id": w.id, "name": w.name, "default_event": w.default_event, "enabled": w.enabled,
             "url": f"/v1/webhooks/{w.id}"} for w in rows]


@router.post("/webhooks", status_code=201)
def create_webhook(
    body: WebhookIn,
    _: User = Depends(require_roles(Role.ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Create an inbound webhook. Returns the HMAC secret once."""
    import secrets
    secret = f"whsec_{secrets.token_urlsafe(24)}"
    w = WebhookEndpoint(tenant_id=tenant.id, name=body.name.strip() or "Webhook entrante",
                        default_event=body.default_event.strip() or "webhook",
                        secret_enc=encrypt(secret, tenant.id))
    session.add(w)
    session.commit()
    session.refresh(w)
    return {"id": w.id, "name": w.name, "url": f"/v1/webhooks/{w.id}", "secret": secret,
            "note": "Firma el cuerpo con HMAC-SHA256 usando este secreto en el header X-Signature."}


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    w = session.get(WebhookEndpoint, webhook_id)
    if not w or w.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Webhook no encontrado")
    session.delete(w)
    session.commit()
    return {"ok": True}
