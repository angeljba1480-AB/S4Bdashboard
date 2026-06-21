"""Workflows endpoint (blueprint section 9). MVP exposes the catalog and a
simulated run that records audit + cost, ready to be wired to n8n/Temporal."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
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
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="workflow",
        object_type="workflow", object_id=workflow_id, risk_level="low",
        reason=f"ejecución simulada de {wf['name']} (run {run_id})",
    ))
    session.commit()
    return {"run_id": run_id, "workflow": wf["name"], "status": "completed", "steps": wf["steps"]}
