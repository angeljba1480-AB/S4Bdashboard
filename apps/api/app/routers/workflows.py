"""Workflows endpoint (blueprint section 9). Triggers real n8n workflows via
webhook when configured; otherwise records a simulated run + audit."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user, require_roles
from ..config import settings
from ..db import get_session
from ..integrations.n8n import resolve_n8n, trigger_workflow
from ..integrations.n8n_provision import (
    ensure_tenant_workflows,
    is_available as is_provision_available,
)
from ..models import AuditEvent, N8nRecipe, Role, Tenant, User

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


def trigger_catalog_workflow(session: Session, tenant: Tenant, user: User,
                             workflow_id: str, payload: dict | None = None) -> dict:
    """Dispara un workflow del catálogo en n8n (con auto-provisión y auditoría).
    Reutilizable desde el endpoint /workflows y desde el agente de acciones."""
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
        "tenant_id": tenant.id, "user_id": user.id, **(payload or {}),
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


@router.post("/{workflow_id}/run")
def run_workflow(
    workflow_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    return trigger_catalog_workflow(session, tenant, user, workflow_id)


# --- recetas n8n a la medida (DB / SOAP / apps propias) ----------------------
def _recipe_out(r: N8nRecipe) -> dict:
    return {"id": r.id, "name": r.name, "description": r.description, "category": r.category,
            "webhook_path": r.webhook_path, "params": json.loads(r.params or "[]"),
            "enabled": r.enabled, "created_at": r.created_at.isoformat()}


def list_recipe_rows(session: Session, tenant_id: str, only_enabled: bool = False) -> list[N8nRecipe]:
    q = select(N8nRecipe).where(N8nRecipe.tenant_id == tenant_id)
    rows = session.exec(q.order_by(N8nRecipe.created_at.desc())).all()
    return [r for r in rows if r.enabled] if only_enabled else rows


def trigger_recipe(session: Session, tenant: Tenant, user: User, recipe: N8nRecipe,
                   payload: dict | None = None) -> dict:
    """Dispara una receta a medida en el n8n del tenant, por su webhook_path."""
    run_id = uuid.uuid4().hex[:12]
    cfg = resolve_n8n(tenant)
    run = trigger_workflow(cfg, recipe.webhook_path or recipe.id, {
        "run_id": run_id, "recipe_id": recipe.id, "recipe": recipe.name,
        "tenant_id": tenant.id, "user_id": user.id, **(payload or {}),
    }, webhook_path=recipe.webhook_path or None)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="workflow", object_type="n8n_recipe",
        object_id=recipe.id, risk_level="med" if run.status == "failed" else "low",
        reason=f"receta {recipe.name} (run {run_id}) · {run.status} · n8n:{run.source} · {run.detail}"))
    session.commit()
    return {"run_id": run_id, "recipe": recipe.name, "status": run.status,
            "engine": "n8n" if run.triggered else "simulado", "source": run.source,
            "detail": run.detail, "response": run.response}


def trigger_workflow_or_recipe(session: Session, tenant: Tenant, user: User,
                               wid: str, payload: dict | None = None) -> dict:
    """Despacha por id: workflow del catálogo base o receta a medida del tenant.
    Usado por el agente de acciones (action `workflow:<id>`)."""
    if any(w["id"] == wid for w in CATALOG):
        return trigger_catalog_workflow(session, tenant, user, wid, payload)
    recipe = session.get(N8nRecipe, wid)
    if not recipe or recipe.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Workflow/receta no encontrada")
    return trigger_recipe(session, tenant, user, recipe, payload)


class RecipeIn(BaseModel):
    name: str
    description: str = ""
    category: str = "custom"
    webhook_path: str = ""
    params: list[str] = []
    enabled: bool = True


@router.get("/recipes")
def list_recipes(
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    return [_recipe_out(r) for r in list_recipe_rows(session, tenant.id)]


@router.post("/recipes", status_code=201)
def create_recipe(
    body: RecipeIn,
    user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    if not body.name.strip() or not body.webhook_path.strip():
        raise HTTPException(status_code=422, detail="Nombre y webhook_path son obligatorios")
    cat = body.category if body.category in ("db", "soap", "app", "custom") else "custom"
    r = N8nRecipe(tenant_id=tenant.id, name=body.name.strip(), description=body.description.strip(),
                  category=cat, webhook_path=body.webhook_path.strip().lstrip("/"),
                  params=json.dumps([p.strip() for p in body.params if p.strip()]), enabled=body.enabled)
    session.add(r); session.commit(); session.refresh(r)
    return _recipe_out(r)


def _owned_recipe(session, tenant, rid) -> N8nRecipe:
    r = session.get(N8nRecipe, rid)
    if not r or r.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Receta no encontrada")
    return r


@router.patch("/recipes/{rid}")
def update_recipe(
    rid: str, body: RecipeIn,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    r = _owned_recipe(session, tenant, rid)
    r.name = body.name.strip() or r.name
    r.description = body.description.strip()
    r.category = body.category if body.category in ("db", "soap", "app", "custom") else r.category
    if body.webhook_path.strip():
        r.webhook_path = body.webhook_path.strip().lstrip("/")
    r.params = json.dumps([p.strip() for p in body.params if p.strip()])
    r.enabled = body.enabled
    session.add(r); session.commit(); session.refresh(r)
    return _recipe_out(r)


@router.delete("/recipes/{rid}")
def delete_recipe(
    rid: str,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    r = _owned_recipe(session, tenant, rid)
    session.delete(r); session.commit()
    return {"ok": True}


class RecipeRunIn(BaseModel):
    payload: dict = {}


@router.post("/recipes/{rid}/run")
def run_recipe(
    rid: str, body: RecipeRunIn,
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    r = _owned_recipe(session, tenant, rid)
    if not r.enabled:
        raise HTTPException(status_code=400, detail="La receta está deshabilitada")
    return trigger_recipe(session, tenant, user, r, body.payload)
