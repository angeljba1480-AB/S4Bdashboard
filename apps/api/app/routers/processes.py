"""/processes — Procesos de Negocio (BPM ligero): Línea → Servicio → Proceso → Paso.

La columna vertebral: mapea qué hace la empresa (líneas), qué entrega (servicios internos
con OLA / externos con SLA a clientes), cómo (procesos y pasos) y prepara el terreno para
ligar cada paso a un agente/automatización y medir su beneficio (fases posteriores).
Todo multi-tenant y auditado. Ver docs/DISENO-PROCESOS-NEGOCIO.md.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import (
    AuditEvent,
    BusinessLine,
    BusinessProcess,
    BusinessService,
    CanvasLayout,
    ProcessStep,
    ServiceClient,
    StepLink,
    StepMetric,
    Tenant,
    User,
)

router = APIRouter(prefix="/processes", tags=["processes"])

_KINDS = {"internal", "external"}
_STATES = {"manual", "candidate", "automated"}


def _audit(session, tenant, user, event, obj_type, obj_id, reason):
    session.add(AuditEvent(tenant_id=tenant.id, user_id=user.id, event_type=event,
                           object_type=obj_type, object_id=obj_id, risk_level="low", reason=reason))


def _owned(session, model, obj_id, tenant):
    row = session.get(model, obj_id)
    if not row or row.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="No encontrado")
    return row


# ----------------------------- Líneas ---------------------------------------
class LineIn(BaseModel):
    name: str
    description: str = ""


def _line_out(x: BusinessLine) -> dict:
    return {"id": x.id, "name": x.name, "description": x.description, "created_at": x.created_at.isoformat()}


@router.get("/lines")
def list_lines(tenant: Tenant = Depends(get_current_tenant), _: User = Depends(get_current_user),
               session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(select(BusinessLine).where(BusinessLine.tenant_id == tenant.id)
                        .order_by(BusinessLine.created_at)).all()
    return [_line_out(x) for x in rows]


@router.post("/lines", status_code=201)
def create_line(body: LineIn, tenant: Tenant = Depends(get_current_tenant),
                user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    x = BusinessLine(tenant_id=tenant.id, name=body.name.strip(), description=body.description.strip())
    session.add(x)
    _audit(session, tenant, user, "process_line_create", "business_line", x.id, f"línea creada: {x.name}")
    session.commit(); session.refresh(x)
    return _line_out(x)


@router.put("/lines/{line_id}")
def update_line(line_id: str, body: LineIn, tenant: Tenant = Depends(get_current_tenant),
                _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    x = _owned(session, BusinessLine, line_id, tenant)
    x.name = body.name.strip() or x.name
    x.description = body.description.strip()
    session.add(x); session.commit(); session.refresh(x)
    return _line_out(x)


@router.delete("/lines/{line_id}")
def delete_line(line_id: str, tenant: Tenant = Depends(get_current_tenant),
                _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    x = _owned(session, BusinessLine, line_id, tenant)
    services = session.exec(select(BusinessService).where(BusinessService.line_id == line_id)).all()
    if services:
        raise HTTPException(status_code=409, detail="La línea tiene servicios; bórralos primero.")
    session.delete(x); session.commit()
    return {"ok": True}


# ----------------------------- Servicios ------------------------------------
class ServiceIn(BaseModel):
    line_id: str
    name: str
    kind: str = "external"      # internal (OLA) | external (SLA)
    sla_ola: str = ""
    description: str = ""


def _service_out(x: BusinessService, clients: list[str] | None = None) -> dict:
    return {"id": x.id, "line_id": x.line_id, "name": x.name, "kind": x.kind,
            "sla_ola": x.sla_ola, "description": x.description,
            "clients": clients if clients is not None else [],
            "created_at": x.created_at.isoformat()}


@router.get("/services")
def list_services(line_id: str = "", tenant: Tenant = Depends(get_current_tenant),
                  _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[dict]:
    q = select(BusinessService).where(BusinessService.tenant_id == tenant.id)
    if line_id:
        q = q.where(BusinessService.line_id == line_id)
    rows = session.exec(q.order_by(BusinessService.created_at)).all()
    out = []
    for x in rows:
        cl = session.exec(select(ServiceClient).where(ServiceClient.service_id == x.id)).all()
        out.append(_service_out(x, [c.client_name for c in cl]))
    return out


@router.post("/services", status_code=201)
def create_service(body: ServiceIn, tenant: Tenant = Depends(get_current_tenant),
                   user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    if body.kind not in _KINDS:
        raise HTTPException(status_code=422, detail="kind debe ser 'internal' u 'external'")
    _owned(session, BusinessLine, body.line_id, tenant)  # valida pertenencia
    x = BusinessService(tenant_id=tenant.id, line_id=body.line_id, name=body.name.strip(),
                        kind=body.kind, sla_ola=body.sla_ola.strip(), description=body.description.strip())
    session.add(x)
    _audit(session, tenant, user, "process_service_create", "business_service", x.id,
           f"servicio {body.kind} creado: {x.name}")
    session.commit(); session.refresh(x)
    return _service_out(x, [])


@router.put("/services/{service_id}")
def update_service(service_id: str, body: ServiceIn, tenant: Tenant = Depends(get_current_tenant),
                   _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if body.kind not in _KINDS:
        raise HTTPException(status_code=422, detail="kind debe ser 'internal' u 'external'")
    x = _owned(session, BusinessService, service_id, tenant)
    x.name = body.name.strip() or x.name
    x.kind = body.kind
    x.sla_ola = body.sla_ola.strip()
    x.description = body.description.strip()
    session.add(x); session.commit(); session.refresh(x)
    cl = session.exec(select(ServiceClient).where(ServiceClient.service_id == x.id)).all()
    return _service_out(x, [c.client_name for c in cl])


@router.delete("/services/{service_id}")
def delete_service(service_id: str, tenant: Tenant = Depends(get_current_tenant),
                   _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    x = _owned(session, BusinessService, service_id, tenant)
    if session.exec(select(BusinessProcess).where(BusinessProcess.service_id == service_id)).all():
        raise HTTPException(status_code=409, detail="El servicio tiene procesos; bórralos primero.")
    for c in session.exec(select(ServiceClient).where(ServiceClient.service_id == service_id)).all():
        session.delete(c)
    session.delete(x); session.commit()
    return {"ok": True}


# --- clientes ligados a un servicio (externo) ---
class ClientIn(BaseModel):
    client_name: str


@router.post("/services/{service_id}/clients", status_code=201)
def add_client(service_id: str, body: ClientIn, tenant: Tenant = Depends(get_current_tenant),
               _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    svc = _owned(session, BusinessService, service_id, tenant)
    if svc.kind != "external":
        raise HTTPException(status_code=422, detail="Solo los servicios externos (SLA) tienen clientes.")
    name = body.client_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="client_name es obligatorio")
    session.add(ServiceClient(tenant_id=tenant.id, service_id=service_id, client_name=name))
    session.commit()
    cl = session.exec(select(ServiceClient).where(ServiceClient.service_id == service_id)).all()
    return {"service_id": service_id, "clients": [c.client_name for c in cl]}


@router.delete("/services/{service_id}/clients/{client_name}")
def remove_client(service_id: str, client_name: str, tenant: Tenant = Depends(get_current_tenant),
                  _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    _owned(session, BusinessService, service_id, tenant)
    rows = session.exec(select(ServiceClient).where(ServiceClient.service_id == service_id,
                                                    ServiceClient.client_name == client_name)).all()
    for r in rows:
        session.delete(r)
    session.commit()
    return {"ok": True, "removed": len(rows)}


# ----------------------------- Procesos -------------------------------------
class ProcessIn(BaseModel):
    service_id: str
    name: str
    description: str = ""


def _process_out(x: BusinessProcess) -> dict:
    return {"id": x.id, "service_id": x.service_id, "name": x.name, "description": x.description,
            "created_at": x.created_at.isoformat()}


@router.get("/processes")
def list_processes(service_id: str = "", tenant: Tenant = Depends(get_current_tenant),
                   _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[dict]:
    q = select(BusinessProcess).where(BusinessProcess.tenant_id == tenant.id)
    if service_id:
        q = q.where(BusinessProcess.service_id == service_id)
    return [_process_out(x) for x in session.exec(q.order_by(BusinessProcess.created_at)).all()]


@router.post("/processes", status_code=201)
def create_process(body: ProcessIn, tenant: Tenant = Depends(get_current_tenant),
                   user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    _owned(session, BusinessService, body.service_id, tenant)
    x = BusinessProcess(tenant_id=tenant.id, service_id=body.service_id, name=body.name.strip(),
                        description=body.description.strip())
    session.add(x)
    _audit(session, tenant, user, "process_create", "business_process", x.id, f"proceso creado: {x.name}")
    session.commit(); session.refresh(x)
    return _process_out(x)


@router.put("/processes/{process_id}")
def update_process(process_id: str, body: ProcessIn, tenant: Tenant = Depends(get_current_tenant),
                   _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    x = _owned(session, BusinessProcess, process_id, tenant)
    x.name = body.name.strip() or x.name
    x.description = body.description.strip()
    session.add(x); session.commit(); session.refresh(x)
    return _process_out(x)


@router.delete("/processes/{process_id}")
def delete_process(process_id: str, tenant: Tenant = Depends(get_current_tenant),
                   _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    x = _owned(session, BusinessProcess, process_id, tenant)
    for s in session.exec(select(ProcessStep).where(ProcessStep.process_id == process_id)).all():
        session.delete(s)
    session.delete(x); session.commit()
    return {"ok": True}


# ----------------------------- Pasos ----------------------------------------
class StepIn(BaseModel):
    process_id: str
    name: str
    description: str = ""
    order: int = 0
    automation_state: str = "manual"


def _step_out(x: ProcessStep) -> dict:
    return {"id": x.id, "process_id": x.process_id, "name": x.name, "description": x.description,
            "order": x.order, "automation_state": x.automation_state, "created_at": x.created_at.isoformat()}


@router.get("/steps")
def list_steps(process_id: str = "", tenant: Tenant = Depends(get_current_tenant),
               _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[dict]:
    q = select(ProcessStep).where(ProcessStep.tenant_id == tenant.id)
    if process_id:
        q = q.where(ProcessStep.process_id == process_id)
    return [_step_out(x) for x in session.exec(q.order_by(ProcessStep.order, ProcessStep.created_at)).all()]


@router.post("/steps", status_code=201)
def create_step(body: StepIn, tenant: Tenant = Depends(get_current_tenant),
                user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    if body.automation_state not in _STATES:
        raise HTTPException(status_code=422, detail="automation_state inválido")
    _owned(session, BusinessProcess, body.process_id, tenant)
    x = ProcessStep(tenant_id=tenant.id, process_id=body.process_id, name=body.name.strip(),
                    description=body.description.strip(), order=body.order,
                    automation_state=body.automation_state)
    session.add(x)
    _audit(session, tenant, user, "process_step_create", "process_step", x.id, f"paso creado: {x.name}")
    session.commit(); session.refresh(x)
    return _step_out(x)


@router.put("/steps/{step_id}")
def update_step(step_id: str, body: StepIn, tenant: Tenant = Depends(get_current_tenant),
                _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    if body.automation_state not in _STATES:
        raise HTTPException(status_code=422, detail="automation_state inválido")
    x = _owned(session, ProcessStep, step_id, tenant)
    x.name = body.name.strip() or x.name
    x.description = body.description.strip()
    x.order = body.order
    x.automation_state = body.automation_state
    session.add(x); session.commit(); session.refresh(x)
    return _step_out(x)


@router.delete("/steps/{step_id}")
def delete_step(step_id: str, tenant: Tenant = Depends(get_current_tenant),
                _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    x = _owned(session, ProcessStep, step_id, tenant)
    session.delete(x); session.commit()
    return {"ok": True}


# ----------------------------- Árbol (para el canvas) -----------------------
@router.get("/tree")
def tree(tenant: Tenant = Depends(get_current_tenant), _: User = Depends(get_current_user),
         session: Session = Depends(get_session)) -> dict:
    """Estructura completa Línea→Servicio→Proceso→Paso del tenant, para el lienzo."""
    lines = session.exec(select(BusinessLine).where(BusinessLine.tenant_id == tenant.id)).all()
    services = session.exec(select(BusinessService).where(BusinessService.tenant_id == tenant.id)).all()
    procs = session.exec(select(BusinessProcess).where(BusinessProcess.tenant_id == tenant.id)).all()
    steps = session.exec(select(ProcessStep).where(ProcessStep.tenant_id == tenant.id)).all()
    clients = session.exec(select(ServiceClient).where(ServiceClient.tenant_id == tenant.id)).all()
    cl_by_svc: dict[str, list[str]] = {}
    for c in clients:
        cl_by_svc.setdefault(c.service_id, []).append(c.client_name)
    steps_by_proc: dict[str, list] = {}
    for s in sorted(steps, key=lambda s: (s.order, s.created_at)):
        steps_by_proc.setdefault(s.process_id, []).append(_step_out(s))
    procs_by_svc: dict[str, list] = {}
    for p in procs:
        procs_by_svc.setdefault(p.service_id, []).append(
            {**_process_out(p), "steps": steps_by_proc.get(p.id, [])})
    svcs_by_line: dict[str, list] = {}
    for x in services:
        svcs_by_line.setdefault(x.line_id, []).append(
            {**_service_out(x, cl_by_svc.get(x.id, [])), "processes": procs_by_svc.get(x.id, [])})
    return {"lines": [{**_line_out(ln), "services": svcs_by_line.get(ln.id, [])} for ln in lines]}


# =============================================================================
# Fase 3 — Trazabilidad (paso ↔ agente/automatización) y ROI real
# =============================================================================
_LINK_TYPES = {"agent", "automation", "recipe"}
_PHASES = {"baseline", "after"}


def _role_rate(role: str) -> float:
    """Costo-hora del rol tomado del Tablero Financiero (Concentrado BC), si existe."""
    if not role:
        return 0.0
    try:
        from ..finance import seed as _fseed
        for r in (_fseed.cost_per_hour().get("by_role") or []):
            if str(r.get("rol", "")).strip().lower() == role.strip().lower():
                return float(r.get("costo_hora") or 0)
    except Exception:
        pass
    return 0.0


# ----------------------------- Links (trazabilidad) -------------------------
class LinkIn(BaseModel):
    target_type: str = "agent"
    target_id: str = ""
    target_name: str


@router.get("/steps/{step_id}/links")
def list_links(step_id: str, tenant: Tenant = Depends(get_current_tenant),
               _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> list[dict]:
    _owned(session, ProcessStep, step_id, tenant)
    rows = session.exec(select(StepLink).where(StepLink.step_id == step_id)).all()
    return [{"id": x.id, "target_type": x.target_type, "target_id": x.target_id,
             "target_name": x.target_name} for x in rows]


@router.post("/steps/{step_id}/links", status_code=201)
def add_link(step_id: str, body: LinkIn, tenant: Tenant = Depends(get_current_tenant),
             user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    step = _owned(session, ProcessStep, step_id, tenant)
    if body.target_type not in _LINK_TYPES:
        raise HTTPException(status_code=422, detail="target_type inválido")
    if not body.target_name.strip():
        raise HTTPException(status_code=422, detail="target_name es obligatorio")
    x = StepLink(tenant_id=tenant.id, step_id=step_id, target_type=body.target_type,
                 target_id=body.target_id, target_name=body.target_name.strip())
    session.add(x)
    # ligar un recurso marca el paso como automatizado
    if step.automation_state != "automated":
        step.automation_state = "automated"
        session.add(step)
    _audit(session, tenant, user, "process_step_link", "process_step", step_id,
           f"paso ligado a {body.target_type}: {body.target_name}")
    session.commit(); session.refresh(x)
    return {"id": x.id, "target_type": x.target_type, "target_id": x.target_id, "target_name": x.target_name}


@router.delete("/links/{link_id}")
def delete_link(link_id: str, tenant: Tenant = Depends(get_current_tenant),
                _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    x = _owned(session, StepLink, link_id, tenant)
    session.delete(x); session.commit()
    return {"ok": True}


# ----------------------------- Métricas (baseline/after) --------------------
class MetricIn(BaseModel):
    phase: str = "baseline"
    hours_per_cycle: float = 0.0
    role: str = ""
    cost_per_cycle: float = 0.0
    cycle_time_hours: float = 0.0
    errors: float = 0.0
    volume_month: float = 0.0


def _metric_out(m: StepMetric) -> dict:
    return {"id": m.id, "phase": m.phase, "hours_per_cycle": m.hours_per_cycle, "role": m.role,
            "cost_per_cycle": m.cost_per_cycle, "cycle_time_hours": m.cycle_time_hours,
            "errors": m.errors, "volume_month": m.volume_month}


@router.get("/steps/{step_id}/metrics")
def list_metrics(step_id: str, tenant: Tenant = Depends(get_current_tenant),
                 _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    _owned(session, ProcessStep, step_id, tenant)
    rows = session.exec(select(StepMetric).where(StepMetric.step_id == step_id)).all()
    out = {m.phase: _metric_out(m) for m in rows}
    return {"baseline": out.get("baseline"), "after": out.get("after")}


@router.put("/steps/{step_id}/metrics")
def upsert_metric(step_id: str, body: MetricIn, tenant: Tenant = Depends(get_current_tenant),
                  _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    _owned(session, ProcessStep, step_id, tenant)
    if body.phase not in _PHASES:
        raise HTTPException(status_code=422, detail="phase debe ser 'baseline' u 'after'")
    # Costo por ciclo: si no se da, se deriva de horas × costo-hora del rol (Tablero).
    cost = body.cost_per_cycle
    if cost <= 0 and body.hours_per_cycle > 0 and body.role:
        cost = round(body.hours_per_cycle * _role_rate(body.role), 2)
    row = session.exec(select(StepMetric).where(StepMetric.step_id == step_id,
                                                StepMetric.phase == body.phase)).first()
    if row is None:
        row = StepMetric(tenant_id=tenant.id, step_id=step_id, phase=body.phase)
    row.hours_per_cycle = body.hours_per_cycle
    row.role = body.role.strip()
    row.cost_per_cycle = cost
    row.cycle_time_hours = body.cycle_time_hours
    row.errors = body.errors
    row.volume_month = body.volume_month
    session.add(row); session.commit(); session.refresh(row)
    return _metric_out(row)


# ----------------------------- ROI ------------------------------------------
def _step_savings(session, step_id: str) -> dict | None:
    """Ahorro mensual de un paso = (costo_antes − costo_después) × volumen."""
    rows = {m.phase: m for m in session.exec(select(StepMetric).where(StepMetric.step_id == step_id)).all()}
    b, a = rows.get("baseline"), rows.get("after")
    if not b:
        return None
    vol = (a.volume_month if a and a.volume_month else b.volume_month) or 0
    cost_after = a.cost_per_cycle if a else 0.0
    hours_after = a.hours_per_cycle if a else 0.0
    save_cycle = b.cost_per_cycle - cost_after
    save_month = round(save_cycle * vol, 2)
    hours_month = round((b.hours_per_cycle - hours_after) * vol, 2)
    return {"savings_per_cycle": round(save_cycle, 2), "savings_month": save_month,
            "hours_saved_month": hours_month, "volume_month": vol,
            "has_after": a is not None}


@router.get("/roi")
def roi(tenant: Tenant = Depends(get_current_tenant), _: User = Depends(get_current_user),
        session: Session = Depends(get_session)) -> dict:
    """Rollup de ahorro por paso → servicio → línea (y por cliente en externos)."""
    lines = {x.id: x for x in session.exec(select(BusinessLine).where(BusinessLine.tenant_id == tenant.id)).all()}
    services = {x.id: x for x in session.exec(select(BusinessService).where(BusinessService.tenant_id == tenant.id)).all()}
    procs = {x.id: x for x in session.exec(select(BusinessProcess).where(BusinessProcess.tenant_id == tenant.id)).all()}
    steps = session.exec(select(ProcessStep).where(ProcessStep.tenant_id == tenant.id)).all()
    clients = session.exec(select(ServiceClient).where(ServiceClient.tenant_id == tenant.id)).all()
    cl_by_svc: dict[str, list[str]] = {}
    for c in clients:
        cl_by_svc.setdefault(c.service_id, []).append(c.client_name)

    by_service: dict[str, dict] = {}
    by_line: dict[str, dict] = {}
    by_client: dict[str, dict] = {}
    total = {"savings_month": 0.0, "hours_saved_month": 0.0, "steps_measured": 0, "steps_automated": 0}
    step_savings: dict[str, dict] = {}

    for st in steps:
        sv = _step_savings(session, st.id)
        if not sv:
            continue
        step_savings[st.id] = sv
        total["steps_measured"] += 1
        if sv["has_after"]:
            total["steps_automated"] += 1
        total["savings_month"] += sv["savings_month"]
        total["hours_saved_month"] += sv["hours_saved_month"]
        proc = procs.get(st.process_id)
        svc = services.get(proc.service_id) if proc else None
        if not svc:
            continue
        s = by_service.setdefault(svc.id, {"name": svc.name, "kind": svc.kind, "savings_month": 0.0,
                                           "clients": cl_by_svc.get(svc.id, [])})
        s["savings_month"] += sv["savings_month"]
        ln = lines.get(svc.line_id)
        if ln:
            lentry = by_line.setdefault(ln.id, {"name": ln.name, "savings_month": 0.0})
            lentry["savings_month"] += sv["savings_month"]
        for cname in cl_by_svc.get(svc.id, []):
            centry = by_client.setdefault(cname, {"name": cname, "savings_month": 0.0})
            centry["savings_month"] += sv["savings_month"]

    total["savings_month"] = round(total["savings_month"], 2)
    total["hours_saved_month"] = round(total["hours_saved_month"], 2)
    total["savings_year"] = round(total["savings_month"] * 12, 2)
    _round = lambda d: {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()}
    return {
        "total": total,
        "by_service": [{"id": k, **_round(v)} for k, v in sorted(by_service.items(), key=lambda x: -x[1]["savings_month"])],
        "by_line": [{"id": k, **_round(v)} for k, v in sorted(by_line.items(), key=lambda x: -x[1]["savings_month"])],
        "by_client": [{**_round(v)} for v in sorted(by_client.values(), key=lambda x: -x["savings_month"])],
        "step_savings": step_savings,
        "roles": [r.get("rol") for r in (__import__("app.finance.seed", fromlist=["cost_per_hour"]).cost_per_hour().get("by_role") or [])],
    }


# ----------------------------- Lienzo: posiciones ---------------------------
class LayoutIn(BaseModel):
    positions: dict


@router.get("/canvas-layout")
def get_layout(tenant: Tenant = Depends(get_current_tenant), _: User = Depends(get_current_user),
               session: Session = Depends(get_session)) -> dict:
    import json
    row = session.get(CanvasLayout, tenant.id)
    try:
        return {"positions": json.loads(row.data) if row and row.data else {}}
    except Exception:
        return {"positions": {}}


@router.put("/canvas-layout")
def save_layout(body: LayoutIn, tenant: Tenant = Depends(get_current_tenant),
                _: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    import json
    from datetime import datetime
    # Sanitiza: solo {id: {x:int, y:int}}
    clean: dict[str, dict] = {}
    for k, v in (body.positions or {}).items():
        if isinstance(v, dict) and "x" in v and "y" in v:
            try:
                clean[str(k)] = {"x": round(float(v["x"])), "y": round(float(v["y"]))}
            except (ValueError, TypeError):
                continue
    row = session.get(CanvasLayout, tenant.id)
    if row is None:
        row = CanvasLayout(tenant_id=tenant.id)
    row.data = json.dumps(clean)
    row.updated_at = datetime.utcnow()
    session.add(row); session.commit()
    return {"ok": True, "count": len(clean)}
