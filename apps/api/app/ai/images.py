"""Text-to-image generation via the OpenAI-compatible images endpoint.

Reuses the **open** provider configured in Admin → Modelos externos (admin runtime
override) or env: POST to `{base_url}/images/generations` (OpenAI standard). PII in
the prompt is redacted before the external call.

NaN Builders expone hoy `/v1/images/generations` y `/v1/images/edits` con el modelo
**`flux-2-klein`** (requiere membresía tier *inference*; cuota 100 req/mes, 1–4 por
request, tamaños múltiplos de 16 entre 256–1536). El modelo de imagen es **distinto**
del de chat (`open_model`): se usa `settings.image_model`, no se reutiliza qwen3.6.
Ver docs/PROVEEDOR-NAN.md.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass

from ..config import settings
from ..models import ModelRoute

# Aspect ratio (UI) → pixel size. Lados múltiplos de 16, entre 256 y 1536 (límites
# de flux-2-klein).
ASPECT_SIZES = {"1:1": "1024x1024", "16:9": "1344x768", "9:16": "768x1344"}
DEFAULT_IMAGE_MODEL = "flux-2-klein"
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


def _raise_for_image_status(resp) -> None:
    """Si la respuesta no es 2xx, levanta el mensaje real del proveedor (NaN devuelve
    el motivo en el cuerpo: `param`, `code`, `message`) en vez de un '400' opaco."""
    if resp.status_code < 400:
        return
    detail = f"HTTP {resp.status_code}"
    try:
        err = resp.json().get("error", {}) or {}
        msg = err.get("message") or ""
        code = err.get("code") or ""
        param = err.get("param") or ""
        detail = " · ".join(x for x in (msg, f"code={code}" if code else "",
                                        f"param={param}" if param else "") if x) or detail
    except Exception:
        detail = (resp.text or detail)[:300]
    raise RuntimeError(f"NaN /images respondió {resp.status_code}: {detail}")


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
    # El modelo de imagen es independiente del de chat: nunca reutilizar prov["model"]
    # (qwen3.6) aquí, o el proveedor responde 404 model_not_found.
    use_model = (model or settings.image_model or DEFAULT_IMAGE_MODEL)
    base = prov["base_url"].rstrip("/")
    resp = httpx.post(
        f"{base}/images/generations",
        headers={"Authorization": f"Bearer {prov['api_key']}"},
        json={"model": use_model, "prompt": redact(prompt), "n": max(1, min(n, 4)),
              "size": size, "response_format": "url"},
        timeout=TIMEOUT,
    )
    _raise_for_image_status(resp)
    return _parse_data(resp.json(), store)


def edit(prompt: str, images: list[tuple[str, bytes]], *, n: int = 1, size: str = "1024x1024",
         model: str | None = None, store: bool = True) -> list[GenImage]:  # pragma: no cover - network
    """Image-to-image: genera a partir de hasta 4 imágenes de referencia
    (`/images/edits`, multipart). PII del prompt redactada antes de enviar."""
    import httpx

    from ..security.dlp import redact

    prov = _open_provider()
    if not prov:
        raise RuntimeError("No hay proveedor abierto (NaN) configurado para editar imágenes.")
    use_model = (model or settings.image_model or DEFAULT_IMAGE_MODEL)
    files = [("image[]", (name or "ref.png", data)) for name, data in images[:4]]
    if not files:
        raise RuntimeError("Sube al menos una imagen de referencia.")
    resp = httpx.post(
        f"{prov['base_url'].rstrip('/')}/images/edits",
        headers={"Authorization": f"Bearer {prov['api_key']}"},
        data={"model": use_model, "prompt": redact(prompt), "n": str(max(1, min(n, 4))), "size": size},
        files=files,
        timeout=TIMEOUT,
    )
    _raise_for_image_status(resp)
    return _parse_data(resp.json(), store)


def _parse_data(payload: dict, store: bool) -> list[GenImage]:
    out: list[GenImage] = []
    for item in payload.get("data", []):
        b64 = item.get("b64_json") or ""
        url = item.get("url") or ""
        if store and not b64 and url:
            try:
                b64 = _fetch_b64(url)
            except Exception:
                b64 = ""
        out.append(GenImage(data_b64=b64, url=url))
    return out
