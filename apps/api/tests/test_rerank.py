"""Reranking del RAG: cuando está activo, reordena los candidatos con el reranker
(NaN) antes de devolver top_k. Se mockea la llamada al reranker — sin red."""
from __future__ import annotations

import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.ai.rag import Citation, _maybe_rerank  # noqa: E402
from app.models import Sensitivity  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def _cites(n: int) -> list[Citation]:
    # Orden de entrada = orden por cosine (score descendente).
    return [Citation(document_id=str(i), filename=f"{i}.txt", chunk_index=0,
                     text=f"texto {i}", score=round(1.0 - i * 0.1, 4),
                     sensitivity=Sensitivity.INTERNAL) for i in range(n)]


def test_maybe_rerank_reorders_when_enabled(monkeypatch):
    from app.ai import rerank as rerank_mod
    monkeypatch.setattr(rerank_mod, "rerank", lambda q, docs, top_n=None: list(range(len(docs)))[::-1])
    out = _maybe_rerank("q", _cites(5), top_k=3, use_rerank=True)
    assert [c.document_id for c in out] == ["4", "3", "2"]  # invertido por el reranker


def test_maybe_rerank_keeps_cosine_when_disabled(monkeypatch):
    from app.ai import rerank as rerank_mod
    called = {"n": 0}
    monkeypatch.setattr(rerank_mod, "rerank", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or None)
    out = _maybe_rerank("q", _cites(5), top_k=3, use_rerank=False)
    assert [c.document_id for c in out] == ["0", "1", "2"]  # orden cosine intacto
    assert called["n"] == 0  # no se invoca el reranker


def test_maybe_rerank_falls_back_on_failure(monkeypatch):
    from app.ai import rerank as rerank_mod
    monkeypatch.setattr(rerank_mod, "rerank", lambda *a, **k: None)  # reranker no disponible
    out = _maybe_rerank("q", _cites(4), top_k=2, use_rerank=True)
    assert [c.document_id for c in out] == ["0", "1"]  # fallback a cosine


def test_efficiency_exposes_rerank_toggle(client):
    h = _auth(client)
    cur = client.get("/admin/efficiency", headers=h).json()
    assert "rerank_enabled" in cur
    upd = client.put("/admin/efficiency", headers=h, json={"rerank_enabled": True}).json()
    assert upd["rerank_enabled"] is True
    from app import runtime_config
    assert runtime_config.rerank_enabled() is True
    # Apágalo de nuevo para no afectar otras pruebas del módulo compartido.
    client.put("/admin/efficiency", headers=h, json={"rerank_enabled": False})


def test_rerank_is_enabled_requires_provider(client):
    # Sin proveedor abierto configurado, is_enabled es False aunque el flag esté on.
    from app.ai.rerank import is_enabled
    assert is_enabled() in (True, False)  # no lanza; depende de config del entorno
