"""Historial de conversaciones del chat: listar, abrir y borrar."""
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


def test_history_list_open_delete(client):
    h = _auth(client)
    agent_id = client.get("/agents", headers=h).json()[0]["id"]
    # crea una conversación enviando un chat
    res = client.post("/chat", headers=h, json={
        "agent_id": agent_id, "prompt": "Hola, ¿qué puedes hacer?", "use_rag": False}).json()
    conv_id = res["conversation_id"]

    # aparece en el historial
    convs = client.get("/chat/conversations", headers=h).json()
    assert any(c["id"] == conv_id for c in convs)
    mine = next(c for c in convs if c["id"] == conv_id)
    assert mine["title"] and mine["messages"] >= 2

    # se puede abrir y trae los mensajes
    full = client.get(f"/chat/conversations/{conv_id}", headers=h).json()
    assert full["id"] == conv_id and len(full["messages"]) >= 2
    assert full["messages"][0]["role"] == "user"

    # se puede borrar y desaparece
    assert client.delete(f"/chat/conversations/{conv_id}", headers=h).json()["ok"] is True
    assert client.get(f"/chat/conversations/{conv_id}", headers=h).status_code == 404
    assert all(c["id"] != conv_id for c in client.get("/chat/conversations", headers=h).json())
