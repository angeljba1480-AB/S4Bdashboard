"""Navigable audit: filters, pagination and stats aggregates."""
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


def _seed_events(client, h):
    # Upload a doc (audit: upload) and chat (audit: chat) to generate events.
    client.post("/documents/upload", headers=h, data={"filename": "a.txt", "text": "hola mundo"})
    agent_id = client.get("/agents", headers=h).json()[0]["id"]
    client.post("/chat", headers=h, json={"agent_id": agent_id, "prompt": "hola", "use_rag": False})


def test_audit_stats_and_filters(client):
    h = _auth(client)
    _seed_events(client, h)

    stats = client.get("/audit/stats", headers=h).json()
    assert stats["total"] >= 2
    assert "upload" in stats["by_event"] and "chat" in stats["by_event"]
    assert "upload" in stats["event_types"]
    assert isinstance(stats["total_cost"], (int, float))

    # Filter by event type.
    uploads = client.get("/audit?event_type=upload", headers=h).json()
    assert uploads and all(e["event_type"] == "upload" for e in uploads)

    # Search in reason.
    found = client.get("/audit?q=clasificado", headers=h).json()
    assert all("clasificad" in (e["reason"] or "").lower() for e in found)


def test_audit_pagination(client):
    h = _auth(client)
    page = client.get("/audit?limit=1&offset=0", headers=h).json()
    assert len(page) <= 1
    # offset beyond data returns empty
    empty = client.get("/audit?limit=1&offset=100000", headers=h).json()
    assert empty == []


def test_audit_detail_fields_present(client):
    h = _auth(client)
    rows = client.get("/audit?limit=5", headers=h).json()
    assert rows and "request_id" in rows[0] and "event_metadata" in rows[0]
