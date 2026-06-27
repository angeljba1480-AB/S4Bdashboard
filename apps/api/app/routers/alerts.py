"""/alerts y /notifications — alertas configurables con pop-ups in-app y webhooks."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import alerts as alerts_engine
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AlertRule, Notification, Tenant, User

router = APIRouter(tags=["alerts"])

_CHANNELS = {"popup", "webhook", "telegram", "whatsapp"}


def _rule_out(r: AlertRule) -> dict:
    return {"id": r.id, "name": r.name, "event_type": r.event_type,
            "channels": json.loads(r.channels or "[]"), "webhook_url": r.webhook_url,
            "telegram_chat_id": r.telegram_chat_id, "has_telegram_token": bool(r.telegram_token),
            "enabled": r.enabled, "created_at": r.created_at.isoformat()}


def _ntf_out(n: Notification) -> dict:
    return {"id": n.id, "title": n.title, "body": n.body, "level": n.level,
            "event_type": n.event_type, "read": n.read, "created_at": n.created_at.isoformat()}


# --- catálogo + reglas ------------------------------------------------------
@router.get("/alerts/event-types")
def event_types(_: User = Depends(get_current_user)) -> list[dict]:
    return alerts_engine.EVENT_TYPES


class RuleIn(BaseModel):
    name: str
    event_type: str
    channels: list[str] = ["popup"]
    webhook_url: str = ""
    telegram_token: str = ""
    telegram_chat_id: str = ""
    enabled: bool = True


def _validate(body: RuleIn) -> tuple[str, list[str]]:
    if body.event_type not in alerts_engine._VALID:
        raise HTTPException(status_code=422, detail="event_type inválido")
    channels = [c for c in body.channels if c in _CHANNELS] or ["popup"]
    if ("webhook" in channels or "whatsapp" in channels) and not body.webhook_url.strip().startswith("http"):
        raise HTTPException(status_code=422, detail="El canal webhook/WhatsApp requiere una URL válida (tu proveedor o Zapier)")
    if "telegram" in channels and not (body.telegram_token.strip() and body.telegram_chat_id.strip()):
        raise HTTPException(status_code=422, detail="Telegram requiere token del bot y chat_id")
    return body.event_type, channels


@router.get("/alerts/rules")
def list_rules(tenant: Tenant = Depends(get_current_tenant), user: User = Depends(get_current_user),
               session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(select(AlertRule).where(
        AlertRule.tenant_id == tenant.id, AlertRule.user_id == user.id)
        .order_by(AlertRule.created_at.desc())).all()
    return [_rule_out(r) for r in rows]


@router.post("/alerts/rules", status_code=201)
def create_rule(body: RuleIn, tenant: Tenant = Depends(get_current_tenant),
                user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    event_type, channels = _validate(body)
    r = AlertRule(tenant_id=tenant.id, user_id=user.id, name=body.name.strip(),
                  event_type=event_type, channels=json.dumps(channels),
                  webhook_url=body.webhook_url.strip(), telegram_token=body.telegram_token.strip(),
                  telegram_chat_id=body.telegram_chat_id.strip(), enabled=body.enabled)
    session.add(r); session.commit(); session.refresh(r)
    return _rule_out(r)


def _owned_rule(session, tenant, user, rid) -> AlertRule:
    r = session.get(AlertRule, rid)
    if not r or r.tenant_id != tenant.id or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    return r


@router.patch("/alerts/rules/{rid}")
def update_rule(rid: str, body: RuleIn, tenant: Tenant = Depends(get_current_tenant),
                user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    r = _owned_rule(session, tenant, user, rid)
    event_type, channels = _validate(body)
    r.name = body.name.strip() or r.name
    r.event_type = event_type
    r.channels = json.dumps(channels)
    r.webhook_url = body.webhook_url.strip()
    if body.telegram_token.strip():
        r.telegram_token = body.telegram_token.strip()
    r.telegram_chat_id = body.telegram_chat_id.strip()
    r.enabled = body.enabled
    session.add(r); session.commit(); session.refresh(r)
    return _rule_out(r)


@router.delete("/alerts/rules/{rid}")
def delete_rule(rid: str, tenant: Tenant = Depends(get_current_tenant),
                user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    r = _owned_rule(session, tenant, user, rid)
    session.delete(r); session.commit()
    return {"ok": True}


@router.post("/alerts/test")
def test_alert(tenant: Tenant = Depends(get_current_tenant), _: User = Depends(get_current_user),
               session: Session = Depends(get_session)) -> dict:
    fired = alerts_engine.dispatch(session, tenant.id, "test", "Alerta de prueba",
                                   "Si ves esto, las alertas funcionan.", level="info")
    return {"fired": fired}


# --- notificaciones (pop-ups in-app) ----------------------------------------
@router.get("/notifications")
def list_notifications(unread: bool = False, tenant: Tenant = Depends(get_current_tenant),
                       user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[dict]:
    q = select(Notification).where(Notification.tenant_id == tenant.id, Notification.user_id == user.id)
    if unread:
        q = q.where(Notification.read == False)  # noqa: E712
    rows = session.exec(q.order_by(Notification.created_at.desc()).limit(50)).all()
    return [_ntf_out(n) for n in rows]


@router.get("/notifications/unread-count")
def unread_count(tenant: Tenant = Depends(get_current_tenant), user: User = Depends(get_current_user),
                 session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(Notification).where(
        Notification.tenant_id == tenant.id, Notification.user_id == user.id,
        Notification.read == False)).all()  # noqa: E712
    return {"count": len(rows)}


@router.post("/notifications/{nid}/read")
def mark_read(nid: str, tenant: Tenant = Depends(get_current_tenant), user: User = Depends(get_current_user),
              session: Session = Depends(get_session)) -> dict:
    n = session.get(Notification, nid)
    if not n or n.tenant_id != tenant.id or n.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    n.read = True
    session.add(n); session.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
def mark_all_read(tenant: Tenant = Depends(get_current_tenant), user: User = Depends(get_current_user),
                  session: Session = Depends(get_session)) -> dict:
    rows = session.exec(select(Notification).where(
        Notification.tenant_id == tenant.id, Notification.user_id == user.id,
        Notification.read == False)).all()  # noqa: E712
    for n in rows:
        n.read = True
        session.add(n)
    session.commit()
    return {"ok": True, "marked": len(rows)}
