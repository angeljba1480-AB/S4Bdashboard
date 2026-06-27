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
    from .. import alerts as _alerts
    _alerts.dispatch(session, tenant.id, "workflow", f"Workflow: {wf['name']}",
                     f"Ejecución {run.status} (run {run_id}).",
                     level="error" if run.status == "failed" else "info")
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
    return {"id": r.id, "provider": r.provider or "n8n", "name": r.name, "description": r.description,
            "category": r.category, "webhook_path": r.webhook_path, "webhook_url": r.webhook_url,
            "params": json.loads(r.params or "[]"), "enabled": r.enabled,
            "created_at": r.created_at.isoformat()}


def _trigger_zapier(webhook_url: str, payload: dict) -> tuple[str, str]:
    """POST directo al Catch Hook del Zap. Devuelve (status, detail)."""
    import httpx
    try:  # pragma: no cover - network path
        resp = httpx.post(webhook_url, json=payload, timeout=30)
        resp.raise_for_status()
        return "completed", f"zapier {resp.status_code}"
    except Exception as exc:  # pragma: no cover - network path
        return "failed", f"zapier error: {exc}"


def list_recipe_rows(session: Session, tenant_id: str, only_enabled: bool = False) -> list[N8nRecipe]:
    q = select(N8nRecipe).where(N8nRecipe.tenant_id == tenant_id)
    rows = session.exec(q.order_by(N8nRecipe.created_at.desc())).all()
    return [r for r in rows if r.enabled] if only_enabled else rows


def trigger_recipe(session: Session, tenant: Tenant, user: User, recipe: N8nRecipe,
                   payload: dict | None = None) -> dict:
    """Dispara una receta a medida: Zapier (webhook_url completo) o n8n (webhook_path)."""
    run_id = uuid.uuid4().hex[:12]
    body = {"run_id": run_id, "recipe_id": recipe.id, "recipe": recipe.name,
            "tenant_id": tenant.id, "user_id": user.id, **(payload or {})}
    provider = recipe.provider or "n8n"
    if provider == "zapier":
        if not recipe.webhook_url:
            status, detail, source, engine, response = "simulated", "Zapier sin webhook_url", "off", "simulado", None
        else:
            status, detail = _trigger_zapier(recipe.webhook_url, body)
            source, engine, response = "zapier", "zapier", None
    else:
        cfg = resolve_n8n(tenant)
        run = trigger_workflow(cfg, recipe.webhook_path or recipe.id, body,
                               webhook_path=recipe.webhook_path or None)
        status, detail, source = run.status, run.detail, run.source
        engine, response = ("n8n" if run.triggered else "simulado"), run.response
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="workflow", object_type="automation_recipe",
        object_id=recipe.id, risk_level="med" if status == "failed" else "low",
        reason=f"receta {recipe.name} ({provider}, run {run_id}) · {status} · {detail}"))
    session.commit()
    from .. import alerts as _alerts
    _alerts.dispatch(session, tenant.id, "recipe", f"Receta: {recipe.name}",
                     f"Ejecución {status} ({provider}).",
                     level="error" if status == "failed" else "info")
    return {"run_id": run_id, "recipe": recipe.name, "provider": provider, "status": status,
            "engine": engine, "source": source, "detail": detail, "response": response}


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
    provider: str = "n8n"          # n8n | zapier
    description: str = ""
    category: str = "custom"
    webhook_path: str = ""        # n8n
    webhook_url: str = ""         # zapier (URL completa del Catch Hook)
    params: list[str] = []
    enabled: bool = True


def _validate_recipe(body: RecipeIn) -> str:
    """Devuelve el provider normalizado o lanza 422 si falta el destino."""
    provider = body.provider if body.provider in ("n8n", "zapier") else "n8n"
    if not body.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio")
    if provider == "zapier":
        if not body.webhook_url.strip().startswith("http"):
            raise HTTPException(status_code=422, detail="Zapier requiere una webhook_url válida (https://hooks.zapier.com/…)")
    elif not body.webhook_path.strip():
        raise HTTPException(status_code=422, detail="n8n requiere webhook_path")
    return provider


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
    provider = _validate_recipe(body)
    cat = body.category if body.category in ("db", "soap", "app", "custom") else "custom"
    r = N8nRecipe(tenant_id=tenant.id, provider=provider, name=body.name.strip(),
                  description=body.description.strip(), category=cat,
                  webhook_path=body.webhook_path.strip().lstrip("/"),
                  webhook_url=body.webhook_url.strip(),
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
    provider = _validate_recipe(body)
    r.provider = provider
    r.name = body.name.strip() or r.name
    r.description = body.description.strip()
    r.category = body.category if body.category in ("db", "soap", "app", "custom") else r.category
    r.webhook_path = body.webhook_path.strip().lstrip("/")
    r.webhook_url = body.webhook_url.strip()
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


@router.get("/zapier/status")
def zapier_status(_: User = Depends(get_current_user)) -> dict:
    """Estado de la integración Zapier. Webhooks/Zaps funcionan ya (recetas con
    webhook_url). AI Actions (NLA) es la ruta nativa opcional, preparada."""
    return {
        "webhooks": {"available": True,
                     "how": "Crea un Zap con trigger 'Catch Hook', copia la URL y créala como receta (provider=zapier)."},
        "ai_actions": {"enabled": settings.zapier_nla_enabled,
                       "configured": bool(settings.zapier_nla_api_key),
                       "status": "preparado" if not settings.zapier_nla_api_key else "configurado",
                       "how": "Requiere registrar la app en Zapier y `ZAPIER_NLA_API_KEY`. Catálogo dinámico de 8,000+ apps."},
    }


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
