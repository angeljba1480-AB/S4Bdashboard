"""Auth endpoints: /auth/login and /me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import create_access_token, get_current_user, verify_password
from ..db import get_session
from ..models import AuditEvent, Tenant, User
from ..schemas import LoginRequest, MeResponse, TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.exec(select(User).where(User.email == body.email)).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    session.add(AuditEvent(
        tenant_id=user.tenant_id, user_id=user.id, event_type="login",
        object_type="user", object_id=user.id, risk_level="low", reason="login exitoso",
    ))
    session.commit()
    return TokenResponse(access_token=create_access_token(user))


@router.get("/account")
def account(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """The user's own license + the company's license pool (seats)."""
    tenant = session.get(Tenant, user.tenant_id)
    seat_holders = session.exec(
        select(User).where(User.tenant_id == user.tenant_id, User.status == "active")
    ).all()
    used = len(seat_holders)
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role.value},
        "license": {
            "type": user.role.value,            # license tier follows the role
            "status": "active" if user.status == "active" else "inactive",
            "seat_assigned": user.status == "active",
        },
        "company": {
            "name": tenant.name if tenant else "",
            "plan": tenant.plan if tenant else "",
            "subscription_status": tenant.subscription_status if tenant else "",
            "renews_at": (tenant.subscription_renews_at or None) if tenant else None,
            "seats_licensed": tenant.seats_licensed if tenant else 0,
            "seats_used": used,
            "seats_available": max(0, (tenant.seats_licensed if tenant else 0) - used),
        },
        "licensed_users": [
            {"name": u.name, "email": u.email, "role": u.role.value, "status": u.status}
            for u in seat_holders
        ],
    }


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MeResponse:
    tenant = session.get(Tenant, user.tenant_id)
    return MeResponse(
        id=user.id, email=user.email, name=user.name, role=user.role,
        tenant_id=user.tenant_id, tenant_name=tenant.name if tenant else "",
        mfa_enabled=user.mfa_enabled,
        brand_name=tenant.brand_name if tenant else "",
        brand_logo_url=tenant.brand_logo_url if tenant else "",
        brand_color=tenant.brand_color if tenant else "",
        brand_tagline=tenant.brand_tagline if tenant else "",
    )
