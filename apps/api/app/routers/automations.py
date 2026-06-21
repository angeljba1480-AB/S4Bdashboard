"""/automations — create automations from templates, enable/disable, run now.

Action dispatch: workflow (n8n), recipe (use-case engine), or notify (audit).
Schedules/events are executed by the workflows layer (n8n/Temporal); this module
manages definitions and immediate runs.
"""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..automations.catalog import TEMPLATES, get_template
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..integrations.n8n import resolve_n8n, trigger_workflow
from ..models import Automation, AuditEvent, Tenant, User

router = APIRouter(prefix="/automations", tags=["automations"])


class AutomationIn(BaseModel):
    name: str
    description: str = ""
    trigger: str = "manual"
    schedule: str = ""
    event: str = ""
    action_type: str = "workflow"
    action_ref: str = ""
    config: dict = {}


class FromTemplate(BaseModel):
    template_id: str


def _out(a: Automation) -> dict:
    return {"id": a.id, "name": a.name, "description": a.description, "trigger": a.trigger,
            "schedule": a.schedule, "event": a.event, "action_type": a.action_type,
            "action_ref": a.action_ref, "config": json.loads(a.config or "{}"),
            "enabled": a.enabled, "status": a.status, "last_run": a.last_run or None}


def _load(session, tenant, user, aid) -> Automation:
    a = session.get(Automation, aid)
    if not a or a.tenant_id != tenant.id or a.user_id != user.id:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    return a


def _run(session: Session, tenant: Tenant, user: User | None, a: Automation,
         payload: dict | None = None) -> tuple[str, str]:
    """Execute the action. Returns (status, detail)."""
    config = json.loads(a.config or "{}")
    if payload:
        config = {**config, **payload}
    uid = user.id if user else None
    if a.action_type == "workflow":
        cfg = resolve_n8n(tenant)
        run = trigger_workflow(cfg, a.action_ref, {
            "automation_id": a.id, "tenant_id": tenant.id, "user_id": uid, **config})
        return run.status, f"workflow {a.action_ref} · n8n:{run.source} · {run.detail}"
    if a.action_type == "recipe":
        from ..recipes.catalog import prefill
        from .recipes import _resolve
        recipe = _resolve(session, tenant.id, a.action_ref)
        if not recipe:
            return "failed", f"receta {a.action_ref} no encontrada"
        draft = prefill(recipe, session, tenant, config)
        return "completed", f"caso {recipe['name']}: {str(draft.get('summary', ''))[:160]}"
    if a.action_type == "connector":
        from .integrations import send_to_connector
        return send_to_connector(session, tenant, a.action_ref, {
            "automation": a.name, "tenant_id": tenant.id, **config})
    # notify
    return "completed", config.get("message", "Notificación enviada")


def dispatch_event(session: Session, tenant: Tenant, event: str,
                   payload: dict | None = None, user: User | None = None) -> int:
    """Run all enabled automations subscribed to an event. Returns how many ran."""
    autos = session.exec(
        select(Automation).where(
            Automation.tenant_id == tenant.id, Automation.event == event, Automation.enabled == True)  # noqa: E712
    ).all()
    ran = 0
    for a in autos:
        try:
            status, detail = _run(session, tenant, user, a, payload)
        except Exception as exc:  # never break the triggering action
            status, detail = "failed", f"error: {exc}"
        a.status = status
        a.last_run = datetime.utcnow().isoformat()
        session.add(a)
        session.add(AuditEvent(
            tenant_id=tenant.id, user_id=user.id if user else None, event_type="automation",
            object_type="automation", object_id=a.id,
            risk_level="med" if status == "failed" else "low",
            reason=f"evento '{event}' → '{a.name}' · {status} · {detail}"))
        ran += 1
    if ran:
        session.commit()
    return ran


def run_due(session: Session, tenant: Tenant, frequency: str) -> int:
    """Run enabled scheduled automations of a given frequency (daily/weekly/...)."""
    autos = session.exec(
        select(Automation).where(
            Automation.tenant_id == tenant.id, Automation.trigger == "schedule",
            Automation.schedule == frequency, Automation.enabled == True)  # noqa: E712
    ).all()
    ran = 0
    for a in autos:
        try:
            status, detail = _run(session, tenant, None, a)
        except Exception as exc:
            status, detail = "failed", f"error: {exc}"
        a.status, a.last_run = status, datetime.utcnow().isoformat()
        session.add(a)
        session.add(AuditEvent(
            tenant_id=tenant.id, event_type="automation", object_type="automation", object_id=a.id,
            risk_level="med" if status == "failed" else "low",
            reason=f"programada ({frequency}) '{a.name}' · {status} · {detail}"))
        ran += 1
    if ran:
        session.commit()
    return ran


@router.get("/templates")
def templates(_: User = Depends(get_current_user)) -> list[dict]:
    return TEMPLATES


@router.post("/run-due")
def run_due_endpoint(
    frequency: str = "daily",
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Run this tenant's due scheduled automations. Called by the scheduler or
    an external cron (works on serverless without an in-process scheduler)."""
    return {"frequency": frequency, "ran": run_due(session, tenant, frequency)}


@router.get("")
def list_automations(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(
        select(Automation).where(Automation.tenant_id == tenant.id, Automation.user_id == user.id)
        .order_by(Automation.created_at.desc())
    ).all()
    return [_out(a) for a in rows]


@router.post("", status_code=201)
def create_automation(
    body: AutomationIn,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    a = Automation(
        tenant_id=tenant.id, user_id=user.id, name=body.name.strip(),
        description=body.description.strip(), trigger=body.trigger, schedule=body.schedule,
        event=body.event, action_type=body.action_type, action_ref=body.action_ref.strip(),
        config=json.dumps(body.config),
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return _out(a)


@router.post("/from-template", status_code=201)
def create_from_template(
    body: FromTemplate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    t = get_template(body.template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    a = Automation(
        tenant_id=tenant.id, user_id=user.id, name=t["name"], description=t["description"],
        trigger=t["trigger"], schedule=t["schedule"], event=t["event"],
        action_type=t["action_type"], action_ref=t["action_ref"], config=json.dumps(t["config"]),
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return _out(a)


@router.post("/{automation_id}/toggle")
def toggle(
    automation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    a = _load(session, tenant, user, automation_id)
    a.enabled = not a.enabled
    session.add(a)
    session.commit()
    return {"id": a.id, "enabled": a.enabled}


@router.post("/{automation_id}/run")
def run_now(
    automation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    a = _load(session, tenant, user, automation_id)
    status, detail = _run(session, tenant, user, a)
    a.status = status
    a.last_run = datetime.utcnow().isoformat()
    session.add(a)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="automation",
        object_type="automation", object_id=a.id,
        risk_level="med" if status == "failed" else "low",
        reason=f"automatización '{a.name}' ejecutada · {status} · {detail}",
    ))
    session.commit()
    return {"id": a.id, "status": status, "detail": detail, "last_run": a.last_run}


@router.delete("/{automation_id}")
def delete_automation(
    automation_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    a = _load(session, tenant, user, automation_id)
    session.delete(a)
    session.commit()
    return {"ok": True}
