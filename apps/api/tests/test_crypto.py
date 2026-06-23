"""Encryption-at-rest unit tests."""
from __future__ import annotations

from app.security.crypto import decrypt, encrypt, is_encrypted


def test_roundtrip():
    token = encrypt("Contrato confidencial BBVA", "tnt_abc")
    assert is_encrypted(token)
    assert "Contrato" not in token  # ciphertext, not plaintext
    assert decrypt(token, "tnt_abc") == "Contrato confidencial BBVA"


def test_per_tenant_keys_isolate():
    token = encrypt("secreto", "tnt_a")
    # Wrong tenant key id cannot recover plaintext (returns token unchanged).
    assert decrypt(token.replace("tnt_a", "tnt_b"), "tnt_b") != "secreto"


def test_plaintext_passthrough():
    assert decrypt("texto plano no cifrado") == "texto plano no cifrado"
    assert not is_encrypted("texto plano")
