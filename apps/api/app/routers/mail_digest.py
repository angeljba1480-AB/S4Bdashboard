"""/mail-digest — resumen de correo automatizado (config + ejecución).

Configura una vez (cuenta, horario, canales, idioma, notas, pendientes) y la plataforma
entrega el resumen del correo por pop-up / correo / WhatsApp. Cron-friendly.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import mailsummary
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import MailDigestConfig, Tenant, User

router = APIRouter(prefix="/mail-digest", tags=["mail-digest"])

_CHANNELS = {"popup", "email", "whatsapp"}
_SCHEDULES = {"daily", "weekdays"}


def _out(c: MailDigestConfig) -> dict:
    return {"id": c.id, "enabled": c.enabled, "account_id": c.account_id, "schedule": c.schedule,
            "channels": json.loads(c.channels or "[]"), "email_to": c.email_to, "language": c.language,
            "notes": c.notes, "discard_propaganda": c.discard_propaganda,
            "pending_enabled": c.pending_enabled, "pending_days": c.pending_days,
            "last_run_at": c.last_run_at or ""}


def _get_or_create(session, tenant, user) -> MailDigestConfig:
    c = session.exec(select(MailDigestConfig).where(
        MailDigestConfig.tenant_id == tenant.id, MailDigestConfig.user_id == user.id)).first()
    if not c:
        c = MailDigestConfig(tenant_id=tenant.id, user_id=user.id)
        session.add(c); session.commit(); session.refresh(c)
    return c


@router.get("/config")
def get_config(tenant: Tenant = Depends(get_current_tenant), user: User = Depends(get_current_user),
               session: Session = Depends(get_session)) -> dict:
    return _out(_get_or_create(session, tenant, user))


class ConfigIn(BaseModel):
    enabled: bool = False
    account_id: str = ""
    schedule: str = "daily"
    channels: list[str] = ["popup"]
    email_to: str = ""
    language: str = "es"
    notes: str = ""
    discard_propaganda: bool = True
    pending_enabled: bool = True
    pending_days: int = 2


@router.put("/config")
def set_config(body: ConfigIn, tenant: Tenant = Depends(get_current_tenant),
               user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if body.schedule not in _SCHEDULES:
        raise HTTPException(status_code=422, detail="schedule inválido (daily o weekdays)")
    channels = [c for c in body.channels if c in _CHANNELS] or ["popup"]
    c = _get_or_create(session, tenant, user)
    c.enabled = body.enabled
    c.account_id = body.account_id.strip()
    c.schedule = body.schedule
    c.channels = json.dumps(channels)
    c.email_to = body.email_to.strip()
    c.language = "bilingue" if body.language == "bilingue" else "es"
    c.notes = body.notes.strip()
    c.discard_propaganda = body.discard_propaganda
    c.pending_enabled = body.pending_enabled
    c.pending_days = max(1, min(int(body.pending_days or 2), 30))
    session.add(c); session.commit(); session.refresh(c)
    return _out(c)


@router.post("/preview")
def preview(tenant: Tenant = Depends(get_current_tenant), user: User = Depends(get_current_user),
            session: Session = Depends(get_session)) -> dict:
    """Genera el resumen ahora y lo devuelve (sin entregarlo por canales)."""
    c = _get_or_create(session, tenant, user)
    summary = mailsummary.build_summary(session, tenant, user, c)
    session.add(c); session.commit()  # persiste el perfil de remitentes aprendido
    return {"ok": summary.get("ok", False), "text": summary.get("text", ""),
            "account": summary.get("account", ""), "message": summary.get("message", ""),
            "counts": summary.get("counts", {})}


@router.post("/run-now")
def run_now(tenant: Tenant = Depends(get_current_tenant), user: User = Depends(get_current_user),
            session: Session = Depends(get_session)) -> dict:
    """Genera y ENTREGA el resumen ahora por los canales configurados."""
    c = _get_or_create(session, tenant, user)
    summary = mailsummary.build_summary(session, tenant, user, c)
    if not summary.get("ok"):
        session.add(c); session.commit()
        raise HTTPException(status_code=400, detail=summary.get("message", "No se pudo generar."))
    sent = mailsummary.deliver(session, tenant, user, c, summary)
    session.add(c); session.commit()
    return {"ok": True, "sent": sent, "account": summary.get("account", "")}


@router.post("/run")
def run_cron(frequency: str = "daily", _: User = Depends(get_current_user),
             session: Session = Depends(get_session)) -> dict:
    """Procesa todas las configs habilitadas (para un cron externo diario/días hábiles)."""
    return {"frequency": frequency, "done": mailsummary.run_due(session, frequency)}
