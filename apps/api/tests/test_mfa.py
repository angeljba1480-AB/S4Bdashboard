"""MFA (TOTP): enrolar → verificar → login exige código → respaldo → desactivar."""
from __future__ import annotations

import os
import tempfile

import pyotp
import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, **extra):
    return client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234", **extra})


def _auth(client) -> dict:
    return {"Authorization": f"Bearer {_login(client).json()['access_token']}"}


def test_login_without_mfa_works(client):
    assert _login(client).status_code == 200  # sin MFA, login normal


def test_mfa_enroll_login_and_disable(client):
    h = _auth(client)
    setup = client.post("/auth/mfa/setup", headers=h).json()
    secret = setup["secret"]
    assert setup["otpauth_uri"].startswith("otpauth://") and "MaestroAI" in setup["otpauth_uri"]

    # Código incorrecto en verify → 400.
    assert client.post("/auth/mfa/verify", headers=h, json={"code": "000000"}).status_code == 400

    totp = pyotp.TOTP(secret)
    verify = client.post("/auth/mfa/verify", headers=h, json={"code": totp.now()}).json()
    assert verify["enabled"] is True and len(verify["backup_codes"]) == 8
    backup = verify["backup_codes"][0]

    # Ahora el login SIN código falla con MFA_REQUIRED.
    r = _login(client)
    assert r.status_code == 401 and r.json()["detail"] == "MFA_REQUIRED"

    # Login con código TOTP válido funciona.
    assert _login(client, mfa_code=totp.now()).status_code == 200

    # Login con un código de respaldo funciona (un solo uso).
    assert _login(client, mfa_code=backup).status_code == 200
    # El mismo código de respaldo ya no sirve.
    assert _login(client, mfa_code=backup).status_code == 401

    # Desactivar con un código TOTP válido.
    h2 = {"Authorization": f"Bearer {_login(client, mfa_code=totp.now()).json()['access_token']}"}
    off = client.post("/auth/mfa/disable", headers=h2, json={"code": totp.now()}).json()
    assert off["enabled"] is False
    # Tras desactivar, login normal otra vez.
    assert _login(client).status_code == 200
