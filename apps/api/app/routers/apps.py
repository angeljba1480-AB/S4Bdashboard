"""/apps — App Studio. Genera apps con IA (plan por el router de privacidad, auditado).

Publicación honesta:
- Sin pasarela de pago (PAYMENTS_ENABLED=false, por defecto): la publicación es
  **simulada** — no se cobra nada ni se despliega a un servidor real; el estado queda
  "simulado". Así no presentamos una transacción/URL falsa como real.
- Con pasarela (PAYMENTS_ENABLED=true): pay-to-prod real — /deploy responde 402 con
  checkout hasta pagar; un proveedor real (Stripe/MercadoPago) confirma vía /checkout y
  un pipeline real reemplaza el stub de deploy.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..ai.cost import estimate_cost, estimate_tokens
from ..ai.resilience import generate_with_fallback
from ..ai.router import route_request
from ..auth import get_current_tenant, get_current_user
from ..config import settings
from ..db import get_session
from ..models import AppProject, AuditEvent, ModelRoute, Tenant, User

router = APIRouter(prefix="/apps", tags=["apps"])

# Pay-to-prod price (configurable; real charge handled by the provider).
DEPLOY_PRICE_MXN = 499


class AppCreate(BaseModel):
    name: str
    description: str


def _now():
    from datetime import datetime
    return datetime.utcnow()


def _out(p: AppProject) -> dict:
    simulated = p.status == "simulado"
    return {"id": p.id, "name": p.name, "description": p.description, "spec": p.spec,
            "status": p.status, "paid": p.paid, "deploy_url": p.deploy_url or None,
            "simulated": simulated,
            "note": ("Publicación simulada: no hay pasarela de pago configurada, no se realizó "
                     "ningún cargo y no se desplegó a un servidor real." if simulated else None)}


def _load(session, tenant, user, app_id) -> AppProject:
    p = session.get(AppProject, app_id)
    if not p or p.tenant_id != tenant.id or p.user_id != user.id:
        raise HTTPException(status_code=404, detail="App no encontrada")
    return p


@router.get("")
def list_apps(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(
        select(AppProject).where(AppProject.tenant_id == tenant.id, AppProject.user_id == user.id)
        .order_by(AppProject.created_at.desc())
    ).all()
    return [_out(p) for p in rows]


@router.post("")
def create_app(
    body: AppCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Build the app: generate a plan/scaffold with AI (governed by the router)."""
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")

    instruction = (
        f"Eres un arquitecto de software. Diseña una app llamada «{body.name}» que: "
        f"{body.description}. Devuelve: objetivo, pantallas, entidades de datos, "
        f"integraciones y pasos para construirla. En español, conciso."
    )
    decision = route_request(tenant, None, instruction, [], task="app_build")
    spec, route = "", decision.route
    if decision.route != ModelRoute.BLOCKED:
        gen = generate_with_fallback(decision.route, "Arquitecto de software.", instruction, decision.context)
        spec = gen.response.content if gen.route != ModelRoute.BLOCKED else ""
        route = gen.route
    tokens = estimate_tokens(instruction + spec)
    cost = estimate_cost(route, tokens)

    p = AppProject(tenant_id=tenant.id, user_id=user.id, name=body.name.strip(),
                   description=body.description.strip(), spec=spec, status="built",
                   token_count=tokens, cost_estimate=cost)
    session.add(p)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="app_build",
        object_type="app", object_id=p.id, risk_level="low",
        reason=f"app construida: {p.name}",
    ))
    session.commit()
    session.refresh(p)
    return _out(p)


@router.get("/{app_id}")
def get_app(
    app_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    return _out(_load(session, tenant, user, app_id))


@router.post("/{app_id}/deploy")
def deploy_app(
    app_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Publica la app. Si hay pasarela de pago (PAYMENTS_ENABLED) es pay-to-prod
    (402 si no está pagado). Sin pasarela: publicación **simulada, sin cargo** —
    no se cobra ni se despliega a un servidor real (honestidad de modo demo)."""
    p = _load(session, tenant, user, app_id)

    if not settings.payments_enabled:
        # Sin pago: no cobramos ni fabricamos una URL muerta. Se marca como simulada.
        p.status = "simulado"
        p.deploy_url = ""
        p.updated_at = _now()
        session.add(p)
        session.add(AuditEvent(
            tenant_id=tenant.id, user_id=user.id, event_type="app_deploy_simulado",
            object_type="app", object_id=p.id, risk_level="low",
            reason=f"publicación simulada (App Studio sin pasarela de pago): {p.name}",
        ))
        session.commit()
        session.refresh(p)
        return _out(p)

    # Con pasarela: gate de pago real.
    if not p.paid:
        p.status = "pending_payment"
        session.add(p)
        session.commit()
        raise HTTPException(status_code=402, detail={
            "message": "Para publicar a producción necesitas completar el pago.",
            "checkout": {"app_id": p.id, "amount": DEPLOY_PRICE_MXN, "currency": "MXN",
                         "confirm_path": f"/apps/{p.id}/checkout"},
        })

    # Stub deploy — a real pipeline (containers / Vercel) wires in here.
    p.status = "deployed"
    p.deploy_url = f"https://{p.id}.apps.tu-saas.mx"
    p.updated_at = _now()
    session.add(p)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="app_deploy",
        object_type="app", object_id=p.id, risk_level="med",
        reason=f"app publicada a producción: {p.name}",
    ))
    session.commit()
    session.refresh(p)
    return _out(p)


@router.post("/{app_id}/checkout")
def confirm_checkout(
    app_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Confirm payment (stub). A real provider webhook (Stripe/MercadoPago) sets
    `paid` here. After this, /deploy succeeds."""
    p = _load(session, tenant, user, app_id)
    if not settings.payments_enabled:
        raise HTTPException(status_code=409, detail=(
            "Pagos no habilitados en esta instancia (modo demo). No se realizó ningún cargo; "
            "publica en modo simulado desde /deploy."))
    p.paid = True
    session.add(p)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="app_payment",
        object_type="app", object_id=p.id, risk_level="med",
        reason=f"pago confirmado (pay-to-prod) por {DEPLOY_PRICE_MXN} MXN: {p.name}",
    ))
    session.commit()
    return {"id": p.id, "paid": True, "next": f"/apps/{p.id}/deploy"}
