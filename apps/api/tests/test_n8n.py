"""n8n workflow integration tests."""
from __future__ import annotations

import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

import app.integrations.n8n as n8n  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@s4b.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_run_simulated_when_n8n_disabled(client):
    r = client.post("/workflows/ingesta/run", headers=_auth(client)).json()
    assert r["engine"] == "simulado"
    assert r["status"] == "simulated"
    assert r["run_id"]


def test_run_triggers_n8n_when_enabled(client, monkeypatch):
    def fake_trigger(workflow_id, payload, webhook_path=None):
        assert payload["workflow_id"] == "rag"
        return n8n.WorkflowRun(triggered=True, status="completed", detail="n8n 200",
                               response={"ok": True})

    # Patch the symbol imported into the router module.
    import app.routers.workflows as wf
    monkeypatch.setattr(wf, "trigger_workflow", fake_trigger)

    r = client.post("/workflows/rag/run", headers=_auth(client)).json()
    assert r["engine"] == "n8n"
    assert r["status"] == "completed"
    assert r["response"] == {"ok": True}


def test_unknown_workflow_404(client):
    assert client.post("/workflows/nope/run", headers=_auth(client)).status_code == 404
