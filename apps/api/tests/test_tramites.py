"""Curated trámites KB (layers: country/state/company) + grounding tests."""
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


def test_curated_search_scoped_by_country(client):
    h = _auth(client)
    mx = client.get("/tramites?q=rfc", headers=h).json()
    assert any(t["id"] == "mx_rfc" for t in mx)
    # Colombia scope should not return the Mexican SAT/RFC entry
    co = client.get("/tramites?q=rfc&country=CO", headers=h).json()
    assert all(t["id"] != "mx_rfc" for t in co)


def test_company_layer_requires_paying_and_ranks_first(client):
    h = _auth(client)
    created = client.post("/tramites", headers=h, json={
        "title": "Política interna de facturación",
        "authority": "Mi Empresa", "keywords": ["factura", "facturación"],
        "requisitos": ["Orden de compra"], "pasos": ["Generar CFDI"],
    })
    assert created.status_code == 201

    res = client.get("/tramites?q=facturación", headers=h).json()
    assert res[0]["source"] == "empresa"     # company-private ranks first
    assert res[0]["title"] == "Política interna de facturación"


def test_company_tramite_blocked_when_subscription_inactive(client):
    h = _auth(client)
    client.put("/admin/billing", headers=h, json={"subscription_status": "expired"})
    r = client.post("/tramites", headers=h, json={"title": "X"})
    assert r.status_code == 402
    client.put("/admin/billing", headers=h, json={"subscription_status": "active"})


def test_company_rag_layer_from_documents(client):
    h = _auth(client)
    # upload a company doc -> becomes part of the company MCP via RAG
    client.post("/documents/upload", headers=h, data={
        "filename": "manual_interno.txt",
        "text": "Procedimiento Zafiro de reembolso de viáticos: adjuntar tickets y aprobar con gerente."})
    res = client.get("/tramites?q=Zafiro%20reembolso%20viáticos&rag=true", headers=h).json()
    assert any(t.get("source") == "empresa-rag" for t in res)


def test_import_document_to_company_tramite(client):
    h = _auth(client)
    doc = client.post("/documents/upload", headers=h, data={
        "filename": "proceso_compras.txt",
        "text": ("Proceso de compras\n"
                 "Requisito: presentar orden de compra firmada\n"
                 "Requisito: adjuntar identificación del proveedor\n"
                 "1. Solicita cotización\n2. Registra la orden\n3. Paga al proveedor")}).json()
    imported = client.post("/tramites/import", headers=h, json={"document_id": doc["id"]}).json()
    assert imported["source"] == "empresa"
    assert imported["requisitos"]            # extracted requisitos
    assert imported["pasos"]                 # extracted pasos
    # now it grounds searches (matches its extracted keywords, e.g. "compras")
    res = client.get("/tramites?q=compras", headers=h).json()
    assert any(t["source"] == "empresa" and "proceso" in t["title"].lower() for t in res)


def test_recipe_prefill_grounds_on_kb(client):
    h = _auth(client)
    start = client.post("/recipes/rfc_alta/start", headers=h, json={
        "inputs": {"actividad": "venta de ropa", "regimen": "RESICO"}}).json()
    # grounding should cite curated sources (SAT among them)
    fuentes = start["draft"].get("fuentes", [])
    assert any("SAT" in (f.get("authority") or "") or "RFC" in (f.get("title") or "") for f in fuentes)
