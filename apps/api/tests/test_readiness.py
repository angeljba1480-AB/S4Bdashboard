"""Autochequeo de preparación: /admin/readiness reporta huecos + guía de arreglo."""
from __future__ import annotations

import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_readiness_lists_checks_with_summary(client):
    r = client.get("/admin/readiness", headers=_auth(client)).json()
    assert "summary" in r and "checks" in r
    keys = {c["key"] for c in r["checks"]}
    # Capacidades clave cubiertas por el autochequeo.
    for k in ("model_open", "model_premium", "n8n", "actions", "finetune", "mfa"):
        assert k in keys
    assert sum(r["summary"].values()) == len(r["checks"])


def test_readiness_missing_has_fix_guide(client):
    r = client.get("/admin/readiness", headers=_auth(client)).json()
    # Sin proveedores configurados, los huecos traen pasos de cómo resolverlo.
    gaps = [c for c in r["checks"] if c["status"] != "ok"]
    assert gaps, "Se esperaba al menos un hueco en entorno de pruebas"
    for c in gaps:
        assert c["fix"] and isinstance(c["fix"]["steps"], list) and c["fix"]["steps"]
