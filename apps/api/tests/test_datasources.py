"""Conector legado: fuente de datos por BD (solo lectura) → import al RAG."""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

# Una BD "legada" de ejemplo, separada de la app.
_legacy_fd, _legacy_path = tempfile.mkstemp(suffix=".db")
_c = sqlite3.connect(_legacy_path)
_c.execute("CREATE TABLE clientes (id INTEGER, nombre TEXT, monto REAL)")
_c.executemany("INSERT INTO clientes VALUES (?,?,?)", [(1, "ACME", 5000.0), (2, "Globex", 8200.0)])
_c.commit()
_c.close()
LEGACY_DSN = f"sqlite:///{_legacy_path}"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_rejects_non_select(client):
    h = _auth(client)
    r = client.post("/datasources", headers=h, json={
        "name": "x", "dsn": LEGACY_DSN, "query": "DELETE FROM clientes"})
    assert r.status_code == 422


def test_create_test_and_import(client):
    h = _auth(client)
    ds = client.post("/datasources", headers=h, json={
        "name": "Clientes legado", "dsn": LEGACY_DSN,
        "query": "SELECT nombre, monto FROM clientes", "category": "conocimiento"}).json()
    assert ds["id"] and ds["query"].lower().startswith("select")

    test = client.post(f"/datasources/{ds['id']}/test", headers=h).json()
    assert test["ok"] is True and "nombre" in test["columns"]

    imp = client.post(f"/datasources/{ds['id']}/import", headers=h).json()
    assert imp["rows"] == 2
    # El documento importado aparece en el repositorio con su contenido.
    docs = client.get("/documents", headers=h).json()
    assert any(d["filename"] == "Clientes legado.txt" for d in docs)


def test_blocks_dml_in_cte(client):
    h = _auth(client)
    r = client.post("/datasources", headers=h, json={
        "name": "evil", "dsn": LEGACY_DSN,
        "query": "WITH x AS (DELETE FROM clientes RETURNING *) SELECT * FROM x"})
    assert r.status_code == 422


def test_blocks_disallowed_dsn_scheme(client):
    h = _auth(client)
    r = client.post("/datasources", headers=h, json={
        "name": "bad", "dsn": "ftp://host/file", "query": "SELECT 1"})
    assert r.status_code == 422


def test_delete(client):
    h = _auth(client)
    ds = client.post("/datasources", headers=h, json={
        "name": "tmp", "dsn": LEGACY_DSN, "query": "SELECT 1 AS uno"}).json()
    assert client.delete(f"/datasources/{ds['id']}", headers=h).json()["ok"] is True
