"""Motor de alertas: cuando ocurre un evento, entrega notificaciones según las reglas
configurables del tenant. Canales: 'popup' (in-app, tabla Notification) y 'webhook'
(POST a una URL — Slack/Teams/correo vía n8n o Zapier).

`dispatch()` es seguro de llamar desde cualquier handler: nunca lanza."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlmodel import select

from .models import AlertRule, AuditEvent, Notification

# Catálogo de eventos que se pueden alertar (para la UI).
EVENT_TYPES = [
    {"key": "test", "label": "Prueba"},
    {"key": "finetune", "label": "Fine-tuning (job)"},
    {"key": "workflow", "label": "Workflow ejecutado"},
    {"key": "recipe", "label": "Receta de automatización"},
    {"key": "action", "label": "Acción del toolkit"},
    {"key": "antivirus", "label": "Antivirus (archivo rechazado)"},
    {"key": "ingest", "label": "Ingesta de documentos"},
    {"key": "webhook", "label": "Webhook entrante"},
    {"key": "threshold", "label": "Umbral de gasto (tokens)"},
    {"key": "digest", "label": "Resumen programado (digest)"},
]
_VALID = {e["key"] for e in EVENT_TYPES}

# Cadencias válidas para reglas programadas (digest).
SCHEDULES = ["", "daily", "weekly"]
_WINDOW = {"daily": timedelta(days=1), "weekly": timedelta(days=7)}


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


def _deliver(session, rule: AlertRule, event_type: str, title: str, body: str,
             level: str) -> None:
    """Entrega una alerta por los canales de una regla (sin commit)."""
    try:
        channels = json.loads(rule.channels or "[]")
    except (ValueError, TypeError):
        channels = ["popup"]
    if "popup" in channels:
        session.add(Notification(tenant_id=rule.tenant_id, user_id=rule.user_id, title=title,
                                 body=body, level=level, event_type=event_type))
    payload = {"event": event_type, "title": title, "body": body, "level": level}
    if "webhook" in channels and rule.webhook_url:
        _post_webhook(rule.webhook_url, payload)
    if "whatsapp" in channels:
        _send_whatsapp(session, rule, f"{title}\n{body}".strip())
    if "telegram" in channels and rule.telegram_token and rule.telegram_chat_id:
        _send_telegram(rule.telegram_token, rule.telegram_chat_id, f"{title}\n{body}")


def _send_whatsapp(session, rule, text: str) -> None:
    """WhatsApp del canal de alertas: usa CallMeBot si el dueño de la regla lo tiene
    configurado; si no, cae al webhook del proveedor (Twilio/Meta/Zapier)."""
    try:
        from .models import Tenant, User
        user = session.get(User, rule.user_id)
        if user and user.callmebot_phone and user.callmebot_apikey_enc:
            from .integrations import whatsapp as _wa
            from .security.crypto import decrypt
            tenant = session.get(Tenant, rule.tenant_id)
            apikey = decrypt(user.callmebot_apikey_enc, tenant.kms_key_id)
            _wa.send_callmebot(user.callmebot_phone, apikey, text)
            return
    except Exception:
        pass
    if rule.webhook_url:
        _post_webhook(rule.webhook_url, {"channel": "whatsapp", "text": text})


def dispatch(session, tenant_id: str, event_type: str, title: str, body: str = "",
             level: str = "info") -> int:
    """Entrega la alerta en TIEMPO REAL a las reglas habilitadas del tenant que
    coinciden con `event_type`. Las reglas programadas (digest) se saltan aquí: las
    procesa `run_digests`. Devuelve cuántas reglas dispararon. Nunca lanza."""
    try:
        rules = session.exec(select(AlertRule).where(
            AlertRule.tenant_id == tenant_id, AlertRule.event_type == event_type,
            AlertRule.schedule == "", AlertRule.enabled == True)).all()  # noqa: E712
    except Exception:
        return 0
    fired = 0
    for r in rules:
        _deliver(session, r, event_type, title, body, level)
        fired += 1
    if fired:
        try:
            session.commit()
        except Exception:
            session.rollback()
    return fired


def _build_digest(session, tenant_id: str, since: datetime) -> tuple[str, int]:
    """Resumen de actividad del tenant (eventos de auditoría) desde `since`.
    Devuelve (texto, total_eventos)."""
    try:
        rows = session.exec(select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id, AuditEvent.created_at >= since)).all()
    except Exception:
        rows = []
    by_type: dict[str, int] = {}
    risky = 0
    for e in rows:
        by_type[e.event_type or "otros"] = by_type.get(e.event_type or "otros", 0) + 1
        if (e.risk_level or "low") in ("med", "high"):
            risky += 1
    if not rows:
        return ("Sin actividad en el periodo.", 0)
    top = sorted(by_type.items(), key=lambda x: -x[1])[:8]
    lines = [f"• {k}: {v}" for k, v in top]
    if risky:
        lines.append(f"• eventos de riesgo (med/alto): {risky}")
    return ("Actividad del periodo:\n" + "\n".join(lines), len(rows))


def run_digests(session, tenant_id: str, frequency: str) -> int:
    """Procesa las reglas programadas (schedule == frequency): construye un resumen de
    la actividad del periodo y lo entrega por los canales de cada regla. Cron-friendly
    (sin scheduler en proceso). Devuelve cuántos digests se enviaron. Nunca lanza."""
    if frequency not in _WINDOW:
        return 0
    try:
        rules = session.exec(select(AlertRule).where(
            AlertRule.tenant_id == tenant_id, AlertRule.schedule == frequency,
            AlertRule.enabled == True)).all()  # noqa: E712
    except Exception:
        return 0
    if not rules:
        return 0
    now = datetime.utcnow()
    since = now - _WINDOW[frequency]
    body, total = _build_digest(session, tenant_id, since)
    label = "diario" if frequency == "daily" else "semanal"
    title = f"Resumen {label} ({total} eventos)"
    sent = 0
    for r in rules:
        _deliver(session, r, "digest", title, body, "info")
        r.last_digest_at = now.isoformat()
        session.add(r)
        sent += 1
    if sent:
        try:
            session.commit()
        except Exception:
            session.rollback()
    return sent


def run_checks(session, tenant_id: str, spend_threshold: float) -> int:
    """Evalúa umbrales del sistema (hoy: gasto de tokens del día). Si el costo de hoy
    supera `spend_threshold` (> 0), dispara una alerta 'threshold'. Devuelve cuántas
    reglas dispararon. Nunca lanza."""
    if not spend_threshold or spend_threshold <= 0:
        return 0
    try:
        since = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        rows = session.exec(select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id, AuditEvent.created_at >= since)).all()
        spent = round(sum(e.cost_estimate for e in rows), 4)
    except Exception:
        return 0
    if spent < spend_threshold:
        return 0
    return dispatch(session, tenant_id, "threshold",
                    "Umbral de gasto superado",
                    f"El gasto de hoy (${spent}) superó el umbral configurado (${spend_threshold}).",
                    level="warn")
