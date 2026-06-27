"""Google/Microsoft action toolkit: approval gate + 'permitir siempre' grants."""
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


@pytest.fixture(autouse=True)
def _mock_exec(monkeypatch):
    from app.integrations import actions_exec, token_store
    monkeypatch.setattr(token_store, "get_valid_access_token", lambda *a, **k: "fake-token")
    monkeypatch.setattr(actions_exec, "execute", lambda action, token, params: f"OK:{action}")


def test_catalog_lists_actions(client):
    acts = {a["id"]: a for a in client.get("/actions", headers=_auth(client)).json()}
    assert "gmail.send" in acts and acts["gmail.send"]["write"] is True
    assert "outlook.send" in acts and acts["teams.post"]["provider"] == "microsoft"


def test_write_action_requires_approval_then_executes(client):
    h = _auth(client)
    run = client.post("/actions/run", headers=h, json={
        "action": "gmail.send", "params": {"to": "a@b.com", "subject": "hi", "body": "x"}}).json()
    assert run["status"] == "pending"
    rid = run["request"]["id"]

    done = client.post(f"/actions/requests/{rid}/approve", headers=h).json()
    assert done["request"]["status"] == "executed" and done["request"]["result"] == "OK:gmail.send"


def test_permitir_siempre_auto_executes_next_time(client):
    h = _auth(client)
    # Approve with always=true → creates a standing grant.
    run = client.post("/actions/run", headers=h, json={"action": "gcal.create_event", "params": {"summary": "Junta"}}).json()
    client.post(f"/actions/requests/{run['request']['id']}/approve?always=true", headers=h)

    grants = {g["action"] for g in client.get("/actions/grants", headers=h).json()}
    assert "gcal.create_event" in grants

    # Next run of the same action executes immediately (no pending).
    again = client.post("/actions/run", headers=h, json={"action": "gcal.create_event", "params": {"summary": "Otra"}}).json()
    assert again["status"] == "done" and again["request"]["status"] == "executed"

    # Revoke → back to requiring approval.
    assert client.delete("/actions/grants/gcal.create_event", headers=h).json()["ok"] is True
    after = client.post("/actions/run", headers=h, json={"action": "gcal.create_event", "params": {"summary": "Z"}}).json()
    assert after["status"] == "pending"


def test_reject(client):
    h = _auth(client)
    run = client.post("/actions/run", headers=h, json={"action": "outlook.send", "params": {"to": "a@b.com"}}).json()
    rej = client.post(f"/actions/requests/{run['request']['id']}/reject", headers=h).json()
    assert rej["request"]["status"] == "rejected"


def test_read_action_runs_without_approval(client):
    h = _auth(client)
    run = client.post("/actions/run", headers=h, json={
        "action": "gcal.list", "params": {"days": "7"}}).json()
    assert run["status"] == "done" and run["request"]["status"] == "executed"


def test_read_actions_in_catalog(client):
    acts = {a["id"]: a for a in client.get("/actions", headers=_auth(client)).json()}
    for rid in ("gsheets.read", "gcal.list", "mscal.list", "onedrive.list",
                "excel.read", "sharepoint.search"):
        assert rid in acts and acts[rid]["write"] is False
    # Excel append es escritura (con aprobación).
    assert acts["excel.append"]["write"] is True


# --- agente de acciones (el modelo ejecuta los pasos en las herramientas) ----
class _Conn:
    def __init__(self, provider):
        self.provider = provider


@pytest.fixture
def _google_connected(monkeypatch):
    from app.integrations import token_store
    monkeypatch.setattr(token_store, "list_connections", lambda *a, **k: [_Conn("google")])


def test_agent_requires_connection(client, monkeypatch):
    from app.integrations import token_store
    monkeypatch.setattr(token_store, "list_connections", lambda *a, **k: [])
    r = client.post("/actions/agent", headers=_auth(client), json={"instruction": "envía un correo"})
    assert r.status_code == 400


def test_agent_runs_reads_and_queues_writes(client, _google_connected):
    h = _auth(client)
    # Lectura: "próximos eventos" → gcal.list se ejecuta al momento.
    r = client.post("/actions/agent", headers=h, json={"instruction": "muéstrame mis próximos eventos"}).json()
    assert r["source"] in ("heurística", "modelo")
    read_steps = [s for s in r["steps"] if s["action"] == "gcal.list"]
    assert read_steps and read_steps[0]["step_status"] == "ejecutado"

    # Escritura: "envía un correo" → gmail.send queda pendiente de aprobación.
    r2 = client.post("/actions/agent", headers=h, json={"instruction": "envía un correo a Juan"}).json()
    send_steps = [s for s in r2["steps"] if s["action"] == "gmail.send"]
    assert send_steps and send_steps[0]["step_status"] == "pendiente_aprobación"


def test_agent_auto_approve_executes_writes(client, _google_connected):
    h = _auth(client)
    r = client.post("/actions/agent", headers=h, json={
        "instruction": "envía un correo a Juan", "auto_approve": True}).json()
    send_steps = [s for s in r["steps"] if s["action"] == "gmail.send"]
    assert send_steps and send_steps[0]["step_status"] == "ejecutado"


def test_unknown_action_404(client):
    h = _auth(client)
    assert client.post("/actions/run", headers=h, json={"action": "nope.x", "params": {}}).status_code == 404
