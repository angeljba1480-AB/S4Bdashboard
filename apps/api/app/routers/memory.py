"""/memory — persistent, taggable, semantically-searchable memory of past work.

Lets the user recall previous work ('¿recuerdas el trabajo C?'), organize it with
tags (CMS-style) and feed it back into the chat. Area-scoped like documents.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..ai.embeddings import cosine, embed
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import MemoryItem, Tenant, User
from ..permissions import can_view_area, visible_areas

router = APIRouter(prefix="/memory", tags=["memory"])


def _tags(raw: str) -> list[str]:
    try:
        v = json.loads(raw or "[]")
        return [str(t).strip() for t in v if str(t).strip()] if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def _out(m: MemoryItem) -> dict:
    return {"id": m.id, "title": m.title, "content": m.content, "source": m.source,
            "source_id": m.source_id, "tags": _tags(m.tags), "area": m.area or "",
            "created_at": m.created_at.isoformat()}


def capture(session: Session, tenant_id: str, user_id: str, *, title: str, content: str,
            source: str = "manual", source_id: str = "", tags: list[str] | None = None,
            area: str = "") -> MemoryItem | None:
    """Save a memory item (best-effort embedding). Returns None on empty content."""
    if not (content or "").strip():
        return None
    try:
        vec = json.dumps(embed(f"{title}\n{content}"[:4000]))
    except Exception:
        vec = ""
    m = MemoryItem(tenant_id=tenant_id, user_id=user_id, title=title.strip() or "(sin título)",
                   content=content.strip(), source=source, source_id=source_id,
                   tags=json.dumps(tags or []), area=area or "", embedding=vec)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def recall(session: Session, tenant_id: str, user: User, query: str, top_k: int = 3) -> list[MemoryItem]:
    """Top memory items for a query, scoped to the user's areas. Used by chat."""
    rows = session.exec(
        select(MemoryItem).where(MemoryItem.tenant_id == tenant_id, MemoryItem.user_id == user.id)
    ).all()
    areas = visible_areas(user)
    rows = [m for m in rows if can_view_area(user, m.area or "")]
    if not rows or not query.strip():
        return rows[:top_k]
    try:
        qv = embed(query)
    except Exception:
        return rows[:top_k]
    scored = []
    for m in rows:
        try:
            score = cosine(qv, json.loads(m.embedding)) if m.embedding else 0.0
        except (ValueError, TypeError):
            score = 0.0
        if query.lower() in (m.title + " " + m.content).lower():
            score += 0.2  # keyword boost
        scored.append((score, m))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:top_k]]


class MemoryBody(BaseModel):
    title: str = ""
    content: str
    source: str = "manual"
    source_id: str = ""
    tags: list[str] = []
    area: str = ""


@router.post("", status_code=201)
def create_memory(
    body: MemoryBody,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    m = capture(session, tenant.id, user.id, title=body.title, content=body.content,
                source=body.source, source_id=body.source_id, tags=body.tags, area=body.area)
    if not m:
        raise HTTPException(status_code=422, detail="El contenido está vacío")
    return _out(m)


@router.get("")
def list_memory(
    q: str = "", tag: str = "",
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(
        select(MemoryItem).where(MemoryItem.tenant_id == tenant.id, MemoryItem.user_id == user.id)
    ).all()
    rows = [m for m in rows if can_view_area(user, m.area or "")]
    if tag:
        rows = [m for m in rows if tag in _tags(m.tags)]
    if q.strip():
        ranked = recall(session, tenant.id, user, q, top_k=50)
        ids = {m.id for m in rows}
        rows = [m for m in ranked if m.id in ids]
    else:
        rows.sort(key=lambda m: m.created_at, reverse=True)
    return [_out(m) for m in rows]


@router.get("/tags")
def list_tags(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[str]:
    rows = session.exec(
        select(MemoryItem).where(MemoryItem.tenant_id == tenant.id, MemoryItem.user_id == user.id)
    ).all()
    tags: set[str] = set()
    for m in rows:
        if can_view_area(user, m.area or ""):
            tags.update(_tags(m.tags))
    return sorted(tags)


@router.delete("/{item_id}")
def delete_memory(
    item_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    m = session.get(MemoryItem, item_id)
    if not m or m.tenant_id != tenant.id or m.user_id != user.id:
        raise HTTPException(status_code=404, detail="No encontrado")
    session.delete(m)
    session.commit()
    return {"ok": True}
