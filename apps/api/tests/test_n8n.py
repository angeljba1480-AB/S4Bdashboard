"""n8n workflow integration tests (hybrid multi-tenant model)."""
from __future__ import annotations

import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

import app.integrations.n8n as n8n  # noqa: E402
from app.integrations.n8n import N8nConfig, resolve_n8n  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Tenant  # noqa: E402
from app.security.crypto import encrypt  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


# --- resolution unit tests --------------------------------------------------
def test_resolve_off_by_default():
    assert resolve_n8n(Tenant(name="T")).source == "off"


def test_resolve_prefers_tenant_override():
    t = Tenant(name="T")
    t.n8n_webhook_base_url = "https://n8n.tenant.mx/webhook"
    t.n8n_api_key_enc = encrypt("tok", t.id)
    cfg = resolve_n8n(t)
    assert cfg.source == "tenant"
    assert cfg.enabled is True
    assert cfg.api_key == "tok"  # decrypted


def test_resolve_tenant_path_prefix_when_provisioned(monkeypatch):
    """BYO + workflows aprovisionados por MaestroAI → path con prefijo del tenant
    ({tenant_id}/{workflow}); BYO con flujos propios → sin prefijo.
    Esto evitaba el 404 al llamar /webhook/mando sin el prefijo."""
    from app.integrations.n8n import trigger_workflow

    t = Tenant(name="T")
    t.n8n_webhook_base_url = "https://n8n.tenant.mx/webhook"
    # Flujos propios del tenant (no aprovisionados) → sin prefijo.
    assert resolve_n8n(t).path_prefix == ""

    # MaestroAI aprovisionó los flujos en su n8n → prefijo = tenant.id.
    t.n8n_provisioned = True
    cfg = resolve_n8n(t)
    assert cfg.path_prefix == t.id

    # La URL disparada incluye el prefijo del tenant.
    captured = {}

    class _Resp:
        status_code = 200
        def raise_for_status(self): ...
        def json(self): return {"ok": True}

    import httpx
    monkeypatch.setattr(httpx, "post", lambda url, **kw: captured.setdefault("url", url) or _Resp())
    trigger_workflow(cfg, "mando", {"x": 1})
    assert captured["url"] == f"https://n8n.tenant.mx/webhook/{t.id}/mando"


# --- API tests --------------------------------------------------------------
def test_run_simulated_when_n8n_disabled(client):
    r = client.post("/workflows/ingesta/run", headers=_auth(client)).json()
    assert r["engine"] == "simulado"
    assert r["source"] == "off"


def test_set_tenant_n8n_and_resolve(client):
    h = _auth(client)
    put = client.put("/admin/n8n", headers=h, json={
        "webhook_base_url": "https://n8n.maestroai.mx/webhook", "api_key": "secret-token", "auth_header": "",
    }).json()
    assert put["source"] == "tenant"

    got = client.get("/admin/n8n", headers=h).json()
    assert got["tenant_override"] is True
    assert got["effective_source"] == "tenant"
    assert got["has_api_key"] is True
    assert "secret-token" not in str(got)  # secret never returned


def test_run_uses_tenant_source(client, monkeypatch):
    h = _auth(client)
    client.put("/admin/n8n", headers=h, json={"webhook_base_url": "https://n8n.maestroai.mx/webhook", "api_key": "t"})

    def fake_trigger(cfg, workflow_id, payload, webhook_path=None):
        assert cfg.source == "tenant"
        return n8n.WorkflowRun(triggered=True, status="completed", source=cfg.source, response={"ok": True})

    import app.routers.workflows as wf
    monkeypatch.setattr(wf, "trigger_workflow", fake_trigger)

    r = client.post("/workflows/rag/run", headers=h).json()
    assert r["engine"] == "n8n"
    assert r["source"] == "tenant"


def test_unknown_workflow_404(client):
    assert client.post("/workflows/nope/run", headers=_auth(client)).status_code == 404


def test_provision_noop_when_rest_not_configured(client):
    # Reset tenant override so it's on the managed path.
    h = _auth(client)
    client.put("/admin/n8n", headers=h, json={"webhook_base_url": "", "api_key": ""})
    r = client.post("/admin/n8n/provision", headers=h).json()
    assert r["provisioned"] is False
    assert "REST" in r["reason"] or "n8n" in r["reason"]


def test_n8n_status_exposes_managed_fields(client):
    h = _auth(client)
    s = client.get("/admin/n8n", headers=h).json()
    assert "managed_available" in s
    assert "auto_provision" in s
    assert "provisioned" in s
