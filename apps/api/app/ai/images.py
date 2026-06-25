"""Text-to-image generation via the OpenAI-compatible images endpoint.

Reuses the **open** provider (NaN Builders / FLUX) configured in Admin → Modelos
externos (admin runtime override) or env. NaN exposes an OpenAI-compatible API, so
we POST to `{base_url}/images/generations`. The model defaults to FLUX.2 but is
configurable. PII in the prompt is redacted before the external call.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass

from ..config import settings
from ..models import ModelRoute

# Aspect ratio (UI) → pixel size (provider). FLUX/SDXL-friendly sizes.
ASPECT_SIZES = {"1:1": "1024x1024", "16:9": "1344x768", "9:16": "768x1344"}
DEFAULT_IMAGE_MODEL = "FLUX.2-klein"
TIMEOUT = 120


@dataclass
class GenImage:
    data_b64: str   # image bytes, base64 (may be empty if only a URL came back)
    url: str        # provider URL (may be empty if only b64 came back)
    mime_type: str = "image/png"


def _open_provider() -> dict | None:
    """Resolve the open route's base_url/api_key/model (admin override → env)."""
    from .adapters import _RUNTIME

    ov = _RUNTIME.get(ModelRoute.OPEN.value)
    if ov and ov.get("enabled") and ov.get("base_url"):
        return {"base_url": ov["base_url"], "api_key": ov.get("api_key", ""),
                "model": ov.get("model") or ""}
    if settings.open_enabled and settings.open_base_url:
        return {"base_url": settings.open_base_url, "api_key": settings.open_api_key,
                "model": settings.open_model}
    return None


def is_configured() -> bool:
    return _open_provider() is not None


def _fetch_b64(url: str) -> str:
    """Download an image URL and return its base64 (so the gallery owns a copy)."""
    import httpx

    r = httpx.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return base64.b64encode(r.content).decode()


def generate(prompt: str, *, n: int = 1, size: str = "1024x1024",
             model: str | None = None, store: bool = True) -> list[GenImage]:  # pragma: no cover - network
    """Generate `n` images for `prompt`. Raises if no provider is configured or the
    call fails. PII is redacted before sending the prompt externally."""
    import httpx

    from ..security.dlp import redact

    prov = _open_provider()
    if not prov:
        raise RuntimeError("No hay proveedor abierto (NaN) configurado para generar imágenes.")
    use_model = (model or prov["model"] or DEFAULT_IMAGE_MODEL)
    base = prov["base_url"].rstrip("/")
    resp = httpx.post(
        f"{base}/images/generations",
        headers={"Authorization": f"Bearer {prov['api_key']}"},
        json={"model": use_model, "prompt": redact(prompt), "n": max(1, min(n, 4)), "size": size},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    out: list[GenImage] = []
    for item in resp.json().get("data", []):
        b64 = item.get("b64_json") or ""
        url = item.get("url") or ""
        if store and not b64 and url:
            try:
                b64 = _fetch_b64(url)
            except Exception:
                b64 = ""
        out.append(GenImage(data_b64=b64, url=url))
    return out
