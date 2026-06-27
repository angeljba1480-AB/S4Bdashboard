"""/search — búsqueda global de la plataforma.

Cruza en una sola consulta lo que el usuario puede ver: documentos, memoria,
notebooks, recetas del agente (playbooks), recetas de automatización (n8n/Zapier),
imágenes generadas y automatizaciones. Devuelve resultados tipados con enlace
profundo a la sección correspondiente. Respeta el tenant y los permisos por área.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import (
    AgentPlaybook, Automation, Document, GeneratedImage, MemoryItem, N8nRecipe,
    Notebook, Tenant, User,
)
from ..permissions import can_view_area

router = APIRouter(prefix="/search", tags=["search"])

_PER_TYPE = 8


def _snippet(text: str, q: str, width: int = 140) -> str:
    """Extracto alrededor de la primera coincidencia (o el inicio)."""
    if not text:
        return ""
    low = text.lower()
    i = low.find(q.lower())
    if i < 0:
        return text[:width].strip()
    start = max(0, i - 40)
    return ("…" if start > 0 else "") + text[start:start + width].strip() + "…"


@router.get("")
def search(
    q: str = Query("", min_length=0),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    term = (q or "").strip()
    if len(term) < 2:
        return {"query": term, "total": 0, "results": []}
    like = f"%{term}%"
    results: list[dict] = []

    # Documentos (filtrados por permiso de área).
    docs = session.exec(select(Document).where(
        Document.tenant_id == tenant.id,
        Document.filename.ilike(like) | Document.text.ilike(like)
    ).order_by(Document.created_at.desc()).limit(_PER_TYPE * 3)).all()
    for d in docs:
        if not can_view_area(user, d.area or ""):
            continue
        results.append({"type": "document", "id": d.id, "title": d.filename,
                        "snippet": _snippet(d.text, term), "area": d.area or "",
                        "href": "/documents"})
        if len([r for r in results if r["type"] == "document"]) >= _PER_TYPE:
            break

    # Memoria (por usuario).
    for m in session.exec(select(MemoryItem).where(
        MemoryItem.tenant_id == tenant.id, MemoryItem.user_id == user.id,
        MemoryItem.title.ilike(like) | MemoryItem.content.ilike(like)
    ).order_by(MemoryItem.created_at.desc()).limit(_PER_TYPE)).all():
        results.append({"type": "memory", "id": m.id, "title": m.title or "(sin título)",
                        "snippet": _snippet(m.content, term), "href": "/memory"})

    # Notebooks (por usuario).
    for n in session.exec(select(Notebook).where(
        Notebook.tenant_id == tenant.id, Notebook.user_id == user.id,
        Notebook.name.ilike(like)
    ).order_by(Notebook.updated_at.desc()).limit(_PER_TYPE)).all():
        results.append({"type": "notebook", "id": n.id, "title": n.name,
                        "snippet": "", "href": "/notebooks"})

    # Recetas del agente (playbooks, por usuario).
    for p in session.exec(select(AgentPlaybook).where(
        AgentPlaybook.tenant_id == tenant.id, AgentPlaybook.user_id == user.id,
        AgentPlaybook.name.ilike(like) | AgentPlaybook.instruction.ilike(like)
    ).order_by(AgentPlaybook.created_at.desc()).limit(_PER_TYPE)).all():
        results.append({"type": "playbook", "id": p.id, "title": p.name,
                        "snippet": _snippet(p.instruction, term), "href": "/agents"})

    # Recetas de automatización (n8n / Zapier, por tenant).
    for rc in session.exec(select(N8nRecipe).where(
        N8nRecipe.tenant_id == tenant.id,
        N8nRecipe.name.ilike(like) | N8nRecipe.description.ilike(like)
    ).order_by(N8nRecipe.created_at.desc()).limit(_PER_TYPE)).all():
        results.append({"type": "recipe", "id": rc.id, "title": rc.name,
                        "snippet": _snippet(rc.description, term), "href": "/workflows"})

    # Imágenes generadas (por tenant).
    for img in session.exec(select(GeneratedImage).where(
        GeneratedImage.tenant_id == tenant.id, GeneratedImage.prompt.ilike(like)
    ).order_by(GeneratedImage.created_at.desc()).limit(_PER_TYPE)).all():
        results.append({"type": "image", "id": img.id, "title": _snippet(img.prompt, term, 60),
                        "snippet": "", "href": "/generate"})

    # Automatizaciones (por usuario).
    for a in session.exec(select(Automation).where(
        Automation.tenant_id == tenant.id, Automation.user_id == user.id,
        Automation.name.ilike(like) | Automation.description.ilike(like)
    ).order_by(Automation.created_at.desc()).limit(_PER_TYPE)).all():
        results.append({"type": "automation", "id": a.id, "title": a.name,
                        "snippet": _snippet(a.description, term), "href": "/automations"})

    return {"query": term, "total": len(results), "results": results}
