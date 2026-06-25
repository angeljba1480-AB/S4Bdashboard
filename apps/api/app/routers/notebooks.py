"""/notebooks — a private, NotebookLM-style workspace over the company's own RAG.

A notebook is a named set of source documents. The user can ask questions answered
ONLY from those sources (with citations) and generate artifacts (summary, FAQ,
study guide, briefing, timeline). Everything runs through the privacy router, so
sensitive sources stay on private routes and PII is redacted before any external call.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..ai.cascade import maybe_refine
from ..ai.rag import retrieve
from ..ai.resilience import generate_with_fallback
from ..ai.router import route_request
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AuditEvent, Document, ModelRoute, Notebook, Tenant, User
from ..permissions import can_view_area, visible_areas

router = APIRouter(prefix="/notebooks", tags=["notebooks"])

ARTIFACTS = {
    "resumen": "Haz un resumen ejecutivo claro de las fuentes, con los puntos más importantes primero.",
    "faq": "Genera una lista de preguntas frecuentes (FAQ) con respuestas, basadas solo en las fuentes.",
    "guia": "Crea una guía de estudio: conceptos clave, definiciones y preguntas de repaso.",
    "brief": "Redacta un documento informativo (briefing) conciso y accionable.",
    "cronologia": "Construye una cronología ordenada de los hechos o eventos mencionados.",
}


def _ids(nb: Notebook) -> list[str]:
    try:
        v = json.loads(nb.document_ids or "[]")
        return [str(x) for x in v] if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def _out(nb: Notebook, session: Session, user: User) -> dict:
    ids = _ids(nb)
    docs = session.exec(select(Document).where(Document.id.in_(ids or [""]))).all()
    sources = [{"id": d.id, "filename": d.filename, "area": d.area or "", "sensitivity": d.sensitivity.value}
               for d in docs if can_view_area(user, d.area or "")]
    return {"id": nb.id, "name": nb.name, "document_ids": ids, "sources": sources,
            "created_at": nb.created_at.isoformat()}


class NotebookBody(BaseModel):
    name: str = "Nuevo notebook"
    document_ids: list[str] = []


@router.get("")
def list_notebooks(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    nbs = session.exec(
        select(Notebook).where(Notebook.tenant_id == tenant.id, Notebook.user_id == user.id)
        .order_by(Notebook.created_at.desc())
    ).all()
    return [_out(nb, session, user) for nb in nbs]


@router.post("", status_code=201)
def create_notebook(
    body: NotebookBody,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    nb = Notebook(tenant_id=tenant.id, user_id=user.id, name=body.name.strip() or "Nuevo notebook",
                  document_ids=json.dumps(body.document_ids))
    session.add(nb)
    session.commit()
    session.refresh(nb)
    return _out(nb, session, user)


def _get_owned(session: Session, tenant: Tenant, user: User, nb_id: str) -> Notebook:
    nb = session.get(Notebook, nb_id)
    if not nb or nb.tenant_id != tenant.id or nb.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notebook no encontrado")
    return nb


@router.put("/{nb_id}")
def update_notebook(
    nb_id: str, body: NotebookBody,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    nb = _get_owned(session, tenant, user, nb_id)
    nb.name = body.name.strip() or nb.name
    nb.document_ids = json.dumps(body.document_ids)
    session.add(nb)
    session.commit()
    session.refresh(nb)
    return _out(nb, session, user)


@router.delete("/{nb_id}")
def delete_notebook(
    nb_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    nb = _get_owned(session, tenant, user, nb_id)
    session.delete(nb)
    session.commit()
    return {"ok": True}


class AskBody(BaseModel):
    question: str
    precision: bool = False
    approve_external: bool = False


def _scoped_ids(nb: Notebook, user: User) -> list[str]:
    """Notebook sources, intersected with what the user is allowed to see."""
    return _ids(nb)  # area filtering happens in retrieve() via `areas`


def _generate(session: Session, tenant: Tenant, user: User, nb: Notebook,
              instruction: str, query: str, *, precision: bool = False, approved: bool = False) -> dict:
    ids = _scoped_ids(nb, user)
    if not ids:
        return {"content": "", "citations": [], "route": "", "empty": True,
                "message": "Agrega documentos al notebook primero."}
    citations = retrieve(session, tenant.id, query, ids, top_k=8, areas=visible_areas(user))
    if not citations:
        return {"content": "", "citations": [], "route": "", "empty": True,
                "message": "No encontré contenido en las fuentes de este notebook."}
    context = [c.text for c in citations]
    system = ("Eres un asistente que responde ESTRICTAMENTE con base en las fuentes del notebook. "
              "Si algo no está en las fuentes, dilo. Responde en español y cita lo relevante.")
    decision = route_request(tenant, None, instruction, context, task="chat")
    gen = generate_with_fallback(decision.route, system, instruction, decision.context or context)

    content, route, escalated, escalation_pending = gen.response.content, gen.route.value, False, False
    if gen.route != ModelRoute.BLOCKED:
        ref = maybe_refine(decision=decision, base_content=content, base_route=gen.route,
                           instruction=instruction, want_precision=precision, advanced=False, approved=approved)
        escalation_pending = ref["escalation_pending"]
        if ref["escalated"]:
            escalated = True
            content = ref["content"] + "\n\n_(Refinado con modelo premium · cascada.)_"
            route = ref["route"]

    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="notebook", object_type="notebook",
        object_id=nb.id, classification=decision.classification, selected_route=ModelRoute(route),
        selected_model=gen.response.model, risk_level="low",
        reason=f"notebook '{nb.name}': {instruction[:60]}" + (" (refinado premium)" if escalated else ""),
    ))
    session.commit()
    return {
        "content": content,
        "route": route,
        "citations": [{"filename": c.filename, "text": c.text, "score": c.score,
                       "sensitivity": c.sensitivity.value} for c in citations],
        "blocked": gen.route == ModelRoute.BLOCKED,
        "escalated": escalated,
        "escalation_pending": escalation_pending,
    }


@router.post("/{nb_id}/ask")
def ask(
    nb_id: str, body: AskBody,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    nb = _get_owned(session, tenant, user, nb_id)
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="Escribe una pregunta")
    return _generate(session, tenant, user, nb, body.question.strip(), body.question.strip(),
                     precision=body.precision, approved=body.approve_external)


@router.post("/{nb_id}/generate/{kind}")
def generate_artifact(
    nb_id: str, kind: str,
    precision: bool = False, approve_external: bool = False,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    nb = _get_owned(session, tenant, user, nb_id)
    instruction = ARTIFACTS.get(kind)
    if not instruction:
        raise HTTPException(status_code=404, detail="Tipo de artefacto desconocido")
    # Broad query so retrieval pulls representative chunks across the sources.
    return _generate(session, tenant, user, nb, instruction, f"{kind} {nb.name}",
                     precision=precision, approved=approve_external)
