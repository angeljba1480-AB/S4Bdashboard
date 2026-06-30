"""/sharepoint — explorar SharePoint como un Drive: navegar sitios/carpetas/
archivos con la cuenta Microsoft conectada e importar al repositorio + RAG.

A diferencia del conector de `/datasources/sharepoint` (carpeta fija para imports
programados), esto es interactivo: el usuario navega y elige qué traer.
"""
from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from .. import doc_categories
from ..ai.rag import index_document
from ..auth import get_current_tenant, get_current_user
from ..db import get_session
from ..integrations import sharepoint as sp
from ..integrations import token_store
from ..ingest import extract_text
from ..models import AuditEvent, Document, Tenant, User
from ..security.classifier import classify_data

router = APIRouter(prefix="/sharepoint", tags=["sharepoint"])


def _token(session: Session, tenant: Tenant, user: User) -> str:
    tok = token_store.get_valid_access_token(session, tenant, user.id, "microsoft")
    if not tok:
        raise HTTPException(status_code=400, detail="Conecta tu cuenta Microsoft en Integraciones.")
    return tok


@router.get("/sites")
def sites(query: str = "", tenant: Tenant = Depends(get_current_tenant),
          user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    token = _token(session, tenant, user)
    try:
        return {"sites": sp.list_sites(token, query)}
    except Exception as exc:  # pragma: no cover - red/permisos
        raise HTTPException(status_code=400, detail=f"No se pudieron listar los sitios: {exc}")


@router.get("/files")
def files(site: str, folder: str = "", tenant: Tenant = Depends(get_current_tenant),
          user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    token = _token(session, tenant, user)
    try:
        return {"files": sp.list_children(token, site, folder)}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=f"No se pudo listar la carpeta: {exc}")


class ImportBody(BaseModel):
    site: str
    item_id: str
    name: str = ""
    area: str = ""
    category: str = ""


@router.post("/import", status_code=201)
def import_item(body: ImportBody, tenant: Tenant = Depends(get_current_tenant),
                user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> dict:
    token = _token(session, tenant, user)
    try:
        filename, raw = sp.fetch_item(token, body.site, body.item_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo descargar de SharePoint: {exc}")
    name = body.name or filename
    content = extract_text(raw, name, "")
    if not (content or "").strip():
        raise HTTPException(status_code=400, detail="El archivo está vacío o no se pudo extraer texto.")
    cls = classify_data(content)
    cat = doc_categories.get_or_create(session, tenant.id, body.category or "")
    doc = Document(
        tenant_id=tenant.id, owner_id=user.id, filename=name, mime_type="text/plain",
        area=(body.area or "").strip(), category=cat.key if cat else "",
        sensitivity=cls.sensitivity, pii_score=cls.pii.score, pii_types=",".join(cls.pii.types),
        storage_uri=f"sharepoint://{body.site}/{body.item_id}",
        hash=hashlib.sha256(content.encode()).hexdigest(), text=content)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    chunks = index_document(session, doc)
    session.add(AuditEvent(
        tenant_id=tenant.id, user_id=user.id, event_type="upload", object_type="document",
        object_id=doc.id, classification=doc.sensitivity, risk_level="low",
        reason=f"importado de SharePoint ({name}); {chunks} chunks"))
    session.commit()
    return {"id": doc.id, "filename": doc.filename, "sensitivity": doc.sensitivity.value}
