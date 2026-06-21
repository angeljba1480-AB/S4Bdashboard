"""Authentication & RBAC: password hashing, JWT, and FastAPI dependencies."""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from .config import settings
from .db import get_session
from .models import Role, Tenant, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
ALGORITHM = "HS256"


# --- Password hashing (PBKDF2; no external crypto dependency) ----------------
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$", 1)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100_000)
    return hmac.compare_digest(dk.hex(), dk_hex)


# --- JWT --------------------------------------------------------------------
def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role.value,
        "email": user.email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


# --- Dependencies -----------------------------------------------------------
def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise cred_exc
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise cred_exc
    user = session.get(User, payload.get("sub"))
    if not user or user.status != "active":
        raise cred_exc
    return user


def get_current_tenant(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Tenant:
    tenant = session.get(Tenant, user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return tenant


def require_roles(*roles: Role):
    """Dependency factory enforcing that the user holds one of the given roles."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles and user.role != Role.SUPER_ADMIN:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user

    return checker
