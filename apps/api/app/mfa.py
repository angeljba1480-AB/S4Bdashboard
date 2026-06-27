"""MFA (segundo factor) por TOTP — blueprint «RBAC + MFA».

El secreto TOTP se guarda cifrado (AES-256-GCM por tenant). Se generan códigos de
respaldo de un solo uso (se guardan hasheados). El login exige el código cuando el
usuario tiene MFA activo.
"""
from __future__ import annotations

import hashlib
import secrets as _secrets

import pyotp

from .security.crypto import decrypt, encrypt

ISSUER = "MaestroAI"
N_BACKUP = 8


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(str(code).strip().replace(" ", ""), valid_window=1)
    except Exception:
        return False


# --- secret at rest (cifrado por tenant) ------------------------------------
def encrypt_secret(secret: str, tenant_id: str) -> str:
    return encrypt(secret, tenant_id)


def decrypt_secret(enc: str, tenant_id: str) -> str:
    return decrypt(enc, tenant_id) if enc else ""


# --- códigos de respaldo (un solo uso) --------------------------------------
def _hash(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def gen_backup_codes() -> tuple[list[str], str]:
    """Devuelve (códigos en claro para mostrar UNA vez, blob de hashes a guardar)."""
    codes = [f"{_secrets.token_hex(2).upper()}-{_secrets.token_hex(2).upper()}" for _ in range(N_BACKUP)]
    blob = ",".join(_hash(c) for c in codes)
    return codes, blob


def consume_backup_code(blob: str, code: str) -> tuple[bool, str]:
    """Si `code` es un código de respaldo válido, lo elimina del blob.
    Devuelve (ok, blob_actualizado)."""
    if not blob or not code:
        return False, blob
    hashes = [h for h in blob.split(",") if h]
    h = _hash(code)
    if h in hashes:
        hashes.remove(h)
        return True, ",".join(hashes)
    return False, blob


def check_second_factor(secret_enc: str, backup_blob: str, tenant_id: str, code: str) -> tuple[bool, str]:
    """Valida TOTP o un código de respaldo. Devuelve (ok, backup_blob_actualizado)."""
    secret = decrypt_secret(secret_enc, tenant_id)
    if verify_totp(secret, code):
        return True, backup_blob
    return consume_backup_code(backup_blob, code)
