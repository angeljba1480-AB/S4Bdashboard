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


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> MeResponse:
    tenant = session.get(Tenant, user.tenant_id)
    return MeResponse(
        id=user.id, email=user.email, name=user.name, role=user.role,
        tenant_id=user.tenant_id, tenant_name=tenant.name if tenant else "",
        mfa_enabled=user.mfa_enabled,
    )
