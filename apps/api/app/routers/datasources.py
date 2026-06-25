"""/datasources — conectores a sistemas legados sin API.

Hoy: base de datos de **solo lectura** (cualquier DSN compatible con SQLAlchemy:
postgres, mysql, sqlite…). Una consulta SELECT se ejecuta y su resultado se
importa al repositorio + índice RAG (clasificado y cifrado). Pensado para que
n8n / conectores REST / webhooks cubran el resto (ver docs/INTEGRATIONS.md).
"""
from __future__ import annotations

import csv
import hashlib
import io
import re

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
# Esquemas de BD permitidos (evita lectura de archivos / drivers raros vía DSN).
ALLOWED_SCHEMES = ("postgresql", "postgres", "mysql", "mariadb", "mssql", "sqlite", "oracle")
# Palabras que indican modificación de datos/estructura (también dentro de un CTE).
_DML = re.compile(r"\b(insert|update|delete|merge|drop|alter|create|truncate|grant|revoke|call|copy|"
                  r"pg_read_file|pg_sleep|lo_import|lo_export|into\s+outfile)\b", re.IGNORECASE)


def _out(d: DataSource) -> dict:
    return {"id": d.id, "name": d.name, "kind": d.kind, "query": d.query,
            "area": d.area or "", "category": d.category or "", "created_at": d.created_at.isoformat()}


def _check_select(query: str) -> str:
    q = (query or "").strip().rstrip(";")
    if not q.lower().startswith(("select", "with")):
        raise HTTPException(status_code=422, detail="Solo se permiten consultas de lectura (SELECT).")
    if ";" in q:
        raise HTTPException(status_code=422, detail="Una sola sentencia, sin ';'.")
    if _DML.search(q):
        raise HTTPException(status_code=422, detail="La consulta contiene operaciones no permitidas (solo lectura).")
    return q


def _check_dsn(dsn: str) -> str:
    scheme = (dsn.split("://", 1)[0].split("+", 1)[0]).strip().lower()
    if scheme not in ALLOWED_SCHEMES:
        raise HTTPException(status_code=422, detail=f"Esquema de BD no permitido. Usa: {', '.join(ALLOWED_SCHEMES)}.")
    return dsn


def _run_query(dsn: str, query: str) -> tuple[list[str], list[tuple]]:
    engine = create_engine(dsn)
    try:
        # Transacción de solo lectura cuando el motor lo soporta (la BD lo refuerza).
        with engine.connect() as conn:
            try:
                conn = conn.execution_options(postgresql_readonly=True)
            except Exception:
                pass
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


def _parse_csv(raw: str, delimiter: str = ",") -> tuple[list[str], list[tuple]]:
    """Parse CSV text into (columns, rows). First row is the header. Capped at MAX_ROWS."""
    delim = (delimiter or ",")[:1] or ","
    reader = csv.reader(io.StringIO(raw), delimiter=delim)
    try:
        cols = next(reader)
    except StopIteration:
        raise HTTPException(status_code=422, detail="El CSV está vacío.")
    rows: list[tuple] = []
    for row in reader:
        rows.append(tuple(row))
        if len(rows) >= MAX_ROWS:
            break
    return [c.strip() for c in cols], rows


def _import_as_document(session: Session, tenant: Tenant, user: User, *, name: str,
                        content: str, area: str, category: str, storage_uri: str,
                        rows: int, source_label: str) -> dict:
    """Classify text content, store it as a Document and index it into the RAG."""
    from ..security.classifier import classify_data
    cls = classify_data(content)
    cat = doc_categories.get_or_create(session, tenant.id, category or "")
    doc = Document(
        tenant_id=tenant.id, owner_id=user.id, filename=f"{name}.txt", mime_type="text/plain",
        area=area or "", category=cat.key if cat else "", sensitivity=cls.sensitivity,
        pii_score=cls.pii.score, pii_types=",".join(cls.pii.types),
        storage_uri=storage_uri, hash=hashlib.sha256(content.encode()).hexdigest(),
        text=content,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    chunks = index_document(session, doc)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="upload", object_type="document",
        object_id=doc.id, risk_level="low",
        reason=f"importado de {source_label} ({rows} filas, {chunks} chunks)",
    ))
    session.commit()
    return {"id": doc.id, "filename": doc.filename, "rows": rows}


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
    _check_dsn(body.dsn.strip())
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
    return _import_as_document(
        session, tenant, user, name=d.name, content=_as_text(cols, rows),
        area=d.area or "", category=d.category or "", storage_uri=f"datasource://{d.id}",
        rows=len(rows), source_label=f"fuente de datos '{d.name}'")


class CsvImportIn(BaseModel):
    name: str
    csv_text: str
    delimiter: str = ","
    area: str = ""
    category: str = ""


@router.post("/import-csv", status_code=201)
def import_csv(
    body: CsvImportIn,
    user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Importa un CSV (exportado por un sistema legado sin API) al repositorio + RAG."""
    if not (body.csv_text or "").strip():
        raise HTTPException(status_code=422, detail="Pega el contenido del CSV.")
    cols, rows = _parse_csv(body.csv_text, body.delimiter)
    name = body.name.strip() or "CSV importado"
    return _import_as_document(
        session, tenant, user, name=name, content=_as_text(cols, rows),
        area=body.area.strip(), category=body.category.strip(), storage_uri="csv://import",
        rows=len(rows), source_label=f"CSV '{name}'")


@router.get("/{ds_id}/reveal")
def reveal_source(
    ds_id: str,
    user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Revela el DSN (con credenciales) configurado — para el 'ojito' de info
    sensible. Solo ADMIN/DEVOPS y queda auditado."""
    d = _owned(session, tenant, ds_id)
    dsn = decrypt(d.dsn_enc, tenant.kms_key_id) if d.dsn_enc else ""
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="reveal", object_type="datasource",
        object_id=d.id, risk_level="med", reason=f"reveló el DSN de la fuente '{d.name}'",
    ))
    session.commit()
    return {"dsn": dsn}


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
