"""Document repository: areas, category catalog, treatment override, RAG toggle."""
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


def test_category_catalog_seeded(client):
    cats = client.get("/documents/categories", headers=_auth(client)).json()
    keys = {c["key"] for c in cats}
    assert {"propuesta_comercial", "licitacion_madre", "certificacion_iso", "conocimiento"} <= keys
    assert all(c["system"] for c in cats if c["key"] == "propuesta_comercial")


def test_upload_with_area_category_and_treatment_override(client):
    h = _auth(client)
    r = client.post("/documents/upload", headers=h, data={
        "filename": "propuesta_acme.txt",
        "text": "Propuesta comercial para ACME. Alcance y precios.",
        "area": "Ventas",
        "category": "propuesta_comercial",
        "sensitivity": "confidential",
    })
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["area"] == "Ventas"
    assert d["category"] == "propuesta_comercial"
    assert d["category_label"] == "Propuesta comercial"
    assert d["sensitivity"] == "confidential"  # override respected over auto-classify


def test_upload_auto_creates_missing_category(client):
    h = _auth(client)
    r = client.post("/documents/upload", headers=h, data={
        "filename": "manual.txt", "text": "Manual interno de operaciones.",
        "category": "Manual de operaciones",
    }).json()
    assert r["category"] == "manual_de_operaciones"
    keys = {c["key"] for c in client.get("/documents/categories", headers=h).json()}
    assert "manual_de_operaciones" in keys


def test_retag_and_filter(client):
    h = _auth(client)
    doc = client.post("/documents/upload", headers=h, data={
        "filename": "x.txt", "text": "texto", "area": "RH", "category": "otro",
    }).json()
    upd = client.patch(f"/documents/{doc['id']}", headers=h, json={
        "category": "contrato_empleado", "sensitivity": "restricted",
    }).json()
    assert upd["category"] == "contrato_empleado" and upd["sensitivity"] == "restricted"

    filtered = client.get("/documents?area=RH", headers=h).json()
    assert any(d["id"] == doc["id"] for d in filtered)
    none = client.get("/documents?area=Inexistente", headers=h).json()
    assert all(d["id"] != doc["id"] for d in none)


def test_create_and_delete_category(client):
    h = _auth(client)
    c = client.post("/documents/categories", headers=h, json={"label": "Plantillas legales"}).json()
    assert c["key"] == "plantillas_legales" and c["system"] is False
    assert client.delete(f"/documents/categories/{c['id']}", headers=h).json()["ok"] is True

    # System categories are protected.
    sys_cat = next(x for x in client.get("/documents/categories", headers=h).json() if x["system"])
    assert client.delete(f"/documents/categories/{sys_cat['id']}", headers=h).status_code == 400


def test_delete_document(client):
    h = _auth(client)
    doc = client.post("/documents/upload", headers=h, data={"filename": "tmp.txt", "text": "borrar"}).json()
    assert client.delete(f"/documents/{doc['id']}", headers=h).json()["ok"] is True
    assert all(d["id"] != doc["id"] for d in client.get("/documents", headers=h).json())


def test_recipe_grounds_only_in_its_category(client):
    """A recipe with rag_category pulls company context from that category only."""
    h = _auth(client)
    client.post("/documents/upload", headers=h, data={
        "filename": "plantilla_prop.txt",
        "text": "PLANTILLA ZXQW de propuesta comercial: estructura, alcance y precios.",
        "category": "propuesta_comercial",
    })
    client.post("/documents/upload", headers=h, data={
        "filename": "contrato_zxqw.txt",
        "text": "PLANTILLA ZXQW de contrato laboral confidencial.",
        "category": "contrato_empleado",
    })
    start = client.post("/recipes/propuesta_comercial/start", headers=h, json={
        "inputs": {"cliente": "ACME", "servicio": "CRM"},
    }).json()
    rag_titles = {f["title"] for f in start["draft"].get("fuentes", []) if f.get("source") == "empresa-rag"}
    assert "plantilla_prop.txt" in rag_titles
    assert "contrato_zxqw.txt" not in rag_titles  # other category excluded


def test_chat_without_context_has_no_citations(client):
    h = _auth(client)
    # Seed a document so "with context" would normally retrieve something.
    client.post("/documents/upload", headers=h, data={
        "filename": "ctx.txt", "text": "Información empresarial de referencia para el RAG.",
    })
    agent_id = client.get("/agents", headers=h).json()[0]["id"]

    no_ctx = client.post("/chat", headers=h, json={
        "agent_id": agent_id, "prompt": "Hola, ¿cómo estás?", "use_rag": False,
    }).json()
    assert no_ctx["citations"] == []

    with_ctx = client.post("/chat", headers=h, json={
        "agent_id": agent_id, "prompt": "información empresarial de referencia", "use_rag": True,
    }).json()
    assert len(with_ctx["citations"]) >= 1
