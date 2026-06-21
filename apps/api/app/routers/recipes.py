"""/recipes — use-case engine: collect minimal input, AI pre-fill, user approves.

Two approval gates keep the user in control: an action gate (approve the
pre-filled draft) and a connection gate (approve access to email/calendar/...).
Everything is tenant-scoped and audited.
"""
from __future__ import annotations

import io
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user, require_roles
from ..db import get_session
from ..models import (
    AuditEvent,
    CatalogRecipe,
    Connection,
    RecipeProposal,
    RecipeRun,
    Role,
    Tenant,
    User,
)
from ..recipes.catalog import (
    CATEGORIES,
    RECIPES,
    db_recipe_to_dict,
    execute,
    get_recipe,
    prefill,
    public_recipe,
    validate_inputs,
)
from .export import _render_md, _render_pdf

router = APIRouter(prefix="/recipes", tags=["recipes"])


class StartRecipe(BaseModel):
    inputs: dict = {}


class ConnectionPrefs(BaseModel):
    prefs: dict = {}


class ProposeRecipe(BaseModel):
    title: str
    description: str = ""
    category: str = "dia_a_dia"


class CurateProposal(BaseModel):
    name: str | None = None
    category: str | None = None
    inputs: list[dict] | None = None
    prompt: str | None = None
    produces: str | None = None


# --- helpers ----------------------------------------------------------------
def _pending_connections(session: Session, tenant_id: str, user_id: str, recipe: dict, identifier: str):
    """Return Connection rows (creating pending ones) for a recipe's providers."""
    out = []
    for spec in recipe.get("connections", []):
        conn = session.exec(
            select(Connection).where(
                Connection.tenant_id == tenant_id,
                Connection.user_id == user_id,
                Connection.provider == spec["provider"],
                Connection.identifier == identifier,
            )
        ).first()
        if not conn:
            conn = Connection(tenant_id=tenant_id, user_id=user_id,
                              provider=spec["provider"], identifier=identifier, status="pending")
            session.add(conn)
            session.commit()
            session.refresh(conn)
        out.append((spec, conn))
    return out


def _conn_out(spec: dict, conn: Connection) -> dict:
    return {"id": conn.id, "provider": conn.provider, "label": spec.get("label", conn.provider),
            "identifier": conn.identifier, "status": conn.status}


def _run_out(run: RecipeRun, recipe: dict, connections: list[dict] | None = None) -> dict:
    return {
        "id": run.id, "recipe_id": run.recipe_id, "recipe_name": recipe["name"],
        "status": run.status, "approval": recipe["approval"], "approve_label": recipe["approve_label"],
        "inputs": json.loads(run.inputs or "{}"),
        "draft": json.loads(run.draft or "{}"),
        "result": json.loads(run.result) if run.result else None,
        "connections": connections or [],
    }


def _now():
    from datetime import datetime
    return datetime.utcnow()


def _db_recipes(session: Session, tenant_id: str) -> list[dict]:
    rows = session.exec(select(CatalogRecipe).where(CatalogRecipe.tenant_id == tenant_id)).all()
    return [db_recipe_to_dict(r) for r in rows]


def _all_recipes(session: Session, tenant_id: str) -> list[dict]:
    """In-code seed catalog (global) + curated DB recipes (tenant-scoped)."""
    return list(RECIPES) + _db_recipes(session, tenant_id)


def _resolve(session: Session, tenant_id: str, recipe_id: str) -> dict | None:
    return next((r for r in _all_recipes(session, tenant_id) if r["id"] == recipe_id), None)


