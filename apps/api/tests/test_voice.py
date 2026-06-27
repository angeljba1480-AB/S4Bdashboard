"""Voz: TTS (kokoro) y STT (whisper) vía el proveedor abierto. Se mockea — sin red."""
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
def _mock_voice(monkeypatch):
    from app.ai import voice
    monkeypatch.setattr(voice, "is_configured", lambda: True)
    monkeypatch.setattr(voice, "tts", lambda text, voice="", fmt="mp3": (b"ID3audiobytes", "audio/mpeg"))
    monkeypatch.setattr(voice, "stt", lambda raw, filename="", language="": {"text": "hola mundo", "language": "es"})


def test_voice_config_lists_spanish_voices(client):
    r = client.get("/voice/config", headers=_auth(client)).json()
    assert r["configured"] is True
    ids = {v["id"] for v in r["voices"]}
    assert "ef_dora" in ids and "em_alex" in ids


def test_tts_returns_audio(client):
    h = _auth(client)
    r = client.post("/voice/tts", headers=h, json={"text": "Bienvenido a MaestroAI", "voice": "ef_dora"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("audio/")
    assert r.content == b"ID3audiobytes"


def test_tts_empty_rejected(client):
    assert client.post("/voice/tts", headers=_auth(client), json={"text": "  "}).status_code == 422


def test_transcribe_returns_text(client):
    h = _auth(client)
    r = client.post("/voice/transcribe", headers=h,
                    files=[("file", ("grab.mp3", b"fake-audio-bytes", "audio/mpeg"))],
                    data={"language": "es"})
    body = r.json()
    assert r.status_code == 200 and body["text"] == "hola mundo" and body["language"] == "es"


def test_transcribe_empty_rejected(client):
    h = _auth(client)
    r = client.post("/voice/transcribe", headers=h, files=[("file", ("x.mp3", b"", "audio/mpeg"))])
    assert r.status_code == 422
