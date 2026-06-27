"""/actions — Google Workspace / Microsoft 365 action toolkit.

Read actions run immediately. Write actions are gated on human approval ("tú
apruebas"), unless the user granted a standing authorization ("Permitir siempre")
for that action. Everything is tenant/area-scoped and audited.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import actions as catalog
from ..ai.adapters import get_adapter
from ..ai.agent_planner import plan_steps, resolve_refs
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..integrations import actions_exec, token_store
from ..models import ActionGrant, ActionRequest, AuditEvent, ModelRoute, Tenant, User
from .workflows import CATALOG as WORKFLOW_CATALOG, trigger_catalog_workflow

router = APIRouter(prefix="/actions", tags=["actions"])


def _granted(session: Session, tenant_id: str, user_id: str, action: str) -> bool:
    return session.exec(
        select(ActionGrant).where(ActionGrant.tenant_id == tenant_id,
                                  ActionGrant.user_id == user_id, ActionGrant.action == action)
    ).first() is not None


def _label(action: str) -> str:
    if action.startswith("workflow:"):
        wid = action.split(":", 1)[1]
        wf = next((w for w in WORKFLOW_CATALOG if w["id"] == wid), None)
        return f"Workflow · {wf['name']}" if wf else action
    return (catalog.get_action(action) or {}).get("label", action)


def _req_out(r: ActionRequest) -> dict:
    return {"id": r.id, "action": r.action, "label": _label(r.action),
            "provider": r.provider, "params": json.loads(r.params or "{}"),
            "status": r.status, "result": r.result, "created_at": r.created_at.isoformat()}


@router.get("")
def list_actions(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    """Catalog with availability (provider connected?) and standing grants."""
    connected = {c.provider for c in token_store.list_connections(session, tenant.id, user.id)}
    out = []
    for a in catalog.list_actions():
        out.append({**a, "connected": a["provider"] in connected,
                    "granted": _granted(session, tenant.id, user.id, a["id"])})
    return out


def _token(session: Session, tenant: Tenant, user: User, provider: str) -> str:
    tok = token_store.get_valid_access_token(session, tenant, user.id, provider)
    if not tok:
        raise HTTPException(status_code=400, detail=f"Conecta {provider} en Integraciones primero.")
    return tok


def _execute(session: Session, tenant: Tenant, user: User, req: ActionRequest) -> ActionRequest:
    try:
        if req.provider == "n8n":
            wid = req.action.split(":", 1)[1]
            res = trigger_catalog_workflow(session, tenant, user, wid, json.loads(req.params or "{}"))
            req.result = f"workflow {res['status']} ({res['source']}) · {res['detail']}"[:240]
            req.status = "executed"
        else:
            token = _token(session, tenant, user, req.provider)
            req.result = actions_exec.execute(req.action, token, json.loads(req.params or "{}"))
            req.status = "executed"
    except HTTPException:
        raise
    except Exception as exc:
        req.status = "failed"
        req.result = f"Error: {exc}"
    session.add(req)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="action", object_type="action",
        object_id=req.action, risk_level="med", reason=f"{req.action} → {req.status}: {str(req.result or '')[:80]}",
    ))
    session.commit()
    session.refresh(req)
    return req


class RunBody(BaseModel):
    action: str
    params: dict = {}


@router.post("/run")
def run_action(
    body: RunBody,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    meta = catalog.get_action(body.action)
    if not meta:
        raise HTTPException(status_code=404, detail="Acción desconocida")
    req = ActionRequest(tenant_id=tenant.id, user_id=user.id, provider=meta["provider"],
                        action=body.action, params=json.dumps(body.params))
    # Read actions and pre-authorized write actions run now; other writes wait.
    if not meta.get("write") or _granted(session, tenant.id, user.id, body.action):
        session.add(req)
        session.commit()
        session.refresh(req)
        return {"status": "done", "request": _req_out(_execute(session, tenant, user, req))}
    req.status = "pending"
    session.add(req)
    session.commit()
    session.refresh(req)
    return {"status": "pending", "request": _req_out(req)}


class AgentBody(BaseModel):
    instruction: str
    auto_approve: bool = False   # ejecuta también escrituras sin pedir aprobación


@router.post("/agent")
def agent_run(
    body: AgentBody,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Agente de acciones: el modelo traduce una instrucción en pasos del toolkit y
    los ejecuta «por detrás». Lecturas y escrituras autorizadas corren al momento;
    el resto queda **pendiente de aprobación**. Todo auditado."""
    # Herramientas disponibles: acciones de proveedores conectados + workflows n8n.
    connected = {c.provider for c in token_store.list_connections(session, tenant.id, user.id)}
    allowed = [a for a in catalog.list_actions() if a["provider"] in connected]
    workflows = [{"id": w["id"], "name": w["name"], "steps": w["steps"]} for w in WORKFLOW_CATALOG]
    if not allowed and not workflows:
        raise HTTPException(status_code=400, detail="Conecta Google o Microsoft en Integraciones primero.")

    # Planifica con el modelo (ruta abierta/NaN); cae a heurística si no hay modelo real.
    adapter = get_adapter(ModelRoute.OPEN)
    plan = plan_steps(body.instruction, allowed, adapter=adapter, workflows=workflows)

    results: list[dict] = []
    outputs: dict[int, str] = {}   # salida (1-based) de pasos ejecutados, para encadenar
    for i, step in enumerate(plan["steps"], start=1):
        action = step["action"]
        is_wf = action.startswith("workflow:")
        if is_wf:
            provider, write = "n8n", True
        else:
            meta = catalog.get_action(action)
            if not meta:
                continue
            provider, write = meta["provider"], bool(meta.get("write"))
        # Encadenamiento: sustituye {{stepN}} por la salida de pasos previos.
        params = resolve_refs(step.get("params", {}), outputs)
        req = ActionRequest(tenant_id=tenant.id, user_id=user.id, provider=provider,
                            action=action, params=json.dumps(params))
        run_now = (not write) or body.auto_approve or _granted(session, tenant.id, user.id, action)
        if run_now:
            session.add(req); session.commit(); session.refresh(req)
            out = _req_out(_execute(session, tenant, user, req))
            out["step_status"] = "ejecutado"
            outputs[i] = str(out.get("result") or "")
        else:
            req.status = "pending"
            session.add(req); session.commit(); session.refresh(req)
            out = _req_out(req)
            out["step_status"] = "pendiente_aprobación"
        out["reason"] = step.get("reason", "")
        results.append(out)

    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="agent", object_type="agent_run",
        object_id="actions", risk_level="med",
        reason=f"agente: {len(results)} paso(s) [{plan['source']}] — {body.instruction[:80]}",
    ))
    session.commit()
    return {"instruction": body.instruction, "source": plan["source"], "note": plan.get("note", ""),
            "steps": results}


