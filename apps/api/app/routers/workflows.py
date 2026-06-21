"""Workflows endpoint (blueprint section 9). Triggers real n8n workflows via
webhook when configured; otherwise records a simulated run + audit."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth import get_current_tenant, get_current_user
from ..config import settings
from ..db import get_session
from ..integrations.n8n import resolve_n8n, trigger_workflow
from ..integrations.n8n_provision import (
    ensure_tenant_workflows,
    is_available as is_provision_available,
)
from ..models import AuditEvent, Tenant, User

router = APIRouter(prefix="/workflows", tags=["workflows"])

CATALOG = [
    {"id": "ingesta", "name": "Ingesta documental",
     "steps": "Upload → antivirus → hash → OCR → clasificación → PII → chunking → embeddings → índice"},
    {"id": "rag", "name": "Consulta RAG",
     "steps": "Prompt → policy → retrieval → reranking → minimización → modelo → fuentes → auditoría"},
    {"id": "sow", "name": "Generación de SOW",
     "steps": "Input comercial → plantilla → RAG metodológico → generación → revisión → export"},
    {"id": "cyber", "name": "Diagnóstico cyber",
     "steps": "Cuestionario → scoring → riesgos → controles → roadmap → reporte ejecutivo"},
    {"id": "mando", "name": "Centro de mando",
     "steps": "Conectores → normalización → KPIs → insights AI → alertas → recomendaciones"},
    {"id": "finetune", "name": "Fine-tuning ligero",
     "steps": "Dataset → anonimización → versionado → LoRA → evals → red team → despliegue"},
]


@router.get("")
def list_workflows() -> list[dict]:
    return CATALOG


@router.post("/{workflow_id}/run")
def run_workflow(
    workflow_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    wf = next((w for w in CATALOG if w["id"] == workflow_id), None)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    run_id = uuid.uuid4().hex[:12]

    cfg = resolve_n8n(tenant)

    # Zero-config for the tenant: auto-provision managed workflows on first use.
    if (cfg.source == "global" and settings.n8n_auto_provision
            and not tenant.n8n_provisioned and is_provision_available()):
        result = ensure_tenant_workflows(tenant, [w["id"] for w in CATALOG])
        if result.get("provisioned"):
            tenant.n8n_provisioned = True
            session.add(tenant)
            session.commit()

    run = trigger_workflow(cfg, workflow_id, {
        "run_id": run_id, "workflow_id": workflow_id, "workflow": wf["name"],
        "tenant_id": tenant.id, "user_id": user.id,
    })

    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="workflow",
        object_type="workflow", object_id=workflow_id,
        risk_level="med" if run.status == "failed" else "low",
        reason=f"{wf['name']} (run {run_id}) · {run.status} · n8n:{run.source} · {run.detail}",
    ))
    session.commit()
    return {"run_id": run_id, "workflow": wf["name"], "status": run.status,
            "engine": "n8n" if run.triggered else "simulado", "source": run.source,
            "detail": run.detail, "response": run.response, "steps": wf["steps"]}
