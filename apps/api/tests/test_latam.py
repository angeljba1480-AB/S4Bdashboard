"""Multi-country (LATAM) localization tests."""
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


def test_countries_listed(client):
    h = _auth(client)
    cs = client.get("/regional/countries", headers=h).json()
    codes = {c["code"] for c in cs}
    assert {"MX", "CO", "AR", "CL", "PE"} <= codes


def test_region_input_localizes_to_country(client):
    h = _auth(client)
    # default MX -> region label "Estado", with the 32 states
    recs = client.get("/recipes?category=abrir", headers=h).json()
    lic = next(r for r in recs if r["id"] == "licencia_funcionamiento")
    region = next(f for f in lic["inputs"] if f["key"] == "region")
    assert region["label"] == "Estado"
    assert "Jalisco" in region["options"]

    # switch tenant to Colombia -> label "Departamento" with CO divisions
    client.put("/admin/branding", headers=h, json={
        "brand_name": "", "brand_logo_url": "", "brand_color": "", "brand_tagline": "", "country": "CO"})
    recs = client.get("/recipes?category=abrir", headers=h).json()
    lic = next(r for r in recs if r["id"] == "licencia_funcionamiento")
    region = next(f for f in lic["inputs"] if f["key"] == "region")
    assert region["label"] == "Departamento"
    assert "Antioquia" in region["options"]
    # restore
    client.put("/admin/branding", headers=h, json={
        "brand_name": "", "brand_logo_url": "", "brand_color": "", "brand_tagline": "", "country": "MX"})


def test_mexico_only_procedures_hidden_for_other_country(client):
    h = _auth(client)
    mx = client.get("/regional/procedures?country=MX", headers=h).json()
    assert any(p["id"] == "alta_sat" for p in mx)
    co = client.get("/regional/procedures?country=CO", headers=h).json()
    assert all(p["id"] != "alta_sat" for p in co)  # SAT is MX-only


def test_me_includes_country(client):
    h = _auth(client)
    me = client.get("/me", headers=h).json()
    assert me["country"] in ("MX", "CO")
    assert me["country_name"]