# --- catalog ----------------------------------------------------------------
@router.get("")
def list_recipes(
    category: str | None = None,
    q: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    items = _all_recipes(session, tenant.id)
    if category:
        items = [r for r in items if r.get("category") == category]
    if q:
        ql = q.lower()
        items = [r for r in items if ql in r["name"].lower() or ql in r["description"].lower()]
    return [public_recipe(r) for r in items]


@router.get("/categories")
def list_categories(
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    counts: dict[str, int] = {}
    for r in _all_recipes(session, tenant.id):
        counts[r.get("category", "otros")] = counts.get(r.get("category", "otros"), 0) + 1
    return [{**c, "count": counts.get(c["id"], 0)} for c in CATEGORIES]


# --- lifecycle --------------------------------------------------------------
@router.post("/{recipe_id}/start")
def start_recipe(
    recipe_id: str,
    body: StartRecipe,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    recipe = _resolve(session, tenant.id, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Caso de uso no encontrado")

    missing = validate_inputs(recipe, body.inputs)
    if missing:
        raise HTTPException(status_code=422, detail=f"Faltan datos: {', '.join(missing)}")

    identifier = str(body.inputs.get("email", "")).strip()
    conns = _pending_connections(session, tenant.id, user.id, recipe, identifier)
    needs_conn = any(c.status != "approved" for _, c in conns)

    draft = prefill(recipe, session, tenant, body.inputs)
    run = RecipeRun(
        tenant_id=tenant.id, user_id=user.id, recipe_id=recipe_id,
        status="needs_connection" if needs_conn else "draft",
        inputs=json.dumps(body.inputs), draft=json.dumps(draft),
    )
    session.add(run)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="recipe",
        object_type="recipe", object_id=recipe_id, risk_level="low",
        reason=f"inicio de caso de uso '{recipe['name']}' (run {run.id})",
    ))
    session.commit()
    session.refresh(run)
    return _run_out(run, recipe, [_conn_out(s, c) for s, c in conns])


@router.get("/runs")
def list_runs(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    runs = session.exec(
        select(RecipeRun).where(RecipeRun.tenant_id == tenant.id, RecipeRun.user_id == user.id)
        .order_by(RecipeRun.created_at.desc())
    ).all()
    out = []
    for r in runs:
        recipe = _resolve(session, tenant.id, r.recipe_id) or {"name": r.recipe_id, "approval": "", "approve_label": ""}
        out.append(_run_out(r, recipe))
    return out


def _load_run(session, tenant, user, run_id) -> RecipeRun:
    run = session.get(RecipeRun, run_id)
    if not run or run.tenant_id != tenant.id or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    return run


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    run = _load_run(session, tenant, user, run_id)
    recipe = _resolve(session, tenant.id, run.recipe_id)
    identifier = str(json.loads(run.inputs or "{}").get("email", "")).strip()
    conns = _pending_connections(session, tenant.id, user.id, recipe, identifier) if recipe else []
    return _run_out(run, recipe, [_conn_out(s, c) for s, c in conns])


def _run_blocks(run: RecipeRun, recipe: dict) -> list[tuple[str, str]]:
    """Flatten a run (inputs + AI draft + result) into (heading, body) blocks."""
    inputs = json.loads(run.inputs or "{}")
    draft = json.loads(run.draft or "{}")
    result = json.loads(run.result) if run.result else {}
    blocks: list[tuple[str, str]] = []

    if inputs:
        blocks.append(("Datos proporcionados",
                       "\n".join(f"{k}: {v}" for k, v in inputs.items())))

    # The finished deliverable takes priority, then the reviewed draft.
    if result.get("documento"):
        blocks.append(("Documento", result["documento"]))
    elif result.get("output"):
        blocks.append(("Resultado", str(result["output"])))
    elif draft.get("contenido"):
        blocks.append(("Borrador generado", draft["contenido"]))

    if isinstance(draft.get("campos"), list):
        body = "\n\n".join(f"Requisito: {c.get('requisito', '')}\n"
                           f"Respuesta: {c.get('respuesta_sugerida', '')}"
                           for c in draft["campos"])
        if body:
            blocks.append(("Requisitos y respuestas", body))

    if not blocks:
        blocks.append(("Resumen", draft.get("summary", recipe.get("name", ""))))
    return blocks


@router.get("/runs/{run_id}/export")
def export_run(
    run_id: str,
    format: str = "pdf",
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Download a use-case result as PDF or Markdown."""
    run = _load_run(session, tenant, user, run_id)
    recipe = _resolve(session, tenant.id, run.recipe_id) or {"name": run.recipe_id}
    title = recipe.get("name", "Caso de uso")
    blocks = _run_blocks(run, recipe)
    fname = f"{run.recipe_id}-{run.id}"
    if format == "md":
        return Response(_render_md(title, blocks), media_type="text/markdown",
                        headers={"Content-Disposition": f'attachment; filename="{fname}.md"'})
    pdf = _render_pdf(title, blocks)
    return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


@router.post("/runs/{run_id}/approve")
def approve_run(
    run_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    run = _load_run(session, tenant, user, run_id)
    recipe = _resolve(session, tenant.id, run.recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Caso de uso no encontrado")

    inputs = json.loads(run.inputs or "{}")
    identifier = str(inputs.get("email", "")).strip()
    conns = _pending_connections(session, tenant.id, user.id, recipe, identifier)
    pending = [_conn_out(s, c) for s, c in conns if c.status != "approved"]
    if pending:
        run.status = "needs_connection"
        session.commit()
        raise HTTPException(status_code=409, detail={
            "message": "Aprueba primero la conexión.", "connections": pending})

    result = execute(recipe, session, tenant.id, inputs, json.loads(run.draft or "{}"))
    run.status = "completed"
    run.result = json.dumps(result)
    run.updated_at = _now()
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="recipe",
        object_type="recipe", object_id=run.recipe_id, risk_level="low",
        reason=f"aprobado y ejecutado '{recipe['name']}' (run {run.id})",
    ))
    session.commit()
    session.refresh(run)
    return _run_out(run, recipe, [_conn_out(s, c) for s, c in conns])


# --- connections ------------------------------------------------------------
@router.get("/connections")
def list_connections(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    conns = session.exec(
        select(Connection).where(Connection.tenant_id == tenant.id, Connection.user_id == user.id)
    ).all()
    return [{"id": c.id, "provider": c.provider, "identifier": c.identifier, "status": c.status} for c in conns]


@router.post("/connections/{conn_id}/approve")
def approve_connection(
    conn_id: str,
    body: ConnectionPrefs | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    conn = session.get(Connection, conn_id)
    if not conn or conn.tenant_id != tenant.id or conn.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conexión no encontrada")
    conn.status = "approved"
    if body and body.prefs:
        conn.prefs = json.dumps(body.prefs)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="connection",
        object_type="connection", object_id=conn.id, risk_level="med",
        reason=f"conexión aprobada: {conn.provider} ({conn.identifier})",
    ))
    session.commit()
    return {"id": conn.id, "provider": conn.provider, "status": conn.status}


# --- user-proposed use cases ------------------------------------------------
@router.post("/propose")
def propose_recipe(
    body: ProposeRecipe,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Anyone can propose a use case; curated ones join the catalog over time."""
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="El título es obligatorio")
    prop = RecipeProposal(
        tenant_id=tenant.id, user_id=user.id, title=body.title.strip(),
        description=body.description.strip(), category=body.category or "dia_a_dia",
    )
    session.add(prop)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="recipe_proposal",
        object_type="recipe_proposal", object_id=prop.id, risk_level="low",
        reason=f"propuesta de caso de uso: {prop.title}",
    ))
    session.commit()
    session.refresh(prop)
    return {"id": prop.id, "title": prop.title, "category": prop.category, "status": prop.status}


@router.get("/proposals")
def list_proposals(
    tenant: Tenant = Depends(get_current_tenant),
    _: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    props = session.exec(
        select(RecipeProposal).where(RecipeProposal.tenant_id == tenant.id)
        .order_by(RecipeProposal.created_at.desc())
    ).all()
    return [{"id": p.id, "title": p.title, "description": p.description,
             "category": p.category, "status": p.status, "votes": p.votes} for p in props]


def _slugify(text: str) -> str:
    import re
    base = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "caso"
    return f"{base}_{__import__('uuid').uuid4().hex[:6]}"


@router.post("/proposals/{proposal_id}/curate")
def curate_proposal(
    proposal_id: str,
    body: CurateProposal,
    _: User = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Turn a user proposal into a live, DB-backed catalog use case."""
    prop = session.get(RecipeProposal, proposal_id)
    if not prop or prop.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")

    name = (body.name or prop.title).strip()
    inputs = body.inputs or [{"key": "detalle", "type": "text", "label": "Detalle", "required": True}]
    recipe = CatalogRecipe(
        tenant_id=tenant.id, slug=_slugify(name), category=body.category or prop.category,
        name=name, description=prop.description or name,
        inputs=json.dumps(inputs),
        prompt=body.prompt or f"{name}: {{detalle}}",
        produces=body.produces or "el resultado", proposal_id=prop.id,
    )
    prop.status = "curated"
    session.add(recipe)
    session.add(prop)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="recipe_curated",
        object_type="catalog_recipe", object_id=recipe.id, risk_level="low",
        reason=f"caso de uso curado al catálogo: {name}",
    ))
    session.commit()
    session.refresh(recipe)
    return {"id": recipe.id, "slug": recipe.slug, "name": recipe.name,
            "category": recipe.category, "status": "curated"}


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str,
    _: User = Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    prop = session.get(RecipeProposal, proposal_id)
    if not prop or prop.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Propuesta no encontrada")
    prop.status = "rejected"
    session.add(prop)
    session.commit()
    return {"id": prop.id, "status": prop.status}
