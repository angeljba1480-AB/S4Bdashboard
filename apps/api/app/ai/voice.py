"""Voz vía el proveedor abierto (NaN), OpenAI-compatible.

- **TTS** (`kokoro`): texto → audio (`/v1/audio/speech`). Voces ES `ef_dora`/`em_alex`.
- **STT** (`whisper`): audio → texto (`/v1/audio/transcriptions`, multipart).

Reutiliza el proveedor abierto configurado en Admin (override) o env. La PII del
texto a narrar se redacta antes de salir (consistente con chat/imágenes).
"""
from __future__ import annotations

from ..config import settings
from .adapters import open_provider_config

TIMEOUT = 60
STT_TIMEOUT = 120

# Voz → etiqueta (las de español primero). Lista corta; NaN soporta más.
VOICES = {
    "ef_dora": "Español · femenina (Dora)",
    "em_alex": "Español · masculina (Alex)",
    "af_heart": "English · female (Heart)",
}
_MIME = {"mp3": "audio/mpeg", "wav": "audio/wav", "flac": "audio/flac",
         "aac": "audio/aac", "opus": "audio/ogg", "pcm": "audio/pcm"}


def is_configured() -> bool:
    return open_provider_config() is not None


def tts(text: str, voice: str = "", fmt: str = "mp3") -> tuple[bytes, str]:  # pragma: no cover - network
    """Texto → audio. Devuelve (bytes, mime). PII redactada antes de enviar."""
    from ..security.dlp import redact

    import httpx

    prov = open_provider_config()
    if not prov:
        raise RuntimeError("No hay proveedor abierto (NaN) configurado para voz.")
    fmt = fmt if fmt in _MIME else "mp3"
    resp = httpx.post(
        f"{prov['base_url'].rstrip('/')}/audio/speech",
        headers={"Authorization": f"Bearer {prov['api_key']}"},
        json={"model": settings.tts_model, "input": redact(text or ""),
              "voice": voice or settings.default_voice, "response_format": fmt},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.content, _MIME[fmt]


def stt(file_bytes: bytes, filename: str = "audio.mp3", language: str = "") -> dict:  # pragma: no cover - network
    """Audio → texto. Devuelve {text, language}."""
    import httpx

    prov = open_provider_config()
    if not prov:
        raise RuntimeError("No hay proveedor abierto (NaN) configurado para voz.")
    data = {"model": settings.stt_model, "response_format": "verbose_json"}
    if language:
        data["language"] = language
    resp = httpx.post(
        f"{prov['base_url'].rstrip('/')}/audio/transcriptions",
        headers={"Authorization": f"Bearer {prov['api_key']}"},
        data=data,
        files={"file": (filename or "audio.mp3", file_bytes)},
        timeout=STT_TIMEOUT,
    )
    resp.raise_for_status()
    j = resp.json()
    return {"text": j.get("text", ""), "language": j.get("language", "")}
