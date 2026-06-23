"""Encryption at rest — AES-256-GCM with a KMS abstraction (blueprint §5).

Per-tenant data keys are derived from a master KMS key (HKDF-like via PBKDF2),
so each tenant's documents are encrypted under a distinct key. Ciphertext is
self-describing: ``v{version}:{tenant_key_id}:{nonce}:{ct}`` (all base64),
which lets keys rotate (bump ``KMS_KEY_VERSION``) without losing old data as
long as the master key is retained.

In production the master key would live in AWS KMS / GCP KMS / Vault and data
keys would be wrapped, not derived — but the call sites stay identical.
"""
from __future__ import annotations

import base64
import hashlib

from Crypto.Cipher import AES

from ..config import settings

_PREFIX = "enc"


def _derive_key(tenant_key_id: str, version: int) -> bytes:
    """Derive a 32-byte data key for a tenant + key version from the master key."""
    salt = f"{tenant_key_id}:v{version}".encode()
    return hashlib.pbkdf2_hmac("sha256", settings.effective_kms_key.encode(), salt, 200_000, dklen=32)


def encrypt(plaintext: str, tenant_key_id: str) -> str:
    """Encrypt plaintext for a tenant. Returns a self-describing token."""
    if not settings.encryption_enabled or plaintext is None:
        return plaintext
    version = settings.kms_key_version
    key = _derive_key(tenant_key_id, version)
    cipher = AES.new(key, AES.MODE_GCM)
    ct, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
    blob = cipher.nonce + tag + ct
    return f"{_PREFIX}:v{version}:{tenant_key_id}:{base64.b64encode(blob).decode()}"


def decrypt(token: str, tenant_key_id: str | None = None) -> str:
    """Decrypt a token produced by :func:`encrypt`. Plaintext passes through."""
    if not token or not token.startswith(f"{_PREFIX}:"):
        return token  # not encrypted (e.g. legacy/plaintext rows)
    try:
        _, vraw, key_id, b64 = token.split(":", 3)
        version = int(vraw.lstrip("v"))
        key = _derive_key(key_id, version)
        blob = base64.b64decode(b64)
        nonce, tag, ct = blob[:16], blob[16:32], blob[32:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ct, tag).decode("utf-8")
    except (ValueError, KeyError):
        return token


def is_encrypted(token: str | None) -> bool:
    return bool(token) and token.startswith(f"{_PREFIX}:")
