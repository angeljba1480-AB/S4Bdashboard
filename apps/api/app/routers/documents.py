"""Document endpoints: upload -> classify -> index (blueprint workflow 9).

Documents are organized by `area` (org structure) and `category` (a per-tenant,
extensible catalog of document types). Sensitivity is auto-classified but can be
overridden by the user. All uploads are chunked + embedded into the RAG index.
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from .. import doc_categories
from ..ai.rag import index_document
from ..auth import get_current_tenant, get_current_user, require_roles
from ..db import get_session
from ..models import (AuditEvent, Document, DocumentCategory, DocumentChunk, Role,
                      Sensitivity, Tenant, User)
from ..permissions import can_view_area
from ..schemas import DocumentCategoryCreate, DocumentCategoryOut, DocumentOut, DocumentUpdate
from ..security.classifier import classify_data

router = APIRouter(prefix="/documents", tags=["documents"])


def _out(d: Document, labels: dict[str, str]) -> DocumentOut:
    return DocumentOut(
        id=d.id, filename=d.filename, mime_type=d.mime_type,
        area=d.area or "", category=d.category or "",
        category_label=labels.get(d.category or "", ""),
        sensitivity=d.sensitivity, pii_score=d.pii_score,
        pii_types=[t for t in d.pii_types.split(",") if t],
        indexed=d.indexed, created_at=d.created_at,
    )


def _label_map(session: Session, tenant_id: str) -> dict[str, str]:
    return {c.key: c.label for c in doc_categories.list_categories(session, tenant_id)}


def _parse_sensitivity(value: str | None) -> Sensitivity | None:
    """Map a user-provided treatment to a Sensitivity, or None to auto-classify."""
    if not value or value.strip().lower() in ("", "auto"):
        return None
    try:
        return Sensitivity(value.strip().lower())
    except ValueError:
        return None


@router.post("/reindex")
def reindex_all(
    user: User = Depends(require_roles(Role.ADMIN, Role.DEVOPS)),
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    """Reconstruye chunks + embeddings de TODOS los documentos del tenant. Necesario
    tras cambiar de proveedor de embeddings (p. ej. local→NaN, que cambia la dimensión
    del vector). Solo ADMIN/DEVOPS."""
    from ..ai.vectorstore import get_vector_store

    docs = session.exec(select(Document).where(Document.tenant_id == tenant.id)).all()
    valid_ids = {d.id for d in docs}

    # Purga de huérfanos: chunks cuyo documento ya no existe (borrados que pudieran
    # haber dejado rastro en el índice). Así "Re-indexar RAG" también limpia el RAG.
    all_chunks = session.exec(
        select(DocumentChunk).where(DocumentChunk.tenant_id == tenant.id)
    ).all()
    orphan_doc_ids = {c.document_id for c in all_chunks if c.document_id not in valid_ids}
    n_orphans = 0
    for c in all_chunks:
        if c.document_id not in valid_ids:
            session.delete(c)
            n_orphans += 1
    store = get_vector_store()
    if store:
        for did in orphan_doc_ids:
            try:
                store.delete_document(tenant.id, did)
            except Exception:
                pass

    n_docs = n_chunks = 0
    for d in docs:
        try:
            n_chunks += index_document(session, d)
            n_docs += 1
        except Exception:
            continue
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="reindex", object_type="documents",
        object_id="all", risk_level="low",
        reason=f"reindex {n_docs} docs / {n_chunks} chunks · {n_orphans} huérfanos purgados"))
    session.commit()
    return {"documents": n_docs, "chunks": n_chunks, "orphans_purged": n_orphans}


# --- categories catalog -----------------------------------------------------
@router.get("/categories", response_model=list[DocumentCategoryOut])
def list_categories(
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[DocumentCategoryOut]:
    cats = doc_categories.list_categories(session, tenant.id)
    return [DocumentCategoryOut(id=c.id, key=c.key, label=c.label,
                                description=c.description, system=c.system) for c in cats]


@router.post("/categories", response_model=DocumentCategoryOut, status_code=201)
def create_category(
    body: DocumentCategoryCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> DocumentCategoryOut:
    if not body.label.strip():
        raise HTTPException(status_code=422, detail="La categoría necesita un nombre")
    c = doc_categories.get_or_create(session, tenant.id, body.label.strip(),
                                     label=body.label.strip(), description=body.description)
    return DocumentCategoryOut(id=c.id, key=c.key, label=c.label,
                              description=c.description, system=c.system)


@router.delete("/categories/{cat_id}")
def delete_category(
    cat_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    c = session.get(DocumentCategory, cat_id)
    if not c or c.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    if c.system:
        raise HTTPException(status_code=400, detail="No se puede borrar una categoría base del sistema")
    session.delete(c)
    session.commit()
    return {"ok": True}


# --- documents --------------------------------------------------------------
@router.get("", response_model=list[DocumentOut])
def list_documents(
    area: str | None = None,
    category: str | None = None,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[DocumentOut]:
    q = select(Document).where(Document.tenant_id == tenant.id)
    if area:
        q = q.where(Document.area == area)
    if category:
        q = q.where(Document.category == category)
    docs = session.exec(q).all()
    # Hierarchical visibility: non-privileged users only see their own area + general.
    docs = [d for d in docs if can_view_area(user, d.area or "")]
    labels = _label_map(session, tenant.id)
    return [_out(d, labels) for d in docs]


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload(
    file: UploadFile | None = File(default=None),
    filename: str | None = Form(default=None),
    text: str | None = Form(default=None),
    area: str | None = Form(default=None),
    category: str | None = Form(default=None),
    sensitivity: str | None = Form(default=None),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DocumentOut:
    """Accept a file upload or raw text. Runs classification + PII + indexing.

    `area`/`category` organize the document; an unknown category is auto-created.
    `sensitivity` (public|internal|confidential|restricted) overrides the
    auto-classifier; omit or 'auto' to let the system decide.
    """
    if file is not None:
        raw = await file.read()
        # El nombre explícito (editado por el usuario) gana sobre el del archivo.
        name = (filename or "").strip() or file.filename or "documento.txt"
        mime = file.content_type or "text/plain"
        # Antivirus + tope de tamaño antes de procesar (blueprint: upload → antivirus).
        from ..security.antivirus import scan
        verdict = scan(raw, name)
        if not verdict.ok:
            session.add(AuditEvent(
                tenant_id=tenant.id, user_id=user.id, event_type="security", object_type="document",
                object_id=name, risk_level="high",
                reason=f"upload bloqueado por antivirus ({verdict.engine}): {verdict.reason}"
                       + (f" [{verdict.threat}]" if verdict.threat else ""),
            ))
            session.commit()
            from .. import alerts as _alerts
            _alerts.dispatch(session, tenant.id, "antivirus", "Archivo rechazado por antivirus",
                             f"{name}: {verdict.reason}" + (f" [{verdict.threat}]" if verdict.threat else ""),
                             level="error")
            raise HTTPException(status_code=422, detail=f"Archivo rechazado: {verdict.reason}.")
        # Extrae texto según el tipo (PDF/DOCX/texto/CSV) — OCR opcional si hay binario.
        from ..ingest import extract_text
        content = extract_text(raw, name, mime)
    elif text is not None:
        content = text
        name = filename or "documento.txt"
        mime = "text/plain"
    else:
        raise HTTPException(status_code=400, detail="Falta archivo o texto")

    digest = hashlib.sha256(content.encode()).hexdigest()
    cls = classify_data(content)
    chosen = _parse_sensitivity(sensitivity) or cls.sensitivity
    cat = doc_categories.get_or_create(session, tenant.id, category or "")

    doc = Document(
        tenant_id=tenant.id, owner_id=user.id, filename=name, mime_type=mime,
        area=(area or "").strip(), category=cat.key if cat else "",
        sensitivity=chosen, pii_score=cls.pii.score,
        pii_types=",".join(cls.pii.types), storage_uri=f"local://{name}",
        hash=digest, text=content,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    chunks = index_document(session, doc)

    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="upload", object_type="document",
        object_id=doc.id, classification=doc.sensitivity, risk_level="high" if cls.pii.score > 0.3 else "low",
        reason=f"clasificado {doc.sensitivity.value}; {chunks} chunks; PII {cls.pii.types}",
    ))
    session.commit()

    # Fire event-driven automations (e.g. alerta de documento sensible, indexar).
    from .automations import dispatch_event
    dispatch_event(session, tenant, "document_uploaded", {
        "document_id": doc.id, "filename": doc.filename, "sensitivity": doc.sensitivity.value,
    }, user=user)

    # Alerta configurable de ingesta de documentos.
    from .. import alerts as _alerts
    _alerts.dispatch(session, tenant.id, "ingest", "Documento ingresado",
                     f"{doc.filename} · {doc.sensitivity.value} · {chunks} fragmentos", level="info")

    return _out(doc, _label_map(session, tenant.id))


@router.patch("/{doc_id}", response_model=DocumentOut)
def update_document(
    doc_id: str,
    body: DocumentUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DocumentOut:
    """Re-tag a document: change its area, category and/or treatment."""
    doc = session.get(Document, doc_id)
    if not doc or doc.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not can_view_area(user, doc.area or ""):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta área")
    if body.area is not None:
        doc.area = body.area.strip()
    if body.category is not None:
        cat = doc_categories.get_or_create(session, tenant.id, body.category)
        doc.category = cat.key if cat else ""
    if body.sensitivity is not None:
        doc.sensitivity = body.sensitivity
        # Keep chunk-level sensitivity in sync so RAG retrieval reflects the change.
        for ch in session.exec(select(DocumentChunk).where(DocumentChunk.document_id == doc.id)).all():
            ch.sensitivity = body.sensitivity
            session.add(ch)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return _out(doc, _label_map(session, tenant.id))


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    doc = session.get(Document, doc_id)
    if not doc or doc.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not can_view_area(user, doc.area or ""):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta área")

    from ..ai.vectorstore import get_vector_store

    for ch in session.exec(select(DocumentChunk).where(DocumentChunk.document_id == doc.id)).all():
        session.delete(ch)
    store = get_vector_store()
    if store:
        store.delete_document(tenant.id, doc.id)
    session.delete(doc)
    session.add(AuditEvent(
        tenant_id=tenant.id, event_type="delete", object_type="document", object_id=doc.id,
        risk_level="low", reason="documento y chunks eliminados (retención)",
    ))
    session.commit()
    return {"ok": True}
