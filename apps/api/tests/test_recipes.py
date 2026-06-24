"""Use-case recipe engine tests (pre-fill + approval gates)."""
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


def test_catalog_lists_two_use_cases(client):
    r = client.get("/recipes", headers=_auth(client)).json()
    ids = {x["id"] for x in r}
    assert {"licitacion", "correo_agenda"} <= ids


def test_licitacion_prefills_and_approves(client):
    h = _auth(client)
    # upload a tender-like document so retrieval has content
    doc = client.post("/documents/upload", headers=h, data={
        "filename": "licitacion.txt",
        "text": ("Bases de la licitación.\n"
                 "Requisito 1: El proveedor deberá acreditar 3 años de experiencia.\n"
                 "Requisito 2: Presentar fianza de garantía vigente.\n"
                 "Criterio de evaluación: propuesta técnica y económica."),
    }).json()

    start = client.post("/recipes/licitacion/start", headers=h, json={
        "inputs": {"document_id": doc["id"], "empresa": "ACME SA"},
    }).json()
    assert start["status"] == "draft"  # no connections needed
    assert start["draft"]["campos"], "debe pre-llenar requisitos"
    assert start["draft"]["route"] == "local"

    done = client.post(f"/recipes/runs/{start['id']}/approve", headers=h).json()
    assert done["status"] == "completed"
    assert "RESPUESTA A LICITACIÓN" in done["result"]["documento"]


def test_correo_agenda_without_connection_prompts_to_connect(client):
    """With no mailbox connected, the case runs but asks the user to connect."""
    h = _auth(client)
    start = client.post("/recipes/correo_agenda/start", headers=h, json={
        "inputs": {"email": "user@empresa.mx", "output": "Resumen diario"},
    }).json()
    assert start["status"] == "draft"
    assert start["draft"].get("needs_oauth") is True

    done = client.post(f"/recipes/runs/{start['id']}/approve", headers=h).json()
    assert done["status"] == "completed"
    assert "Conecta tu correo" in done["result"]["message"]


def test_correo_agenda_with_connected_mailbox_summarizes(client, monkeypatch):
    """With a connected mailbox (mocked fetch), the case produces a real summary."""
    import time

    from sqlmodel import Session

    from app.db import engine
    from app.integrations import mailbox
    from app.models import OAuthToken, Tenant
    from app.security.crypto import encrypt

    h = _auth(client)
    me = client.get("/me", headers=h).json()
    with Session(engine) as s:
        tenant = s.get(Tenant, me["tenant_id"])
        s.add(OAuthToken(
            tenant_id=me["tenant_id"], user_id=me["id"], provider="microsoft",
            identifier="user@empresa.mx",
            access_token_enc=encrypt("fake-access", tenant.kms_key_id),
            expires_at=time.time() + 3600, status="active",
        ))
        s.commit()

    monkeypatch.setattr(mailbox, "fetch", lambda provider, token: {
        "messages": [{"from": "Ana", "subject": "Pago", "received": "", "preview": "Favor de revisar la factura", "unread": True}],
        "events": [{"subject": "Junta", "start": "2026-06-24T10:00:00", "end": "", "location": "Sala 2"}],
    })

    start = client.post("/recipes/correo_agenda/start", headers=h, json={
        "inputs": {"email": "user@empresa.mx", "output": "Resumen diario"},
    }).json()
    assert start["status"] == "draft"
    assert start["draft"].get("connected") is True

    done = client.post(f"/recipes/runs/{start['id']}/approve", headers=h).json()
    assert done["status"] == "completed"
    assert done["result"].get("documento"), "debe entregar un resumen generado"


def test_oauth_providers_listed(client):
    r = client.get("/oauth/providers", headers=_auth(client)).json()
    provs = {p["provider"] for p in r["providers"]}
    assert {"microsoft", "google"} <= provs


def test_missing_required_input_422(client):
    h = _auth(client)
    r = client.post("/recipes/licitacion/start", headers=h, json={"inputs": {"empresa": "X"}})
    assert r.status_code == 422


def test_categories_and_filter(client):
    h = _auth(client)
    cats = client.get("/recipes/categories", headers=h).json()
    ids = {c["id"] for c in cats}
    assert {"crecer", "abrir", "cumplimiento", "operaciones", "dia_a_dia"} <= ids
    assert all("count" in c for c in cats)
    filtered = client.get("/recipes?category=operaciones", headers=h).json()
    assert filtered and all(r["category"] == "operaciones" for r in filtered)


def test_generic_recipe_prefills_and_runs(client):
    h = _auth(client)
    start = client.post("/recipes/cotizacion/start", headers=h, json={
        "inputs": {"cliente": "Juan", "concepto": "10 playeras", "monto": "1500"},
    }).json()
    assert start["status"] == "draft"
    assert "Juan" in start["draft"]["plan"]
    done = client.post(f"/recipes/runs/{start['id']}/approve", headers=h).json()
    assert done["status"] == "completed"


