"""Auth endpoints: /auth/login and /me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import mfa as mfa_lib
from ..auth import create_access_token, get_current_user, verify_password
from ..db import get_session
from ..models import AuditEvent, Tenant, User
from ..regional.countries import get_country
from ..schemas import LoginRequest, MeResponse, TokenResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.exec(select(User).where(User.email == body.email)).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    # Segundo factor: solo se exige si MFA está activo Y hay un secreto enrolado
    # (evita bloquear cuentas con el flag puesto pero sin TOTP configurado).
    if user.mfa_enabled and user.mfa_secret_enc:
        if not body.mfa_code:
            raise HTTPException(status_code=401, detail="MFA_REQUIRED")
        ok, new_blob = mfa_lib.check_second_factor(
            user.mfa_secret_enc, user.mfa_backup_codes, user.tenant_id, body.mfa_code)
        if not ok:
            session.add(AuditEvent(
                tenant_id=user.tenant_id, user_id=user.id, event_type="login", object_type="user",
                object_id=user.id, risk_level="med", reason="MFA inválido"))
            session.commit()
            raise HTTPException(status_code=401, detail="Código MFA inválido")
        if new_blob != user.mfa_backup_codes:   # se consumió un código de respaldo
            user.mfa_backup_codes = new_blob
            session.add(user)
    session.add(AuditEvent(
        tenant_id=user.tenant_id, user_id=user.id, event_type="login",
        object_type="user", object_id=user.id, risk_level="low", reason="login exitoso",
    ))
    session.commit()
    return TokenResponse(access_token=create_access_token(user))


# --- MFA (TOTP) -------------------------------------------------------------
class MfaCode(BaseModel):
    code: str


@router.post("/auth/mfa/setup")
def mfa_setup(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    """Genera un secreto TOTP (pendiente hasta verificar) y devuelve el otpauth URI."""
    secret = mfa_lib.new_secret()
    user.mfa_secret_enc = mfa_lib.encrypt_secret(secret, user.tenant_id)
    session.add(user)
    session.commit()
    return {"secret": secret, "otpauth_uri": mfa_lib.provisioning_uri(secret, user.email),
            "issuer": mfa_lib.ISSUER}


@router.post("/auth/mfa/verify")
def mfa_verify(body: MfaCode, user: User = Depends(get_current_user),
               session: Session = Depends(get_session)) -> dict:
    """Confirma el enrolamiento: valida el primer código y activa MFA. Devuelve los
    códigos de respaldo (se muestran una sola vez)."""
    secret = mfa_lib.decrypt_secret(user.mfa_secret_enc, user.tenant_id)
    if not secret or not mfa_lib.verify_totp(secret, body.code):
        raise HTTPException(status_code=400, detail="Código inválido")
    codes, blob = mfa_lib.gen_backup_codes()
    user.mfa_enabled = True
    user.mfa_backup_codes = blob
    session.add(user)
    session.add(AuditEvent(tenant_id=user.tenant_id, user_id=user.id, event_type="security",
                           object_type="user", object_id=user.id, risk_level="low", reason="MFA activado"))
    session.commit()
    return {"enabled": True, "backup_codes": codes}


@router.post("/auth/mfa/disable")
def mfa_disable(body: MfaCode, user: User = Depends(get_current_user),
                session: Session = Depends(get_session)) -> dict:
    """Desactiva MFA validando primero un código vigente (TOTP o respaldo)."""
    if not user.mfa_enabled:
        return {"enabled": False}
    ok, _ = mfa_lib.check_second_factor(user.mfa_secret_enc, user.mfa_backup_codes, user.tenant_id, body.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Código inválido")
    user.mfa_enabled = False
    user.mfa_secret_enc = ""
    user.mfa_backup_codes = ""
    session.add(user)
    session.add(AuditEvent(tenant_id=user.tenant_id, user_id=user.id, event_type="security",
                           object_type="user", object_id=user.id, risk_level="med", reason="MFA desactivado"))
    session.commit()
    return {"enabled": False}


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
        country=tenant.country if tenant else "MX",
        country_name=get_country(tenant.country if tenant else "MX")["name"],
    )
