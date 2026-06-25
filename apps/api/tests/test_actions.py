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


def test_unknown_action_404(client):
    h = _auth(client)
    assert client.post("/actions/run", headers=h, json={"action": "nope.x", "params": {}}).status_code == 404