def test_generic_recipe_generates_content_via_router(client):
    h = _auth(client)
    start = client.post("/recipes/propuesta_comercial/start", headers=h, json={
        "inputs": {"cliente": "ACME", "servicio": "consultoría", "precio": "50000"},
    }).json()
    assert start["draft"]["contenido"], "el LLM (mock offline) debe generar contenido"
    assert start["draft"]["route"] in ("local", "vpc", "open", "premium")
    done = client.post(f"/recipes/runs/{start['id']}/approve", headers=h).json()
    assert done["status"] == "completed"
    assert done["result"]["output"]


def test_generic_recipe_routes_sensitive_input_privately(client):
    h = _auth(client)
    start = client.post("/recipes/contrato_simple/start", headers=h, json={
        "inputs": {"parte_a": "Mi Empresa SA", "parte_b": "Cliente con RFC BBM930101XYZ",
                   "objeto": "servicios y CURP BEAA900101HDFLNN09"},
    }).json()
    # PII present -> never external by default
    assert start["draft"]["route"] in ("local", "vpc")


def test_region_aware_recipe_localizes_and_warns(client):
    h = _auth(client)
    # region is country-localized; municipio is text — both required
    start = client.post("/recipes/licencia_funcionamiento/start", headers=h, json={
        "inputs": {"giro": "cafetería", "region": "Jalisco", "municipio": "Guadalajara"},
    }).json()
    assert "Guadalajara" in start["draft"]["plan"]
    assert start["draft"]["region_aware"] is True
    assert "autoridad local" in start["draft"]["summary"]


def test_region_recipe_requires_region(client):
    h = _auth(client)
    r = client.post("/recipes/licencia_funcionamiento/start", headers=h, json={
        "inputs": {"giro": "cafetería", "municipio": "Guadalajara"},
    })
    assert r.status_code == 422  # region required


def test_propose_use_case(client):
    h = _auth(client)
    r = client.post("/recipes/propose", headers=h, json={
        "title": "Recordatorio de pagos a proveedores", "category": "operaciones",
    }).json()
    assert r["status"] == "proposed"
    titles = [p["title"] for p in client.get("/recipes/proposals", headers=h).json()]
    assert "Recordatorio de pagos a proveedores" in titles


def test_curate_proposal_into_catalog(client):
    h = _auth(client)
    prop = client.post("/recipes/propose", headers=h, json={
        "title": "Carta de cobranza", "category": "operaciones",
        "description": "Genera una carta para cobrar a un cliente moroso.",
    }).json()

    curated = client.post(f"/recipes/proposals/{prop['id']}/curate", headers=h, json={
        "inputs": [{"key": "cliente", "type": "text", "label": "Cliente", "required": True},
                   {"key": "monto", "type": "text", "label": "Monto"}],
        "prompt": "Carta de cobranza para {cliente} por {monto}.",
        "produces": "una carta de cobranza",
    }).json()
    assert curated["status"] == "curated"
    slug = curated["slug"]

    # now it appears in the catalog and can run end-to-end
    catalog_ids = {r["id"] for r in client.get("/recipes", headers=h).json()}
    assert slug in catalog_ids

    start = client.post(f"/recipes/{slug}/start", headers=h, json={
        "inputs": {"cliente": "Pedro", "monto": "2000"},
    }).json()
    assert "Pedro" in start["draft"]["plan"]
    done = client.post(f"/recipes/runs/{start['id']}/approve", headers=h).json()
    assert done["status"] == "completed"

    # proposal now marked curated
    statuses = {p["id"]: p["status"] for p in client.get("/recipes/proposals", headers=h).json()}
    assert statuses[prop["id"]] == "curated"


def test_export_run_pdf_and_md(client):
    h = _auth(client)
    start = client.post("/recipes/cotizacion/start", headers=h, json={
        "inputs": {"cliente": "Marta", "concepto": "servicio", "monto": "999"},
    }).json()
    client.post(f"/recipes/runs/{start['id']}/approve", headers=h)

    pdf = client.get(f"/recipes/runs/{start['id']}/export?format=pdf", headers=h)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"

    md = client.get(f"/recipes/runs/{start['id']}/export?format=md", headers=h)
    assert md.status_code == 200
    assert "Marta" in md.text


def test_reject_proposal(client):
    h = _auth(client)
    prop = client.post("/recipes/propose", headers=h, json={"title": "Caso a rechazar"}).json()
    r = client.post(f"/recipes/proposals/{prop['id']}/reject", headers=h).json()
    assert r["status"] == "rejected"
