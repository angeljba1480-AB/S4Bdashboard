"""Generación de imágenes de texto (NaN/FLUX) + galería gobernada. Se mockea el
proveedor — sin red real."""
from __future__ import annotations

import base64
import os
import tempfile

import pytest

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

# Un PNG 1x1 válido en base64.
_PNG_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _auth(client) -> dict:
    tok = client.post("/auth/login", json={"email": "admin@maestroai.mx", "password": "demo1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(autouse=True)
def _mock_gen(monkeypatch):
    from app.ai import images as imagegen

    def fake_generate(prompt, *, n=1, size="1024x1024", model=None, store=True):
        return [imagegen.GenImage(data_b64=_PNG_B64, url="https://nan/img.png") for _ in range(n)]

    def fake_edit(prompt, images, *, n=1, size="1024x1024", model=None, store=True):
        return [imagegen.GenImage(data_b64=_PNG_B64, url="https://nan/edit.png") for _ in range(n)]

    monkeypatch.setattr(imagegen, "generate", fake_generate)
    monkeypatch.setattr(imagegen, "edit", fake_edit)
    monkeypatch.setattr(imagegen, "is_configured", lambda: True)


def test_raise_for_image_status_surfaces_nan_error():
    from app.ai import images as imagegen

    class _R:
        status_code = 400
        def json(self):
            return {"error": {"message": "size must be divisible by 16", "code": "invalid_request_error", "param": "size"}}
        @property
        def text(self):
            return ""

    import pytest as _pytest
    with _pytest.raises(RuntimeError) as ei:
        imagegen._raise_for_image_status(_R())
    assert "400" in str(ei.value) and "size" in str(ei.value)
    # 2xx no levanta.
    class _OK:
        status_code = 200
    imagegen._raise_for_image_status(_OK())


def test_config(client):
    r = client.get("/images/config", headers=_auth(client)).json()
    assert r["configured"] is True and "1:1" in r["aspect_ratios"]


def test_generate_creates_gallery_and_data(client):
    h = _auth(client)
    r = client.post("/images/generate", headers=h, json={
        "prompt": "Un centro de datos futurista en Marte", "aspect_ratio": "16:9", "variants": 2}).json()
    assert len(r["images"]) == 2
    img = r["images"][0]
    assert img["size"] == "1344x768" and img["has_data"] is True

    # Aparece en la galería.
    gallery = client.get("/images", headers=h).json()
    assert any(g["id"] == img["id"] for g in gallery)

    # Devuelve los bytes almacenados (PNG).
    data = client.get(f"/images/{img['id']}/data", headers=h)
    assert data.status_code == 200 and data.content[:8] == base64.b64decode(_PNG_B64)[:8]


def test_empty_prompt_rejected(client):
    h = _auth(client)
    assert client.post("/images/generate", headers=h, json={"prompt": "  "}).status_code == 422


def test_variants_capped_at_4(client):
    h = _auth(client)
    r = client.post("/images/generate", headers=h, json={"prompt": "gatos", "variants": 9}).json()
    assert len(r["images"]) == 4


def test_edit_image_from_reference(client):
    h = _auth(client)
    png = base64.b64decode(_PNG_B64)
    r = client.post("/images/edit", headers=h,
                    data={"prompt": "ponlo en invierno con nieve", "aspect_ratio": "1:1", "variants": "2"},
                    files=[("files", ("ref.png", png, "image/png"))])
    body = r.json()
    assert r.status_code == 201 and len(body["images"]) == 2
    assert body["images"][0]["has_data"] is True


def test_edit_requires_reference(client):
    h = _auth(client)
    r = client.post("/images/edit", headers=h, data={"prompt": "algo"}, files=[])
    assert r.status_code == 422


def test_delete_image(client):
    h = _auth(client)
    r = client.post("/images/generate", headers=h, json={"prompt": "borrar"}).json()
    iid = r["images"][0]["id"]
    assert client.delete(f"/images/{iid}", headers=h).json()["ok"] is True
    assert client.get(f"/images/{iid}/data", headers=h).status_code == 404
