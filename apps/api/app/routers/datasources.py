"""/datasources — conectores a sistemas legados sin API.

Hoy: base de datos de **solo lectura** (cualquier DSN compatible con SQLAlchemy:
postgres, mysql, sqlite…). Una consulta SELECT se ejecuta y su resultado se
importa al repositorio + índice RAG (clasificado y cifrado). Pensado para que
n8n / conectores REST / webhooks cubran el resto (ver docs/INTEGRATIONS.md).
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlmodel import Session, select

from .. import doc_categories
from ..ai.rag import index_document
from ..auth import get_current_tenant, require_roles
from ..db import get_session
from ..models import AuditEvent, DataSource, Document, Role, Tenant, User
from ..security.crypto import decrypt, encrypt

router = APIRouter(prefix="/datasources", tags=["datasources"])

MAX_ROWS = 1000


def _out(d: DataSource) -> dict:
    return {"id": d.id, "name": d.name, "kind": d.kind, "query": d.query,
            "area": d.area or "", "category": d.category or "", "created_at": d.created_at.isoformat()}


def _check_select(query: str) -> str:
    q = (query or "").strip().rstrip(";")
    if not q.lower().startswith(("select", "with")):
        raise HTTPException(status_code=422, detail="Solo se permiten consultas de lectura (SELECT).")
    if ";" in q:
        raise HTTPException(status_code=422, detail="Una sola sentencia, sin ';'.")
    return q


def _run_query(dsn: str, query: str) -> tuple[list[str], list[tuple]]:
    engine = create_engine(dsn)
    try:
        with engine.connect() as conn:
            res = conn.execute(text(query))
            cols = list(res.keys())
            rows = res.fetchmany(MAX_ROWS)
            return cols, [tuple(r) for r in rows]
    finally:
        engine.dispose()


def _as_text(cols: list[str], rows: list[tuple]) -> str:
    head = " | ".join(cols)
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(" | ".join("" if v is None else str(v) for v in r))
    return "\n".join(lines)


class DataSourceIn(BaseModel):
    name: str
    dsn: str
    query: str
    kind: str = "db"
    area: str = ""
    category: str = ""


@router.get("")
def list_sources(
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.exec(select(DataSource).where(DataSource.tenant_id == tenant.id)).all()
    return [_out(d) for d in rows]


@router.post("", status_code=201)
def create_source(
    body: DataSourceIn,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    if not body.dsn.strip():
        raise HTTPException(status_code=422, detail="Falta el DSN de conexión")
    q = _check_select(body.query)
    d = DataSource(tenant_id=tenant.id, name=body.name.strip() or "Fuente", kind="db",
                   dsn_enc=encrypt(body.dsn.strip(), tenant.kms_key_id), query=q,
                   area=body.area.strip(), category=body.category.strip())
    session.add(d)
    session.commit()
    session.refresh(d)
    return _out(d)


def _owned(session, tenant, ds_id) -> DataSource:
    d = session.get(DataSource, ds_id)
    if not d or d.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    return d


@router.post("/{ds_id}/test")
def test_source(
    ds_id: str,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    d = _owned(session, tenant, ds_id)
    try:
        cols, rows = _run_query(decrypt(d.dsn_enc, tenant.kms_key_id), d.query)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo consultar: {exc}")
    return {"ok": True, "columns": cols, "sample_rows": len(rows[:5]), "total_preview": len(rows)}


@router.post("/{ds_id}/import", status_code=201)
def import_source(
    ds_id: str,
    user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    d = _owned(session, tenant, ds_id)
    try:
        cols, rows = _run_query(decrypt(d.dsn_enc, tenant.kms_key_id), d.query)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo consultar: {exc}")
    content = _as_text(cols, rows)
    from ..security.classifier import classify_data
    cls = classify_data(content)
    cat = doc_categories.get_or_create(session, tenant.id, d.category or "")
    doc = Document(
        tenant_id=tenant.id, owner_id=user.id, filename=f"{d.name}.txt", mime_type="text/plain",
        area=d.area or "", category=cat.key if cat else "", sensitivity=cls.sensitivity,
        pii_score=cls.pii.score, pii_types=",".join(cls.pii.types),
        storage_uri=f"datasource://{d.id}", hash=hashlib.sha256(content.encode()).hexdigest(),
        text=content,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    chunks = index_document(session, doc)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="upload", object_type="document",
        object_id=doc.id, risk_level="low",
        reason=f"importado de fuente de datos '{d.name}' ({len(rows)} filas, {chunks} chunks)",
    ))
    session.commit()
    return {"id": doc.id, "filename": doc.filename, "rows": len(rows)}


@router.delete("/{ds_id}")
def delete_source(
    ds_id: str,
    _: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    d = _owned(session, tenant, ds_id)
    session.delete(d)
    session.commit()
    return {"ok": True}