@router.get("/requests")
def list_requests(
    status: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    q = select(ActionRequest).where(ActionRequest.tenant_id == tenant.id, ActionRequest.user_id == user.id)
    if status:
        q = q.where(ActionRequest.status == status)
    rows = session.exec(q.order_by(ActionRequest.created_at.desc()).limit(50)).all()
    return [_req_out(r) for r in rows]


def _owned_req(session, tenant, user, req_id) -> ActionRequest:
    r = session.get(ActionRequest, req_id)
    if not r or r.tenant_id != tenant.id or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    return r


@router.post("/requests/{req_id}/approve")
def approve_request(
    req_id: str, always: bool = False,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    req = _owned_req(session, tenant, user, req_id)
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="La solicitud ya no está pendiente")
    if always and not _granted(session, tenant.id, user.id, req.action):
        session.add(ActionGrant(tenant_id=tenant.id, user_id=user.id, action=req.action))
        session.commit()
    return {"request": _req_out(_execute(session, tenant, user, req))}


@router.post("/requests/{req_id}/reject")
def reject_request(
    req_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    req = _owned_req(session, tenant, user, req_id)
    req.status = "rejected"
    session.add(req)
    session.commit()
    return {"request": _req_out(req)}


# --- standing authorizations ("Permitir siempre") ---------------------------
@router.get("/grants")
def list_grants(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(
        select(ActionGrant).where(ActionGrant.tenant_id == tenant.id, ActionGrant.user_id == user.id)
    ).all()
    return [{"action": g.action, "label": (catalog.get_action(g.action) or {}).get("label", g.action)} for g in rows]


@router.delete("/grants/{action}")
def revoke_grant(
    action: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    rows = session.exec(
        select(ActionGrant).where(ActionGrant.tenant_id == tenant.id,
                                  ActionGrant.user_id == user.id, ActionGrant.action == action)
    ).all()
    for g in rows:
        session.delete(g)
    session.commit()
    return {"ok": True, "revoked": len(rows)}
