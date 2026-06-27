"""Motor de alertas: cuando ocurre un evento, entrega notificaciones según las reglas
configurables del tenant. Canales: 'popup' (in-app, tabla Notification) y 'webhook'
(POST a una URL — Slack/Teams/correo vía n8n o Zapier).

`dispatch()` es seguro de llamar desde cualquier handler: nunca lanza."""
from __future__ import annotations

import json

from sqlmodel import select

from .models import AlertRule, Notification

# Catálogo de eventos que se pueden alertar (para la UI).
EVENT_TYPES = [
    {"key": "test", "label": "Prueba"},
    {"key": "finetune", "label": "Fine-tuning (job)"},
    {"key": "workflow", "label": "Workflow ejecutado"},
    {"key": "recipe", "label": "Receta de automatización"},
    {"key": "action", "label": "Acción del toolkit"},
    {"key": "antivirus", "label": "Antivirus (archivo rechazado)"},
    {"key": "ingest", "label": "Ingesta de documentos"},
]
_VALID = {e["key"] for e in EVENT_TYPES}


def _post_webhook(url: str, payload: dict) -> None:  # pragma: no cover - network
    import httpx
    try:
        httpx.post(url, json=payload, timeout=15)
    except Exception:
        pass


def _send_telegram(token: str, chat_id: str, text: str) -> None:  # pragma: no cover - network
    import httpx
    try:
        httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                   json={"chat_id": chat_id, "text": text}, timeout=15)
    except Exception:
        pass


def dispatch(session, tenant_id: str, event_type: str, title: str, body: str = "",
             level: str = "info") -> int:
    """Entrega la alerta a todas las reglas habilitadas del tenant que coinciden con
    `event_type`. Devuelve cuántas reglas dispararon. Nunca lanza."""
    try:
        rules = session.exec(select(AlertRule).where(
            AlertRule.tenant_id == tenant_id, AlertRule.event_type == event_type,
            AlertRule.enabled == True)).all()  # noqa: E712
    except Exception:
        return 0
    fired = 0
    for r in rules:
        try:
            channels = json.loads(r.channels or "[]")
        except (ValueError, TypeError):
            channels = ["popup"]
        if "popup" in channels:
            session.add(Notification(tenant_id=tenant_id, user_id=r.user_id, title=title,
                                     body=body, level=level, event_type=event_type))
        payload = {"event": event_type, "title": title, "body": body, "level": level}
        if "webhook" in channels and r.webhook_url:
            _post_webhook(r.webhook_url, payload)
        if "whatsapp" in channels and r.webhook_url:
            # WhatsApp vía tu proveedor (Twilio/Meta/Zapier): se envía al webhook configurado.
            _post_webhook(r.webhook_url, {**payload, "channel": "whatsapp"})
        if "telegram" in channels and r.telegram_token and r.telegram_chat_id:
            _send_telegram(r.telegram_token, r.telegram_chat_id, f"{title}\n{body}")
        fired += 1
    if fired:
        try:
            session.commit()
        except Exception:
            session.rollback()
    return fired
