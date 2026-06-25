"""Navigable flowcharts: catalog + graph integrity."""
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


def test_lists_base_flowcharts(client):
    ids = {f["id"] for f in client.get("/flowcharts", headers=_auth(client)).json()}
    assert {"arquitectura_segura", "prompt_rag_finetuning", "pipeline_finetuning", "caso_de_uso"} <= ids


def test_flowchart_graph_is_valid(client):
    h = _auth(client)
    for fid in [f["id"] for f in client.get("/flowcharts", headers=h).json()]:
        flow = client.get(f"/flowcharts/{fid}", headers=h).json()
        node_ids = {n["id"] for n in flow["nodes"]}
        assert flow["start"] in node_ids
        for n in flow["nodes"]:
            if n.get("next"):
                assert n["next"] in node_ids
            for b in n.get("branches", []):
                assert b["to"] in node_ids


def test_unknown_flowchart_404(client):
    assert client.get("/flowcharts/nope", headers=_auth(client)).status_code == 404


def test_requires_auth(client):
    assert client.get("/flowcharts").status_code == 401
