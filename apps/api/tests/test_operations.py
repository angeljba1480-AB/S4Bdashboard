"""Operations dashboard + account/license tests."""
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


def test_operations_counts_cases_and_tokens(client):
    h = _auth(client)
    # run a case so it shows up with tokens
    start = client.post("/recipes/cotizacion/start", headers=h, json={
        "inputs": {"cliente": "Ana", "concepto": "logo", "monto": "800"}}).json()
    client.post(f"/recipes/runs/{start['id']}/approve", headers=h)

    ops = client.get("/usage/operations", headers=h).json()
    assert ops["cases"]["total"] >= 1
    assert ops["tokens"]["total"] >= 1
    assert "casos" in ops["tokens"]["by_source"]
    assert any(c["id"] == start["id"] for c in ops["recent_cases"])


def test_account_shows_user_and_company_licenses(client):
    h = _auth(client)
    acc = client.get("/account", headers=h).json()
    assert acc["user"]["email"] == "admin@maestroai.mx"
    assert acc["license"]["seat_assigned"] is True
    assert acc["company"]["seats_licensed"] >= acc["company"]["seats_used"]
    assert any(u["email"] == "admin@maestroai.mx" for u in acc["licensed_users"])
