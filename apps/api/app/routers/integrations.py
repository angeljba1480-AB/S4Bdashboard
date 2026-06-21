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
from ..models import Connector, Role, Tenant, User
from ..security.crypto import decrypt, encrypt

router = APIRouter(prefix="/integrations", tags=["integrations"])

KINDS = ["crm", "erp", "delivery", "custom"]


class ConnectorIn(BaseModel):
    kind: str = "crm"
    name: str
    base_url: str
    auth_header: str = "Authorization"
    token: str = ""


def _out(c: Connector) -> dict:
    return {"id": c.id, "kind": c.kind, "name": c.name, "base_url": c.base_url,
            "auth_header": c.auth_header, "has_token": bool(c.token_enc), "enabled": c.enabled}


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
        r = httpx.post(cnx.base_url, json=payload, headers=headers, timeout=20)
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
                  base_url=body.base_url.strip(), auth_header=body.auth_header.strip() or "Authorization",
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
