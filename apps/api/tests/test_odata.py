"""Lector OData (SAP S/4HANA) de solo lectura → repositorio + RAG."""
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


def test_rows_from_payload_v2_and_v4():
    from app.integrations.odata import _rows_from_payload
    v2 = {"d": {"results": [{"Id": "1"}, {"Id": "2"}], "__next": "https://x/next"}}
    rows, nxt = _rows_from_payload(v2)
    assert len(rows) == 2 and nxt == "https://x/next"
    v4 = {"value": [{"Id": "1"}], "@odata.nextLink": "https://x/n2"}
    rows, nxt = _rows_from_payload(v4)
    assert rows[0]["Id"] == "1" and nxt == "https://x/n2"
    single = {"d": {"Id": "9", "__metadata": {"x": 1}}}
    rows, nxt = _rows_from_payload(single)
    assert rows == [{"Id": "9", "__metadata": {"x": 1}}] and nxt is None


def test_fetch_flattens_and_paginates(monkeypatch):
    """fetch sigue __next y aplana columnas (omite __metadata / objetos anidados)."""
    import httpx
    from app.integrations import odata

    pages = [
        {"d": {"results": [
            {"__metadata": {"u": "x"}, "Cliente": "IMSS", "Venta": 1000, "Nav": {"deferred": 1}},
        ], "__next": "https://sap/next"}},
        {"d": {"results": [{"Cliente": "ALSEA", "Venta": 500}]}},
    ]
    calls = {"i": 0}

    class _Resp:
        def raise_for_status(self): ...
        def json(self):
            p = pages[calls["i"]]; calls["i"] += 1; return p

    class _Client:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): ...
        def get(self, url, **kw): return _Resp()

    monkeypatch.setattr(httpx, "Client", _Client)
    cols, rows = odata.fetch("https://sap/host/Set", auth_type="basic", username="u", secret="p")
    assert "Cliente" in cols and "Venta" in cols
    assert "__metadata" not in cols and "Nav" in cols  # anidado queda como columna vacía
    assert len(rows) == 2  # paginó dos páginas
    assert rows[0][cols.index("Cliente")] == "IMSS"


def test_odata_source_crud_and_import(client, monkeypatch):
    h = _auth(client)
    created = client.post("/datasources/odata", headers=h, json={
        "name": "SAP Ventas", "base_url": "https://sap/host/sap/opu/odata/sap/SRV/VentasSet",
        "auth_type": "basic", "username": "RFC_USER", "secret": "s3cr3t",
        "odata_filter": "Anio eq 2025", "area": "Finanzas"}).json()
    assert created["base_url"].endswith("VentasSet") and created["auth_type"] == "basic"
    lst = client.get("/datasources/odata", headers=h).json()
    assert any(o["id"] == created["id"] for o in lst)
    # el secreto se revela cifrado/descifrado (auditado), nunca en el listado
    assert "s3cr3t" not in str(lst)
    assert client.get(f"/datasources/odata/{created['id']}/reveal", headers=h).json()["secret"] == "s3cr3t"

    # test + import con fetch parcheado (sin red)
    import app.routers.datasources as ds
    monkeypatch.setattr(ds.odata_client, "fetch",
                        lambda *a, **k: (["Cliente", "Venta"], [("IMSS", 1000), ("ALSEA", 500)]))
    t = client.post(f"/datasources/odata/{created['id']}/test", headers=h).json()
    assert t["ok"] is True and "Cliente" in t["columns"]
    imp = client.post(f"/datasources/odata/{created['id']}/import", headers=h).json()
    assert imp["rows"] == 2 and imp["id"]
    # quedó como documento en el repositorio (indexado al RAG)
    docs = client.get("/documents", headers=h).json()
    assert any("SAP Ventas" in d["filename"] for d in docs)
    assert client.delete(f"/datasources/odata/{created['id']}", headers=h).json()["ok"] is True
