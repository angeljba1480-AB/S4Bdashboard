"""Document endpoints: upload -> classify -> index (blueprint workflow 9)."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from ..ai.rag import index_document
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..models import AuditEvent, Document, Tenant, User
from ..schemas import DocumentOut
from ..security.classifier import classify_data

router = APIRouter(prefix="/documents", tags=["documents"])


def _out(d: Document) -> DocumentOut:
    return DocumentOut(
        id=d.id, filename=d.filename, mime_type=d.mime_type, sensitivity=d.sensitivity,
        pii_score=d.pii_score, pii_types=[t for t in d.pii_types.split(",") if t],
        indexed=d.indexed, created_at=d.created_at,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> list[DocumentOut]:
    docs = session.exec(select(Document).where(Document.tenant_id == tenant.id)).all()
    return [_out(d) for d in docs]


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload(
    file: UploadFile | None = File(default=None),
    filename: str | None = Form(default=None),
    text: str | None = Form(default=None),
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> DocumentOut:
    """Accept a file upload or raw text. Runs classification + PII + indexing."""
    if file is not None:
        raw = await file.read()
        content = raw.decode("utf-8", errors="ignore")
        name = file.filename or filename or "documento.txt"
        mime = file.content_type or "text/plain"
    elif text is not None:
        content = text
        name = filename or "documento.txt"
        mime = "text/plain"
    else:
        raise HTTPException(status_code=400, detail="Falta archivo o texto")

    digest = hashlib.sha256(content.encode()).hexdigest()
    cls = classify_data(content)

    doc = Document(
        tenant_id=tenant.id, owner_id=user.id, filename=name, mime_type=mime,
        sensitivity=cls.sensitivity, pii_score=cls.pii.score,
        pii_types=",".join(cls.pii.types), storage_uri=f"local://{name}",
        hash=digest, text=content,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    chunks = index_document(session, doc)

    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="upload", object_type="document",
        object_id=doc.id, classification=cls.sensitivity, risk_level="high" if cls.pii.score > 0.3 else "low",
        reason=f"clasificado {cls.sensitivity.value}; {chunks} chunks; PII {cls.pii.types}",
    ))
    session.commit()

    # Fire event-driven automations (e.g. alerta de documento sensible, indexar).
    from .automations import dispatch_event
    dispatch_event(session, tenant, "document_uploaded", {
        "document_id": doc.id, "filename": doc.filename, "sensitivity": cls.sensitivity.value,
    }, user=user)

    return _out(doc)


@router.delete("/{doc_id}")
def delete_document(
    doc_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    session: Session = Depends(get_session),
) -> dict:
    doc = session.get(Document, doc_id)
    if not doc or doc.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    from ..ai.vectorstore import get_vector_store
    from ..models import DocumentChunk

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
