"""Fine-tuning ligero (LoRA): datasets, anonimización, gate, export y jobs."""
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


def _dataset(client, h) -> str:
    return client.post("/finetune/datasets", headers=h, json={"name": "Tono comercial", "base_model": "llama3.1"}).json()["id"]


def test_base_models_catalog(client):
    h = _auth(client)
    models = client.get("/finetune/base-models", headers=h).json()
    names = {m["name"]: m for m in models}
    # Familias clave de la industria presentes.
    assert "llama3.2:3b" in names and names["llama3.2:3b"]["mlx_model"].startswith("mlx-community/")
    assert any(n.startswith("qwen") for n in names)
    assert any(n.startswith("mistral") for n in names)
    assert any(n.startswith("gemma") for n in names)
    assert any(n.startswith("deepseek") for n in names)
    assert names["deepseek-r1:8b"]["family"] == "DeepSeek"


def test_example_is_anonymized(client):
    h = _auth(client)
    ds = _dataset(client, h)
    client.post(f"/finetune/datasets/{ds}/examples", headers=h, json={
        "prompt": "Escribe a juan@acme.mx", "completion": "Estimado cliente,"})
    export = client.get(f"/finetune/datasets/{ds}/export", headers=h).text
    assert "[EMAIL]" in export and "juan@acme.mx" not in export


def test_gate_blocks_small_then_passes(client):
    h = _auth(client)
    ds = _dataset(client, h)
    # 1 ejemplo → gate falla (muy pocos).
    client.post(f"/finetune/datasets/{ds}/examples", headers=h, json={"prompt": "a", "completion": "b"})
    chk = client.post(f"/finetune/datasets/{ds}/check", headers=h).json()
    assert chk["ok"] is False and chk["status"] == "draft"
    # Crear job con gate fallido → 422.
    assert client.post("/finetune/jobs", headers=h, json={"dataset_id": ds}).status_code == 422
    # Completar a ≥3 ejemplos limpios → gate pasa.
    for i in range(3):
        client.post(f"/finetune/datasets/{ds}/examples", headers=h, json={
            "prompt": f"Pregunta {i}", "completion": f"Respuesta formal {i}"})
    chk2 = client.post(f"/finetune/datasets/{ds}/check", headers=h).json()
    assert chk2["ok"] is True and chk2["status"] == "ready"


def test_from_memory_builds_examples(client):
    h = _auth(client)
    client.post("/memory", headers=h, json={"title": "Resumen ACME", "content": "Propuesta enviada y aprobada."})
    ds = _dataset(client, h)
    r = client.post(f"/finetune/datasets/{ds}/from-memory", headers=h, json={"limit": 50}).json()
    assert r["added"] >= 1 and r["examples"] >= 1


def test_job_simulado_and_callback(client):
    h = _auth(client)
    ds = _dataset(client, h)
    for i in range(3):
        client.post(f"/finetune/datasets/{ds}/examples", headers=h, json={
            "prompt": f"P{i}", "completion": f"Respuesta clara y formal {i}"})
    job = client.post("/finetune/jobs", headers=h, json={"dataset_id": ds}).json()
    # Sin trainer configurado → modo laboratorio.
    assert job["status"] == "simulado" and job["base_model"] == "llama3.1"

    done = client.post(f"/finetune/jobs/{job['id']}/callback", headers=h, json={
        "status": "completed", "adapter_uri": "file:///adapters/x", "serve_base_url": "http://ollama/v1",
        "metrics": {"loss": 0.21}}).json()
    assert done["status"] == "completed" and done["metrics"]["loss"] == 0.21
    assert any(j["id"] == job["id"] for j in client.get("/finetune/jobs", headers=h).json())
