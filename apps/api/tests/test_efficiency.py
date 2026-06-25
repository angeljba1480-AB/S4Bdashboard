"""Admin token-efficiency controls (condensación + tope de gasto) configurables."""
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


def test_get_and_update_efficiency(client):
    h = _auth(client)
    cur = client.get("/admin/efficiency", headers=h).json()
    assert "condense_enabled" in cur and "max_tokens_per_request" in cur and "tokens_saved_total" in cur

    upd = client.put("/admin/efficiency", headers=h, json={
        "condense_enabled": True, "condense_threshold_chars": 4000, "max_tokens_per_request": 8000}).json()
    assert upd["condense_threshold_chars"] == 4000 and upd["max_tokens_per_request"] == 8000

    # Persisted + reflected in the runtime config used by the generation path.
    from app import runtime_config
    assert runtime_config.max_tokens_per_request() == 8000
    assert runtime_config.condense_threshold_chars() == 4000
