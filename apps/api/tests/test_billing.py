"""Subscription / seats billing tests (setup + annual prepaid by seats)."""
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
    tok = client.post("/auth/login", json={"email": "admin@s4b.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_billing_summary(client):
    h = _auth(client)
    b = client.get("/admin/billing", headers=h).json()
    assert "seats_licensed" in b and "seats_used" in b
    assert b["seats_available"] == b["seats_licensed"] - b["seats_used"]
    assert b["prod_deploy_price_mxn"] > 0


def test_seat_limit_enforced(client):
    h = _auth(client)
    # tighten seats to exactly what's used, then adding a user must fail with 402
    used = client.get("/admin/billing", headers=h).json()["seats_used"]
    client.put("/admin/billing", headers=h, json={"seats_licensed": used})
    r = client.post("/admin/users", headers=h, json={
        "email": "extra@s4b.mx", "name": "Extra", "role": "user"})
    assert r.status_code == 402

    # raise seats, now it works
    client.put("/admin/billing", headers=h, json={"seats_licensed": used + 1})
    ok = client.post("/admin/users", headers=h, json={
        "email": "extra@s4b.mx", "name": "Extra", "role": "user"})
    assert ok.status_code == 201


def test_plans_and_estimate(client):
    h = _auth(client)
    plans = client.get("/admin/plans", headers=h).json()
    ids = {p["id"] for p in plans["plans"]}
    assert {"emprende", "negocio", "empresa"} <= ids
    assert plans["currency"] == "MXN"

    est = client.get("/admin/plans/estimate?plan=negocio&seats=10", headers=h).json()
    assert est["seats"] == 10
    assert est["first_year_total"] == est["setup_fee"] + est["annual_total"]

    # gobierno has no public price -> 404
    assert client.get("/admin/plans/estimate?plan=gobierno&seats=5", headers=h).status_code == 404


def test_expired_subscription_blocks_new_users(client):
    h = _auth(client)
    client.put("/admin/billing", headers=h, json={"seats_licensed": 50, "subscription_status": "expired"})
    r = client.post("/admin/users", headers=h, json={
        "email": "blocked@s4b.mx", "name": "Blocked", "role": "user"})
    assert r.status_code == 402
    client.put("/admin/billing", headers=h, json={"subscription_status": "active"})
