"""WhatsApp vía CallMeBot — envío simple por HTTP GET.

CallMeBot (https://www.callmebot.com/blog/free-api-whatsapp-messages/) permite
enviar mensajes de WhatsApp con una sola llamada:
    GET https://api.callmebot.com/whatsapp.php?phone=<intl>&text=<urlencoded>&apikey=<key>
El usuario registra su número con el bot una vez para obtener su apikey. No requiere
servidor propio ni proveedor de pago. Pensado para avisos personales / del equipo.
"""
from __future__ import annotations

from urllib.parse import quote

ENDPOINT = "https://api.callmebot.com/whatsapp.php"
_MAX = 900  # CallMeBot corta mensajes largos; recortamos para evitar fallos silenciosos.


def send_callmebot(phone: str, apikey: str, text: str) -> tuple[bool, str]:
    """Envía `text` al `phone` (formato internacional, p. ej. +5215512345678) usando la
    `apikey` de CallMeBot. Devuelve (ok, detalle). No lanza."""
    phone = (phone or "").strip()
    apikey = (apikey or "").strip()
    if not phone or not apikey:
        return False, "Falta el número o la apikey de CallMeBot."
    body = (text or "").strip()
    if not body:
        return False, "Mensaje vacío."
    if len(body) > _MAX:
        body = body[:_MAX] + "…"
    import httpx
    try:
        r = httpx.get(ENDPOINT, params={"phone": phone, "text": body, "apikey": apikey},
                      timeout=20)
        ok = r.status_code < 400
        detail = (r.text or "")[:200] if not ok else "Mensaje enviado a WhatsApp."
        return ok, detail
    except Exception as exc:  # pragma: no cover - network
        return False, f"No se pudo contactar a CallMeBot: {exc}"


def callmebot_link(phone: str, apikey: str, text: str) -> str:
    """URL directa (por si se quiere abrir/depurar manualmente)."""
    return f"{ENDPOINT}?phone={quote(phone)}&text={quote(text)}&apikey={quote(apikey)}"
