"""Escaneo antivirus de archivos subidos (blueprint: «upload → antivirus → …»).

Estrategia en capas, segura por defecto:
1. Tope de tamaño configurable (rechaza archivos enormes).
2. Firma estándar **EICAR** — detección determinista del archivo de prueba de
   antivirus, sin necesidad de ningún daemon (sirve para validar el flujo).
3. **ClamAV** (opcional): si hay un daemon configurado (host/puerto o socket unix)
   y la librería `clamd`, se escanea el contenido real. Si no está disponible, se
   degrada con elegancia (no bloquea archivos limpios).
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from ..config import settings

# Firma del archivo de prueba EICAR (estándar de la industria, inofensivo).
EICAR = (b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")


@dataclass
class ScanResult:
    ok: bool
    reason: str = ""
    threat: str = ""
    engine: str = ""


def _too_big(raw: bytes) -> bool:
    cap = settings.max_upload_mb
    return cap > 0 and len(raw) > cap * 1024 * 1024


def _clamd_scan(raw: bytes) -> ScanResult | None:
    """Escanea con ClamAV si hay daemon + librería. None si no está disponible."""
    if not (settings.clamav_host or settings.clamav_socket):
        return None
    try:  # pragma: no cover - requiere daemon clamd
        import clamd
        cd = (clamd.ClamdUnixSocket(settings.clamav_socket) if settings.clamav_socket
              else clamd.ClamdNetworkSocket(settings.clamav_host, settings.clamav_port))
        res = cd.instream(io.BytesIO(raw))
        status, name = res.get("stream", ("OK", ""))
        if status == "FOUND":
            return ScanResult(ok=False, reason="Archivo infectado", threat=name or "desconocido", engine="clamav")
        return ScanResult(ok=True, engine="clamav")
    except Exception:
        return None  # daemon caído / no instalado → degradar


def scan(raw: bytes, filename: str = "") -> ScanResult:
    """Escanea un archivo. Nunca lanza; devuelve un ScanResult."""
    if not settings.antivirus_enabled:
        return ScanResult(ok=True, engine="disabled")
    if _too_big(raw):
        return ScanResult(ok=False, reason=f"Archivo supera el tope de {settings.max_upload_mb} MB", engine="size")
    if EICAR in raw:
        return ScanResult(ok=False, reason="Archivo de prueba EICAR detectado",
                          threat="EICAR-Test-Signature", engine="eicar")
    clam = _clamd_scan(raw)
    if clam is not None:
        return clam
    return ScanResult(ok=True, engine="eicar-only")
