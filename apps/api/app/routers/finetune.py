"""/finetune — pipeline de fine-tuning ligero (LoRA), Fase 5 del blueprint.

Andamiaje independiente de la GPU: datasets versionados, anonimización, gate de
calidad/red-team, export JSONL y despacho del entrenamiento a un trainer externo
(servidor con GPU / App NaN / webhook n8n). El adapter resultante se sirve como
ruta local/VPC compatible OpenAI. Solo ADMIN/DEVOPS.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from .. import finetune as ft
from ..auth import get_current_tenant, get_current_user, require_roles
from ..config import settings
from ..db import get_session
from ..models import (AuditEvent, FineTuneDataset, FineTuneExample, FineTuneJob,
                      MemoryItem, Role, Tenant, User)

router = APIRouter(prefix="/finetune", tags=["finetune"])


def _ds_out(d: FineTuneDataset, n: int) -> dict:
    return {"id": d.id, "name": d.name, "area": d.area or "", "base_model": d.base_model,
            "status": d.status, "version": d.version, "examples": n, "created_at": d.created_at.isoformat()}


def _job_out(j: FineTuneJob) -> dict:
    return {"id": j.id, "dataset_id": j.dataset_id, "base_model": j.base_model, "status": j.status,
            "adapter_uri": j.adapter_uri, "serve_base_url": j.serve_base_url,
            "metrics": json.loads(j.metrics or "{}"), "reason": j.reason, "created_at": j.created_at.isoformat()}


def _count(session, ds_id) -> int:
    return len(session.exec(select(FineTuneExample).where(FineTuneExample.dataset_id == ds_id)).all())


def _owned_ds(session, tenant, ds_id) -> FineTuneDataset:
    d = session.get(FineTuneDataset, ds_id)
    if not d or d.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Dataset no encontrado")
    return d


def _examples(session, ds_id) -> list[tuple[str, str]]:
    rows = session.exec(select(FineTuneExample).where(FineTuneExample.dataset_id == ds_id)).all()
    return [(e.prompt, e.completion) for e in rows]


# --- datasets ---------------------------------------------------------------
class DatasetIn(BaseModel):
    name: str
    area: str = ""
    base_model: str = ""


@router.post("/datasets", status_code=201)
def create_dataset(body: DatasetIn, _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                   tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> dict:
    d = FineTuneDataset(tenant_id=tenant.id, name=body.name.strip() or "Dataset",
                        area=body.area.strip(), base_model=body.base_model.strip() or settings.finetune_default_base_model)
    session.add(d); session.commit(); session.refresh(d)
    return _ds_out(d, 0)


@router.get("/datasets")
def list_datasets(_: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                  tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(select(FineTuneDataset).where(FineTuneDataset.tenant_id == tenant.id)).all()
    return [_ds_out(d, _count(session, d.id)) for d in rows]


class ExampleIn(BaseModel):
    prompt: str
    completion: str
    source: str = "manual"


@router.post("/datasets/{ds_id}/examples", status_code=201)
def add_example(ds_id: str, body: ExampleIn, _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> dict:
    d = _owned_ds(session, tenant, ds_id)
    if not body.prompt.strip() or not body.completion.strip():
        raise HTTPException(status_code=422, detail="prompt y completion son obligatorios")
    # Anonimiza antes de guardar (irreversible-looking).
    e = FineTuneExample(tenant_id=tenant.id, dataset_id=d.id, source=body.source,
                        prompt=ft.anonymize(body.prompt), completion=ft.anonymize(body.completion))
    session.add(e); session.commit()
    return {"id": e.id, "examples": _count(session, d.id)}


class FromMemoryIn(BaseModel):
    tag: str = ""
    limit: int = 50


@router.post("/datasets/{ds_id}/from-memory")
def from_memory(ds_id: str, body: FromMemoryIn, _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> dict:
    """Construye ejemplos a partir de trabajos guardados en Memoria (comportamiento:
    título→prompt, contenido→completion). Anonimizado."""
    d = _owned_ds(session, tenant, ds_id)
    q = select(MemoryItem).where(MemoryItem.tenant_id == tenant.id)
    rows = session.exec(q.order_by(MemoryItem.created_at.desc()).limit(max(1, min(body.limit, 200)))).all()
    added = 0
    for m in rows:
        if body.tag and body.tag not in (m.tags or ""):
            continue
        if not m.title.strip() or not m.content.strip():
            continue
        session.add(FineTuneExample(tenant_id=tenant.id, dataset_id=d.id, source="memory",
                                    prompt=ft.anonymize(m.title), completion=ft.anonymize(m.content)))
        added += 1
    session.commit()
    return {"added": added, "examples": _count(session, d.id)}


@router.get("/datasets/{ds_id}/export", response_class=PlainTextResponse)
def export_jsonl(ds_id: str, _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                 tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> str:
    _owned_ds(session, tenant, ds_id)
    return ft.to_jsonl(_examples(session, ds_id))


@router.post("/datasets/{ds_id}/check")
def check_dataset(ds_id: str, _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                  tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> dict:
    """Gate de calidad + red-team. Si pasa, marca el dataset como 'ready'."""
    d = _owned_ds(session, tenant, ds_id)
    report = ft.quality_gate(_examples(session, ds_id))
    d.status = "ready" if report["ok"] else "draft"
    session.add(d); session.commit()
    return {"status": d.status, **report}


# --- jobs -------------------------------------------------------------------
class JobIn(BaseModel):
    dataset_id: str
    base_model: str = ""


@router.post("/jobs", status_code=201)
def create_job(body: JobIn, user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
               tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> dict:
    d = _owned_ds(session, tenant, body.dataset_id)
    examples = _examples(session, d.id)
    gate = ft.quality_gate(examples)
    if not gate["ok"]:
        raise HTTPException(status_code=422, detail="El dataset no pasa el gate de calidad: " + "; ".join(gate["issues"]))
    base = body.base_model.strip() or d.base_model or settings.finetune_default_base_model
    job = FineTuneJob(tenant_id=tenant.id, dataset_id=d.id, base_model=base)
    session.add(job); session.commit(); session.refresh(job)
    ollama_name = ft.suggest_ollama_name(d.name, d.version)
    out = ft.dispatch_training(job.id, base, examples, ollama_name=ollama_name)
    job.status = out["status"]; job.reason = out.get("reason", "")
    session.add(job)
    session.add(AuditEvent(tenant_id=tenant.id, user_id=user.id, event_type="finetune", object_type="finetune_job",
                           object_id=job.id, risk_level="low", reason=f"job {job.status}: {base} ({len(examples)} ej.)"))
    session.commit(); session.refresh(job)
    return _job_out(job)


@router.get("/jobs")
def list_jobs(_: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
              tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> list[dict]:
    rows = session.exec(select(FineTuneJob).where(FineTuneJob.tenant_id == tenant.id)
                        .order_by(FineTuneJob.created_at.desc())).all()
    return [_job_out(j) for j in rows]


class CallbackIn(BaseModel):
    status: str
    adapter_uri: str = ""
    serve_base_url: str = ""
    metrics: dict = {}


@router.post("/jobs/{job_id}/callback")
def job_callback(job_id: str, body: CallbackIn, user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
                 tenant: Tenant = Depends(get_current_tenant), session: Session = Depends(get_session)) -> dict:
    """El trainer (GPU/n8n) reporta el resultado del entrenamiento aquí."""
    j = session.get(FineTuneJob, job_id)
    if not j or j.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    j.status = body.status.strip() or j.status
    j.adapter_uri = body.adapter_uri or j.adapter_uri
    j.serve_base_url = body.serve_base_url or j.serve_base_url
    j.metrics = json.dumps(body.metrics or {})
    session.add(j)
    session.add(AuditEvent(tenant_id=tenant.id, user_id=user.id, event_type="finetune", object_type="finetune_job",
                           object_id=j.id, risk_level="low", reason=f"callback: {j.status}"))
    session.commit(); session.refresh(j)
    return _job_out(j)
